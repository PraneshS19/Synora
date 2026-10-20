from abc import ABC, abstractmethod
import re
from app.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_instruction: str = "") -> str:
        pass

class LocalExtractiveLLMProvider(LLMProvider):
    """
    Built-in local grounded extractive synthesizer.
    Produces answers strictly by locating direct evidence in the retrieved passages.
    Never hallucinates or fabricates citations.
    """
    def generate(self, prompt: str, system_instruction: str = "") -> str:
        # Check if the prompt has context passages
        # The prompt is formatted with "Context:\n...\nQuestion: <question>"
        context_match = re.search(r"Context:\s*(.*?)\s*Question:\s*(.*)", prompt, re.DOTALL | re.IGNORECASE)
        if not context_match:
            return "Based on the available evidence, no direct statement was found to answer this inquiry."

        context = context_match.group(1).strip()
        question = context_match.group(2).strip()

        # Extract words from question (excluding stopwords)
        stopwords = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "is", "are", "was", "were", "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "does", "do", "did", "can", "could", "should", "would", "about", "any"}
        q_words = [w.lower() for w in re.findall(r"\w+", question) if w.lower() not in stopwords]

        # Break context into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if len(s.strip()) > 15]

        # Score sentences by question word overlap
        scored: list[tuple[float, str]] = []
        for sentence in sentences:
            s_words = set(w.lower() for w in re.findall(r"\w+", sentence))
            overlap = sum(1 for qw in q_words if qw in s_words)
            if overlap > 0:
                score = overlap / (len(q_words) + 1e-5)
                scored.append((score, sentence))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored or scored[0][0] < 0.2:
            return "No sufficient evidence was found in the private collection to answer this question."

        # Return the top matching sentences as grounded answer
        top_sentences = [s for _, s in scored[:3]]
        return " ".join(top_sentences)

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.1}
        )

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        response = self.model.generate_content(full_prompt)
        return response.text.strip() if response.text else ""

class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model_name: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        import httpx
        self.client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60.0)
        self.model_name = model_name

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        res = self.client.post("/chat/completions", json={
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1
        })
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()

def get_llm_provider() -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "local":
        return LocalExtractiveLLMProvider()
    elif provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "Gemini LLM provider requested, but GEMINI_API_KEY is not configured in .env."
            )
        return GeminiLLMProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    elif provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OpenAI LLM provider requested, but OPENAI_API_KEY is not configured in .env."
            )
        return OpenAILLMProvider(settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider_name}'. Supported: 'local', 'gemini', 'openai'.")
