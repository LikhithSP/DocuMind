"""Query endpoint with hybrid retrieval, streaming SSE generation, and token/cost logging.
EPIC 2 / EPIC 3 / EPIC 6:
- Scopes search strictly to authenticated tenant_id
- Streams answer tokens via SSE chunk events
- Emits final event containing structured citations, retrieval timing, and estimated cost
- Asynchronously logs metrics to PostgreSQL/SQLite query_logs
"""
import json
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal, get_db
from backend.db.models import Tenant
from backend.db.repository import log_query
from backend.security.auth import get_current_tenant
from backend.security.rate_limiter import rate_limiter
from backend.retrieval.hybrid_search import hybrid_retrieval_service
from backend.generation.generator import generation_service

router = APIRouter(prefix="/query", tags=["Query"])

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5

@router.post("")
async def query_documents(
    payload: QueryRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Executes hybrid retrieval over tenant documents, streams grounded generation,
    and returns verified inline citations and observability telemetry.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question exceeds maximum allowed length of 1000 characters.")

    # 1. Rate limiting check
    rate_limiter.check_query_limit(current_tenant.id)

    # 2. Hybrid retrieval (Dense + BM25 + RRF + Re-rank) scoped strictly to tenant_id
    retrieved_chunks, timing = hybrid_retrieval_service.retrieve(
        tenant_id=current_tenant.id,
        query=question,
        top_k=payload.top_k or 5
    )
    retrieval_latency_ms = timing.get("total_retrieval_ms", 0)

    # 3. Stream generation and logging
    async def sse_event_generator():
        citations = []
        prompt_tokens = 0
        completion_tokens = 0
        generation_latency_ms = 0
        cost_usd = 0.0

        # Stream answer chunks
        async for item in generation_service.stream_answer(question, retrieved_chunks):
            if item["type"] == "token":
                data = json.dumps({"event": "token", "data": item["content"]})
                yield f"data: {data}\n\n"
            elif item["type"] == "complete":
                citations = item.get("citations", [])
                prompt_tokens = item.get("prompt_tokens", 0)
                completion_tokens = item.get("completion_tokens", 0)
                generation_latency_ms = item.get("generation_latency_ms", 0)
                cost_usd = item.get("estimated_cost_usd", 0.0)

        # Emit completion payload with citations & observability breakdown
        final_payload = {
            "event": "complete",
            "data": {
                "citations": citations,
                "metrics": {
                    "retrieval_latency_ms": retrieval_latency_ms,
                    "generation_latency_ms": generation_latency_ms,
                    "total_latency_ms": retrieval_latency_ms + generation_latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "estimated_cost_usd": cost_usd,
                    "chunks_retrieved_count": len(retrieved_chunks),
                    "dense_candidates": timing.get("dense_candidates_count", 0),
                    "bm25_candidates": timing.get("bm25_candidates_count", 0),
                    "fused_candidates": timing.get("fused_candidates_count", 0),
                    "rerank_latency_ms": timing.get("rerank_ms", 0)
                }
            }
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

        # Log query to DB in background
        try:
            db_log: Session = SessionLocal()
            log_query(
                db=db_log,
                tenant_id=current_tenant.id,
                query_text=question,
                retrieval_latency_ms=retrieval_latency_ms,
                generation_latency_ms=generation_latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=cost_usd,
                chunks_retrieved_count=len(retrieved_chunks)
            )
            db_log.close()
        except Exception as e:
            print(f"[QueryLogging] Failed to log query: {e}")

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
