# Track 1: export design

Lead roles: architect, product.

**Outcome in one paragraph.** Add `GET /export`, which returns the caller's notes as a JSON file with
`Content-Disposition: attachment`. It reuses the key check of F-2.

## 2. Blocker ledger

| ID | Problem | Resolution | Status |
|---|---|---|---|
| T1-B1 | Large exports could be slow | Notes are in memory (F-1); no limit needed for this size | RESOLVED |
