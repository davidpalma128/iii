from datetime import date

from bwc.queries import one_to_ones as o2o_q
from bwc.queries import referrals as referrals_q
from bwc.queries import stats as stats_q
from bwc.queries import tyfcb as tyfcb_q

from .conftest import login

# Fixed reference day: Tuesday 2026-08-11 (ISO week starts Mon 2026-08-10).
TODAY = date(2026, 8, 11)


def test_period_start():
    assert stats_q.period_start("week", TODAY) == "2026-08-10"
    assert stats_q.period_start("month", TODAY) == "2026-08-01"
    assert stats_q.period_start("all", TODAY) is None


def seed_activity(conn, members):
    bob, carol, admin = members["bob"], members["carol"], members["admin"]
    # In-week, in-month, and prior-month activity.
    referrals_q.create(conn, bob, carol, "This Week", "", "", "outside", "hot", "2026-08-10")
    referrals_q.create(conn, bob, carol, "Earlier This Month", "", "", "outside", "warm", "2026-08-02")
    referrals_q.create(conn, carol, bob, "Last Month", "", "", "inside", "cold", "2026-07-15")
    o2o_q.create(conn, bob, carol, "2026-08-11", "Cafe", "", bob)
    o2o_q.create(conn, bob, admin, "2026-07-20", "Zoom", "", bob)
    tyfcb_q.create(conn, carol, bob, 100000, None, 1, "", "2026-08-10")
    tyfcb_q.create(conn, carol, bob, 50000, None, 0, "", "2026-07-01")


def rollup_for(conn, members, period):
    rows = stats_q.member_rollup(conn, period, TODAY)
    return {r["id"]: r for r in rows}


def test_week_vs_month_vs_all_counts(conn, members):
    seed_activity(conn, members)

    week = rollup_for(conn, members, "week")[members["bob"]]
    assert week["refs_given"] == 1
    assert week["refs_received"] == 0
    assert week["one_to_ones"] == 1
    assert week["tyfcb_received"] == 100000

    month = rollup_for(conn, members, "month")[members["bob"]]
    assert month["refs_given"] == 2
    assert month["one_to_ones"] == 1
    assert month["tyfcb_received"] == 100000

    alltime = rollup_for(conn, members, "all")[members["bob"]]
    assert alltime["refs_given"] == 2
    assert alltime["refs_received"] == 1
    assert alltime["one_to_ones"] == 2
    assert alltime["tyfcb_received"] == 150000


def test_chapter_totals_do_not_double_count_one_to_ones(conn, members):
    seed_activity(conn, members)
    rows = stats_q.member_rollup(conn, "all", TODAY)
    totals = stats_q.chapter_totals(rows)
    assert totals["refs_given"] == 3
    assert totals["one_to_ones"] == 2  # two meetings, four participant rows
    assert totals["tyfcb"] == 150000
    assert totals["members"] == 3


def test_leaderboard_ordering(conn, members):
    seed_activity(conn, members)
    by_refs = stats_q.leaderboard(conn, "refs_given", "all", TODAY)
    assert by_refs[0]["id"] == members["bob"]

    by_tyfcb_given = stats_q.leaderboard(conn, "tyfcb_given", "all", TODAY)
    assert by_tyfcb_given[0]["id"] == members["carol"]

    by_tyfcb_received = stats_q.leaderboard(conn, "tyfcb_received", "all", TODAY)
    assert by_tyfcb_received[0]["id"] == members["bob"]


def test_inactive_members_excluded_from_rollup(conn, members):
    from bwc.queries import members as members_q
    seed_activity(conn, members)
    members_q.set_active(conn, members["carol"], False)
    rows = stats_q.member_rollup(conn, "all", TODAY)
    assert members["carol"] not in {r["id"] for r in rows}


def test_dashboard_and_leaderboard_pages(client, conn, members):
    seed_activity(conn, members)
    login(client, "bob@example.com")

    dashboard = client.get("/?period=all")
    assert dashboard.status_code == 200
    assert "$1,500.00" in dashboard.text  # chapter TYFCB total
    assert "Recent activity" in dashboard.text

    leaderboard = client.get("/leaderboard?metric=tyfcb_received&period=all")
    assert leaderboard.status_code == 200
    assert "$1,500.00" in leaderboard.text

    bogus = client.get("/leaderboard?metric=nonsense&period=nonsense")
    assert bogus.status_code == 200
