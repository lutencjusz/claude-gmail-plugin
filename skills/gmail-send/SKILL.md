---
name: gmail-send
description: Use when sending an email from the Gmail mailbox — plain or HTML, with attachments or as a reply. Triggers: "wyślij maila z gmaila", "odpowiedz na wiadomość gmail", "wyślij załącznik gmailem".
---

# gmail-send

Wysyłka wiadomości przez SMTP Gmaila. Gmail sam zapisuje kopię do `[Gmail]/Sent`.

## WAŻNE — akcja wychodząca
**Przed każdą realną wysyłką** pokaż użytkownikowi plan i poczekaj na zgodę.
Najpierw uruchom `--dry-run`, pokaż wynik, dopiero po akceptacji wyślij bez `--dry-run`.

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
