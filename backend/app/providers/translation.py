from abc import ABC, abstractmethod
import re
from app.config import settings

# Institutional term vocabulary mapping for Indian languages (English -> Indic)
INSTITUTIONAL_GLOSSARY = {
    "tamil": {
        "policy": "கொள்கை",
        "guidelines": "வழிகாட்டுதல்கள்",
        "admission": "சேர்க்கை",
        "admissions": "மாணவர் சேர்க்கை",
        "academic": "கல்விசார்",
        "council": "மன்றம்",
        "information": "தகவல்",
        "document": "ஆவணம்",
        "notice": "அறிவிப்பு",
        "meeting": "கூட்டம்",
        "decision": "முடிவு",
        "minutes": "கூட்டக் குறிப்புகள்",
        "deadline": "கடைசி தேதி",
        "action item": "செயல் திட்டம்",
        "confidential": "ரகசியமானது",
        "student": "மாணவர்",
        "institution": "நிறுவனம்",
        "approved": "ஒப்புதல் அளிக்கப்பட்டது",
        "review": "மறுஆய்வு",
        "status": "நிலை",
        "report": "அறிக்கை",
        "calendar": "நாட்காட்டி",
        "process": "செயல்முறை",
        "circular": "சுற்றறிக்கை",
        "verification": "சரிபார்ப்பு",
    },
    "hindi": {
        "policy": "नीति",
        "guidelines": "दिशा-निर्देश",
        "admission": "प्रवेश",
        "admissions": "प्रवेश प्रक्रिया",
        "academic": "शैक्षणिक",
        "council": "परिषद",
        "information": "सूचना",
        "document": "दस्तावेज़",
        "notice": "सूचना",
        "meeting": "बैठक",
        "decision": "निर्णय",
        "minutes": "कार्यवृत्त",
        "deadline": "अंतिम तिथि",
        "action item": "कार्य बिंदु",
        "confidential": "गोपनीय",
        "student": "छात्र",
        "institution": "संस्थान",
        "approved": "स्वीकृत",
        "review": "समीक्षा",
        "status": "स्थिति",
        "report": "रिपोर्ट",
        "calendar": "कैलेंडर",
        "process": "प्रक्रिया",
        "circular": "परिपत्र",
        "verification": "सत्यापन",
    },
    "telugu": {
        "policy": "విధానం",
        "guidelines": "మార్గదర్శకాలు",
        "admission": "ప్రవేశం",
        "admissions": "ప్రవేశాలు",
        "academic": "విద్యా",
        "council": "మండలి",
        "information": "సమాచారం",
        "document": "పత్రం",
        "meeting": "సమావేశం",
        "decision": "నిర్ణయం",
        "minutes": "సమావేశ నివేదిక",
        "deadline": "గడువు తేదీ",
    },
    "kannada": {
        "policy": "ನೀತಿ",
        "guidelines": "ಮಾರ್ಗಸೂಚಿಗಳು",
        "admission": "ಪ್ರವೇಶ",
        "admissions": "ಪ್ರವೇಶಗಳು",
        "academic": "ಶೈಕ್ಷಣಿಕ",
        "council": "ಮಂಡಳಿ",
        "information": "ಮಾಹಿತಿ",
        "document": "ದಾಖಲೆ",
        "meeting": "ಸಭೆ",
        "decision": "ನಿರ್ಧಾರ",
        "minutes": "ಸಭಾ ನಡಾವಳಿ",
    },
    "malayalam": {
        "policy": "നയം",
        "guidelines": "മാർഗ്ഗനിർദ്ദേശങ്ങൾ",
        "admission": "പ്രവേശനം",
        "admissions": "പ്രവേശന നടപടികൾ",
        "academic": "അക്കാദമിക്",
        "council": "കൗൺസിൽ",
        "information": "വിവരം",
        "document": "രേഖ",
        "meeting": "യോഗം",
        "decision": "തീരുമാനം",
        "minutes": "യോഗക്കുറിപ്പുകൾ",
    },
    "bengali": {
        "policy": "নীতি",
        "guidelines": "নির্দেশিকাবলী",
        "admission": "ভর্তি",
        "admissions": "ভর্তি প্রক্রিয়া",
        "academic": "শিক্ষাগত",
        "council": "পরিষদ",
        "information": "তথ্য",
        "document": "নথি",
        "meeting": "বৈঠক",
        "decision": "সিদ্ধান্ত",
        "minutes": "কার্যবিবরণী",
    },
    "marathi": {
        "policy": "धोरण",
        "guidelines": "मार्गदर्शक तत्त्वे",
        "admission": "प्रवेश",
        "admissions": "प्रवेश प्रक्रिया",
        "academic": "शैक्षणिक",
        "council": "परिषद",
        "information": "माहिती",
        "document": "दस्तऐवज",
        "meeting": "बैठक",
        "decision": "निर्णय",
        "minutes": "इतिवृत्त",
    }
}

