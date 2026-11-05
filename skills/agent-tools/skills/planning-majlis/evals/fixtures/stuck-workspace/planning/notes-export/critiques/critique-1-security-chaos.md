# Critique 1: security-chaos

Reviewers: security, qa-chaos. None of us wrote any of the material reviewed.

## 1. Findings

| ID | Severity | Finding and evidence | Minimum mechanism |
|---|---|---|---|
| XB-security-chaos-1 | blocker | The export reuses the key check, but nothing stops one user requesting another user's export by a query parameter if one is added later | The handler takes the user only from the key; a test asserts a `?user=` parameter is ignored |
| XB-security-chaos-2 | major | No test proves the file holds only the caller's notes | Acceptance test with two users |

## 2. Scores

| Role | Score | Condition for 9 |
|---|---|---|
| security | 7 | XB-security-chaos-1 resolved in the record |
| qa-chaos | 8 | XB-security-chaos-2 resolved |
