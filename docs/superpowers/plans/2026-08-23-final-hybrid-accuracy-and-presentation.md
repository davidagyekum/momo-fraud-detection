# Final Hybrid Accuracy and Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the final MTN hybrid correctness and presentation pass on PR #18 without replacing hybrid v3/policy v4 or rewriting immutable historical evidence.

**Architecture:** Add small pure helpers at the backend and frontend presentation boundaries, keep OCR candidate grouping internal, and reuse existing stored allowlisted reason codes throughout projections. Extend the existing safe `/api/v1/version` projection for Profile build information; preserve all database/domain names and avoid a migration.

**Tech Stack:** Python 3.12, Flask, pytest, React Native/Expo/TypeScript/Jest, React/Vite/TypeScript/Vitest/Playwright, PostgreSQL, Docker Compose, Tesseract.

**Spec:** `docs/superpowers/specs/2026-08-23-final-hybrid-accuracy-and-presentation-design.md`

## Global Constraints

- Work only on `codex/final-mtn-format-hybrid-accuracy` and update PR #18.
- Keep `ghana-momo-hybrid-text-risk-v3` and `analysis-risk-policy-demo-v4`; do not restart completed phases.
- Do not rewrite stored automated evidence or change database/domain `Receipt` names.
- Public risk objects and logs must not expose raw OCR, matched text, phone numbers, amounts, references, URLs, names, geometry, or private paths.
- Use observed red → green tests for every production behavior.
- Do not claim hosted CI success; retain `B-CI-001` as the hosted-CI blocker.

---

### Task 1: Canonical reason-code-aware high-risk copy

**Files:**
- Create: `services/api/src/momo_fdvs/services/risk_presentation.py`
- Modify: `services/api/src/momo_fdvs/services/hybrid_text_risk.py`
- Modify: `services/api/src/momo_fdvs/services/risk_policy.py`
- Modify: `services/api/src/momo_fdvs/services/notifications.py`
- Modify: `services/api/src/momo_fdvs/services/reports.py`
- Test: `services/api/tests/unit/test_risk_presentation.py`
- Test: `services/api/tests/unit/test_hybrid_text_risk.py`
- Test: `services/api/tests/unit/test_analysis_outcome_copy.py`
- Test: `services/api/tests/unit/test_analysis_report_copy.py`
- Test: `services/api/tests/integration/test_analysis_journey.py`

**Interfaces:**
- Produces: `high_risk_summary(reason_codes: Iterable[str]) -> str` and a safe active-scam reason-code constant.
- Consumes: only allowlisted categorical reason codes already present in hybrid and risk-policy evidence.

- [ ] **Step 1: Write failing pure-helper tests** for counterfeit-pair precedence, active-scam copy, and generic fallback.
- [ ] **Step 2: Run the focused tests and observe the exact missing-helper/copy failures.**
- [ ] **Step 3: Implement the pure backend helper** with the exact approved copy and precedence.
- [ ] **Step 4: Route hybrid preview and persisted risk summaries through the helper** without changing risk classification, score, versions, or stored historical rows.
- [ ] **Step 5: Update notification/report/history/detail integration assertions** so each projection uses the canonical summary and contains no dynamic private value.
- [ ] **Step 6: Run focused backend tests until green.**
- [ ] **Step 7: Commit:** `fix(risk): make high-risk copy reason-aware`.

### Task 2: Provider-safe MTN profile eligibility

**Files:**
- Modify: `services/api/src/momo_fdvs/services/hybrid_text_risk.py`
- Modify: `services/api/src/momo_fdvs/services/passive_counterfeit.py` only if candidate-level provider context is required
- Modify: `services/api/src/momo_fdvs/services/sender_context.py` only for a safe categorical explicit-label identity
- Test: `services/api/tests/unit/test_hybrid_text_risk.py`
- Test: `services/api/tests/unit/test_passive_counterfeit.py`

**Interfaces:**
- Produces: an internal pure profile-eligibility decision from `provider_code` and explicit provider-label context.
- Consumes: existing MTN profile loader and existing provider codes.

