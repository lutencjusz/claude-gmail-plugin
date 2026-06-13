# gmail — plugin Claude Code

Operacje na skrzynce Gmail przez IMAP/SMTP (App Password): odczyt/wyszukiwanie,
wysyłka i drafty. Dostarcza skille Claude Code (`gmail-setup`, `gmail-read`,
`gmail-send`, `gmail-drafts`) oparte o CLI `gmail`.

> Poświadczenia trzymane są w pliku `.env` **poza repozytorium**. Plugin nigdy
> nie zawiera ani nie loguje kluczy dostępowych.

## Instalacja

Instalacja składa się z dwóch części: **skille** (przez marketplace Claude Code)
oraz **backend CLI** (`gmail`, pakiet Python).

### 1. Skille — marketplace Claude Code

W Claude Code:

```
/plugin marketplace add lutencjusz/claude-gmail-plugin
/plugin install gmail@claude-gmail-plugin
```

### 2. Backend CLI `gmail`

Skille wołają binarkę `gmail`. Zainstaluj ją z repozytorium (wymaga
[uv](https://docs.astral.sh/uv/)):

```bash
uv tool install git+https://github.com/lutencjusz/claude-gmail-plugin.git
# -> ~/.local/bin/gmail(.exe)
```

Alternatywnie, z lokalnego klona:

```bash
git clone https://github.com/lutencjusz/claude-gmail-plugin.git
cd claude-gmail-plugin
uv tool install .
```

### 3. Konfiguracja poświadczeń

1. Włącz **2FA** i **IMAP** w koncie Gmail (Ustawienia → „Przekazywanie i POP/IMAP").
2. Wygeneruj 16-znakowy **App Password**: https://myaccount.google.com/apppasswords
3. Utwórz plik `.env` (wzór: [`.env.example`](.env.example)). Domyślna lokalizacja:
   `~/.secrets/gmail-plugin.env`. Inną ścieżkę wskazuje zmienna `GMAIL_PLUGIN_ENV`.

   ```ini
   GMAIL_USER=twoj.adres@gmail.com
   GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
   ```

4. Weryfikacja:

   ```bash
   gmail auth-status
   ```

   `{"ok": true, ...}` → gotowe.

## Skille

- `gmail-setup` — weryfikacja konfiguracji i połączenia
- `gmail-read` — search / get / thread
- `gmail-send` — wysyłka (od razu; `--dry-run` pokazuje plan bez wysyłki)
- `gmail-drafts` — tworzenie / lista / get / send szkiców

## Bezpieczeństwo

- `.env` jest w `.gitignore` i **nigdy** nie trafia do repozytorium.
- `Credentials.__repr__` redaguje hasło; sekret nie jest serializowany do outputu.
- Operacje wychodzące wysyłają od razu; `--dry-run` pozwala podejrzeć plan bez sieci.

## Rozwój

```bash
uv sync              # zależności
uv run pytest -v     # testy (offline, mock IMAP/SMTP)
```

## Licencja

[MIT](LICENSE)
