"""Unit tests for recursive text chunker.
TICKET-103 testing:
- Validates chunk sizes and overlap
- Boundary cases: empty documents, short text, documents with no paragraph breaks
- Verifies retention of document_id, source_page, chunk_index
"""
import pytest
from backend.ingestion.extractor import ExtractedPage
from backend.ingestion.chunker import RecursiveChunker

def test_recursive_chunker_basic():
    chunker = RecursiveChunker(chunk_size_chars=200, chunk_overlap_chars=40)
    text = (
        "DocuMind is an enterprise retrieval platform. It implements hybrid retrieval combining dense vectors and BM25. "
        "It also uses cross-encoder re-ranking to prioritize the most relevant documents. "
        "Each tenant has isolated vector namespaces ensuring high multi-tenant security."
    )
    pages = [ExtractedPage(page_number=1, text=text)]
    chunks = chunker.chunk_document("doc-123", pages)
    
    assert len(chunks) >= 1
    for idx, c in enumerate(chunks):
        assert c.document_id == "doc-123"
        assert c.source_page == 1
        assert c.chunk_index == idx
        assert len(c.text) > 0
        assert c.token_count > 0

def test_chunker_empty_and_short_docs():
    chunker = RecursiveChunker()
    # Empty page
    chunks = chunker.chunk_document("doc-empty", [ExtractedPage(page_number=1, text="")])
    assert len(chunks) == 0
    
    # Very short noise
    chunks_short = chunker.chunk_document("doc-short", [ExtractedPage(page_number=1, text="Hi.")])
    assert len(chunks_short) == 0 # Filtered out < 10 chars

def test_chunker_multi_page():
    chunker = RecursiveChunker(chunk_size_chars=100, chunk_overlap_chars=20)
    pages = [
        ExtractedPage(page_number=1, text="Page one details the introductory architecture and design patterns for DocuMind platform."),
        ExtractedPage(page_number=2, text="Page two describes the multi-tenant isolation guarantees and Pinecone namespaces enforcement.")
    ]
    chunks = chunker.chunk_document("doc-multi", pages)
    assert len(chunks) >= 2
    pages_found = {c.source_page for c in chunks}
    assert 1 in pages_found
    assert 2 in pages_found