- [ ] **Step 1: Add failing Telecel and AirtelTigo negative tests**, including `GENERIC_MOMO` with explicit conflicting labels.
- [ ] **Step 2: Run them and verify they fail because MTN profile matching is still attempted.**
- [ ] **Step 3: Implement the minimal profile eligibility gate before profile matching.**
- [ ] **Step 4: Add/retain positive MTN and non-conflicting generic coverage.**
- [ ] **Step 5: Run hybrid/passive-counterfeit focused tests until green.**
- [ ] **Step 6: Commit:** `fix(ocr): gate MTN profile by provider`.

### Task 3: Independent OCR evidence groups

**Files:**
- Modify: `services/api/src/momo_fdvs/services/ocr_evidence_consensus.py`
- Modify: `services/api/src/momo_fdvs/services/passive_counterfeit.py`
- Modify: `services/api/src/momo_fdvs/services/hybrid_text_risk.py`
- Modify: `services/api/src/momo_fdvs/services/ocr.py`
- Test: `services/api/tests/unit/test_ocr_evidence_consensus.py`
- Test: `services/api/tests/unit/test_ocr_pipeline.py`
- Test: `services/api/tests/unit/test_hybrid_text_risk.py`

**Interfaces:**
- `CandidateEvidence.evidence_group_id: str` identifies the source crop before variant/PSM expansion.
- Consensus votes at most once per `(reason_code, evidence_group_id)` while retaining per-reason strongest candidate metrics.

- [ ] **Step 1: Add failing consensus tests** proving two variants/PSMs from one group equal one vote and two independent groups equal two votes.
- [ ] **Step 2: Add a failing test preserving every existing strong-single threshold.**
- [ ] **Step 3: Run focused tests and observe over-counting/missing-field failures.**
- [ ] **Step 4: Add `evidence_group_id` and group-aware aggregation**, using the strongest candidate metrics within each group.
- [ ] **Step 5: Thread stable region IDs through all candidate constructors** without exposing them publicly.
- [ ] **Step 6: Run consensus, OCR, hybrid, and public-projection privacy tests until green.**
- [ ] **Step 7: Commit:** `fix(ocr): count independent region evidence`.

### Task 4: Truthful raw-text sender fallback

**Files:**
- Modify: `services/api/src/momo_fdvs/services/sender_context.py`
- Modify: `services/api/src/momo_fdvs/services/hybrid_text_risk.py`
- Test: `services/api/tests/unit/test_sender_context.py`
- Test: `services/api/tests/unit/test_hybrid_text_risk.py`

**Interfaces:**
- Raw-only detection returns its actual confidence, `source="raw_text_fallback"`, and both header-presence flags false.
- Stored projection accepts the new safe source value while remaining compatible with `ocr_header` and `none`.

- [ ] **Step 1: Expand the raw fallback test with failing exact assertions** for confidence, source, and header flags.
- [ ] **Step 2: Add a failing hybrid test proving raw fallback cannot trigger numeric-header evidence.**
- [ ] **Step 3: Run and observe the current 0.80/header promotion failure.**
- [ ] **Step 4: Separate fallback provenance from geometric header provenance and remove confidence floors.**
- [ ] **Step 5: Update stored safe-projection validation for `raw_text_fallback`.**
- [ ] **Step 6: Run sender/hybrid/privacy focused tests until green.**
- [ ] **Step 7: Commit:** `fix(ocr): preserve sender fallback provenance`.

### Task 5: Shared mobile/admin risk presentation

**Files:**
- Modify: `apps/mobile/src/lib/fraud-risk-presentation.ts`
- Modify: `apps/mobile/src/lib/analysis-presentation.ts`
- Modify: `apps/mobile/src/components/analysis-result.tsx`
- Modify: `apps/mobile/src/components/transaction-history.tsx`
- Modify: `apps/mobile/src/app/transaction/[transactionId].tsx`
- Modify: `apps/mobile/src/app/(tabs)/notifications.tsx`
- Create or modify: `apps/admin/src/lib/risk-presentation.ts`
- Modify: `apps/admin/src/pages/transaction-detail-page.tsx`
- Modify relevant administrator list/report/case surfaces discovered by focused search
- Test: `apps/mobile/src/lib/__tests__/fraud-risk-presentation.test.ts`
- Test: `apps/mobile/src/lib/__tests__/analysis-presentation.test.ts`
- Test: `apps/mobile/src/components/__tests__/analysis-result.test.tsx`
- Test: `apps/mobile/src/components/__tests__/transaction-history.test.tsx`
- Test relevant administrator component/unit files

