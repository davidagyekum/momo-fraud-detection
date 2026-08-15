# PR18 Analysis Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an honest mobile screenshot journey from confirmed OCR through persisted evidence-aware analysis, result, history and detail while unavailable models remain explicit.

**Architecture:** A pure hash-addressed policy module evaluates typed evidence without averaging or inventing probabilities. A bounded synchronous orchestrator persists eight isolated stages in the existing analysis tables, and Flask projections expose immutable results to Zod-validated Expo clients. Existing JSONB result/configuration fields are sufficient, so no migration is added.

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2, PostgreSQL, Marshmallow/OpenAPI, pytest, Expo 57, React Native 0.86, TypeScript 6, Zod 4, TanStack Query 5, Jest.

## Global Constraints

- Base every change on final PR17 head `d9b096af46232530bc47eff96856260d083885e4`.
- Keep `ghana-momo-parser-v1` and the selected OCR bundle unchanged and experimental.
- Keep the historical image model inactive; macro F1 `0.333333` failed acceptance.
- Never access a locked-test partition before PR20.
- Verification is stored/imported-record comparison, never live provider confirmation.
- Verification and risk remain separate objects in persistence, API and UI.
- Deterministic image evidence is supporting evidence and cannot assert tampering or fraud.
- Never synthesize structured-model history, graph or balance features from screenshot fields.
- Missing or incompatible evidence produces null values plus `PARTIAL`/`inconclusive`.
- Raw private images, OCR text, confirmed values, identifiers, paths and model artifacts stay outside Git and safe logs.
- Use Node `24.14.0` and npm `10.9.0` for reportable mobile gates.
- Write every behavior test first, observe the intended RED, then add minimal GREEN code.

---

### Task 1: Versioned analysis policy contract

**Files:**
- Create: `services/api/src/momo_fdvs/services/risk_policy.py`
- Create: `services/api/src/momo_fdvs/policies/risk_policy_demo_v1.json`
- Create: `packages/evidence-contracts/analysis-result-v1.schema.json`
- Create: `services/api/tests/unit/test_risk_policy.py`
- Modify: `services/api/src/momo_fdvs/services/__init__.py`

**Interfaces:**
- Consumes: `EvidenceMode`, `RiskBand` and `legacy_risk_from_band` from `momo_fdvs.contracts.evidence`.
- Produces: `PolicyReason`, `ModelPolicySignal`, `AnalysisPolicyInput`, `AnalysisPolicyResult`, `PolicyFailure`, `load_risk_policy(path: Path, *, expected_sha256: str | None = None) -> LoadedRiskPolicy`, and `evaluate_risk_policy(policy: LoadedRiskPolicy, value: AnalysisPolicyInput) -> AnalysisPolicyResult`. `ModelPolicySignal.kind` is exactly `IMAGE` or `STRUCTURED`; its classmethod is `unavailable(kind: Literal["IMAGE", "STRUCTURED"], reason_code: str) -> ModelPolicySignal`.

- [ ] **Step 1: Write failing policy tests**

Create tests with a local `policy` fixture loaded from the committed JSON and explicit inputs. Include this core RED:

```python
def test_reference_amount_mismatch_is_categorical_high_without_invented_score(
    policy: LoadedRiskPolicy,
) -> None:
    result = evaluate_risk_policy(
        policy,
        AnalysisPolicyInput(
            mode=EvidenceMode.SCREENSHOT_ONLY,
            verification_status="MISMATCH",
            critical_verification_mismatches=("amount",),
            confirmed_critical_fields_complete=True,
            corrected_low_confidence_fields=(),
            deterministic_image_reasons=(),
            image_model=ModelPolicySignal.unavailable(
                "IMAGE", "IMAGE_MODEL_NOT_ACTIVE"
            ),
            structured_model=ModelPolicySignal.unavailable(
                "STRUCTURED", "STRUCTURED_CONTEXT_UNAVAILABLE"
            ),
            semantic_reasons=(),
        ),
    )
    assert result.status == "COMPLETED"
    assert result.band is RiskBand.HIGH
    assert result.legacy_risk_class == "FRAUDULENT"
    assert result.score is None
    assert [reason.code for reason in result.reasons] == [
        "REFERENCE_AMOUNT_MISMATCH"
    ]
```

Add separate tests proving:

```python
assert verified_without_model.band is RiskBand.INCONCLUSIVE
assert deterministic_warning_only.band is RiskBand.INCONCLUSIVE
assert structured_genuine.band is RiskBand.LOW
assert structured_suspicious.band is RiskBand.MEDIUM
assert structured_fraudulent.band is RiskBand.HIGH
assert active_image_tamper_above_threshold.band is RiskBand.HIGH
assert corrected_low_confidence.band is not RiskBand.HIGH
assert invalid_hash_raises.value.code == "RISK_POLICY_HASH_MISMATCH"
assert invalid_schema_raises.value.code == "RISK_POLICY_SCHEMA_INVALID"
```

Available signals must carry a finite score/class plus exact artifact/schema identities. IMAGE accepts only `unaltered`/`tampered`; STRUCTURED accepts only `GENUINE`/`SUSPICIOUS`/`FRAUDULENT`. Test that unavailable signals reject non-null scores/classes and that a class from the wrong model kind fails closed.

