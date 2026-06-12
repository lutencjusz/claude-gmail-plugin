from email.message import EmailMessage

from gmail_plugin import messages


def test_search_returns_header_records(fake_imap):
    fake_imap.search_result = ("OK", [b"10 11"])
    fake_imap.fetch_results["11"] = ("OK", [(b"11 (..)", b"From: A <a@x.pl>\r\nSubject: S11\r\nX-GM-MSGID: 111\r\n\r\n")])
    fake_imap.fetch_results["10"] = ("OK", [(b"10 (..)", b"From: B <b@x.pl>\r\nSubject: S10\r\nX-GM-MSGID: 110\r\n\r\n")])
    rows = messages.search("from:x", limit=10, imap=fake_imap)
    assert [r["subject"] for r in rows] == ["S11", "S10"]
    assert rows[0]["msgid"] == "111"


def test_get_returns_full_message(fake_imap):
    fake_imap.search_result = ("OK", [b"42"])
    m = EmailMessage()
    m["From"] = "a@x.pl"
    m["Subject"] = "Pelna"
    m.set_content("Tresc wiadomosci")
    fake_imap.fetch_results["42"] = ("OK", [(b"42 (..)", m.as_bytes())])
    out = messages.get("999", imap=fake_imap)
    assert out["subject"] == "Pelna"
    assert "Tresc wiadomosci" in out["body_text"]


def test_get_missing_returns_none_marker(fake_imap):
    fake_imap.search_result = ("OK", [b""])
    out = messages.get("doesnotexist", imap=fake_imap)
    assert out is None


def test_thread_returns_messages_oldest_first(fake_imap):
    # UID-y nie po kolei -> wynik posortowany rosnaco po uid (najstarsze pierwsze)
    fake_imap.search_result = ("OK", [b"21 20"])
    fake_imap.fetch_results["20"] = ("OK", [(b"20 (..)", b"Subject: pierwsza\r\nX-GM-THRID: 900\r\n\r\n")])
    fake_imap.fetch_results["21"] = ("OK", [(b"21 (..)", b"Subject: druga\r\nX-GM-THRID: 900\r\n\r\n")])
    rows = messages.thread("900", imap=fake_imap)
    assert [r["subject"] for r in rows] == ["pierwsza", "druga"]
    assert [r["uid"] for r in rows] == [20, 21]
