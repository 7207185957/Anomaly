from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthContext, get_auth_service, require_auth
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.services.ldap_service import LdapAuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, auth_service: LdapAuthService = Depends(get_auth_service)) -> LoginResponse:
    try:
        user = auth_service.authenticate(payload.username, payload.password)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"LDAP authentication failed: {exc}")
    token = create_access_token(
        subject=user.username,
        extra_claims={"display_name": user.display_name, "groups": user.groups},
    )
    return LoginResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
        groups=user.groups,
    )


@router.get("/me", response_model=UserInfo)
def me(ctx: AuthContext = Depends(require_auth)) -> UserInfo:
    return UserInfo(
        username=ctx.username,
        display_name=ctx.display_name,
        groups=ctx.groups,
        is_admin=ctx.is_admin,
    )

