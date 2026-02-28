from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=2)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str
    groups: list[str]


class UserInfo(BaseModel):
    username: str
    display_name: str
    groups: list[str]
    is_admin: bool

