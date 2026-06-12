# gmail — plugin Claude Code

Operacje na skrzynce Gmail przez IMAP/SMTP (app password): odczyt/wyszukiwanie,
wysyłka, drafty.

## Instalacja

```bash
cd C:\claude\gmail-plugin
uv sync
uv tool install .            # -> ~/.local/bin/gmail.exe
```

Konfiguracja: plik `.env` z `GMAIL_USER` i `GMAIL_APP_PASSWORD` (16-znakowy App
Password; wymaga 2FA i włączonego IMAP). Ścieżkę wskazuje zmienna `GMAIL_PLUGIN_ENV`.

Weryfikacja: `gmail auth-status`.

## Eksponowanie skilli globalnie (Windows junctions)

```powershell
$src = "C:\claude\gmail-plugin\skills"
Get-ChildItem $src -Directory | ForEach-Object {
  $link = Join-Path "$env:USERPROFILE\.claude\skills" $_.Name
  if (-not (Test-Path $link)) { New-Item -ItemType Junction -Path $link -Target $_.FullName }
}
```

Jeśli plugin zmieni lokalizację — zaktualizuj ścieżki w README/CLAUDE.md i odtwórz junctions.

## Skille

- `gmail-setup` — weryfikacja konfiguracji
- `gmail-read` — search / get / thread
- `gmail-send` — wysyłka (za zgodą)
- `gmail-drafts` — tworzenie / lista / get / send szkiców
