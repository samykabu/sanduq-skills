# Scorecard

Gate: every seated role's latest score is at least 9, and the record has no OPEN rows.
Run `python <SKILL_DIR>/scripts/gate.py <workspace>`; only its output declares a pass.

| Role | Kind | R1 | Conditions |
|---|---|---|---|
| chair | core | <score> | <conditions> |
| product | core | <score> | <conditions> |
| architect | core | <score> | <conditions> |
| security | core | <score> | <conditions> |
| qa-chaos | core | <score> | <conditions> |

Add one `R<n>` column per round, before `Conditions`. One row per seated role, no others.
