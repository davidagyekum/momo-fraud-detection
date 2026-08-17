# ADR-041 — Persisted Screenshot-Only Text-Risk Analysis

**Status:** Proposed by the final completion override; Codex must review, implement, test and mark accepted before release.  
**Date:** 2026-08-17

## Context

The current OCR flow can detect obvious scam language immediately, but the existing final-analysis endpoint requires a complete immutable OCR confirmation containing transaction reference, amount, currency, date/time and status. Many scam-message screenshots do not contain those fields. Requiring the user to invent them violates evidence integrity; refusing to persist the result makes the product appear not to detect fraud.

## Decision

Add a versioned `screenshot_only` analysis mode alongside the existing confirmed combined path.

### Persistence

Add to `analysis_runs`:

- `analysis_mode` — non-null enum/check: `combined`, `screenshot_only`, `transaction_only`;
- `ocr_result_id` — nullable FK to `ocr_results`;
- make `ocr_confirmation_id` nullable;
- check constraint:
  - `screenshot_only` requires `ocr_result_id`;
  - `combined` and `transaction_only` require `ocr_confirmation_id`.

Historical rows backfill to `combined`; their confirmation linkage and outputs remain unchanged.

### API

Extend `POST /api/v1/transactions/{transaction_id}/analyses` additively:

```json
{
  "mode": "screenshot_only",
  "ocr_result_id": "uuid"
}
```

An omitted body preserves the existing combined behavior. The server verifies ownership, receipt linkage, OCR-result immutability and idempotency.

### Stage behavior

For `screenshot_only`:

- OCR text risk: required and replayed from the persisted `_text_fraud` snapshot;
- deterministic image evidence: run when the private receipt is available;
- stored-reference verification: `SKIPPED / NOT_APPLICABLE_SCREENSHOT_ONLY`;
- structured transaction model: `SKIPPED / NOT_APPLICABLE_SCREENSHOT_ONLY`;
- image classifier: explicit active/unavailable status;
- risk policy: may produce medium/high from decisive text evidence;
- history, notifications and reports: supported.

No amount, reference, name, phone, timestamp or status value is synthesized.

### Projection

The result exposes:

- `analysis_mode`;
- fraud risk band and safe reasons;
- `conclusion_status` independent of execution `status`;
- verification status `NOT_ATTEMPTED` with basis `NOT_APPLICABLE_SCREENSHOT_ONLY`;
- component availability and limitations;
- policy/ruleset versions and immutable evidence identifiers.

Raw OCR text remains protected and is not copied into risk, notification, report-summary or audit metadata.

## Consequences

- Message-only screenshots can produce persisted, reviewable risk results.
- The combined reference-verification path remains backward compatible.
- A migration, OpenAPI update, mobile type update, history/report update and tests are required.
- Existing v1 OCR text snapshots are never recomputed silently under v2 rules.
- The failed image classifier remains inactive and cannot block a decisive text-risk result.

## Rejected alternatives

- Fake confirmation values: violates evidence integrity.
- Treat `UNVERIFIED` as fraud: conflates verification with risk.
- Reuse the structured transaction model with zero/default history: invalid feature semantics.
- Store only a transient mobile warning: fails history, report and audit requirements.
