# DECISION_LOG.md

Use this file for Architecture Decision Records (ADRs). Do not edit an accepted decision silently; create a superseding ADR.

## ADR template

### ADR-XXX — Title

- **Status:** Proposed / Accepted / Superseded
- **Date:** YYYY-MM-DD
- **Decision owners:** Project owner / Codex / supervisor as applicable
- **Context:** Why a decision is required.
- **Options considered:** Concise alternatives.
- **Decision:** What is chosen.
- **Consequences:** Benefits, costs, risks and follow-up.
- **Related requirements/phases:** IDs.
- **Supersedes:** ADR ID or none.

---

## ADR-001 — Fixed product stack

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Chapter Three specifies React Native/React, Flask, PostgreSQL, Tesseract/OpenCV, TensorFlow/Keras and scikit-learn.
- **Decision:** Use Expo/React Native TypeScript for mobile, React/Vite TypeScript for staff web, Python 3.12/Flask for API/worker, PostgreSQL/SQLAlchemy, Tesseract/OpenCV, TensorFlow/Keras and scikit-learn.
- **Consequences:** Implementation remains aligned with documentation. Replacements require explicit approval.
- **Related:** All phases.

## ADR-002 — Fraud risk and verification are separate

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Visual/ML risk and reference-record verification answer different questions.
- **Decision:** Persist and display risk (`GENUINE`, `SUSPICIOUS`, `FRAUDULENT`) separately from verification (`VERIFIED`, `UNVERIFIED`, `MISMATCH`).
- **Consequences:** APIs, schema, UI and reports require both fields. A mismatch may be a rule input but cannot overwrite verification/risk directly.
- **Related:** FR-VER-005, FR-VER-007, FR-RISK-*.

## ADR-003 — No live MNO claim in prototype

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** No authorised production MNO integration has been supplied.
- **Decision:** Verify against stored/imported reference transactions and label the basis clearly.
- **Consequences:** Live MNO adapter remains future work. Demo/reference imports must be safe and auditable.
- **Related:** P08, FR-VER-006.

## ADR-004 — Private object storage

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Receipt images contain sensitive financial/personal evidence and can be large.
- **Decision:** Store images/reports/model artifacts in private storage; PostgreSQL stores metadata, keys and hashes.
- **Consequences:** Downloads require server policy or short signed URL; no public web path.
- **Related:** P02, P06, NFR-SEC-003.

## ADR-005 — PostgreSQL-backed analysis queue

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** CPU-heavy analysis should not block Flask web workers, but a mandatory Redis service would add prototype complexity.
- **Decision:** Use persisted analysis runs and a separate worker with safe PostgreSQL row claiming. Keep a dispatcher boundary for later queue replacement.
- **Consequences:** Worker/recovery/concurrency logic must be tested. API returns 202/polling.
- **Related:** P13, worker architecture.

## ADR-006 — Versioned immutable analytical evidence

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Models, rules, templates and OCR pipelines will evolve.
- **Decision:** Every analysis snapshots versions/configuration; completed evidence is not overwritten. Reanalysis creates a new run.
- **Consequences:** More storage and schema complexity, but full traceability.
- **Related:** FR-RISK-007, NFR-AUD-001.

## ADR-007 — Explicit partial-analysis state

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Model artifacts, Tesseract or other subsystems may be unavailable.
- **Decision:** Preserve successful evidence and return `PARTIAL` with disclosed missing components; never fabricate a probability.
- **Consequences:** UI/API/tests must support degraded states.
- **Related:** FR-ML-003, FR-RISK-005.

## ADR-008 — OpenAPI-generated TypeScript contract

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Two TypeScript clients must stay consistent with Flask responses.
- **Decision:** Generate shared API types/client from the backend OpenAPI contract.
- **Consequences:** CI checks contract drift; client-visible changes update all consumers.
- **Related:** P01, P04, P05.

## ADR-009 — Wireframes remain design artefacts

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** Supervisor requires actual wireframes to be distinguishable from system interfaces.
- **Decision:** Preserve monochrome low-fidelity Chapter Three wireframes; implement polished interfaces separately and capture them for Chapter Four.
- **Consequences:** Documentation/evidence must label artefact type.
- **Related:** P17, P20.

## ADR-010 — Controlled/synthetic data is labelled

- **Status:** Accepted
- **Date:** Initial plan
- **Context:** A lawful representative real fraud dataset may be unavailable.
- **Decision:** Build reproducible controlled sample tooling, label synthetic scope and never claim provider-wide production performance from it.
- **Consequences:** Model metrics may remain limited; limitation is academically explicit.
- **Related:** P10-P12, FR-ML-005.

