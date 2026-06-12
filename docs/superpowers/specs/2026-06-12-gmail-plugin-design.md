# Gmail plugin — projekt (design)

**Data:** 2026-06-12
**Status:** zatwierdzony do napisania planu implementacji
**Autor:** micha + Claude

## Cel

Plugin Claude Code `gmail` udostępniający operacje na skrzynce Gmail jako skille:
odczyt/wyszukiwanie, wysyłka i drafty. Wzorowany strukturalnie na istniejącym
pluginie `home-pl`.

## Kluczowa decyzja: transport IMAP/SMTP (nie REST API)

Dostępne poświadczenie to **App Password** (`GMAIL_APP_PASSWORD`, 16 znaków).
Gmail REST API **nie akceptuje** haseł aplikacji — wymaga OAuth2. App password
działa wyłącznie z IMAP/SMTP. Dlatego plugin używa IMAP/SMTP.

Nie tracimy natywnej składni wyszukiwania Gmaila: rozszerzenie IMAP **`X-GM-RAW`**
pozwala wykonywać zapytania w składni Gmaila (`from:`, `is:unread`, `after:` itd.).
Wątki i identyfikatory globalne dostępne przez `X-GM-THRID` / `X-GM-MSGID`.

| Operacja | Mechanizm |
|----------|-----------|
| Odczyt/wyszukiwanie | IMAP `imap.gmail.com:993` (SSL), `X-GM-RAW` |
| Wysyłka | SMTP `smtp.gmail.com:465` (SSL) |
| Drafty | IMAP `APPEND` do `[Gmail]/Drafts` z flagą `\Draft` |

Gmail automatycznie zapisuje wiadomości wysłane przez SMTP do `[Gmail]/Sent`
— w przeciwieństwie do home.pl nie trzeba ręcznie dopisywać kopii do Sent.

## Stack i zależności

- **Python 3.11+**, zarządzane przez `uv`.
- Logika transportu: **biblioteka standardowa** — `imaplib`, `smtplib`, `email`.
- Zależność runtime: `python-dotenv` (odczyt pliku `.env`).
- CLI: `argparse` (stdlib, zero zależności).
- Dev: `pytest`.

Lekki zestaw zależności jest celowy — szybka instalacja, mało powierzchni błędu.

## Architektura

**Jeden CLI, cienkie skille** — analogicznie do `graphify` i wzorca `home-pl`.
Cała logika w pakiecie `gmail_plugin`; skille (`SKILL.md`) to proza wołająca
komendę `gmail <subkomenda>`. CLI zwraca **JSON**, żeby Claude łatwo parsował.

```
C:\claude\gmail-plugin\
  .claude-plugin/plugin.json      # manifest pluginu (name: gmail)
  pyproject.toml                  # uv; dep: python-dotenv; dev: pytest;
                                  #   console_scripts: gmail = gmail_plugin.cli:main
  CLAUDE.md  README.md
  src/gmail_plugin/
    __init__.py
    config.py      # odczyt .env, walidacja, dostawca poświadczeń (user, password)
    imap_client.py # połączenie IMAP, X-GM-RAW search, fetch, APPEND (drafty)
    messages.py    # odczyt/wyszukiwanie: search / get / thread, parsowanie MIME
    send.py        # budowa MIME (tekst/HTML/załączniki/reply), wysyłka SMTP
    drafts.py      # drafty: create / list / get / send
    cli.py         # dispatcher subkomend -> JSON, obsługa --dry-run
  tests/
    test_query.py  test_mime.py  test_config.py  test_dryrun.py
  skills/
    gmail-setup/SKILL.md
    gmail-read/SKILL.md
    gmail-send/SKILL.md
    gmail-drafts/SKILL.md
  docs/superpowers/specs/2026-06-12-gmail-plugin-design.md   # ten plik
```

Instalacja: `uv tool install C:\claude\gmail-plugin` → binarka `~/.local/bin/gmail.exe`
(jak `graphify`). Skille rejestrowane przez plugin; opcjonalnie eksponowane globalnie
przez junction points w `~/.claude/skills/` (snippet w README, jak w home-pl).

## Poświadczenia i konfiguracja

- **Źródło:** plik `.env` (`GMAIL_USER`, `GMAIL_APP_PASSWORD`), domyślnie pod ścieżką
  z sekretów użytkownika; nadpisywalne zmienną `GMAIL_PLUGIN_ENV`.
