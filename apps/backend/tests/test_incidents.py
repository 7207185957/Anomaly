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

    def summarize_incident(self, req):  # noqa: ANN001
        incident = req.incident or {}
        title = str(incident.get("title") or "Synthetic incident")
        return {
            "incident_id": incident.get("incident_id", 394921),
            "title": title,
            "executive_summary": "Incident Summary:\nSynthetic incident",
            "incident_summary": f"{title} summary.",
            "probable_cause": "Synthetic cause.",
            "recommended_fix": "Synthetic fix.",
            "generated_by": "heuristic",
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


def test_summarize_incident_endpoint():
    app.dependency_overrides[deps.require_auth] = _fake_auth
    app.dependency_overrides[deps.get_incidents_service] = lambda: _FakeIncidentsService()
    client = TestClient(app)
    response = client.post(
        "/api/v1/incidents/summarize",
        json={
            "incident": {
                "incident_id": 394921,
                "title": "Synthetic incident",
                "severity": "high",
                "status": "open",
            },
            "context": {"keyword": "airflow"},
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "394921"
    assert "executive_summary" in payload
    assert payload["generated_by"] in {"heuristic", "llm"}

