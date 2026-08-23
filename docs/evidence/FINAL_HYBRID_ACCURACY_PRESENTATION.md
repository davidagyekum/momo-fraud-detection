# Final Hybrid Accuracy and Presentation Evidence

## Evidence identity

- Date: 2026-08-23
- Branch: `codex/final-mtn-format-hybrid-accuracy`
- Pull request: #18
- Base SHA: `eab389e2a8dff5d1a29dcce289bd036994757cd7`
- Final implementation SHA: `4f9a30ad588e3edb9c053e210e799e20ad6d4357`
- Scope: final correctness and owner-presentation pass over the existing MTN hybrid implementation

This record describes executed local and controlled evidence. It does not restart an earlier phase, replace the hybrid ruleset, or claim hosted production acceptance.

## Accepted behavior

| Requirement | Implemented result | Evidence boundary |
|---|---|---|
| Reason-aware high-risk copy | The counterfeit reason pair presents “Likely counterfeit transaction notification”; active-scam reasons present “Strong scam indicators detected”; other high-risk results present “Multiple high-risk indicators detected”. The helper is shared by OCR preview, persistence, notifications, reports, history/detail and administrator projections. | Copy is selected from allowlisted reason codes. Raw OCR and matched phrases are not projected. |
| Provider isolation | The MTN genuine-format profile runs for MTN. Explicit `TELECEL_CASH` and `AIRTELTIGO_MONEY` labels exclude it. `GENERIC_MOMO` may use it only when there is no explicit conflicting provider label. | Telecel and AirtelTigo negative tests are registered. This is not provider-wide accuracy evidence. |
| Independent evidence groups | Each OCR crop has an `evidence_group_id`; preprocessing or PSM variants from the same crop contribute at most one vote per reason. The strongest candidate is retained and the documented strong-single-candidate threshold remains active. | Variants from one crop are correlated evidence, not independent votes. |
| Raw sender fallback | Raw-text fallback reports confidence `0.55`, source `raw_text_fallback`, and does not set `header_phone_present`. | It does not pretend to be header-region evidence or promote confidence to `0.80`. |
| Shared risk semantics | Low maps to success, medium to warning, high to error and inconclusive to info across mobile, administrator and report presentation. | Text labels remain present; colour is not the only signal. |
| Owner-flow simplification | Owner-facing terms use screenshot/check language. Redundant badges, alerts and actions were removed. Compact evidence remains visible and detailed rules, policy score, disclaimer and versions are grouped under “Why this result?”. Upload warnings use one card. | Database and domain class names remain unchanged for compatibility. The high-risk “What to do now” guidance is unchanged. |
| Safe build metadata | Profile shows app version, short build SHA, API contract, OCR pipeline, fraud ruleset and risk-policy version. | No secret, credential, private path or private receipt value is returned. |
| OCR warning scope | The compact OCR banner appears for actual text-readability limitations and does not label every forensic/quality warning as unreadable text. | Other quality evidence remains available in the combined quality card or detailed evidence. |

## Verification evidence

| Gate | Executed result |
|---|---|
| Focused red/green tests | New backend, mobile and administrator behavior was introduced with focused failing tests, then made green. |
| Full backend | `scripts/verify_backend.py`: 292 passed; exactly seven host skips reserved for real Tesseract; 85.72% branch-aware coverage; Ruff format/lint; strict mypy over 78 source files; OpenAPI and ER drift checks passed. |
| Real Tesseract | Seven generated Docker cases passed in 77.42 seconds: one passive-counterfeit positive and six genuine/advisory/provider/context negatives. |
| Mobile | `scripts/verify_mobile.py`: 22 suites, 118 tests; 83.78% statement and 71.04% branch coverage; formatting, linting, typing, token/routing policy and static export passed. |
| Administrator | `scripts/verify_admin.py`: 12 files, 47 tests; 93.17% statement and 83.83% branch coverage; three Playwright flows and production build passed. |
| ML regression | `scripts/verify_ml.py`: 714 tests at 90.15% coverage with `training_executed=false`; governance, data and notebook checks passed. |
| Security | `scripts/verify_security.py`: 31 PostgreSQL scenarios passed with zero skips; admin/mobile policy checks and a 722-file secret/prohibited-artifact scan passed. |
| Migrations | Disposable empty and previous-revision databases both upgraded to `20260817_0006`; schema drift checks passed; disposable databases were removed. No new migration was needed for this pass. |
| Controlled E2E | API journey, eight mobile tests/export and three administrator Playwright flows passed. |
| Four-service release | Rebuilt database, API, administrator and mobile services became healthy; release verification passed with migration head and the expected explicit `full_analysis_available=false` degraded image-model state. |
| Browser widths | Controlled upload → OCR → screenshot-only high-risk persistence passed at 360, 390, 768 and 1440 pixels with no horizontal overflow and the exact counterfeit copy. |
| Cache-cold LAN | A fresh browser context loaded the LAN URL with HTTP 200, empty local/session storage and no unexpected console or request failures. |

The controlled browser journey observed one expected handled `409` from the initial “get or run OCR review” probe before the client performed OCR. It also observed two expected aborted `HEAD` root-image probes. Both were classified explicitly; the final unexpected-console and unexpected-request arrays were empty.

## Privacy regression

The integration journey seeds distinct raw OCR, phone, amount, reference, URL and matched-phrase markers. It asserts that none appears in public analysis, history, transaction detail, notifications, private-report projections or captured structured logs. Docker API logs were also inspected: request paths, status and duration were present; planted private values were absent.

## Limitations and non-claims

- Hosted CI is not green or independently reproduced. B-CI-001 prevents GitHub-hosted runner allocation; local gates are recorded precisely instead.
- The release evidence is local Docker/LAN evidence, not a hosted deployment.
- The responsive browser checks are Expo web checks, not native iOS or Android device acceptance.
- Transaction verification uses stored/imported reference records; no live MNO verification was performed.
- The image classifier artifact remains inactive/unavailable. Deterministic image checks are supporting evidence only.
- ML regression ran with training disabled. No new model metric or provider-wide fraud-detection accuracy is claimed.
- The seven real-Tesseract cases are controlled boundary tests, not representative field accuracy or a performance benchmark.

