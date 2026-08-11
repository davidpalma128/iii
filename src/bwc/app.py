"""FastAPI application factory for the BWC chapter tracker."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import CHAPTER_NAME, load_settings
from .db import init_db
from .deps import LoginRequired
from .money import format_cents
from .routes import admin, auth, dashboard, one_to_ones, referrals, tyfcb
from .routes import members as members_routes
from .web import login_redirect

PACKAGE_DIR = Path(__file__).parent


def _datefmt(value) -> str:
    """'2026-08-11' or full ISO timestamp -> 'Aug 11, 2026'."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return str(value)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def create_app(db_path=None, secret_key=None, cookie_secure=None) -> FastAPI:
    settings = load_settings(db_path, secret_key, cookie_secure)
    init_db(settings.db_path)

    app = FastAPI(title=CHAPTER_NAME, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings

    from .security import CookieSigner

    app.state.signer = CookieSigner(settings.secret_key)

    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    templates.env.filters["money"] = format_cents
    templates.env.filters["datefmt"] = _datefmt
    templates.env.globals["chapter_name"] = CHAPTER_NAME
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        return login_redirect(exc.next_path)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(members_routes.router)
    app.include_router(admin.router)
    app.include_router(referrals.router)
    app.include_router(one_to_ones.router)
    app.include_router(tyfcb.router)
    return app
