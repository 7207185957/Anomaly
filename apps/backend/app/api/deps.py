from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.services.ldap_service import LdapAuthService
from app.services.incidents_service import IncidentsService
from app.services.loki_service import LokiService
from app.services.nebula_service import NebulaService
from app.services.summary_service import SummaryService


security_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    username: str
    display_name: str
    groups: list[str]
    is_admin: bool


def get_auth_service() -> LdapAuthService:
    return LdapAuthService()


def get_summary_service() -> SummaryService:
    return SummaryService()


def get_loki_service() -> LokiService:
    return LokiService()


def get_nebula_service() -> NebulaService:
    return NebulaService()


def get_incidents_service() -> IncidentsService:
    return IncidentsService()


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthContext:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        claims = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    settings = get_settings()
    groups = list(claims.get("groups", []))
    is_admin = any(settings.ldap_admin_group_keyword.lower() in g.lower() for g in groups)
    return AuthContext(
        username=str(claims.get("sub", "")),
        display_name=str(claims.get("display_name", claims.get("sub", ""))),
        groups=groups,
        is_admin=is_admin,
    )

