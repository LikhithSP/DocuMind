"""Hybrid Retrieval Pipeline: Dense + Sparse (BM25) + Reciprocal Rank Fusion (RRF) + Re-ranking.
EPIC 2:
1. Dense search in tenant namespace (Pinecone / local)
2. BM25 sparse search in tenant index
3. Reciprocal Rank Fusion (RRF) merging & deduplication:
   RRF_score(chunk) = Σ 1 / (k + rank_in_list_i)
4. Cross-encoder re-ranking to top-5 chunks
5. Detailed latency logging and structured citation preparation
"""
from typing import List, Dict, Any, Tuple
import time
from backend.config import settings
from backend.retrieval.embeddings import embedding_service
from backend.retrieval.vector_store import vector_store
from backend.retrieval.bm25_search import bm25_service
from backend.retrieval.reranker import reranker_service

class HybridRetrievalService:
    def __init__(self):
        self.rrf_k = settings.RRF_K # standard 60

    def reciprocal_rank_fusion(
        self, 
        dense_results: List[Dict[str, Any]], 
        bm25_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merges dense and sparse lists using Reciprocal Rank Fusion formula:
        RRF_score = Σ (1 / (k + rank))
        Deduplicates chunks appearing in both lists.
        """
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # 1. Score dense candidates
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item["id"]
            score = 1.0 / (self.rrf_k + rank)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + score
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = {
                    "id": chunk_id,
                    "text": item.get("metadata", {}).get("chunk_text", ""),
                    "metadata": item.get("metadata", {}),
                    "dense_rank": rank,
                    "dense_score": item.get("score", 0.0),
                    "bm25_rank": None,
                    "bm25_score": None
                }

        # 2. Score BM25 candidates
        for rank, item in enumerate(bm25_results, start=1):
            chunk_id = item["id"]
            score = 1.0 / (self.rrf_k + rank)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + score
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = {
                    "id": chunk_id,
                    "text": item.get("text", "") or item.get("metadata", {}).get("chunk_text", ""),
                    "metadata": item.get("metadata", {}),
                    "dense_rank": None,
                    "dense_score": None,
                    "bm25_rank": rank,
                    "bm25_score": item.get("score", 0.0)
                }
            else:
                chunk_map[chunk_id]["bm25_rank"] = rank
                chunk_map[chunk_id]["bm25_score"] = item.get("score", 0.0)

        # 3. Assemble fused list
        fused_candidates = []
        for chunk_id, rrf_score in fused_scores.items():
            entry = chunk_map[chunk_id]
            entry["rrf_score"] = round(rrf_score, 6)
            fused_candidates.append(entry)

        # Sort descending by RRF score
        fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_candidates

    def retrieve(
        self, 
        tenant_id: str, 
        query: str, 
        top_k: int = 5,
        dense_top_k: int = 20,
        bm25_top_k: int = 20
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Executes full hybrid retrieval pipeline strictly scoped to tenant_id:
        Returns:
            (top_k_chunks, timing_metrics_dict)
        """
        overall_start = time.perf_counter()
        timing: Dict[str, int] = {}

        # 1. Dense retrieval in tenant namespace
        t0 = time.perf_counter()
        q_emb = embedding_service.embed_query(query)
        dense_results = vector_store.query(
            namespace=tenant_id,
            query_vector=q_emb,
            top_k=dense_top_k
        )
        timing["dense_ms"] = int((time.perf_counter() - t0) * 1000)

        # 2. Sparse (BM25) retrieval in tenant index
        t1 = time.perf_counter()
        bm25_results = bm25_service.search(
            tenant_id=tenant_id,
            query=query,
            top_k=bm25_top_k
        )
        timing["bm25_ms"] = int((time.perf_counter() - t1) * 1000)

        # 3. Reciprocal Rank Fusion
        t2 = time.perf_counter()
        fused_candidates = self.reciprocal_rank_fusion(dense_results, bm25_results)
        timing["fusion_ms"] = int((time.perf_counter() - t2) * 1000)

        # 4. Cross-Encoder Re-ranking
        t3 = time.perf_counter()
        # Re-rank top candidates (up to 20 fused candidates)
        candidates_to_rerank = fused_candidates[:25]
        top_reranked, rerank_latency_ms = reranker_service.rerank(
            query=query,
            candidates=candidates_to_rerank,
            top_k=top_k
        )
        timing["rerank_ms"] = rerank_latency_ms

        total_retrieval_ms = int((time.perf_counter() - overall_start) * 1000)
        timing["total_retrieval_ms"] = total_retrieval_ms
        timing["dense_candidates_count"] = len(dense_results)
        timing["bm25_candidates_count"] = len(bm25_results)
        timing["fused_candidates_count"] = len(fused_candidates)

        return top_reranked, timing

hybrid_retrieval_service = HybridRetrievalService()