- `config.py` waliduje obecność obu zmiennych. Brak → błąd kierujący do skilla
  `gmail-setup`, bez wypisywania wartości.
- Poświadczenia są wyłącznie do użytku wewnętrznego (login IMAP/SMTP).
  **Nigdy nie trafiają do outputu, planu, błędu ani logu.**

> Plik `.env` jest poufny. Claude **nie odczytuje, nie wyświetla i nie loguje**
> jego zawartości — czyta go tylko proces pluginu w czasie działania.

## Powierzchnia skilli i CLI

| Skill | Subkomendy | Uwagi |
|-------|------------|-------|
| `gmail-setup` | `gmail auth-status` | Weryfikuje obecność pliku/zmiennych i że logowanie IMAP działa (IMAP musi być włączony w koncie + 2FA). Nie drukuje sekretów. Instrukcja naprawy przy braku. |
| `gmail-read` | `gmail search "<query>"` (`--limit`, `--folder`, `--unread`), `gmail get <msgid>`, `gmail thread <thrid>` | Składnia Gmaila przez `X-GM-RAW`. Domyślnie From/Subject/Date/id; pełna treść na żądanie. |
| `gmail-send` | `gmail send --to … --subject … --body …` (`--html`, `--attach`, `--reply-to <msgid>`, `--dry-run`) | **Akcja wychodząca — zawsze plan do potwierdzenia przed wysyłką.** |
| `gmail-drafts` | `gmail draft create … `, `gmail draft list`, `gmail draft get <id>`, `gmail draft send <id>` | `draft send` też wymaga potwierdzenia; po wysyłce usuwa z `Drafts`. |

**Identyfikatory:** publiczny `msgid` = `X-GM-MSGID` (globalnie stabilny), `thrid` =
`X-GM-THRID`. `get`/`thread` lokalizują wiadomość przez `UID SEARCH X-GM-MSGID/THRID`.

**Reply/threading:** `--reply-to <msgid>` pobiera oryginał, ustawia nagłówki
`In-Reply-To` i `References` oraz temat `Re: …`, aby Gmail powiązał wątek.

## Bezpieczeństwo i human-in-the-loop

- Każda operacja wychodząca (`send`, `draft send`) — najpierw plan do akceptacji
  użytkownika, dopiero potem wykonanie. Skill instruuje Claude, by pokazał plan.
- `--dry-run` na operacjach wychodzących zwraca obiekt planu
  (odbiorcy / temat / załączniki / flaga HTML) **bez** sekretów i **bez** kontaktu
  z serwerem.
- Sekrety nigdy nie są drukowane; w komunikatach błędu hasło jest redagowane.
- `.env` jest poza repo; `.gitignore` chroni przed przypadkowym commitem sekretów.
- Wymagania konta: włączone **2FA** i **IMAP** w ustawieniach Gmaila — inaczej login
  IMAP zwróci błąd; `gmail-setup` podpowiada przyczynę.

## Testy (offline, jak Pester w home-pl)

`pytest` z mockowanym `imaplib`/`smtplib` (monkeypatch). Każda operacja ma testy:

1. **Budowa zapytania** — poprawne cytowanie/escapowanie `X-GM-RAW`.
2. **Budowa MIME** — tekst, HTML, załącznik, nagłówki reply (`In-Reply-To`/`References`).
3. **Konfiguracja** — brak zmiennych → czytelny błąd; wczytane poświadczenia
   nigdy nie pojawiają się w żadnym planie/stringu outputu.
4. **Inwariant sekretu** — serializowany plan/output nigdy nie zawiera wartości
   `GMAIL_APP_PASSWORD`.
5. **Dry-run** — operacja wychodząca z `--dry-run` nie nawiązuje połączenia.

## Konwencje (z home-pl)

- Komentarze i komunikaty do użytkownika po polsku.
- Identyfikatory/kod po angielsku; bez polskich znaków w stringach logów
  (encoding-safe).
- Operacje destrukcyjne/wychodzące zawsze human-in-the-loop.

## Poza zakresem (YAGNI)

- OAuth2 / Gmail REST API (zablokowane przez app password; osobny setup w razie potrzeby).
- Etykiety, archiwizacja, kosz, push/Pub-Sub, ustawienia konta (filtry/vacation/forwarding).
- Obsługa wielu kont (jedno konto z `.env`).
