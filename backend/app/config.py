import os
from pathlib import Path
from dotenv import load_dotenv

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BACKEND_DIR / ".env")

class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]

    # Storage paths
    UPLOAD_DIR: Path = BACKEND_DIR / os.getenv("UPLOAD_DIR", "data/uploads")
    DATABASE_PATH: Path = BACKEND_DIR / os.getenv("DATABASE_PATH", "data/synora.db")
    MAX_DOC_SIZE_MB: int = int(os.getenv("MAX_DOC_SIZE_MB", "20"))
    MAX_AUDIO_SIZE_MB: int = int(os.getenv("MAX_AUDIO_SIZE_MB", "200"))

    # Provider selections
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local").lower()
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local").lower()
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "local").lower()
    AUDIO_PROVIDER: str = os.getenv("AUDIO_PROVIDER", "none").lower()

    # External Provider Keys & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    INDICTRANS2_EN_INDIC_MODEL: str = os.getenv("INDICTRANS2_EN_INDIC_MODEL", "ai4bharat/indictrans2-en-indic-dist-200M")
    INDICTRANS2_INDIC_EN_MODEL: str = os.getenv("INDICTRANS2_INDIC_EN_MODEL", "ai4bharat/indictrans2-indic-en-dist-200M")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
