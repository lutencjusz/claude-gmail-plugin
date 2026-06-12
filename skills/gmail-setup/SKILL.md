---
name: gmail-setup
description: Use when configuring or troubleshooting Gmail access for this plugin — checking that the .env credentials exist and IMAP login works. Triggers: "skonfiguruj gmail", "czy gmail działa", "sprawdź połączenie gmail", "gmail nie loguje".
---

# gmail-setup

Weryfikuje konfigurację pluginu gmail. Poświadczenia (`GMAIL_USER`, `GMAIL_APP_PASSWORD`)
są w pliku `.env` poza repo — **nie odczytuj ani nie wypisuj jego zawartości**.

## Weryfikacja

```bash
gmail auth-status
```

- `{"ok": true, ...}` → konfiguracja działa.
- Błąd `config` → brak pliku `.env` lub zmiennych. Ścieżkę można nadpisać zmienną
  `GMAIL_PLUGIN_ENV`. Domyślnie plugin szuka pliku z app password użytkownika.
- Błąd logowania IMAP → w koncie Google musi być włączone **2FA** oraz **IMAP**
  (Ustawienia Gmaila → „Przekazywanie i POP/IMAP"), a hasło to **App Password** (16 znaków).

## Zasady
- Nigdy nie drukuj wartości `GMAIL_APP_PASSWORD`.