**Interfaces:**
- Mobile/admin `riskTone` maps low/success, medium/warning, high/error, inconclusive/info.
- Mobile `highRiskSummaryFromReasonCodes` mirrors the canonical backend precedence only as a safe compatibility fallback.

- [ ] **Step 1: Add failing helper tests** for all four tones and all three high-risk copy branches.
- [ ] **Step 2: Add failing surface tests** for history, detail, analysis, notifications, reports, and administrator views.
- [ ] **Step 3: Run focused mobile/admin tests and observe inconsistent inline tone/copy failures.**
- [ ] **Step 4: Implement the shared helpers and replace inline mappings.**
- [ ] **Step 5: Keep icon/text status labels and unchanged high-risk safety guidance.**
- [ ] **Step 6: Run focused mobile/admin tests until green.**
- [ ] **Step 7: Commit:** `refactor(ui): share fraud risk presentation`.

### Task 6: Distilled owner flow and terminology

**Files:**
- Modify owner-facing files under `apps/mobile/src/app/**` and `apps/mobile/src/components/**` identified by exact-text search
- Modify: `apps/mobile/src/components/analysis-result.tsx`
- Modify: `apps/mobile/src/app/ocr/[transactionId].tsx`
- Modify: `apps/mobile/src/app/analysis/[analysisRunId].tsx`
- Modify: `apps/mobile/src/app/(tabs)/profile.tsx`
- Test existing screen/component tests plus new narrow tests where absent

**Interfaces:**
- One visible compact evidence summary; one accessible “Why this result?” disclosure for detailed reasons, non-probability score, disclaimer, limitations, and versions.
- Internal API/domain/storage/audit `receipt` names stay unchanged.

- [ ] **Step 1: Add failing tests for every required removal** and for ordinary-user role suppression.
- [ ] **Step 2: Add failing progressive-disclosure tests** proving compact evidence is visible, technical content starts hidden, and accessibility state changes.
- [ ] **Step 3: Add failing owner-copy tests** for “screenshot/check” terminology on primary screens.
- [ ] **Step 4: Run the focused tests and observe current clutter/copy failures.**
- [ ] **Step 5: Remove the specified badges, alerts, and redundant actions; update owner-facing text only.**
- [ ] **Step 6: Consolidate detailed content under “Why this result?” and label the deterministic score “not a probability.”**
- [ ] **Step 7: Run focused mobile tests until green.**
- [ ] **Step 8: Commit:** `feat(mobile): distill owner analysis flow`.

### Task 7: Quality warning consolidation and filtering

**Files:**
- Modify: `apps/mobile/src/components/ocr-quality-banner.tsx`
- Modify: `apps/mobile/src/app/ocr/[transactionId].tsx`
- Modify upload screen/component that currently renders `quality_warnings`
- Test: `apps/mobile/src/components/__tests__/ocr-quality-banner.test.tsx`
- Test OCR/upload screen tests

**Interfaces:**
- `ocrReadabilityWarnings(warnings)` returns only deduplicated real OCR-readability warnings.
- One combined upload-quality card renders all readable upload warnings.

- [ ] **Step 1: Add failing filter tests** for readability vs duplicate/model/forensic/availability warnings.
- [ ] **Step 2: Add a failing rendering test** for one combined warning card.
- [ ] **Step 3: Run and observe current over-broad/unreadable-copy behavior.**
- [ ] **Step 4: Implement the pure warning filter and consolidated card.**
- [ ] **Step 5: Run focused mobile tests until green.**
- [ ] **Step 6: Commit:** `fix(mobile): clarify screenshot quality warnings`.

### Task 8: Safe About-this-build projection

