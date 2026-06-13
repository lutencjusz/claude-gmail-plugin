---
name: gmail-send
description: Use when sending an email from the Gmail mailbox — plain or HTML, with attachments or as a reply. Triggers: "wyślij maila z gmaila", "odpowiedz na wiadomość gmail", "wyślij załącznik gmailem".
---

# gmail-send

Wysyłka wiadomości przez SMTP Gmaila. Gmail sam zapisuje kopię do `[Gmail]/Sent`.

## Wysyłka

**Wysyłaj od razu** bez dry-run i bez pytania o potwierdzenie.

### Markdown → HTML (automatycznie)
Jeśli treść lub plik źródłowy jest w formacie Markdown (`.md`):
1. Skonwertuj do HTML (callout `[!type]` → kolorowe `div`, wikilinki `[[x]]` → tekst `x`, nagłówki, listy, pogrubienia — standardowy Markdown HTML).
2. Dodaj `--html` do komendy.
3. Nie pytaj użytkownika o zgodę na konwersję — rób to automatycznie.

## Użycie

```bash
# 1) Podglad planu (bez wysylki, bez sieci)
gmail send --to "x@y.pl" --subject "Oferta" --body "Tresc." --dry-run

# 2) Po akceptacji — realna wysylka
gmail send --to "x@y.pl" --subject "Oferta" --body "Tresc."

# HTML + zalacznik
gmail send --to "x@y.pl" --subject "Faktura" --body "<b>W zalaczniku.</b>" --html --attach "C:\\fv\\FV.pdf"

# Odpowiedz w watku (reply-to = msgid oryginalu)
gmail send --to "x@y.pl" --subject "Re: Oferta" --body "Dziekuje." --reply-to 17000000000000001
```
