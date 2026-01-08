from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class KeywordExtractRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


class KeywordExtractResponse(BaseModel):
    raw: str
    keywords: list[str]


class AIOpsSummaryRequest(BaseModel):
    keyword: str
    lookback_hours: int = 3
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None


class RCAReportRequest(BaseModel):
    incident_id: Optional[str] = None
    keyword: Optional[str] = None

    # override fields if you don't want DB lookup
    service_impacted: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

    # window passed through to AIOps backend
    lookback_hours: int = 3
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None

    include_aiops_combined: bool = True
    include_aiops_infra: bool = False
    include_aiops_app: bool = False


class RCAReportResponse(BaseModel):
    keyword: str
    incident_id: Optional[str] = None
    executive_summary: dict[str, Any]
    aiops: dict[str, Any] = Field(default_factory=dict)

