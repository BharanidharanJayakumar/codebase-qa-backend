"""Rate limiting middleware using slowapi, keyed by user ID."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def _get_user_key(request: Request) -> str:
    """Extract user ID from auth header for rate limiting, fall back to IP."""
    # The auth middleware sets this attribute when user is authenticated
    user = getattr(request.state, "rate_limit_user", None)
    if user:
        return f"user:{user}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_key)

# Rate limit constants
GUEST_QUESTION_LIMIT = "10/day"
AUTH_QUESTION_LIMIT = "100/day"
GUEST_INDEX_LIMIT = "2/day"
AUTH_INDEX_LIMIT = "20/day"
