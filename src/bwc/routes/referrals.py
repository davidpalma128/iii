"""Referral CRUD, detail thread, and status updates."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from ..db import get_db
from ..deps import get_current_member
from ..queries import members as members_q
from ..queries import referrals as referrals_q
from ..web import redirect, render

router = APIRouter(prefix="/referrals", dependencies=[Depends(get_current_member)])


def _get_or_404(conn, referral_id):
    referral = referrals_q.get(conn, referral_id)
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral not found")
    return referral


def _can_view(referral, member) -> bool:
    return member["is_admin"] or member["id"] in (referral["giver_id"], referral["receiver_id"])


@router.get("")
def referral_list(request: Request, conn=Depends(get_db),
                  member=Depends(get_current_member),
                  tab: str = "given", status: str = ""):
    if tab not in ("given", "received"):
        tab = "given"
    if status not in referrals_q.STATUSES:
        status = ""
    rows = referrals_q.list_for_member(conn, member["id"], tab, status or None)
    return render(request, "referrals/list.html",
                  {"referrals": rows, "tab": tab, "status": status,
                   "statuses": referrals_q.STATUSES,
                   "status_labels": referrals_q.STATUS_LABELS})


@router.get("/new")
def new_referral_page(request: Request, conn=Depends(get_db),
                      member=Depends(get_current_member)):
    others = [m for m in members_q.list_active(conn) if m["id"] != member["id"]]
    return render(request, "referrals/form.html",
                  {"others": others, "today": date.today().isoformat()})


@router.post("/new")
def new_referral_submit(request: Request, conn=Depends(get_db),
                        member=Depends(get_current_member),
                        receiver_id: int = Form(...), contact_name: str = Form(""),
                        contact_info: str = Form(""), notes: str = Form(""),
                        referral_type: str = Form("outside"),
                        temperature: str = Form("warm"),
                        referral_date: str = Form("")):
    others = [m for m in members_q.list_active(conn) if m["id"] != member["id"]]
    ctx = {"others": others, "today": date.today().isoformat()}
    error = None
    receiver = members_q.get_by_id(conn, receiver_id)
    if receiver is None or not receiver["is_active"] or receiver_id == member["id"]:
        error = "Pick a member to receive the referral."
    elif not contact_name.strip():
        error = "The referred contact's name is required."
    elif referral_type not in referrals_q.TYPES or temperature not in referrals_q.TEMPERATURES:
        error = "Invalid referral type or temperature."
    if error:
        ctx["error"] = error
        return render(request, "referrals/form.html", ctx, status_code=400)
    referral_id = referrals_q.create(
        conn, member["id"], receiver_id, contact_name.strip(), contact_info.strip(),
        notes.strip(), referral_type, temperature,
        referral_date.strip() or date.today().isoformat(),
    )
    return redirect(request, f"/referrals/{referral_id}",
                    flash=f"Referral passed to {receiver['name']}.")


@router.get("/{referral_id}")
def referral_detail(request: Request, referral_id: int, conn=Depends(get_db),
                    member=Depends(get_current_member)):
    referral = _get_or_404(conn, referral_id)
    if not _can_view(referral, member):
        raise HTTPException(status_code=403, detail="Not your referral")
    updates = referrals_q.list_updates(conn, referral_id)
    return render(request, "referrals/detail.html",
                  {"referral": referral, "updates": updates,
                   "statuses": referrals_q.STATUSES,
                   "status_labels": referrals_q.STATUS_LABELS})


@router.post("/{referral_id}/updates")
def add_update(request: Request, referral_id: int, conn=Depends(get_db),
               member=Depends(get_current_member),
               note: str = Form(""), new_status: str = Form("")):
    referral = _get_or_404(conn, referral_id)
    if not _can_view(referral, member):
        raise HTTPException(status_code=403, detail="Not your referral")
    note = note.strip()
    new_status = new_status.strip() or None
    if new_status is not None and new_status not in referrals_q.STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if new_status == referral["status"]:
        new_status = None  # no-op status keeps the thread honest
    if not note and new_status is None:
        return redirect(request, f"/referrals/{referral_id}",
                        flash="Add a note or pick a new status.", category="error")
    referrals_q.add_update(conn, referral_id, member["id"], note, new_status)
    return redirect(request, f"/referrals/{referral_id}", flash="Update added.")


@router.post("/{referral_id}/delete")
def delete_referral(request: Request, referral_id: int, conn=Depends(get_db),
                    member=Depends(get_current_member)):
    referral = _get_or_404(conn, referral_id)
    if not (member["is_admin"] or member["id"] == referral["giver_id"]):
        raise HTTPException(status_code=403, detail="Only the giver or an admin can delete")
    referrals_q.delete(conn, referral_id)
    return redirect(request, "/referrals", flash="Referral deleted.")
