from gmail_plugin import send


def test_dry_run_returns_plan_without_network(fake_smtp):
    plan = send.send(
        to="x@y.pl", subject="Temat", body="Tresc",
        attachments=None, dry_run=True,
        creds_user="me@gmail.com", smtp=fake_smtp,
    )
    assert plan["dry_run"] is True
    assert plan["to"] == "x@y.pl"
    assert plan["subject"] == "Temat"
    assert plan["html"] is False
    assert fake_smtp.sent == []


def test_real_send_uses_smtp(fake_smtp):
    res = send.send(
        to="x@y.pl", subject="T", body="B",
        dry_run=False, creds_user="me@gmail.com",
        creds_password="abcdefghijklmnop", smtp=fake_smtp,
    )
    assert res["sent"] is True
    assert len(fake_smtp.sent) == 1
    assert fake_smtp.sent[0]["To"] == "x@y.pl"


def test_plan_never_contains_password(fake_smtp):
    plan = send.send(
        to="x@y.pl", subject="T", body="B", dry_run=True,
        creds_user="me@gmail.com", creds_password="topsecret1234567",
        smtp=fake_smtp,
    )
    assert "topsecret1234567" not in str(plan)
