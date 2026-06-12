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
from .send import _smtp_ctx


def _conn(imap, creds):
    if imap is not None:
        return nullcontext(imap)
    return imap_connection(creds or load_credentials())


def create(
    to, subject, body, html=False, attachments=None, dry_run=False,
    *, creds=None, creds_user=None, imap=None,
):
    sender = creds_user or (creds.user if creds else None)
    if sender is None:
        creds = creds or load_credentials()
        sender = creds.user
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
    user = creds_user or (creds.user if creds else None)
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

        # Usuniecie szkicu jest best-effort; mail jest juz wyslany, jesli tu dotarlismy.
        delete_uid(conn, DRAFTS_FOLDER, uid)

    return {"sent": True, "to": to, "subject": subject, "deleted_draft": True}
