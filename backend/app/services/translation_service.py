import re
import json
import uuid
from pathlib import Path
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

        source_file_name = None
        source_file_ext = None
        if file_ids:
            rec = self.storage.get_file_record(file_ids[0])
            if rec:
                source_file_name = rec.get("original_name")
                source_file_ext = Path(source_file_name).suffix.lower() if source_file_name else None

        # Check if source is a single DOCX upload to preserve document structure
        is_structured_docx = (
            len(file_ids) == 1
            and not (source_text and source_text.strip())
            and source_file_ext == ".docx"
        )

        doc_blocks = None
        raw_segments = []
        if is_structured_docx:
            fid = file_ids[0]
            record = self.storage.get_file_record(fid)
            if not record:
                raise HTTPException(status_code=404, detail=f"File ID '{fid}' not found.")
            file_path = self.storage.get_file_path(fid)
            if not file_path or not file_path.exists():
                raise HTTPException(status_code=404, detail="Uploaded file missing on disk.")
            try:
                doc_blocks = DocumentExtractor.extract_structured_docx(file_path)
            except RuntimeError as e:
                raise HTTPException(status_code=400, detail=str(e))

            texts_to_translate = [b.text for b in doc_blocks if b.text.strip()]
            if not texts_to_translate:
                raise HTTPException(status_code=400, detail="No readable text found in document.")

        else:
            raw_texts: list[str] = []
            if source_text and source_text.strip():
                raw_texts.append(source_text.strip())

            for fid in file_ids:
                record = self.storage.get_file_record(fid)
                if not record:
                    raise HTTPException(status_code=404, detail=f"File ID '{fid}' not found.")
                file_path = self.storage.get_file_path(fid)
                if file_path and file_path.exists():
                    try:
                        passages = DocumentExtractor.extract_from_path(file_path)
                        for p in passages:
                            if p.text.strip():
                                raw_texts.append(p.text.strip())
                    except RuntimeError as e:
                        raise HTTPException(status_code=400, detail=str(e))

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

            texts_to_translate = raw_segments

        # Record queued job
        with self.storage._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO translation_jobs (id, status, source_lang, target_lang, segments_json, error, source_file_name, source_file_ext)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, "processing", source_lang, target_lang, "[]", None, source_file_name, source_file_ext)
            )
            conn.commit()

        try:
            from app.providers.translation import LocalTranslationProvider
            provider = get_translation_provider()
            translated_results = provider.translate_segments(texts_to_translate, source_lang, target_lang)

            is_unconfigured = isinstance(provider, (NullTranslationProvider, LocalTranslationProvider)) or all(not (t and t.strip()) for t in translated_results)

            segments: list[TranslationSegment] = []
            if is_structured_docx and doc_blocks:
                trans_iter = iter(translated_results)
                for idx, block in enumerate(doc_blocks, start=1):
                    if block.text.strip():
                        trans = next(trans_iter, "")
                    else:
                        trans = ""
                    is_seg_blank = not (trans and trans.strip())
                    flag = "no_model" if (is_unconfigured or is_seg_blank) else "unreviewed"
                    segments.append(TranslationSegment(
                        id=f"seg-{idx}",
                        source=block.text,
                        translated=trans if not is_unconfigured else "",
                        reviewFlag=flag,
                        confidence=0.0 if (is_unconfigured or is_seg_blank) else 0.92,
                        blockType=block.block_type,
                        blockLevel=block.block_level,
                        styleName=block.style_name,
                        tableIndex=block.table_index,
                        rowIndex=block.row_index,
                        cellIndex=block.cell_index,
                        numRows=block.num_rows,
                        numCols=block.num_cols,
                        blockOrder=block.block_order,
                    ))
            else:
                for idx, (src, trans) in enumerate(zip(raw_segments, translated_results), start=1):
                    is_seg_blank = not (trans and trans.strip())
                    flag = "no_model" if (is_unconfigured or is_seg_blank) else "unreviewed"
                    segments.append(TranslationSegment(
                        id=f"seg-{idx}",
                        source=src,
                        translated=trans if not is_unconfigured else "",
                        reviewFlag=flag,
                        confidence=0.0 if (is_unconfigured or is_seg_blank) else 0.92,
                        blockType="paragraph",
                        blockLevel=0,
                        blockOrder=idx,
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
                "No translation model is configured. Translated segments are blank; configure a translation provider (IndicTrans2) or enter translations manually."
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
                providerUsed=provider.__class__.__name__,
                sourceFileName=source_file_name,
                sourceFileExt=source_file_ext,
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
                error=err_msg,
                sourceFileName=source_file_name,
                sourceFileExt=source_file_ext,
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

            keys = row.keys()
            return TranslationJobResponse(
                id=row["id"],
                status=row["status"],
                sourceLanguage=row["source_lang"],
                targetLanguage=row["target_lang"],
                segments=segments,
                limitations=limitations,
                error=row["error"],
                sourceFileName=row["source_file_name"] if "source_file_name" in keys else None,
                sourceFileExt=row["source_file_ext"] if "source_file_ext" in keys else None,
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
