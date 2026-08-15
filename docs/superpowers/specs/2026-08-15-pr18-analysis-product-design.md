# PR18 Evidence-Aware Analysis Product Design

**Date:** 2026-08-15  
**Branch:** `codex/pr18-analysis-product`  
**Base:** `d9b096af46232530bc47eff96856260d083885e4`  
**Status:** Approved fast-lane design derived from the owner-supplied PR17–PR20 completion package

## Purpose

PR18 completes the safe user journey from confirmed OCR evidence to a persisted analysis result,
transaction history and mobile detail screen. It integrates existing stored-reference verification,
deterministic image evidence and optional model services through a versioned policy without
claiming capabilities the repository does not have.

The historical image model remains inactive after failing acceptance at macro F1 `0.333333`.
The current private screenshot corpus remains image-ineligible. PR18 therefore records the image
model as unavailable and does not train or activate a replacement model.

## Chosen approach

### Selected: complete the product vertical slice

Build a synchronous bounded analysis orchestrator, a hash-addressed categorical risk policy,
owner-safe analysis/history APIs and the missing mobile result/history/detail experience. Reuse the
existing immutable analysis tables and their JSONB snapshots. This is the shortest path to an
honest demo-complete application and matches the completion package selected by the owner.

### Rejected: image-model training first

The blueprint's image classifier/localizer work cannot complete honestly because broadly approved,
grouped Ghana image derivatives and masks do not exist. STFD is one train-only external corpus and
cannot supply internal selection or calibration evidence. Training first would delay the product
journey while leaving the resulting model non-promotable.

### Rejected: backend-only analysis

Completing only policy and APIs would leave the mobile History placeholder and no persisted result
journey. That fails the owner's mobile-app and demo-complete success criteria.

## Scope

PR18 includes:

- a versioned and SHA-256-addressed analysis policy;
- a typed policy input/result contract;
- persisted stage orchestration with idempotency and failure isolation;
- `POST /transactions/{id}/analyses` completion;
- `GET /analyses/{id}` and enriched evidence projection;
- owner transaction list/detail APIs using persisted results;
- generated OpenAPI updates;
- mobile analysis, history and transaction-detail clients/screens;
- OCR-confirmation handoff into the analysis route;
- controlled fictitious vertical-slice evidence;
- documentation, traceability, changelog and handoff updates.

PR18 excludes:

- CNN training, model promotion or locked-test access;
- fabricated structured history from screenshot fields;
- live mobile-network-operator verification;
- case management, notifications, staff dashboard and release hardening, which remain PR19;
- final evaluation, which remains PR20;
- private images, transcripts, paths or model artifacts in Git.

## Architecture

### Policy boundary

Create `momo_fdvs.services.risk_policy` as a pure, deterministic module. It loads
`risk_policy_demo_v1.json`, validates an exact allowlisted schema, computes the canonical SHA-256
over the policy bytes and evaluates only typed inputs. Unknown keys, unsupported versions,
non-finite scores, inconsistent availability states and hash/version drift fail closed.

The policy does not average heterogeneous signals. It emits:

```python
AnalysisPolicyResult(
    policy_version: str,
    policy_sha256: str,
    evidence_mode: EvidenceMode,
    status: Literal["COMPLETED", "PARTIAL"],
    band: RiskBand,
    legacy_risk_class: Literal["GENUINE", "SUSPICIOUS", "FRAUDULENT"] | None,
    score: Decimal | None,
    reasons: tuple[PolicyReason, ...],
    missing_signals: tuple[str, ...],
    limitations: tuple[str, ...],
)
```

`score` remains null for categorical rules. A null score is not replaced with zero or a synthetic
probability. Legacy class mapping is explicit: low/medium/high map to
GENUINE/SUSPICIOUS/FRAUDULENT, while inconclusive maps to null.

The existing `EvidenceResult` contract remains unchanged for compatibility. The new analysis
projection is specified separately by `analysis-result-v1.schema.json`, because its categorical
policy legitimately permits a conclusive class with a null probability.

### Policy decision order

Rules are evaluated in fixed priority order:

1. Invalid policy configuration raises a safe configuration error and produces no result.
2. A stored-reference mismatch on amount or transaction reference yields categorical
   `high_risk`, even when optional models are unavailable. The reason states that the stored record
   differs; it does not claim provider-side confirmation or legal fraud.
