"""Admin-only member management."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from ..db import get_db
from ..deps import require_admin
from ..queries import members as members_q
from ..security import hash_password
from ..web import redirect, render

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def _get_or_404(conn, member_id):
    member = members_q.get_by_id(conn, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/members")
def manage_members(request: Request, conn=Depends(get_db)):
    return render(request, "admin/members_list.html",
                  {"members": members_q.list_all(conn)})


@router.get("/members/new")
def new_member_page(request: Request):
    return render(request, "admin/member_form.html", {"member": None})


@router.post("/members/new")
def new_member_submit(request: Request, conn=Depends(get_db),
                      name: str = Form(""), email: str = Form(""),
                      password: str = Form(""), business_name: str = Form(""),
                      category: str = Form(""), phone: str = Form(""),
                      is_admin: str = Form("")):
    name, email = name.strip(), email.strip()
    error = None
    if not name or not email:
        error = "Name and email are required."
    elif len(password) < 8:
        error = "Temporary password must be at least 8 characters."
    if error:
        return render(request, "admin/member_form.html",
                      {"member": None, "error": error}, status_code=400)
    try:
        members_q.create(conn, name, email, hash_password(password),
                         business_name.strip(), category.strip(), phone.strip(),
                         is_admin=1 if is_admin else 0)
    except sqlite3.IntegrityError:
        return render(request, "admin/member_form.html",
                      {"member": None, "error": "A member with that email already exists."},
                      status_code=400)
    return redirect(request, "/admin/members", flash=f"Member {name} created.")


@router.get("/members/{member_id}/edit")
def edit_member_page(request: Request, member_id: int, conn=Depends(get_db)):
    member = _get_or_404(conn, member_id)
    return render(request, "admin/member_form.html", {"member": member})


@router.post("/members/{member_id}/edit")
def edit_member_submit(request: Request, member_id: int, conn=Depends(get_db),
                       name: str = Form(""), email: str = Form(""),
                       business_name: str = Form(""), category: str = Form(""),
                       phone: str = Form(""), scheduling_url: str = Form(""),
                       is_admin: str = Form("")):
    member = _get_or_404(conn, member_id)
    name, email = name.strip(), email.strip()
    if not name or not email:
        return render(request, "admin/member_form.html",
                      {"member": member, "error": "Name and email are required."},
                      status_code=400)
    try:
        members_q.admin_update(conn, member_id, name, email, business_name.strip(),
                               category.strip(), phone.strip(), scheduling_url.strip(),
                               1 if is_admin else 0)
    except sqlite3.IntegrityError:
        return render(request, "admin/member_form.html",
                      {"member": member, "error": "A member with that email already exists."},
                      status_code=400)
    return redirect(request, "/admin/members", flash=f"Member {name} updated.")


@router.post("/members/{member_id}/deactivate")
def deactivate_member(request: Request, member_id: int, conn=Depends(get_db),
                      admin=Depends(require_admin)):
    member = _get_or_404(conn, member_id)
    if member["id"] == admin["id"]:
        return redirect(request, "/admin/members",
                        flash="You cannot deactivate your own account.", category="error")
    members_q.set_active(conn, member_id, False)
    return redirect(request, "/admin/members", flash=f"{member['name']} deactivated.")


@router.post("/members/{member_id}/activate")
def activate_member(request: Request, member_id: int, conn=Depends(get_db)):
    member = _get_or_404(conn, member_id)
    members_q.set_active(conn, member_id, True)
    return redirect(request, "/admin/members", flash=f"{member['name']} reactivated.")


@router.post("/members/{member_id}/reset-password")
def reset_password(request: Request, member_id: int, conn=Depends(get_db),
                   password: str = Form("")):
    member = _get_or_404(conn, member_id)
    if len(password) < 8:
        return redirect(request, "/admin/members",
                        flash="Temporary password must be at least 8 characters.",
                        category="error")
    members_q.set_password(conn, member_id, hash_password(password))
    return redirect(request, "/admin/members",
                    flash=f"Password reset for {member['name']}.")
