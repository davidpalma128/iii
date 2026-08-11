import pytest
from fastapi.testclient import TestClient

import bwc.security as security
from bwc.app import create_app
from bwc.db import connect
from bwc.queries import members as members_q

# Full-strength PBKDF2 makes the suite crawl; the stored-format tests still
# exercise the real algorithm, just with fewer rounds.
security.PBKDF2_ITERATIONS = 1000

PASSWORD = "password123"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.sqlite3"


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path, secret_key="test-secret")


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def conn(app, db_path):
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def members(conn):
    password_hash = security.hash_password(PASSWORD)
    return {
        "admin": members_q.create(conn, "Alice Admin", "alice@example.com",
                                  password_hash, is_admin=1),
        "bob": members_q.create(conn, "Bob Builder", "bob@example.com", password_hash,
                                business_name="Bob Co", category="Construction"),
        "carol": members_q.create(conn, "Carol Coach", "carol@example.com",
                                  password_hash, category="Coaching"),
    }


def login(client, email, password=PASSWORD):
    return client.post("/login",
                       data={"email": email, "password": password, "next": "/"},
                       follow_redirects=False)