## ADR-011 — P00 runtime version baseline

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Codex, pending project-owner confirmation only if institutional constraints differ
- **Context:** The new repository needs pinned runtime directions before application scaffolding. Python 3.12.10 and Node.js 22.11.0 are available on the preflight machine. The unqualified Windows `python` command resolves to Python 3.11.7, while the Python launcher exposes 3.12.
- **Options considered:** Python 3.11 versus the specified Python 3.12; Node 20 versus the installed Node 22 LTS line.
- **Decision:** Pin Python 3.12 through `.python-version` and Node major 22 through `.nvmrc`. Use `py -3.12` in Windows P00 commands and retain cross-platform `python` examples when the selected environment already resolves to 3.12.
- **Consequences:** P01 dependency compatibility must be verified against Python 3.12 and Node 22. Windows documentation must not assume `python` selects 3.12 or that PowerShell permits `npm.ps1`; `npm.cmd` is the safe observed command.
- **Related requirements/phases:** P00, P01, P04, P05, NFR-MNT-001, NFR-COMP-001.
- **Supersedes:** None.

## ADR-012 — New local repository with deferred remote

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Codex; project owner must supply the remote
- **Context:** The selected workspace was empty and was not a Git repository. No existing history, default remote branch, CI, or GitHub repository could be discovered.
- **Options considered:** Stop before local work; initialise locally and preserve a remote blocker; guess or create an unauthorised remote.
- **Decision:** Initialise a local repository, create `codex/p00-preflight-foundation`, complete and commit the safe P00 foundation, and explicitly block phase completion on the missing remote push evidence.
- **Consequences:** The local work is reproducible and preserved. P00 remains blocked—not complete—until `origin` is configured and the phase branch is pushed successfully.
- **Related requirements/phases:** P00, NFR-MNT-001, NFR-DATA-001.
- **Supersedes:** None.

## ADR-013 — Schema-generated P01 contract and split readiness

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Codex within the approved P01 architecture
- **Context:** P01 must generate OpenAPI from live response schemas and distinguish an API that can serve non-analysis routes from later OCR/model capabilities that are not yet activated.
- **Options considered:** Hand-maintained OpenAPI versus Flask-Smorest/Marshmallow generation; one all-or-nothing readiness flag versus a core readiness flag plus explicit analysis capabilities.
- **Decision:** Use Flask-Smorest with Marshmallow response schemas as the OpenAPI source. `/ready` requires PostgreSQL and private storage for core readiness, reports Tesseract and both model slots independently, and never labels inactive analysis components as ready.
- **Consequences:** Both clients receive a deterministic contract snapshot. The API can remain operational for non-analysis routes while exposing `analysis_available` and `full_analysis_available` honestly. Later phases must extend schemas and regenerate the snapshot rather than editing JSON by hand.
- **Related requirements/phases:** P01, FR-AUD-003, FR-AUD-005, NFR-INT-001, ADR-007, ADR-008.
- **Supersedes:** None.

## ADR-014 — Google Colab for model-training execution

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Project owner
- **Context:** The project owner requested Google Colab for the compute-intensive structured and image model training runs. The repository must still preserve reproducibility, provenance and inference compatibility.
- **Options considered:** Train on the implementation workstation; train in Google Colab; use an unspecified external managed trainer.
- **Decision:** Complete local product and data-governance phases through P10, including deterministic split/manifests and Colab-ready notebooks or scripts. Stop before the first P11 training run and hand the project owner exact Colab instructions. Training evidence, metrics and artifact hashes enter the repository only after a real Colab execution.
- **Consequences:** Local tests may validate preprocessing, leakage guards and small non-training fixtures, but must not claim model performance. Colab runs must record the dataset manifest hash, split seed, code commit, dependency versions, per-class metrics, macro F1, confusion matrix and exported artifact hash. Private data and credentials must not be committed or embedded in notebooks.
- **Related requirements/phases:** P10, P11, P12, FR-ML-001, FR-ML-003, FR-ML-004, FR-ML-005, FR-ML-006, FR-ML-007, NFR-DATA-001.
- **Supersedes:** None.

## ADR-015 — P04 mobile runtime baseline update

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Codex within the approved Expo technology direction
- **Context:** P04 uses the current Expo SDK 57 baseline, whose React Native 0.86 dependency requires Node.js 22.13.0 or newer. The workstation's unqualified Node.js 22.11.0 does not meet that engine requirement, while the workspace provides Node.js 24.14.0.
- **Options considered:** Use the unsupported installed Node.js 22.11.0; downgrade Expo below the current supported SDK; pin the available supported Node.js 24.14.0 runtime.
- **Decision:** Pin Node.js 24.14.0 and npm 10.9.0 for repository JavaScript work. Mobile verification and CI must use that exact baseline.
- **Consequences:** Contributors must activate Node.js 24.14.0 before mobile commands. This supersedes only the Node.js portion of ADR-011; Python 3.12 remains unchanged. No product scope or selected technology changes.
- **Related requirements/phases:** P04, P05, NFR-MNT-001, NFR-COMP-001.
- **Supersedes:** ADR-011 Node.js 22 direction.

