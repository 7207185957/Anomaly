from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthContext, get_summary_service, require_auth
from app.schemas.summary import SummaryRequest
from app.services.summary_service import SummaryService

router = APIRouter(prefix="", tags=["summary"])


@router.post("/summaries/combined")
def summarize_combined(
    req: SummaryRequest,
    _: AuthContext = Depends(require_auth),
    service: SummaryService = Depends(get_summary_service),
):
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword required")
    return service.get_combined_summary(req)


@router.post("/cluster/health")
def cluster_health(
    req: SummaryRequest,
    _: AuthContext = Depends(require_auth),
    service: SummaryService = Depends(get_summary_service),
):
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword required")
    return service.get_cluster_health(req)

