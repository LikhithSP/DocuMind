"""SQLAlchemy relational models for DocuMind."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    
    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="tenant", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"
    
    key_hash = Column(String(64), primary_key=True) # SHA-256 hex string
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    prefix = Column(String(16), nullable=False) # e.g. docu_live_xxxx...
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    
    tenant = relationship("Tenant", back_populates="api_keys")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(32), default="PROCESSING", nullable=False) # PROCESSING, READY, FAILED
    error = Column(Text, nullable=True)
    page_count = Column(Integer, default=0, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    
    tenant = relationship("Tenant", back_populates="documents")

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    retrieval_latency_ms = Column(Integer, default=0, nullable=False)
    generation_latency_ms = Column(Integer, default=0, nullable=False)
    total_latency_ms = Column(Integer, default=0, nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0, nullable=False)
    chunks_retrieved_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    
    tenant = relationship("Tenant", back_populates="query_logs")

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_version = Column(String(64), nullable=False) # e.g. "hybrid+rerank-v1" or "dense-only"
    faithfulness = Column(Numeric(5, 4), nullable=False)
    answer_relevancy = Column(Numeric(5, 4), nullable=False)
    context_precision = Column(Numeric(5, 4), nullable=False)
    context_recall = Column(Numeric(5, 4), nullable=False)
    per_question_results = Column(Text, nullable=False) # JSON encoded
    run_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
