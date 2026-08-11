"""TYFCB (Thank You For Closed Business) logging."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from ..db import get_db
from ..deps import get_current_member
from ..money import parse_dollars
from ..queries import members as members_q
from ..queries import referrals as referrals_q
from ..queries import tyfcb as tyfcb_q
from ..web import redirect, render

router = APIRouter(prefix="/tyfcb", dependencies=[Depends(get_current_member)])


@router.get("")
def tyfcb_list(request: Request, conn=Depends(get_db),
               member=Depends(get_current_member), tab: str = "given"):
    if tab not in ("given", "received"):
        tab = "given"
    rows = tyfcb_q.list_for_member(conn, member["id"], tab)
    total_cents = sum(r["amount_cents"] for r in rows)
    return render(request, "tyfcb/list.html",
                  {"entries": rows, "tab": tab, "total_cents": total_cents})


def _form_context(conn, member):
    others = [m for m in members_q.list_active(conn) if m["id"] != member["id"]]
    received = referrals_q.list_received(conn, member["id"])
    return {"others": others, "received_referrals": received,
            "today": date.today().isoformat()}


@router.get("/new")
def new_tyfcb_page(request: Request, conn=Depends(get_db),
                   member=Depends(get_current_member)):
    return render(request, "tyfcb/form.html", _form_context(conn, member))


@router.post("/new")
def new_tyfcb_submit(request: Request, conn=Depends(get_db),
                     member=Depends(get_current_member),
                     thanked_id: int = Form(...), amount: str = Form(""),
                     referral_id: str = Form(""), is_new_business: str = Form("1"),
                     notes: str = Form(""), tyfcb_date: str = Form("")):
    ctx = _form_context(conn, member)
    thanked = members_q.get_by_id(conn, thanked_id)
    error = None
    amount_cents = 0
    if thanked is None or not thanked["is_active"] or thanked_id == member["id"]:
        error = "Pick the member you are thanking."
    else:
        try:
            amount_cents = parse_dollars(amount)
        except ValueError as exc:
            error = str(exc)
    linked_id = None
    if not error and referral_id.strip():
        referral = referrals_q.get(conn, int(referral_id))
        if referral is None or referral["receiver_id"] != member["id"]:
            error = "That referral is not one you received."
        else:
            linked_id = referral["id"]
    if error:
        ctx["error"] = error
        return render(request, "tyfcb/form.html", ctx, status_code=400)
    tyfcb_q.create(conn, member["id"], thanked_id, amount_cents, linked_id,
                   1 if is_new_business == "1" else 0, notes.strip(),
                   tyfcb_date.strip() or date.today().isoformat())
    return redirect(request, "/tyfcb", flash=f"TYFCB recorded for {thanked['name']}.")


@router.post("/{tyfcb_id}/delete")
def delete_tyfcb(request: Request, tyfcb_id: int, conn=Depends(get_db),
                 member=Depends(get_current_member)):
    row = tyfcb_q.get(conn, tyfcb_id)
    if row is None:
        raise HTTPException(status_code=404, detail="TYFCB entry not found")
    if not (member["is_admin"] or member["id"] == row["thanker_id"]):
        raise HTTPException(status_code=403, detail="Only the reporter or an admin can delete")
    tyfcb_q.delete(conn, tyfcb_id)
    return redirect(request, "/tyfcb", flash="TYFCB entry deleted.")
