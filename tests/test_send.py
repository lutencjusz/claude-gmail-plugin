from email.message import EmailMessage

from gmail_plugin import send


def test_reply_sets_threading_headers(fake_imap, fake_smtp):
    # oryginal pobierany przez messages.get (imap) -> ustaw In-Reply-To/References i "Re:"
    fake_imap.search_result = ("OK", [b"5"])
    orig = EmailMessage()
    orig["Message-ID"] = "<orig@mail>"
    orig["Subject"] = "Pytanie"
    orig.set_content("q")
    fake_imap.fetch_results["5"] = ("OK", [(b"5 (..)", orig.as_bytes())])
    send.send(
        to="x@y.pl", subject="Odpowiedz", body="ok", reply_to="999",
        creds_user="me@gmail.com", creds_password="abcdefghijklmnop",
        smtp=fake_smtp, imap=fake_imap,
    )
    sent = fake_smtp.sent[0]
    assert sent["In-Reply-To"] == "<orig@mail>"
    assert sent["References"] == "<orig@mail>"
    assert sent["Subject"].startswith("Re:")


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
