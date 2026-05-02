"""Embedding service supporting HuggingFace sentence-transformers with fallback.
TICKET-104 / TICKET-201:
Ensures identical embedding model is used for both document ingestion and query embedding.
"""
from typing import List
import numpy as np
import hashlib
from backend.config import settings

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL_NAME
        
        if settings.USE_FAST_FALLBACK_EMBEDDINGS:
            self.model = None
            return

        try:
            from sentence_transformers import SentenceTransformer
            # Load sentence transformer model
            self.model = SentenceTransformer(self.model_name)
            self.dimension = getattr(self.model, "get_embedding_dimension", self.model.get_sentence_embedding_dimension)()
        except Exception as e:
            # Fallback gracefully if model weights cannot be downloaded or offline
            print(f"[EmbeddingService] Warning: Could not initialize HF SentenceTransformer ({e}). Using deterministic embedding fallback.")
            self.model = None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of document chunk texts."""
        if not texts:
            return []
        
        if self.model is not None:
            try:
                embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                print(f"[EmbeddingService] Warning during batch encode: {e}, falling back to deterministic.")
        
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single query string using the exact same representation as document chunks."""
        if self.model is not None:
            try:
                embedding = self.model.encode(query, normalize_embeddings=True)
                return embedding.tolist()
            except Exception as e:
                print(f"[EmbeddingService] Warning during query encode: {e}, falling back.")
        
        return self._fallback_embed(query)

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic, normalized pseudo-semantic vector generator for offline/airgapped testing."""
        dim = self.dimension
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for idx, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            pos = h % dim
            weight = 1.0 / (idx + 1.0)**0.3
            vec[pos] += weight
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()

embedding_service = EmbeddingService()
