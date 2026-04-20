"""Database repository operations for Tenants, API Keys, Documents, and Query Logs."""
import hashlib
import secrets
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import Tenant, ApiKey, Document, QueryLog, EvaluationRun

def hash_api_key(api_key: str) -> str:
    """Hash raw API key with SHA-256 for secure DB storage."""
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()

def generate_api_key(prefix: str = "docu_live_") -> Tuple[str, str, str]:
    """Generates a raw API key, its SHA-256 hash, and key preview."""
    random_part = secrets.token_hex(24)
    raw_key = f"{prefix}{random_part}"
    key_hash = hash_api_key(raw_key)
    preview = f"{raw_key[:14]}...{raw_key[-4:]}"
    return raw_key, key_hash, preview

# --- Tenant & API Key Operations ---

def create_tenant_with_key(db: Session, name: str) -> Tuple[Tenant, str]:
    """Creates a tenant and an associated API key. Returns (tenant, raw_api_key)."""
    tenant = Tenant(id=str(uuid.uuid4()), name=name)
    db.add(tenant)
    db.flush()
    
    raw_key, key_hash, preview = generate_api_key()
    api_key_record = ApiKey(
        key_hash=key_hash,
        tenant_id=tenant.id,
        prefix=preview,
        revoked=False
    )
    db.add(api_key_record)
    db.commit()
    db.refresh(tenant)
    return tenant, raw_key

def get_tenant_by_api_key(db: Session, raw_key: str) -> Optional[Tenant]:
    """Authenticates the raw API key and returns the associated tenant if valid."""
    if not raw_key:
        return None
    key_hash = hash_api_key(raw_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.revoked == False).first()
    if not api_key:
        return None
    return db.query(Tenant).filter(Tenant.id == api_key.tenant_id).first()

def get_tenant_by_id(db: Session, tenant_id: str) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()

def list_all_tenants(db: Session) -> List[Tenant]:
    return db.query(Tenant).order_by(Tenant.created_at.desc()).all()

# --- Document Operations ---

def create_document(db: Session, tenant_id: str, filename: str, file_size_bytes: int = 0) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        status="PROCESSING"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def get_document_by_id(db: Session, document_id: str, tenant_id: str) -> Optional[Document]:
    return db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant_id
    ).first()

def list_documents_by_tenant(db: Session, tenant_id: str) -> List[Document]:
    return db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).order_by(Document.created_at.desc()).all()

def update_document_status(
    db: Session, 
    document_id: str, 
    status: str, 
    page_count: int = 0, 
    chunk_count: int = 0, 
    error: Optional[str] = None
) -> Optional[Document]:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = status
        if page_count > 0:
            doc.page_count = page_count
        if chunk_count > 0:
            doc.chunk_count = chunk_count
        if error:
            doc.error = error
        db.commit()
        db.refresh(doc)
    return doc

def delete_document(db: Session, document_id: str, tenant_id: str) -> bool:
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.tenant_id == tenant_id
    ).first()
    if doc:
        db.delete(doc)
        db.commit()
        return True
    return False

# --- Query Log Operations ---

def log_query(
    db: Session,
    tenant_id: str,
    query_text: str,
    retrieval_latency_ms: int,
    generation_latency_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost_usd: float,
    chunks_retrieved_count: int = 0
) -> QueryLog:
    total_latency_ms = retrieval_latency_ms + generation_latency_ms
    total_tokens = prompt_tokens + completion_tokens
    
    log = QueryLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        query_text=query_text,
        retrieval_latency_ms=retrieval_latency_ms,
        generation_latency_ms=generation_latency_ms,
        total_latency_ms=total_latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        chunks_retrieved_count=chunks_retrieved_count
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_tenant_usage_summary(db: Session, tenant_id: str):
    """Computes total queries, total tokens, avg latency, and total estimated cost."""
    logs = db.query(QueryLog).filter(QueryLog.tenant_id == tenant_id).all()
    if not logs:
        return {
            "tenant_id": tenant_id,
            "total_queries": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_retrieval_latency_ms": 0.0,
            "avg_generation_latency_ms": 0.0,
            "avg_total_latency_ms": 0.0,
            "recent_queries": []
        }
    
    total_queries = len(logs)
    total_tokens = sum(l.total_tokens for l in logs)
    prompt_tokens = sum(l.prompt_tokens for l in logs)
    completion_tokens = sum(l.completion_tokens for l in logs)
    total_cost_usd = float(sum(l.estimated_cost_usd for l in logs))
    avg_retrieval = sum(l.retrieval_latency_ms for l in logs) / total_queries
    avg_generation = sum(l.generation_latency_ms for l in logs) / total_queries
    avg_total = sum(l.total_latency_ms for l in logs) / total_queries
    
    recent = [
        {
            "id": l.id,
            "query_text": l.query_text,
            "retrieval_latency_ms": l.retrieval_latency_ms,
            "generation_latency_ms": l.generation_latency_ms,
            "total_latency_ms": l.total_latency_ms,
            "total_tokens": l.total_tokens,
            "estimated_cost_usd": float(l.estimated_cost_usd),
            "chunks_retrieved_count": l.chunks_retrieved_count,
            "created_at": l.created_at.isoformat()
        }
        for l in logs[-10:] # last 10 queries
    ]
    
    return {
        "tenant_id": tenant_id,
        "total_queries": total_queries,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_cost_usd": round(total_cost_usd, 6),
        "avg_retrieval_latency_ms": round(avg_retrieval, 2),
        "avg_generation_latency_ms": round(avg_generation, 2),
        "avg_total_latency_ms": round(avg_total, 2),
        "recent_queries": list(reversed(recent))
    }
