# Decision record: <project> — v1

The single source of truth. When any other file disagrees, this record wins.

**Changelog**
- **v1 (<YYYY-MM-DD>).** Consolidated from tracks 1–<n> and critiques 1–<n>.

## 1. Decisions

**DR-1 <Title> (resolves <finding ids>).** <The binding decision: what, why, and the mechanism.>

## 2. Resolution ledger

Status is RESOLVED (with its DR), OWNER-DECISION (default in force, see §5) or OPEN.

| ID | Raised by | Finding | Resolution | DR | Status |
|---|---|---|---|---|---|
| XB-<group>-1 | <role> | <finding> | <resolution> | DR-1 | RESOLVED |

## 3. Superseded text (do not copy into deliverables)

| Where | Superseded text | Replaced by |
|---|---|---|
| <track n §x> | <what it said> | DR-n |

## 4. Spike register (UNVERIFIED facts)

| ID | Unverified fact | Test and pass criterion | Fallback that keeps every claim true | Scheduled before |
|---|---|---|---|---|
| SP-1 | <fact> | <test> | <fallback> | <date or task> |

## 5. Owner decisions

| ID | Question | Options | Recommended default | Status |
|---|---|---|---|---|
| OD-1 | <question> | <a; b> | <default and why> | OWNER-DECISION |
