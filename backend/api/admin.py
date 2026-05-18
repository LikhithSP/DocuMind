"""Admin endpoints for managing Tenants and API Keys."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.repository import create_tenant_with_key, list_all_tenants

router = APIRouter(prefix="/admin", tags=["Admin"])

class CreateTenantRequest(BaseModel):
    name: str

class TenantResponse(BaseModel):
    id: str
    name: str
    created_at: str

class CreateTenantResponse(BaseModel):
    tenant: TenantResponse
    api_key: str
    note: str

@router.post("/tenants", response_model=CreateTenantResponse)
def create_tenant_endpoint(payload: CreateTenantRequest, db: Session = Depends(get_db)):
    """Creates a new tenant and generates their initial raw API key.
    The raw API key is displayed once upon creation and hashed in the database.
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tenant name cannot be empty.")
        
    tenant, raw_key = create_tenant_with_key(db, name)
    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "created_at": tenant.created_at.isoformat()
        },
        "api_key": raw_key,
        "note": "Save this API key securely. It maps directly to your tenant ID and is not stored in plaintext."
    }

@router.get("/tenants")
def list_tenants_endpoint(db: Session = Depends(get_db)):
    """Lists all tenants in the system."""
    tenants = list_all_tenants(db)
    return {
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "created_at": t.created_at.isoformat()
            }
            for t in tenants
        ]
    }
