"""Document management endpoints: upload, list, status polling, and delete.
TICKET-101 / TICKET-102:
- Uploads PDF/DOCX (max 25MB), derives tenant_id strictly from API key
- Runs ingestion pipeline asynchronously
- Returns document_id immediately with status PROCESSING
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from backend.config import settings
from backend.db.session import get_db
from backend.db.models import Tenant
from backend.db.repository import (
    create_document, 
    get_document_by_id, 
    list_documents_by_tenant, 
    delete_document as repo_delete_document
)
from backend.security.auth import get_current_tenant
from backend.security.rate_limiter import rate_limiter
from backend.ingestion.pipeline import ingestion_pipeline
from backend.retrieval.vector_store import vector_store
from backend.retrieval.bm25_search import bm25_service

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Uploads a PDF or DOCX document for asynchronous chunking, embedding, and indexing."""
    # Check rate limit
    rate_limiter.check_upload_limit(current_tenant.id)
    
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {list(ALLOWED_EXTENSIONS)}"
        )

    # Read content to check file size limit (25MB)
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum limit of 25MB."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty."
        )

    # Save temporary file for background worker
    temp_dir = Path(settings.STORAGE_DIR) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{filename}"
    temp_path = str(temp_dir / temp_filename)
    
    with open(temp_path, "wb") as f:
        f.write(content)

    # Create DB document row with status PROCESSING
    doc = create_document(
        db=db,
        tenant_id=current_tenant.id,
        filename=filename,
        file_size_bytes=file_size
    )

    # Dispatch ingestion in background
    background_tasks.add_task(
        ingestion_pipeline.process_document,
        document_id=doc.id,
        tenant_id=current_tenant.id,
        temp_file_path=temp_path,
        filename=filename
    )

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "tenant_id": current_tenant.id,
        "message": "Document accepted for asynchronous ingestion."
    }

@router.get("")
def list_documents(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Lists all documents belonging to the authenticated tenant."""
    docs = list_documents_by_tenant(db, current_tenant.id)
    return {
        "tenant_id": current_tenant.id,
        "tenant_name": current_tenant.name,
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "error": d.error,
                "page_count": d.page_count,
                "chunk_count": d.chunk_count,
                "file_size_bytes": d.file_size_bytes,
                "created_at": d.created_at.isoformat()
            }
            for d in docs
        ]
    }

@router.get("/{document_id}")
def get_document_status(
    document_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Polls document processing status."""
    doc = get_document_by_id(db, document_id, current_tenant.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or does not belong to tenant.")
        
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "error": doc.error,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "file_size_bytes": doc.file_size_bytes,
        "created_at": doc.created_at.isoformat()
    }

@router.delete("/{document_id}")
def delete_document_endpoint(
    document_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Deletes document from database, vector store namespace, and BM25 index."""
    # Delete from vector namespace
    vector_store.delete_by_document(namespace=current_tenant.id, document_id=document_id)
    
    # Delete from BM25 index
    bm25_service.remove_document(tenant_id=current_tenant.id, document_id=document_id)
    
    # Delete from SQL
    deleted = repo_delete_document(db, document_id, current_tenant.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    return {"message": "Document successfully deleted.", "document_id": document_id}
