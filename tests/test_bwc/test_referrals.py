from bwc.queries import referrals as referrals_q

from .conftest import login


def make_referral(client, receiver_id, contact="Jane Prospect", **extra):
    data = {"receiver_id": receiver_id, "contact_name": contact,
            "referral_type": "outside", "temperature": "warm",
            "referral_date": "2026-08-10"}
    data.update(extra)
    return client.post("/referrals/new", data=data, follow_redirects=False)


def test_create_referral_starts_as_given(client, members):
    login(client, "bob@example.com")
    response = make_referral(client, members["carol"])
    assert response.status_code == 303
    detail = client.get(response.headers["location"])
    assert "Jane Prospect" in detail.text
    assert "Given" in detail.text


def test_cannot_refer_to_self(client, members):
    login(client, "bob@example.com")
    assert make_referral(client, members["bob"]).status_code == 400


def test_contact_name_required(client, members):
    login(client, "bob@example.com")
    assert make_referral(client, members["carol"], contact="  ").status_code == 400


def test_status_update_changes_status_and_logs_thread(client, conn, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["carol"]).headers["location"]
    referral_id = int(url.rsplit("/", 1)[1])

    client.post(f"{url}/updates", data={"note": "Called them", "new_status": "contacted"})
    client.post(f"{url}/updates", data={"note": "", "new_status": "closed"})

    referral = referrals_q.get(conn, referral_id)
    assert referral["status"] == "closed"
    updates = referrals_q.list_updates(conn, referral_id)
    assert [u["new_status"] for u in updates] == ["contacted", "closed"]
    assert updates[0]["note"] == "Called them"

    detail = client.get(url)
    assert "Closed business" in detail.text


def test_invalid_status_rejected(client, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["carol"]).headers["location"]
    response = client.post(f"{url}/updates", data={"note": "x", "new_status": "bogus"})
    assert response.status_code == 400


def test_receiver_can_post_update(client, conn, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["carol"]).headers["location"]
    client.post("/logout")

    login(client, "carol@example.com")
    response = client.post(f"{url}/updates",
                           data={"note": "Met with Jane", "new_status": "in_progress"},
                           follow_redirects=False)
    assert response.status_code == 303
    referral_id = int(url.rsplit("/", 1)[1])
    assert referrals_q.get(conn, referral_id)["status"] == "in_progress"


def test_third_party_cannot_view_or_update(client, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["admin"]).headers["location"]
    client.post("/logout")

    login(client, "carol@example.com")
    assert client.get(url).status_code == 403
    assert client.post(f"{url}/updates", data={"note": "hi"}).status_code == 403


def test_admin_can_view_any_referral(client, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["carol"]).headers["location"]
    client.post("/logout")

    login(client, "alice@example.com")
    assert client.get(url).status_code == 200


def test_only_giver_or_admin_deletes(client, conn, members):
    login(client, "bob@example.com")
    url = make_referral(client, members["carol"]).headers["location"]
    client.post("/logout")

    login(client, "carol@example.com")
    assert client.post(f"{url}/delete").status_code == 403
    client.post("/logout")

    login(client, "bob@example.com")
    assert client.post(f"{url}/delete", follow_redirects=False).status_code == 303
    assert client.get(url).status_code == 404


def test_list_tabs_and_status_filter(client, members):
    login(client, "bob@example.com")
    make_referral(client, members["carol"], contact="Given One")
    client.post("/logout")

    login(client, "carol@example.com")
    given = client.get("/referrals?tab=given")
    assert "Given One" not in given.text
    received = client.get("/referrals?tab=received")
    assert "Given One" in received.text
    filtered = client.get("/referrals?tab=received&status=closed")
    assert "Given One" not in filtered.text
