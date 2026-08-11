from fastapi.testclient import TestClient

from bwc.app import create_app
from bwc.cli import main
from bwc.db import connect


def test_init_db_idempotent(tmp_path, capsys):
    db = tmp_path / "cli.sqlite3"
    assert main(["--db", str(db), "init-db"]) == 0
    assert main(["--db", str(db), "init-db"]) == 0
    conn = connect(db)
    version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    conn.close()
    assert version["value"] == "1"


def test_create_admin_can_login(tmp_path):
    db = tmp_path / "cli.sqlite3"
    assert main(["--db", str(db), "create-admin", "--email", "boss@example.com",
                 "--name", "Boss", "--password", "bosspass123"]) == 0

    app = create_app(db_path=db, secret_key="test-secret")
    client = TestClient(app)
    response = client.post("/login", data={
        "email": "boss@example.com", "password": "bosspass123", "next": "/"},
        follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/admin/members").status_code == 200


def test_create_admin_duplicate_email_fails(tmp_path):
    db = tmp_path / "cli.sqlite3"
    args = ["--db", str(db), "create-admin", "--email", "boss@example.com",
            "--name", "Boss", "--password", "bosspass123"]
    assert main(args) == 0
    assert main(args) == 1


def test_create_admin_short_password_fails(tmp_path):
    db = tmp_path / "cli.sqlite3"
    assert main(["--db", str(db), "create-admin", "--email", "b@example.com",
                 "--name", "B", "--password", "short"]) == 1
