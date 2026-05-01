"""Rate-limiting via slowapi.

Key strategy:
- Authenticated routes: by shop API key prefix (header X-Api-Key first 8 chars).
- Unauthenticated/admin: by remote IP fallback.

Storage backend: Redis if `REDIS_URL` is reachable, otherwise in-memory
(single-process only; fine for dev/CI). slowapi falls back automatically when
the URI is missing — we keep that behavior.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.config import settings


def _shop_or_ip_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key and len(api_key) >= 8:
        return f"shop:{api_key[:8]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_shop_or_ip_key,
    storage_uri=settings.rate_limit_storage_uri or None,
    default_limits=[settings.rate_limit_default],
)
