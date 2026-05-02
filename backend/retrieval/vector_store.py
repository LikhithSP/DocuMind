"""Vector DB abstraction with Pinecone Namespace multi-tenant isolation.
TICKET-104 / TICKET-201 / TICKET-402:
Enforces hard tenant isolation via namespaces at the storage layer.
A query against tenant namespace A CANNOT physically return vectors from namespace B.
"""
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
import numpy as np
from backend.config import settings

class VectorStore:
    def __init__(self):
        self.pinecone_client = None
        self.index = None
        self.use_pinecone = False
        self.storage_dir = Path(settings.VECTOR_STORAGE_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if Pinecone is configured
        if settings.PINECONE_API_KEY:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                self.index = pc.Index(settings.PINECONE_INDEX_NAME)
                self.use_pinecone = True
                print("[VectorStore] Connected to Pinecone cloud index.")
            except Exception as e:
                print(f"[VectorStore] Pinecone initialization notice ({e}). Using embedded namespaced engine.")
                self.use_pinecone = False

    def _get_namespace_file(self, namespace: str) -> Path:
        safe_ns = "".join([c if c.isalnum() or c in "-_" else "_" for c in namespace])
        return self.storage_dir / f"ns_{safe_ns}.json"

    def _load_local_namespace(self, namespace: str) -> List[Dict[str, Any]]:
        file_path = self._get_namespace_file(namespace)
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_local_namespace(self, namespace: str, vectors: List[Dict[str, Any]]):
        file_path = self._get_namespace_file(namespace)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(vectors, f, ensure_ascii=False)

    def upsert(self, namespace: str, vectors: List[Dict[str, Any]]):
        """Upserts a list of vectors into the specified tenant namespace.
        Each vector format:
        {
            "id": chunk_id,
            "values": [0.1, ...],
            "metadata": {
                "tenant_id": ...,
                "document_id": ...,
                "chunk_text": ...,
                "source_page": ...,
                "chunk_index": ...
            }
        }
        """
        if not namespace:
            raise ValueError("Tenant namespace is strictly required for vector upsert.")

        if self.use_pinecone and self.index:
            try:
                # Batch upsert to Pinecone in chunks of 100
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i + batch_size]
                    self.index.upsert(vectors=batch, namespace=namespace)
                return
            except Exception as e:
                print(f"[VectorStore] Pinecone upsert failed: {e}. Falling back to local storage.")

        # Local namespaced storage
        current_data = self._load_local_namespace(namespace)
        existing_ids = {item["id"]: idx for idx, item in enumerate(current_data)}
        
        for vec in vectors:
            if vec["id"] in existing_ids:
                current_data[existing_ids[vec["id"]]] = vec
            else:
                current_data.append(vec)
                existing_ids[vec["id"]] = len(current_data) - 1
                
        self._save_local_namespace(namespace, current_data)

    def query(
        self, 
        namespace: str, 
        query_vector: List[float], 
        top_k: int = 20, 
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries the vector index strictly scoped to the tenant namespace.
        Returns matches: [{"id": ..., "score": ..., "metadata": {...}}]
        """
        if not namespace:
            raise ValueError("Tenant namespace is strictly required for query isolation.")

        if self.use_pinecone and self.index:
            try:
                res = self.index.query(
                    namespace=namespace,
                    vector=query_vector,
                    top_k=top_k,
                    include_metadata=True,
                    filter=filter_metadata
                )
                matches = []
                for m in res.matches:
                    matches.append({
                        "id": m.id,
                        "score": float(m.score),
                        "metadata": m.metadata or {}
                    })
                return matches
            except Exception as e:
                print(f"[VectorStore] Pinecone query failed: {e}. Falling back to local.")

        # Local namespaced vector cosine similarity
        local_vectors = self._load_local_namespace(namespace)
        if not local_vectors:
            return []
        
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored_matches = []
        for item in local_vectors:
            meta = item.get("metadata", {})
            if filter_metadata:
                match = True
                for k, v in filter_metadata.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            v_vec = np.array(item["values"], dtype=np.float32)
            v_norm = np.linalg.norm(v_vec)
            if v_norm == 0:
                score = 0.0
            else:
                score = float(np.dot(q_vec, v_vec) / (q_norm * v_norm))

            scored_matches.append({
                "id": item["id"],
                "score": score,
                "metadata": meta
            })

        # Sort descending by score
        scored_matches.sort(key=lambda x: x["score"], reverse=True)
        return scored_matches[:top_k]

    def delete_by_document(self, namespace: str, document_id: str):
        """Deletes all chunks belonging to a document from the tenant namespace."""
        if not namespace or not document_id:
            return

        if self.use_pinecone and self.index:
            try:
                self.index.delete(
                    namespace=namespace,
                    filter={"document_id": document_id}
                )
                return
            except Exception as e:
                print(f"[VectorStore] Pinecone delete failed: {e}")

        # Local storage delete
        current_data = self._load_local_namespace(namespace)
        filtered = [v for v in current_data if v.get("metadata", {}).get("document_id") != document_id]
        self._save_local_namespace(namespace, filtered)

vector_store = VectorStore()