- [ ] **Step 2: Run the policy tests and verify RED**

Run:

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/unit/test_risk_policy.py -q --no-cov
```

Expected: collection fails because `momo_fdvs.services.risk_policy` does not exist.

- [ ] **Step 3: Add the exact policy file**

Create:

```json
{
  "schema_version": "analysis-risk-policy-schema-v1",
  "policy_version": "analysis-risk-policy-demo-v1",
  "critical_verification_fields": ["amount", "transaction_reference"],
  "structured_class_bands": {
    "GENUINE": "low_risk",
    "SUSPICIOUS": "medium_risk",
    "FRAUDULENT": "high_risk"
  },
  "image_high_threshold": 0.85,
  "categorical_score_is_null": true,
  "deterministic_image_supporting_only": true,
  "stored_reference_match_is_not_low_risk": true
}
```

- [ ] **Step 4: Implement typed loading and evaluation**

Use frozen dataclasses and strict enums/literals. The evaluator must follow this shape:

```python
def evaluate_risk_policy(
    policy: LoadedRiskPolicy,
    value: AnalysisPolicyInput,
) -> AnalysisPolicyResult:
    mismatch_reasons = tuple(
        PolicyReason(
            code=f"REFERENCE_{field.upper()}_MISMATCH",
            title=f"{field.replace('_', ' ').title()} differs from the stored record",
            severity="HIGH",
        )
        for field in value.critical_verification_mismatches
    )
    if mismatch_reasons:
        return _result(policy, value, RiskBand.HIGH, mismatch_reasons)
    structured_class = value.structured_model.predicted_class
    if value.structured_model.available and structured_class == "FRAUDULENT":
        return _result(policy, value, RiskBand.HIGH, value.semantic_reasons)
    if (
        value.image_model.available
        and value.image_model.predicted_class == "tampered"
        and value.image_model.score is not None
        and value.image_model.score >= policy.image_high_threshold
    ):
        reason = PolicyReason(
            code="IMAGE_MODEL_TAMPER_THRESHOLD_EXCEEDED",
            title="The accepted image model found manipulation indicators",
            severity="HIGH",
        )
        return _result(policy, value, RiskBand.HIGH, (reason,))
    if value.structured_model.available and structured_class is not None:
        band = policy.structured_class_bands[structured_class]
        if band is RiskBand.LOW and not value.confirmed_critical_fields_complete:
            return _inconclusive(policy, value, "CRITICAL_OCR_FIELDS_INCOMPLETE")
        return _result(policy, value, band, value.semantic_reasons)
    return _inconclusive(policy, value, "CONCLUSIVE_MODEL_EVIDENCE_UNAVAILABLE")
```

`_result` must set `score=None` for the committed categorical policy. `_inconclusive` must include exact image/structured missing-signal codes, deterministic reasons as supporting evidence and correction limitations without turning them into fraud reasons. Sort/deduplicate codes deterministically.

`load_risk_policy` reads bytes once, computes SHA-256, decodes UTF-8/JSON, rejects every unknown or missing key, validates exact enum values and returns the computed hash. It must never include the path or JSON values in a public error.

- [ ] **Step 5: Add the JSON Schema contract**

Define `analysis-result-v1` with required `status`, `band`, nullable `legacy_risk_class`, nullable numeric `score`, reason objects, `missing_signals`, `limitations`, `verification`, `image_evidence`, model-status objects and version snapshot. Use `additionalProperties: false` at every owned object boundary.

- [ ] **Step 6: Run focused and source-quality checks**

Run:

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/unit/test_risk_policy.py `
  services/api/tests/unit/test_evidence_contracts.py -q --no-cov
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\ruff.exe check `
  services/api/src/momo_fdvs/services/risk_policy.py `
  services/api/tests/unit/test_risk_policy.py
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\mypy.exe `
  --config-file services/api/pyproject.toml services/api/src/momo_fdvs
```

Expected: all pass; no existing evidence-contract behavior changes.

- [ ] **Step 7: Commit Task 1**

```powershell
git add services/api/src/momo_fdvs/services/risk_policy.py `
  services/api/src/momo_fdvs/services/__init__.py `
  services/api/src/momo_fdvs/policies/risk_policy_demo_v1.json `
  services/api/tests/unit/test_risk_policy.py `
  packages/evidence-contracts/analysis-result-v1.schema.json
git commit -m "feat(analysis): add evidence-aware risk policy"
```

---

### Task 2: Bounded analysis orchestrator and immutable stage persistence

**Files:**
- Create: `services/api/src/momo_fdvs/services/analysis_orchestrator.py`
- Create: `services/api/tests/integration/test_analysis_orchestrator.py`
- Modify: `services/api/src/momo_fdvs/services/verification.py`
- Modify: `services/api/tests/integration/test_reference_verification.py`
- Modify: `services/api/src/momo_fdvs/services/__init__.py`

