"""Request dependencies: current member resolution and admin gating."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .db import get_db
from .queries import members as members_q
from .security import SESSION_COOKIE


class LoginRequired(Exception):
    """Raised when an anonymous/invalid session hits a protected page."""

    def __init__(self, next_path: str = "/"):
        self.next_path = next_path


def get_current_member(request: Request, conn=Depends(get_db)):
    signer = request.app.state.signer
    uid = signer.read_session(request.cookies.get(SESSION_COOKIE, ""))
    member = members_q.get_by_id(conn, uid) if uid else None
    if member is None or not member["is_active"]:
        raise LoginRequired(request.url.path)
    request.state.member = member
    return member


def require_admin(member=Depends(get_current_member)):
    if not member["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return member