class TranslationProvider(ABC):
    @abstractmethod
    def translate_segments(self, segments: list[str], source_lang: str, target_lang: str) -> list[str]:
        pass

class LocalTranslationProvider(TranslationProvider):
    """
    Local translation provider when no neural MT model (IndicTrans2 or Gemini) is active.
    Returns blank drafts for segments so the user can manually enter translations.
    Never produces glossary substitutions, unchanged English, or mixed-language text.
    """
    def translate_segments(self, segments: list[str], source_lang: str, target_lang: str) -> list[str]:
        # Return blank segments so human reviewers can enter or edit translations manually
        # without presenting glossary substitutions as machine translations.
        return ["" for _ in segments]

class GeminiTranslationProvider(TranslationProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def translate_segments(self, segments: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not segments:
            return []

        prompt = (
            f"You are an institutional document translation engine.\n"
            f"Translate each numbered segment from {source_lang} to {target_lang}.\n"
            f"Keep formal institutional terminology intact. Do not add conversational remarks.\n"
            f"Output each translated segment on a separate line prefixed with 'SEGMENT_N: '.\n\n"
        )
        for idx, seg in enumerate(segments, start=1):
            prompt += f"SEGMENT_{idx}: {seg}\n"

        response = self.model.generate_content(prompt)
        text = response.text or ""

        results: list[str] = []
        seg_pattern = re.compile(r"SEGMENT_\d+:\s*(.*)")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            m = seg_pattern.match(line)
            if m:
                results.append(m.group(1).strip())

        if len(results) != len(segments):
            raise RuntimeError(
                f"Gemini translation returned {len(results)} segments, expected {len(segments)}. "
                f"Source text is preserved. Please try again or switch to manual editing."
            )

        return results

class IndicTrans2Provider(TranslationProvider):
    """
    AI4Bharat IndicTrans2 Neural Machine Translation integration.
    Default checkpoint: ai4bharat/indictrans2-en-indic-dist-200M (~1.1 GB local cache).
    The model checkpoint is MIT-licensed by AI4Bharat. Verify any mirrored weights
    against the official upstream checkpoint before redistribution or deployment.
    This configured checkpoint supports English-to-Indic translation.

    Dependencies (pip):
        transformers, torch, sentencepiece, accelerate
        IndicTransToolkit  (pip install git+https://github.com/VarunGumma/IndicTransToolkit.git)

    The constructor does NOT auto-download weights.
    Pre-download with:
        hf download ai4bharat/indictrans2-en-indic-dist-200M
    """

    # ── BCP-47 language-code map used by IndicTrans2 ──────────────────
    _LANG_MAP: dict[str, str] = {
        "english": "eng_Latn",
        "hindi": "hin_Deva",
        "tamil": "tam_Taml",
        "telugu": "tel_Telu",
        "kannada": "kan_Knda",
        "malayalam": "mal_Mlym",
        "bengali": "ben_Beng",
        "marathi": "mar_Deva",
        "gujarati": "guj_Gujr",
        "punjabi": "pan_Guru",
        "odia": "ori_Orya",
        "assamese": "asm_Beng",
        "urdu": "urd_Arab",
        "nepali": "nep_Deva",
        "sinhala": "sin_Sinh",
    }

    def __init__(self) -> None:
        self.model_name: str = settings.INDICTRANS2_EN_INDIC_MODEL

        # ── Step 1: check Python dependencies ─────────────────────────
        missing: list[str] = []
        for pkg in ("transformers", "torch", "sentencepiece"):
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        try:
            __import__("IndicTransToolkit")
        except ImportError:
            try:
                __import__("indictranstoolkit")
            except ImportError:
                missing.append(
                    "IndicTransToolkit "
                    "(pip install git+https://github.com/VarunGumma/IndicTransToolkit.git)"
                )

        if missing:
            raise RuntimeError(
                f"IndicTrans2 Python dependencies are missing: {', '.join(missing)}. "
                f"Install them before selecting TRANSLATION_PROVIDER=indictrans2."
            )

        # ── Step 2: probe HuggingFace cache for local weights ────────
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        model_candidates = [self.model_name]
        if "indictrans2-en-indic-dist-200M" in self.model_name:
            for fallback in ("naklitechie/indictrans2-en-indic-dist-200M", "ai4bharat/indictrans2-en-indic-dist-200M"):
                if fallback not in model_candidates:
                    model_candidates.append(fallback)

        last_err = None
        loaded = False
        for candidate in model_candidates:
            try:
                # local_files_only=True ensures nothing is downloaded
                self._tokenizer = AutoTokenizer.from_pretrained(
                    candidate,
                    trust_remote_code=True,
                    local_files_only=True,
                )
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    candidate,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    low_cpu_mem_usage=True,
                    local_files_only=True,
                )
                self.model_name = candidate
                loaded = True
                break
            except (OSError, ValueError, EnvironmentError) as exc:
                last_err = exc

        if not loaded:
            raise RuntimeError(
                f"IndicTrans2 model weights for '{self.model_name}' are not present in "
                f"the local HuggingFace cache (~1.1 GB). Download them first:\n"
                f"  hf download {self.model_name}\n"
                f"Or choose a different provider: TRANSLATION_PROVIDER=gemini|local\n"
                f"(Underlying error: {last_err})"
            )

        # ── Step 3: move to device and set eval mode ─────────────────
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = self._model.to(self._device)
        self._model.eval()

        # ── Step 4: initialise IndicProcessor ────────────────────────
        try:
            from IndicTransToolkit.processor import IndicProcessor
        except ImportError:
            from indictranstoolkit.processor import IndicProcessor
        self._ip = IndicProcessor(inference=True)

    # ------------------------------------------------------------------ #

    @classmethod
    def _resolve_lang_code(cls, lang_name: str) -> str:
        """Map a human-readable language name to the BCP-47 code
        expected by IndicTrans2.  Raises ValueError for unsupported
        languages."""
        key = lang_name.strip().lower()
        code = cls._LANG_MAP.get(key)
        if code is None:
            supported = ", ".join(sorted(cls._LANG_MAP.keys()))
            raise ValueError(
                f"Language '{lang_name}' is not supported by IndicTrans2. "
                f"Supported: {supported}"
            )
        return code

    def translate_segments(
        self,
        segments: list[str],
        source_lang: str,
        target_lang: str,
    ) -> list[str]:
        if not segments:
            return []

        import torch

        src_code = self._resolve_lang_code(source_lang)
        tgt_code = self._resolve_lang_code(target_lang)

        # Pre-process through IndicProcessor
        batch = self._ip.preprocess_batch(
            list(segments), src_lang=src_code, tgt_lang=tgt_code
        )

        inputs = self._tokenizer(
            batch,
            padding="longest",
            truncation=True,
            max_length=256,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            generated = self._model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )

        with self._tokenizer.as_target_tokenizer():
            decoded = self._tokenizer.batch_decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

        # Post-process (de-tokenize, script-specific fixes)
        translations = self._ip.postprocess_batch(decoded, lang=tgt_code)

        if len(translations) != len(segments):
            # Safety fallback — should not happen with correct pre-processing
            return LocalTranslationProvider().translate_segments(
                segments, source_lang, target_lang
            )

        return translations

class NullTranslationProvider(TranslationProvider):
    """
    Provider when no translation model is configured (TRANSLATION_PROVIDER=none).
    Returns blank translations for segments, explicitly signaling that no model is active.
    """
    def translate_segments(self, segments: list[str], source_lang: str, target_lang: str) -> list[str]:
        return ["" for _ in segments]

def get_translation_provider() -> TranslationProvider:
    provider_name = settings.TRANSLATION_PROVIDER.lower()
    if provider_name in ("none", "null", "unconfigured", ""):
        return NullTranslationProvider()
    elif provider_name == "local":
        return LocalTranslationProvider()
    elif provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "Gemini translation provider requested, but GEMINI_API_KEY is not configured in .env."
            )
        return GeminiTranslationProvider(settings.GEMINI_API_KEY)
    elif provider_name == "indictrans2":
        return IndicTrans2Provider()
    else:
        raise ValueError(f"Unknown TRANSLATION_PROVIDER: '{provider_name}'. Supported: 'local', 'gemini', 'indictrans2', 'none'.")