## ADR-016 — Controlled P11 model is pipeline evidence, not production evidence

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Codex within ADR-010/ADR-014 and the approved P11 scope
- **Context:** No authorised representative real fraud dataset is available. The governed P10 corpus has six isolated source groups, so P11 can support an honest controlled pipeline run but cannot estimate provider-wide generalisation or fit a defensible probability calibrator.
- **Options considered:** Invent or scrape real labels; postpone every P11 integration; train the deterministic controlled baseline and preserve its limitations.
- **Decision:** Train the P11 Random Forest only in signed-in Google Colab on deterministic controlled scenarios. Fit preprocessing/model state on four training groups, select thresholds on one validation group, touch the one-group/three-sample held-out test once, and publish all per-class metrics plus calibration diagnostics. Do not fit a calibrator. A passing controlled acceptance gate permits prototype `READY` registration but never a production-readiness or provider-accuracy claim.
- **Consequences:** The measured macro F1 and balanced accuracy of 1.0 demonstrate pipeline correctness only. The model card must retain the one-group/three-sample limitation, human review remains required, and future authorised data requires a new version and evaluation. The private joblib artifact remains outside Git and is SHA-256 verified before every trusted load.
- **Related requirements/phases:** P11, FR-ML-001, FR-ML-002, FR-ML-004, FR-ML-005, FR-ML-006, FR-ML-007, NFR-ACC-002, ADR-010, ADR-014.
- **Supersedes:** None.

## ADR-018 — Failed P12 controlled image artifact remains inactive

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Codex within ADR-010/ADR-014 and the measured P12 acceptance contract
- **Context:** The owner-authorised signed-in Colab run completed on the six-group/twelve-image controlled corpus. Validation and held-out macro F1 were both `0.333333`; both held-out images were classified as `CONTROLLED_TAMPERED` at the validation-selected threshold `0.05`. The configured acceptance minimum was `0.85`.
- **Options considered:** Activate the artifact because packaging/hash checks passed; rerun or tune against the two held-out samples; preserve the failed experiment and keep the adapter unavailable.
- **Decision:** Preserve safe metrics, hashes, confusion matrix, latency and model-card evidence, but do not register or activate the private Keras artifact. Do not tune or rerun against the exhausted held-out partition. Treat the result as controlled experimental pipeline evidence and require a new model version, representative authorised grouped data and newly frozen partitions before another reportable run.
- **Consequences:** P12 remains In Progress. Image-model inference continues to return an explicit unavailable state with null probability. The private artifact stays outside Git. Documentation must distinguish the deterministic dataset-preflight report from the external Colab-run evidence.
- **Related requirements/phases:** P12, FR-ML-003, FR-ML-005, FR-ML-006, ADR-010, ADR-014.
- **Supersedes:** None.

## ADR-019 — Adopt the PR10-PR20 blueprint through compatibility reconciliation

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Project owner and Codex
- **Context:** The owner supplied a Colab-first PR10-PR20 blueprint after the repository had already merged P00-P11 and prepared/executed a controlled P12 experiment. The blueprint was intentionally drafted without repository visibility and proposes stronger data, split, calibration, locked-test and evidence-separation controls, but also uses logical PR numbers and taxonomies that do not match the implemented contracts.
- **Options considered:** Replace the repository plan verbatim; ignore the blueprint; adopt it as a lower-precedence reconciled roadmap while preserving correct work and requiring compatibility migrations for conflicts.
- **Decision:** Add the blueprint under `docs/plans`, include it in source precedence below the fixed scope/requirements/contracts, and use logical milestone numbering without rewriting Git history. Preserve existing stored-reference verification and technology choices. Audit every logical PR10-PR12 item as complete, partial, absent or conflicting before acquisition or additional full training.
- **Consequences:** The old master plan remains historical for completed phases. Missing PR10-PR12 foundations enter a dedicated reconciliation branch. Risk-band, image-label, endpoint and artifact-format changes are not effective until versioned compatibility work and tests exist. Full training remains Google Colab-only and locked tests remain unopened until their governed milestone.
- **Related requirements/phases:** Logical PR10-PR20, P10-P12, ADR-014, ADR-018, all analytical and data-governance requirements.
- **Supersedes:** The unreconciled P13-P20 sequencing in `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`; it does not supersede fixed product scope or completed phase evidence.

