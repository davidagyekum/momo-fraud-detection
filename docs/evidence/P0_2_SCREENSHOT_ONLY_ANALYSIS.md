# P0.2 Screenshot-Only Analysis Evidence

## Scope and authority

- Date: 2026-08-17
- Authority: `FINAL_COMPLETION_OVERRIDE.md`, P0 Task 2
- Branch: `codex/audit-fix-40-final-completion`
- Task base: `5970a9ef35683e0ab37b8162419f831979b41f91`
- Requirements: FR-SCREENSHOT-001 through FR-SCREENSHOT-005
- Decision: accepted ADR-041

The change persists fraud-risk analysis for message-only screenshots without
forcing a user to invent transaction fields. It preserves the existing
confirmation and stored-reference comparison workflow as a separate combined
mode.

## Implemented behavior

| Concern | Screenshot-only | Existing combined mode |
|---|---|---|
| Evidence source | owned, receipt-linked immutable OCR result | immutable OCR confirmation |
| Request | `{ "mode": "screenshot_only", "ocr_result_id": "..." }` | omitted request body |
| Verification | `NOT_ATTEMPTED` | normal stored/imported reference comparison |
| Structured inference | skipped as not applicable | runs when confirmed fields support it |
| Fraud-risk evidence | stored text assessment plus available image evidence | confirmed fields, reference verification and available text/image/model evidence |
| Idempotency | fingerprint binds mode and OCR result | existing confirmation-backed fingerprint |

`AnalysisEvidenceSelection` owns the mode-specific validation and prevents
controllers from inventing placeholder transaction fields. The API checks user
ownership and receipt linkage before orchestration. Result, evidence, history,
notification and private-report projections retain the analysis mode and
immutable OCR identity.

## Migration evidence

Migration `20260817_0006_screenshot_only_analysis.py`:

- adds non-null `analysis_runs.analysis_mode` and backfills historical rows to
  `combined`;
- adds nullable indexed `analysis_runs.ocr_result_id` with a foreign key to the
  immutable OCR result;
- makes `ocr_confirmation_id` nullable only for screenshot-only rows;
- constrains the valid evidence identity for every mode;
- extends verification status with `NOT_ATTEMPTED`;
- forward-renames the duplicated report-artifact constraint name, resolving
  `B-MIG-001` without editing historical migration files.

Two isolated PostgreSQL databases on the healthy project database container
were used. An empty database upgraded to head. A second database upgraded first
to `20260816_0005`, then to head. Both reached `20260817_0006`, and
`flask db check` reported no drift.

## Verification performed

| Gate | Result |
|---|---|
| registered backend gate | 223 tests passed, zero skipped, 85.80% branch-aware coverage; Ruff, strict mypy, OpenAPI and ER drift passed |
| registered mobile gate | 71 tests passed; 83.78% statements, 71.04% branches; format, lint, type, token policy and 28-route export passed |
| registered administrator gate | 40 tests passed; 92.94% statements, 83.22% branches; 3 Playwright flows and production build passed |
| registered security gate | 31 PostgreSQL scenarios passed with zero skips; admin/mobile policy checks and secret scan passed |
| controlled end-to-end gate | screenshot-only and combined API journeys passed; 7 mobile journey tests, 28-route export and 3 administrator Playwright flows passed |
| registered ML gate | 714 tests passed at 90.15% branch-aware coverage; governance checks recorded `training_executed=false` |
| empty migration | upgraded to `20260817_0006 (head)`; drift check clean |
| previous migration | `20260816_0005` upgraded to `20260817_0006 (head)`; drift check clean |

The controlled screenshot-only journey uploads a message-only screenshot, runs
OCR, starts analysis without confirmation, obtains a conclusive high-risk
result, persists `NOT_ATTEMPTED` verification and then exercises history. The
same journey continues through the pre-existing combined confirmation,
reference, report and case flow, providing backward-compatibility evidence.

## Local runtime

The isolated Compose project `momo-fdvs-text-risk` was rebuilt and is healthy:

- PostgreSQL: `localhost:55436`
- API: `http://localhost:8003`
- administrator portal: `http://localhost:5177`
- mobile web: `http://localhost:8084`

Direct API health/readiness, mobile, same-origin mobile API proxy and
administrator probes all returned HTTP 200. The mobile login page was inspected
in the in-app browser. No authenticated browser upload/result claim is made:
the P1 mobile task still needs to expose screenshot-only analysis as the primary
OCR action, and no user password was entered.

## Security, privacy and claims not made

- Raw OCR text remains private and is absent from private HTML reports.
- Object ownership and receipt linkage are enforced server-side.
- Automated OCR and analysis evidence remains immutable; human confirmation is
  not fabricated for screenshot-only mode.
- No model was trained, promoted or activated.
- No locked-test data was accessed.
- No accuracy, calibration, live-MNO verification, hosted deployment, staging,
  production-readiness or production-security claim is made.
