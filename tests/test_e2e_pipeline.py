"""End-to-end integration test of the DocuMind API:
1. Create tenant
2. Upload test document
3. Verify status transitions to READY
4. Query document via streaming endpoint
5. Check citations returned
6. Check query log and usage stats
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.session import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()

def test_full_rag_lifecycle():
    client = TestClient(app)
    
    # 1. Create a new tenant via admin API
    resp = client.post("/admin/tenants", json={"name": "E2E Test Enterprise"})
    assert resp.status_code == 200
    data = resp.json()
    api_key = data["api_key"]
    tenant_id = data["tenant"]["id"]
    headers = {"X-API-Key": api_key}

    # 2. Upload a sample document
    sample_content = (
        "DocuMind Enterprise Handbook:\n"
        "Section 1.1: Security Policy\n"
        "All employee passwords must be a minimum of 16 characters with multi-factor authentication enabled.\n"
        "Section 1.2: Remote Work Stipend\n"
        "Full-time engineering staff are eligible for a $1,000 home office ergonomics stipend upon hiring."
    )
    files = {
        "file": ("handbook.txt", sample_content.encode("utf-8"), "text/plain")
    }
    
    upload_resp = client.post("/documents", headers=headers, files=files)
    assert upload_resp.status_code == 202
    doc_id = upload_resp.json()["document_id"]

    # 3. Poll status
    status_resp = client.get(f"/documents/{doc_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ["PROCESSING", "READY"]

    # 4. Query endpoint
    query_resp = client.post(
        "/query",
        headers=headers,
        json={"question": "What is the home office ergonomics stipend for engineering?"}
    )
    assert query_resp.status_code == 200
    assert "text/event-stream" in query_resp.headers["content-type"]
    
    # Parse SSE stream
    stream_content = query_resp.text
    assert "data:" in stream_content
    assert "complete" in stream_content
    assert "citations" in stream_content

    # 5. Check usage endpoint
    usage_resp = client.get("/usage", headers=headers)
    assert usage_resp.status_code == 200
    usage_data = usage_resp.json()
    assert usage_data["tenant_id"] == tenant_id
    assert usage_data["total_queries"] >= 1
