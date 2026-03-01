from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimeWindowRequest


class SummaryRequest(TimeWindowRequest):
    pass


class ComponentScore(BaseModel):
    health_score: int
    affected_metrics: list[dict[str, Any]]
    affected_metric_names: list[str]
    affected_instances: list[str]
    affected_instances_by_metric: dict[str, list[str]]


class CombinedSummaryResponse(BaseModel):
    keyword: str
    since_utc: datetime
    until_utc: datetime
    cluster_health: int
    severity_breakdown: dict[str, int]
    infra_only: dict[str, Any]
    app_only: dict[str, Any]
    health_failure_timeline: list[dict[str, Any]]
    incident_timeline: list[dict[str, Any]]
    app_log_error_count: int
    dag_log_error_count: int


class ClusterHealthResponse(BaseModel):
    keyword: str
    since_utc: datetime
    until_utc: datetime
    health_score: int
    infra_metrics: ComponentScore
    app_metrics: ComponentScore
    logs_metrics: ComponentScore
    counts: dict[str, Any]
    health_signature: dict[str, Any]
    health_failure_last: dict[str, Any] | None
    health_failure_timeline: list[dict[str, Any]]
    asset_health_timeline: list[dict[str, Any]] = []
    infra_only: dict[str, Any] = {}
    app_only: dict[str, Any] = {}

