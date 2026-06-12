import pytest
from gmail_plugin.config import load_credentials, ConfigError, Credentials


def _write_env(tmp_path, body):
    p = tmp_path / "creds.env"
    p.write_text(body, encoding="utf-8")
    return p


def test_loads_user_and_password(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\nGMAIL_APP_PASSWORD=abcdefghijklmnop\n")
    creds = load_credentials(env)
    assert creds.user == "me@gmail.com"
    assert creds.password == "abcdefghijklmnop"


def test_missing_password_raises_configerror(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\n")
    with pytest.raises(ConfigError):
        load_credentials(env)


def test_missing_file_raises_configerror(tmp_path):
    with pytest.raises(ConfigError):
        load_credentials(tmp_path / "nope.env")


def test_repr_redacts_password(tmp_path):
    env = _write_env(tmp_path, "GMAIL_USER=me@gmail.com\nGMAIL_APP_PASSWORD=secret1234567890\n")
    creds = load_credentials(env)
    assert "secret1234567890" not in repr(creds)
    assert "redacted" in repr(creds).lower()
