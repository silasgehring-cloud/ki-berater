"""Admin UI — server-rendered Jinja2 templates + HTMX.

Mounts under /admin/. Single-user owner-admin auth: anyone holding
ADMIN_API_KEY can log in via the cookie-backed session.

The HTML side reuses the Klarmacher design tokens (warm off-white,
charcoal, sage). Templates live in backend/admin/templates/, static
assets in backend/admin/static/.
"""
from backend.admin.routes import router as admin_router

__all__ = ["admin_router"]
