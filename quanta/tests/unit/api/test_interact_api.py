from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_interact_missing_headers():
    response = client.post("/api/v1/interact", json={"text": "Hello"})
    assert response.status_code == 401


def test_interact_valid_headers():
    response = client.post(
        "/api/v1/interact",
        json={"text": "Hello Quanta"},
        headers={"X-User-ID": "user_123", "X-Session-ID": "session_456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "request_id" in data
