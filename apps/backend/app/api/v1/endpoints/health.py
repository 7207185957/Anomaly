from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok", timestamp_utc=datetime.now(timezone.utc))


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    return HealthResponse(status="ready", timestamp_utc=datetime.now(timezone.utc))

