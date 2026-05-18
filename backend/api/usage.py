"""Usage and cost metrics endpoint.
TICKET-602:
GET /usage returns aggregate query count, total tokens, average latencies, and estimated USD cost.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Tenant
from backend.db.repository import get_tenant_usage_summary
from backend.security.auth import get_current_tenant

router = APIRouter(prefix="/usage", tags=["Usage"])

@router.get("")
def get_usage_metrics(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns aggregated query counts, latency profiles, token consumption, and cost estimates."""
    summary = get_tenant_usage_summary(db, current_tenant.id)
    summary["tenant_name"] = current_tenant.name
    return summary
