from abc import ABC, abstractmethod
import numpy as np
from app.config import settings

class EmbeddingProvider(ABC):
    provider_name: str = "base"
    model_name: str = "base"
    dimension: int = 0

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass

class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local TF-IDF & character n-gram embedding engine using scikit-learn.
    Operates 100% offline without external network or heavy weights.
    Suitable for local development and multilingual string matching.
    """
    def __init__(self, n_features: int = 256):
        from sklearn.feature_extraction.text import HashingVectorizer
        self.provider_name = "local"
        self.dimension = n_features
        self.model_name = f"local-hashing-{n_features}"
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            ngram_range=(1, 3),
            analyzer="char_wb"
        )

    def embed_query(self, text: str) -> list[float]:
        matrix = self.vectorizer.transform([text])
        vec = matrix.toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self.vectorizer.transform(texts)
        arr = matrix.toarray()
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = arr / norms
        return normalized.tolist()

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = ""):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.provider_name = "gemini"
        self.model = model or settings.GEMINI_EMBEDDING_MODEL or "models/gemini-embedding-001"
        self.model_name = self.model
        self.dimension = 768

    def embed_query(self, text: str) -> list[float]:
        import google.generativeai as genai
        res = genai.embed_content(model=self.model, content=text, task_type="retrieval_query")
        return res["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import google.generativeai as genai
        embeddings = []
        for text in texts:
            res = genai.embed_content(model=self.model, content=text, task_type="retrieval_document")
            embeddings.append(res["embedding"])
        return embeddings

def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.EMBEDDING_PROVIDER.lower()
    if provider_name == "local":
        return LocalEmbeddingProvider()
    elif provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini embedding provider requested, but GEMINI_API_KEY is not set.")
        return GeminiEmbeddingProvider(settings.GEMINI_API_KEY, settings.GEMINI_EMBEDDING_MODEL)
    elif provider_name == "openai":
        raise NotImplementedError("OpenAI embedding provider configured but requires active OPENAI_API_KEY.")
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: '{provider_name}'. Supported: 'local', 'gemini'.")
