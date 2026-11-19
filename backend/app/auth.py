import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def auth_is_enabled() -> bool:
    """Return True when single-user credentials are configured."""
    return bool(settings.auth_username and settings.auth_password)


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time check against configured single-user credentials."""
    if not auth_is_enabled():
        return False
    user_ok = secrets.compare_digest(username.encode("utf-8"), settings.auth_username.encode("utf-8"))
    pass_ok = secrets.compare_digest(password.encode("utf-8"), settings.auth_password.encode("utf-8"))
    return user_ok and pass_ok


def create_access_token(username: str) -> str:
    """Create an HMAC-SHA256 signed bearer token."""
    payload = {
        "sub": username,
        "exp": int(time.time()) + settings.auth_token_ttl_seconds,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(settings.auth_secret.encode("utf-8"), b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify_access_token(token: str) -> str | None:
    """Validate token signature and expiry, returning the subject username or None."""
    try:
        b64, sig = token.split(".", 1)
    except ValueError:
        return None
    expected_sig = hmac.new(
        settings.auth_secret.encode("utf-8"), b64.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not secrets.compare_digest(sig, expected_sig):
        return None
    padding = "=" * (-len(b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(b64 + padding).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    sub = payload.get("sub")
    if not isinstance(sub, str) or not secrets.compare_digest(sub, settings.auth_username):
        return None
    return sub


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token: str | None = Query(default=None),
) -> str | None:
    """FastAPI dependency enforcing bearer/query token auth when enabled."""
    if not auth_is_enabled():
        return None
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = verify_access_token(raw_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
