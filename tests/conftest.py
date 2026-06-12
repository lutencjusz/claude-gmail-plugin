import pytest


class FakeIMAP:
    """Minimalny zamiennik imaplib.IMAP4_SSL do testow offline."""

    def __init__(self):
        self.selected = None
        self.appended = []
        self.logged_out = False
        self.last_uid_call = None
        self.search_result = ("OK", [b""])
        self.fetch_results = {}  # uid(str) -> ("OK", data)

    def login(self, user, password):
        self.login_args = (user, password)
        return ("OK", [b"LOGIN completed"])

    def select(self, mailbox, readonly=False):
        self.selected = (mailbox, readonly)
        return ("OK", [b"1"])

    def uid(self, command, *args):
        self.last_uid_call = (command, args)
        if command == "SEARCH":
            return self.search_result
        if command == "FETCH":
            return self.fetch_results.get(args[0], ("NO", [None]))
        return ("OK", [None])

    def append(self, mailbox, flags, date_time, message):
        self.appended.append((mailbox, flags, message))
        return ("OK", [b"[APPENDUID 1 99]"])

    def expunge(self):
        self.expunged = True
        return ("OK", [b"1"])

    def logout(self):
        self.logged_out = True
        return ("BYE", [b"logout"])


class FakeSMTP:
    """Minimalny zamiennik smtplib.SMTP_SSL."""

    def __init__(self):
        self.sent = []
        self.login_args = None

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_imap():
    return FakeIMAP()


@pytest.fixture
def fake_smtp():
    return FakeSMTP()
