"""Member queries. All functions take an open sqlite3 connection."""

from __future__ import annotations

from ..db import utcnow


def create(conn, name, email, password_hash, business_name="", category="",
           phone="", scheduling_url="", is_admin=0):
    cur = conn.execute(
        """INSERT INTO members (name, email, password_hash, business_name, category,
                                phone, scheduling_url, is_admin, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, email, password_hash, business_name, category, phone,
         scheduling_url, int(is_admin), utcnow()),
    )
    conn.commit()
    return cur.lastrowid


def get_by_id(conn, member_id):
    return conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()


def get_by_email(conn, email):
    return conn.execute("SELECT * FROM members WHERE email = ?", (email,)).fetchone()


def list_active(conn, q=None):
    if q:
        like = f"%{q}%"
        return conn.execute(
            """SELECT * FROM members
               WHERE is_active = 1
                 AND (name LIKE ? OR business_name LIKE ? OR category LIKE ?)
               ORDER BY name COLLATE NOCASE""",
            (like, like, like),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM members WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    ).fetchall()


def list_all(conn):
    return conn.execute(
        "SELECT * FROM members ORDER BY is_active DESC, name COLLATE NOCASE"
    ).fetchall()


def update_profile(conn, member_id, name, business_name, category, phone, scheduling_url):
    conn.execute(
        """UPDATE members SET name = ?, business_name = ?, category = ?,
                              phone = ?, scheduling_url = ? WHERE id = ?""",
        (name, business_name, category, phone, scheduling_url, member_id),
    )
    conn.commit()


def admin_update(conn, member_id, name, email, business_name, category, phone,
                 scheduling_url, is_admin):
    conn.execute(
        """UPDATE members SET name = ?, email = ?, business_name = ?, category = ?,
                              phone = ?, scheduling_url = ?, is_admin = ? WHERE id = ?""",
        (name, email, business_name, category, phone, scheduling_url,
         int(is_admin), member_id),
    )
    conn.commit()


def set_password(conn, member_id, password_hash):
    conn.execute("UPDATE members SET password_hash = ? WHERE id = ?",
                 (password_hash, member_id))
    conn.commit()


def set_active(conn, member_id, active):
    conn.execute("UPDATE members SET is_active = ? WHERE id = ?",
                 (int(active), member_id))
    conn.commit()