**Interfaces:**
- Consumes: `evaluate_verification`, `run_image_forensics`, active `ModelVersion` rows, `predict_image_tampering`, `evaluate_risk_policy`, `ObjectStorage`, existing analysis/evidence models and audit service.
- Produces: `AnalysisFailure`, `AnalysisOrchestrationResult`, `run_analysis(*, transaction: Transaction, confirmation: OCRConfirmation, user: User, roles: set[str], idempotency_key: str, storage: ObjectStorage, policy_path: Path | None = None, mode: EvidenceMode = EvidenceMode.SCREENSHOT_ONLY) -> AnalysisOrchestrationResult`, `analysis_projection(run: AnalysisRun, *, include_evidence: bool = False) -> dict[str, Any]`, and stable stage constants.

- [ ] **Step 1: Expose verification primitives without changing behavior**

Rename only the helpers required by the orchestrator:

```python
analysis_request_hash = _request_hash
claim_analysis_idempotency = _claim_idempotency
verification_reuse_warnings = _reuse_warnings
```

Prefer explicit public functions over aliases if mypy or Ruff rejects aliases. Keep
`run_partial_verification_analysis` as a compatibility wrapper until the route changes in Task 3.
Add a focused parity assertion to `test_reference_verification.py` proving the same confirmed fields
produce the same `VerificationOutcome` before and after extraction.

- [ ] **Step 2: Write failing orchestrator tests**

Use real SQLAlchemy models and the existing controlled storage fixture. Add separate tests for:

Define a `controlled_analysis_case` fixture that exposes `run(key: str, confirmation: OCRConfirmation | None = None) -> AnalysisOrchestrationResult`, its transaction/confirmation, and the configured storage. Then add:

```python
def test_mismatch_completes_high_risk_and_persists_all_stages(
    controlled_analysis_case: ControlledAnalysisCase,
) -> None:
    result = controlled_analysis_case.run(key="analysis-mismatch-key")
    assert result.run.status == "COMPLETED"
    assert result.run.risk_class == "FRAUDULENT"
    assert result.run.risk_score is None
    assert [stage.stage for stage in result.stages] == list(ANALYSIS_STAGES)

def test_verified_reference_without_models_is_partial_inconclusive(
    verified_analysis_case: ControlledAnalysisCase,
) -> None:
    result = verified_analysis_case.run(key="analysis-verified-key")
    assert result.run.status == "PARTIAL"
    assert result.run.risk_class is None
    assert result.run.component_scores["policy"]["band"] == "inconclusive"

def test_same_key_and_fingerprint_replays_immutable_run(
    controlled_analysis_case: ControlledAnalysisCase,
) -> None:
    first = controlled_analysis_case.run(key="analysis-replay-key")
    second = controlled_analysis_case.run(key="analysis-replay-key")
    assert second.replayed is True
    assert second.run.id == first.run.id
    assert len(second.stages) == len(first.stages)

def test_same_key_with_changed_confirmation_returns_conflict(
    controlled_analysis_case: ControlledAnalysisCase,
    second_confirmation: OCRConfirmation,
) -> None:
    controlled_analysis_case.run(key="analysis-conflict-key")
    with pytest.raises(AnalysisFailure) as raised:
        controlled_analysis_case.run(
            key="analysis-conflict-key", confirmation=second_confirmation
        )
    assert raised.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert raised.value.status == 409

def test_image_failure_retains_verification_and_safe_error(
    image_failure_case: ControlledAnalysisCase,
) -> None:
    result = image_failure_case.run(key="analysis-image-failure-key")
    assert result.verification.status in {"VERIFIED", "MISMATCH", "UNVERIFIED"}
    image_stage = next(stage for stage in result.stages if stage.stage == "DETERMINISTIC_IMAGE")
    assert image_stage.status == "FAILED"
    assert image_stage.error_code == "IMAGE_SOURCE_UNAVAILABLE"

def test_structured_stage_skips_without_exact_context(
    controlled_analysis_case: ControlledAnalysisCase,
) -> None:
    result = controlled_analysis_case.run(key="analysis-structured-skip-key")
    stage = next(stage for stage in result.stages if stage.stage == "STRUCTURED_MODEL")
    assert stage.status == "SKIPPED"
    assert stage.error_code == "STRUCTURED_CONTEXT_UNAVAILABLE"

def test_invalid_policy_rolls_back_without_final_risk(
    invalid_policy_case: ControlledAnalysisCase,
) -> None:
    with pytest.raises(AnalysisFailure) as raised:
        invalid_policy_case.run(key="analysis-invalid-policy-key")
    assert raised.value.code == "RISK_POLICY_SCHEMA_INVALID"
    assert db.session.scalar(select(func.count(AnalysisRun.id))) == 0
```

Assert stage details contain safe versions/statuses only, not confirmed values, transcript, object
keys or artifact paths.

- [ ] **Step 3: Run orchestrator tests and verify RED**

Run:

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/integration/test_analysis_orchestrator.py -q --no-cov
```

Expected: collection fails because `analysis_orchestrator` does not exist.

- [ ] **Step 4: Implement stage and snapshot helpers**

Use these fixed definitions:

```python
ANALYSIS_STAGES = (
    "SNAPSHOT",
    "VERIFICATION",
    "DETERMINISTIC_IMAGE",
    "IMAGE_MODEL",
    "STRUCTURED_MODEL",
    "SEMANTIC_RULES",
    "RISK_POLICY",
    "FINALIZE",
)

