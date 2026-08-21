# P0.3 Text-Rule Hardening Evidence

## Scope

- Date: 2026-08-21
- Authority: `FINAL_COMPLETION_OVERRIDE.md`, P0.3
- Branch: `codex/audit-fix-40-final-completion`
- Starting SHA: `87cce7184b588487cdc17fb612fc3dbbbd42f2f8`
- Implementation SHA: `96e700b9b3d4f14b7182b12520e6406de9c11561`
- Requirements: FR-P0-3-TEXT-001 through FR-P0-3-TEXT-003
- Active ruleset: `ghana-momo-obvious-scam-rules-v2`
- Active deterministic policy: `analysis-risk-policy-demo-v3`

P0.3 hardens new OCR-text assessments without reinterpreting immutable historical evidence. The public API shape and database schema are unchanged. Historical v1 projections remain readable through a deliberately small frozen validator/classifier; the product does not expose a v1 selector and does not rerun historical OCR.

## Accepted behavior

| Concern | v2 behavior |
|---|---|
| Unicode obfuscation | remove every Unicode `Cf` format-control character before matching |
| Clause boundaries | split sentence/visual-line punctuation and contrastives such as `but`, `however`, `yet`, `although`, `nevertheless` and `instead` |
| Compound cues | require related cues in the same or immediately adjacent bounded clause |
| Scheme-less short links | recognise allowlisted shortener domains only when a bounded account or credential action corroborates them |
| Contact redirects | recognise Ghanaian and international phone redirects cautiously; one contact family alone remains suspicious |
| Fraudulent threshold | one critical family or two independent high families |
| Suspicious threshold | one high family, including one high family plus urgency |
| Public reasons | return only fixed allowlisted codes, titles, summaries, severities and guidance; never matched private spans |

The policy identity was advanced to v3 so every new analysis snapshot binds the v2 text ruleset. The legacy filename `risk_policy_demo_v1.json` remains only as a stable packaged resource path; its internal policy identity is v3.

## Historical v1 compatibility

`stored_text_assessment()` accepts only known v1 or v2 projection shapes and reconstructs all public reason metadata from the current allowlist. For v1 evidence it applies the frozen v1 score/class validation rules. A hard-coded v1 high-plus-urgency fixture remains `FRAUDULENT` with score 82, while the equivalent newly assessed v2 signal is `SUSPICIOUS`. Unknown, incomplete or inconsistent stored evidence fails to an explicit unavailable state; raw OCR is not recomputed under a different ruleset.

## Focused red/green evidence

Before implementation, the focused P0.3 suite produced 8 expected failures and 26 passes. The failures covered the new contrastive, format-control, locality, short-link, contact, threshold and versioning requirements. After implementation:

```text
services/api/tests/unit/test_text_fraud.py
services/api/tests/unit/test_risk_policy.py
58 passed
Ruff passed
```

The regression set includes all Unicode format controls, contrastive advisory bypasses, distant compound cues, corroborated scheme-less short links, international contacts, high-plus-urgency, two independent high families, active v2 identity and frozen v1 semantics.

## Complete verification

| Gate | Result |
|---|---|
| Backend | PASS: 233 tests; 85.68% branch-aware coverage; Ruff format/lint, strict mypy over 70 source files, OpenAPI drift and ER drift passed |
| Mobile | PASS: 16 suites / 73 tests; 83.78% statements, 71.04% branches; format, lint, type check, token policy and 28-route static export passed |
| Administrator | PASS: 11 files / 40 tests; 92.94% statements, 83.22% branches; 3 Playwright role/access flows and production build passed |
| ML | PASS: 714 tests; 90.15% coverage; governance, lock, notebook and data checks passed; `training_executed=false` |
| Security | PASS: 31 PostgreSQL scenarios with zero skips; admin/mobile policies and secret/prohibited-artifact scan passed |
| E2E | PASS: controlled API journey, 7 mobile journey tests, 28-route export and 3 administrator Playwright flows |
| Empty migration | PASS: empty PostgreSQL database upgraded to `20260817_0006 (head)`; `flask db check` reported no new operations |
| Previous migration | PASS: representative `20260816_0005` database upgraded to `20260817_0006`; migration drift remained clean |
| Docker release | PASS: PostgreSQL, API, administrator and mobile containers healthy on ports 55436/8003/5177/8084 |
| Installed identities | PASS: API image reports `ghana-momo-obvious-scam-rules-v2`; policy reports `analysis-risk-policy-demo-v3` and binds v2 |
| Release verifier | PASS: four services; migration `20260817_0006`; `full_analysis_available=False` truthfully preserves inactive optional models |

The first disposable backend database was intentionally empty and failed before migration with missing tables. After applying the documented prerequisite, the complete backend gate passed. During the later browser phase, Docker Desktop stopped and Windows exhausted its paging file while restarting it; after the owner-approved reboot and Docker recovery, all four existing containers returned healthy and the browser acceptance completed. Neither setup incident is claimed as product success or product failure.

## Controlled browser acceptance

The browser used a disposable fictitious local account and a generated PNG containing controlled scam language. No real receipt, phone number, account, OTP, PIN or provider credential was used. The accepted flow was:

```text
sign in -> upload controlled PNG -> OCR -> v2 obvious-fraud preview
-> save screenshot-only risk result -> receipt detail -> History
```

Observed results:

- preview: `High fraud risk`;
- deterministic policy score: `96/100 — not a probability`;
- reasons: one critical family, two independent high families and urgency;
- persisted fraud risk: `High risk`;
- transaction verification: `Not attempted`;
- History: `Risk: High risk` and `Verification: Not attempted` shown as separate statuses;
- steady-state browser console: zero warnings and zero errors.

The agent-created browser tab was closed after acceptance and the exact temporary PNG was deleted. The disposable local database identity remains fictitious audit evidence; it contains no real personal data.

## Limitations and non-claims

- These are deterministic rules, not a trained model and not a probability estimate.
- This is local Docker/Chromium evidence, not hosted, staging or production deployment.
- No live MNO verification, model training, locked-test access or new model metric occurred.
- Optional structured and image models remain explicitly unavailable; no fake success was introduced.
- P0.3 does not claim provider-wide fraud detection accuracy or legal fraud determination.
