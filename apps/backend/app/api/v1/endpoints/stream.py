import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import AuthContext, get_summary_service, require_auth
from app.schemas.summary import SummaryRequest
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/cluster-health")
async def stream_cluster_health(
    keyword: str = Query(..., min_length=1),
    lookback_hours: int = Query(3, ge=1, le=168),
    start_utc: datetime | None = None,
    end_utc: datetime | None = None,
    interval_seconds: int = Query(5, ge=2, le=60),
    _: AuthContext = Depends(require_auth),
    service: SummaryService = Depends(get_summary_service),
):
    async def gen():
        while True:
            req = SummaryRequest(
                keyword=keyword,
                lookback_hours=lookback_hours,
                start_utc=start_utc,
                end_utc=end_utc,
            )
            payload = service.get_cluster_health(req)
            yield "event: cluster_health\n"
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(gen(), media_type="text/event-stream")

