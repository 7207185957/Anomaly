from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthContext, get_loki_service, require_auth
from app.core.config import get_settings
from app.schemas.logs import LogsQueryRequest, LogsQueryResponse
from app.services.demo_data_service import DemoDataService
from app.services.loki_service import LokiService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/query", response_model=LogsQueryResponse)
def query_logs(
    req: LogsQueryRequest,
    _: AuthContext = Depends(require_auth),
    service: LokiService = Depends(get_loki_service),
) -> LogsQueryResponse:
    if req.end_utc <= req.start_utc:
        raise HTTPException(status_code=400, detail="end_utc must be greater than start_utc")
    start = req.start_utc.astimezone(timezone.utc)
    end = req.end_utc.astimezone(timezone.utc)
    settings = get_settings()
    if settings.demo_mode:
        demo = DemoDataService()
        data = demo.query_logs(
            keyword="demo",
            start=start,
            end=end,
            group_by_host_ip=req.group_by_host_ip,
        )
        return LogsQueryResponse(rows=data["rows"], total=int(data["total"]))

    if req.group_by_host_ip:
        grouped = service.query_count_per_minute_by_host_ip(logql=req.logql, start_dt=start, end_dt=end)
        rows = [
            {
                "host_ip": host_ip,
                "minute_counts": {k.isoformat(): v for k, v in mm.items()},
            }
            for host_ip, mm in grouped.items()
        ]
        return LogsQueryResponse(rows=rows, total=len(rows))
    raw = service.query_raw_logs(logql=req.logql, start_dt=start, end_dt=end)
    return LogsQueryResponse(rows=raw, total=len(raw))

