# Final Completion Override — MoMo-FDVS

**Effective:** 2026-08-17  
**Reviewed continuation branch:** `codex/audit-fix-40-ocr-text-risk`  
**Reviewed head:** `37a30043e4c63e2845d456e360129e067e19d16a`  
**Required ancestor:** `447e7be6ed355716f007023503f1cfcf5ddd19ac` (`codex/pr19-release-hardening`)

This document is the current execution authority for finishing the application. It does not erase the repository's requirements, security rules, migrations, evidence or historical records. It overrides only stale **next-step instructions** and phase sequencing.

## 1. Mandatory reading order

Before changing code, read in this order:

1. `FINAL_COMPLETION_OVERRIDE.md`
2. `IMPLEMENTATION_STATUS.md`
3. `AGENTS.md`
4. the current code, migrations, generated OpenAPI contract and tests for the files being changed
5. `00_SOURCE_OF_TRUTH_AND_SCOPE.md`
6. `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md`
7. `05_API_CONTRACT.md`
8. `04_DATABASE_AND_STORAGE_SPEC.md`
9. `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md`
10. `06_UI_UX_IMPLEMENTATION_SPEC.md`
11. `08_SECURITY_PRIVACY_AUDIT_SPEC.md`
12. `09_TESTING_QA_RELEASE_PLAN.md`

When an older roadmap tells Codex to start a completed phase, this document and `IMPLEMENTATION_STATUS.md` win.

## 2. Documents that are historical, not executable commands

The following remain useful evidence but must not choose the next task:

- `README_FIRST.md`
- `COMPLETE_CODEX_HANDOFF.md`
- the phase sequence in `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`
- `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` except for still-applicable data, privacy and final-evaluation controls
- every file under `docs/handoffs/`
- every completed session plan under `docs/implementation/`
- every completed PR17 plan/spec under `docs/superpowers/plans/` and `docs/superpowers/specs/`
- `docs/WEBCHAT_GPT_OCR_TEXT_RISK_REVIEW_BRIEF.md`
- external review requests and supplied ZIP prompts

Those files may explain why a decision exists. They do not authorize reverting current code, repeating PR17 diagnostics, reopening the locked test, retraining a failed model, or restarting the product roadmap.

## 3. Current product state to preserve

The continuation must preserve all working behavior already present on the reviewed branch:

- hostile-image validation and private storage;
- authenticated ownership and role enforcement;
- OCR extraction, immutable raw OCR evidence and owner correction workflow;
- persisted deterministic OCR-text fraud preview;
- stored/imported reference verification;
- deterministic image-forensics evidence;
- categorical, hash-bound risk policy with `score_is_probability=false`;
- analysis result, history, reports, notifications, casework and staff operations;
- four-service local Docker release packaging;
- existing tests, generated contracts, migrations and audit evidence.

Do not replace this implementation with an older package wholesale.

## 4. Remaining P0 work

### P0.1 — Correct conclusion semantics

A `PARTIAL` execution with a `high` or `medium` risk band is still a conclusive risk result. It must not be persisted or displayed as “inconclusive.”

- `ANALYSIS_EVIDENCE_INCONCLUSIVE` is allowed only when `risk.band == "inconclusive"`.
- A conclusive band with unavailable optional components uses `ANALYSIS_COMPONENTS_PARTIAL` or no error code, plus explicit missing signals.
- UI copy must say that some components were unavailable without weakening a high-risk warning.

### P0.2 — Add a truthful screenshot-only analysis path

A scam-message screenshot may lack a transaction reference, amount, date or receipt status. The app must not require invented values merely to persist a fraud result.

Add an explicit `screenshot_only` mode that:

- is bound to an owned immutable `OCRResult`;
- does not require or fabricate an `OCRConfirmation`;
- persists the text-risk result and available deterministic image evidence;
- records verification as `NOT_ATTEMPTED`, not `UNVERIFIED`;
- marks structured transaction inference `NOT_APPLICABLE`;
- creates an immutable analysis run visible in history, detail and reports;
- preserves the existing confirmed combined/reference workflow unchanged.

This requires a versioned migration and API/OpenAPI/client updates. Do not hide the change in JSON without a compatibility decision.

### P0.3 — Harden text-rule locality and negation

Create a new ruleset version. Do not silently change historical v1 results.

- remove all Unicode format-control characters before matching;
- split contrastive clauses so an advisory cannot suppress a later malicious request;
- require compound cues to occur in the same or adjacent bounded clause;
- support scheme-less short links only with corroborating account/credential actions;
- treat ordinary/international contact redirects cautiously;
- require one critical family or two independent high families for `FRAUDULENT`;
- keep a single high family, including high plus urgency, as `SUSPICIOUS`;
- return only allowlisted reason codes and safe copy.

## 5. Remaining P1 UI work

- Put the OCR-text risk card before the transaction-field form.
- Replace “Your receipt is safe” with neutral evidence-integrity copy.
- For message-only screenshots, show `Save screenshot risk result` as the primary action.
- Make transaction fields an optional secondary path unless the user chooses reference comparison.
- Collapse raw OCR text behind progressive disclosure.
- Keep fraud risk, verification, image evidence and component availability in separate cards.
- Display `Policy score — not a probability` wherever the deterministic score appears.
- Provide text/icon labels in addition to colour.
- Verify 360, 390, 768 and 1440 widths, keyboard navigation, screen-reader names, loading, offline, empty, failure and retry states.

## 6. Required verification before completion

A claim of completion requires all of the following:

1. focused red/green tests for every changed behavior;
2. backend complete gate;
3. mobile complete gate and static web export;
4. administrator complete gate and Playwright flows;
5. ML regression gate with no training and no locked-test access;
6. registered security suite with zero unexpected skips;
7. controlled end-to-end screenshot-only and combined journeys;
8. clean migration from an empty database and upgrade from the previous revision;
9. generated OpenAPI drift check;
10. secret/prohibited-artifact scan;
11. four-service Docker build and health/readiness probes;
12. browser verification of upload → OCR → obvious fraud → persisted result → history;
13. final evidence files, status, decision log, changelog and traceability updates;
14. pushed commits and an updated pull request with exact SHAs and commands.

## 7. Prohibited shortcuts

- Do not restart from PR17 or the old `main` branch.
- Do not re-run PR17 OCR-engine benchmarks or parser-ceiling diagnostics.
- Do not open the locked test before the final frozen evaluation procedure.
- Do not activate the failed image classifier.
- Do not feed screenshot-only data into the structured model using fabricated defaults.
- Do not label `UNVERIFIED` as fraud or genuine.
- Do not change historical risk results when a new text ruleset is introduced.
- Do not expose raw OCR text, matched secret spans, phone numbers, URLs or transaction values in public risk objects or logs.
- Do not claim Docker, browser, native-device, performance or deployment success without executing it.
- Do not delete Docker volumes to repair the engine unless the owner explicitly authorizes destructive recovery.

## 8. Completion target

The final demonstrable product must support both paths:

```text
Receipt path:
upload → OCR → review/correct → stored-reference comparison → risk result → history/report

Message path:
upload → OCR → fraud-language assessment → screenshot-only risk result → history/report
```

For an obvious request to disclose a PIN/OTP or pay a fee to unlock funds, the screenshot-only path must produce a persisted **high-risk / fraudulent** result even when reference verification, image classification and structured transaction inference are unavailable.
