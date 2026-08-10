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
| `data/registry.yaml` for PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private | `complete` | Logical PR11 registers exactly the six sources and leaves every entry disabled/not acquired; FSTS is optional and Ghana-private requires consent/internal-only handling. |
| Dataset cards with source/version/licence/use/limits/distribution/citation | `complete` | `data/cards/` contains a card for every source. Unknown terms are recorded as unverified/blocked rather than inferred as permission. |
| JSON schemas for transactions, screenshots, OCR truth, edits, splits and runs | `complete` | Six strict JSON Schema 2020-12 documents are aligned with executable validators and fictitious examples. |
| Data dictionary and tamper taxonomy | `complete` | `data/DATA_DICTIONARY.md` defines portable fields and `data/tamper-taxonomy.json` records the canonical target/method plan. |
| Participant information, consent, publication scope, withdrawal/deletion, de-identification, roles, retention and incident process | `complete` | `data/governance/` provides templates and procedures; the executable withdrawal ledger blocks pseudonymous participant hashes. No completed/private record is committed. |
| Threat model and `DATA_ACCESS.md` | `complete` | Repository-root access rules and `docs/security/PR11_DATA_THREAT_MODEL.md` define boundaries, threats and mitigations. |
| Ignore rules for data/checkpoints/models/secrets/consent | `complete` | `.gitignore` and the repository scanner cover raw/private/authorised data, consent/withdrawal records, checkpoints, models, secrets and credentials. |
| Large-file, secret and PII-filename validators | `complete` | The scanner retains the 10 MiB budget and rejects Ghana-phone, email and person-labelled sensitive filenames, with negative tests. |
| Fictitious fixtures and provenance card | `complete` | Six portable fixtures, a synthetic withdrawal ledger and `data/fixtures/PROVENANCE.md` are deterministic and contain explicit fictitious markers. |

### Required tests

| Blueprint test | Status | Evidence and gap |
|---|---|---|
| Registry/schema validation | `complete` | `momo_fdvs_ml.governance` validates exact source IDs, fail-closed enablement, card/schema links and strict portable-schema alignment. |
| All fixtures validate | `complete` | Registered ML verification validates all six portable fixtures plus existing controlled image/structured reports. |
| Raw paths ignored | `complete` | `.gitignore`, scanner and manifest path-containment tests cover raw/private/authorised paths. |
| Secret/PII/large-file negative harness | `complete` | Backend unit tests exercise credential, prohibited path/artifact, PII filename and oversized-file rejection. |
| Consent scope required for private records | `complete` | Controlled-real screenshots require a participant hash and internal/release consent scope; synthetic fixtures prohibit participant linkage; withdrawals fail closed. |
| Taxonomy percentages sum to 100% | `complete` | The registered governance gate verifies exact categories, non-negative integer percentages and total 100. |

### Done assessment

`complete locally on logical PR11`. The deterministic governance report records six disabled sources, six schemas, six fictitious fixtures, a 100% taxonomy total and explicit `acquisition_executed: false`/`training_executed: false`. Dataset acquisition remains a later owner-reviewed boundary.

## Logical PR12 — Reproducible Colab foundation

### Work items

