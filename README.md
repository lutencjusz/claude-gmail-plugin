# gmail — Claude Code plugin

Gmail mailbox operations over IMAP/SMTP (App Password): read/search, send and
drafts. Ships Claude Code skills (`gmail-setup`, `gmail-read`, `gmail-send`,
`gmail-drafts`) backed by the `gmail` CLI.

> Credentials live in a `.env` file **outside the repository**. The plugin never
> contains or logs access keys.

## Installation

Installation has two parts: the **skills** (via the Claude Code marketplace) and
the **CLI backend** (`gmail`, a Python package).

### 1. Skills — Claude Code marketplace

In Claude Code:

```
/plugin marketplace add lutencjusz/claude-gmail-plugin
/plugin install gmail@claude-gmail-plugin
```

### 2. The `gmail` CLI backend

The skills call the `gmail` binary. Install it from the repository (requires
[uv](https://docs.astral.sh/uv/)):

```bash
uv tool install git+https://github.com/lutencjusz/claude-gmail-plugin.git
# -> ~/.local/bin/gmail(.exe)
```

Alternatively, from a local clone:

```bash
git clone https://github.com/lutencjusz/claude-gmail-plugin.git
cd claude-gmail-plugin
uv tool install .
```

### 3. Configure credentials

1. Enable **2FA** and **IMAP** on your Gmail account (Settings → "Forwarding and POP/IMAP").
2. Generate a 16-character **App Password**: https://myaccount.google.com/apppasswords
3. Create a `.env` file (see [`.env.example`](.env.example)). Default location:
   `~/.secrets/gmail-plugin.env`. Override the path with the `GMAIL_PLUGIN_ENV`
   environment variable.

   ```ini
   GMAIL_USER=your.address@gmail.com
   GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
   ```

4. Verify:

   ```bash
   gmail auth-status
   ```

   `{"ok": true, ...}` → you're set.

## Skills

- `gmail-setup` — verify configuration and connectivity
- `gmail-read` — search / get / thread
- `gmail-send` — send (immediate; `--dry-run` previews the plan without sending)
- `gmail-drafts` — create / list / get / send drafts

## Security

- `.env` is in `.gitignore` and **never** reaches the repository.
- `Credentials.__repr__` redacts the password; the secret is not serialized to output.
- Outgoing operations send immediately; use `--dry-run` to preview the plan without network access.

## Development

```bash
uv sync              # dependencies
uv run pytest -v     # tests (offline, mocked IMAP/SMTP)
```

## License

[MIT](LICENSE)
