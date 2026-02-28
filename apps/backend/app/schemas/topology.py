from typing import Any

from pydantic import BaseModel, Field


class TopologyRequest(BaseModel):
    keyword: str
    region_filter: list[str] = Field(default_factory=list)
    structured: bool = True


class TopologyResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    stats: dict[str, int]

