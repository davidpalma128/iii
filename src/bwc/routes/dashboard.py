"""Chapter dashboard and leaderboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..db import get_db
from ..deps import get_current_member
from ..queries import stats as stats_q
from ..web import render

router = APIRouter(dependencies=[Depends(get_current_member)])


@router.get("/")
def dashboard(request: Request, conn=Depends(get_db),
              member=Depends(get_current_member), period: str = "week"):
    if period not in stats_q.PERIODS:
        period = "week"
    rows = stats_q.member_rollup(conn, period)
    totals = stats_q.chapter_totals(rows)
    mine = next((r for r in rows if r["id"] == member["id"]), None)
    activity = stats_q.recent_activity(conn)
    return render(request, "dashboard.html",
                  {"period": period, "periods": stats_q.PERIODS,
                   "totals": totals, "mine": mine, "activity": activity})


@router.get("/leaderboard")
def leaderboard(request: Request, conn=Depends(get_db),
                period: str = "all", metric: str = "refs_given"):
    if period not in stats_q.PERIODS:
        period = "all"
    if metric not in stats_q.METRICS:
        metric = "refs_given"
    rows = stats_q.leaderboard(conn, metric, period)
    return render(request, "leaderboard.html",
                  {"rows": rows, "period": period, "periods": stats_q.PERIODS,
                   "metric": metric, "metrics": stats_q.METRICS})
