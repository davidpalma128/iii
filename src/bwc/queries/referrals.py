"""Referral + referral-update queries."""

from __future__ import annotations

from ..db import utcnow

STATUSES = ("given", "contacted", "in_progress", "closed", "lost")
TYPES = ("inside", "outside")
TEMPERATURES = ("hot", "warm", "cold")

STATUS_LABELS = {
    "given": "Given",
    "contacted": "Contacted",
    "in_progress": "In progress",
    "closed": "Closed business",
    "lost": "Lost",
}

_BASE_SELECT = """
    SELECT r.*, g.name AS giver_name, v.name AS receiver_name
    FROM referrals r
    JOIN members g ON g.id = r.giver_id
    JOIN members v ON v.id = r.receiver_id
"""


def create(conn, giver_id, receiver_id, contact_name, contact_info, notes,
           referral_type, temperature, referral_date):
    cur = conn.execute(
        """INSERT INTO referrals (giver_id, receiver_id, contact_name, contact_info,
                                  notes, referral_type, temperature, referral_date, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (giver_id, receiver_id, contact_name, contact_info, notes,
         referral_type, temperature, referral_date, utcnow()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn, referral_id):
    return conn.execute(_BASE_SELECT + " WHERE r.id = ?", (referral_id,)).fetchone()


def list_for_member(conn, member_id, tab="given", status=None):
    column = "r.giver_id" if tab == "given" else "r.receiver_id"
    sql = _BASE_SELECT + f" WHERE {column} = ?"
    params = [member_id]
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.referral_date DESC, r.id DESC"
    return conn.execute(sql, params).fetchall()


def list_received(conn, receiver_id):
    """Referrals a member received — options for linking a TYFCB."""
    return conn.execute(
        _BASE_SELECT + " WHERE r.receiver_id = ? ORDER BY r.referral_date DESC",
        (receiver_id,),
    ).fetchall()


def add_update(conn, referral_id, author_id, note="", new_status=None):
    """Append a thread entry; a status change also updates the referral, atomically."""
    if new_status is not None and new_status not in STATUSES:
        raise ValueError(f"Invalid status: {new_status}")
    with conn:
        conn.execute(
            """INSERT INTO referral_updates (referral_id, author_id, new_status, note, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (referral_id, author_id, new_status, note, utcnow()),
        )
        if new_status is not None:
            conn.execute("UPDATE referrals SET status = ? WHERE id = ?",
                         (new_status, referral_id))


def list_updates(conn, referral_id):
    return conn.execute(
        """SELECT u.*, m.name AS author_name
           FROM referral_updates u JOIN members m ON m.id = u.author_id
           WHERE u.referral_id = ? ORDER BY u.created_at, u.id""",
        (referral_id,),
    ).fetchall()


def delete(conn, referral_id):
    with conn:
        conn.execute("UPDATE tyfcb SET referral_id = NULL WHERE referral_id = ?",
                     (referral_id,))
        conn.execute("DELETE FROM referrals WHERE id = ?", (referral_id,))