@dataclass(frozen=True)
class AnalysisOrchestrationResult:
    run: AnalysisRun
    verification: VerificationResult
    image_analysis: ImageAnalysis | None
    stages: tuple[AnalysisStageRun, ...]
    replayed: bool
```

Implement `_begin_stage`, `_finish_stage`, `_fail_stage` and `_skip_stage`. Measure durations with
`time.perf_counter()` and persist non-negative integer milliseconds. Stage details accept only
allowlisted booleans, counts, versions and reason codes.

The snapshot fingerprint must hash owner ID, transaction ID, confirmation ID, evidence mode, policy
version and policy hash using canonical sorted JSON. Store receipt/OCR/policy/model identities in
`configuration_snapshot`, never raw values.

- [ ] **Step 5: Implement optional-stage isolation and policy finalization**

The orchestrator sequence must:

```python
verification_outcome = evaluate_verification(confirmation.confirmed_fields)
image_outcome = run_image_forensics(
    run=run,
    transaction=transaction,
    ocr_result=confirmation.ocr_result,
    storage=storage,
)
image_model = active_model("IMAGE")
structured_model = None  # screenshot request has no exact structured context
policy_result = evaluate_risk_policy(policy, policy_input)
```

Catch `ImageForensicsFailure` and `ImageModelFailure` only at their stage boundaries. Mark the image
model `SKIPPED/IMAGE_MODEL_NOT_ACTIVE` when no ACTIVE artifact exists. Mark structured
`SKIPPED/STRUCTURED_CONTEXT_UNAVAILABLE` for screenshot-only requests. Never call the structured
predictor with partial or zero-filled inputs.

Persist model predictions only when inference succeeds and include model ID, version, feature schema
hash, threshold snapshot, probability vector and reason codes. Finalize `risk_class`, nullable
`risk_score`, `top_reasons`, `component_scores`, `status`, `completed_at`, transaction status and
latest run atomically.

- [ ] **Step 6: Implement idempotent replay and cleanup**

Claim the existing idempotency record before external work. On replay, load all persisted component
rows and return them without rerunning any stage. On conflict raise:

```python
AnalysisFailure(
    "IDEMPOTENCY_KEY_REUSED",
    "This Idempotency-Key was already used for a different analysis request.",
    409,
)
```

On transaction failure, rollback and delete only derived objects written by this attempt. Do not
delete the original receipt or evidence from earlier runs.

- [ ] **Step 7: Run focused regression and quality checks**

Run:

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/integration/test_analysis_orchestrator.py `
  services/api/tests/integration/test_reference_verification.py `
  services/api/tests/integration/test_image_forensics_workflow.py -q --no-cov
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\ruff.exe check `
  services/api/src/momo_fdvs/services/analysis_orchestrator.py `
  services/api/src/momo_fdvs/services/verification.py `
  services/api/tests/integration/test_analysis_orchestrator.py
```

- [ ] **Step 8: Commit Task 2**

```powershell
git add services/api/src/momo_fdvs/services/analysis_orchestrator.py `
  services/api/src/momo_fdvs/services/verification.py `
  services/api/src/momo_fdvs/services/__init__.py `
  services/api/tests/integration/test_analysis_orchestrator.py `
  services/api/tests/integration/test_reference_verification.py
git commit -m "feat(analysis): orchestrate immutable evidence stages"
```

---

### Task 3: Start/read analysis APIs and evidence projection

**Files:**
- Modify: `services/api/src/momo_fdvs/api/v1/ocr.py`
- Modify: `services/api/src/momo_fdvs/api/v1/ocr_schemas.py`
- Modify: `services/api/src/momo_fdvs/api/v1/analyses.py`
- Modify: `services/api/src/momo_fdvs/api/v1/analysis_schemas.py`
- Create: `services/api/tests/integration/test_analysis_api.py`
- Modify: `services/api/tests/contract/test_openapi.py`

**Interfaces:**
- Consumes: `run_analysis`, `analysis_projection`, `AnalysisFailure` and existing authentication/storage helpers.
- Produces: complete POST start response, GET analysis response and enriched evidence response.

- [ ] **Step 1: Write failing API and ownership tests**

Cover:

```python
response = client.post(
    f"/api/v1/transactions/{transaction_id}/analyses",
    headers={**auth_headers(owner), "Idempotency-Key": "analysis-key-123"},
)
assert response.status_code == 202
run_id = response.json["data"]["analysis_run_id"]
assert response.json["data"]["poll_url"] == f"/api/v1/analyses/{run_id}"

detail = client.get(f"/api/v1/analyses/{run_id}", headers=auth_headers(owner))
assert detail.status_code == 200
assert set(detail.json["data"]) >= {
    "id", "status", "risk", "verification", "evidence_summary", "versions"
}
assert detail.json["data"]["risk"]["score"] is None

