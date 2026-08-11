"""TYFCB (Thank You For Closed Business) queries."""

from __future__ import annotations

from ..db import utcnow

_BASE_SELECT = """
    SELECT t.*, tk.name AS thanker_name, td.name AS thanked_name,
           r.contact_name AS referral_contact
    FROM tyfcb t
    JOIN members tk ON tk.id = t.thanker_id
    JOIN members td ON td.id = t.thanked_id
    LEFT JOIN referrals r ON r.id = t.referral_id
"""


def create(conn, thanker_id, thanked_id, amount_cents, referral_id,
           is_new_business, notes, tyfcb_date):
    cur = conn.execute(
        """INSERT INTO tyfcb (thanker_id, thanked_id, amount_cents, referral_id,
                              is_new_business, notes, tyfcb_date, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (thanker_id, thanked_id, amount_cents, referral_id,
         int(is_new_business), notes, tyfcb_date, utcnow()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn, tyfcb_id):
    return conn.execute(_BASE_SELECT + " WHERE t.id = ?", (tyfcb_id,)).fetchone()


def list_for_member(conn, member_id, tab="given"):
    column = "t.thanker_id" if tab == "given" else "t.thanked_id"
    return conn.execute(
        _BASE_SELECT + f" WHERE {column} = ? ORDER BY t.tyfcb_date DESC, t.id DESC",
        (member_id,),
    ).fetchall()


def delete(conn, tyfcb_id):
    conn.execute("DELETE FROM tyfcb WHERE id = ?", (tyfcb_id,))
    conn.commit()
