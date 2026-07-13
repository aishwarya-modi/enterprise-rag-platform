from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_document_endpoint() -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", b"pdf-bytes", "application/pdf")},
        data={"tenant_id": "tenant-1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
