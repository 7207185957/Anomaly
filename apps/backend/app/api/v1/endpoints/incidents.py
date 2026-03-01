from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, get_incidents_service, require_auth
from app.schemas.incidents import (
    IncidentSummaryRequest,
    IncidentSummaryResponse,
    IncidentsRequest,
    IncidentsResponse,
)
from app.services.incidents_service import IncidentsService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/open", response_model=IncidentsResponse)
def list_open_incidents(
    req: IncidentsRequest,
    _: AuthContext = Depends(require_auth),
    service: IncidentsService = Depends(get_incidents_service),
) -> IncidentsResponse:
    payload = service.list_incidents(req)
    return IncidentsResponse(**payload)


@router.post("/summarize", response_model=IncidentSummaryResponse)
def summarize_incident(
    req: IncidentSummaryRequest,
    _: AuthContext = Depends(require_auth),
    service: IncidentsService = Depends(get_incidents_service),
) -> IncidentSummaryResponse:
    payload = service.summarize_incident(req)
    return IncidentSummaryResponse(**payload)

