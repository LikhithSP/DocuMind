"""DocuMind system configuration loaded from environment variables."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocuMind"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    BASE_DIR: str = str(ROOT_DIR)
    USE_FAST_FALLBACK_EMBEDDINGS: bool = os.getenv("USE_FAST_FALLBACK_EMBEDDINGS", "false").lower() in ("1", "true")
    
    # Storage and DB
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'data' / 'documind.db'}")
    STORAGE_DIR: str = str(ROOT_DIR / "data" / "storage")
    BM25_INDEX_DIR: str = str(ROOT_DIR / "data" / "bm25_indices")
    VECTOR_STORAGE_DIR: str = str(ROOT_DIR / "data" / "vector_store")
    
    # Vector DB
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "documind-index")
    EMBEDDING_DIMENSION: int = 384
    
    # Embeddings & Reranker models
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # Chunking
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 50
    
    # Retrieval
    DENSE_TOP_K: int = 20
    BM25_TOP_K: int = 20
    RRF_K: int = 60
    FINAL_TOP_K: int = 5
    
    # LLM API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    
    # Rate Limits (queries per minute per tenant)
    QUERY_RATE_LIMIT_PER_MINUTE: int = 20
    UPLOAD_RATE_LIMIT_PER_MINUTE: int = 10
    
    # Maximum upload size: 25MB
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure required directories exist
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.BM25_INDEX_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.VECTOR_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
