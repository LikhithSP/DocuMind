"""Database connection, engine configuration, and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
from backend.db.models import Base

# Configure SQLite or PostgreSQL
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables defined in Base."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for obtaining database session in FastAPI endpoints."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
