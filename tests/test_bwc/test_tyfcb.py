import pytest

from bwc.money import format_cents, parse_dollars

from .conftest import login


@pytest.mark.parametrize("text,cents", [
    ("1,250.50", 125050),
    ("$300", 30000),
    ("$1,000,000.00", 100000000),
    (" 42.05 ", 4205),
    ("0.01", 1),
])
def test_parse_dollars(text, cents):
    assert parse_dollars(text) == cents


@pytest.mark.parametrize("text", ["", "abc", "0", "-5", "1.005", "$", "1..2"])
def test_parse_dollars_rejects(text):
    with pytest.raises(ValueError):
        parse_dollars(text)


def test_format_cents():
    assert format_cents(125050) == "$1,250.50"
    assert format_cents(0) == "$0.00"
    assert format_cents(5) == "$0.05"


def record_tyfcb(client, thanked_id, amount="500", **extra):
    data = {"thanked_id": thanked_id, "amount": amount, "is_new_business": "1",
            "tyfcb_date": "2026-08-11", "notes": ""}
    data.update(extra)
    return client.post("/tyfcb/new", data=data, follow_redirects=False)


def test_record_and_totals(client, members):
    login(client, "bob@example.com")
    assert record_tyfcb(client, members["carol"], "1,250.50").status_code == 303
    assert record_tyfcb(client, members["carol"], "$749.50").status_code == 303

    given = client.get("/tyfcb?tab=given")
    assert "$2,000.00" in given.text
    client.post("/logout")

    login(client, "carol@example.com")
    received = client.get("/tyfcb?tab=received")
    assert "$2,000.00" in received.text
    assert client.get("/tyfcb?tab=given").text.count("$0.00") >= 1


def test_bad_amount_rejected(client, members):
    login(client, "bob@example.com")
    assert record_tyfcb(client, members["carol"], "zero dollars").status_code == 400
    assert record_tyfcb(client, members["carol"], "-10").status_code == 400


def test_cannot_thank_self(client, members):
    login(client, "bob@example.com")
    assert record_tyfcb(client, members["bob"]).status_code == 400


def test_link_to_received_referral(client, members):
    login(client, "carol@example.com")
    client.post("/referrals/new", data={
        "receiver_id": members["bob"], "contact_name": "Jane Prospect",
        "referral_type": "outside", "temperature": "hot",
        "referral_date": "2026-08-01"}, follow_redirects=False)
    client.post("/logout")

    login(client, "bob@example.com")
    assert record_tyfcb(client, members["carol"], "900", referral_id="1").status_code == 303
    page = client.get("/tyfcb?tab=given")
    assert "via referral: Jane Prospect" in page.text


def test_cannot_link_referral_not_received(client, members):
    login(client, "bob@example.com")
    client.post("/referrals/new", data={
        "receiver_id": members["carol"], "contact_name": "Someone Else",
        "referral_type": "outside", "temperature": "warm",
        "referral_date": "2026-08-01"}, follow_redirects=False)
    # Bob gave this referral; he didn't receive it, so he can't link it.
    assert record_tyfcb(client, members["carol"], "900", referral_id="1").status_code == 400


def test_only_reporter_or_admin_deletes(client, members):
    login(client, "bob@example.com")
    record_tyfcb(client, members["carol"])
    client.post("/logout")

    login(client, "carol@example.com")
    assert client.post("/tyfcb/1/delete").status_code == 403
    client.post("/logout")

    login(client, "alice@example.com")
    assert client.post("/tyfcb/1/delete", follow_redirects=False).status_code == 303
