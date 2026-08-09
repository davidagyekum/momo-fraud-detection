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
