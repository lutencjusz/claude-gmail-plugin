from gmail_plugin.query import build_gmail_query, raw_criteria


def test_query_only():
    assert build_gmail_query("from:allegro", unread=False) == "from:allegro"


def test_unread_prepended():
    assert build_gmail_query("from:allegro", unread=True) == "is:unread from:allegro"


def test_unread_without_query():
    assert build_gmail_query(None, unread=True) == "is:unread"


def test_empty_defaults_to_inbox():
    assert build_gmail_query(None, unread=False) == "in:inbox"


def test_raw_criteria_quotes_and_escapes():
    crit = raw_criteria('subject:"a \\"b\\""')
    assert crit[0] == "X-GM-RAW"
    assert crit[1].startswith('"') and crit[1].endswith('"')
    assert '\\"' in crit[1]
