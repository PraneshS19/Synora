import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from app.config import settings
from app.services.extractor import DocumentPassage

class AudioTranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> list[DocumentPassage]:
        pass

class NullAudioProvider(AudioTranscriptionProvider):
    def transcribe(self, audio_path: Path) -> list[DocumentPassage]:
        raise RuntimeError(
            "Audio speech-to-text is not configured (AUDIO_PROVIDER=none). "
            "Please upload a transcript document (.txt, .docx, .pdf, .vtt, .srt) "
            "or configure AUDIO_PROVIDER=whisper with openai-whisper and ffmpeg."
        )

class WhisperAudioProvider(AudioTranscriptionProvider):
    """
    OpenAI Whisper speech-to-text integration.
    License: MIT.
    Supports .mp3, .wav, .m4a.
    Requires: 'pip install openai-whisper' and ffmpeg on system PATH.
    """
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "Whisper speech-to-text requires 'ffmpeg' installed on system PATH to process audio files. "
                "Please install ffmpeg or use transcript uploads."
            )
        try:
            import whisper
            self.whisper = whisper
        except ImportError:
            raise RuntimeError(
                "Whisper speech-to-text requires the 'openai-whisper' package. "
                "Install it via 'pip install openai-whisper' or upload a text transcript."
            )

    def transcribe(self, audio_path: Path) -> list[DocumentPassage]:
        model = self.whisper.load_model(self.model_size)
        result = model.transcribe(str(audio_path))

        passages: list[DocumentPassage] = []
        for segment in result.get("segments", []):
            start = int(segment.get("start", 0))
            minutes = start // 60
            seconds = start % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            text = segment.get("text", "").strip()
            if text:
                passages.append(DocumentPassage(
                    text=text,
                    timestamp=time_str,
                    section=f"Time {time_str}"
                ))

        if not passages and result.get("text"):
            passages.append(DocumentPassage(text=result["text"].strip(), section="Audio Transcript"))

        return passages

def get_audio_provider() -> AudioTranscriptionProvider:
    provider_name = settings.AUDIO_PROVIDER.lower()
    if provider_name == "whisper":
        return WhisperAudioProvider(settings.WHISPER_MODEL_SIZE)
    elif provider_name == "none":
        return NullAudioProvider()
    else:
        raise ValueError(f"Unknown AUDIO_PROVIDER: '{provider_name}'. Supported: 'whisper', 'none'.")