| Blueprint requirement | Status | Repository evidence and gap |
|---|---|---|
| Locked environments | `complete` | Logical PR12 records exact runtime/training/dev lock hashes and validates every active requirement is exact or a local lock include. |
| `00_environment_preflight.ipynb` and notebook template | `complete` | Clean-session preflight, thin template and restart-safe smoke notebooks live under `ml/notebooks/colab/`; stored outputs/counts are prohibited. |
| Drive paths without personal hard-coding | `complete` | `ColabPaths` uses generic configurable Drive/VM roots, rejects relative/nested roots and creates the standard layout. |
| Clone/update and commit recording | `complete` | Credential-free HTTPS checkout is argument-safe, detaches at a full SHA and records clean Git state without persisting the remote URL. |
| Runtime inventory and seeding | `complete` | Allowlisted runtime/package/accelerator/RAM inventory and deterministic Python/NumPy seeds enter every manifest. |
| Run IDs/manifests, atomic writer, checkpoints and resume | `complete locally` | `colab-run-manifest-v1`, atomic fsync/replace, immutable ledger entries, hash-before-resume, Drive mirroring and interrupted-session history are implemented and tested. |
| SMOKE/FULL parameters | `complete` | UNIT, SMOKE and FULL are executable boundaries; smoke has hard row/image/epoch/test caps and all outputs are non-promotable. |
| Colab Secrets loading without printing | `complete` | `SecretBundle` loads named Colab secrets in memory, redacts representation and exposes only names for safe logging. |
| Notebook lint/output checks | `complete` | The registered notebook policy checks structure, outputs, counts, credentials, personal paths, ad-hoc installs, thin wrappers and stop boundaries. |
| Tiny end-to-end smoke notebook | `complete` | The owner-operated signed-in Colab run completed at clean code commit `b2e6b24a…`; the safe evidence records prediction digest `43833f49…`, owner-reported manifest SHA-256 `bb0ebffb…`, and acquisition/FULL/promotion false. |
| Lost-runtime recovery runbook | `complete` | `ml/COLAB_RUNTIME_RECOVERY.md` documents same-run restore, corruption handling, evidence return and incident boundaries. |
| CI cannot enter full mode | `complete` | CI pins UNIT and explicitly invokes `assert_ci_profile_is_safe`; code/tests reject CI FULL even with Colab markers. |

### Smoke flow and required tests

| Blueprint requirement | Status | Evidence and gap |
|---|---|---|
| Complete smoke flow emits a run manifest | `complete` | Local integration tests validate the flow, and signed-in Colab produced run `20260810T161011Z_smoke-foundation_b2e6b24a_seed20260810` with an owner-reported manifest SHA-256. |
| Deterministic fixture split/predictions | `complete locally` | Two isolated runs produce the same prediction digest; transaction/image smoke excludes the committed test split and export/reload uses `1e-9` tolerance. |
| Corrupt checkpoint rejected; valid checkpoint resumes | `complete locally` | Tests simulate runtime loss, restore a valid mirrored checkpoint into a fresh VM path and reject modified durable bytes. |
| Secrets absent from notebooks/logs | `complete` | Notebook policy plus repository secret/artifact scanning rejects assigned credentials and retained output; secret values are redacted by construction. |
| Run manifest validates | `complete` | Portable JSON Schema and strict runtime validation cover Git/runtime/locks/data/config/features/artifacts/checkpoints/session history and execution flags. |
| Restart-and-run-all | `complete` | The owner ran preflight and smoke in signed-in Colab. After one expected kernel restart to clear a NumPy in-process upgrade mismatch, the smoke completed without acquisition or FULL mode. Notebook policy v2 permanently enforces the live-kernel source path repair found during the first attempt. |
| Full mode blocked locally/CI | `complete` | Existing reportable CLIs require acknowledged non-CI Colab FULL; CI explicitly checks its UNIT selection and smoke cannot enter those CLIs. |

### Done assessment

`complete`. Registered ML verification passes the runtime, notebook, manifest, deterministic prediction, corruption and resume suite. The owner-operated signed-in Colab preflight/smoke completed at clean commit `b2e6b24a…`; safe evidence is recorded in `docs/evidence/PR12_COLAB_FOUNDATION_SMOKE.json`. The run performed no acquisition, held-out evaluation, reportable training or artifact promotion.

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

## Post-audit implementation update — evidence and execution foundation

Branch `codex/p10-evidence-execution-foundation` implements the first two ordered backlog items without changing the historical audit evidence:

- `evidence-result-v1` now defines screenshot-only, transaction-only, combined and inconclusive modes with explicit nullable unavailable signals;
- new contracts use `unaltered`/`tampered` and low/medium/high/inconclusive, while named adapters preserve existing manifests, artifacts, database records and public enums;
- newly governed image labels reject `genuine`, `fake` and other authenticity terms;
- current structured/image training entry points require acknowledged FULL mode in detected Google Colab and reject local/CI execution;
- CI pins UNIT and registers `scripts/verify_ml.py`;
- unit tests enforce the blueprint's mode/nullability/wording/full-guard requirements.

Logical PR10 is still `partial/not done` because final production orchestration/API/UI adoption and the reusable SMOKE workflow remain later versioned work. Dataset acquisition and model training did not occur in this update.
