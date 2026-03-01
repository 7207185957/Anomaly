from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.config import get_settings
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.incidents import IncidentsRequest
from app.services.demo_data_service import DemoDataService


class IncidentsService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = PostgresRepository()
        self.demo = DemoDataService()

    @staticmethod
    def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        phase_counter = Counter()
        severity_counter = Counter()
        for row in rows:
            phase = str(row.get("status") or row.get("currentphase") or "unknown").lower()
            severity = str(row.get("severity") or "unknown").lower()
            phase_counter[phase] += 1
            severity_counter[severity] += 1
        return {
            "status_breakdown": dict(phase_counter),
            "severity_breakdown": dict(severity_counter),
            "open_count": int(sum(v for k, v in phase_counter.items() if "resolve" not in k and "close" not in k)),
        }

    def list_incidents(self, req: IncidentsRequest) -> dict[str, Any]:
        # Incidents are intentionally independent of keyword/time controls.
        # This keeps incident command view stable even when dashboard filters change.
        since = None
        end_ts = None
        team_name = req.team_name or self.settings.incident_team_name

        if self.settings.demo_mode:
            rows = self.demo.list_incidents(
                team_name=team_name,
                keyword=None,
                since=since,
                end=end_ts,
                include_resolved=req.include_resolved,
            )
        else:
            rows = self.repo.fetch_open_incidents(
                team_name=team_name,
                keyword=None,
                since_ts=since,
                until_ts=end_ts,
                include_resolved=req.include_resolved,
            )

        return {
            "team_name": team_name,
            "keyword": None,
            "since_utc": since,
            "until_utc": end_ts,
            "count": len(rows),
            "incidents": rows,
            "summary": self._summary(rows),
        }