3. A hash-valid, schema-compatible ACTIVE structured-model prediction may yield low, medium or high
   according to its frozen exported class/threshold contract. Low is allowed only when no critical
   verification conflict exists and confirmed critical OCR fields are complete.
4. A future hash-valid ACTIVE image model may contribute only under its frozen threshold contract.
   An `unaltered` prediction never proves transaction authenticity. No such model is active in PR18.
5. Deterministic metadata, duplicate, compression, residual, layout and quality signals add
   supporting reasons and limitations only. They cannot independently assert tampering or fraud.
6. A stored-reference match alone does not yield low risk.
7. If no independent conclusive rule applies, the result is `inconclusive`/`PARTIAL` with a null
   class and score plus exact missing-signal codes.

User-confirmed/corrected OCR fields are policy inputs. Raw OCR remains immutable evidence. A
corrected low-confidence source value is recorded as a limitation, not automatically treated as
fraud.

### Orchestration boundary

Create `momo_fdvs.services.analysis_orchestrator`. It owns one database transaction for the final
projection and invokes existing low-level verification and image-forensics functions without using
the transitional `run_partial_verification_analysis` wrapper.

Stages are fixed and persisted:

1. `SNAPSHOT`
2. `VERIFICATION`
3. `DETERMINISTIC_IMAGE`
4. `IMAGE_MODEL`
5. `STRUCTURED_MODEL`
6. `SEMANTIC_RULES`
7. `RISK_POLICY`
8. `FINALIZE`

Each `AnalysisStageRun` records start, finish, duration, status and safe error code. Optional stages
become `SKIPPED` or `FAILED` without deleting completed verification/image evidence. Policy or
snapshot failure prevents a fabricated final risk result. Finalization atomically updates the
immutable `AnalysisRun` and `Transaction.latest_analysis_run_id`.

### Idempotency and immutability

The request fingerprint hashes:

- owner ID;
- transaction ID;
- OCR confirmation ID;
- requested evidence mode;
- policy version and hash.

The raw idempotency key is never stored. Same key and fingerprint replays the existing run. Same key
with a different fingerprint returns 409. A completed or partial run is immutable. Later reanalysis
creates a new linked run and never rewrites automated evidence.

### Persistence

No migration is required. Existing columns represent the contract:

- `risk_class` stores only the compatibility class;
- `risk_score` stays null for categorical results;
- `component_scores` stores typed component availability and the canonical policy result;
- `top_reasons` stores safe reason objects;
- `configuration_snapshot` stores policy/model/OCR/forensics versions and content hashes;
- `error_code`/`error_message_safe` describe partial or failed execution;
- `AnalysisStageRun`, `VerificationResult`, `ImageAnalysis`, `FraudPrediction` and
  `RuleEvaluation` retain component evidence.

History projections read persisted rows and never recompute against the currently active policy or
model. Canonical-band filters translate to the existing compatibility class, with inconclusive
identified by a null class and `PARTIAL` status.

## API design

### Start analysis

`POST /api/v1/transactions/{transaction_id}/analyses` remains owner-only and requires
`Idempotency-Key` plus an immutable OCR confirmation. The bounded prototype may finish
synchronously but returns the contract-compatible `202` envelope. The response includes the run ID,
status, current stage and poll URL; replay is explicitly marked.

### Analysis projection

`GET /api/v1/analyses/{analysis_run_id}` returns:

- progress for queued/processing runs;
- canonical band, nullable score, compatibility class and disclaimer for final runs;
- verification as a separate object;
- OCR coverage/correction state;
- deterministic image-evidence status;
- image/structured model availability and versions;
- reason codes, missing signals and limitations;
- immutable configuration/version snapshot.

Owner and authorised staff access follow existing object/role policy. Unauthorised existence is
hidden with 404.

### Evidence projection

`GET /api/v1/analyses/{analysis_run_id}/evidence` retains detailed verification and deterministic
image evidence, adds policy/model/stage snapshots and keeps diagnostic media staff-only. It exposes
no storage key, filesystem path, transcript, raw private field in logs, or unsupported probability.

### History and detail

