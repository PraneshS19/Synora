import re
import json
import uuid
from typing import Optional
from fastapi import HTTPException

from app.services.storage import storage_service
from app.services.extractor import DocumentExtractor
from app.providers.translation import get_translation_provider, NullTranslationProvider
from app.models.schemas import (
    TranslationJobResponse,
    TranslationSegment,
)

SUPPORTED_SOURCE_LANGUAGES = {"English", "Tamil", "Hindi", "Telugu", "Kannada", "Malayalam"}
SUPPORTED_TARGET_LANGUAGES = {"Tamil", "Hindi", "Telugu", "Kannada", "Malayalam", "Bengali", "Marathi", "English"}

class TranslationService:
    def __init__(self):
        self.storage = storage_service

    def create_job(
        self,
        file_ids: list[str],
        source_text: Optional[str],
        source_lang: str,
        target_lang: str
    ) -> TranslationJobResponse:
        job_id = str(uuid.uuid4())

        # Validate language pair
        src_norm = source_lang.strip().capitalize()
        tgt_norm = target_lang.strip().capitalize()

        if src_norm.lower() == tgt_norm.lower():
            raise HTTPException(
                status_code=400,
                detail="Source and target languages cannot be identical. Please select distinct languages."
            )

        if src_norm not in SUPPORTED_SOURCE_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Source language '{source_lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_SOURCE_LANGUAGES))}"
            )

        if tgt_norm not in SUPPORTED_TARGET_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Target language '{target_lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_TARGET_LANGUAGES))}"
            )

        # Collect raw text
        raw_texts: list[str] = []
        if source_text and source_text.strip():
            raw_texts.append(source_text.strip())

        for fid in file_ids:
            record = self.storage.get_file_record(fid)
            if not record:
                raise HTTPException(status_code=404, detail=f"File ID '{fid}' not found.")
            file_path = self.storage.get_file_path(fid)
            if file_path and file_path.exists():
                passages = DocumentExtractor.extract_from_path(file_path)
                for p in passages:
                    if p.text.strip():
                        raw_texts.append(p.text.strip())

        if not raw_texts:
            raise HTTPException(
                status_code=400,
                detail="No source content found. Please provide an uploaded document or source text."
            )

        full_content = "\n\n".join(raw_texts)

        # Segment content into sentences / clauses
        raw_segments = [
            s.strip()
            for s in re.split(r"(?<=[.!?\n])\s+", full_content)
            if s.strip() and len(s.strip()) > 3
        ]

        if not raw_segments:
            raw_segments = [full_content[:500]]

        # Record queued job
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO translation_jobs (id, status, source_lang, target_lang, segments_json, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, "processing", source_lang, target_lang, "[]", None)
            )
            conn.commit()

        try:
            from app.providers.translation import LocalTranslationProvider
            provider = get_translation_provider()
            translated_texts = provider.translate_segments(raw_segments, source_lang, target_lang)

            is_unconfigured = isinstance(provider, (NullTranslationProvider, LocalTranslationProvider)) or all(not (t and t.strip()) for t in translated_texts)

            segments: list[TranslationSegment] = []
            for idx, (src, trans) in enumerate(zip(raw_segments, translated_texts), start=1):
                is_seg_blank = not (trans and trans.strip())
                flag = "no_model" if (is_unconfigured or is_seg_blank) else "unreviewed"
                segments.append(TranslationSegment(
                    id=f"seg-{idx}",
                    source=src,
                    translated=trans if not is_unconfigured else "",
                    reviewFlag=flag,
                    confidence=0.0 if (is_unconfigured or is_seg_blank) else 0.92
                ))

            segments_json = json.dumps([s.model_dump() for s in segments])

            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE translation_jobs SET status = 'completed', segments_json = ? WHERE id = ?",
                    (segments_json, job_id)
                )
                conn.commit()

            limitations = [
                "No translation model is configured. Translated segments are blank; configure a translation provider (IndicTrans2 or Gemini) or enter translations manually."
            ] if is_unconfigured else [
                "Machine translation draft. Human review required before institutional publication."
            ]

            return TranslationJobResponse(
                id=job_id,
                status="completed",
                sourceLanguage=source_lang,
                targetLanguage=target_lang,
                segments=segments,
                limitations=limitations,
                providerUsed=provider.__class__.__name__
            )

        except Exception as e:
            err_msg = str(e)
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE translation_jobs SET status = 'failed', error = ? WHERE id = ?",
                    (err_msg, job_id)
                )
                conn.commit()

            return TranslationJobResponse(
                id=job_id,
                status="failed",
                sourceLanguage=source_lang,
                targetLanguage=target_lang,
                segments=[],
                error=err_msg
            )

    def get_job(self, job_id: str) -> Optional[TranslationJobResponse]:
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM translation_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            segments_data = json.loads(row["segments_json"] or "[]")
            segments = [TranslationSegment(**s) for s in segments_data]

            is_unconfigured = all(s.reviewFlag == "no_model" or not s.translated.strip() for s in segments) if segments else False
            limitations = [
                "No translation model is configured. Translated segments are blank; configure a translation provider or enter translations manually."
            ] if is_unconfigured else [
                "Machine translation draft. Human review required before institutional publication."
            ]

            return TranslationJobResponse(
                id=row["id"],
                status=row["status"],
                sourceLanguage=row["source_lang"],
                targetLanguage=row["target_lang"],
                segments=segments,
                limitations=limitations,
                error=row["error"]
            )

    def update_segment(self, job_id: str, segment_id: str, new_translated: str, review_flag: str = "edited") -> TranslationJobResponse:
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Translation job not found.")

        updated = False
        for seg in job.segments:
            if seg.id == segment_id:
                seg.translated = new_translated
                seg.reviewFlag = review_flag
                updated = True
                break

        if not updated:
            raise HTTPException(status_code=404, detail=f"Segment '{segment_id}' not found in job.")

        segments_json = json.dumps([s.model_dump() for s in job.segments])
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE translation_jobs SET segments_json = ? WHERE id = ?",
                (segments_json, job_id)
            )
            conn.commit()

        return job

translation_service = TranslationService()
