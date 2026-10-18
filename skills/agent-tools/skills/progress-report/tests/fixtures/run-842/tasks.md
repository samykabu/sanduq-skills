# Tasks: Persist and publish versioned project workflow graphs
## Execution configuration

| Marker | Work |
|---|---|
| `[Impl]` | General coding, including the unit and integration tests that belong to that code |
| `[QA]` | End-to-end planning, scenarios, fixtures and the API sample exporter |
| `[Collect]` | Run the authors' fixed commands and collect evidence |
| `[Docs]` | Manuals and illustrations |
| `[Review]` | The one final independent review |
| `[P]` | Runs in parallel with the other task named in its line |
| `[A]` / `[B]` | Coding lane: **A** owns schema, SQL and server paths; **B** owns rules, browser modules, seeds and consumer tests. Lanes never edit each other's files |

## Phase 1: Setup
- [x] T001 [Impl] [A] Record the implementation baseline in `…` from `…`, `…`, `…` and `…`.
## Phase 2: Shared contracts (settled before either lane builds on them)
- [x] T002 [Impl] [B] Define the shared wire and port contracts in `…`, `…` and the TypeScript mirror `…`.
## Phase 3: Rules and schema (parallel lanes)
- [x] T003 [P] [Impl] [B] Implement validation and normalization in `…`, `…` and `…`, the shared vectors `…`, and `…` plus `…`. Parallel with T004.
- [x] T004 [P] [Impl] [A] Change the EF model and generate one migration: `…`, `…`, `…`, `…` (+ Designer and model snapshot), the embedded installers `…` and `…`, and their byte-identical mirrors `…`
## Phase 4: Server paths (lane A) and browser modules and seeds (lane B)
- [x] T005 [Impl] [A] Implement the read side in `…`, `…` and `…`.
- [x] T006 [Impl] [A] Implement the write side in `…`, `…` and `…`.
- [x] T007 [Impl] [A] Expose the four routes in `…` and `…`, and register them and the workflow services in `…`.
- [x] T008 [Impl] [B] Add the idempotent workflow acceptance seed to `…`.
- [x] T009 [P] [Impl] [B] Build the headless browser modules `…`, `…`, `…`, `…`, `…` and `…`, with Vitest files `…`, `…`, `…`, `…` and `…` in the same folder. Parallel with T005–T007.
## Phase 5: Integration tests (both lanes)
- [x] T010 [Impl] [A] Write `…` and the publication-path classes `…` (I-01–I-05), `…` (I-06, I-07), `…` (I-08, I-09), `…` (I-10–I-12) and `…` (I-13, I-14).
- [x] T011 [Impl] [B] Write the consumer, migration and realtime classes `…` (I-15), `…` (I-16), `…` (I-17), `…` (I-18) and `…` (I-19).
## Phase 6: Journey, samples and manuals
- [x] T012 [P] [QA] Author the local Aspire journey `…` and `…`, the API sample exporter `…`, and the handoff `…`. Parallel with T011.
- [x] T013 [P] [Docs] Draft the manual sections in `…`, `…`, `…`, `…`, `…` and `…`, and generate the publication sequence illustration as `…`, `…`, `…` and `…`. Parallel with T010–T012.
## Phase 7: Local acceptance collection
- [x] T014 [Collect] Run the fixed build, lint, unit, web, EF and integration commands from QA plan section 6 and quickstart sections 1–3; store logs in `…` and the results in `…`.
- [x] T015 [Collect] Run the J842 journey and the API sample exporter from T012's handoff in a fresh owned Aspire session; store `…`, Playwright reports and redacted statuses in `…` and the samples in
- [x] T016 [Docs] Reconcile the manual sections with T014–T015 evidence, insert observed sample excerpts, and verify and build the four local outputs with `…`, `…` and `…`; record results in `…`.
- [x] T020 [QA] Extend the API sample exporter `…` with observed denial and conflict samples, and write the sample manifest `…`.
- [x] T021 [QA] Add one existing-screen capture at J842-09 in `…`, saved as `…`, and update `…` with the T020 and T021 commands and outputs.
- [x] T022 [Impl] [B] Add `…` for the document rules of the shared contracts.
- [x] T023 [Impl] [A] Add `…` for version-history paging and replay re-authorization, using `…` without editing it.
## Phase 8: Final independent review and corrective continuation
- [x] T017 [Review] Independently review the completed #842 feature against `…`, `…`, the three contracts, `…`, the implementation evidence and the affected #623/#624/#625/#13 behavior; record finding
- [x] T018 [Impl] Apply the review's findings in the owning files and record each disposition in `…`; route any test, fixture or E2E change to an eligible QA author.
- [x] T019 [Collect] Re-run the checks affected by T018 (at minimum build, lint and the touched unit, integration or journey scenarios) and write the closing evidence summary to `…`.
## Dependencies and execution order
## Requirement coverage
