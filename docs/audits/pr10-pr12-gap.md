# Logical PR10-PR12 Gap Audit

- Audit date: 2026-08-10
- Audit branch: `codex/audit-fix-10-pr10-pr12-reconciliation`
- Audit base: `fa72c5b989f8ce75cda1a15a3b56f28aa7b0e6c4`
- Blueprint: `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md`
- Scope: repository evidence through the failed controlled P12 experiment plus the separate Ghana-corpus branch

## Status vocabulary

- `complete`: implemented and backed by applicable tests/evidence.
- `partial`: useful implementation exists but does not satisfy the complete blueprint item.
- `absent`: no implementation/evidence was found.
- `conflicting`: the blueprint item differs from a higher-precedence fixed or implemented contract and needs an explicit migration.

## Repository/PR reality

The blueprint's PR numbers are logical milestones. They do not match the actual GitHub history and must not be recreated merely to align numbering.

| Actual evidence | Repository meaning |
|---|---|
| GitHub PR #10, merge `5ed38ac` | Historical P09 deterministic image forensics |
| GitHub PR #11/#12, heads `2e2c1fd`/`d996114` | Historical P10 controlled dataset governance/publication |
| GitHub PR #13/#14, merge `42a0ec6`, publication head `2c4e88e` | Historical P11 controlled structured model and merge evidence |
| Branch `codex/p12-cnn-tampering`, head `fa72c5b` | Historical P12 image pipeline plus failed controlled experiment evidence; not merged |
| Branch `codex/p10-ghana-image-corpus`, commits `80bf6c6`/`d73dfb1` | Separate rights/privacy-gated Ghana fraud-message corpus tooling; not merged and based on the P12 pre-evidence head |

## Baseline evidence

| Check | Result |
|---|---|
| Remote refresh | Pass with repository-scoped safe-directory override |
| Toolchain doctor | Blocked: unqualified Node is 22.11.0 instead of pinned 24.14.0; host Tesseract and PostgreSQL CLI are absent. Docker and Python 3.12 pass. |
| Prohibited artifact/secret scan | Pass; 381 candidate files on the P12 branch after evidence import |
| Registered P12-branch ML gate | Pass: Ruff format/lint, strict mypy, 99 tests, 91.83% coverage, controlled/structured/image report drift checks |
| Ghana branch ML baseline before branch switch | Pass: 117 tests, 93.00% coverage |
| P12 artifact evidence | Hash matched private ignored artifact; acceptance failed with held-out macro F1 `0.333333`; artifact not registered or activated |
| Hosted CI | Externally blocked by repository-owner Actions billing/account lock `B-CI-001` |

## Logical PR10 — Architecture correction and Colab-only training

### Work items

| Blueprint requirement | Status | Repository evidence and gap |
|---|---|---|
| ADRs for Colab-only training, evidence modes, unaltered-not-verified and no invented features | `partial` | `DECISION_LOG.md` ADR-014 enforces Colab evidence and ADR-019 adopts reconciliation. `00_SOURCE_OF_TRUTH_AND_SCOPE.md` separates risk from stored verification and prohibits live-MNO claims. Explicit evidence-mode and no-invented-feature ADRs/tests remain missing. |
| Shared image, OCR, semantic, transaction and policy contracts | `partial` | Separate Flask schemas/services exist under `services/api/src/momo_fdvs`; image, OCR and stored verification return explicit unavailable states. There is no shared versioned evidence-mode contract, semantic-message result contract or final policy contract. |
| `screenshot_only`, `transaction_only`, `combined`, `inconclusive` modes | `absent` | Existing partial analyses use `unavailable_stages` and nullable fields but expose no canonical mode enum. |
| Canonical image labels `unaltered`/`tampered` | `conflicting` | Current schema/runtime/tests use `ORIGINAL`/`CONTROLLED_TAMPERED` in `ml/src/momo_fdvs_ml/image_schema.py` and `services/api/src/momo_fdvs/services/image_model.py`. A versioned compatibility migration is required. |
| Risk bands plus nullable unavailable signals | `conflicting` | Nullable risk/tamper values and explicit unavailable states are implemented. Fixed public taxonomy remains `GENUINE`/`SUSPICIOUS`/`FRAUDULENT`; proposed risk bands require database/API/UI migration. |
| Unit/smoke/full profiles and full-training guard | `absent` | Pinned notebooks and local non-training verification exist, but no generic profile contract exists. Training functions are callable wherever dependencies are installed; wording that training “must run in Colab” is not an execution guard. |
| Architecture, README and limitations updates | `partial` | `ml/README.md`, `ml/COLAB_TRAINING_HANDOFF.md`, phase plans, model cards and handoffs document controlled-only limits. They do not describe the full blueprint evidence-mode architecture. |
| API migration and compatibility shim | `absent` | ADR-019 requires one, but no code or contract migration exists yet. |

