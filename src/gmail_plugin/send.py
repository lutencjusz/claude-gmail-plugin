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
    # wstrzykniety fake albo realne SMTP_SSL; polaczenie zawsze zamkniete.
    # Reuzywane przez drafts.send.
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
