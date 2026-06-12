---
name: gmail-read
description: Use when reading or searching the Gmail mailbox — listing messages by Gmail query, reading a message, or viewing a thread. Triggers: "sprawdź maile na gmailu", "znajdź wiadomość od X na gmailu", "przeczytaj nieprzeczytane gmail", "pokaż wątek".
---

# gmail-read

Odczyt i wyszukiwanie skrzynki Gmail przez IMAP (`X-GM-RAW` — natywna składnia Gmaila).
Wynik to JSON.

## Użycie

```bash
# Wyszukiwanie skladnia Gmaila (from:, subject:, is:unread, after:, has:attachment ...)
gmail search "from:allegro is:unread" --limit 20

# Tylko nieprzeczytane z INBOX
gmail search --unread --limit 10

# Inny folder
gmail search "faktura" --folder "[Gmail]/All Mail"

# Pelna tresc wiadomosci po msgid (z wyniku search)
gmail get 17000000000000001

# Caly watek po thrid
gmail thread 17000000000000009
```

## Zasady
- `search` zwraca From/Subject/Date/msgid/thrid. Pełną treść pobieraj `get` na żądanie.
- Nie wypisuj pełnych treści wrażliwych wiadomości bez potrzeby.
