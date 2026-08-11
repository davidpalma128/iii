"""Login, logout, and change-password routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request

from ..db import get_db
from ..deps import get_current_member
from ..queries import members as members_q
from ..security import SESSION_COOKIE, SESSION_MAX_AGE, hash_password, verify_password
from ..web import redirect, render

router = APIRouter()


def _safe_next(next_path: str) -> str:
    # Only same-site absolute paths — no scheme/host redirects.
    if next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/"


@router.get("/login")
def login_page(request: Request, next: str = "/"):
    return render(request, "login.html", {"next": _safe_next(next)})


@router.post("/login")
def login_submit(request: Request, conn=Depends(get_db),
                 email: str = Form(""), password: str = Form(""), next: str = Form("/")):
    member = members_q.get_by_email(conn, email.strip())
    if member is None or not verify_password(password, member["password_hash"]):
        return render(request, "login.html",
                      {"error": "Invalid email or password.", "next": _safe_next(next)},
                      status_code=401)
    if not member["is_active"]:
        return render(request, "login.html",
                      {"error": "This account has been deactivated.", "next": _safe_next(next)},
                      status_code=403)
    response = redirect(request, _safe_next(next))
    response.set_cookie(
        SESSION_COOKIE,
        request.app.state.signer.make_session(member["id"]),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.cookie_secure,
    )
    return response


@router.post("/logout")
def logout(request: Request):
    response = redirect(request, "/login", flash="You have been logged out.")
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/password")
def password_page(request: Request, member=Depends(get_current_member)):
    return render(request, "password.html")


@router.post("/password")
def password_submit(request: Request, conn=Depends(get_db),
                    member=Depends(get_current_member),
                    current_password: str = Form(""), new_password: str = Form(""),
                    confirm_password: str = Form("")):
    if not verify_password(current_password, member["password_hash"]):
        return render(request, "password.html",
                      {"error": "Current password is incorrect."}, status_code=400)
    if len(new_password) < 8:
        return render(request, "password.html",
                      {"error": "New password must be at least 8 characters."},
                      status_code=400)
    if new_password != confirm_password:
        return render(request, "password.html",
                      {"error": "New passwords do not match."}, status_code=400)
    members_q.set_password(conn, member["id"], hash_password(new_password))
    return redirect(request, "/", flash="Password updated.")
