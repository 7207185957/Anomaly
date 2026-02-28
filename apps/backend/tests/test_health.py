from fastapi.testclient import TestClient

from app.main import app


def test_live_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp_utc" in payload

