"""Cookie-backed admin auth.

The cookie holds the literal ADMIN_API_KEY. We never trust it; on every
request we constant-time compare against settings.admin_api_key. So even
if a forged cookie shows up, it just won't match.

The cookie is httponly + samesite=lax + secure (in prod). It does not need
to survive a key rotation — when the admin rotates their key, all old
cookies stop verifying naturally.
"""
import hmac
from typing import Annotated

from fastapi import Cookie, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from backend.core.config import settings

COOKIE_NAME = "kib_admin"


def is_authenticated(token: str | None) -> bool:
    if not settings.admin_api_key or not token:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"),
        settings.admin_api_key.encode("utf-8"),
    )


def require_admin_session(
    request: Request,
    kib_admin: Annotated[str | None, Cookie()] = None,
) -> None:
    """Use as a dependency on every protected admin route."""
    if is_authenticated(kib_admin):
        return
    # HTMX requests get a 401 with HX-Redirect so the client navigates;
    # plain GET requests get a 302 to /admin/login.
    if request.headers.get("HX-Request"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"HX-Redirect": "/admin/login"},
        )
    # For non-HTMX requests, raise a redirect via custom status. FastAPI doesn't
    # let dependencies return responses, so we throw HTTPException with a 303
    # and the route's exception handler turns it into a Location redirect.
    # Simpler: raise 401 and let a global handler in routes.py handle it.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not_authenticated",
    )


def login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
