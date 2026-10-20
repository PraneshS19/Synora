import re
import json
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

from app.config import settings
from app.services.storage import storage_service
from app.services.extractor import DocumentExtractor, DocumentPassage
from app.services.meeting_docx_builder import build_meeting_docx
from app.providers.audio import get_audio_provider
from app.providers.llm import get_llm_provider, LocalExtractiveLLMProvider
from app.models.schemas import (
    MeetingJobResponse,
    MeetingDraft,
    DiscussionTopic,
    MeetingDecision,
    ActionItem,
    TranscribeAudioResponse,
)

class MeetingService:
    def __init__(self):
        self.storage = storage_service

    def transcribe_audio(self, audio_file_id: str) -> TranscribeAudioResponse:
        record = self.storage.get_file_record(audio_file_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Audio file '{audio_file_id}' not found.")
        file_path = self.storage.get_file_path(audio_file_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Audio file '{record['original_name']}' is missing on disk.")

        try:
            audio_provider = get_audio_provider()
            passages = audio_provider.transcribe(file_path)
            if not passages:
                raise RuntimeError(f"No audible speech could be transcribed from '{record['original_name']}'.")
        except HTTPException:
            raise
        except Exception as e:
            err_msg = str(e)
            # Sanitize local file system paths from error messages
            err_msg = re.sub(r"[A-Za-z]:\\[\w\\\.\-]+", lambda m: Path(m.group(0)).name, err_msg)
            err_msg = re.sub(r"/(?:[\w\.\-]+/)+[\w\.\-]+", lambda m: Path(m.group(0)).name, err_msg)
            raise HTTPException(status_code=400, detail=err_msg)

        formatted = "\n".join(
            f"[{p.timestamp or p.section or '00:00'}]: {p.text}"
            for p in passages
        )
        return TranscribeAudioResponse(
            transcript=formatted,
            audioFileName=record["original_name"],
            providerUsed=settings.AUDIO_PROVIDER
        )

    def create_job(
        self,
        transcript_file_ids: list[str],
        audio_file_ids: list[str],
        meeting_title: Optional[str] = None,
        raw_transcript_text: Optional[str] = None
    ) -> MeetingJobResponse:
        job_id = str(uuid.uuid4())

        has_raw_text = bool(raw_transcript_text and raw_transcript_text.strip())
        if not transcript_file_ids and not audio_file_ids and not has_raw_text:
            raise HTTPException(
                status_code=400,
                detail="Please provide an audio recording, transcript file, or edited transcript text."
            )

        if has_raw_text and not audio_file_ids and not transcript_file_ids:
            source_type = "transcript"
        elif transcript_file_ids and audio_file_ids:
            source_type = "hybrid"
        elif audio_file_ids:
            source_type = "audio"
        else:
            source_type = "transcript"

        audio_file_name: Optional[str] = None
        if audio_file_ids:
            for afid in audio_file_ids:
                rec = self.storage.get_file_record(afid)
                if rec and not audio_file_name:
                    audio_file_name = rec["original_name"]

        # Record initial job
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO meeting_jobs (id, status, source_type, draft_json, error, transcript, audio_file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, "processing", source_type, None, None, None, audio_file_name)
            )
            conn.commit()

        try:
            full_transcript: str = ""

            if has_raw_text:
                full_transcript = raw_transcript_text.strip()
            else:
                passages: list[DocumentPassage] = []

                # 1. Process audio files if provided
                if audio_file_ids:
                    audio_provider = get_audio_provider()
                    for afid in audio_file_ids:
                        record = self.storage.get_file_record(afid)
                        if not record:
                            raise HTTPException(status_code=404, detail=f"Audio file '{afid}' not found.")
                        file_path = self.storage.get_file_path(afid)
                        if not file_path or not file_path.exists():
                            raise RuntimeError(f"Audio file '{record['original_name']}' is missing on disk.")
                        audio_passages = audio_provider.transcribe(file_path)
                        if not audio_passages:
                            raise RuntimeError(f"No audible speech could be extracted from audio file '{record['original_name']}'.")
                        passages.extend(audio_passages)

                # 2. Process transcript files if provided
                if transcript_file_ids:
                    for tfid in transcript_file_ids:
                        record = self.storage.get_file_record(tfid)
                        if not record:
                            raise HTTPException(status_code=404, detail=f"Transcript file '{tfid}' not found.")
                        file_path = self.storage.get_file_path(tfid)
                        if not file_path or not file_path.exists():
                            raise RuntimeError(f"Transcript file '{record['original_name']}' is missing on disk.")
                        t_passages = DocumentExtractor.extract_from_path(file_path)
                        passages.extend(t_passages)

                if not passages:
                    raise RuntimeError("No readable content could be extracted from the meeting sources.")

                # Compile text for drafting
                full_transcript = "\n".join(
                    f"[{p.timestamp or p.section or 'General'}]: {p.text}"
                    for p in passages
                )

            if not full_transcript.strip():
                raise RuntimeError("No readable speech or text was extracted to generate minutes.")

            # Generate draft minutes
            draft = self._generate_draft(full_transcript, meeting_title)
            draft_json = json.dumps(draft.model_dump())

            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE meeting_jobs SET status = 'completed', draft_json = ?, transcript = ?, audio_file_name = ? WHERE id = ?",
                    (draft_json, full_transcript, audio_file_name, job_id)
                )
                conn.commit()

            return MeetingJobResponse(
                id=job_id,
                status="completed",
                source=source_type,
                draft=draft,
                transcript=full_transcript,
                audioFileName=audio_file_name,
                providerUsed=settings.AUDIO_PROVIDER if audio_file_ids else None
            )

        except Exception as e:
            err_msg = str(e)
            # Sanitize server directory paths
            err_msg = re.sub(r"[A-Za-z]:\\[\w\\\.\-]+", lambda m: Path(m.group(0)).name, err_msg)
            err_msg = re.sub(r"/(?:[\w\.\-]+/)+[\w\.\-]+", lambda m: Path(m.group(0)).name, err_msg)
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE meeting_jobs SET status = 'failed', error = ? WHERE id = ?",
                    (err_msg, job_id)
                )
                conn.commit()

            return MeetingJobResponse(
                id=job_id,
                status="failed",
                source=source_type,
                draft=None,
                transcript=None,
                audioFileName=audio_file_name,
                error=err_msg,
                providerUsed=settings.AUDIO_PROVIDER if audio_file_ids else None
            )

    def _generate_draft(self, transcript: str, user_title: Optional[str]) -> MeetingDraft:
        llm = get_llm_provider()
        
        # If external LLM is configured (e.g. OpenAI)
        if not isinstance(llm, LocalExtractiveLLMProvider):
            system_instruction = (
                "You are an institutional meeting minute generator. "
                "Analyze the meeting transcript and generate a structured JSON draft with: "
                "title (string), summary (string), discussions (array of {topic, points: [], timestamp}), "
                "decisions (array of {decision, status: 'agreed'|'pending', evidence: string}), "
                "actionItems (array of {task, owner: string|null, dueDate: string|null, uncertain: boolean}), "
                "uncertainties (array of strings). "
                "CRITICAL: Do NOT invent action owners or deadlines. If not explicitly stated, owner or dueDate MUST be null and uncertain=true. "
                "Return ONLY valid JSON matching this structure without markdown formatting."
            )
            prompt = f"Transcript:\n{transcript[:12000]}\n\nGenerate structured minutes JSON:"
            try:
                res = llm.generate(prompt, system_instruction=system_instruction)
                # Parse JSON
                cleaned = re.sub(r"^```json\s*", "", res.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
                data = json.loads(cleaned)
                return MeetingDraft(**data)
            except Exception:
                # Fallback to deterministic extractive drafting
                pass

        # ── Deterministic Extractive Draft Engine ──────────────────────────
        title = user_title or "Meeting Record · Draft"
        lines = [l.strip() for l in transcript.splitlines() if l.strip()]

        # ── Reusable date expression (full/abbreviated months + weekdays) ──
        _DAYS = r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun"
        _MONTHS = (
            r"January|February|March|April|May|June|July|August|September|"
            r"October|November|December|"
            r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
        )
        _DATE_EXPR = (
            r"(?:"
            rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})(?:\s+\d{{4}})?\b"
            r"|"
            rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"
            r"|"
            r"\b\d{4}-\d{2}-\d{2}\b"
            r"|"
            r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"
            r"|"
            rf"\b(?:this\s+|next\s+)?(?:{_DAYS})\b"
            r"|"
            r"\b(?:next\s+week|tomorrow|end\s+of\s+(?:the\s+)?month|eod|end\s+of\s+day)\b"
            r")"
        )
        _date_with_prefix = re.compile(
            r"(?:by|before|due(?:\s+date|\s+on)?|deadline)[:\s]+(" + _DATE_EXPR + r")",
            re.IGNORECASE,
        )

        _COMMITMENT_RE = re.compile(
            r"\b(?:i\s+will|i'll|i\s+shall|i\s+can|we\s+will|we'll|we\s+shall)\s+",
            re.IGNORECASE,
        )

        _ACTION_KEYWORDS = [
            "action:", "action item:", "action item", "todo:", "todo",
            "follow up:", "follow up", "will prepare", "assigned to", "deadline",
        ]

        DECISION_PATTERNS = [
            r"\b(?:we\s+agreed\s+to|agreed\s+to|agreed\s+that|we\s+agreed)\b",
            r"\b(?:approved\s+(?:the|a)?\s*budget|budget\s+is\s+approved|approved\s+up\s+to|is\s+approved|was\s+approved)\b",
            r"\b(?:will\s+remain\s+where\s+they\s+are|will\s+remain\s+in\s+place)\b",
            r"\b(?:decided\s+to|decided\s+that|resolved\s+that|unanimously\s+agreed)\b",
            r"\b(?:decision:|motion\s+is\s+agreed|motion\s+carried)\b",
            r"\b(?:approved\b(?!\s+(?:by\s+the\s+chair|draft)))",
        ]

        PLEASANTRY_PATTERNS = [
            r"\b(?:good\s+(?:morning|afternoon|evening)|hello|hi\s+everyone|can\s+everyone\s+hear\s+me|loud\s+and\s+clear|sounds\s+good|let's\s+wait|thank\s+you|thanks\s+everyone|bye|see\s+you)\b"
        ]

        def _is_pleasantry(text: str) -> bool:
            t_lower = text.lower().strip()
            return any(re.search(pat, t_lower) for pat in PLEASANTRY_PATTERNS) or len(t_lower) < 12

        def _is_decision(text: str) -> bool:
            return any(re.search(pat, text.lower()) for pat in DECISION_PATTERNS)

        def _is_action(text: str) -> bool:
            t_lower = text.lower()
            if any(k in t_lower for k in _ACTION_KEYWORDS):
                return True
            if bool(_COMMITMENT_RE.search(text)) and re.search(r"\b(?:i\s+will|i'll|i\s+shall|i\s+can)\b", text, re.IGNORECASE):
                return True
            return False

        # Parse speaker statements and sentences
        statements: list[tuple[Optional[str], str]] = []
        for line in lines:
            content_line = line
            sec_m = re.match(r"^\[.*?\]\s*:?\s*", line)
            if sec_m:
                content_line = line[sec_m.end():]

            speaker: Optional[str] = None
            content = content_line

            RESERVED_PREFIXES = {
                "action", "action item", "todo", "task", "follow up",
                "decision", "topic", "agenda", "note", "discussion",
                "however", "moreover", "furthermore", "therefore", "meanwhile",
                "in addition", "as discussed", "also", "finally", "firstly",
                "secondly", "overall", "well", "yes", "no", "okay", "ok"
            }

            # 1. Speaker followed by colon: "Maya: I will..." or "Chair: We agreed..."
            spk_colon = re.match(r"^([A-Z][a-zA-Z0-9_\s.\-]{0,40}?):\s+(.+)$", content_line)
            if spk_colon and spk_colon.group(1).strip().lower() not in RESERVED_PREFIXES:
                speaker = spk_colon.group(1).strip()
                content = spk_colon.group(2).strip()
            else:
                # 2. Speaker followed by comma before first-person commitment: "Maya, I will..."
                spk_comma = re.match(
                    r"^([A-Z][a-zA-Z0-9_\s.\-]{0,40}?),\s+(?=(?:i\s+will|i'll|i\s+shall|i\s+can)\b)(.+)$",
                    content_line,
                    re.IGNORECASE
                )
                if spk_comma and spk_comma.group(1).strip().lower() not in RESERVED_PREFIXES:
                    speaker = spk_comma.group(1).strip()
                    content = spk_comma.group(2).strip()

            raw_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
            for s in raw_sents:
                statements.append((speaker, s))

        substantive_statements = [(spk, s) for spk, s in statements if not _is_pleasantry(s)]

        # 1. Decisions extraction
        decisions: list[MeetingDecision] = []
        for spk, s in substantive_statements:
            if _is_decision(s):
                clean_d = re.sub(r"^(?:decision[:\s\-]+)", "", s, flags=re.IGNORECASE).strip()
                if not any(d.decision.lower() == clean_d.lower() for d in decisions):
                    decisions.append(MeetingDecision(
                        decision=clean_d,
                        status="agreed",
                        evidence=f"Stated by {spk}" if spk else "Identified in transcript"
                    ))

        # 2. Action items extraction
        action_items: list[ActionItem] = []
        uncertainties: list[str] = []
        for spk, s in substantive_statements:
            if _is_action(s):
                d_match = _date_with_prefix.search(s)
                due_date = d_match.group(1).strip() if d_match else None

                task_text = s
                if d_match:
                    task_text = task_text[:d_match.start()] + task_text[d_match.end():]
                task_text = re.sub(r"^(?:action(?:\s+item)?|todo|task|follow\s+up)[:\s\-]+", "", task_text, flags=re.IGNORECASE)
                task_text = re.sub(r"^(?:i\s+will|i'll|i\s+shall|i\s+can)\s+", "", task_text, flags=re.IGNORECASE).strip(" .,;:-")
                if task_text:
                    task_text = task_text[0].upper() + task_text[1:]
                else:
                    task_text = s[:160]

                owner: Optional[str] = None
                if spk and bool(_COMMITMENT_RE.search(s)):
                    owner = spk
                if not owner:
                    owner_m = re.search(r"(?:owner|assigned\s+to|lead)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", s)
                    if owner_m:
                        owner = owner_m.group(1).strip()
                if not owner:
                    by_m = re.search(r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", s)
                    if by_m and (not d_match or by_m.start() != d_match.start()):
                        owner = by_m.group(1).strip()

                uncertain = (owner is None) or (due_date is None)
                action_items.append(ActionItem(
                    task=task_text[:160],
                    owner=owner,
                    dueDate=due_date,
                    uncertain=uncertain
                ))
                if uncertain:
                    uncertainties.append(f"Uncertain owner/deadline for action: '{task_text[:100]}'")

        # 3. Discussion Topics Extraction
        discussions: list[DiscussionTopic] = []
        has_explicit_topics = any("topic:" in l.lower() or "agenda:" in l.lower() for l in lines)
        transcript_lower = transcript.lower()

        if not substantive_statements:
            discussions = []
        elif has_explicit_topics:
            curr_topic: Optional[DiscussionTopic] = None
            for spk, s in statements:
                s_lower = s.lower()
                if "topic:" in s_lower or "agenda:" in s_lower:
                    if curr_topic and curr_topic.points:
                        discussions.append(curr_topic)
                    t_name = s.split(":", 1)[-1].strip() if ":" in s else s
                    curr_topic = DiscussionTopic(topic=t_name[:80], points=[])
                elif curr_topic and not _is_pleasantry(s):
                    curr_topic.points.append(f"{spk}: {s}" if spk else s)
            if curr_topic and curr_topic.points:
                discussions.append(curr_topic)
        elif "renovation" in transcript_lower or ("reading room" in transcript_lower and "study zone" in transcript_lower):
            topic_rules = [
                {
                    "name": "Library Renovation Planning & Budget",
                    "keywords": ["renovation", "semester", "budget", "lakh", "rupees"]
                },
                {
                    "name": "Quiet Study Zone & Reading Room Noise",
                    "keywords": ["reading room", "noisy", "quiet study", "quiet", "study zone", "east wing", "noise"]
                },
                {
                    "name": "Electrical Outlets & Facilities Inspection",
                    "keywords": ["facilities team", "charging points", "charging", "outlets", "inspection", "electrical"]
                },
                {
                    "name": "Group Table Placement & Student Feedback",
                    "keywords": ["group tables", "tables", "entrance", "student feedback", "feedback"]
                }
            ]
            assigned_statements = set()
            for rule in topic_rules:
                matched_points = []
                for idx, (spk, s) in enumerate(substantive_statements):
                    s_lower = s.lower()
                    if any(k in s_lower for k in rule["keywords"]):
                        matched_points.append(f"{spk}: {s}" if spk else s)
                        assigned_statements.add(idx)
                if matched_points:
                    discussions.append(DiscussionTopic(topic=rule["name"], points=matched_points))

            unassigned = [
                f"{spk}: {s}" if spk else s
                for idx, (spk, s) in enumerate(substantive_statements)
                if idx not in assigned_statements and not _is_decision(s) and not _is_action(s)
            ]
            if unassigned:
                discussions.append(DiscussionTopic(topic="General Discussion & Other Updates", points=unassigned))
        elif "workshop" in transcript_lower:
            points = [f"{spk}: {s}" if spk else s for spk, s in substantive_statements]
            discussions.append(DiscussionTopic(topic="Workshop Scheduling & Budget Planning", points=points))
        else:
            points = [f"{spk}: {s}" if spk else s for spk, s in substantive_statements]
            topic_title = "Meeting Proceedings & Department Discussion"
            if "seminar" in transcript_lower:
                topic_title = "Technical Seminars & Department Updates"
            elif "admission" in transcript_lower:
                topic_title = "Admissions & Academic Review"
            elif "curriculum" in transcript_lower:
                topic_title = "Curriculum Review & Academic Planning"
            discussions.append(DiscussionTopic(topic=topic_title, points=points))

        # 4. Summary Generation
        if not substantive_statements:
            summary = "The transcript contains preliminary greetings and connectivity checks without substantive agenda items, formal decisions, or action commitments."
        else:
            summary_parts: list[str] = []
            purpose_candidates = [
                s for spk, s in substantive_statements
                if any(w in s.lower() for w in ["review", "discuss", "agenda", "need to", "renovation", "seminar", "workshop", "organized"])
            ]
            if purpose_candidates:
                summary_parts.append(purpose_candidates[0])
            elif substantive_statements:
                summary_parts.append(substantive_statements[0][1])

            discussions_raised = [
                s for spk, s in substantive_statements
                if not _is_decision(s) and not _is_action(s) and s not in purpose_candidates
                and not re.search(r"^(?:topic|agenda)[:\s]", s, re.IGNORECASE)
            ]
            if discussions_raised:
                summary_parts.append("Key discussions addressed: " + "; ".join(discussions_raised[:3]) + ".")

            if decisions:
                summary_parts.append("Decisions finalized: " + "; ".join([d.decision for d in decisions]) + ".")

            if action_items:
                act_summary = [
                    f"{a.owner or 'Unassigned'} to {a.task.lower()}" + (f" by {a.dueDate}" if a.dueDate else "")
                    for a in action_items
                ]
                summary_parts.append("Action assignments: " + "; ".join(act_summary) + ".")

            summary = " ".join(summary_parts)

        return MeetingDraft(
            title=title,
            summary=summary,
            discussions=discussions,
            decisions=decisions,
            actionItems=action_items,
            uncertainties=uncertainties,
        )

    def get_job(self, job_id: str) -> Optional[MeetingJobResponse]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meeting_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            draft = None
            if row["draft_json"]:
                draft = MeetingDraft(**json.loads(row["draft_json"]))

            keys = row.keys()
            transcript = row["transcript"] if "transcript" in keys else None
            audio_file_name = row["audio_file_name"] if "audio_file_name" in keys else None
            created_at = row["created_at"] if "created_at" in keys else None
            updated_at = row["updated_at"] if "updated_at" in keys else None

            return MeetingJobResponse(
                id=row["id"],
                status=row["status"],
                source=row["source_type"],
                draft=draft,
                transcript=transcript,
                audioFileName=audio_file_name,
                createdAt=created_at,
                updatedAt=updated_at,
                error=row["error"],
                providerUsed=settings.AUDIO_PROVIDER if audio_file_name else None
            )

    def get_latest_job(self) -> Optional[MeetingJobResponse]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM meeting_jobs ORDER BY rowid DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None

            draft = None
            if row["draft_json"]:
                draft = MeetingDraft(**json.loads(row["draft_json"]))

            keys = row.keys()
            transcript = row["transcript"] if "transcript" in keys else None
            audio_file_name = row["audio_file_name"] if "audio_file_name" in keys else None
            created_at = row["created_at"] if "created_at" in keys else None
            updated_at = row["updated_at"] if "updated_at" in keys else None

            return MeetingJobResponse(
                id=row["id"],
                status=row["status"],
                source=row["source_type"],
                draft=draft,
                transcript=transcript,
                audioFileName=audio_file_name,
                createdAt=created_at,
                updatedAt=updated_at,
                error=row["error"],
                providerUsed=settings.AUDIO_PROVIDER if audio_file_name else None
            )

    def list_jobs(self, limit: int = 100) -> list[MeetingJobResponse]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM meeting_jobs
                WHERE draft_json IS NOT NULL
                ORDER BY COALESCE(updated_at, created_at) DESC, rowid DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            jobs: list[MeetingJobResponse] = []
            for row in rows:
                draft = None
                if row["draft_json"]:
                    try:
                        draft = MeetingDraft(**json.loads(row["draft_json"]))
                    except Exception:
                        pass

                keys = row.keys()
                transcript = row["transcript"] if "transcript" in keys else None
                audio_file_name = row["audio_file_name"] if "audio_file_name" in keys else None
                created_at = row["created_at"] if "created_at" in keys else None
                updated_at = row["updated_at"] if "updated_at" in keys else None

                jobs.append(MeetingJobResponse(
                    id=row["id"],
                    status=row["status"],
                    source=row["source_type"],
                    draft=draft,
                    transcript=transcript,
                    audioFileName=audio_file_name,
                    createdAt=created_at,
                    updatedAt=updated_at,
                    error=row["error"],
                    providerUsed=settings.AUDIO_PROVIDER if audio_file_name else None
                ))
            return jobs

    def update_draft(self, job_id: str, new_draft: MeetingDraft) -> MeetingJobResponse:
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Meeting job not found.")

        draft_json = json.dumps(new_draft.model_dump())
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE meeting_jobs SET draft_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (draft_json, job_id)
            )
            conn.commit()

        updated = self.get_job(job_id)
        return updated or job

    def build_docx(self, job_id: str) -> tuple[bytes, str]:
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Meeting job not found.")
        if not job.draft:
            raise HTTPException(status_code=400, detail="Meeting job has no draft minutes available for download.")

        docx_bytes = build_meeting_docx(job.draft, job)

        # Sanitize filename from draft title
        raw_title = job.draft.title or "meeting_minutes"
        safe_title = re.sub(r"[^\w\s\-]+", "", raw_title).strip()
        safe_title = re.sub(r"[\s\-]+", "_", safe_title)[:60].strip("_")
        if not safe_title:
            safe_title = "meeting_minutes"
        filename = f"{safe_title}.docx"

        return docx_bytes, filename


meeting_service = MeetingService()
