# P1 OCR-First Mobile Evidence

## Scope

- Date: 2026-08-20
- Authority: `FINAL_COMPLETION_OVERRIDE.md`, P1 UI work
- Branch: `codex/audit-fix-40-final-completion`
- Base SHA: `fbe6f6c00df9dcf0f61867fc6e6ef6abee43577b`
- Mobile implementation SHA: `7e910bab494db7115c911034bf2118f65aafde49`
- Release-verifier repair SHA: `6804a479ed191622288e13474d0eb0296db36682`
- Requirements: FR-P1-UI-001 through FR-P1-UI-004 and NFR-P1-RESP-001

P1 exposes the already accepted P0.2 screenshot-only contract as the normal primary path. It changes presentation and client orchestration only; immutable analysis semantics, ownership checks, stored-reference comparison and historical evidence remain unchanged.

## Implemented behavior

| Concern | Accepted behavior |
|---|---|
| First result | privacy-safe OCR message-risk card before receipt imagery and transaction fields |
| Primary action | `Save screenshot risk result` with `{ mode: "screenshot_only", ocrResultId }` |
| Secondary action | expandable `Compare with a transaction record (optional)` using the existing confirmation-backed combined flow |
| Missing fields | do not block screenshot-only persistence and are required only after the user chooses comparison |
| Score copy | `Policy score N/100 — not a probability` |
| Raw OCR | collapsed behind an accessible expanded-state control |
| Result hierarchy | fraud risk and verification are separate; image evidence and component availability are separate |
| Failure behavior | offline disables persistence; API failures remain visible and retryable; no fake success |

The shared button component now merges caller-provided accessibility state with busy/disabled state and accepts an accessibility hint. The optional comparison and raw OCR controls expose `expanded`. Status labels include text and are not communicated by colour alone.

## Focused red/green evidence

Before the implementation, the focused mobile tests failed because `OCRAnalysisChoices` did not exist and the deterministic score used the old wording. After implementation:

```text
apps/mobile/src/components/__tests__/ocr-analysis-choices.test.tsx: 2 passed
apps/mobile/src/components/__tests__/text-fraud-risk-card.test.tsx: 2 passed
apps/mobile/src/lib/__tests__/analysis-client.test.ts: screenshot-only request passed
```

The final complete mobile gate passed 16 suites / 73 tests with 83.78% statement and 71.04% branch coverage, plus formatting, lint, type checking, secure-token policy and a 28-route static Expo export.

## Controlled browser journey

Environment:

- PostgreSQL 17.5: `localhost:55436`
- Flask API: `http://localhost:8003`
- Administrator portal: `http://localhost:5177`
- Mobile web: `http://localhost:8084`
- Compose project: `momo-fdvs-text-risk`

The browser account, screenshot, email, phone-like text and message content were wholly fictitious. The flow was:

```text
register -> upload controlled PNG -> OCR -> high message-risk preview
-> save screenshot-only result -> high-risk persisted result
-> transaction detail -> History
```

Observed persisted semantics:

- OCR class: `FRAUDULENT`
- deterministic policy score: `95/100`, explicitly not a probability
- persisted fraud-risk band: `High risk`
- transaction verification: `Not attempted`
- structured/reference fields: not required for screenshot-only persistence
- History: shows `Risk: High risk` and `Verification: Not attempted` as separate statuses

The first save attempt returned `503 No active analysis rule set is available` after the local stack restarted with an unseeded database. The UI displayed `Risk result not saved` and did not fabricate a result. Running the repository's idempotent, development-only `seed-development` command activated the controlled `demo-1` rule set; retry then completed successfully.

The flow's console contained the deliberately exercised OCR-not-yet-run `409`, the pre-seed `503`, and one recovered access-token `401` during the long session. A new login followed by normal in-app navigation to History produced zero console errors or warnings. The previously observed React hydration warning did not reproduce in the rebuilt bundle.

## Responsive evidence

All four required viewports measured `document.documentElement.scrollWidth == window.innerWidth`:

| Viewport | SHA-256 | Evidence |
|---|---|---|
| 360x800 | `af342dddd453dba6f18f755841458b036b0789114fa6bf00717d39d1fca21c72` | `docs/evidence/mobile/p1-ocr-risk-360x800.png` |
| 390x844 | `7f225efc0b1da65ce7f2ea079a4c3e5e239b2f59cda63cfe005cfde41f1b8f3f` | `docs/evidence/mobile/p1-ocr-risk-390x844.png` |
| 768x1024 | `d01d596b61710bd066d07adbbe82f9f4dfca65183787ab8be492c7b043564144` | `docs/evidence/mobile/p1-ocr-risk-768x1024.png` |
| 1440x900 | `a40c4eba2d01f1cc37d17b0777e5055774f88aa16c54a3af6d73e3a12a2f410c` | `docs/evidence/mobile/p1-ocr-risk-1440x900.png` |

The screenshots are full-page captures of a controlled synthetic receipt. No real receipt, account value or browser authentication state is retained. Temporary Playwright logs and state files were deleted before the secret/prohibited-artifact scan.

## Complete verification

| Gate | Result |
|---|---|
| Backend | 224 passed, 85.80% branch-aware coverage; Ruff, mypy, OpenAPI and ER drift passed |
| Mobile | 16 suites / 73 tests passed; 83.78% statements, 71.04% branches; 28 routes exported |
| Administrator | 11 files / 40 tests and 3 Playwright tests passed; build passed |
| ML | 714 passed, 90.15% coverage; `training_executed=false` |
| Security | 31 PostgreSQL scenarios with zero skips; admin/mobile policies and 664-file secret scan passed |
| E2E | 1 controlled API journey, 7 mobile journey tests, 28-route export and 3 admin Playwright tests passed |
| Empty migration | empty PostgreSQL database upgraded through `20260817_0006` and supported the 224-test backend gate |
| Previous migration | representative seeded `20260816_0005` database upgraded to `20260817_0006`; `flask db check` reported no new operations |
| Docker release | db/api/admin/mobile healthy; health/readiness and both web probes HTTP 200 |
| Release verifier | PASS at `20260817_0006`; `full_analysis_available=false` truthfully reflects inactive optional models |
| Impeccable detector | `[]` across all changed production TSX files |

One initial backend attempt against an unmigrated disposable database failed with missing tables; after the documented migration prerequisite it passed. One initial E2E command used a mistyped disposable database username; the corrected full gate passed. Neither is represented as product failure or passing evidence.

## Limitations

- This is local Docker and Chromium-based web evidence, not a hosted or production deployment.
- No native Android/iOS device automation was run in P1.
- Optional image and structured models remain unavailable by design; no model was trained or activated.
- The text ruleset remains v1. P0.3 locality and negation hardening is the next phase and must create a new version without rewriting historical results.
- No locked-test data was accessed and no new model metric was measured.
