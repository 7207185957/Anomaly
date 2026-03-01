from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthContext, get_nebula_service, require_auth
from app.core.config import get_settings
from app.schemas.topology import TopologyRequest, TopologyResponse
from app.services.demo_data_service import DemoDataService
from app.services.nebula_service import NebulaService

router = APIRouter(prefix="/topology", tags=["topology"])


@router.post("/graph", response_model=TopologyResponse)
def get_topology(
    req: TopologyRequest,
    _: AuthContext = Depends(require_auth),
    service: NebulaService = Depends(get_nebula_service),
) -> TopologyResponse:
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword required")
    settings = get_settings()
    if settings.demo_mode:
        data = DemoDataService().topology_graph(keyword, req.region_filter)
        return TopologyResponse(**data)
    data = service.topology_for_keyword(keyword, req.region_filter)
    return TopologyResponse(**data)

