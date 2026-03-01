from fastapi.testclient import TestClient

from app.api import deps
from app.main import app


class _FakeIncidentsService:
    def list_incidents(self, req):  # noqa: ANN001
        return {
            "team_name": req.team_name or "WCS-DataOps-Tier2",
            "keyword": req.keyword,
            "since_utc": "2026-01-01T00:00:00+00:00",
            "until_utc": "2026-01-01T01:00:00+00:00",
            "count": 1,
            "incidents": [
                {
                    "incident_id": "INC-1",
                    "title": "Synthetic incident",
                    "severity": "high",
                    "status": "open",
                    "service_impacted": "airflow",
                }
            ],
            "summary": {
                "status_breakdown": {"open": 1},
                "severity_breakdown": {"high": 1},
                "open_count": 1,
            },
        }


def _fake_auth():
    return deps.AuthContext(
        username="tester",
        display_name="Test User",
        groups=["Admins"],
        is_admin=True,
    )


def test_open_incidents_endpoint():
    app.dependency_overrides[deps.require_auth] = _fake_auth
    app.dependency_overrides[deps.get_incidents_service] = lambda: _FakeIncidentsService()
    client = TestClient(app)
    response = client.post(
        "/api/v1/incidents/open",
        json={"lookback_hours": 2, "team_name": "WCS-DataOps-Tier2"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["summary"]["open_count"] == 1
    assert payload["incidents"][0]["incident_id"] == "INC-1"

