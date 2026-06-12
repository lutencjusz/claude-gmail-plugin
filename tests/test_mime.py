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
