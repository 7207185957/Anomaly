from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.config import get_settings
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.incidents import IncidentSummaryRequest, IncidentsRequest
from app.services.demo_data_service import DemoDataService
from app.services.llm_service import LlmService


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

    @staticmethod
    def _as_str_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalized_incident(incident: dict[str, Any]) -> dict[str, Any]:
        return {
            "incident_id": IncidentsService._as_str_or_none(
                incident.get("incident_id") or incident.get("incidentnumber") or incident.get("id")
            ),
            "title": incident.get("title") or incident.get("entitydisplayname") or "Incident",
            "description": incident.get("description") or incident.get("details") or "",
            "severity": incident.get("severity") or "unknown",
            "status": incident.get("status") or incident.get("entitystate") or "open",
            "service_impacted": incident.get("service_impacted") or incident.get("service") or "unknown",
            "start_time": incident.get("start_time") or incident.get("starttime"),
            "end_time": incident.get("end_time") or incident.get("endtime"),
            "team_name": incident.get("team_name") or incident.get("team"),
        }

    @staticmethod
    def _heuristic_summary(incident: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
        title = str(incident.get("title") or "Incident")
        sev = str(incident.get("severity") or "unknown")
        status = str(incident.get("status") or "open")
        svc = str(incident.get("service_impacted") or "unknown")
        desc = str(incident.get("description") or "").strip()
        keyword = str(context.get("keyword") or "").strip()

        incident_summary = (
            f"{title} impacted service '{svc}' with severity '{sev}' and current status '{status}'. "
            f"{desc if desc else 'Detailed incident description is limited.'}"
        )
        probable_cause = (
            "Most probable cause: insufficient evidence in incident payload; "
            "likely tied to recent runtime changes, anomaly spikes, or dependency saturation."
        )
        recommended_fix = (
            "Recommended fix: triage recent deployments/config changes, check affected service logs and queue depth, "
            "validate recovery with health/failure trend for the impacted scope."
        )
        executive_summary = (
            f"Incident Summary:\n{incident_summary}\n\n"
            f"Most Probable Cause:\n{probable_cause}\n\n"
            f"Recommended Fix:\n{recommended_fix}"
        )
        if keyword:
            executive_summary += f"\n\nScope keyword considered: {keyword}"
        return {
            "executive_summary": executive_summary,
            "incident_summary": incident_summary,
            "probable_cause": probable_cause,
            "recommended_fix": recommended_fix,
        }

    def summarize_incident(self, req: IncidentSummaryRequest) -> dict[str, Any]:
        normalized = self._normalized_incident(req.incident)
        sections = self._heuristic_summary(normalized, req.context)
        generated_by = "heuristic"

        if not self.settings.demo_mode:
            try:
                llm = LlmService()
                llm_sections = llm.generate_incident_executive_summary(
                    incident=normalized,
                    context=req.context,
                )
                # Merge model output with safe fallback defaults.
                sections = {
                    "executive_summary": llm_sections.get("executive_summary") or sections["executive_summary"],
                    "incident_summary": llm_sections.get("incident_summary") or sections["incident_summary"],
                    "probable_cause": llm_sections.get("probable_cause") or sections["probable_cause"],
                    "recommended_fix": llm_sections.get("recommended_fix") or sections["recommended_fix"],
                }
                generated_by = "llm"
            except Exception:
                generated_by = "heuristic"

        return {
            "incident_id": normalized.get("incident_id"),
            "title": str(normalized.get("title") or "Incident"),
            "executive_summary": sections["executive_summary"],
            "incident_summary": sections["incident_summary"],
            "probable_cause": sections["probable_cause"],
            "recommended_fix": sections["recommended_fix"],
            "generated_by": generated_by,
        }

