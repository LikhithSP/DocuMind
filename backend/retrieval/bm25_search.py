"""Tenant-scoped BM25 keyword search index.
TICKET-202:
Enables keyword/sparse retrieval over all chunks for a specific tenant,
catching exact codes, SKU numbers, names, and terms missed by pure dense vectors.
"""
from typing import List, Dict, Any, Tuple
import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from backend.config import settings

class BM25IndexService:
    def __init__(self):
        self.index_dir = Path(settings.BM25_INDEX_DIR)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        # Memory cache: tenant_id -> (BM25Okapi instance, chunks_metadata)
        self._indices: Dict[str, Tuple[BM25Okapi, List[Dict[str, Any]]]] = {}

    def _get_tenant_file(self, tenant_id: str) -> Path:
        safe_tenant = "".join([c if c.isalnum() or c in "-_" else "_" for c in tenant_id])
        return self.index_dir / f"bm25_{safe_tenant}.json"

    def _tokenize(self, text: str) -> List[str]:
        """Lowercases, splits on non-alphanumeric, and strips punctuation."""
        return [w for w in re.findall(r"\w+", text.lower()) if len(w) > 1]

    def add_chunks_to_index(self, tenant_id: str, new_chunks: List[Dict[str, Any]]):
        """Adds or updates chunks in the tenant's BM25 index and persists it."""
        current_chunks = self.load_chunks(tenant_id)
        
        # Merge chunks by chunk_id
        chunk_map = {c["chunk_id"]: c for c in current_chunks}
        for chunk in new_chunks:
            chunk_map[chunk["chunk_id"]] = chunk
            
        merged_chunks = list(chunk_map.values())
        self._persist_chunks(tenant_id, merged_chunks)
        
        # Build in-memory index
        tokenized_corpus = [self._tokenize(c["text"]) for c in merged_chunks]
        if tokenized_corpus:
            bm25 = BM25Okapi(tokenized_corpus)
            self._indices[tenant_id] = (bm25, merged_chunks)

    def load_chunks(self, tenant_id: str) -> List[Dict[str, Any]]:
        file_path = self._get_tenant_file(tenant_id)
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _persist_chunks(self, tenant_id: str, chunks: List[Dict[str, Any]]):
        file_path = self._get_tenant_file(tenant_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)

    def search(self, tenant_id: str, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Searches BM25 index for the tenant. Returns scored chunks:
        [{"id": chunk_id, "score": bm25_score, "text": ..., "metadata": ...}]
        """
        if tenant_id not in self._indices:
            chunks = self.load_chunks(tenant_id)
            if not chunks:
                return []
            tokenized_corpus = [self._tokenize(c["text"]) for c in chunks]
            if not tokenized_corpus:
                return []
            bm25 = BM25Okapi(tokenized_corpus)
            self._indices[tenant_id] = (bm25, chunks)

        bm25, chunks = self._indices[tenant_id]
        if not chunks:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = bm25.get_scores(tokenized_query)
        scored_pairs = []
        for idx, score in enumerate(scores):
            if score > 0.0:
                chunk = chunks[idx]
                scored_pairs.append({
                    "id": chunk["chunk_id"],
                    "score": float(score),
                    "text": chunk["text"],
                    "metadata": {
                        "document_id": chunk["document_id"],
                        "source_page": chunk["source_page"],
                        "chunk_index": chunk["chunk_index"],
                        "chunk_text": chunk["text"]
                    }
                })

        scored_pairs.sort(key=lambda x: x["score"], reverse=True)
        return scored_pairs[:top_k]

    def remove_document(self, tenant_id: str, document_id: str):
        """Removes all chunks of document_id from tenant index."""
        current_chunks = self.load_chunks(tenant_id)
        filtered = [c for c in current_chunks if c.get("document_id") != document_id]
        self._persist_chunks(tenant_id, filtered)
        if tenant_id in self._indices:
            del self._indices[tenant_id]

bm25_service = BM25IndexService()
