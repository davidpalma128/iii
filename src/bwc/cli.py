"""bwc command line: init-db, create-admin, serve."""

from __future__ import annotations

import argparse
import getpass
import sys

from .config import resolve_db_path
from .db import connect, init_db
from .queries import members as members_q
from .security import hash_password


def cmd_init_db(args) -> int:
    db_path = resolve_db_path(args.db)
    init_db(db_path)
    print(f"Database ready at {db_path}")
    return 0


def cmd_create_admin(args) -> int:
    db_path = resolve_db_path(args.db)
    init_db(db_path)
    password = args.password
    if not password:
        password = getpass.getpass("Password for new admin: ")
        if password != getpass.getpass("Confirm password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1
    conn = connect(db_path)
    try:
        if members_q.get_by_email(conn, args.email):
            print(f"A member with email {args.email} already exists.", file=sys.stderr)
            return 1
        members_q.create(conn, args.name, args.email, hash_password(password), is_admin=1)
    finally:
        conn.close()
    print(f"Admin {args.name} <{args.email}> created.")
    return 0


def cmd_serve(args) -> int:
    import uvicorn

    uvicorn.run("bwc.asgi:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bwc", description="The Business Wealth Collective chapter tracker"
    )
    parser.add_argument("--db", help="Path to the SQLite database (default: data/bwc.sqlite3)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create the database and schema")

    p_admin = sub.add_parser("create-admin", help="Create an admin member")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--name", required=True)
    p_admin.add_argument("--password", help="Password (omit to be prompted)")

    p_serve = sub.add_parser("serve", help="Run the web app")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)
    handlers = {"init-db": cmd_init_db, "create-admin": cmd_create_admin, "serve": cmd_serve}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
