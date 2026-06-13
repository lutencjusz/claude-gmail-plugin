# Gmail plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zbudować plugin Claude Code `gmail` z CLI i skillami do odczytu/wyszukiwania, wysyłki i draftów na skrzynce Gmail przez IMAP/SMTP (app password).

**Architecture:** Jeden pakiet Python `gmail_plugin` z cienkim CLI (`argparse`, wynik JSON). Logika transportu na stdlib (`imaplib`/`smtplib`/`email`); wyszukiwanie przez rozszerzenie Gmaila `X-GM-RAW`. Skille (`SKILL.md`) wołają komendę `gmail`. Funkcje przyjmują wstrzykiwalny obiekt połączenia (`imap=`/`smtp=`), by testy działały offline bez sieci.

**Tech Stack:** Python 3.11+, uv, python-dotenv, pytest. Stdlib: imaplib, smtplib, email, argparse, json.

---

## File Structure

| Plik | Odpowiedzialność |
|------|------------------|
| `pyproject.toml` | projekt uv, dep `python-dotenv`, entry point `gmail` |
| `.claude-plugin/plugin.json` | manifest pluginu |
| `src/gmail_plugin/config.py` | stałe serwerów, `Credentials`, `load_credentials`, `ConfigError` |
| `src/gmail_plugin/query.py` | budowa zapytania Gmaila i kryterium `X-GM-RAW` |
| `src/gmail_plugin/mime_build.py` | budowa wiadomości MIME (tekst/HTML/załączniki/reply) |
| `src/gmail_plugin/imap_client.py` | połączenie IMAP, parsowanie odpowiedzi, fetch/search/append |
| `src/gmail_plugin/messages.py` | `search` / `get` / `thread` |
| `src/gmail_plugin/send.py` | plan wysyłki + wysyłka SMTP |
| `src/gmail_plugin/drafts.py` | `create` / `list_drafts` / `get` / `send` |
| `src/gmail_plugin/cli.py` | dispatcher subkomend → JSON, `auth-status` |
| `tests/conftest.py` | `FakeIMAP`, `FakeSMTP` |
| `tests/test_*.py` | testy jednostkowe offline |
| `skills/*/SKILL.md` | cienkie skille |
| `CLAUDE.md`, `README.md` | dokumentacja, instalacja, junctions |

Funkcje publiczne mają parametr `*, imap=None` / `smtp=None`; gdy `None`, otwierają realne połączenie z poświadczeń, w testach wstrzykiwany jest fake.

---

## Task 1: Scaffold projektu i instalacja

**Files:**
- Create: `pyproject.toml`
- Create: `.claude-plugin/plugin.json`
- Create: `src/gmail_plugin/__init__.py`

- [ ] **Step 1: Utwórz `pyproject.toml`**

```toml
[project]
name = "gmail-plugin"
version = "0.1.0"
description = "Operacje na skrzynce Gmail (IMAP/SMTP) jako skille Claude Code."
requires-python = ">=3.11"
dependencies = ["python-dotenv>=1.0"]

[project.scripts]
gmail = "gmail_plugin.cli:main"

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gmail_plugin"]
```

- [ ] **Step 2: Utwórz manifest `.claude-plugin/plugin.json`**

```json
{
  "name": "gmail",
  "version": "0.1.0",
  "description": "Skrzynka Gmail przez IMAP/SMTP: odczyt/wyszukiwanie, wysyłka i drafty.",
  "author": { "name": "micha" },
  "keywords": ["gmail", "imap", "smtp", "poczta", "email", "x-gm-raw"]
}
```

- [ ] **Step 3: Utwórz pusty `src/gmail_plugin/__init__.py`**

```python
"""Plugin gmail: operacje na skrzynce Gmail przez IMAP/SMTP."""
```

- [ ] **Step 4: Zainstaluj zależności i zweryfikuj**

Run: `cd /c/claude/gmail-plugin && uv sync`
Expected: tworzy `.venv`, instaluje python-dotenv i pytest, bez błędów.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .claude-plugin src/gmail_plugin/__init__.py
git commit -m "chore: scaffold pluginu gmail (pyproject, manifest, pakiet)"
```

---

## Task 2: config.py — poświadczenia i stałe

**Files:**
- Create: `src/gmail_plugin/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_config.py
import pytest
from gmail_plugin.config import load_credentials, ConfigError, Credentials


def _write_env(tmp_path, body):
    p = tmp_path / "creds.env"
    p.write_text(body, encoding="utf-8")
    return p


