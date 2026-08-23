# Codex Session Handoff

## Session identity

- Date/time: 2026-08-23, Africa/Lagos
- Phase/sub-phase: final MTN format-hybrid passive-counterfeit accuracy repair
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `codex/audit-fix-40-final-completion`
- Base SHA: `eab389e2a8dff5d1a29dcce289bd036994757cd7`
- Work branch: `codex/final-mtn-format-hybrid-accuracy`
- Production/test head before evidence freeze: `39ca7903ac922365310efd55f05b96253c0c2b23`
- Final head SHA: report the exact post-documentation commit in the final response and generated package manifest
- Pull request: stacked repair branch; base `codex/audit-fix-40-final-completion`
- Push status: push and remote equality are completed after this handoff is committed
- Worktree status: clean is required before submission packaging

## Scope completed

- Requirement IDs: FR-HYBRID-001 through FR-HYBRID-004; NFR-HYBRID-ACC-001; NFR-HYBRID-WEB-001
- Goal: detect the controlled passive counterfeit notification without weakening genuine/advisory boundaries, privacy, historical evidence or risk/verification separation.
- Actual completed work:
  - reproduced the real-OCR false negative RED before production changes;
  - installed and hash-bound the privacy-safe MTN genuine-format profile;
  - added categorical header sender context, bounded OCR regions/candidates, financial spelling/format evidence and consensus;
  - introduced hybrid ruleset v3 and deterministic policy v4 while retaining stored v1/v2 semantics;
  - persisted screenshot-only high risk with verification `NOT_ATTEMPTED` and no fabricated transaction fields;
  - made the mobile decision and guidance primary, with optional comparison and technical OCR collapsed;
  - added generated real-Tesseract positive and genuine/advisory/context negatives;
  - repaired concrete Expo web route hydration with a single-shell export and permanent verifier;
  - reran complete local product, migration, security, E2E, release and browser acceptance gates;
  - reconciled academic evidence and explicit limitations.

## Changed files

| Path/area | Change | Why |
|---|---|---|
| `services/api/src/momo_fdvs/services/mtn_format_profile.py` and bundled profile | strict hash/privacy/schema validation and structural matching | use genuine structure without committing raw messages |
| `sender_context.py`, `ocr_regions.py`, `financial_message_evidence.py`, `passive_counterfeit.py`, `ocr_evidence_consensus.py` | bounded privacy-safe evidence production | detect passive counterfeit signals across real OCR candidates |
| `hybrid_text_risk.py`, `risk_policy.py`, policy JSON and orchestrator/API schemas | versioned v3/v4 aggregation and persistence | preserve v1/v2 history and categorical non-probabilistic policy |
| generated backend fixtures/tests | positive and six false-positive boundaries under real Tesseract | prove the whole image-to-policy path |
| mobile OCR/result presentation and tests | decisive guidance/save-first flow and safe fixed evidence rows | make the result understandable without requiring comparison fields |
| `apps/mobile/app.json`, `scripts/check_mobile_web_routing.py`, `scripts/verify_mobile.py` | one Expo SPA shell and routing policy gate | prevent direct dynamic-route hydration mismatch |
| evidence/status/traceability/decision/changelog/handoff | final academic reconciliation | make accepted behavior, hashes, gates and non-claims reviewable |

## Database/migrations

- Migration revision(s): no schema change; head remains `20260817_0006`.
- Upgrade tested from: empty PostgreSQL database and representative `20260816_0005`.
- Result: both reached head; `flask db check` reported no drift.
- Downgrade/rollback notes: no downgrade required; removing hybrid v3 would require a new policy/ruleset version, never rewriting stored evidence.
- Data backfill/schema/ERD update: none; ER drift passed.

## API/contract

- Endpoints changed additively: OCR review and analysis evidence expose hybrid v3 aggregate fields through existing endpoints.
- OpenAPI/client regenerated: generated contract drift passed.
- Breaking change: none; nullable profile evidence handles old stored projections.
- Error/permission behavior: ownership and role enforcement unchanged; missing/invalid profile fails to explicit unavailable evidence.

## UI

- Screens/components: OCR review, fraud-risk presentation helper and persisted analysis result.
- States covered: high, inconclusive/unavailable, OCR-quality limitation, loading, offline, failure/retry, optional comparison collapsed/expanded and technical OCR collapsed.
- Viewports/devices: Chromium Expo web at 360x800, 390x844, 768x1024 and 1440x900; no horizontal overflow. No native-device claim.
- Screenshot/evidence paths: aggregate acceptance is recorded in `docs/evidence/MTN_HYBRID_ACCURACY_REPAIR.md`; controlled screenshots remain local and contain no owner data.
- Accessibility notes: text accompanies status colour; controls have explicit accessible names and expanded/busy/disabled state.

## OCR/image/ML/verification

- Pipeline/model/rule/template versions: OCR pipeline v1; hybrid `ghana-momo-hybrid-text-risk-v3`; policy `analysis-risk-policy-demo-v4`; profile `mtn-genuine-format-profile-v1`.
- Profile SHA-256: `dd2671cfaa44ab59a79ed5828dff6ef7f1fc6d17355110b67695fd7a378347d8`.
- Safe source-analysis SHA-256: `9a9adb3a514b2472d46f6c7cf35aa4fe5bbc466223f28156016163689ca6a7fa`.
- Metrics actually measured: software coverage/counts and seven-fixture total wall time 70.99 seconds; 24 candidates on the controlled positive.
- Limitations: no formal median/p95/peak memory, model accuracy, calibration or provider-wide performance.
- No fabricated or unavailable evidence: score is not a probability; verification is not live MNO; image and optional text models remain inactive/untrained.

