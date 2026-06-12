from gmail_plugin.imap_client import parse_header_response, search_uids


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
