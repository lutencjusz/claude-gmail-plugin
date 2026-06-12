from email.message import EmailMessage

import pytest

from gmail_plugin.imap_client import (
    append_draft,
    delete_uid,
    fetch_full,
    fetch_headers,
    parse_full,
    parse_header_response,
    search_uids,
    uid_for_gmail_id,
    IMAPError,
)


def test_parse_header_response_extracts_fields():
    raw = (
        b"From: Jan Kowalski <jan@x.pl>\r\n"
        b"Subject: Oferta\r\n"
        b"Date: Mon, 01 Jun 2026 10:00:00 +0200\r\n"
        b"X-GM-MSGID: 17000000000000001\r\n"
        b"X-GM-THRID: 17000000000000009\r\n\r\n"
    )
    out = parse_header_response(raw)
    assert out["from"] == "Jan Kowalski <jan@x.pl>"
    assert out["subject"] == "Oferta"
    assert out["msgid"] == "17000000000000001"
    assert out["thrid"] == "17000000000000009"


def test_search_uids_parses_ids_and_limits(fake_imap):
    fake_imap.search_result = ("OK", [b"11 12 13 14 15"])
    uids = search_uids(fake_imap, "INBOX", ["X-GM-RAW", '"is:unread"'], limit=3)
    assert uids == [15, 14, 13]
    assert fake_imap.last_uid_call[1][1] == "X-GM-RAW"


def test_fetch_headers_returns_records_with_uid(fake_imap):
    fake_imap.fetch_results["12"] = ("OK", [(b"12 (..)", b"From: A <a@x.pl>\r\nSubject: S\r\nX-GM-MSGID: 120\r\n\r\n")])
    rows = fetch_headers(fake_imap, "INBOX", [12])
    assert rows[0]["subject"] == "S"
    assert rows[0]["uid"] == 12


def test_fetch_full_returns_message(fake_imap):
    m = EmailMessage()
    m["Subject"] = "Pelna"
    m.set_content("tresc")
    fake_imap.fetch_results["9"] = ("OK", [(b"9 (..)", m.as_bytes())])
    msg = fetch_full(fake_imap, "INBOX", 9)
    assert msg["Subject"] == "Pelna"


def test_uid_for_gmail_id_returns_first(fake_imap):
    fake_imap.search_result = ("OK", [b"7 8"])
    assert uid_for_gmail_id(fake_imap, "INBOX", "X-GM-MSGID", "555") == 7


def test_append_draft_ok(fake_imap):
    m = EmailMessage()
    m["Subject"] = "Szkic"
    m.set_content("b")
    append_draft(fake_imap, "[Gmail]/Drafts", m)
    assert fake_imap.appended[0][0] == "[Gmail]/Drafts"
    assert "Draft" in fake_imap.appended[0][1]


def test_append_draft_raises_on_failure(fake_imap):
    fake_imap.append = lambda *a, **k: ("NO", [b"quota"])
    m = EmailMessage()
    m.set_content("b")
    with pytest.raises(IMAPError):
        append_draft(fake_imap, "[Gmail]/Drafts", m)


def test_delete_uid_sets_deleted_and_expunges(fake_imap):
    delete_uid(fake_imap, "[Gmail]/Drafts", 5)
    assert fake_imap.selected == ("[Gmail]/Drafts", False)
    assert getattr(fake_imap, "expunged", False) is True


def test_parse_full_extracts_body_and_attachments():
    m = EmailMessage()
    m["From"] = "a@x.pl"
    m["Subject"] = "T"
    m.set_content("tekst")
    m.add_attachment(b"data", maintype="application", subtype="pdf", filename="f.pdf")
    out = parse_full(m)
    assert out["body_text"].startswith("tekst")
    assert "f.pdf" in out["attachments"]
