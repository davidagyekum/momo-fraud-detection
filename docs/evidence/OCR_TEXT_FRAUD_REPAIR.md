# OCR Text-Fraud Repair Evidence

## Identity and scope

- Date: `2026-08-17`
- Branch: `codex/audit-fix-40-ocr-text-risk`
- Base SHA: `447e7be6ed355716f007023503f1cfcf5ddd19ac`
- Replacement package SHA-256:
  `9b05450025363e1bde86e423dd685fbf5f5b00a191597a020a2a64d62f06fb57`
- Package manifest: 34/34 files matched; hygiene and Python syntax checks passed.
- Integrated assessment: `momo-text-fraud-assessment-v1`
- Integrated ruleset: `ghana-momo-obvious-scam-rules-v1`
- Integrated policy: `analysis-risk-policy-demo-v2`
- Policy SHA-256:
  `1792dc73da11782c82a05a1e4e7a8f1cc585f4e8e99111b6a30e9ed220cc51b4`

The replacement package was used as technical reference. Its older final-risk
overlay was not applied because it conflicts with the current categorical,
null-score, hash-bound policy and separate verification contract. ADR-040
records the resulting compatibility decision.

## Measured verification

| Gate | Result |
|---|---|
| Backend complete gate | PASS — 213 tests, 85.63% branch-aware coverage; Ruff format/lint, strict mypy, OpenAPI and ER drift clean |
| Mobile complete gate | PASS — 67 tests, 83.80% statement / 69.07% branch coverage; format, lint, typecheck and 28-route web export clean |
| Administrator regression gate | PASS — 40 tests at 92.94% statement coverage, 3 Playwright flows and production build |
| ML regression gate | PASS — 714 tests at 90.15% branch-aware coverage; no training executed |
| Security gate | PASS — 31 PostgreSQL-backed scenarios, admin/mobile policy checks and 642-file secret/artifact scan |
| Controlled E2E | PASS — API journey, 6 mobile journey assertions and 3 administrator browser flows |
| OpenAPI | PASS — generated contract matches `packages/api-client/openapi.json` |
| Migration current | PASS — isolated clean database upgraded through `20260816_0005 (head)` |
| Running local release baseline | PASS — db/api/admin/mobile healthy; migration `20260816_0005`; full analysis remains unavailable by design |
| Impeccable UI detector | PASS — no findings (`[]`) after the OCR risk-card change |

## Real OCR demonstration

An auto-removed repository API container mounted the current source read-only,
generated the package's wholly fictitious screenshot and executed the integrated
`execute_ocr` pipeline with Tesseract `5.3.0`. The allowlisted result was:

- status `SUCCESS`;
- class `FRAUDULENT`;
- rule score `95`;
- `score_is_probability=false`;
- reason codes `PIN_OR_OTP_REQUEST`,
  `ACCOUNT_BLOCK_THREAT_WITH_ACTION` and `URGENCY_PRESSURE`;
- no raw OCR text or matched private value in the printed projection.

The package's isolated host reference run separately produced 32 passing tests;
its one real-Tesseract test could not run because host Tesseract is not on
`PATH`. The containerised integrated demonstration closes the binary/runtime
part of that environment limitation without claiming a representative accuracy
metric.

## Explicit boundaries

- No database model or migration changed.
- No optional text model was ported, fitted or registered.
- No locked test, private dataset or real receipt was accessed.
- No accuracy, precision, recall, F1, calibration or production claim is made.
- A no-match assessment has null class and is not evidence of genuineness.
- Stored/imported-reference verification remains independent and is not live
  mobile-network verification.
- Missing accepted image or structured models keep analysis status `PARTIAL`
  even when text evidence maps to a high risk band.

## Known external/pre-existing gate findings

- Repository wrapper doctor: host Node.js `22.23.2` and npm `10.9.8` differ from
  pinned `24.14.0` / `10.9.0`; host Tesseract and optional PostgreSQL CLI are not
  installed. All registered product sections pass under the installed runtime.
- `flask db check` detects a pre-existing PR19 naming mismatch between database
  constraint `ck_report_artifacts_ck_report_artifacts_source_version_positive`
  and model metadata `ck_report_artifacts_source_version_positive`. The database
  is at head and all 213 backend tests pass. This schema-neutral repair does not
  rewrite the already-applied migration.
