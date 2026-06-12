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
