from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.storage import storage_service
from app.services.rag_service import rag_service
from app.services.translation_service import translation_service
from app.services.meeting_service import meeting_service
from app.models.schemas import (
    HealthResponse,
    UploadResponse,
    CreateCollectionRequest,
    CollectionResponse,
    QuestionRequest,
    QuestionResponse,
    CreateTranslationJobRequest,
    TranslationJobResponse,
    UpdateSegmentRequest,
    CreateMeetingJobRequest,
    MeetingJobResponse,
    UpdateMeetingDraftRequest,
    TranscribeAudioRequest,
    TranscribeAudioResponse,
)

app = FastAPI(
    title="SYNORA Institutional Intelligence API",
    version="1.0.0",
    description="Backend services for Institutional RAG, IndicTranslate, and Meeting Minutes."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Health Check Endpoint
# ==========================================

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        modules=["rag", "translate", "meeting"],
        providers={
            "embeddings": settings.EMBEDDING_PROVIDER,
            "llm": settings.LLM_PROVIDER,
            "translation": settings.TRANSLATION_PROVIDER,
            "audio": settings.AUDIO_PROVIDER
        }
    )

# ==========================================
# Shared File Upload Endpoint
# ==========================================

@app.post("/api/uploads", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    module: str = Form(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    uploaded_records = []
    for file in files:
        rec = await storage_service.save_upload(file, module)
        uploaded_records.append(rec)

    return UploadResponse(files=uploaded_records)

# ==========================================
# Tool 2: Institutional RAG Endpoints
# ==========================================

@app.post("/api/rag/collections", response_model=CollectionResponse)
def create_rag_collection(req: CreateCollectionRequest):
    return rag_service.create_collection(name=req.name, file_ids=req.fileIds)

@app.get("/api/rag/collections/{collection_id}", response_model=CollectionResponse)
def get_rag_collection(collection_id: str):
    col = rag_service.get_collection(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")
    return col

@app.post("/api/rag/collections/{collection_id}/questions", response_model=QuestionResponse)
def ask_rag_question(collection_id: str, req: QuestionRequest):
    return rag_service.answer_question(collection_id=collection_id, question=req.question)

# ==========================================
# Tool 4: IndicTranslate Endpoints
# ==========================================

@app.post("/api/translate/jobs", response_model=TranslationJobResponse)
def create_translation_job(req: CreateTranslationJobRequest):
    return translation_service.create_job(
        file_ids=req.fileIds,
        source_text=req.sourceText,
        source_lang=req.sourceLanguage,
        target_lang=req.targetLanguage
    )

@app.get("/api/translate/jobs/{job_id}", response_model=TranslationJobResponse)
def get_translation_job(job_id: str):
    job = translation_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found.")
    return job

@app.put("/api/translate/jobs/{job_id}/segments/{segment_id}", response_model=TranslationJobResponse)
def update_translation_segment(job_id: str, segment_id: str, req: UpdateSegmentRequest):
    return translation_service.update_segment(
        job_id=job_id,
        segment_id=segment_id,
        new_translated=req.translated,
        review_flag=req.reviewFlag
    )

@app.get("/api/translate/jobs/{job_id}/download")
def download_translation(job_id: str, format: str = "auto"):
    """
    Download the translated document as a file.
    format: "txt", "docx", or "auto" (uses source file ext if known, defaults to txt)
    """
    from app.services.document_builder import build_translated_document
    job = translation_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Translation job not found.")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Translation job is not completed (status: {job.status}).")
    if not job.segments:
        raise HTTPException(status_code=400, detail="Translation job has no segments to download.")

    if format == "auto":
        src_ext = getattr(job, "sourceFileExt", None)
        out_format = "docx" if src_ext in (".docx", ".pdf") else "txt"
    else:
        out_format = format.lower().lstrip(".")

    base_name = getattr(job, "sourceFileName", None) or "translation"
    base_stem = base_name.rsplit(".", 1)[0] if "." in base_name else base_name
    lang_code = job.targetLanguage[:3].lower() if job.targetLanguage else "xx"
    out_name = f"{base_stem}-{lang_code}.{out_format}"

    file_bytes, content_type = build_translated_document(
        job.segments, out_format, job.sourceLanguage, job.targetLanguage
    )
    return FastAPIResponse(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

# ==========================================
# Tool 5: Meeting Minutes Endpoints
# ==========================================

@app.post("/api/meetings/transcribe", response_model=TranscribeAudioResponse)
def transcribe_audio(req: TranscribeAudioRequest):
    return meeting_service.transcribe_audio(audio_file_id=req.audioFileId)

@app.post("/api/meetings/jobs", response_model=MeetingJobResponse)
def create_meeting_job(req: CreateMeetingJobRequest):
    return meeting_service.create_job(
        transcript_file_ids=req.transcriptFileIds,
        audio_file_ids=req.audioFileIds,
        meeting_title=req.meetingTitle,
        raw_transcript_text=req.rawTranscriptText,
    )

@app.get("/api/meetings/jobs", response_model=list[MeetingJobResponse])
def list_meeting_jobs():
    """List saved meeting drafts with their latest metadata."""
    return meeting_service.list_jobs()

@app.get("/api/meetings/jobs/latest", response_model=MeetingJobResponse)
def get_latest_meeting_job():
    job = meeting_service.get_latest_job()
    if not job:
        raise HTTPException(status_code=404, detail="No meeting jobs found.")
    return job

@app.get("/api/meetings/jobs/{job_id}", response_model=MeetingJobResponse)
def get_meeting_job(job_id: str):
    job = meeting_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Meeting job not found.")
    return job

@app.get("/api/meetings/jobs/{job_id}/download")
def download_meeting_docx(job_id: str):
    """
    Download the meeting draft as a formatted DOCX document with latest saved edits.
    """
    docx_bytes, filename = meeting_service.build_docx(job_id)
    return FastAPIResponse(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

@app.put("/api/meetings/jobs/{job_id}/draft", response_model=MeetingJobResponse)
def update_meeting_draft(job_id: str, req: UpdateMeetingDraftRequest):
    return meeting_service.update_draft(job_id=job_id, new_draft=req.draft)
