"""Dashboard / leaderboard aggregates."""

from __future__ import annotations

from datetime import date, timedelta

PERIODS = ("week", "month", "all")

METRICS = {
    "refs_given": "Referrals given",
    "refs_received": "Referrals received",
    "one_to_ones": "One-to-ones",
    "tyfcb_received": "TYFCB received",
    "tyfcb_given": "TYFCB given",
}


def period_start(period, today=None):
    """ISO-date lower bound for a period, or None for all-time.

    'week' starts on the Monday of the current ISO week.
    """
    today = today or date.today()
    if period == "week":
        return (today - timedelta(days=today.weekday())).isoformat()
    if period == "month":
        return today.replace(day=1).isoformat()
    return None


_ROLLUP_SQL = """
    SELECT m.id, m.name, m.business_name,
      (SELECT COUNT(*) FROM referrals r
        WHERE r.giver_id = m.id AND (:start IS NULL OR r.referral_date >= :start))
        AS refs_given,
      (SELECT COUNT(*) FROM referrals r
        WHERE r.receiver_id = m.id AND (:start IS NULL OR r.referral_date >= :start))
        AS refs_received,
      (SELECT COUNT(*) FROM one_to_ones o
        WHERE (o.member1_id = m.id OR o.member2_id = m.id)
          AND (:start IS NULL OR o.met_on >= :start))
        AS one_to_ones,
      (SELECT COALESCE(SUM(t.amount_cents), 0) FROM tyfcb t
        WHERE t.thanked_id = m.id AND (:start IS NULL OR t.tyfcb_date >= :start))
        AS tyfcb_received,
      (SELECT COALESCE(SUM(t.amount_cents), 0) FROM tyfcb t
        WHERE t.thanker_id = m.id AND (:start IS NULL OR t.tyfcb_date >= :start))
        AS tyfcb_given
    FROM members m
    WHERE m.is_active = 1
"""


def member_rollup(conn, period="all", today=None):
    start = period_start(period, today)
    return conn.execute(
        _ROLLUP_SQL + " ORDER BY m.name COLLATE NOCASE", {"start": start}
    ).fetchall()


def single_member(conn, member_id, period="all", today=None):
    start = period_start(period, today)
    return conn.execute(
        _ROLLUP_SQL + " AND m.id = :member_id",
        {"start": start, "member_id": member_id},
    ).fetchone()


def chapter_totals(rows):
    """Sum a member_rollup result into chapter-wide totals.

    One-to-ones and inside referrals involve two members, so member-column
    sums would double-count; recomputing per column keeps that explicit.
    """
    totals = {
        "refs_given": sum(r["refs_given"] for r in rows),
        "one_to_ones": sum(r["one_to_ones"] for r in rows) // 2
        if rows else 0,
        "tyfcb": sum(r["tyfcb_received"] for r in rows),
        "members": len(rows),
    }
    return totals


def leaderboard(conn, metric="refs_given", period="all", today=None):
    if metric not in METRICS:
        metric = "refs_given"
    rows = member_rollup(conn, period, today)
    return sorted(rows, key=lambda r: (-r[metric], r["name"].lower()))


def recent_activity(conn, limit=12):
    return conn.execute(
        """
        SELECT * FROM (
          SELECT 'referral' AS kind, r.id, r.created_at, g.name AS who,
                 v.name AS whom, r.contact_name AS detail, NULL AS amount_cents
          FROM referrals r
          JOIN members g ON g.id = r.giver_id JOIN members v ON v.id = r.receiver_id
          UNION ALL
          SELECT 'one_to_one', o.id, o.created_at, a.name, b.name, o.location, NULL
          FROM one_to_ones o
          JOIN members a ON a.id = o.member1_id JOIN members b ON b.id = o.member2_id
          UNION ALL
          SELECT 'tyfcb', t.id, t.created_at, tk.name, td.name, t.notes, t.amount_cents
          FROM tyfcb t
          JOIN members tk ON tk.id = t.thanker_id JOIN members td ON td.id = t.thanked_id
        )
        ORDER BY created_at DESC, id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
