import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
DRAFTS_FOLDER = "[Gmail]/Drafts"
ALL_MAIL_FOLDER = "[Gmail]/All Mail"


class ConfigError(Exception):
    """Brak/niekompletna konfiguracja poswiadczen Gmaila."""


@dataclass(frozen=True)
class Credentials:
    user: str
    password: str

    def __repr__(self) -> str:
        return f"Credentials(user={self.user!r}, password=<redacted>)"

    # UWAGA: __repr__/__str__ redaguja haslo, ale dataclasses.asdict(creds)
    # zwroci je jawnie. Nie serializuj Credentials do logow/outputu.


def default_env_path() -> Path:
    override = os.environ.get("GMAIL_PLUGIN_ENV")
    if override:
        return Path(override)
    return Path.home() / ".secrets" / "daily-political-digest.env"


def load_credentials(env_path: Path | None = None) -> Credentials:
    path = Path(env_path) if env_path is not None else default_env_path()
    if not path.is_file():
        raise ConfigError(
            f"Nie znaleziono pliku .env: {path}. Uruchom skill gmail-setup."
        )
    values = dotenv_values(path)
    user = (values.get("GMAIL_USER") or "").strip()
    password = (values.get("GMAIL_APP_PASSWORD") or "").strip()
    if not user or not password:
        raise ConfigError(
            "Brak GMAIL_USER lub GMAIL_APP_PASSWORD w pliku .env. Uruchom skill gmail-setup."
        )
    return Credentials(user=user, password=password)