denied = client.get(f"/api/v1/analyses/{run_id}", headers=auth_headers(other))
assert denied.status_code == 404
```

Add tests for no OCR confirmation (409), missing key (400), replay (202 with `replayed=true`), policy
configuration failure (503), staff evidence visibility and absence of storage/model paths.

- [ ] **Step 2: Run API tests and verify RED**

Run the new test file. Expected: GET analysis returns 404 because the route is absent and POST still
returns the transitional verification-only projection.

- [ ] **Step 3: Replace the transitional POST implementation**

In `ocr.py`, keep the route and readiness/ownership guards, replace
`run_partial_verification_analysis` with `run_analysis`, and return:

```python
{
    "data": {
        "analysis_run_id": result.run.id,
        "transaction_id": transaction.id,
        "status": result.run.status,
        "current_stage": result.run.current_stage,
        "poll_url": f"/api/v1/analyses/{result.run.id}",
        "replayed": result.replayed,
    },
    "meta": _meta(),
}, 202
```

Translate only `AnalysisFailure` into its safe envelope. Unexpected errors follow the shared handler.

- [ ] **Step 4: Add GET analysis and enrich evidence**

Add `@analyses_blueprint.route("/<uuid:analysis_run_id>")`. Use one shared visibility query for GET
analysis/evidence so owner/staff behavior cannot drift. The normal projection includes canonical
band, nullable score/class, reasons, missing signals, limitations, verification, evidence summary,
version snapshot and progress.

Evidence keeps detailed comparisons/stages and staff diagnostic URLs while reusing the same persisted
policy result. Never recompute the policy at read time.

- [ ] **Step 5: Replace generic schema dictionaries at owned boundaries**

Define Marshmallow schemas for policy reason, risk, verification summary, component status,
progress/version and analysis envelope. Preserve dictionaries only for open-ended field comparisons
and controlled deterministic image details.

- [ ] **Step 6: Update and check OpenAPI**

Add `/api/v1/analyses/{analysis_run_id}` to the contract test and assert POST/GET response codes and
nullable risk fields. Run:

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  scripts/export_openapi.py
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  scripts/export_openapi.py --check
```

- [ ] **Step 7: Run focused tests and commit**

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/integration/test_analysis_api.py `
  services/api/tests/integration/test_ocr_workflow.py `
  services/api/tests/contract/test_openapi.py -q --no-cov
git add services/api/src/momo_fdvs/api/v1/ocr.py `
  services/api/src/momo_fdvs/api/v1/ocr_schemas.py `
  services/api/src/momo_fdvs/api/v1/analyses.py `
  services/api/src/momo_fdvs/api/v1/analysis_schemas.py `
  services/api/tests/integration/test_analysis_api.py `
  services/api/tests/contract/test_openapi.py packages/api-client/openapi.json
git commit -m "feat(api): expose persisted analysis results"
```

---

### Task 4: Owner transaction history and immutable detail APIs

**Files:**
- Modify: `services/api/src/momo_fdvs/api/v1/transactions.py`
- Modify: `services/api/src/momo_fdvs/api/v1/transaction_schemas.py`
- Create: `services/api/tests/integration/test_transaction_history_api.py`
- Modify: `services/api/tests/contract/test_openapi.py`

**Interfaces:**
- Consumes: persisted `Transaction.latest_analysis_run`, OCR confirmation and safe receipt projections.
- Produces: paginated `GET /transactions` and owner-safe `GET /transactions/{id}`.

- [ ] **Step 1: Write failing history/detail tests**

Create two owners with multiple persisted runs. Assert:

```python
history = client.get(
    "/api/v1/transactions?page=1&page_size=20&band=inconclusive",
    headers=auth_headers(owner),
)
assert history.status_code == 200
assert all(row["owner_visible"] for row in history.json["data"]["items"])
assert other_transaction_id not in {
    row["id"] for row in history.json["data"]["items"]
}

detail = client.get(
    f"/api/v1/transactions/{transaction_id}", headers=auth_headers(owner)
)
assert detail.json["data"]["latest_analysis"]["id"] == str(latest_run.id)
assert len(detail.json["data"]["analysis_runs"]) == 2
```

Add pagination bounds (1–100), stable newest-first ordering, provider/status/verification/band filters,
cross-owner 404 and proof that activating a different policy/model does not change history.

- [ ] **Step 2: Run tests and verify RED**

Expected: GET on the collection/detail is method-not-allowed or absent.

- [ ] **Step 3: Implement bounded owner queries**

Add `get()` to `TransactionsResource` without changing POST. Parse query parameters with a
Marshmallow query schema. Always filter `Transaction.user_id == g.current_user.id`, cap page size at
100 and eager-load only the latest run/receipt fields required by the projection.

Translate canonical bands:

```python
BAND_TO_LEGACY = {
    "low_risk": "GENUINE",
    "medium_risk": "SUSPICIOUS",
    "high_risk": "FRAUDULENT",
}
```

For `inconclusive`, filter latest run `risk_class IS NULL` and `status == "PARTIAL"`.

- [ ] **Step 4: Implement owner-safe detail**

Add `/transactions/<uuid:transaction_id>` before the more specific receipt route declaration or in a
non-conflicting resource class. Return masked reference, provider/status/timestamps, protected
thumbnail endpoint, confirmed-field coverage/correction count, latest analysis summary and bounded
prior-run summaries. Do not return confirmed values, raw OCR, storage keys or another user's IDs.

- [ ] **Step 5: Update OpenAPI, run tests and commit**

