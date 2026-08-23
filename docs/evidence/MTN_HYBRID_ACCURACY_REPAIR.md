# MTN Format-Hybrid Accuracy Repair Evidence

## Scope and authority

- Date: 2026-08-23
- Authority: `MoMo_MTN_Format_Hybrid_Fraud_Final_Package.zip`, adopted only for the reported passive-counterfeit false negative under the repository source-of-truth order
- Branch: `codex/final-mtn-format-hybrid-accuracy`
- Base SHA: `eab389e2a8dff5d1a29dcce289bd036994757cd7`
- Last production/test SHA before this evidence freeze: `39ca7903ac922365310efd55f05b96253c0c2b23`
- Hybrid ruleset: `ghana-momo-hybrid-text-risk-v3`
- Deterministic policy: `analysis-risk-policy-demo-v4`
- Profile schema: `mtn-genuine-format-profile-v1`
- Bundled profile SHA-256: `dd2671cfaa44ab59a79ed5828dff6ef7f1fc6d17355110b67695fd7a378347d8`
- Private-source analysis SHA-256 recorded by the safe profile: `9a9adb3a514b2472d46f6c7cf35aa4fe5bbc466223f28156016163689ca6a7fa`

This repair closes the controlled failure in which a passive counterfeit cash-in notification was previously inconclusive because it contained no explicit request to pay, reveal a secret or follow a link. It extends new assessments only; immutable v1 and v2 projections retain their stored meaning.

## Implemented evidence path

```text
private receipt image
  -> bounded full/header/body OCR regions and PSM candidates
  -> categorical sender context with no number persistence
  -> hash-bound genuine-format comparison
  -> financial spelling and malformed-format evidence
  -> cross-candidate consensus
  -> hybrid v3 assessment
  -> categorical policy v4
  -> screenshot-only high-risk persistence with verification NOT_ATTEMPTED
```

The privacy-safe public projection contains fixed reason codes and aggregate evidence only. It excludes raw OCR, matched tokens, sender numbers, names, URLs, amounts, references, bounding boxes and nearest-template content.

## Accepted behavior

| Boundary | Accepted result |
|---|---|
| Controlled passive counterfeit | `FRAUDULENT`, high risk, `score_is_probability=false` |
| Required high reasons | `NUMERIC_SENDER_TRANSACTION_CLAIM` and `GENUINE_TEMPLATE_ANOMALY` survive consensus |
| Corroborating reasons | `FINANCIAL_TERM_SPELLING_ANOMALY` and `MALFORMED_FINANCIAL_FORMAT` |
| Genuine cash-in | not fraudulent |
| Genuine payment-made | not fraudulent |
| One typo in a genuine-format message | not fraudulent |
| Official safety advisory | not fraudulent |
| Numeric-sender ordinary chat | not fraudulent |
| Body-only phone with unknown header | no numeric-sender reason |
| Profile missing/invalid or insufficient OCR | explicit unavailable/inconclusive state; never a genuine verdict |

Spelling or formatting evidence alone cannot reach the fraudulent threshold. The two independent high families are required for the passive-counterfeit decision.

## Test-first and integration evidence

- The generated passive-counterfeit real-OCR regression was committed RED before production changes.
- The package manifest, Python compilation and 32 isolated reference tests passed; the package real-Tesseract demo classified its controlled fixture as fraudulent without printing raw OCR.
- The focused backend hybrid/profile/region/sender/language/consensus/policy boundary suite passed 100 tests.
- Seven generated real-Tesseract integration fixtures passed inside the API container in 70.99 seconds: one positive passive counterfeit and six genuine/advisory/context negatives. Host backend verification routes these seven cases to Docker when the Windows host has no Tesseract executable.
- The complete backend gate passed 275 tests with seven Docker-routed skips at 85.53% branch-aware coverage, plus Ruff, strict mypy over 77 source files, OpenAPI drift and ER drift.
- The complete mobile gate passed 18 suites / 83 tests at 83.78% statements and 71.04% branches, plus formatting, lint, type checking, secure-token policy and the hydration-safe single-shell Expo web export.
- Administrator verification passed 40 tests, three Playwright role/access flows and the production build.
- ML verification passed 714 tests at 90.15% coverage with training disabled.
- Security verification passed 31 PostgreSQL scenarios with zero skips, both client policy checks and the secret/prohibited-artifact scan. The final standalone scan covered 704 candidate files.
- Controlled end-to-end verification passed the API journey, seven mobile result/engagement tests, Expo export and three administrator Playwright flows.
- Empty and representative `20260816_0005` databases upgraded to `20260817_0006`; `flask db check` reported no drift. No new migration was needed.
- The final four-service release verifier passed with db/api/admin/mobile running, migration `20260817_0006` and `full_analysis_available=False`.

## Controlled browser acceptance

A fictitious local user uploaded the generated passive-counterfeit PNG through the Expo web app. The rendered OCR review showed:

- `High fraud risk` and `Likely counterfeit transaction notification` before the private screenshot and technical OCR;
- `Policy score 92/100 — not a probability`;
- explicit do-not-act / official-channel guidance;
- one compact OCR-quality limitation;
- a primary `Save screenshot risk result` action;
- optional transaction comparison collapsed until requested; and
- technical OCR details collapsed.

Saving produced a persisted `High fraud risk` result while transaction verification remained separately `Not attempted`. Layout checks at 360x800, 390x844, 768x1024 and 1440x900 found no horizontal overflow. A cache-cold direct dynamic URL loaded through the final single-shell image with zero console warnings or errors. An earlier static-export direct URL reproduced React hydration error 418; the regression is prevented by `scripts/check_mobile_web_routing.py` and the final mobile gate.

The browser used only generated values. No owner screenshot pixels, private message text, provider credential, real phone number or token is committed.

## Performance evidence boundary

The positive controlled run used 24 bounded OCR candidates and completed within the prototype's 32-candidate maximum. The seven-fixture Docker suite completed in 70.99 seconds total. Formal per-request median, p95 and peak-memory measurements were not collected, so the package's p95-under-20-seconds target is not claimed.

## Limitations and non-claims

- The safe profile describes reviewed genuine MTN message structure; it is not fraud-labelled training data and repeated source rows are not independent samples.
- The hybrid result is a deterministic policy score, not a calibrated probability, provider-wide accuracy figure or legal determination.
- No optional text model was trained or activated. No locked-test partition was opened.
- The P12 image model remains rejected/inactive at held-out macro F1 `0.333333`; no image probability is fabricated.
- Transaction verification uses stored/imported references only. There is no live MNO connection.
- Acceptance is local Docker plus Chromium Expo web. There is no hosted/staging/production deployment claim and no native Android/iOS device acceptance claim.
- Formal latency/load, full evergreen-browser and backup/restore evidence remain outstanding.
