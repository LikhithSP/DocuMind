"""Integration test verifying dense vector search, BM25 keyword search, RRF fusion, and Re-ranking.
EPIC 2 testing:
- Validates RRF formula combines and ranks hits accurately
- Confirms cross-encoder prioritizes semantically aligned passages
"""
import pytest
from backend.retrieval.hybrid_search import hybrid_retrieval_service
from backend.retrieval.vector_store import vector_store
from backend.retrieval.bm25_search import bm25_service
from backend.retrieval.embeddings import embedding_service

def test_reciprocal_rank_fusion():
    dense_results = [
        {"id": "c1", "score": 0.95, "metadata": {"chunk_text": "text 1"}},
        {"id": "c2", "score": 0.85, "metadata": {"chunk_text": "text 2"}},
    ]
    bm25_results = [
        {"id": "c2", "score": 8.5, "text": "text 2", "metadata": {"chunk_text": "text 2"}},
        {"id": "c3", "score": 5.0, "text": "text 3", "metadata": {"chunk_text": "text 3"}},
    ]
    
    fused = hybrid_retrieval_service.reciprocal_rank_fusion(dense_results, bm25_results)
    assert len(fused) == 3
    # c2 appears in BOTH lists, so its RRF score must be the highest
    assert fused[0]["id"] == "c2"
    assert fused[0]["dense_rank"] == 2
    assert fused[0]["bm25_rank"] == 1
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]

def test_hybrid_search_end_to_end():
    tenant_id = "tenant-hybrid-test"
    
    # Ingest test vector and bm25
    chunk_text = "Incident command steps for P0 database outage require paging primary SRE."
    q_emb = embedding_service.embed_documents([chunk_text])[0]
    
    vector_store.upsert(
        namespace=tenant_id,
        vectors=[{
            "id": "chunk-incident-1",
            "values": q_emb,
            "metadata": {
                "tenant_id": tenant_id,
                "document_id": "doc-runbook",
                "filename": "runbook.pdf",
                "chunk_text": chunk_text,
                "source_page": 1,
                "chunk_index": 0
            }
        }]
    )
    
    bm25_service.add_chunks_to_index(
        tenant_id=tenant_id,
        new_chunks=[{
            "chunk_id": "chunk-incident-1",
            "document_id": "doc-runbook",
            "filename": "runbook.pdf",
            "text": chunk_text,
            "source_page": 1,
            "chunk_index": 0
        }]
    )
    
    results, timing = hybrid_retrieval_service.retrieve(
        tenant_id=tenant_id,
        query="What are the steps for a P0 database outage?",
        top_k=3
    )
    
    assert len(results) > 0
    assert results[0]["id"] == "chunk-incident-1"
    assert "total_retrieval_ms" in timing
    assert "rerank_ms" in timing
