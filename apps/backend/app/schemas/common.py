from datetime import datetime

from pydantic import BaseModel


class TimeWindowRequest(BaseModel):
    keyword: str
    lookback_hours: int = 3
    start_utc: datetime | None = None
    end_utc: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp_utc: datetime