`GET /api/v1/transactions` is owner-scoped, paginated and bounded. It supports date, canonical band,
compatibility class, verification and provider/status filters. Rows contain the latest persisted
analysis summary.

`GET /api/v1/transactions/{transaction_id}` returns the owner-safe receipt link, confirmed OCR
summary, latest analysis, prior run summaries, verification and available actions. It does not
recompute evidence.

## Mobile design

Add Zod-validated clients for start/get analysis and list/get transaction. The client accepts
200/201/202 start responses, performs bounded cancellable polling with capped exponential delay and
treats unknown enum values as controlled errors.

The OCR confirmation screen starts analysis and navigates to
`/analysis/[analysisRunId]`. The result screen displays, in order:

1. analysis status and canonical policy band;
2. evidence quality/missing signals;
3. stored-reference verification in a separate card;
4. policy reasons;
5. confirmed OCR summary;
6. deterministic image evidence;
7. optional-model availability;
8. limitations and disclaimer;
9. history/detail/retry actions.

History replaces the placeholder with loading, empty, offline, error and paginated data states.
Transaction detail reopens the persisted result and prior-run list. Risk is never represented by
colour alone. Copy avoids “safe”, “verified genuine”, “confirmed fraud” and live-provider claims.

## Error handling

- Missing active policy or invalid hash/schema: 503 safe configuration error, no result.
- Missing/corrupt optional model: stage unavailable/error, continue to partial policy result.
- Missing structured feature contract: skip structured inference; never insert zeros.
- Missing private image: retain verification and record deterministic/image stages unavailable.
- Policy exception: fail closed with a safe code; no partial fabricated risk class.
- Persistence failure: rollback the analysis transaction and clean newly written derived objects.
- Cross-owner access: audited 404.
- Client timeout/offline: retain run ID and offer safe retry/resume.

Logs and public errors contain only safe IDs and reason codes, never confirmed field values,
transcripts, storage paths, access tokens or artifact locations.

## Test strategy

Every behavior change follows RED/GREEN/refactor.

### Policy unit tests

- critical reference mismatch yields categorical high risk with null score;
- reference match alone stays inconclusive;
- deterministic image warning alone stays inconclusive;
- valid structured predictions can yield low/medium/high;
- unavailable image and structured models remain null;
- absent exact structured feature contract prevents inference;
- corrected low-confidence OCR does not become a fraud reason;
- policy version/hash/schema drift fails closed;
- no naïve averaging or invented score;
- stable reason ordering and privacy-safe projection.

### Orchestrator/API integration tests

- fixed stage transitions and timings;
- successful owner flow and cross-owner 404;
- idempotent replay and fingerprint conflict;
- optional-stage failure retains completed evidence;
- invalid policy prevents finalization;
- immutable history after policy/model activation changes;
- bounded pagination/filtering;
- no raw fields/paths in logs or responses;
- OpenAPI schema and drift checks.

### Mobile tests

- start response parsing for 200/201/202;
- queued to processing to completed/partial polling;
- cancellation, timeout, retry and offline states;
- result cards keep risk and verification separate;
- empty/error/populated history;
- deep link to transaction detail;
- unknown enum and safe-copy tests;
- accessibility labels and no colour-only status.

### Verification gates

- API format, Ruff, strict mypy, unit/integration/contract tests;
- migration upgrade from clean and previous revision, even though PR18 adds no migration;
- ML registered gate to prove PR17/locked-test controls remain intact;
- mobile format, lint, typecheck, tests and web export under Node `24.14.0`/npm `10.9.0`;
- controlled PostgreSQL/private-storage vertical slice;
- secret/prohibited-artifact scan;
- OpenAPI regeneration/drift check;
- `git diff --check`, status, ancestry and locked-test inspection.

## Acceptance

PR18 is ready for review when:

- its ancestry contains final PR17 head `d9b096af…`;
- one fictitious upload can complete OCR confirmation, persisted analysis, result, history and
  detail;
- verification and risk remain structurally and visually separate;
- unavailable image/structured models are explicit and null-valued;
- history is reconstructed from immutable persisted evidence;
- all applicable backend, mobile, ML, OpenAPI and privacy gates pass;
- the locked test remains sealed;
- no private bytes or paths enter Git;
- exact local evidence, external CI blocker, branch and pushed head are documented.
