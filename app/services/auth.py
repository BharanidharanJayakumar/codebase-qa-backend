from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request

from app.services.supabase_client import get_supabase


@dataclass
class AuthUser:
    id: str
    email: str | None
    is_anonymous: bool


async def get_current_user(request: Request) -> AuthUser:
    """FastAPI dependency that extracts and verifies the Supabase JWT from the
    Authorization header. Returns the authenticated user or raises 401."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header[7:]
    try:
        supabase = get_supabase()
        resp = supabase.auth.get_user(token)
        user = resp.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return AuthUser(
            id=user.id,
            email=user.email,
            is_anonymous=user.is_anonymous or False,
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=401, detail=f"Auth failed: {str(e)}")


async def get_optional_user(request: Request) -> AuthUser | None:
    """Same as get_current_user but returns None instead of raising 401.
    Use for endpoints that work with or without auth."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
