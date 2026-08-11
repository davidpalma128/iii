from .conftest import login


def test_directory_lists_active_members(client, members):
    login(client, "bob@example.com")
    page = client.get("/members")
    assert page.status_code == 200
    for name in ("Alice Admin", "Bob Builder", "Carol Coach"):
        assert name in page.text


def test_directory_search(client, members):
    # Log in as Alice so Bob's name can only come from the directory itself.
    login(client, "alice@example.com")
    page = client.get("/members", params={"q": "coach"})
    assert "Carol Coach" in page.text
    assert "Bob Builder" not in page.text


def test_profile_shows_scheduling_link(client, conn, members):
    login(client, "bob@example.com")
    client.post("/profile", data={
        "name": "Bob Builder", "business_name": "Bob Co", "category": "Construction",
        "phone": "555-0100", "scheduling_url": "https://calendly.com/bob"})
    page = client.get(f"/members/{members['bob']}")
    assert 'href="https://calendly.com/bob"' in page.text
    assert "Book a 1-to-1 with Bob" in page.text


def test_profile_url_gets_https_prefix(client, conn, members):
    login(client, "bob@example.com")
    client.post("/profile", data={
        "name": "Bob Builder", "business_name": "", "category": "",
        "phone": "", "scheduling_url": "calendly.com/bob"})
    page = client.get(f"/members/{members['bob']}")
    assert 'href="https://calendly.com/bob"' in page.text


def test_profile_requires_name(client, members):
    login(client, "bob@example.com")
    response = client.post("/profile", data={
        "name": "  ", "business_name": "", "category": "", "phone": "",
        "scheduling_url": ""})
    assert response.status_code == 400


def test_non_admin_cannot_reach_admin_pages(client, members):
    login(client, "bob@example.com")
    assert client.get("/admin/members").status_code == 403
    assert client.post("/admin/members/new", data={
        "name": "X", "email": "x@example.com", "password": "password123"}).status_code == 403


def test_admin_creates_member_who_can_login(client, members):
    login(client, "alice@example.com")
    response = client.post("/admin/members/new", data={
        "name": "Dave Dev", "email": "dave@example.com", "password": "temppass123",
        "business_name": "Dev LLC", "category": "Software", "phone": ""},
        follow_redirects=False)
    assert response.status_code == 303

    client.post("/logout")
    assert login(client, "dave@example.com", "temppass123").status_code == 303


def test_admin_duplicate_email_rejected(client, members):
    login(client, "alice@example.com")
    response = client.post("/admin/members/new", data={
        "name": "Copy", "email": "BOB@example.com", "password": "temppass123"})
    assert response.status_code == 400
    assert "already exists" in response.text


def test_admin_deactivate_and_reactivate(client, conn, members):
    login(client, "alice@example.com")
    client.post(f"/admin/members/{members['bob']}/deactivate")
    page = client.get("/members")
    assert "Bob Builder" not in page.text

    client.post(f"/admin/members/{members['bob']}/activate")
    assert "Bob Builder" in client.get("/members").text


def test_admin_cannot_deactivate_self(client, conn, members):
    login(client, "alice@example.com")
    client.post(f"/admin/members/{members['admin']}/deactivate")
    assert "Alice Admin" in client.get("/members").text


def test_admin_reset_password(client, members):
    login(client, "alice@example.com")
    client.post(f"/admin/members/{members['bob']}/reset-password",
                data={"password": "resetpass123"})
    client.post("/logout")
    assert login(client, "bob@example.com", "resetpass123").status_code == 303


def test_deactivated_member_profile_404(client, conn, members):
    from bwc.queries import members as members_q
    members_q.set_active(conn, members["carol"], False)
    login(client, "bob@example.com")
    assert client.get(f"/members/{members['carol']}").status_code == 404
