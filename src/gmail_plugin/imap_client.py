import email
import imaplib
from contextlib import contextmanager
from email.message import Message

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