## ADR-020 — Additive evidence contracts and fail-closed Colab execution profiles

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Project owner and Codex within ADR-014/ADR-019
- **Context:** The reconciled blueprint requires explicit screenshot-only, transaction-only, combined and inconclusive modes; canonical manipulation/risk terms; null unavailable signals; and enforceable UNIT/SMOKE/FULL profiles. Existing API/database/artifact taxonomies cannot be replaced silently, and documentation alone did not prevent a local or CI caller from entering a training command.
- **Options considered:** Immediately replace persisted/public enums; keep policy only in prose; introduce an additive portable contract with explicit legacy projections and a fail-closed training guard.
- **Decision:** Adopt `evidence-result-v1` with canonical `unaltered`/`tampered` labels and low/medium/high/inconclusive risk bands while preserving existing enums through named compatibility functions. Unavailable signals must carry null scores/labels. Existing training CLIs require FULL mode, a deliberate acknowledgement token, detected Google Colab context and a non-CI runtime. UNIT and SMOKE cannot enter the existing reportable fitting paths.
- **Consequences:** Existing clients, records and failed P12 evidence remain unchanged. New dataset schemas must reject authenticity labels. Inconclusive cannot be projected into a fabricated legacy risk class. CI is pinned to UNIT and now registers the ML verification gate. A later migration must wire the new contract into orchestration/API/UI and implement the bounded restart-safe SMOKE workflow.
- **Related requirements/phases:** Logical PR10-PR12, FR-ML-003, FR-ML-005, FR-ML-006, FR-RISK-004, FR-RISK-005, NFR-AUD-001, ADR-014, ADR-018, ADR-019.
- **Supersedes:** None; this is an additive compatibility foundation.

## ADR-021 — Keep canonical data sources disabled until evidence is verified

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Project owner and Codex within the repository security/data rules
- **Context:** Logical PR11 must register public/simulator, external-image and owner-supplied Ghana-private sources before acquisition. A source name or public search result does not establish licence, redistribution rights, consent or suitability, and completed consent/private data cannot be committed.
- **Options considered:** Enable named sources from assumed public availability; defer the entire registry until files arrive; register every source now with explicit fail-closed evidence states.
- **Decision:** Register exactly PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private, but keep all disabled and `not_acquired`. Enabling requires approved permission, verified/not-applicable-private-consent status and registered acquisition state. FSTS stays optional. Ghana-private requires consent and defaults to internal-only. Committed fixtures must be demonstrably fictitious and participant-free; controlled-real records require pseudonymous participant linkage, consent scope and withdrawal checks.
- **Consequences:** Registry/schema/governance development and Colab foundations can proceed without inventing data rights or exposing personal data. Future acquisition must update the relevant card and evidence outside Git before enabling a source. Withdrawal and publication checks may require dataset/model rebuilds. This decision records no legal conclusion and grants no redistribution right.
- **Related requirements/phases:** Logical PR11, PR12, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-014, ADR-019, ADR-020.
- **Supersedes:** None.

## ADR-022 — Treat restart-safe smoke output as non-promotable infrastructure evidence

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Project owner and Codex within ADR-014/ADR-020/ADR-021
- **Context:** Logical PR12 needs a real end-to-end Colab smoke before expensive runs, while existing structured/image training commands are reportable FULL workflows and the historical P12 image artifact failed acceptance. Reusing those commands or their held-out tests for smoke would blur evidence boundaries and risk accidental promotion.
- **Options considered:** Let SMOKE call the existing reportable trainers; perform no fitting in smoke; implement a separately capped surrogate flow over fictitious train/validation fixtures with its own manifest and non-promotable bundle.
- **Decision:** SMOKE may fit only the dedicated PR12 surrogate under hard limits of 1,000 transaction rows, 20 synthetic images, one epoch and no locked-test access. It emits JSON-only infrastructure evidence with `acquisition_executed: false`, `full_training_executed: false` and `promotable: false`. Existing structured/image training CLIs continue to require acknowledged non-CI Google Colab FULL. Every session/checkpoint/artifact is hash-recorded and a lost runtime resumes under the same run ID only after verification.
- **Consequences:** Laptop/CI tests can prove deterministic orchestration and recovery without claiming model quality. The owner must still execute one fresh signed-in Colab smoke before logical PR12 completes. Smoke metrics/artifacts cannot be registered, cited as accuracy evidence or used to rehabilitate the failed P12 image artifact. Future reportable workflows reuse the manifest/checkpoint semantics but require governed data and separate acceptance evidence.
- **Related requirements/phases:** Logical PR12, FR-ML-005, FR-ML-006, NFR-AUD-001, NFR-DATA-001, ADR-014, ADR-018, ADR-020, ADR-021.
- **Supersedes:** None.
