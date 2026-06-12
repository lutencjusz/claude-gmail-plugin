---
name: gmail-drafts
description: Use when creating, listing, reading or sending Gmail drafts. Triggers: "utwórz szkic na gmailu", "zapisz wersję roboczą gmail", "pokaż szkice gmail", "wyślij szkic".
---

# gmail-drafts

Operacje na szkicach Gmaila (IMAP APPEND/SEARCH/DELETE do `[Gmail]/Drafts`).

## Użycie

```bash
# Podglad planu szkicu
gmail draft create --to "x@y.pl" --subject "Szkic" --body "Tresc." --dry-run

# Utworz szkic
gmail draft create --to "x@y.pl" --subject "Szkic" --body "Tresc."

# Lista szkicow
gmail draft list --limit 10

# Pelna tresc szkicu po msgid (z listy)
gmail draft get 17000000000000001

# Wyslanie szkicu (usuwa go z Drafts po wyslaniu)
gmail draft send 17000000000000001 --dry-run   # podglad
gmail draft send 17000000000000001             # po akceptacji
```

## Zasady
- `create`, `list`, `get` są bezpieczne (nie wysyłają).
- **`draft send` to akcja wychodząca** — najpierw `--dry-run`, pokaż użytkownikowi,
  wyślij dopiero po zgodzie. Po wysyłce szkic jest usuwany z `Drafts`.
