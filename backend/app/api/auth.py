from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth import auth_is_enabled, create_access_token, verify_access_token, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class AuthStatusResponse(BaseModel):
    auth_required: bool
    authenticated: bool
    username: str | None = None


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> AuthStatusResponse:
    if not auth_is_enabled():
        return AuthStatusResponse(auth_required=False, authenticated=True, username=None)
    if credentials:
        user = verify_access_token(credentials.credentials)
        if user:
            return AuthStatusResponse(auth_required=True, authenticated=True, username=user)
    return AuthStatusResponse(auth_required=True, authenticated=False, username=None)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    if not verify_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return LoginResponse(
        access_token=create_access_token(body.username),
        username=body.username,
    )
