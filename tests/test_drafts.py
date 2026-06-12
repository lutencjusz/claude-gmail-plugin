from gmail_plugin import drafts


def test_create_appends_to_drafts_folder(fake_imap):
    res = drafts.create(
        to="x@y.pl", subject="Szkic", body="Tresc",
        creds_user="me@gmail.com", imap=fake_imap,
    )
    assert res["created"] is True
    assert len(fake_imap.appended) == 1
    mailbox, flags, raw = fake_imap.appended[0]
    assert mailbox == "[Gmail]/Drafts"
    assert "Draft" in flags


def test_list_returns_header_records(fake_imap):
    fake_imap.search_result = ("OK", [b"5"])
    fake_imap.fetch_results["5"] = ("OK", [(b"5 (..)", b"From: me@gmail.com\r\nSubject: Szkic\r\nX-GM-MSGID: 555\r\n\r\n")])
    rows = drafts.list_drafts(limit=10, imap=fake_imap)
    assert rows[0]["subject"] == "Szkic"


def test_create_dry_run_does_not_append(fake_imap):
    res = drafts.create(
        to="x@y.pl", subject="S", body="B", dry_run=True,
        creds_user="me@gmail.com", imap=fake_imap,
    )
    assert res["dry_run"] is True
    assert fake_imap.appended == []


def test_get_returns_full_draft(fake_imap):
    from email.message import EmailMessage
    fake_imap.search_result = ("OK", [b"7"])
    m = EmailMessage()
    m["From"] = "me@gmail.com"
    m["Subject"] = "Szkic"
    m.set_content("Robocza tresc")
    fake_imap.fetch_results["7"] = ("OK", [(b"7 (..)", m.as_bytes())])
    out = drafts.get("555", imap=fake_imap)
    assert out["subject"] == "Szkic"
    assert "Robocza tresc" in out["body_text"]


def test_send_dry_run_does_not_send(fake_imap, fake_smtp):
    plan = drafts.send("555", dry_run=True, imap=fake_imap, smtp=fake_smtp)
    assert plan["dry_run"] is True
    assert fake_smtp.sent == []


def test_send_sends_and_deletes_draft(fake_imap, fake_smtp):
    from email.message import EmailMessage
    fake_imap.search_result = ("OK", [b"7"])
    m = EmailMessage()
    m["From"] = "me@gmail.com"
    m["To"] = "x@y.pl"
    m["Subject"] = "Szkic"
    m.set_content("Robocza tresc")
    fake_imap.fetch_results["7"] = ("OK", [(b"7 (..)", m.as_bytes())])
    res = drafts.send("555", dry_run=False, creds_user="me@gmail.com",
                      creds_password="abcdefghijklmnop", imap=fake_imap, smtp=fake_smtp)
    assert res["sent"] is True
    assert len(fake_smtp.sent) == 1
    assert getattr(fake_imap, "expunged", False) is True