**Files:**
- Modify: `services/api/src/momo_fdvs/api/v1/schemas.py`
- Modify: `services/api/src/momo_fdvs/api/v1/__init__.py`
- Modify: `services/api/tests/integration/test_system_endpoints.py`
- Modify: `services/api/tests/contract/test_openapi.py`
- Modify generated OpenAPI snapshot/client only through registered generators
- Create: `apps/mobile/src/lib/version-client.ts`
- Modify: `apps/mobile/src/app/(tabs)/profile.tsx`
- Test: `apps/mobile/src/lib/__tests__/version-client.test.ts`
- Add/modify Profile screen test

**Interfaces:**
- `/api/v1/version` adds safe `ocr_pipeline_version`, `fraud_ruleset_version`, and `risk_policy_version` fields alongside existing version/build/API contract fields.
- Mobile displays only the app version, short SHA, contract version, OCR pipeline, fraud ruleset, and policy version.

- [ ] **Step 1: Add failing API schema/integration tests** for exact safe fields and absence of secret/path keys.
- [ ] **Step 2: Add failing mobile parser/Profile tests** including missing-value fallback and short-SHA formatting.
- [ ] **Step 3: Run focused tests and observe schema/UI failures.**
- [ ] **Step 4: Implement the additive safe API projection and strict mobile parser.**
- [ ] **Step 5: Render the About-this-build Profile card without secrets or private paths.**
- [ ] **Step 6: Regenerate OpenAPI/client artifacts and verify drift.**
- [ ] **Step 7: Run focused backend/mobile tests until green.**
- [ ] **Step 8: Commit:** `feat(profile): show safe build identities`.

### Task 9: Public-risk and log privacy regression

**Files:**
- Modify: `services/api/tests/unit/test_hybrid_text_risk.py`
- Modify: `services/api/tests/integration/test_analysis_journey.py`
- Modify existing logging/redaction security tests
- Modify production only if a failing privacy test exposes a real leak

**Interfaces:**
- Public risk/projection/log text remains categorical and free of all controlled private markers.

- [ ] **Step 1: Add a failing-or-proving regression fixture** containing unique raw OCR, phone, amount, reference, URL, and matched phrase markers.
- [ ] **Step 2: Assert every public risk object, notification, report, history/detail response, and captured log excludes all markers.**
- [ ] **Step 3: Run the privacy tests; if any fail, fix only the leaking projection/log path and rerun.**
- [ ] **Step 4: Commit:** `test(security): guard public risk redaction`.

### Task 10: Full release verification, evidence, and PR #18

**Files:**
- Modify: `IMPLEMENTATION_STATUS.md`
- Modify: `CHANGELOG.md`
- Modify: `DECISION_LOG.md` only if implementation required a compatibility decision
- Modify: `requirements_traceability.csv`
- Create/update final-pass evidence under `docs/evidence/`
- Create: `docs/handoffs/2026-08-23-final-hybrid-accuracy-presentation.md`
- Update PR #18 through GitHub CLI after push

- [ ] **Step 1: Run focused red/green backend and mobile tests and record commands/results.**
- [ ] **Step 2: Run the full backend gate.**
- [ ] **Step 3: Run the seven-case real-Tesseract Docker gate.**
- [ ] **Step 4: Run the full mobile gate and Expo static export.**
- [ ] **Step 5: Run administrator tests/build and Playwright.**
- [ ] **Step 6: Run ML regression with training disabled.**
- [ ] **Step 7: Run security with zero unexpected skips.**
- [ ] **Step 8: Run empty and previous-revision migration upgrades.**
- [ ] **Step 9: Run the controlled screenshot-only E2E.**
- [ ] **Step 10: Rebuild/start the four-service Docker release and verify health/readiness.**
- [ ] **Step 11: Run browser checks at 360, 390, 768, and 1440, then one cache-cold/incognito LAN check.**
- [ ] **Step 12: Run OpenAPI drift, secret/prohibited-artifact, public-risk/log privacy, and Impeccable detector checks.**
- [ ] **Step 13: Update status, evidence, traceability, changelog, and handoff with exact evidence and limitations.**
- [ ] **Step 14: Run verification-before-completion checks, inspect diff/status, and commit documentation.**
- [ ] **Step 15: Push the branch, verify local/remote SHA equality, and update PR #18 with exact commands/results and `B-CI-001`.**

