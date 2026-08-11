"""One-to-one meeting queries."""

from __future__ import annotations

from ..db import utcnow

_BASE_SELECT = """
    SELECT o.*, a.name AS member1_name, b.name AS member2_name
    FROM one_to_ones o
    JOIN members a ON a.id = o.member1_id
    JOIN members b ON b.id = o.member2_id
"""


def create(conn, member1_id, member2_id, met_on, location, notes, created_by):
    cur = conn.execute(
        """INSERT INTO one_to_ones (member1_id, member2_id, met_on, location, notes,
                                    created_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (member1_id, member2_id, met_on, location, notes, created_by, utcnow()),
    )
    conn.commit()
    return cur.lastrowid


def get(conn, one_to_one_id):
    return conn.execute(_BASE_SELECT + " WHERE o.id = ?", (one_to_one_id,)).fetchone()


def list_all(conn):
    return conn.execute(_BASE_SELECT + " ORDER BY o.met_on DESC, o.id DESC").fetchall()


def list_for_member(conn, member_id):
    return conn.execute(
        _BASE_SELECT + " WHERE o.member1_id = ? OR o.member2_id = ?"
                       " ORDER BY o.met_on DESC, o.id DESC",
        (member_id, member_id),
    ).fetchall()


def delete(conn, one_to_one_id):
    conn.execute("DELETE FROM one_to_ones WHERE id = ?", (one_to_one_id,))
    conn.commit()
