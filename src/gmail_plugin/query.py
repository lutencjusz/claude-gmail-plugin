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
