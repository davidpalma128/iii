from bwc.queries import members as members_q
from bwc.security import SESSION_COOKIE, hash_password, verify_password

from .conftest import PASSWORD, login


def test_hash_roundtrip():
    stored = hash_password("s3cret-pass")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret-pass", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("s3cret-pass", "garbage")


def test_anonymous_redirected_to_login(client):
    response = client.get("/referrals", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/referrals"


def test_login_success_sets_cookie_and_next(client, members):
    response = client.post(
        "/login",
        data={"email": "bob@example.com", "password": PASSWORD, "next": "/members"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/members"
    assert SESSION_COOKIE in response.cookies

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Bob Builder" in dashboard.text


def test_login_wrong_password(client, members):
    response = login(client, "bob@example.com", "not-the-password")
    assert response.status_code == 401
    assert "Invalid email or password" in response.text


def test_login_unknown_email(client, members):
    response = login(client, "nobody@example.com")
    assert response.status_code == 401


def test_login_rejects_external_next(client, members):
    response = client.post(
        "/login",
        data={"email": "bob@example.com", "password": PASSWORD,
              "next": "https://evil.example.com"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/"


def test_inactive_member_cannot_login(client, conn, members):
    members_q.set_active(conn, members["bob"], False)
    response = login(client, "bob@example.com")
    assert response.status_code == 403


def test_inactive_member_session_invalidated(client, conn, members):
    login(client, "bob@example.com")
    assert client.get("/").status_code == 200
    members_q.set_active(conn, members["bob"], False)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303


def test_tampered_cookie_rejected(client, members):
    client.cookies.set(SESSION_COOKIE, "forged.token.value")
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303


def test_logout_clears_session(client, members):
    login(client, "bob@example.com")
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/", follow_redirects=False).status_code == 303


def test_password_change_flow(client, members):
    login(client, "bob@example.com")
    bad = client.post("/password", data={
        "current_password": "wrong", "new_password": "newpassword1",
        "confirm_password": "newpassword1"})
    assert bad.status_code == 400

    mismatch = client.post("/password", data={
        "current_password": PASSWORD, "new_password": "newpassword1",
        "confirm_password": "different1"})
    assert mismatch.status_code == 400

    ok = client.post("/password", data={
        "current_password": PASSWORD, "new_password": "newpassword1",
        "confirm_password": "newpassword1"}, follow_redirects=False)
    assert ok.status_code == 303

    client.post("/logout")
    assert login(client, "bob@example.com").status_code == 401
    assert login(client, "bob@example.com", "newpassword1").status_code == 303
