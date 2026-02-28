from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RcaJobRequest(BaseModel):
    keyword: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class JobSubmitResponse(BaseModel):
    job_id: str
    queue: str
    status: str
    submitted_at: datetime


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None

