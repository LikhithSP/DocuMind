"""In-memory sliding window rate limiter per tenant."""
import time
from collections import defaultdict
from fastapi import HTTPException, status
from backend.config import settings

class SlidingWindowRateLimiter:
    def __init__(self):
        # Maps tenant_id -> list of timestamp floats
        self.query_history = defaultdict(list)
        self.upload_history = defaultdict(list)
        self.window_seconds = 60

    def check_query_limit(self, tenant_id: str):
        now = time.time()
        timestamps = self.query_history[tenant_id]
        # Prune older than window
        self.query_history[tenant_id] = [t for t in timestamps if now - t < self.window_seconds]
        
        if len(self.query_history[tenant_id]) >= settings.QUERY_RATE_LIMIT_PER_MINUTE:
            retry_after = int(self.window_seconds - (now - self.query_history[tenant_id][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Query rate limit exceeded ({settings.QUERY_RATE_LIMIT_PER_MINUTE}/min). Try again in {retry_after}s.",
                headers={"Retry-After": str(max(1, retry_after))}
            )
        self.query_history[tenant_id].append(now)

    def check_upload_limit(self, tenant_id: str):
        now = time.time()
        timestamps = self.upload_history[tenant_id]
        self.upload_history[tenant_id] = [t for t in timestamps if now - t < self.window_seconds]
        
        if len(self.upload_history[tenant_id]) >= settings.UPLOAD_RATE_LIMIT_PER_MINUTE:
            retry_after = int(self.window_seconds - (now - self.upload_history[tenant_id][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Upload rate limit exceeded ({settings.UPLOAD_RATE_LIMIT_PER_MINUTE}/min). Try again in {retry_after}s.",
                headers={"Retry-After": str(max(1, retry_after))}
            )
        self.upload_history[tenant_id].append(now)

rate_limiter = SlidingWindowRateLimiter()