### Required tests

| Blueprint test | Status | Evidence and gap |
|---|---|---|
| Screenshot-only transaction score is null | `partial` | P08/P09 integration tests prove risk and model values remain null when unavailable, but no `screenshot_only` request/response mode exists. |
| Transaction-only image/OCR signals unavailable | `absent` | No transaction-only contract or test exists. |
| Missing history/balance cannot become zero defaults | `partial` | The current controlled structured schema does not include history/balance fields and preserves nullable CNN/reference comparisons with missingness flags. The future transaction-core schema and explicit forbidden-zero-default test are absent. |
| New canonical data rejects `genuine` image labels | `conflicting` | Current manifest label `genuine` maps to `ORIGINAL`; migration has not begun. |
| Full training blocked without acknowledgement | `absent` | No environment/profile acknowledgement guard exists. |
| No rendered result says safe/verified/100% | `partial` | The UI labels risk as automated and verification as stored/imported-only. `VERIFIED` intentionally remains valid for stored-reference matches, so the blueprint wording must be implemented as “not live/provider verified,” not as removal of the verification record. A dedicated prohibited-copy test is absent. |

### Done assessment

`not done`. Evidence separation and nullable failures provide a strong base, but canonical modes, compatibility contracts and enforceable execution profiles are incomplete.

## Logical PR11 — Governance, schemas and dataset registry

### Work items

| Blueprint requirement | Status | Repository evidence and gap |
|---|---|---|
| `data/registry.yaml` for PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private | `absent` | No canonical dataset registry exists. |
| Dataset cards with source/version/licence/use/limits/distribution/citation | `partial` | Controlled dataset and model cards exist. Canonical PaySim/MoMTSim/STFD/FSTS cards are absent. Ghana protocol exists only on the separate Ghana branch. |
| JSON schemas for transactions, screenshots, OCR truth, edits, splits and runs | `partial` | Typed Python manifest/feature schemas and Flask API schemas exist. Portable JSON Schema documents for all blueprint objects, especially run manifests, are absent. |
| Data dictionary and tamper taxonomy | `partial` | P10 manifest schema, controlled operation provenance and feature schema exist. The blueprint-wide transaction/OCR/edit/tamper dictionary is incomplete. |
| Participant information, consent, publication scope, withdrawal/deletion, de-identification, roles, retention and incident process | `partial` | Existing manifests require consent/licence references; source scope prohibits private training without consent/anonymisation. The separate Ghana branch adds a protocol and release gates, but repository-wide templates, withdrawal ledger and publication checklist are absent. |
| Threat model and `DATA_ACCESS.md` | `absent` | Security specifications and private-storage rules exist, but the named data-access/threat-model artifacts do not. |
| Ignore rules for data/checkpoints/models/secrets/consent | `complete` | `.gitignore` covers private/raw/authorised data, artifacts, checkpoints/model formats and secrets; `scripts/check_secrets.py` verifies policy. |
| Large-file, secret and PII-filename validators | `partial` | Secret/prohibited-artifact and private-path checks exist with tests. A general size budget and PII-filename validator are not complete. |
| Fictitious fixtures and provenance card | `complete` | P10 generic Ghana-style fixtures, deterministic provenance, manifest hashes and dataset report are committed and tested. |

### Required tests

| Blueprint test | Status | Evidence and gap |
|---|---|---|
| Registry/schema validation | `partial` | Manifest/feature schema validation is extensive; registry and run-schema validation are absent. |
| All fixtures validate | `complete` | Registered ML verification validates controlled image/structured fixtures and recorded reports. |
| Raw paths ignored | `complete` | `.gitignore`, scanner and manifest path-containment tests cover raw/private/authorised paths. |
| Secret/PII/large-file negative harness | `partial` | Secret and forbidden artifact regression tests exist; full filename/size matrix is missing. |
| Consent scope required for private records | `partial` | Manifest validation requires `consent_or_licence_reference`; the Ghana branch adds release-right checks. Internal-versus-public scope and withdrawal enforcement are absent. |
| Taxonomy percentages sum to 100% | `absent` | No canonical percentage-based tamper taxonomy artifact/test exists. |

### Done assessment

`not done`. Existing P10 governance is useful and should be preserved, but canonical source registry, portable schemas and executable participant/withdrawal governance must land before acquisition.

