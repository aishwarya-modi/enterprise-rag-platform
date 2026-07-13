from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_tenant_endpoint() -> None:
    response = client.post(
        "/api/v1/tenants",
        json={"name": "Acme Corp", "slug": "acme-corp"},
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "acme-corp"
