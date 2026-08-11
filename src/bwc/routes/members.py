"""Member directory, profiles, and own-profile editing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from ..db import get_db
from ..deps import get_current_member
from ..queries import members as members_q
from ..queries import stats as stats_q
from ..web import redirect, render

router = APIRouter(dependencies=[Depends(get_current_member)])


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


@router.get("/members")
def member_list(request: Request, conn=Depends(get_db), q: str = ""):
    rows = members_q.list_active(conn, q.strip() or None)
    return render(request, "members/list.html", {"members": rows, "q": q.strip()})


@router.get("/members/{member_id}")
def member_detail(request: Request, member_id: int, conn=Depends(get_db)):
    member = members_q.get_by_id(conn, member_id)
    if member is None or not member["is_active"]:
        raise HTTPException(status_code=404, detail="Member not found")
    stats = stats_q.single_member(conn, member_id)
    return render(request, "members/detail.html", {"member": member, "stats": stats})


@router.get("/profile")
def profile_page(request: Request, member=Depends(get_current_member)):
    return render(request, "members/profile_form.html", {"member": member})


@router.post("/profile")
def profile_submit(request: Request, conn=Depends(get_db),
                   member=Depends(get_current_member),
                   name: str = Form(""), business_name: str = Form(""),
                   category: str = Form(""), phone: str = Form(""),
                   scheduling_url: str = Form("")):
    name = name.strip()
    if not name:
        return render(request, "members/profile_form.html",
                      {"member": member, "error": "Name is required."}, status_code=400)
    members_q.update_profile(conn, member["id"], name, business_name.strip(),
                             category.strip(), phone.strip(), _clean_url(scheduling_url))
    return redirect(request, f"/members/{member['id']}", flash="Profile updated.")
