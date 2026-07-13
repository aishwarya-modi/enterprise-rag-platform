from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_document_endpoint_returns_processing_status() -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", b"pdf-bytes", "application/pdf")},
        data={"tenant_id": "tenant-1", "content_type": "pdf"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["content_type"] == "pdf"


def test_upload_rejects_unsupported_content_type() -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.exe", b"exe-bytes", "application/octet-stream")},
        data={"tenant_id": "tenant-1", "content_type": "exe"},
    )
    assert response.status_code == 400


def test_duplicate_upload_returns_existing_document() -> None:
    first = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", b"pdf-bytes", "application/pdf")},
        data={"tenant_id": "tenant-1", "content_type": "pdf"},
    )
    second = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", b"pdf-bytes", "application/pdf")},
        data={"tenant_id": "tenant-1", "content_type": "pdf"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
