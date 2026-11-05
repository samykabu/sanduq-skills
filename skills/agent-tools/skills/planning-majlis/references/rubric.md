# Scoring rubric

Each seated role scores the plan 0–10 from its own domain, in every critique and re-score.

| Score | Meaning |
| --- | --- |
| 9–10 | Buildable as written. Every risk in this domain has a mechanism, a test, or an owner decision with a default. Remaining items are named conditions, not gaps |
| 7–8 | Sound direction, but at least one gap would cause rework or an incident if building started now |
| 5–6 | Major parts are missing, contradictory or rest on unverified facts presented as true |
| 0–4 | Wrong problem, unsafe, or not buildable |

Rules:

- A score below 9 must name the **exact condition** that would make it a 9: a DR to add or change, a
  spike to schedule, or an owner decision to record. "More detail" is not a condition.
- A blocker finding keeps its role below 9 until the ledger row is RESOLVED or OWNER-DECISION.
- A 9 may carry non-blocking conditions (a spike to pass, a measurement to take); list them in the
  scorecard's last column.
- Scores never come from the clerk. The clerk copies them into `scorecard.md` as written.

The gate (`scripts/gate.py`): every seated role's latest score ≥ 9 and no OPEN ledger rows.
