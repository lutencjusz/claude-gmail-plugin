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


def test_draft_send_dry_run_wiring(monkeypatch, capsys):
    captured = {}
    def fake_draft_send(msgid, dry_run=False):
        captured["msgid"] = msgid
        captured["dry_run"] = dry_run
        return {"dry_run": dry_run, "msgid": msgid, "action": "send-draft"}
    monkeypatch.setattr(cli.drafts, "send", fake_draft_send)
    rc = cli.main(["draft", "send", "555", "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert captured == {"msgid": "555", "dry_run": True}
    assert out["action"] == "send-draft"


def test_config_error_returns_code_2(monkeypatch, capsys):
    from gmail_plugin.config import ConfigError
    def boom():
        raise ConfigError("brak .env")
    monkeypatch.setattr(cli, "_check_auth", boom)
    rc = cli.main(["auth-status"])
    err = capsys.readouterr().err
    assert rc == 2
    assert json.loads(err)["error"] == "config"
