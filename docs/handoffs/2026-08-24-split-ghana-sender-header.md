# Codex Session Handoff

## Session identity

- Date/time: 2026-08-24, Africa/Lagos
- Phase/sub-phase: final PR #18 split Ghana sender-header correction
- Repository: MoMo-FDVS
- Base branch: `main`
- Starting remote-equal SHA: `1b863e69285d15b43af672dc8682dc8cc65834ff`
- Work branch: `codex/final-mtn-format-hybrid-accuracy`
- Implementation SHA: `18f2765e05f56eebe0ae02307fa2791ff13362c7`
- Pull request: #18
- Merge status: not merged, as explicitly required
- Push status: pending the documentation-close commit and remote-equality check

## Scope completed

- Requirement IDs: `FR-HYBRID-001`, `FR-HYBRID-009`, `NFR-HYBRID-ACC-001`, `NFR-HYBRID-PRIV-001`
- Goal: recover a full spaced Ghana phone-number sender from realistic top-header OCR geometry without converting body numbers, identifiers or UI digits into numeric sender evidence.
- Actual completed work: bounded x-sorted token-window scanning, Ghana mobile-form validation, explicit truncated-number support, number-token-only confidence, identifier exclusion, privacy-safe projection, one realistic positive fixture and five realistic negative fixtures.

## Changed files

| Path | Change | Why |
|---|---|---|
| `services/api/src/momo_fdvs/services/sender_context.py` | Replaced whole-line matching with bounded header token windows | Recover split numbers while excluding UI noise and lower-body values. |
| `services/api/tests/unit/test_sender_context.py` | Added geometry-backed positive, body-only negative and identifier negative tests | Preserve sender/context and privacy boundaries test-first. |
| `services/api/tests/fixtures/generated_realistic_sender_headers.py` | Added six wholly fictitious realistic screenshot generators | Exercise full spaced sender, genuine provider, ordinary chat, body-only number, identifier and date/count boundaries. |
| `services/api/tests/integration/test_passive_counterfeit_ocr.py` | Expanded the real-Tesseract matrix from seven to 13 cases | Prove required reasons, final class, non-probability semantics and negative boundaries through the production OCR path. |

## Database/migrations

- Migration revisions: none; head remains `20260817_0006`.
- Empty upgrade: disposable `momo_fdvs_sender_pr18` upgraded through head before Docker OCR testing.
- Schema/ERD: unchanged; the full backend drift check passed.
- Cleanup: the disposable database is removed after final evidence/package operations.

## API/contract

- Endpoint behavior: existing OCR endpoints now infer the split sender header correctly.
- Contract shape: unchanged. Sender evidence still contains only `sender_kind`, confidence, two header-presence booleans and source.
- Breaking change: none.
- Privacy: no candidate string, phone number or new raw OCR field is returned, persisted or logged.

## UI

- Product UI code changed: none.
- Browser result: the existing reason-aware copy displayed “Likely counterfeit transaction notification” for the new realistic fixture, then persisted high fraud risk separately from verification not attempted.
- Viewports: 360, 390, 768 and 1440 pixels, all without horizontal overflow.
- Cache-cold LAN: HTTP 200 with empty local/session storage and no unexpected console/request failure.

## OCR/image/ML/verification

- Versions retained: `ocr-pipeline-v1`, `ghana-momo-hybrid-text-risk-v3`, `analysis-risk-policy-demo-v4`, hash-verified `mtn-genuine-format-profile-v1`.
- Positive result: `NUMERIC_SENDER_TRANSACTION_CLAIM` plus `GENUINE_TEMPLATE_ANOMALY`, final `FRAUDULENT`, `score_is_probability=false`.
- Real OCR: 13/13 Docker cases passed in 195.48 seconds.
- ML: no model path or artifact changed; no training executed.
- Limitations: controlled generated cases do not establish provider-wide accuracy or field performance.

## Security/privacy

- Access control and private storage: unchanged.
- Public projection: exact allowlisted categorical sender fields only.
- Privacy regression: existing controlled markers prove that raw OCR, phone, amount, reference, URL and matched phrase are absent from public risk surfaces and structured logs.
- Security gate: 31 PostgreSQL scenarios passed with zero skips.

## Verification performed

| Command/gate | Result | Counts/summary |
|---|---|---|
| Focused correction selection | PASS | 35 sender/hybrid/consensus tests plus one public-projection privacy test; 36 total; the new geometry case was observed RED before implementation |
| Real-Tesseract Docker selection | PASS | 13 passed in 195.48 s |
| `scripts/verify_backend.py` | PASS | 295 passed; 13 Docker-routed host skips; 85.97% coverage; Ruff, mypy, OpenAPI and ER drift green |
| `scripts/verify_mobile.py` | PASS | 22 suites / 118 tests; static export green |
| `scripts/verify_security.py` | PASS | 31 passed; zero skips; final secret/prohibited-artifact scan covered 726 candidate files |
| `scripts/verify_e2e.py` | PASS | API journey, eight mobile tests/export and three administrator Playwright flows |
| Controlled real-OCR browser journey | PASS | reason-aware high risk persisted; four widths; fresh LAN context |

The first browser attempt exposed a stale already-running API container; inspecting the live module proved that it lacked the new scanner. After recreating only the API from the verified image, the second attempt isolated a Windows Arial versus Docker DejaVu fixture-rendering difference. The unchanged classifier passed when the browser uploaded the exact Docker-rendered fixture used by the real-Tesseract gate. These failed attempts are diagnostic evidence and are not counted as passes.

## Known blockers and non-claims

| ID | Description | Next action |
|---|---|---|
| B-CI-001 | GitHub-hosted runners do not allocate because of the repository/account billing lock. Hosted CI is not claimed green. | Repository owner resolves the external lock and reruns the pinned workflow. |
| Image model unavailable | No accepted active image-model artifact is configured. | Retain explicit degraded availability until governed activation. |

No hosted deployment, native-device acceptance, live MNO verification, image-model activation, model training or provider-wide accuracy is claimed.

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: correction SHA, behavior and exact correction gates.
- `requirements_traceability.csv`: split-header requirement and 13-case false-positive matrix.
- `CHANGELOG.md`: correction and acceptance summary.
- `docs/evidence/FINAL_HYBRID_ACCURACY_PRESENTATION.md`: final correction evidence and honest browser diagnostics.

## Next exact task

Push the documentation-close commit, confirm local/upstream SHA equality, update PR #18 without merging, inspect the new hosted check allocation result, then generate and verify the repository-safe submission ZIP from that exact pushed SHA.
