from fastapi import APIRouter, Depends

from app.config import settings
from app.services.auth import AuthUser, get_optional_user

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    user: AuthUser | None = Depends(get_optional_user),
):
    return {
        "status": "ok",
        "auth_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "user": {
            "id": user.id,
            "email": user.email,
            "is_anonymous": user.is_anonymous,
        } if user else None,
    }