```powershell
$env:PYTHONPATH = "$PWD/services/api/src"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m pytest services/api/tests/integration/test_transaction_history_api.py `
  services/api/tests/integration/test_receipt_upload.py `
  services/api/tests/contract/test_openapi.py -q --no-cov
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  scripts/export_openapi.py
git add services/api/src/momo_fdvs/api/v1/transactions.py `
  services/api/src/momo_fdvs/api/v1/transaction_schemas.py `
  services/api/tests/integration/test_transaction_history_api.py `
  services/api/tests/contract/test_openapi.py packages/api-client/openapi.json
git commit -m "feat(transactions): add immutable owner history"
```

---

### Task 5: Zod-validated mobile analysis and history clients

**Files:**
- Create: `apps/mobile/src/types/analysis.ts`
- Create: `apps/mobile/src/types/history.ts`
- Create: `apps/mobile/src/lib/analysis-client.ts`
- Create: `apps/mobile/src/lib/history-client.ts`
- Create: `apps/mobile/src/lib/__tests__/analysis-client.test.ts`
- Create: `apps/mobile/src/lib/__tests__/history-client.test.ts`
- Modify: `apps/mobile/src/lib/verification-client.ts`
- Modify: `apps/mobile/src/lib/__tests__/verification-client.test.ts`

**Interfaces:**
- Consumes: authenticated `JsonRequest` from the existing API layer and PR18 API envelopes.
- Produces: `startAnalysis`, `getAnalysis`, `pollAnalysis`, `listTransactions`, `getTransaction`, schema-derived TypeScript types and controlled `AnalysisContractError`.

- [ ] **Step 1: Write failing client contract tests**

Use a real valid envelope fixture and a small fake transport. Assert:

```typescript
const started = await startAnalysis(
  request,
  "transaction-id",
  "analysis-key-123",
);
expect(started.analysis_run_id).toBe("analysis-id");
expect(request.calls[0]).toEqual([
  "/api/v1/transactions/transaction-id/analyses",
  { method: "POST", headers: { "Idempotency-Key": "analysis-key-123" } },
]);

await expect(getAnalysis(badEnumRequest, "analysis-id")).rejects.toThrow(
  "Analysis response is incompatible",
);
```

Test `pollAnalysis` for queued → processing → partial, cancellation via `AbortSignal`, maximum attempt
timeout and capped delays with an injected no-wait scheduler. Test history query encoding and invalid
page/band rejection.

- [ ] **Step 2: Run Jest and verify RED**

```powershell
npm.cmd --prefix apps/mobile test -- --runTestsByPath `
  src/lib/__tests__/analysis-client.test.ts `
  src/lib/__tests__/history-client.test.ts
```

Expected: modules do not exist.

- [ ] **Step 3: Implement exact Zod schemas**

Define `riskBandSchema`, `analysisStatusSchema`, `verificationSchema`, `componentStatusSchema`,
`analysisSchema`, `transactionSummarySchema` and `transactionDetailSchema`. Use `.strict()` for owned
objects and allow only the documented enums. Do not coerce unknown enum values.

- [ ] **Step 4: Implement bounded clients**

Use these signatures:

```typescript
export async function startAnalysis(
  request: JsonRequest,
  transactionId: string,
  idempotencyKey: string,
): Promise<AnalysisStart>;

export async function getAnalysis(
  request: JsonRequest,
  analysisRunId: string,
): Promise<AnalysisResult>;

export async function pollAnalysis(
  request: JsonRequest,
  analysisRunId: string,
  options?: { signal?: AbortSignal; maxAttempts?: number; wait?: (ms: number) => Promise<void> },
): Promise<AnalysisResult>;
```

Default polling uses at most 12 attempts with delay `min(500 * 2 ** attempt, 5000)` milliseconds.
Stop on `COMPLETED`, `PARTIAL`, `FAILED` or `CANCELLED`. URL-encode every path/query value.

History methods accept an explicit filter object and cap `page_size` at 100 before issuing a request.

- [ ] **Step 5: Retire transitional verification client behavior**

Keep verification display helpers, move start-analysis transport into `analysis-client.ts`, and update
existing tests/imports. Do not duplicate request types.

- [ ] **Step 6: Run mobile client gates and commit**

```powershell
npm.cmd --prefix apps/mobile run format:check
npm.cmd --prefix apps/mobile run lint
npm.cmd --prefix apps/mobile run typecheck
npm.cmd --prefix apps/mobile test -- --runTestsByPath `
  src/lib/__tests__/analysis-client.test.ts `
  src/lib/__tests__/history-client.test.ts `
  src/lib/__tests__/verification-client.test.ts
git add apps/mobile/src/types/analysis.ts apps/mobile/src/types/history.ts `
  apps/mobile/src/lib/analysis-client.ts apps/mobile/src/lib/history-client.ts `
  apps/mobile/src/lib/verification-client.ts apps/mobile/src/lib/__tests__
git commit -m "feat(mobile): add analysis and history clients"
```

---

### Task 6: Mobile result, history and transaction-detail experience