## Logical PR12 — Reproducible Colab foundation

### Work items

| Blueprint requirement | Status | Repository evidence and gap |
|---|---|---|
| Locked environments | `partial` | Runtime/dev/training lock files exist for current controlled workflows; one cross-notebook environment/profile contract is absent. |
| `00_environment_preflight.ipynb` and notebook template | `partial` | P10/P11/P12 pinned notebooks exist, but the standard environment notebook/template does not. |
| Drive paths without personal hard-coding | `partial` | Current notebooks avoid committing credentials/private data, but there is no reusable Drive path/config abstraction. |
| Clone/update and commit recording | `partial` | P11/P12 notebooks pin immutable commits and verify checkout. A reusable clone/update library and dirty-checkout manifest field are absent. |
| Runtime inventory and seeding | `partial` | Model reports record Python/framework versions and seeds. There is no standard run inventory schema across notebooks. |
| Run IDs/manifests, atomic writer, checkpoints and resume | `absent` | Model reports and one Keras best checkpoint exist, but no restart-safe run manifest, atomic Drive sync, resume protocol or checkpoint ledger exists. |
| SMOKE/FULL parameters | `absent` | No standard profile enum/config exists. |
| Colab Secrets loading without printing | `absent` | Documentation prohibits embedded secrets; no reusable secret-loader implementation/test exists. |
| Notebook lint/output checks | `partial` | P10 notebook structure is tested and secret scanning covers tracked notebooks. Generic output stripping/lint validation is absent. |
| Tiny end-to-end smoke notebook | `absent` | Current notebooks are phase-specific; none performs the blueprint's full transaction/OCR/image/export/reload flow. |
| Lost-runtime recovery runbook | `partial` | `ml/COLAB_TRAINING_HANDOFF.md` covers clean setup and boundaries, not checkpoint recovery/resume. |
| CI cannot enter full mode | `absent` | CI does not currently run full training, but no fail-closed profile guard enforces that invariant. |

### Smoke flow and required tests

| Blueprint requirement | Status | Evidence and gap |
|---|---|---|
| Complete smoke flow emits a run manifest | `absent` | No combined smoke notebook or run manifest exists. |
| Deterministic fixture split/predictions | `partial` | Dataset/split hashes and controlled model preprocessing are deterministic; cross-runtime prediction tolerance contract is incomplete. |
| Corrupt checkpoint rejected; valid checkpoint resumes | `absent` | Runtime artifact corruption is rejected before inference, but training checkpoint resume/corruption is not implemented. |
| Secrets absent from notebooks/logs | `partial` | Secret scan passes; explicit log/output inspection tests are incomplete. |
| Run manifest validates | `absent` | No run-manifest schema/validator exists. |
| Restart-and-run-all | `absent` | No evidence exists. |
| Full mode blocked locally/CI | `absent` | Policy is documented but not enforced by code. |

### Done assessment

`not done`. Current notebooks prove immutable checkout and real Colab execution, but the reusable restart-safe foundation required before expensive public/private runs is missing.

## Preserved work and conflicts requiring migration

1. Keep Flask, PostgreSQL, Expo/React, TensorFlow/Keras, scikit-learn, Tesseract/OpenCV/Pillow and the current service boundaries.
2. Keep stored/imported reference matching as a separate immutable verification record; label it as non-live provider evidence.
3. Keep deterministic P09 image evidence and P10 leakage/privacy tooling as baselines.
4. Keep P11/P12 controlled runs only as pipeline evidence; P12 failed acceptance and remains inactive.
5. Treat proposed risk bands and tamper labels as versioned migrations, not immediate global replacements.
6. Treat the Ghana fraud-message semantic corpus as separate from receipt-tampering data.

## Ordered reconciliation backlog

1. Implement shared evidence-mode contracts and compatibility projections without changing existing public responses prematurely.
2. Add enforceable `UNIT`/`SMOKE`/`FULL` execution profiles and local/CI guards.
3. Add the canonical dataset registry, portable schemas, access/threat documentation and executable privacy/withdrawal validators.
4. Add standard Colab preflight/template, run manifest, atomic Drive checkpoint/resume and a tiny restart-safe smoke notebook.
5. Re-run all local gates and one clean Colab smoke; stop for owner review.
6. Only then begin logical PR13 acquisition. Do not open locked tests or perform another full training run during reconciliation.

## Audit conclusion

Logical PR10, PR11 and PR12 are all `partial/not done`. The repository contains substantial correct foundations, but proceeding directly to acquisition or another reportable training run would bypass blueprint prerequisites. The next implementation branch should be limited to the ordered reconciliation backlog above.