def test_loads_user_and_password(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\nGMAIL_APP_PASSWORD=abcdefghijklmnop\n")
    creds = load_credentials(env)
    assert creds.user == "me@gmail.com"
    assert creds.password == "abcdefghijklmnop"


def test_missing_password_raises_configerror(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\n")
    with pytest.raises(ConfigError):
        load_credentials(env)


def test_missing_file_raises_configerror(tmp_path):
    with pytest.raises(ConfigError):
        load_credentials(tmp_path / "nope.env")


def test_repr_redacts_password(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\nGMAIL_APP_PASSWORD=secret1234567890\n")
    creds = load_credentials(env)
    assert "secret1234567890" not in repr(creds)
    assert "redacted" in repr(creds).lower()
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.config`.

- [ ] **Step 3: Zaimplementuj `config.py`**

```python
# src/gmail_plugin/config.py
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
DRAFTS_FOLDER = "[Gmail]/Drafts"
ALL_MAIL_FOLDER = "[Gmail]/All Mail"


class ConfigError(Exception):
    """Brak/niekompletna konfiguracja poswiadczen Gmaila."""


@dataclass(frozen=True)
class Credentials:
    user: str
    password: str

    def __repr__(self) -> str:
        return f"Credentials(user={self.user!r}, password=<redacted>)"


def default_env_path() -> Path:
    override = os.environ.get("GMAIL_PLUGIN_ENV")
    if override:
        return Path(override)
    return Path.home() / ".secrets" / "gmail-plugin.env"


def load_credentials(env_path: Path | None = None) -> Credentials:
    path = Path(env_path) if env_path is not None else default_env_path()
    if not path.is_file():
        raise ConfigError(
            f"Nie znaleziono pliku .env: {path}. Uruchom skill gmail-setup."
        )
    values = dotenv_values(path)
    user = (values.get("GMAIL_USER") or "").strip()
    password = (values.get("GMAIL_APP_PASSWORD") or "").strip()
    if not user or not password:
        raise ConfigError(
            "Brak GMAIL_USER lub GMAIL_APP_PASSWORD w pliku .env. Uruchom skill gmail-setup."
        )
    return Credentials(user=user, password=password)
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_config.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/config.py tests/test_config.py
git commit -m "feat(config): odczyt poswiadczen z .env, redakcja sekretu"
```

---

## Task 3: query.py — budowa zapytania Gmaila

**Files:**
- Create: `src/gmail_plugin/query.py`
- Test: `tests/test_query.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_query.py
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
    # zapytanie z cudzyslowem nie moze rozbic skladni IMAP
    crit = raw_criteria('subject:"a \\"b\\""')
    assert crit[0] == "X-GM-RAW"
    assert crit[1].startswith('"') and crit[1].endswith('"')
    assert '\\"' in crit[1]
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_query.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.query`.

- [ ] **Step 3: Zaimplementuj `query.py`**

```python
# src/gmail_plugin/query.py


def build_gmail_query(query: str | None, unread: bool) -> str:
    parts: list[str] = []
    if unread:
        parts.append("is:unread")
    if query:
        parts.append(query)
    return " ".join(parts) if parts else "in:inbox"


def raw_criteria(gmail_query: str) -> list[str]:
    """Kryterium IMAP SEARCH dla rozszerzenia Gmaila X-GM-RAW."""
    escaped = gmail_query.replace("\\", "\\\\").replace('"', '\\"')
    return ["X-GM-RAW", f'"{escaped}"']
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_query.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/query.py tests/test_query.py
git commit -m "feat(query): budowa zapytania Gmaila i kryterium X-GM-RAW"
```

---

## Task 4: mime_build.py — budowa wiadomości MIME

**Files:**
- Create: `src/gmail_plugin/mime_build.py`
- Test: `tests/test_mime.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_mime.py
from gmail_plugin.mime_build import build_message


def test_plain_text_message():
    msg = build_message(
        sender="me@gmail.com", to="x@y.pl", subject="Temat", body="Tresc"
    )
    assert msg["From"] == "me@gmail.com"
    assert msg["To"] == "x@y.pl"
    assert msg["Subject"] == "Temat"
    assert msg.get_content_type() == "text/plain"
    assert "Tresc" in msg.get_content()


def test_html_message():
    msg = build_message(
        sender="me@gmail.com", to="x@y.pl", subject="T", body="<b>hi</b>", html=True
    )
    assert msg.get_content_type() == "text/html"


def test_attachment_added(tmp_path):
    f = tmp_path / "plik.txt"
    f.write_text("zawartosc", encoding="utf-8")
    msg = build_message(
        sender="me@gmail.com", to="x@y.pl", subject="T", body="b",
        attachments=[str(f)],
    )
    names = [p.get_filename() for p in msg.iter_attachments()]
    assert "plik.txt" in names


def test_reply_headers_set():
    msg = build_message(
        sender="me@gmail.com", to="x@y.pl", subject="Re: T", body="b",
        in_reply_to="<orig@mail>", references="<orig@mail>",
    )
    assert msg["In-Reply-To"] == "<orig@mail>"
    assert msg["References"] == "<orig@mail>"
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_mime.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.mime_build`.

- [ ] **Step 3: Zaimplementuj `mime_build.py`**

```python
# src/gmail_plugin/mime_build.py
import mimetypes
from email.message import EmailMessage
from pathlib import Path


def build_message(
    sender: str,
    to: str,
    subject: str,
    body: str,
    html: bool = False,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    if html:
        # jednoczesciowa wiadomosc text/html (get_content_type() == "text/html")
        msg.set_content(body, subtype="html")
    else:
        msg.set_content(body)

    for path in attachments or []:
        p = Path(path)
        data = p.read_bytes()
        ctype, _ = mimetypes.guess_type(p.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)

    return msg
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_mime.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/mime_build.py tests/test_mime.py
git commit -m "feat(mime): budowa wiadomosci tekst/HTML/zalaczniki/reply"
```

---

## Task 5: conftest + imap_client (parsowanie i glue)

**Files:**
- Create: `tests/conftest.py`
- Create: `src/gmail_plugin/imap_client.py`
- Test: `tests/test_imap_client.py`

- [ ] **Step 1: Utwórz fake'i w `tests/conftest.py`**

```python
# tests/conftest.py
import pytest


class FakeIMAP:
    """Minimalny zamiennik imaplib.IMAP4_SSL do testow offline."""

    def __init__(self):
        self.selected = None
        self.appended = []
        self.logged_out = False
        # mapowanie: ostatnie argumenty uid() do podgladu w testach
        self.last_uid_call = None
        # zaplanowane odpowiedzi: dict[(command) -> ("OK", data)]
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
            return self.fetch_results.get(args[0], ("OK", [None]))
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
```

- [ ] **Step 2: Napisz failing test dla `imap_client`**

```python
# tests/test_imap_client.py
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
    # najnowsze (najwyzsze UID) najpierw, limit 3
    assert uids == [15, 14, 13]
    # przeszlo poprawne kryterium X-GM-RAW
    assert fake_imap.last_uid_call[1][1] == "X-GM-RAW"
```

- [ ] **Step 3: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_imap_client.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.imap_client`.

- [ ] **Step 4: Zaimplementuj `imap_client.py`**

```python
# src/gmail_plugin/imap_client.py
import email
import imaplib
from contextlib import contextmanager
from email.message import Message
from email.utils import getaddresses

from .config import (
    IMAP_HOST,
    IMAP_PORT,
    Credentials,
)

_HEADER_FIELDS = "FROM SUBJECT DATE X-GM-MSGID X-GM-THRID MESSAGE-ID"


class IMAPError(Exception):
    """Operacja IMAP zwrocila status inny niz OK."""


@contextmanager
def imap_connection(creds: Credentials):
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(creds.user, creds.password)
        yield conn
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def parse_header_response(raw: bytes) -> dict:
    msg = email.message_from_bytes(raw)
    return {
        "from": (msg.get("From") or "").strip(),
        "subject": (msg.get("Subject") or "").strip(),
        "date": (msg.get("Date") or "").strip(),
        "msgid": (msg.get("X-GM-MSGID") or "").strip(),
        "thrid": (msg.get("X-GM-THRID") or "").strip(),
        "message_id": (msg.get("Message-ID") or "").strip(),
    }


def search_uids(imap, folder: str, criteria: list[str], limit: int | None = None) -> list[int]:
    imap.select(folder, readonly=True)
    typ, data = imap.uid("SEARCH", None, *criteria)
    if typ != "OK" or not data or data[0] is None:
        return []
    ids = [int(x) for x in data[0].split()]
    ids.sort(reverse=True)  # najnowsze najpierw
    if limit is not None:
        ids = ids[:limit]
    return ids


def fetch_headers(imap, folder: str, uids: list[int]) -> list[dict]:
    if not uids:
        return []
    imap.select(folder, readonly=True)
    out: list[dict] = []
    for uid in uids:
        typ, data = imap.uid("FETCH", str(uid), f"(BODY.PEEK[HEADER.FIELDS ({_HEADER_FIELDS})])")
        if typ != "OK" or not data or data[0] is None:
            continue
        raw = data[0][1] if isinstance(data[0], tuple) else data[0]
        rec = parse_header_response(raw)
        rec["uid"] = uid
        out.append(rec)
    return out


def uid_for_gmail_id(imap, folder: str, header: str, gmail_id: str) -> int | None:
    """Znajdz UID po X-GM-MSGID lub X-GM-THRID."""
    imap.select(folder, readonly=True)
    typ, data = imap.uid("SEARCH", None, header, gmail_id)
    if typ != "OK" or not data or data[0] is None:
        return None
    ids = data[0].split()
    return int(ids[0]) if ids else None


def fetch_full(imap, folder: str, uid: int) -> Message | None:
    imap.select(folder, readonly=True)
    typ, data = imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
    if typ != "OK" or not data or data[0] is None:
        return None
    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    return email.message_from_bytes(raw)


def append_draft(imap, folder: str, message: Message) -> None:
    typ, _ = imap.append(folder, "(\\Draft)", None, message.as_bytes())
    if typ != "OK":
        raise IMAPError(f"APPEND do {folder} nieudany: {typ}")


def delete_uid(imap, folder: str, uid: int) -> None:
    imap.select(folder, readonly=False)
    typ, _ = imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)")
    if typ != "OK":
        raise IMAPError(f"STORE \\Deleted dla UID {uid} nieudany: {typ}")
    imap.expunge()


def parse_full(msg: Message) -> dict:
    body_text, body_html = "", ""
    attachments: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = part.get_content_disposition()
            ctype = part.get_content_type()
            if disp == "attachment":
                if part.get_filename():
                    attachments.append(part.get_filename())
            elif ctype == "text/plain" and not body_text:
                body_text = part.get_content()
            elif ctype == "text/html" and not body_html:
                body_html = part.get_content()
    else:
        if msg.get_content_type() == "text/html":
            body_html = msg.get_content()
        else:
            body_text = msg.get_content()
    return {
        "from": (msg.get("From") or "").strip(),
        "to": (msg.get("To") or "").strip(),
        "subject": (msg.get("Subject") or "").strip(),
        "date": (msg.get("Date") or "").strip(),
        "message_id": (msg.get("Message-ID") or "").strip(),
        "msgid": (msg.get("X-GM-MSGID") or "").strip(),
        "thrid": (msg.get("X-GM-THRID") or "").strip(),
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
    }
```

- [ ] **Step 5: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_imap_client.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py src/gmail_plugin/imap_client.py tests/test_imap_client.py
git commit -m "feat(imap): polaczenie, parsowanie naglowkow/tresci, search/fetch/append"
```

---

## Task 6: messages.py — search / get / thread

**Files:**
- Create: `src/gmail_plugin/messages.py`
- Test: `tests/test_messages.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_messages.py
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
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_messages.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.messages`.

- [ ] **Step 3: Zaimplementuj `messages.py`**

```python
# src/gmail_plugin/messages.py
from contextlib import nullcontext

from .config import ALL_MAIL_FOLDER, Credentials, load_credentials
from .imap_client import (
    fetch_full,
    fetch_headers,
    imap_connection,
    parse_full,
    search_uids,
    uid_for_gmail_id,
)
from .query import build_gmail_query, raw_criteria


def _conn(imap, creds: Credentials | None):
    if imap is not None:
        return nullcontext(imap)
    return imap_connection(creds or load_credentials())


def search(query=None, limit=20, folder="INBOX", unread=False, *, creds=None, imap=None):
    gmail_query = build_gmail_query(query, unread)
    criteria = raw_criteria(gmail_query)
    with _conn(imap, creds) as conn:
        uids = search_uids(conn, folder, criteria, limit=limit)
        return fetch_headers(conn, folder, uids)


def get(msgid, folder="INBOX", *, creds=None, imap=None):
    with _conn(imap, creds) as conn:
        uid = uid_for_gmail_id(conn, folder, "X-GM-MSGID", msgid)
        if uid is None:
            # sprobuj w calym koncie
            uid = uid_for_gmail_id(conn, ALL_MAIL_FOLDER, "X-GM-MSGID", msgid)
            folder = ALL_MAIL_FOLDER
        if uid is None:
            return None
        msg = fetch_full(conn, folder, uid)
        return parse_full(msg) if msg is not None else None


def thread(thrid, *, creds=None, imap=None):
    criteria = ["X-GM-THRID", thrid]
    with _conn(imap, creds) as conn:
        uids = search_uids(conn, ALL_MAIL_FOLDER, criteria, limit=None)
        rows = fetch_headers(conn, ALL_MAIL_FOLDER, uids)
        return sorted(rows, key=lambda r: r["uid"])
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_messages.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/messages.py tests/test_messages.py
git commit -m "feat(messages): search/get/thread przez X-GM-RAW i X-GM-THRID"
```

---

## Task 7: send.py — plan wysyłki i SMTP

**Files:**
- Create: `src/gmail_plugin/send.py`
- Test: `tests/test_send.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_send.py
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
    # nic nie wyslano
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
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_send.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.send`.

- [ ] **Step 3: Zaimplementuj `send.py`**

```python
# src/gmail_plugin/send.py
import smtplib
from contextlib import contextmanager

from .config import SMTP_HOST, SMTP_PORT, load_credentials
from .mime_build import build_message
from .messages import get as get_message


def _resolve_sender(creds, creds_user, dry_run):
    if creds_user:
        return creds_user
    if creds:
        return creds.user
    if not dry_run:
        return load_credentials().user
    return "me@gmail.com"


@contextmanager
def _smtp_ctx(smtp):
    # wstrzykniety fake albo realne SMTP_SSL; polaczenie zawsze zamkniete
    if smtp is not None:
        yield smtp
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as conn:
            yield conn


def send(
    to, subject, body, html=False, attachments=None, reply_to=None,
    dry_run=False, *, creds=None, creds_user=None, creds_password=None,
    smtp=None, imap=None,
):
    sender = _resolve_sender(creds, creds_user, dry_run)

    if dry_run:
        return {
            "dry_run": True,
            "from": sender,
            "to": to,
            "subject": subject,
            "html": html,
            "attachments": list(attachments or []),
            "reply_to": reply_to,
        }

    # naglowki watku przy odpowiedzi
    in_reply_to = references = None
    subj = subject
    if reply_to:
        original = get_message(reply_to, creds=creds, imap=imap)
        if original and original.get("message_id"):
            in_reply_to = references = original["message_id"]
            if not subj.lower().startswith("re:"):
                subj = f"Re: {subj}"

    # poswiadczenia do logowania SMTP
    if creds_password is not None:
        user, password = sender, creds_password
    else:
        c = creds or load_credentials()
        user, password, sender = c.user, c.password, c.user

    msg = build_message(
        sender=sender, to=to, subject=subj, body=body, html=html,
        attachments=attachments, in_reply_to=in_reply_to, references=references,
    )

    with _smtp_ctx(smtp) as conn:
        conn.login(user, password)
        conn.send_message(msg)
    return {"sent": True, "to": to, "subject": subj}
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_send.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/send.py tests/test_send.py
git commit -m "feat(send): plan wysylki, --dry-run bez sieci, SMTP, reply-threading"
```

---

## Task 8: drafts.py — create / list / get / send

**Files:**
- Create: `src/gmail_plugin/drafts.py`
- Test: `tests/test_drafts.py`

Wymaga `delete_uid` i `expunge` z Task 5 (dodane w `imap_client.py` / `FakeIMAP`).

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_drafts.py
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
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_drafts.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.drafts`.

- [ ] **Step 3: Zaimplementuj `drafts.py`**

```python
# src/gmail_plugin/drafts.py
from contextlib import nullcontext

from .config import DRAFTS_FOLDER, load_credentials
from .imap_client import (
    append_draft,
    delete_uid,
    fetch_full,
    fetch_headers,
    imap_connection,
    parse_full,
    search_uids,
    uid_for_gmail_id,
)
from .mime_build import build_message
from .query import raw_criteria
from .send import _resolve_sender, _smtp_ctx


def _conn(imap, creds):
    if imap is not None:
        return nullcontext(imap)
    return imap_connection(creds or load_credentials())


def create(
    to, subject, body, html=False, attachments=None, dry_run=False,
    *, creds=None, creds_user=None, imap=None,
):
    # dry-run nie wymaga .env (placeholder nadawcy), tak jak w send.send
    sender = _resolve_sender(creds, creds_user, dry_run)
    if dry_run:
        return {"dry_run": True, "from": sender, "to": to, "subject": subject,
                "html": html, "attachments": list(attachments or [])}
    msg = build_message(sender=sender, to=to, subject=subject, body=body,
                        html=html, attachments=attachments)
    with _conn(imap, creds) as conn:
        append_draft(conn, DRAFTS_FOLDER, msg)
    return {"created": True, "to": to, "subject": subject}


def list_drafts(limit=20, *, creds=None, imap=None):
    criteria = raw_criteria("in:drafts")
    with _conn(imap, creds) as conn:
        uids = search_uids(conn, DRAFTS_FOLDER, criteria, limit=limit)
        return fetch_headers(conn, DRAFTS_FOLDER, uids)


def get(msgid, *, creds=None, imap=None):
    with _conn(imap, creds) as conn:
        uid = uid_for_gmail_id(conn, DRAFTS_FOLDER, "X-GM-MSGID", msgid)
        if uid is None:
            return None
        msg = fetch_full(conn, DRAFTS_FOLDER, uid)
        return parse_full(msg) if msg is not None else None


def send(msgid, dry_run=False, *, creds=None, creds_user=None,
         creds_password=None, imap=None, smtp=None):
    if dry_run:
        return {"dry_run": True, "msgid": msgid, "action": "send-draft"}

    if creds is None and creds_password is None:
        creds = load_credentials()
    # user rozwiazywany tak jak w send.send (brak foot-guna user=None)
    user = _resolve_sender(creds, creds_user, dry_run=False)
    password = creds_password or (creds.password if creds else None)

    with _conn(imap, creds) as conn:
        uid = uid_for_gmail_id(conn, DRAFTS_FOLDER, "X-GM-MSGID", msgid)
        if uid is None:
            return None
        msg = fetch_full(conn, DRAFTS_FOLDER, uid)
        if msg is None:
            return None
        to = (msg.get("To") or "").strip()
        subject = (msg.get("Subject") or "").strip()

        with _smtp_ctx(smtp) as s:
            s.login(user, password)
            s.send_message(msg)

        delete_uid(conn, DRAFTS_FOLDER, uid)

    return {"sent": True, "to": to, "subject": subject, "deleted_draft": True}
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_drafts.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/gmail_plugin/drafts.py tests/test_drafts.py
git commit -m "feat(drafts): tworzenie/lista/get/send (APPEND, SMTP, delete po wyslaniu)"
```

---

## Task 9: cli.py — dispatcher JSON + auth-status

**Files:**
- Create: `src/gmail_plugin/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Napisz failing test**

```python
# tests/test_cli.py
import json

from gmail_plugin import cli


def test_search_command_outputs_json(monkeypatch, capsys):
    monkeypatch.setattr(cli.messages, "search", lambda **kw: [{"subject": "S", "msgid": "1"}])
    rc = cli.main(["search", "from:x", "--limit", "5"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out[0]["subject"] == "S"


def test_send_dry_run_outputs_plan(monkeypatch, capsys):
    monkeypatch.setattr(cli.send, "send", lambda **kw: {"dry_run": True, "to": kw["to"]})
    rc = cli.main(["send", "--to", "x@y.pl", "--subject", "T", "--body", "B", "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["dry_run"] is True
    assert out["to"] == "x@y.pl"


def test_auth_status_ok(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_check_auth", lambda: {"ok": True, "user": "me@gmail.com"})
    rc = cli.main(["auth-status"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["ok"] is True
```

- [ ] **Step 2: Uruchom test — ma się wywalić**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: gmail_plugin.cli`.

- [ ] **Step 3: Zaimplementuj `cli.py`**

```python
# src/gmail_plugin/cli.py
import argparse
import json
import sys

from . import drafts, messages, send
from .config import ConfigError, load_credentials
from .imap_client import imap_connection


def _emit(obj) -> int:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def _check_auth() -> dict:
    creds = load_credentials()
    with imap_connection(creds) as conn:
        conn.select("INBOX", readonly=True)
    return {"ok": True, "user": creds.user}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gmail", description="Operacje na skrzynce Gmail (IMAP/SMTP).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth-status", help="Sprawdz polaczenie i poswiadczenia.")

    p_search = sub.add_parser("search", help="Wyszukaj wiadomosci (skladnia Gmaila).")
    p_search.add_argument("query", nargs="?", default=None)
    p_search.add_argument("--limit", type=int, default=20)
    p_search.add_argument("--folder", default="INBOX")
    p_search.add_argument("--unread", action="store_true")

    p_get = sub.add_parser("get", help="Pobierz pelna wiadomosc po msgid.")
    p_get.add_argument("msgid")

    p_thread = sub.add_parser("thread", help="Pobierz watek po thrid.")
    p_thread.add_argument("thrid")

    p_send = sub.add_parser("send", help="Wyslij wiadomosc.")
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body", required=True)
    p_send.add_argument("--html", action="store_true")
    p_send.add_argument("--attach", action="append", default=None)
    p_send.add_argument("--reply-to", default=None)
    p_send.add_argument("--dry-run", action="store_true")

    p_draft = sub.add_parser("draft", help="Operacje na draftach.")
    draft_sub = p_draft.add_subparsers(dest="draft_cmd", required=True)
    d_create = draft_sub.add_parser("create")
    d_create.add_argument("--to", required=True)
    d_create.add_argument("--subject", required=True)
    d_create.add_argument("--body", required=True)
    d_create.add_argument("--html", action="store_true")
    d_create.add_argument("--attach", action="append", default=None)
    d_create.add_argument("--dry-run", action="store_true")
    d_list = draft_sub.add_parser("list")
    d_list.add_argument("--limit", type=int, default=20)
    d_get = draft_sub.add_parser("get")
    d_get.add_argument("msgid")
    d_send = draft_sub.add_parser("send")
    d_send.add_argument("msgid")
    d_send.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "auth-status":
            return _emit(_check_auth())
        if args.cmd == "search":
            return _emit(messages.search(query=args.query, limit=args.limit,
                                         folder=args.folder, unread=args.unread))
        if args.cmd == "get":
            return _emit(messages.get(args.msgid))
        if args.cmd == "thread":
            return _emit(messages.thread(args.thrid))
        if args.cmd == "send":
            return _emit(send.send(to=args.to, subject=args.subject, body=args.body,
                                   html=args.html, attachments=args.attach,
                                   reply_to=args.reply_to, dry_run=args.dry_run))
        if args.cmd == "draft":
            if args.draft_cmd == "create":
                return _emit(drafts.create(to=args.to, subject=args.subject, body=args.body,
                                           html=args.html, attachments=args.attach,
                                           dry_run=args.dry_run))
            if args.draft_cmd == "list":
                return _emit(drafts.list_drafts(limit=args.limit))
            if args.draft_cmd == "get":
                return _emit(drafts.get(args.msgid))
            if args.draft_cmd == "send":
                return _emit(drafts.send(args.msgid, dry_run=args.dry_run))
    except ConfigError as e:
        print(json.dumps({"error": "config", "message": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": "runtime", "message": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0
```

- [ ] **Step 4: Uruchom test — ma przejść**

Run: `cd /c/claude/gmail-plugin && uv run pytest tests/test_cli.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Uruchom cały zestaw testów**

Run: `cd /c/claude/gmail-plugin && uv run pytest -v`
Expected: PASS (wszystkie testy zielone).

- [ ] **Step 6: Commit**

```bash
git add src/gmail_plugin/cli.py tests/test_cli.py
git commit -m "feat(cli): dispatcher subkomend, wynik JSON, auth-status"
```

---

## Task 10: Skille (SKILL.md)

**Files:**
- Create: `skills/gmail-setup/SKILL.md`
- Create: `skills/gmail-read/SKILL.md`
- Create: `skills/gmail-send/SKILL.md`
- Create: `skills/gmail-drafts/SKILL.md`

- [ ] **Step 1: `skills/gmail-setup/SKILL.md`**

```markdown
---
name: gmail-setup
description: Use when configuring or troubleshooting Gmail access for this plugin — checking that the .env credentials exist and IMAP login works. Triggers: "skonfiguruj gmail", "czy gmail działa", "sprawdź połączenie gmail", "gmail nie loguje".
---

# gmail-setup

Weryfikuje konfigurację pluginu gmail. Poświadczenia (`GMAIL_USER`, `GMAIL_APP_PASSWORD`)
są w pliku `.env` poza repo — **nie odczytuj ani nie wypisuj jego zawartości**.

## Weryfikacja

\`\`\`bash
gmail auth-status
\`\`\`

- `{"ok": true, ...}` → konfiguracja działa.
- Błąd `config` → brak pliku `.env` lub zmiennych. Ścieżkę można nadpisać zmienną
  `GMAIL_PLUGIN_ENV`. Domyślnie plugin szuka pliku z app password użytkownika.
- Błąd logowania IMAP → w koncie Google musi być włączone **2FA** oraz **IMAP**
  (Ustawienia Gmaila → „Przekazywanie i POP/IMAP"), a hasło to **App Password** (16 znaków).

## Zasady
- Nigdy nie drukuj wartości `GMAIL_APP_PASSWORD`.
```

- [ ] **Step 2: `skills/gmail-read/SKILL.md`**

```markdown
---
name: gmail-read
description: Use when reading or searching the Gmail mailbox — listing messages by Gmail query, reading a message, or viewing a thread. Triggers: "sprawdź maile na gmailu", "znajdź wiadomość od X na gmailu", "przeczytaj nieprzeczytane gmail", "pokaż wątek".
---

# gmail-read

Odczyt i wyszukiwanie skrzynki Gmail przez IMAP (`X-GM-RAW` — natywna składnia Gmaila).
Wynik to JSON.

## Użycie

\`\`\`bash
# Wyszukiwanie skladnia Gmaila (from:, subject:, is:unread, after:, has:attachment ...)
gmail search "from:allegro is:unread" --limit 20

# Tylko nieprzeczytane z INBOX
gmail search --unread --limit 10

# Inny folder
gmail search "faktura" --folder "[Gmail]/All Mail"

# Pelna tresc wiadomosci po msgid (z wyniku search)
gmail get 17000000000000001

# Caly watek po thrid
gmail thread 17000000000000009
\`\`\`

## Zasady
- `search` zwraca From/Subject/Date/msgid/thrid. Pełną treść pobieraj `get` na żądanie.
- Nie wypisuj pełnych treści wrażliwych wiadomości bez potrzeby.
```

- [ ] **Step 3: `skills/gmail-send/SKILL.md`**

```markdown
---
name: gmail-send
description: Use when sending an email from the Gmail mailbox — plain or HTML, with attachments or as a reply. Triggers: "wyślij maila z gmaila", "odpowiedz na wiadomość gmail", "wyślij załącznik gmailem".
---

# gmail-send

Wysyłka wiadomości przez SMTP Gmaila. Gmail sam zapisuje kopię do `[Gmail]/Sent`.

## WAŻNE — akcja wychodząca
**Przed każdą realną wysyłką** pokaż użytkownikowi plan i poczekaj na zgodę.
Najpierw uruchom `--dry-run`, pokaż wynik, dopiero po akceptacji wyślij bez `--dry-run`.

## Użycie

\`\`\`bash
# 1) Podglad planu (bez wysylki, bez sieci)
gmail send --to "x@y.pl" --subject "Oferta" --body "Tresc." --dry-run

# 2) Po akceptacji — realna wysylka
gmail send --to "x@y.pl" --subject "Oferta" --body "Tresc."

# HTML + zalacznik
gmail send --to "x@y.pl" --subject "Faktura" --body "<b>W zalaczniku.</b>" --html --attach "C:\\fv\\FV.pdf"

# Odpowiedz w watku (reply-to = msgid oryginalu)
gmail send --to "x@y.pl" --subject "Re: Oferta" --body "Dziekuje." --reply-to 17000000000000001
\`\`\`
```

- [ ] **Step 4: `skills/gmail-drafts/SKILL.md`**

```markdown
---
name: gmail-drafts
description: Use when creating, listing, reading or sending Gmail drafts. Triggers: "utwórz szkic na gmailu", "zapisz wersję roboczą gmail", "pokaż szkice gmail", "wyślij szkic".
---

# gmail-drafts

Operacje na szkicach Gmaila (IMAP APPEND/SEARCH/DELETE do `[Gmail]/Drafts`).

## Użycie

\`\`\`bash
# Podglad planu szkicu
gmail draft create --to "x@y.pl" --subject "Szkic" --body "Tresc." --dry-run

# Utworz szkic
gmail draft create --to "x@y.pl" --subject "Szkic" --body "Tresc."

# Lista szkicow
gmail draft list --limit 10

# Pelna tresc szkicu po msgid (z listy)
gmail draft get 17000000000000001

# Wyslanie szkicu (usuwa go z Drafts po wyslaniu)
gmail draft send 17000000000000001 --dry-run   # podglad
gmail draft send 17000000000000001             # po akceptacji
\`\`\`

## Zasady
- `create`, `list`, `get` są bezpieczne (nie wysyłają).
- **`draft send` to akcja wychodząca** — najpierw `--dry-run`, pokaż użytkownikowi,
  wyślij dopiero po zgodzie. Po wysyłce szkic jest usuwany z `Drafts`.
```

- [ ] **Step 5: Commit**

```bash
git add skills/
git commit -m "docs(skills): gmail-setup/read/send/drafts"
```

---

## Task 11: CLAUDE.md, README.md, instalacja i junctions

**Files:**
- Create: `CLAUDE.md`
- Create: `README.md`

- [ ] **Step 1: Napisz `CLAUDE.md`**

```markdown
# CLAUDE.md

## What this is

Plugin Claude Code (`gmail`) udostępniający operacje na skrzynce Gmail przez IMAP/SMTP
jako skille: odczyt/wyszukiwanie, wysyłka, drafty. Logika w pakiecie Python `gmail_plugin`,
skille wołają CLI `gmail` (wynik JSON).

## Commands

\`\`\`bash
uv sync                 # instalacja zaleznosci
uv run pytest -v        # testy (offline, mock IMAP/SMTP)
uv tool install .       # instalacja CLI 'gmail' do ~/.local/bin
\`\`\`

## Architecture

Transport na stdlib (`imaplib`/`smtplib`/`email`). Wyszukiwanie przez rozszerzenie
Gmaila `X-GM-RAW` (natywna składnia). Identyfikatory: `msgid` = `X-GM-MSGID`,
wątek = `X-GM-THRID`. Funkcje przyjmują wstrzykiwalne `imap=`/`smtp=` (testy offline).

## Config & secrets

Poświadczenia (`GMAIL_USER`, `GMAIL_APP_PASSWORD`) w pliku `.env` poza repo;
ścieżka z `GMAIL_PLUGIN_ENV` lub domyślna. **Nigdy nie czytaj/wypisuj/loguj `.env`.**
App password wymaga 2FA i włączonego IMAP w koncie Gmail.

## Conventions

- Komunikaty po polsku; w stringach kodu/logów bez polskich znaków (encoding-safe).
- Operacje wychodzące (`send`, przyszły `draft send`) — human-in-the-loop: plan → zgoda → wysyłka.
- Testy: każda operacja ma test, `--dry-run` nie dotyka sieci, sekret nigdy nie trafia do outputu.
```

- [ ] **Step 2: Napisz `README.md`**

```markdown
# gmail — plugin Claude Code

Operacje na skrzynce Gmail przez IMAP/SMTP (app password): odczyt/wyszukiwanie,
wysyłka, drafty.

## Instalacja

\`\`\`bash
cd C:\claude\gmail-plugin
uv sync
uv tool install .            # -> ~/.local/bin/gmail.exe
\`\`\`

Konfiguracja: plik `.env` z `GMAIL_USER` i `GMAIL_APP_PASSWORD` (16-znakowy App
Password; wymaga 2FA i włączonego IMAP). Ścieżkę wskazuje zmienna `GMAIL_PLUGIN_ENV`.

Weryfikacja: `gmail auth-status`.

## Eksponowanie skilli globalnie (Windows junctions)

\`\`\`powershell
$src = "C:\claude\gmail-plugin\skills"
Get-ChildItem $src -Directory | ForEach-Object {
  $link = Join-Path "$env:USERPROFILE\.claude\skills" $_.Name
  if (-not (Test-Path $link)) { New-Item -ItemType Junction -Path $link -Target $_.FullName }
}
\`\`\`

Jeśli plugin zmieni lokalizację — zaktualizuj ścieżki w README/CLAUDE.md i odtwórz junctions.

## Skille

- `gmail-setup` — weryfikacja konfiguracji
- `gmail-read` — search / get / thread
- `gmail-send` — wysyłka (za zgodą)
- `gmail-drafts` — tworzenie/lista szkiców
```

- [ ] **Step 3: Zainstaluj CLI i zrób smoke test (offline)**

Run: `cd /c/claude/gmail-plugin && uv tool install . && gmail --help`
Expected: pomoc CLI z subkomendami `auth-status, search, get, thread, send, draft`.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: CLAUDE.md i README (instalacja, junctions, konwencje)"
```

---

## Self-Review (wykonane przy pisaniu planu)

**Spec coverage:**
- Transport IMAP/SMTP + X-GM-RAW → Task 3, 5, 6. ✓
- Odczyt/wyszukiwanie/get/thread → Task 6. ✓
- Wysyłka + reply + dry-run → Task 7. ✓
- Drafty: create/list/get/send (APPEND, SMTP, delete) → Task 8. ✓
- Sekrety z `.env`, redakcja, inwariant „brak hasła w outpucie" → Task 2 (repr), 7 (test_plan_never_contains_password). ✓
- auth-status (setup) → Task 9 + skill Task 10. ✓
- CLI JSON, dry-run bez sieci → Task 9, 7, 8. ✓
- Skille + dokumentacja + instalacja/junctions → Task 10, 11. ✓
- Poza zakresem (etykiety/OAuth/push) — nieujęte, zgodnie ze spec. ✓

**Uwagi do implementacji:**
- `send.send` ma rozbudowaną logikę poświadczeń (dry-run bez sieci vs realna wysyłka) —
  przy implementacji trzymaj się testów z Task 7 jako kontraktu; uprość, jeśli da się
  zachować zachowanie testów.
- `draft send` (Task 8) wysyła szkic przez SMTP i usuwa go z `Drafts` (\\Deleted + expunge).
  To akcja wychodząca — skill wymaga `--dry-run` + zgody użytkownika przed realną wysyłką.
```

