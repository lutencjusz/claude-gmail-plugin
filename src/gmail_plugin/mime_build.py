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
