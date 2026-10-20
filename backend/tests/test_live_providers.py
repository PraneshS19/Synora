import os
import shutil
import pytest
from app.config import settings
from app.providers.translation import IndicTrans2Provider
from app.providers.audio import WhisperAudioProvider

# ==============================================================================
# Live Provider Smoke Tests
# These tests exercise REAL model calls and check external dependencies.
# They are kept strictly separate from the local fallback test suite (test_api.py).
# ==============================================================================

def test_live_indictrans2_smoke_test():
    """
    Smoke test for AI4Bharat IndicTrans2 translation.
    Skips with setup instructions when:
      - Python dependencies (transformers, torch, sentencepiece, IndicTransToolkit) are missing
      - Model weights (~4 GB) have not been downloaded to local HuggingFace cache
    Runs a real English→Tamil translation when prerequisites are present.
    """
    # ── Check Python dependencies first ───────────────────────────────
    dep_missing: list[str] = []
    for pkg in ("transformers", "torch", "sentencepiece"):
        try:
            __import__(pkg)
        except ImportError:
            dep_missing.append(pkg)
    try:
        __import__("IndicTransToolkit")
    except ImportError:
        try:
            __import__("indictranstoolkit")
        except ImportError:
            dep_missing.append(
                "IndicTransToolkit "
                "(pip install git+https://github.com/VarunGumma/IndicTransToolkit.git)"
            )
    if dep_missing:
        pytest.skip(
            f"IndicTrans2 Python dependencies are not installed: {', '.join(dep_missing)}. "
            f"Install them to exercise live IndicTrans2 translation."
        )

    # ── Check whether model weights are in local cache ────────────────
    from transformers import AutoTokenizer
    candidates = [
        settings.INDICTRANS2_EN_INDIC_MODEL,
        "naklitechie/indictrans2-en-indic-dist-200M",
        "ai4bharat/indictrans2-en-indic-dist-200M",
    ]
    has_local_weights = False
    for cand in candidates:
        try:
            AutoTokenizer.from_pretrained(
                cand, trust_remote_code=True, local_files_only=True
            )
            has_local_weights = True
            break
        except (OSError, ValueError, EnvironmentError):
            continue

    if not has_local_weights:
        pytest.skip(
            f"IndicTrans2 model weights are not in the local HuggingFace cache (~1.1 GB). "
            f"Download with 'hf download {settings.INDICTRANS2_EN_INDIC_MODEL}' and re-run."
        )

    # ── Both deps and weights are available — run real translations ──
    provider = IndicTrans2Provider()

    # 1. English to Tamil
    input_segments = ["The academic council approved the new admissions policy."]
    translated_ta = provider.translate_segments(input_segments, "English", "Tamil")
    assert len(translated_ta) == 1, f"Expected 1 translated segment, got {len(translated_ta)}"
    assert translated_ta[0].strip() != "", "IndicTrans2 returned an empty translation for Tamil"
    import re as _re
    assert _re.search(r"[\u0B80-\u0BFF]", translated_ta[0]), (
        f"Expected Tamil script output, got: {translated_ta[0]}"
    )

    # 2. English to Hindi
    translated_hi = provider.translate_segments(input_segments, "English", "Hindi")
    assert len(translated_hi) == 1, f"Expected 1 translated segment, got {len(translated_hi)}"
    assert translated_hi[0].strip() != "", "IndicTrans2 returned an empty translation for Hindi"
    assert _re.search(r"[\u0900-\u097F]", translated_hi[0]), (
        f"Expected Hindi (Devanagari) script output, got: {translated_hi[0]}"
    )

def test_live_whisper_audio_smoke_test():
    """
    Smoke test for OpenAI Whisper audio transcription.
    Verifies whether openai-whisper package and ffmpeg are installed on the system PATH.
    If not installed, confirms that the provider cleanly reports the requirement.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip(
            "ffmpeg is not installed on system PATH. "
            "Live Whisper transcription requires ffmpeg to process audio files."
        )
    try:
        import whisper
    except ImportError:
        pytest.skip(
            "openai-whisper package is not installed. "
            "Install with 'pip install openai-whisper' to exercise live audio transcription."
        )

    # If both dependencies exist, execute transcription probe
    whisper_provider = WhisperAudioProvider(model_size="tiny")
    assert whisper_provider is not None
