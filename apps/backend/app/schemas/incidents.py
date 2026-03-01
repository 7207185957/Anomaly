from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class IncidentsRequest(BaseModel):
    team_name: str | None = None
    keyword: str | None = None
    include_resolved: bool = False
    lookback_hours: int | None = Field(default=None, ge=1, le=168)
    start_utc: datetime | None = None
    end_utc: datetime | None = None


class IncidentsResponse(BaseModel):
    team_name: str | None
    keyword: str | None
    since_utc: datetime | None = None
    until_utc: datetime | None = None
    count: int
    incidents: list[dict[str, Any]]
    summary: dict[str, Any]
    generated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

