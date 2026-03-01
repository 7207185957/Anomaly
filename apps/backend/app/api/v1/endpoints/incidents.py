from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, get_incidents_service, require_auth
from app.schemas.incidents import IncidentsRequest, IncidentsResponse
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

