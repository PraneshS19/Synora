import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
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
    def __init__(self, model_size: Optional[str] = None, device: Optional[str] = None):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self.device = device or getattr(settings, "WHISPER_DEVICE", "auto")
        self._model = None

    def _resolve_device(self) -> str:
        dev = (self.device or "auto").lower().strip()
        if dev == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                return "cpu"
        elif dev in ("cuda", "cpu"):
            return dev
        return "cpu"

    def _ensure_model(self):
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "Whisper speech-to-text requires 'ffmpeg' installed on system PATH to decode audio files. "
                "Please install ffmpeg (e.g., 'winget install Gyan.FFmpeg' on Windows, 'brew install ffmpeg' on macOS, "
                "or 'sudo apt install ffmpeg' on Linux) and add it to your PATH, or upload a text transcript."
            )
        try:
            import whisper
        except ImportError:
            raise RuntimeError(
                "Whisper speech-to-text requires the 'openai-whisper' package. "
                "Install it via 'pip install openai-whisper' or upload a text transcript."
            )

        if self._model is None:
            resolved_device = self._resolve_device()
            try:
                self._model = whisper.load_model(self.model_size, device=resolved_device)
            except Exception as e:
                err_str = str(e)
                if "OutOfMemoryError" in type(e).__name__ or "CUDA out of memory" in err_str:
                    raise RuntimeError(
                        f"Insufficient GPU memory to load Whisper model '{self.model_size}'. "
                        "Try setting WHISPER_MODEL_SIZE=tiny or WHISPER_DEVICE=cpu."
                    )
                raise RuntimeError(
                    f"Failed to load Whisper model '{self.model_size}': {err_str}. "
                    "Ensure model weights are accessible or configure a supported model size."
                )

    def transcribe(self, audio_path: Path) -> list[DocumentPassage]:
        self._ensure_model()

        try:
            result = self._model.transcribe(str(audio_path))
        except Exception as e:
            err_name = type(e).__name__
            err_str = str(e)
            # Sanitize local paths from error messages
            sanitized = err_str.replace(str(audio_path), audio_path.name)
            if "OutOfMemoryError" in err_name or "out of memory" in err_str.lower():
                raise RuntimeError(
                    "Transcription failed due to insufficient GPU/system memory during audio processing."
                )
            raise RuntimeError(f"Whisper audio transcription failed: {sanitized}")

        segments = result.get("segments", [])

        # Duration limit check
        if segments:
            total_duration_sec = max((float(s.get("end", 0.0)) for s in segments), default=0.0)
            max_duration_sec = getattr(settings, "MAX_AUDIO_MINUTES", 180) * 60
            if total_duration_sec > max_duration_sec:
                raise RuntimeError(
                    f"Audio duration ({total_duration_sec / 60:.1f} minutes) exceeds the maximum limit "
                    f"of {getattr(settings, 'MAX_AUDIO_MINUTES', 180)} minutes."
                )

        # Empty / inaudible recording check
        raw_text = result.get("text", "").strip()
        if not raw_text or not any(c.isalnum() for c in raw_text):
            raise RuntimeError(
                "The audio file contains no audible speech or usable content. Please provide a clear recording."
            )

        passages: list[DocumentPassage] = []
        for segment in segments:
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", 0.0))
            s_min, s_sec = divmod(int(start), 60)
            e_min, e_sec = divmod(int(end), 60)
            time_str = f"{s_min:02d}:{s_sec:02d}"
            time_range = f"{s_min:02d}:{s_sec:02d} - {e_min:02d}:{e_sec:02d}"
            text = segment.get("text", "").strip()
            if text:
                passages.append(DocumentPassage(
                    text=text,
                    timestamp=time_range,
                    section=f"Time {time_str}"
                ))

        if not passages and raw_text:
            passages.append(DocumentPassage(
                text=raw_text,
                timestamp="00:00 - 00:00",
                section="Audio Transcript"
            ))

        return passages

def get_audio_provider() -> AudioTranscriptionProvider:
    provider_name = settings.AUDIO_PROVIDER.lower()
    if provider_name == "whisper":
        return WhisperAudioProvider(settings.WHISPER_MODEL_SIZE, getattr(settings, "WHISPER_DEVICE", "auto"))
    elif provider_name == "none":
        return NullAudioProvider()
    else:
        raise ValueError(f"Unknown AUDIO_PROVIDER: '{provider_name}'. Supported: 'whisper', 'none'.")
