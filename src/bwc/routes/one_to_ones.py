"""One-to-one meeting logging."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Form

from ..db import get_db
from ..deps import get_current_member
from ..queries import members as members_q
from ..queries import one_to_ones as o2o_q
from ..web import redirect, render

router = APIRouter(prefix="/one-to-ones", dependencies=[Depends(get_current_member)])


@router.get("")
def o2o_list(request: Request, conn=Depends(get_db),
             member=Depends(get_current_member), scope: str = "mine"):
    if scope not in ("mine", "all"):
        scope = "mine"
    rows = (o2o_q.list_for_member(conn, member["id"]) if scope == "mine"
            else o2o_q.list_all(conn))
    return render(request, "one_to_ones/list.html",
                  {"one_to_ones": rows, "scope": scope})


@router.get("/new")
def new_o2o_page(request: Request, conn=Depends(get_db),
                 member=Depends(get_current_member)):
    others = [m for m in members_q.list_active(conn) if m["id"] != member["id"]]
    return render(request, "one_to_ones/form.html",
                  {"others": others, "today": date.today().isoformat()})


@router.post("/new")
def new_o2o_submit(request: Request, conn=Depends(get_db),
                   member=Depends(get_current_member),
                   other_id: int = Form(...), met_on: str = Form(""),
                   location: str = Form(""), notes: str = Form("")):
    other = members_q.get_by_id(conn, other_id)
    if other is None or not other["is_active"] or other_id == member["id"]:
        others = [m for m in members_q.list_active(conn) if m["id"] != member["id"]]
        return render(request, "one_to_ones/form.html",
                      {"others": others, "today": date.today().isoformat(),
                       "error": "Pick the member you met with."},
                      status_code=400)
    o2o_q.create(conn, member["id"], other_id,
                 met_on.strip() or date.today().isoformat(),
                 location.strip(), notes.strip(), member["id"])
    return redirect(request, "/one-to-ones",
                    flash=f"One-to-one with {other['name']} logged.")


@router.post("/{one_to_one_id}/delete")
def delete_o2o(request: Request, one_to_one_id: int, conn=Depends(get_db),
               member=Depends(get_current_member)):
    row = o2o_q.get(conn, one_to_one_id)
    if row is None:
        raise HTTPException(status_code=404, detail="One-to-one not found")
    allowed = member["is_admin"] or member["id"] in (row["member1_id"], row["member2_id"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Not your one-to-one")
    o2o_q.delete(conn, one_to_one_id)
    return redirect(request, "/one-to-ones", flash="One-to-one deleted.")
