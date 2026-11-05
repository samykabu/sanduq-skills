# Decision record: notes export — v2

**Changelog**
- **v2 (2026-10-30).** DR-2 adds the two-user acceptance test.
- **v1 (2026-10-30).** Consolidated from track 1 and critiques 1–2.

## 1. Decisions

**DR-1 Export endpoint.** `GET /export` returns the caller's notes as `notes.json` with `Content-Disposition: attachment`.

**DR-2 Two-user acceptance test (resolves XB-security-chaos-2).** A test creates notes for two users and checks each export holds only its own.

## 2. Resolution ledger

| ID | Raised by | Finding | Resolution | DR | Status |
|---|---|---|---|---|---|
| XB-security-chaos-1 | security | Export user must come only from the key | — | — | OPEN |
| XB-security-chaos-2 | qa-chaos | No two-user test | Acceptance test | DR-2 | RESOLVED |
