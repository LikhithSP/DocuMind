"""Cross-Encoder re-ranker service for final relevance scoring.
TICKET-204:
Cross-encoders jointly score (query, chunk) pairs to identify true semantic alignment,
refining the broad fused candidate set (~20-30 chunks) down to high-precision top-5 chunks.
"""
from typing import List, Dict, Any, Tuple
import time
from backend.config import settings

class ReRankerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ReRankerService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        self.model = None
        self.model_name = settings.RERANKER_MODEL_NAME
        if settings.USE_FAST_FALLBACK_EMBEDDINGS:
            self.model = None
            return

        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
        except Exception as e:
            print(f"[ReRankerService] Notice: CrossEncoder model not loaded ({e}). Using algorithmic cross-scoring fallback.")
            self.model = None

    def rerank(
        self, 
        query: str, 
        candidates: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Scores (query, chunk) pairs and reorders candidates descending by relevance.
        Returns (reordered_top_k_candidates, elapsed_latency_ms).
        """
        start_time = time.perf_counter()
        if not candidates:
            return [], 0

        texts = [c.get("text") or c.get("metadata", {}).get("chunk_text", "") for c in candidates]
        
        scores = []
        if self.model is not None:
            try:
                pairs = [[query, text] for text in texts]
                raw_scores = self.model.predict(pairs)
                scores = [float(s) for s in raw_scores]
            except Exception as e:
                print(f"[ReRankerService] Prediction error: {e}, falling back.")
                scores = [self._fallback_score(query, text) for text in texts]
        else:
            scores = [self._fallback_score(query, text) for text in texts]

        # Attach rerank score and sort
        for idx, c in enumerate(candidates):
            c["rerank_score"] = float(scores[idx])

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_results = candidates[:top_k]
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return top_results, elapsed_ms

    def _fallback_score(self, query: str, text: str) -> float:
        """Heuristic cross-scorer computing word containment, exact bi-gram matches, and phrase coverage."""
        q_words = [w for w in query.lower().split() if len(w) > 2]
        if not q_words:
            return 0.0
        
        t_lower = text.lower()
        word_hits = sum(1 for w in q_words if w in t_lower)
        coverage = word_hits / len(q_words)
        
        # Check consecutive bi-grams
        bigrams = [f"{q_words[i]} {q_words[i+1]}" for i in range(len(q_words)-1)]
        bigram_hits = sum(1 for bg in bigrams if bg in t_lower) if bigrams else 0
        bigram_bonus = (bigram_hits / len(bigrams)) * 0.5 if bigrams else 0.0
        
        return float(coverage + bigram_bonus)

reranker_service = ReRankerService()
