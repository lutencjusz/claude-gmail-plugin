import email
import email.policy
import imaplib
import re
from contextlib import contextmanager
from email.message import Message

from .config import (
    IMAP_HOST,
    IMAP_PORT,
    Credentials,
)

# X-GM-MSGID / X-GM-THRID to atrybuty rozszerzenia Gmaila (FETCH items), a NIE
# naglowki RFC822 — przychodza w metadanych odpowiedzi FETCH, nie w tresci naglowka.
_HEADER_FIELDS = "FROM SUBJECT DATE MESSAGE-ID"
_GM_MSGID_RE = re.compile(rb"X-GM-MSGID\s+(\d+)")
_GM_THRID_RE = re.compile(rb"X-GM-THRID\s+(\d+)")


class IMAPError(Exception):
    """Operacja IMAP zwrocila status inny niz OK."""


def _quote_mailbox(name: str) -> str:
    """imaplib.select nie cytuje nazw; nazwy ze spacja (np. 'Wersje robocze') psuja komende."""
    if name.startswith('"') or not re.search(r'[\s"\()]', name):
        return name
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _select(imap, folder: str, readonly: bool = True) -> None:
    typ, data = imap.select(_quote_mailbox(folder), readonly=readonly)
    if typ != "OK":
        raise IMAPError(f"Nie mozna otworzyc folderu {folder}: {typ} {data}")


_LIST_RE = re.compile(rb'\((?P<attrs>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$')


def resolve_special_folder(imap, attribute: str, default: str) -> str:
    """Nazwa folderu po atrybucie special-use (np. Drafts, All), niezalezna od jezyka konta.

    Gmail lokalizuje nazwy ('[Gmail]/Wersje robocze'); atrybut jest staly. Zwraca nazwe
    w formie z LIST (modified UTF-7), ktora mozna od razu podac do SELECT/APPEND.
    """
    try:
        typ, data = imap.list()
    except Exception:
        return default
    if typ != "OK":
        return default
    wanted = attribute.lower().encode()
    for line in data or []:
        if not isinstance(line, bytes):
            continue
        m = _LIST_RE.match(line.strip())
        if not m or wanted not in m.group("attrs").lower().split():
            continue
        name = m.group("name").strip()
        if name.startswith(b'"') and name.endswith(b'"'):
            name = name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
        return name.decode("ascii", "replace")
    return default


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
    _select(imap, folder, readonly=True)
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
    _select(imap, folder, readonly=True)
    out: list[dict] = []
    for uid in uids:
        typ, data = imap.uid(
            "FETCH",
            str(uid),
            f"(X-GM-MSGID X-GM-THRID BODY.PEEK[HEADER.FIELDS ({_HEADER_FIELDS})])",
        )
        if typ != "OK" or not data or data[0] is None:
            continue
        if isinstance(data[0], tuple):
            meta, raw = data[0][0], data[0][1]
        else:
            meta, raw = data[0], b""
        rec = parse_header_response(raw)
        # msgid/thrid czytamy z metadanych FETCH, bo to atrybuty Gmaila, nie naglowki
        m = _GM_MSGID_RE.search(meta or b"")
        t = _GM_THRID_RE.search(meta or b"")
        if m:
            rec["msgid"] = m.group(1).decode()
        if t:
            rec["thrid"] = t.group(1).decode()
        rec["uid"] = uid
        out.append(rec)
    return out


def uid_for_gmail_id(imap, folder: str, header: str, gmail_id: str) -> int | None:
    """Znajdz UID po X-GM-MSGID lub X-GM-THRID."""
    _select(imap, folder, readonly=True)
    typ, data = imap.uid("SEARCH", None, header, gmail_id)
    if typ != "OK" or not data or data[0] is None:
        return None
    ids = data[0].split()
    return int(ids[0]) if ids else None


def fetch_full(imap, folder: str, uid: int) -> Message | None:
    _select(imap, folder, readonly=True)
    typ, data = imap.uid("FETCH", str(uid), "(BODY.PEEK[])")
    if typ != "OK" or not data or data[0] is None:
        return None
    raw = data[0][1] if isinstance(data[0], tuple) else data[0]
    return email.message_from_bytes(raw, policy=email.policy.default)


def append_draft(imap, folder: str, message: Message) -> None:
    typ, _ = imap.append(_quote_mailbox(folder), "(\\Draft)", None, message.as_bytes())
    if typ != "OK":
        raise IMAPError(f"APPEND do {folder} nieudany: {typ}")


def delete_uid(imap, folder: str, uid: int) -> None:
    _select(imap, folder, readonly=False)
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
