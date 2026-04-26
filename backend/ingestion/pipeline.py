"""Async document ingestion pipeline.
EPIC 1:
- Extracts text via DocumentExtractor (PDF/DOCX/TXT)
- Recursively splits into structured overlapping chunks
- Generates batch embeddings with sentence-transformers
- Stores embeddings in Pinecone under tenant-isolated namespace
- Updates BM25 keyword search index for the tenant
- Updates document status to READY or FAILED with error details
"""
import os
import shutil
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.db.repository import update_document_status
from backend.ingestion.extractor import DocumentExtractor
from backend.ingestion.chunker import RecursiveChunker
from backend.retrieval.embeddings import embedding_service
from backend.retrieval.vector_store import vector_store
from backend.retrieval.bm25_search import bm25_service

class IngestionPipeline:
    def __init__(self):
        self.chunker = RecursiveChunker()

    def process_document(self, document_id: str, tenant_id: str, temp_file_path: str, filename: str):
        """Processes an uploaded file asynchronously."""
        db: Session = SessionLocal()
        try:
            # 1. Extract text
            pages, page_count = DocumentExtractor.extract_from_file(temp_file_path, filename)
            
            # 2. Chunk document
            chunks = self.chunker.chunk_document(document_id, pages)
            if not chunks:
                raise ValueError("Document yielded no valid text chunks after splitting.")

            # 3. Batch Embed Chunks
            chunk_texts = [c.text for c in chunks]
            embeddings = embedding_service.embed_documents(chunk_texts)

            # 4. Store in Vector DB under tenant-isolated namespace
            vector_payloads = []
            bm25_payloads = []
            
            for idx, c in enumerate(chunks):
                vec_item = {
                    "id": c.chunk_id,
                    "values": embeddings[idx],
                    "metadata": {
                        "tenant_id": tenant_id,
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_text": c.text,
                        "source_page": c.source_page,
                        "chunk_index": c.chunk_index,
                        "token_count": c.token_count
                    }
                }
                vector_payloads.append(vec_item)
                
                bm25_payloads.append({
                    "chunk_id": c.chunk_id,
                    "document_id": document_id,
                    "filename": filename,
                    "text": c.text,
                    "source_page": c.source_page,
                    "chunk_index": c.chunk_index
                })

            # Hard tenant-isolated namespace
            vector_store.upsert(namespace=tenant_id, vectors=vector_payloads)

            # 5. Add to Tenant BM25 Index
            bm25_service.add_chunks_to_index(tenant_id=tenant_id, new_chunks=bm25_payloads)

            # 6. Mark Document READY
            update_document_status(
                db=db,
                document_id=document_id,
                status="READY",
                page_count=page_count,
                chunk_count=len(chunks)
            )

        except Exception as e:
            err_msg = str(e)
            print(f"[IngestionPipeline] Document processing failed ({document_id}): {err_msg}")
            update_document_status(
                db=db,
                document_id=document_id,
                status="FAILED",
                error=err_msg
            )
        finally:
            # Clean up uploaded temp file
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception:
                pass
            db.close()

ingestion_pipeline = IngestionPipeline()
