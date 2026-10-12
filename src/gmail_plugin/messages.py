from contextlib import nullcontext

from .config import ALL_MAIL_FOLDER, Credentials, load_credentials
from .imap_client import (
    fetch_full,
    fetch_headers,
    imap_connection,
    parse_full,
    resolve_special_folder,
    search_uids,
    uid_for_gmail_id,
)
from .query import build_gmail_query, raw_criteria


def _conn(imap, creds: Credentials | None):
    if imap is not None:
        return nullcontext(imap)
    return imap_connection(creds or load_credentials())


def _all_mail(conn):
    return resolve_special_folder(conn, "\\All", ALL_MAIL_FOLDER)


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
            folder = _all_mail(conn)
            uid = uid_for_gmail_id(conn, folder, "X-GM-MSGID", msgid)
        if uid is None:
            return None
        msg = fetch_full(conn, folder, uid)
        return parse_full(msg) if msg is not None else None


def thread(thrid, *, creds=None, imap=None):
    criteria = ["X-GM-THRID", thrid]
    with _conn(imap, creds) as conn:
        folder = _all_mail(conn)
        uids = search_uids(conn, folder, criteria, limit=None)
        rows = fetch_headers(conn, folder, uids)
        return sorted(rows, key=lambda r: r["uid"])
