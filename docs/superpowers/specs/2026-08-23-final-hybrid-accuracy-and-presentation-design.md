# Final Hybrid Accuracy and Presentation Design

**Date:** 2026-08-23  
**Branch:** `codex/final-mtn-format-hybrid-accuracy`  
**Pull request:** #18  
**Status:** Approved for implementation

## Purpose

Complete the final correctness and presentation pass without restarting an earlier phase, replacing the Ghana MoMo hybrid text-risk implementation, or changing historical analysis evidence. New analyses continue to bind the existing hybrid v3 text rules and risk-policy v4 unless a compatibility-safe code fix requires a patch-level implementation change that preserves those public version identities.

## Product invariants

- Fraud risk and stored-reference verification remain separate results.
- Automated evidence remains immutable. This pass does not rewrite stored analysis rows.
- Public risk projections and logs remain allowlisted and must not expose raw OCR, matched text, phone numbers, amounts, references, URLs, names, token geometry, or private paths.
- Missing optional image or model components remain explicit degraded states and never become fake successes.
- `Receipt` database/domain classes, routes, storage keys, audit event identifiers, and API compatibility names remain unchanged. Only owner-facing presentation uses “screenshot” or “check.”
- No live-MNO verification, active image model, hosted deployment, hosted CI, or native-device acceptance claim is added.

## 1. Reason-code-aware high-risk presentation

The server owns the canonical high-risk summary. A small pure presentation helper receives only the risk band and allowlisted reason codes and returns one of these exact summaries, in this precedence order:

1. When both `NUMERIC_SENDER_TRANSACTION_CLAIM` and `GENUINE_TEMPLATE_ANOMALY` are present: **“Likely counterfeit transaction notification”**.
2. Otherwise, when any active-scam reason is present: **“Strong scam indicators detected”**.
3. Otherwise: **“Multiple high-risk indicators detected”**.

The active-scam set is the existing allowlisted active family used by hybrid v3: `PIN_OR_OTP_REQUEST`, `WRONG_TRANSFER_REFUND_LURE`, `ACCOUNT_BLOCK_THREAT_WITH_ACTION`, `PAY_TO_UNLOCK_OR_RELEASE`, `SUSPICIOUS_LINK_ACCOUNT_ACTION`, `UNVERIFIED_CONTACT_REDIRECT`, `PRIZE_OR_BONUS_LURE`, `URGENCY_PRESSURE`, and `UNOFFICIAL_SENDER_CONTEXT`.

The helper is used for new OCR previews and new persisted analysis projections. Notifications and reports consume the same stored/projected summary instead of inventing their own copy. Mobile and administrator presentation helpers use the same exact precedence as a compatibility fallback for older safe response shapes. History, transaction detail, analysis detail, notification, downloadable report, and administrator surfaces therefore agree.

The existing “What to do now” safety guidance remains unchanged. Medium, low, unavailable, and inconclusive meanings remain unchanged.

## 2. Provider-safe MTN genuine-format matching

The MTN genuine-format profile is eligible only when the provider context is compatible with MTN:

- `MTN_MOMO`: eligible.
- `TELECEL_CASH`: never eligible.
- `AIRTELTIGO_MONEY`: never eligible.
- `GENERIC_MOMO`: eligible only when neither the resolved provider context nor an explicit header/provider label identifies Telecel or AirtelTigo.
- Any other explicit conflicting provider: ineligible.

Profile eligibility is decided before calling the profile matcher. A conflicting provider cannot produce `GENUINE_TEMPLATE_ANOMALY` from the MTN profile. Telecel and AirtelTigo negative tests cover both explicit provider codes and generic-provider input with an explicit conflicting label.

No Telecel or AirtelTigo “genuine profile” is inferred or fabricated by this change.

## 3. Independent OCR evidence groups

`CandidateEvidence` gains the internal field `evidence_group_id`. It identifies an independent image region/crop before OCR variant and PSM expansion. Every candidate created from the same crop carries the same group ID even when preprocessing variants or PSM modes differ.

Consensus aggregation groups candidates by `(reason_code, evidence_group_id)` and contributes at most one vote for that reason from each group. Within a group, the strongest qualifying candidate supplies confidence, format margin, spelling count, and formatting count for threshold evaluation. Public output continues to expose only safe aggregate values.

The existing explicit strong-single-candidate thresholds remain valid: one independent group can still satisfy a reason when one candidate from that group reaches the existing confidence and corroboration threshold. Repeated variants or PSM modes from one crop cannot manufacture independent consensus.

`candidate_count` continues to describe processed candidates for diagnostics; it is not treated as an independent-vote count.

## 4. Raw-text sender fallback

When geometric header candidates are unavailable, raw-text fallback candidates retain their actual bounded confidence. The current fallback confidence remains `0.55` unless the extractor supplies another measured value; it is never promoted to `0.80` or `0.75`.

