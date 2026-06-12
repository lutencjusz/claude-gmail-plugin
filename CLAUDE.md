# CLAUDE.md

## What this is

Plugin Claude Code (`gmail`) udostępniający operacje na skrzynce Gmail przez IMAP/SMTP
jako skille: odczyt/wyszukiwanie, wysyłka, drafty. Logika w pakiecie Python `gmail_plugin`,
skille wołają CLI `gmail` (wynik JSON).

## Commands

```bash
uv sync                 # instalacja zaleznosci
uv run pytest -v        # testy (offline, mock IMAP/SMTP)
uv tool install .       # instalacja CLI 'gmail' do ~/.local/bin
```

## Architecture

Transport na stdlib (`imaplib`/`smtplib`/`email`). Wyszukiwanie przez rozszerzenie
Gmaila `X-GM-RAW` (natywna składnia). Identyfikatory: `msgid` = `X-GM-MSGID`,
wątek = `X-GM-THRID`. Funkcje przyjmują wstrzykiwalne `imap=`/`smtp=` (testy offline).
`_smtp_ctx` (send.py) to wspólny kontekst SMTP, reużywany przez `drafts.send`.

## Config & secrets

Poświadczenia (`GMAIL_USER`, `GMAIL_APP_PASSWORD`) w pliku `.env` poza repo;
ścieżka z `GMAIL_PLUGIN_ENV` lub domyślna. **Nigdy nie czytaj/wypisuj/loguj `.env`.**
App password wymaga 2FA i włączonego IMAP w koncie Gmail.

## Conventions

- Komunikaty po polsku; w stringach kodu/logów bez polskich znaków (encoding-safe).
- Operacje wychodzące (`send`, `draft send`) — human-in-the-loop: plan → zgoda → wysyłka.
- Testy: każda operacja ma test, `--dry-run` nie dotyka sieci, sekret nigdy nie trafia do outputu.
