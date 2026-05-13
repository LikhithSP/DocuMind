"""Authentication and tenant context derivation from X-API-Key header.
TICKET-401: All document/query endpoints derive tenant_id strictly from authenticated key.
Tenant ID is NEVER accepted as a client-supplied parameter.
"""
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Tenant
from backend.db.repository import get_tenant_by_api_key

def get_current_tenant(
    x_api_key: str = Header(..., alias="X-API-Key", description="Tenant API Key"),
    db: Session = Depends(get_db)
) -> Tenant:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via 'X-API-Key' header."
        )
    
    tenant = get_tenant_by_api_key(db, x_api_key)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key."
        )
    return tenant
