# Final Hybrid Accuracy and Presentation Evidence

## Evidence identity

- Date: 2026-08-24
- Branch: `codex/final-mtn-format-hybrid-accuracy`
- Pull request: #18
- Base SHA: `eab389e2a8dff5d1a29dcce289bd036994757cd7`
- Final implementation SHA: `4f9a30ad588e3edb9c053e210e799e20ad6d4357`
- Split sender-header correction SHA: `18f2765e05f56eebe0ae02307fa2791ff13362c7`
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
| Split Ghana sender header | Within top geometry-bounded header lines, OCR tokens are sorted by x-position and searched through bounded contiguous windows for a valid Ghana mobile-number subsequence or explicitly truncated `+233` form. Adjacent back/call/video/menu noise is ignored, and confidence is calculated only from number-contributing tokens. | Body-only numbers, phone-shaped transaction IDs, dates, times and message counts do not become numeric sender evidence. Only categorical sender fields are projected; candidate strings are never returned, persisted or logged. |

## Verification evidence

| Gate | Executed result |
|---|---|
| Focused red/green tests | New backend, mobile and administrator behavior was introduced with focused failing tests, then made green. |
| Focused correction selection | 35 sender-context, hybrid-risk, passive-counterfeit and OCR-consensus tests plus one public-projection privacy test passed, 36 total. The new geometry test was first observed failing. |
| Full backend | `scripts/verify_backend.py`: 295 passed; exactly 13 host skips reserved for real Tesseract; 85.97% branch-aware coverage; Ruff format/lint; strict mypy over 78 source files; OpenAPI and ER drift checks passed. |
| Real Tesseract | All 13 generated Docker cases passed in 195.48 seconds: the existing seven plus one realistic spaced-header counterfeit positive and five new header/body look-alike negatives. |
| Mobile | `scripts/verify_mobile.py`: 22 suites, 118 tests; 83.78% statement and 71.04% branch coverage; formatting, linting, typing, token/routing policy and static export passed. |
| Administrator baseline | At starting remote-equal SHA `1b863e69285d15b43af672dc8682dc8cc65834ff`, `scripts/verify_admin.py` passed 12 files / 47 tests, three Playwright flows and production build. The correction-specific controlled E2E reran all three administrator Playwright flows. |
| ML baseline | At starting remote-equal SHA `1b863e69285d15b43af672dc8682dc8cc65834ff`, `scripts/verify_ml.py` passed 714 tests at 90.15% coverage with `training_executed=false`. This correction changed no ML path and did not execute training. |
| Security | `scripts/verify_security.py`: 31 PostgreSQL scenarios passed with zero skips; admin/mobile policy checks passed. The final secret/prohibited-artifact scan covered 726 candidate files; the earlier 722-file result remains an intermediate run. |
| Migrations | Empty and previous-revision upgrade acceptance was established at starting SHA `1b863e69285d15b43af672dc8682dc8cc65834ff`. For this schema-neutral correction, a new isolated empty database upgraded through `20260817_0006`; no migration was added. |
| Controlled E2E | API journey, eight mobile tests/export and three administrator Playwright flows passed. |
| Four-service release baseline | Full release verification passed at starting SHA `1b863e69285d15b43af672dc8682dc8cc65834ff`. During correction acceptance, the API alone was recreated from the verified corrected image while the healthy database, administrator and mobile services remained running. |
| Browser widths | Controlled upload → OCR → screenshot-only high-risk persistence passed at 360, 390, 768 and 1440 pixels with no horizontal overflow and the exact counterfeit copy. |
| Cache-cold LAN | A fresh browser context loaded the LAN URL with HTTP 200, empty local/session storage and no unexpected console or request failures. |

The controlled browser journey observed one expected handled `409` from the initial “get or run OCR review” probe before the client performed OCR. It also observed two expected aborted `HEAD` root-image probes. Both were classified explicitly; the final unexpected-console and unexpected-request arrays were empty. The fresh LAN context returned HTTP 200 with empty local/session storage.

The first two browser attempts are retained as diagnostic evidence, not hidden as passes. The first proved that Compose was still serving the pre-correction API container even though the corrected image had been built. After only the API was recreated, the second isolated a cross-platform fixture difference: Windows Arial rendering did not produce the same OCR tokenization as the Linux DejaVu fixture used by the Docker gate. Uploading the exact Docker-rendered test fixture made the unchanged classifier complete the expected high-risk flow.

## Privacy regression

The integration journey seeds distinct raw OCR, phone, amount, reference, URL and matched-phrase markers. It asserts that none appears in public analysis, history, transaction detail, notifications, private-report projections or captured structured logs. Docker API logs were also inspected: request paths, status and duration were present; planted private values were absent.

## Limitations and non-claims

- Hosted CI is not green or independently reproduced. B-CI-001 prevents GitHub-hosted runner allocation; local gates are recorded precisely instead.
- The release evidence is local Docker/LAN evidence, not a hosted deployment.
- The responsive browser checks are Expo web checks, not native iOS or Android device acceptance.
- Transaction verification uses stored/imported reference records; no live MNO verification was performed.
- The image classifier artifact remains inactive/unavailable. Deterministic image checks are supporting evidence only.
- ML regression ran with training disabled. No new model metric or provider-wide fraud-detection accuracy is claimed.
- The 13 real-Tesseract cases are controlled boundary tests, not representative field accuracy or a performance benchmark.
