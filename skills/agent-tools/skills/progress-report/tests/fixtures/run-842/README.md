# run-842 fixture

A frozen, sanitized copy of the Progress inputs of one real Workflow run (a 23-task feature, 89 delegation
attempts, 88 lane records). Paths, repository and user names, claim tokens and session ids are replaced by stable
fakes; ids, statuses, timestamps, models and note text are kept. The checkpoint keeps only the fields Progress reads
(receipts reduced to scalars, recoveries to stage/reason/time). Do not edit it to make a test pass; regenerate the
whole set instead. Build a projection from it with `tests/helpers.py: run842_report()`.

Known shape: no `.host` telemetry, no `.delegate/runs`, `checkpoint.status` `in-progress`, no active claim, a
`pause` older than the last accepted receipt, and facts lanes that mirror stage runs.