## Security/privacy

- Access-control impact: none weakened; private images remain owner/in-scope investigator only.
- Private-data impact: raw CSV, raw OCR, sender numbers, matched values and owner screenshots are excluded from Git/public projections.
- Upload/storage impact: hostile validation, immutable image hash and protected storage unchanged.
- Audit events: version/profile/policy identities are reconstructable; no raw evidence is logged.
- Security checks: 31 PostgreSQL scenarios with zero skips; mobile/admin policies; 704-file secret/prohibited-artifact scan.

## Verification performed

| Command/gate | Result | Counts/summary | Duration |
|---|---|---|---|
| package verifier/reference suite/demo | PASS | 57-file manifest, 32 tests, real-Tesseract demo fraudulent | recorded in package review |
| focused hybrid/profile/region/policy tests | PASS | 100 tests | 0.91 s |
| Docker real-OCR integration | PASS | 7 generated cases | 70.99 s |
| `scripts/verify_backend.py` with isolated DB | PASS | 275 passed, 7 Docker-routed host skips, 85.53%; Ruff/mypy/OpenAPI/ER | recorded output |
| `scripts/verify_mobile.py` | PASS | 18 suites / 83 tests; 83.78% statements, 71.04% branches; single-shell export | recorded output |
| `scripts/verify_admin.py` | PASS | 40 tests, 3 Playwright, build | recorded output |
| `scripts/verify_ml.py` | PASS | 714 tests, 90.15%; training disabled | recorded output |
| `scripts/verify_security.py` | PASS | 31 PostgreSQL scenarios, zero skips; client policies and scan | recorded output |
| `scripts/verify_e2e.py` | PASS | API journey, 7 mobile tests, Expo export, 3 admin Playwright | recorded output |
| empty and previous migration paths | PASS | head `20260817_0006`, no drift | recorded output |
| `scripts/verify_release.py` | PASS | db/api/admin/mobile; `full_analysis_available=False` | recorded output |
| in-app browser acceptance | PASS | upload, OCR, 92/100 high risk, save, verification not attempted, responsive checks | controlled local run |
| cache-cold direct dynamic URL | PASS | final bundle; zero console warnings/errors | controlled local run |

Final recovery re-verification used PostgreSQL `5432`, API `18000`, administrator
`15173` and Expo web `18081` because Windows reserved the range `7997-8096`
after WSL/Docker recovery. Repository defaults are unchanged. Docker Desktop and
WSL were fully restarted without deleting volumes. The exact-tree backend,
mobile, administrator, ML, security, E2E, empty/previous migration, seven-case
real-Tesseract and four-service release gates all passed. The fresh browser flow
persisted a 92/100 high-risk screenshot-only result with verification separately
`NOT_ATTEMPTED`; a cache-cold SPA-shell load had zero console warnings/errors.
Expo-web authentication intentionally requires a new login after a full reload
because its non-native refresh-token fallback is volatile; native secure storage
behaviour is covered by policy and unit tests, not claimed as device acceptance.

Skipped/blocked checks and reason:

- Seven real-Tesseract cases skip only in the host backend gate because the Windows host has no Tesseract executable; the same seven pass in the API container.
- Hosted CI/deployment, native Android/iOS acceptance, full browser matrix, formal performance/load and restore rehearsal were not performed.

## Known defects/blockers

| ID | Severity | Description | Impact | Safe fallback | Owner/input | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | External | GitHub Actions billing/account lock | no hosted CI reproduction | exact local evidence and pushed SHA | repository owner | resolve account lock and rerun |
| B-SEC-002 | Upstream | supported Expo graph retains transitive advisories | build-chain risk remains | supported pins and server-side hostile validation | Expo/React Native upstream | upgrade only through supported matrix |
| P12-ACCEPTANCE | Product/model | image model macro F1 `0.333333` failed acceptance | no image probability/model | explicit unavailable state plus deterministic support | owner/data steward | only a new governed version may retry |
| HYBRID-PERF | Evidence | formal p95 and peak memory not measured | package performance target cannot be claimed | retain bounded 32-candidate maximum and correctness | owner/new scope | run a controlled performance protocol if academically required |

## Documentation updated

- `IMPLEMENTATION_STATUS.md`: accuracy repair complete locally; final pushed-package regeneration next.
- `requirements_traceability.csv`: six overlay requirements added without altering original completion counts.
- `DECISION_LOG.md`: ADR-045 hybrid evidence and ADR-046 single-shell routing.
- `CHANGELOG.md`: hybrid accuracy and hydration-safe routing entry.
- Evidence manifest/docs: 42 safe evidence rows including `MTN_HYBRID_ACCURACY_REPAIR.md`.

## Git evidence

```text
base: eab389e2a8dff5d1a29dcce289bd036994757cd7
branch: codex/final-mtn-format-hybrid-accuracy
production/test head before evidence freeze: 39ca7903ac922365310efd55f05b96253c0c2b23
final head and push equality: reported after documentation commit
```

## Next exact task

Push the repair branch, confirm local HEAD equals its upstream, regenerate the deterministic repository-safe submission ZIP/checksum from that exact commit, verify it independently and give the artifact/hash to the project owner for academic submission. Do not activate optional models or weaken hosted/native/live-MNO/performance non-claims.
