import os
import uuid
import sqlite3
import datetime
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.models.schemas import UploadedFileResponse

# Supported extensions by category
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}
TRANSCRIPT_EXTENSIONS = {".txt", ".docx", ".pdf", ".vtt", ".srt"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

ALLOWED_EXTENSIONS_BY_MODULE = {
    "rag": DOCUMENT_EXTENSIONS,
    "translate": DOCUMENT_EXTENSIONS,
    "meeting": TRANSCRIPT_EXTENSIONS.union(AUDIO_EXTENSIONS),
    "change": DOCUMENT_EXTENSIONS,
    "shield": DOCUMENT_EXTENSIONS,
}

class StorageService:
    def __init__(self):
        self.db_path = settings.DATABASE_PATH
        self.upload_dir = settings.UPLOAD_DIR
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id TEXT PRIMARY KEY,
                    original_name TEXT NOT NULL,
                    internal_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    module TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    embedding_provider TEXT,
                    embedding_dim INTEGER,
                    embedding_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Safely migrate existing databases if columns are missing
            for col_name, col_type in [
                ("embedding_provider", "TEXT"),
                ("embedding_dim", "INTEGER"),
                ("embedding_model", "TEXT"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE rag_collections ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_collection_files (
                    collection_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    PRIMARY KEY (collection_id, file_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER,
                    section_title TEXT,
                    text TEXT NOT NULL,
                    embedding_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translation_jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    segments_json TEXT,
                    error TEXT,
                    source_file_name TEXT,
                    source_file_ext TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Safely migrate existing databases (add columns if missing)
            for col_name, col_type in [
                ("source_file_name", "TEXT"),
                ("source_file_ext", "TEXT"),
            ]:
                try:
                    cursor.execute(
                        f"ALTER TABLE translation_jobs ADD COLUMN {col_name} {col_type}"
                    )
                except sqlite3.OperationalError:
                    pass
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meeting_jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    draft_json TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Safely migrate meeting_jobs columns if missing
            for col_name, col_type in [
                ("transcript", "TEXT"),
                ("audio_file_name", "TEXT"),
                ("updated_at", "TIMESTAMP"),
            ]:
                try:
                    cursor.execute(
                        f"ALTER TABLE meeting_jobs ADD COLUMN {col_name} {col_type}"
                    )
                except sqlite3.OperationalError:
                    pass
            conn.commit()

    def validate_file_content(self, filename: str, ext: str, content: bytes, module: str):
        # 0. Empty file check
        if not content or len(content.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' is empty. Please upload a file containing usable content."
            )

        # 1. Size check
        size_mb = len(content) / (1024 * 1024)
        max_size = settings.MAX_AUDIO_SIZE_MB if ext in AUDIO_EXTENSIONS else settings.MAX_DOC_SIZE_MB
        if size_mb > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' ({size_mb:.1f} MB) exceeds maximum allowed size of {max_size} MB."
            )

        # 2. Magic byte / header check
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not a valid PDF document.")
        elif ext == ".docx":
            if not content.startswith(b"PK\x03\x04"):
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not a valid DOCX document.")
        elif ext == ".wav":
            if not (content.startswith(b"RIFF") and b"WAVE" in content[:16]):
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not a valid WAV audio file.")
            if len(content) < 44:
                raise HTTPException(status_code=400, detail=f"Audio file '{filename}' contains incomplete WAV header data.")
        elif ext == ".m4a":
            if len(content) < 8 or b"ftyp" not in content[:16]:
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not a valid M4A audio file.")
        elif ext == ".mp3":
            # MP3 begins with ID3 or sync frame (0xFF 0xFB/0xF3/0xF2)
            has_id3 = content.startswith(b"ID3")
            has_sync = len(content) > 2 and content[0] == 0xFF and (content[1] & 0xE0 == 0xE0)
            if not (has_id3 or has_sync):
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not a valid MP3 audio file.")
        elif ext in {".txt", ".vtt", ".srt"}:
            try:
                # Test text decodability
                decoded = content.decode("utf-8")
                if not decoded.strip():
                    raise HTTPException(status_code=400, detail=f"File '{filename}' contains only whitespace.")
            except UnicodeDecodeError:
                try:
                    decoded = content.decode("latin-1")
                    if not decoded.strip():
                        raise HTTPException(status_code=400, detail=f"File '{filename}' contains only whitespace.")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=400, detail=f"File '{filename}' contains unreadable binary data.")

        # Audio stream decodability check if ffmpeg is available
        if ext in AUDIO_EXTENSIONS and shutil.which("ffmpeg"):
            try:
                proc = subprocess.run(
                    ["ffmpeg", "-v", "error", "-i", "pipe:0", "-t", "0.5", "-f", "null", "-"],
                    input=content,
                    capture_output=True,
                    timeout=5
                )
                if proc.returncode != 0:
                    err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Audio file '{filename}' is corrupt or cannot be decoded: {err_msg[:200] if err_msg else 'Invalid audio stream.'}"
                    )
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=400, detail=f"Audio file '{filename}' took too long to validate.")
            except HTTPException:
                raise
            except Exception:
                pass
            except UnicodeDecodeError:
                try:
                    decoded = content.decode("latin-1")
                    if not decoded.strip():
                        raise HTTPException(status_code=400, detail=f"File '{filename}' contains only whitespace.")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=400, detail=f"File '{filename}' contains unreadable binary data.")

    async def save_upload(self, upload_file: UploadFile, module: str) -> UploadedFileResponse:
        filename = upload_file.filename or "unnamed"
        # Sanitize filename
        safe_original_name = Path(filename).name
        ext = Path(safe_original_name).suffix.lower()

        allowed_exts = ALLOWED_EXTENSIONS_BY_MODULE.get(module.lower())
        if not allowed_exts:
            raise HTTPException(status_code=400, detail=f"Invalid or unsupported module: '{module}'.")

        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not supported for module '{module}'. Allowed: {', '.join(sorted(allowed_exts))}"
            )

        content = await upload_file.read()
        self.validate_file_content(safe_original_name, ext, content, module)

        file_id = str(uuid.uuid4())
        internal_filename = f"{file_id}{ext}"
        destination = self.upload_dir / internal_filename

        with open(destination, "wb") as f:
            f.write(content)

        mime_type = upload_file.content_type or "application/octet-stream"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO uploaded_files (id, original_name, internal_name, mime_type, size, module)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_id, safe_original_name, internal_filename, mime_type, len(content), module)
            )
            conn.commit()

        return UploadedFileResponse(
            id=file_id,
            name=safe_original_name,
            mimeType=mime_type,
            size=len(content),
            status="ready",
            module=module
        )

    def get_file_record(self, file_id: str) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_file_path(self, file_id: str) -> Optional[Path]:
        record = self.get_file_record(file_id)
        if not record:
            return None
        return self.upload_dir / record["internal_name"]

storage_service = StorageService()