A sender inferred only from raw text uses:

- `source="raw_text_fallback"`;
- `header_phone_present=false`;
- `header_provider_label_present=false`.

It may describe a categorical sender kind, but it cannot stand in for geometric header evidence. Therefore it cannot independently trigger `NUMERIC_SENDER_TRANSACTION_CLAIM`, whose existing requirement for `header_phone_present=true` remains intact.

## 5. Shared risk tone

Each frontend uses one shared `riskTone` helper with this mapping:

- low → `success`;
- medium → `warning`;
- high → `error`;
- inconclusive → `info`.

The helper accepts the domain spellings already present in each client (`low_risk`/`medium_risk`/`high_risk` and normalized equivalents) and returns the existing UI tone type. History, transaction detail, analysis, notifications, report presentation, and administrator views consume this helper. Text/icon labels remain present so colour is never the only signal.

## 6. Owner-facing terminology and removals

Owner-facing mobile copy uses “screenshot,” “check,” “image,” or “transaction” according to context. Internal routes such as `/receipt`, API fields, database classes, source filenames, audit actions, and staff technical language are not renamed.

Remove these owner-facing elements:

- “Ready for your review” badge;
- full “Private image evidence” blue alert;
- per-notification “Mark as read” action;
- ordinary-user roles display;
- redundant “Open transaction history” action;
- primary-flow “Open private receipt” action.

Removing an action must not remove the underlying protected endpoint, ownership enforcement, deep-link compatibility, or staff evidence access.

## 7. Progressive disclosure

The main analysis result keeps a compact evidence summary visible. A single accessible disclosure labelled **“Why this result?”** contains:

- detailed rule reasons;
- deterministic policy score, always labelled “not a probability”;
- the complete disclaimer;
- detailed component and limitation information;
- evidence and ruleset versions.

The disclosure exposes `accessibilityState.expanded` and a useful accessibility hint. The unchanged “What to do now” guidance stays visible for high risk. Fraud risk and transaction verification remain separate cards.

## 8. Upload and OCR quality warnings

Upload-quality warnings are deduplicated and rendered in one warning card rather than multiple competing alerts.

`CompactOcrQualityBanner` shows only warnings that directly affect OCR readability or text coverage, such as low OCR confidence, blur, low contrast, glare, severe crop/text-edge loss, unreadable text, or an unavailable OCR result. Duplicate-image, format-policy, optional-model, metadata, deterministic-forensics, and generic evidence-availability warnings do not become “unreadable text” messages.

If no real readability warning is present, the compact banner is absent.

## 9. About this build

Profile adds an owner-visible **“About this build”** card containing:

- app version;
- short build SHA;
- API contract version;
- OCR pipeline version;
- fraud ruleset version;
- risk-policy version.

Values come from existing safe build configuration or a minimal safe version projection. Missing values display “Unavailable”; they are never guessed. The projection excludes secrets, environment names containing credentials, host filesystem paths, repository-private URLs, full tokens, and private artifact locations.

## 10. Test-first implementation

Every production behavior begins with a focused test that is observed failing for the intended reason. Implementation then makes that test pass before refactoring. The primary red/green slices are:

1. canonical reason-code presentation and all projections;
2. provider eligibility and Telecel/AirtelTigo negatives;
3. independent evidence-group voting and strong-single preservation;
4. raw fallback confidence/provenance/header semantics;
5. shared mobile/admin risk tones;
6. terminology/removal/progressive-disclosure behavior;
7. warning consolidation and OCR-readability filtering;
8. safe build-information projection and Profile rendering;
9. public-risk/log redaction regression.

## 11. Release verification and evidence

Completion requires evidence for all requested gates:

- focused backend and mobile red/green tests;
- complete backend gate;
- seven-case real-Tesseract Docker gate;
- complete mobile gate and static export;
- administrator unit tests and Playwright;
- ML regression with training disabled;
- security suite with zero unexpected skips;
- empty and previous-revision migration upgrades;
- controlled screenshot-only E2E;
- healthy four-service Docker release;
- browser checks at 360, 390, 768, and 1440 widths;
- cache-cold/incognito LAN check;
- explicit public risk/log privacy regression for raw OCR, phone, amount, reference, URL, and matched phrase;
- updated implementation status, traceability/evidence, changelog, session handoff, and PR #18.

Hosted CI remains blocked by the documented account/billing condition `B-CI-001` unless independently observed otherwise. Local passing evidence must not be described as hosted CI success.

## 12. Compatibility and migration decision

This pass is intended to require no database migration: `evidence_group_id` is internal transient OCR evidence, the build-information projection is read-only, and presentation is derived from already persisted allowlisted reason codes. If implementation discovery shows a database or public API schema change is necessary, work stops long enough to record the compatibility decision and add a versioned migration/contract update before proceeding.
