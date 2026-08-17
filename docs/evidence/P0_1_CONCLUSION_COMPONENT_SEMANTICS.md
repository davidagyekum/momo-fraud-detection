# P0.1 Conclusion and Component Semantics Evidence

## Scope and authority

- Date: 2026-08-17
- Authority: `FINAL_COMPLETION_OVERRIDE.md`, P0 Task 1
- Branch: `codex/audit-fix-40-final-completion`
- Task base: `76e7e31dc405b28c21049c3fa83efaef6bd7f381`
- Requirement coverage: FR-RISK-001, FR-RISK-004, FR-RISK-005, FR-RISK-007, FR-HIST-003, FR-HIST-004 and NFR-AUD-001
- Decision: ADR-042

The task fixes one semantic defect: an analysis execution may be `PARTIAL`
because an optional/accepted component is unavailable while its available
evidence still supports a decisive low, medium or high fraud-risk band. The old
finalizer assigned `ANALYSIS_EVIDENCE_INCONCLUSIVE` to every partial execution,
which could visibly weaken a high-risk conclusion.

## Implemented contract

The two independent axes are now explicit:

| Risk band | Execution | Conclusion status | Component status | Terminal code |
|---|---|---|---|---|
| low/medium/high | `COMPLETED` | `CONCLUSIVE` | `COMPLETE` | none |
| low/medium/high | `PARTIAL` | `CONCLUSIVE` | `DEGRADED` | `ANALYSIS_COMPONENTS_PARTIAL` |
| inconclusive | `COMPLETED` or `PARTIAL` | `INCONCLUSIVE` | `COMPLETE` or `DEGRADED` | `ANALYSIS_EVIDENCE_INCONCLUSIVE` |
| any failed run | `FAILED` | `FAILED` | `FAILED` | `ANALYSIS_FAILED` |

The API, generated OpenAPI snapshot and `analysis-result-v1` evidence schema add
`conclusion_status` and `component_status`. Existing `status`, band, score,
missing signals, limitations, reason codes and verification fields remain
unchanged. Historical API/report projections derive the new fields from the
immutable run and stored policy evidence; no automated record is recomputed or
rewritten, and no database migration is needed.

## Product behavior

- The mobile result renders the fraud-risk card before the degraded-component
  alert. A conclusive high/medium/low band never receives inconclusive copy.
- Evidence detail displays risk conclusion and component availability as
  separate lines without relying on color alone.
- Completion notifications lead with the risk result and append component
  limitations only when degraded. The existing high-risk notification now also
  recognizes the persisted `high_risk` band spelling.
- Private HTML reports render risk band, conclusion and component availability
  separately and retain limitations/disclaimer content.
- Stored/imported reference verification remains independent and does not
  authenticate or override fraud risk.

## Test-first evidence

The initial focused backend run failed 7 tests and the mobile run failed 3 tests
because the fields, finalization behavior and risk-first copy did not yet exist.
After implementation:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest services/api/tests/unit/test_risk_policy.py services/api/tests/unit/test_analysis_outcome_copy.py services/api/tests/unit/test_analysis_report_copy.py services/api/tests/integration/test_analysis_orchestrator.py services/api/tests/contract -q --no-cov` | 28 passed, 9 PostgreSQL-dependent skipped |
| `.\.venv\Scripts\python.exe -m pytest services/api/tests -q --no-cov` | 164 passed, 58 PostgreSQL-dependent skipped |
| backend Ruff format check | 107 files formatted |
| backend Ruff lint | passed |
| repository backend strict mypy wrapper | success, 70 source files |
| `scripts/export_openapi.py --check` | passed after regenerating `packages/api-client/openapi.json` |
| `npm.cmd run format:check` in `apps/mobile` | passed |
| `npm.cmd run lint` in `apps/mobile` | passed |
| `npm.cmd run typecheck` in `apps/mobile` | passed |
| `npm.cmd test -- --runInBand --coverage=false` in `apps/mobile` | 15 suites, 70 tests passed |
| Impeccable detector on `apps/mobile/src/components/analysis-result.tsx` | zero findings |
| `.\.venv\Scripts\python.exe scripts/check_secrets.py` | passed, 653 candidate files scanned |

The focused backend skip count is part of the 58 skips in the broader suite; it
is not counted as acceptance evidence.

The registered `scripts/verify_backend.py` wrapper passes formatting, linting
and strict typing, then returns non-zero at pytest coverage: 164 tests pass and
58 database tests skip, leaving aggregate coverage at 58.04% against the 85%
gate. This is recorded as a blocked gate, not a passing backend wrapper.

## Environment blocker

`B-DOCKER-003` remains open. A read-only escalated `docker info` check confirmed
that the Docker client is installed, but Docker Desktop's Linux engine returned
HTTP 500 for its info endpoint. WSL diagnostics did not complete and were
interrupted after the engine failure was captured. PostgreSQL was not listening
on the repository's known local ports.

Consequently, these gates are blocked rather than passed:

- PostgreSQL-backed integration scenarios;
- Alembic upgrade from a clean database;
- Alembic upgrade from the previous revision;
- live Compose/end-to-end verification.

Safe next action: restart or repair Docker Desktop/WSL without resetting or
deleting Docker data, then rerun the database and migration gates before P0.1 is
declared fully accepted or P0.2 begins.

## Claims not made

- No locked-test data was opened.
- No training or model promotion ran.
- No model accuracy, calibration, deployment, hosted CI, live-MNO verification
  or production-readiness claim is made.
- No private receipt value is included in this evidence document.
