"""Main FastAPI application entrypoint for DocuMind."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.db.session import init_db, SessionLocal
from backend.db.repository import create_tenant_with_key, list_all_tenants
from backend.api.admin import router as admin_router
from backend.api.documents import router as documents_router
from backend.api.query import router as query_router
from backend.api.usage import router as usage_router
from backend.api.eval import router as eval_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup
    init_db()
    
    # Auto-seed default demo tenant if empty
    db = SessionLocal()
    try:
        tenants = list_all_tenants(db)
        if not tenants:
            tenant, raw_key = create_tenant_with_key(db, "Enterprise Demo Corp")
            print(f"[DocuMind Startup] Created default demo tenant '{tenant.name}' (ID: {tenant.id})")
            print(f"[DocuMind Startup] Default API Key: {raw_key}")
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Multi-Tenant RAG Platform with Hybrid Retrieval, Cross-Encoder Re-ranking, and RAGAS Evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(admin_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(usage_router)
app.include_router(eval_router)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "vector_isolation": "Pinecone Namespaces / Local Namespaces",
        "retrieval": "Hybrid (Dense Vector + BM25 + RRF + Cross-Encoder Re-Rank)"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[DocuMind Error] Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
