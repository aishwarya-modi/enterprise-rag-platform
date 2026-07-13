from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_endpoint() -> None:
    response = client.post(
        "/api/v1/llm/chat",
        json={"tenant_id": "tenant-1", "provider": "openai", "prompt": "hello"},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "openai"
