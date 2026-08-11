from .conftest import login


def log_o2o(client, other_id, met_on="2026-08-11", location="Cafe"):
    return client.post("/one-to-ones/new",
                       data={"other_id": other_id, "met_on": met_on,
                             "location": location, "notes": ""},
                       follow_redirects=False)


def test_create_and_visible_to_both_participants(client, members):
    login(client, "bob@example.com")
    assert log_o2o(client, members["carol"]).status_code == 303
    assert "Carol Coach" in client.get("/one-to-ones").text
    client.post("/logout")

    login(client, "carol@example.com")
    assert "Bob Builder" in client.get("/one-to-ones?scope=mine").text


def test_mine_scope_excludes_others(client, members):
    login(client, "bob@example.com")
    log_o2o(client, members["carol"])
    client.post("/logout")

    login(client, "alice@example.com")
    mine = client.get("/one-to-ones?scope=mine")
    assert "Bob Builder" not in mine.text
    everyone = client.get("/one-to-ones?scope=all")
    assert "Bob Builder" in everyone.text


def test_cannot_meet_self(client, members):
    login(client, "bob@example.com")
    assert log_o2o(client, members["bob"]).status_code == 400


def test_participant_can_delete_third_party_cannot(client, members):
    login(client, "bob@example.com")
    log_o2o(client, members["admin"])
    client.post("/logout")

    login(client, "carol@example.com")
    assert client.post("/one-to-ones/1/delete").status_code == 403
    client.post("/logout")

    login(client, "bob@example.com")
    assert client.post("/one-to-ones/1/delete", follow_redirects=False).status_code == 303
    assert "Alice Admin" not in client.get("/one-to-ones").text