**Files:**
- Create: `apps/mobile/src/components/analysis-result.tsx`
- Create: `apps/mobile/src/components/transaction-history.tsx`
- Create: `apps/mobile/src/components/__tests__/analysis-result.test.tsx`
- Create: `apps/mobile/src/components/__tests__/transaction-history.test.tsx`
- Create: `apps/mobile/src/app/analysis/[analysisRunId].tsx`
- Create: `apps/mobile/src/app/transaction/[transactionId].tsx`
- Modify: `apps/mobile/src/app/ocr/[transactionId].tsx`
- Modify: `apps/mobile/src/app/(tabs)/history.tsx`
- Modify: `apps/mobile/src/app/(tabs)/home.tsx`
- Modify: `apps/mobile/src/app/_layout.tsx`

**Interfaces:**
- Consumes: typed clients/results from Task 5, existing auth/network contexts and UI primitives.
- Produces: accessible presentational result/history components plus routed query screens.

- [ ] **Step 1: Write failing presentational tests**

Test real rendered output for:

```tsx
const view = render(<AnalysisResultView result={partialResult} />);
expect(view.getByText("Inconclusive")).toBeTruthy();
expect(view.getByText("Transaction verification")).toBeTruthy();
expect(view.getByText("Fraud risk assessment")).toBeTruthy();
expect(view.getByText("Image model unavailable")).toBeTruthy();
expect(view.queryByText(/verified genuine|confirmed fraud|safe/i)).toBeNull();
```

Add high-risk categorical/null-score, model-unavailable, verification mismatch, missing signals,
limitations, empty history and populated history tests. Assert accessible text labels convey status
without relying on colour.

- [ ] **Step 2: Run component tests and verify RED**

Expected: component modules do not exist.

- [ ] **Step 3: Implement focused presentational components**

`AnalysisResultView` renders separate cards for status/evidence quality, verification, risk reasons,
confirmed OCR coverage, deterministic image evidence, model availability and limitations. Never
render a score label when score is null.

`TransactionHistoryView` accepts items, pending/error/empty state and an `onOpen(id)` callback. Each
row displays date/provider, verification, canonical band/status and a text action.

- [ ] **Step 4: Implement routed query screens**

The analysis screen validates route ID, restores auth, handles offline, calls `pollAnalysis` with an
AbortController and displays retry/resume. The transaction detail screen fetches persisted detail and
links to its latest/prior analysis IDs.

History uses TanStack Query, resets page when filters change, and keeps empty/loading/error/offline
states explicit.

- [ ] **Step 5: Change OCR confirmation handoff**

After `startAnalysis` succeeds, navigate with:

```typescript
router.replace({
  pathname: "/analysis/[analysisRunId]",
  params: { analysisRunId: result.analysis_run_id },
});
```

Remove the transitional inline verification/risk result cards from the OCR screen. OCR remains only
review/confirmation/start-analysis.

- [ ] **Step 6: Register routes and safe home/history navigation**

Add both dynamic routes to the root Stack. Home links to upload and history without claiming a
successful model. History opens `/transaction/[transactionId]`.

- [ ] **Step 7: Run mobile tests/build and commit**

```powershell
npm.cmd --prefix apps/mobile run format:check
npm.cmd --prefix apps/mobile run lint
npm.cmd --prefix apps/mobile run typecheck
npm.cmd --prefix apps/mobile run test:ci
npm.cmd --prefix apps/mobile run build:web
git add apps/mobile/src/components apps/mobile/src/app apps/mobile/src/lib
git commit -m "feat(mobile): complete screenshot analysis journey"
```

---

### Task 7: Controlled vertical slice, OpenAPI and full verification

**Files:**
- Create: `services/api/tests/integration/test_analysis_journey.py`
- Modify: `services/api/src/momo_fdvs/seeds.py`
- Modify: `services/api/tests/integration/test_auth_seed.py`
- Modify: `packages/api-client/openapi.json`

**Interfaces:**
- Consumes: controlled fictitious receipt fixtures, seeded demo rule set and all PR18 APIs.
- Produces: one repeatable login/upload/OCR-confirm/analysis/result/history/detail test with safe IDs.

- [ ] **Step 1: Write the failing journey test**

Exercise:

```text
register/login
POST controlled fictitious receipt
POST OCR or controlled OCR fixture path
POST immutable confirmation
POST analysis
GET analysis
GET transactions
GET transaction detail
GET analysis evidence
```

Assert the same analysis ID appears in result/history/detail, the locked-test access flag remains
false, risk and verification differ structurally, and no private path/value appears in serialized
output or captured logs.

- [ ] **Step 2: Run the journey test and verify RED**

Expected: failure at the first missing PR18 projection or seed condition, not fixture setup.

- [ ] **Step 3: Extend only fictitious seed data required by the journey**

Reuse controlled repository images and `demo-1` rule set. Keep the image model inactive. Do not add
real provider receipts, private records or model binaries. Seed changes must remain idempotent.

- [ ] **Step 4: Run backend verification**

```powershell
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe scripts/verify_backend.py
```

This must pass formatting, Ruff, strict mypy, API tests and OpenAPI drift. Record exact counts.

- [ ] **Step 5: Verify migration boundaries**

Run the exact disposable-database sequence:

```powershell
docker compose up -d db
docker compose exec -T db createdb -U momo_fdvs momo_fdvs_pr18_empty
docker compose exec -T db createdb -U momo_fdvs momo_fdvs_pr18_previous
$env:PYTHONPATH = "$PWD/services/api/src"
$env:DATABASE_URL = "postgresql+psycopg://momo_fdvs:momo_fdvs_local_only@localhost:5432/momo_fdvs_pr18_empty"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m flask --app momo_fdvs db upgrade
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m flask --app momo_fdvs db current
$env:DATABASE_URL = "postgresql+psycopg://momo_fdvs:momo_fdvs_local_only@localhost:5432/momo_fdvs_pr18_previous"
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m flask --app momo_fdvs db upgrade 20260809_0001
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m flask --app momo_fdvs db upgrade
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe `
  -m flask --app momo_fdvs db current
docker compose exec -T db dropdb -U momo_fdvs momo_fdvs_pr18_empty
docker compose exec -T db dropdb -U momo_fdvs momo_fdvs_pr18_previous
```

Both `current` calls must report `20260809_0002`; `git status` must contain no generated migration.

- [ ] **Step 6: Run ML and privacy gates**

```powershell
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe scripts/verify_ml.py
& C:\Users\David_A\Desktop\CS\momoFraudDetection\.venv\Scripts\python.exe scripts/check_secrets.py
```

Record exact tests/coverage/candidate counts and verify no locked-test or training path ran.

- [ ] **Step 7: Run mobile verification under pinned Node/npm**

```powershell
npm.cmd --prefix apps/mobile ci
npm.cmd --prefix apps/mobile run format:check
npm.cmd --prefix apps/mobile run lint
npm.cmd --prefix apps/mobile run typecheck
npm.cmd --prefix apps/mobile run test:ci
npm.cmd --prefix apps/mobile run build:web
```

If the host remains Node 22/npm 10.9.8, record the exact host blocker and run the repository's pinned
toolchain/container route; do not change pins or claim the host gate passed.

- [ ] **Step 8: Run the controlled live PostgreSQL journey**

Start `db` and `api` with Docker Compose, check health/readiness, run the same fictitious journey and
capture only safe request/run UUIDs plus build SHA. Stop services normally after evidence capture.

- [ ] **Step 9: Commit Task 7**

```powershell
git add services/api/tests/integration/test_analysis_journey.py `
  services/api/src/momo_fdvs/seeds.py `
  services/api/tests/integration/test_auth_seed.py `
  packages/api-client/openapi.json
git commit -m "test(analysis): prove controlled mobile-ready journey"
```

---

### Task 8: PR18 evidence, review and publication

**Files:**
- Modify: `IMPLEMENTATION_STATUS.md`
- Modify: `requirements_traceability.csv`
- Modify: `DECISION_LOG.md` only for an actual compatibility/deviation decision
- Modify: `CHANGELOG.md`
- Create: `docs/evidence/PR18_ANALYSIS_PRODUCT.json`
- Modify: `docs/evidence/EVIDENCE_MANIFEST.csv`
- Create: `docs/handoffs/2026-08-15-PR18-analysis-product.md`

**Interfaces:**
- Consumes: exact fresh commands/results, commit identities, policy hash, OpenAPI hash and live safe IDs.
- Produces: public aggregate-only evidence and an auditable PR18 handoff.

- [ ] **Step 1: Record exact evidence without private values**

The evidence JSON must include branch/base/head, policy version/hash, OpenAPI hash, commands/results,
component availability, `image_model_active=false`, `locked_test_accessed=false`,
`training_executed=false`, privacy flags and live journey status. Canonically self-hash it using the
existing evidence convention.

- [ ] **Step 2: Update status, traceability, changelog and handoff**

State what is active:

- OCR review/correction;
- stored/imported reference verification;
- deterministic image evidence;
- categorical policy/orchestration;
- persisted mobile result/history/detail.

State what remains unavailable:

- accepted CNN image classifier/localizer;
- screenshot-derived structured history;
- live provider verification;
- locked-test/final metrics;
- hosted CI while billing is blocked;
- deployment credentials.

- [ ] **Step 3: Run final prohibited-content and consistency checks**

Parse JSON/CSV, verify evidence hashes, run `git diff --check`, search for private paths/values and
run the final secret scan. Inspect `git diff`, `git status`, ancestry and migration head.

- [ ] **Step 4: Run final fresh applicable suites**

Rerun backend, mobile, ML, secret and controlled journey gates after documentation changes. Do not
reuse earlier output for final claims.

- [ ] **Step 5: Commit documentation**

```powershell
git add IMPLEMENTATION_STATUS.md requirements_traceability.csv DECISION_LOG.md `
  CHANGELOG.md docs/evidence docs/handoffs/2026-08-15-PR18-analysis-product.md
git commit -m "docs(handoff): record PR18 analysis product evidence"
```

- [ ] **Step 6: Review, push and open the PR**

Perform a scoped branch review against `d9b096af…`, fix validated findings test-first, rerun affected
and full gates, then:

```powershell
git push -u origin codex/pr18-analysis-product
gh pr create --base codex/p17-ocr-benchmark `
  --head codex/pr18-analysis-product `
  --title "feat(analysis): complete evidence-aware receipt analysis journey"
```

Use a stacked PR base while PR17 remains open. After PR17 merges, retarget PR18 to `main` without
rewriting history. Verify the remote head, PR state/body marker and clean tracking branch.
