from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LogsQueryRequest(BaseModel):
    logql: str = Field(min_length=3)
    start_utc: datetime
    end_utc: datetime
    group_by_host_ip: bool = False


class LogsQueryResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: int

