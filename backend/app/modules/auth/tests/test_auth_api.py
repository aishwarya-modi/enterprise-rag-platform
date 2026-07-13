from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_endpoint_returns_tokens() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!", "tenant_id": "tenant-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"


def test_refresh_token_endpoint_returns_new_access_token() -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!", "tenant_id": "tenant-1"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]


def test_logout_blacklists_refresh_token() -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!", "tenant_id": "tenant-1"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 200

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_google_oauth_creates_tokens_for_new_user() -> None:
    response = client.post(
        "/api/v1/auth/google",
        json={
            "id_token": "google-test-token",
            "email": "oauth@example.com",
            "tenant_id": "tenant-2",
            "organization_id": "org-2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]


def test_admin_endpoint_requires_admin_role() -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Password123!", "tenant_id": "tenant-1"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/admin",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
