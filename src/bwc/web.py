"""Rendering and redirect helpers shared by all routes."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse

from .security import FLASH_COOKIE


def render(request: Request, template_name: str, context=None, status_code: int = 200):
    ctx = dict(context or {})
    ctx["current_member"] = getattr(request.state, "member", None)
    signer = request.app.state.signer
    flash = signer.read_flash(request.cookies.get(FLASH_COOKIE, ""))
    ctx["flash"] = flash
    response = request.app.state.templates.TemplateResponse(
        request, template_name, ctx, status_code=status_code
    )
    if flash:
        response.delete_cookie(FLASH_COOKIE)
    return response


def redirect(request: Request, url: str, flash=None, category: str = "success"):
    response = RedirectResponse(url, status_code=303)
    if flash:
        response.set_cookie(
            FLASH_COOKIE,
            request.app.state.signer.make_flash(flash, category),
            max_age=60,
            httponly=True,
            samesite="lax",
            secure=request.app.state.settings.cookie_secure,
        )
    return response


def login_redirect(next_path: str):
    return RedirectResponse(f"/login?next={quote(next_path, safe='/')}", status_code=303)
