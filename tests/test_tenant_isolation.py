"""Multi-tenant isolation security verification test.
TICKET-402 & 06_security_access.md:
CRITICAL SECURITY TEST:
- Ingests overlapping confidential document content under two distinct tenants (Tenant A and Tenant B)
- Queries retrieval pipeline strictly as Tenant A
- Asserts that ZERO chunks or snippets from Tenant B appear in Tenant A's results.
- Asserts that Tenant B's query similarly never leaks Tenant A's records.
"""
import pytest
from backend.retrieval.vector_store import vector_store
from backend.retrieval.bm25_search import bm25_service
from backend.retrieval.hybrid_search import hybrid_retrieval_service
from backend.retrieval.embeddings import embedding_service

def test_tenant_isolation_zero_leakage():
    tenant_a = "tenant-apple-prod"
    tenant_b = "tenant-banana-corp"
    
    # Tenant A confidential doc
    doc_a_text = "SECRET-PROJECT-TITAN: Internal Apple autonomous vehicle testing coordinates in Arizona desert."
    emb_a = embedding_service.embed_documents([doc_a_text])[0]
    
    vector_store.upsert(
        namespace=tenant_a,
        vectors=[{
            "id": "titan-chunk-01",
            "values": emb_a,
            "metadata": {
                "tenant_id": tenant_a,
                "document_id": "apple-confidential-doc",
                "filename": "apple_secret.pdf",
                "chunk_text": doc_a_text,
                "source_page": 1,
                "chunk_index": 0
            }
        }]
    )
    bm25_service.add_chunks_to_index(
        tenant_id=tenant_a,
        new_chunks=[{
            "chunk_id": "titan-chunk-01",
            "document_id": "apple-confidential-doc",
            "filename": "apple_secret.pdf",
            "text": doc_a_text,
            "source_page": 1,
            "chunk_index": 0
        }]
    )

    # Tenant B confidential doc with similar wording/query terms
    doc_b_text = "CONFIDENTIAL-PROJECT-CYBER: Banana Corp robotics testing protocol in Arizona test track."
    emb_b = embedding_service.embed_documents([doc_b_text])[0]
    
    vector_store.upsert(
        namespace=tenant_b,
        vectors=[{
            "id": "cyber-chunk-99",
            "values": emb_b,
            "metadata": {
                "tenant_id": tenant_b,
                "document_id": "banana-confidential-doc",
                "filename": "banana_secret.pdf",
                "chunk_text": doc_b_text,
                "source_page": 1,
                "chunk_index": 0
            }
        }]
    )
    bm25_service.add_chunks_to_index(
        tenant_id=tenant_b,
        new_chunks=[{
            "chunk_id": "cyber-chunk-99",
            "document_id": "banana-confidential-doc",
            "filename": "banana_secret.pdf",
            "text": doc_b_text,
            "source_page": 1,
            "chunk_index": 0
        }]
    )

    # Query as Tenant A: searching for "Arizona testing protocol robotics"
    results_a, _ = hybrid_retrieval_service.retrieve(
        tenant_id=tenant_a,
        query="Arizona testing protocol robotics",
        top_k=10
    )

    # Verify: Zero chunks from Tenant B can EVER appear in Tenant A's result
    for r in results_a:
        assert r["id"] != "cyber-chunk-99", "CRITICAL SECURITY BREACH: Tenant B chunk leaked to Tenant A!"
        meta = r.get("metadata", {})
        assert meta.get("tenant_id") == tenant_a or meta.get("tenant_id") is None
        assert "Banana Corp" not in (r.get("text") or meta.get("chunk_text", ""))

    # Query as Tenant B: searching for "TITAN vehicle coordinates"
    results_b, _ = hybrid_retrieval_service.retrieve(
        tenant_id=tenant_b,
        query="TITAN autonomous vehicle coordinates",
        top_k=10
    )

    # Verify: Zero chunks from Tenant A appear in Tenant B's result
    for r in results_b:
        assert r["id"] != "titan-chunk-01", "CRITICAL SECURITY BREACH: Tenant A chunk leaked to Tenant B!"
        meta = r.get("metadata", {})
        assert meta.get("tenant_id") == tenant_b or meta.get("tenant_id") is None
        assert "Apple autonomous" not in (r.get("text") or meta.get("chunk_text", ""))
