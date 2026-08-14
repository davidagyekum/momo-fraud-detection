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

## ADR-023 — Require local-only registration after source-rights approval

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Project owner and Codex within ADR-014/ADR-019/ADR-021
- **Context:** Logical PR13 requires source acquisition and validation, but all six canonical registry entries remain disabled and `not_acquired`. Project-owner permission to automate collection does not establish third-party licence, access, redistribution, consent or authoritative version/schema evidence.
- **Options considered:** Add an automated network downloader now; open named sources based on assumed public availability; implement fail-closed local registration and wait for accountable source-specific approval.
- **Decision:** PR13 contains no network acquisition client. It first emits a metadata-only readiness report. Registration may inspect only an independently obtained local/private source under an explicitly approved root and only after the registry, permission/licence/consent state, canonical version and validation specification are ready. The caller must supply opaque reviewer/evidence references plus independently obtained expected hash and size. Any identity or validation failure produces a redacted quarantine manifest without mutating source bytes. All PR13 manifests remain non-promotable.
- **Consequences:** The registration and validation foundation can be tested without acquiring private or uncertain-rights data. Logical PR13 remains incomplete until at least the required sources are approved and their real bytes validate in owner-operated Colab. Registry approval is a separate reviewed change; a valid hash does not prove legality, representativeness or label quality.
- **Related requirements/phases:** Logical PR13, FR-ML-005, FR-ML-006, NFR-AUD-001, NFR-DATA-001, ADR-014, ADR-019, ADR-021, ADR-022.
- **Supersedes:** None.

## ADR-024 — Approve only the canonical PaySim Version 2 account-based acquisition path

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Project owner and Codex within ADR-021/ADR-023
- **Context:** PaySim is the first logical PR13 source with a ready structural validation specification. Its canonical Kaggle listing is published under PaySim author Edgar Lopez-Rojas, declares CC BY-SA 4.0, identifies Dataset Version 2 and one 493.53 MB CSV, and cites the 2016 PaySim paper. Kaggle's active Terms effective 2025-06-22 restrict service use and prohibit crawling/scraping while exposing an official signed-in Download action.
- **Options considered:** Keep PaySim blocked despite authoritative terms; download from a mirror or scrape Kaggle; approve a narrowly controlled official account-based acquisition path.
- **Decision:** Set PaySim permission to approved and licence to verified only for the project owner's internal personal non-commercial academic use of the canonical `ealaxi/paysim1` Version 2 download. Require the owner's own signed-in Kaggle account, official Download functionality, CC BY-SA attribution/change/ShareAlike compliance, private raw storage, exact post-download SHA-256/byte size and source-specific validation. Prohibit scraping, crawling, mirrors, version substitution, raw Git storage and provider/Ghana prevalence claims.
- **Consequences:** PaySim becomes the sole source eligible for local registration. It remains disabled, `not_acquired` and non-promotable until official bytes are obtained, hash-verified and validated. The other five source gates are unchanged. The review is an engineering governance determination, not legal advice.
- **Related requirements/phases:** Logical PR13, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-021, ADR-023.
- **Supersedes:** None.

## ADR-025 — Reconcile PaySim to 743 observed unique steps

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Codex within ADR-023/ADR-024 and the measured fail-closed registration evidence
- **Context:** The first owner-operated Colab registration of the exact approved PaySim Version 2 archive matched its SHA-256, byte size, member identity, 6,362,620 rows, 8,213 positives, schema, labels, amounts, null count and duplicate count, but quarantined because the blueprint-derived validation specification expected 744 unique steps. The validator measured 743. An independent aggregate-only pass over the same hash-verified local archive measured the complete contiguous range 1 through 743 with no missing values.
- **Options considered:** Accept the quarantined archive despite the mismatch; seek a different archive or mirror; correct the non-authoritative count assumption and rerun the same fail-closed registration.
- **Decision:** Keep the archive identity fixed and change only `expected_step_count` from 744 to 743. Preserve the first quarantine manifest as audit evidence and require a fresh owner-operated Colab registration at a new immutable code commit. Do not weaken any other identity, schema, count, class, duplicate, null or invalid-value check.
- **Consequences:** This is a metadata correction, not dataset substitution or a bypass. PaySim remains disabled and non-promotable until the corrected registration produces `status: registered`. The lower-precedence blueprint's approximate 744-step statement is recorded as reconciled rather than silently changed.
- **Related requirements/phases:** Logical PR13, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-019, ADR-023, ADR-024.
- **Supersedes:** Only the PaySim unique-step expectation derived from the logical PR13 blueprint; no fixed product/API/database contract changes.

## ADR-026 — Approve only official Mendeley MoMTSim DOI versions

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Codex within ADR-021/ADR-023 and authoritative CC BY 4.0 metadata
- **Context:** Logical PR13 requires MoMTSim v1 and v2 as separate structured sources. Mendeley Data publishes immutable DOI versions `10.17632/zhj366m53p.1` and `.2`, both under CC BY 4.0, while the linked peer-reviewed data article publishes the common raw schema and exact row/class counts. The version-2 page lists two CSV files, but displayed sizes alone do not prove their version mapping or exact byte identity.
- **Options considered:** Keep rights unverified; accept a mirror or infer versions from filenames/sizes; approve official Mendeley acquisition while retaining an exact-file identity gate.
- **Decision:** Approve permission and verify CC BY 4.0 only for official Mendeley DOI downloads for the recorded academic purpose. Keep v1 and v2 disabled and `not_acquired`; do not register either until exact official file mapping, byte size, SHA-256, encoding/header and measured aggregate profile are recorded separately. Treat the published `nbSteps=720` as a simulator parameter, not an observed unique-step assertion.
- **Consequences:** Rights and published-schema blockers are resolved without opening bytes. Acquisition/registration remains blocked on exact official file identity. Attribution, licence link and change indication are mandatory; mirrors, version substitution, raw Git/public serving, merged-population claims and Ghana/provider prevalence claims remain prohibited.
- **Related requirements/phases:** Logical PR13, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-019, ADR-021, ADR-023.
- **Supersedes:** None.

## ADR-027 — Preserve the official MoMTSim v2 duplicate-row quarantine

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Codex within ADR-023/ADR-026 and the measured fail-closed registration evidence
- **Context:** The official version-2 CSV matched its DOI package identity, SHA-256, byte size, UTF-8 header, 4,225,958 rows, 2,233,118 positives and 193 observed distinct steps, with no null, invalid-label or invalid-amount values. The strict validator found 20 exact duplicate rows and therefore produced `status: quarantined`. Version 1 passed the same validator with zero duplicates.
- **Options considered:** Weaken the validator; silently delete the 20 rows and call the official source registered; preserve the immutable quarantine and require a separately reviewed deterministic derived-dataset policy.
- **Decision:** Preserve the official v2 source and quarantine manifest unchanged. Keep v2 disabled and non-promotable. Do not delete, rewrite or merge source rows. Any future deduplicated candidate must be a content-addressed derived dataset with an explicit transformation manifest, duplicate-group audit counts, source-group-first split rules and independent validation before the registry can change.
- **Consequences:** MoMTSim v1 may proceed to later governed split design, but v2 cannot be used for splitting, fitting, evaluation or promotion. The 20 duplicate rows are a data-quality finding, not permission to bypass the acquisition gate. No raw duplicate values or identifiers are committed.
- **Related requirements/phases:** Logical PR13-PR14, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-019, ADR-023, ADR-026.
- **Supersedes:** None.

## ADR-028 — Register a separately versioned deterministic MoMTSim v2 derivative

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Codex within ADR-023/ADR-026/ADR-027 and the measured derivation/registration evidence
- **Context:** The immutable official MoMTSim v2 CSV is quarantined because it contains 20 exact duplicate rows. Aggregate-only analysis found 20 duplicate groups, each of size two; all 20 removable duplicate occurrences were negative-label rows. The official file otherwise matched its approved identity and validation specification.
- **Options considered:** Weaken the duplicate validator; modify the official source in place; exclude v2 permanently; create a separately versioned, content-addressed first-occurrence derivative and validate it independently.
- **Decision:** Preserve the official source and quarantine unchanged. Create version `2-derived-exact-dedup-v1` by retaining the first byte-identical row occurrence in original source order and omitting later exact occurrences. Require an immutable transformation manifest containing source/output hashes and sizes, row/class deltas, duplicate-group counts, policy/version, code/contract hashes and explicit false flags for network acquisition, splitting, training and promotion. Register the derivative only through the existing full validator under its own expected identity.
- **Consequences:** The derivative contains 4,225,938 rows, retains all 2,233,118 positives, has zero exact duplicates and is registered under output SHA-256 `642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd`. It remains disabled and non-promotable. Registration does not authorize PR14 splits or FULL training, and future source-group-first split design must treat the source and derivative as the same lineage. Raw source/derived bytes and private requests remain outside Git.
- **Related requirements/phases:** Logical PR13-PR14, NFR-AUD-001, NFR-DATA-001, FR-ML-005, FR-ML-006, ADR-019, ADR-023, ADR-026, ADR-027.
- **Supersedes:** None; implements the separately reviewed derivation path required by ADR-027.

## ADR-029 — Follow STFD's stricter access notice and freeze metadata only

- **Status:** Accepted
- **Date:** 2026-08-11
- **Decision owners:** Codex within ADR-021/ADR-023 and the current authoritative STFD sources
- **Context:** Hugging Face `Zegkim/STFD` is public/ungated and labels the dataset CC BY 4.0, while its current card restricts use to academic research, requests an extraction-password application from an academic/institutional email and asks users not to redistribute images. The official STFL-Net repository separately published an extraction password on 2026-03-06. The public card documents five tampering directories and same-filename binary masks but not a leakage-safe source-lineage grouping key.
- **Options considered:** Treat the public password as sufficient permission and download immediately; keep every STFD fact unverified; freeze exact public metadata while following the stricter access notice and retaining fail-closed acquisition/grouping gates.
- **Decision:** Record Hugging Face revision `9edebed2109052a77e9a5581c2ea7ce33d685da0`, archive size 2,941,753,426 bytes and LFS SHA-256 `6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c`. Treat the academic/no-redistribution conditions as the effective licence scope, but keep permission `access_request_required` until the project owner receives written approval through the dataset card's stated channel. Do not download/open the archive or form splits until an authoritative or conservatively reviewed lineage grouping rule exists.
- **Consequences:** STFD remains `not_acquired`, disabled and non-promotable even though its exact public archive identity and image/mask pairing are now known. A public password is not stored or treated as project-specific approval. Filename-level random splits are prohibited. The repository can validate future archive identity without exposing protected bytes.
- **Related requirements/phases:** Logical PR13-PR15, NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006, ADR-019, ADR-021, ADR-023.
- **Supersedes:** The blueprint's now-stale implication that STFD's archive identity/layout were wholly unknown; it does not supersede the written-access requirement.

**2026-08-11 implementation addendum:** The project owner explicitly attested that STFD permission has been obtained. Only opaque reference `OWNER_ATTESTATION_STFD_20260811` is committed; no access email, password or personal details are recorded. Permission may move to approved, but ADR-029's archive-identity, private-storage, no-redistribution and lineage-grouping gates remain unchanged.

The exact pinned archive was subsequently acquired into restricted private storage and matched both its 2,941,753,426-byte LFS size and SHA-256. A central-directory-only review passed path/member/declared-size caps and found 3,932 complete image/mask pairs. Because every file payload is encrypted and public metadata still lacks source lineage, the registry advances only to `acquired_pending_registration`; decoding, splitting and training remain prohibited.

## ADR-030 — Register STFD as one train-only external corpus with derived soft-mask thresholding

- **Date:** 2026-08-11
- **Status:** Accepted
- **Decision owners:** Codex/data steward within ADR-021, ADR-023 and ADR-029
- **Context:** Private extraction and complete validation found 3,932 decodable same-name image/mask pairs, zero missing/orphan/dimension/decode/exact-duplicate failures and no public lineage key. Three otherwise valid masks contain 12,860 antialiased rendered pixels across removal, insertion and replacement categories. An initial validator run quarantined the source because one category name also appeared as an empty nested directory; the role-aware fix requires exactly one category directory containing both `tamper` and `masks`, and the initial quarantine remains preserved.
- **Options considered:** Infer independent groups from opaque filenames; randomly split images; exclude the entire source; preserve one corpus-level group and use STFD only for external pretraining; rewrite the three source masks; preserve sources and threshold only derived tensors.
- **Decision:** Register exact extracted inventory `1087bbc4ba2cd349f08e2a0a4c4ebbc78c209d603d625c2a5344c0ff50f220dc` but keep it disabled/non-promotable. Treat every STFD record as one `single_external_pretraining_corpus_group`, assign it only to the future external-pretraining train role and prohibit internal STFD validation/test metrics. Preserve all source masks byte-for-byte. A derived training adapter may convert rendered luminance to binary at threshold 128; the validation contract freezes exactly three soft masks and 12,860 soft pixels so upstream drift fails closed.
- **Consequences:** PR14 cannot scatter STFD filenames or categories across partitions. Model selection, calibration and final evaluation must use independently grouped non-STFD data. Any claim based on STFD alone is limited to external pretraining, not Ghana/provider accuracy. The initial quarantine and final private registration artifacts remain content-addressed outside Git; only sanitized aggregate evidence is committed.
- **Related requirements/phases:** Logical PR13-PR17, NFR-DATA-001, NFR-AUD-001, FR-ML-005, FR-ML-006, ADR-019, ADR-021, ADR-023, ADR-029.
- **Supersedes:** ADR-029's temporary `acquired_pending_registration` state after its decoded-validation and conservative-grouping gates passed; ADR-029's access, no-redistribution and private-storage rules remain in force.

## ADR-031 — Freeze source-specific temporal partitions and strictly-prior transaction history

- **Date:** 2026-08-11
- **Status:** Accepted
- **Decision owners:** Codex/data steward under the logical PR14 blueprint
- **Context:** PaySim and the two registered MoMTSim candidates contain ordered simulation steps and raw actor identifiers needed transiently for history. Random row splits, same-step row ordering, balance/tutorial fields, pooled source identity or preprocessing fitted on later partitions would leak information or produce an inference-incompatible model. Locked-test labels must exist for one-time PR20 evaluation without becoming available to PR15 model selection.
- **Decision:** Map each registered source separately, derive stable row IDs from dataset ID, registered source hash and one-based source position, and split sorted unique steps chronologically into 70% train, 10% tuning, 10% calibration and 10% locked test. Minimally adjust boundaries to supply at least 100 positives in each non-train partition where feasible. Compute history from strictly earlier steps only; all rows sharing a step observe the same pre-step state. Keep features, labels and opaque provenance in separate content-hashed Parquet shards. Fit numeric neutral values and categorical vocabulary on train only, then reuse without refit. Reject locked-test loading before PR20. Preserve each dataset as a separate experiment and keep STFD as ADR-030's one-corpus train-only assignment.
- **Consequences:** Raw actor IDs may exist only transiently in restricted preprocessing memory and never become model columns or public evidence. Same-step ordering and future insertion cannot change earlier features. Full frozen manifests remain private and immutable after creation; Git may store only sanitized aggregate evidence/hashes. PR15 cannot train from an ad hoc table and cannot start until all required PR14 Colab bundles pass review.
- **Related requirements/phases:** Logical PR14-PR15 and PR20, NFR-DATA-001, NFR-AUD-001, NFR-MNT-001, FR-ML-005, FR-ML-006, ADR-019, ADR-030.

## ADR-032 — Keep PR15 binary transaction risk source-specific and non-breaking

- **Date:** 2026-08-11
- **Status:** Accepted
- **Decision owners:** Codex/model steward under the fixed product taxonomy and logical PR15 blueprint
- **Context:** The reconciled PR15 blueprint calls for a calibrated binary `transaction_core` fraud score and additive low/medium/high risk bands, while the higher-precedence product contract retains `GENUINE`/`SUSPICIOUS`/`FRAUDULENT` and the existing structured-model probability-vector interface. PaySim and MoMTSim have synthetic, materially different class prevalences, so pooled calibration or presentation as a Ghanaian real-world fraud probability would be misleading. The PR14 calibration partition must support both probability calibration and threshold selection without leaking into the locked final partition.
- **Decision:** Train separate binary candidates per registered source. Rank candidate configurations on tuning average precision first, then the documented recall/FPR operating constraint, calibration, stability and operational properties. Split each chronological calibration partition into an earlier calibrator-fit half and later calibrator/threshold-selection half; compare sigmoid and sufficiently supported isotonic calibration there. Select medium risk by maximum F2 under the configured FPR cap and high risk by the lowest threshold meeting the configured precision target, with an explicit fallback record. Export `p_fraud`, thresholds, additive risk band and a label-only compatibility projection (`low_risk→GENUINE`, `medium_risk→SUSPICIOUS`, `high_risk→FRAUDULENT`). Do not fabricate a three-class probability vector from the binary score. Keep every PR15 bundle `EXPERIMENTAL_NOT_FINAL_EVALUATED`, inactive, non-promotable and marked `not_real_world_probability` until PR19 implements a reviewed versioned integration and PR20 opens locked tests once.
- **Consequences:** PR15 can follow the stronger calibration discipline without silently breaking the fixed public taxonomy. Existing clients and persisted three-class evidence are unchanged. Source-specific bundle identity, PR14 preprocessor/split hashes, selected seed/configuration, calibration method and thresholds remain reconstructable. Cross-source results are research/domain-shift evidence only; no source calibration transfers automatically. The product must return an explicit unavailable/partial state rather than substitute this binary artifact where a compatible public probability vector is mandatory.
- **Related requirements/phases:** Logical PR15, PR19 and PR20; FR-ML-001, FR-ML-002, FR-ML-005, FR-ML-006, NFR-AUD-001; ADR-019 and ADR-031.
- **Supersedes:** None; this is the required compatibility decision before implementing the blueprint's binary transaction candidate.

## ADR-033 — Admit friend screenshots as an internal non-training permission-attested pilot

- **Date:** 2026-08-13
- **Status:** Accepted
- **Decision owners:** Project owner and Codex/data steward under the logical PR16 blueprint
- **Context:** The project owner supplied ten screenshots received from friends and explicitly attested that permission to use them was obtained. The files contain direct identifiers, one exact duplicate and one related-variant family. Direct contributor consent artifacts, contributor-to-file identity mapping and public-release permission were not supplied.
- **Decision:** Record the ten files outside Git as project-owner-attested friend permission, internal-only, with pseudonymous permission/participant references, controlled-derivative permission, public release false and training eligibility false. Use conservative file/source groups, keep the known related variants together, quarantine exact/perceptual duplicates and write no ML working copy until de-identification is reviewed. Treat the six earlier internet downloads separately as rights-review-only candidates. Do not freeze splits or train until consent/provenance, de-identification and independent content review gates pass.
- **Consequences:** PR16 can validate its real private-data pipeline without claiming direct signed consent, publication rights, representative coverage, final labels or model readiness. Withdrawal can be propagated through the private index, but contributor mapping should be refined if direct forms become available. The owner-attested status cannot silently become release-approved or training-eligible.
- **Related requirements/phases:** Logical PR16-PR20, NFR-DATA-001, NFR-PRIV-001, NFR-AUD-001, ADR-019, ADR-021.
- **Supersedes:** None.

**2026-08-13 online-candidate addendum:** The project owner attested that site permission for internal model development covers exactly `images1.jpg` through `images5.jpg`; it does not cover `images6.jpg`. Only an opaque permission reference is retained. Permission does not prove a fraud label and does not bypass de-identification, independent review or split gates. Private triage found images 1, 2 and 4 strong primary-fraud candidates, image 3 ambiguous, and images 5-6 mixed-authenticity threads. All six remain non-training; image 6 also remains rights-blocked.

**2026-08-13 de-identification addendum:** Deterministic solid-region masking and metadata stripping produced nine unique friend and five permitted-online working copies after repeated visual privacy checks. Privacy-safe annotations preserve sender kind and categorical fraud indicators without raw names, phone numbers, references or sensitive genuine balances. Ten records are provisional fraud candidates, one is a provisional genuine candidate, two are ambiguous and one is mixed. All fourteen remain non-training pending an independent second privacy/label review; no split was frozen.

**2026-08-13 second-review addendum:** The project owner approved the ten fraud candidates and the friend-supplied genuine candidate, excluded both ambiguous records, and approved splitting the mixed online image into separately redacted suspicious and genuine crops. The two crops inherit the source permission and one common `source_group_id`; identifiers, amounts, names, tokens, references and the URL are masked. The resulting label-level outcome is ten `FRAUDULENT`, two `GENUINE` and one `SUSPICIOUS` records, preserving the fixed product taxonomy. This approval does not amend the internal-only rights scope or bypass de-identified transcription, field annotation, mask-quality review, minimum independent-group/class balance, split freezing or Colab-only training gates. Training eligibility therefore remains false and no split or model run exists.

**2026-08-13 private-QA addendum:** De-identified transcripts, field-presence annotations, capture metadata and independent mask reviews were recorded outside Git for all 13 label-approved derivatives. Twelve records across ten immutable source groups passed privacy and utility QA; one remains label-approved but was rejected because safe masking removes too much evidence. A visual audit found residual ICC profiles in friend PNGs, so all nine were deterministically regenerated with unchanged pixels and empty metadata. Split freezing now fails closed unless records are explicitly training eligible and the pilot contains at least 30 controlled-real plus 20 synthetic-clean groups. The current class mix (nine `FRAUDULENT`, two `GENUINE`, one `SUSPICIOUS` QA passes) is insufficient, so no record was enabled, no split was frozen and no training occurred.

**2026-08-13 OCR text-corpus addendum:** Pixel masking was rejected as the training representation because even field-guided boxes can obscure adjacent labels and fraud-language cues. Each of the 13 approved screenshots is now retained privately only as immutable OCR evidence; exact, human-corrected transcripts and field annotations are exported to a raw private CSV. A paired de-identified CSV replaces exact names, phones, references, amounts, balances, URLs and other declared sensitive values with typed placeholders while preserving all remaining wording, spelling errors, sender context and ordering. Earlier masked derivatives remain historical privacy-QA artifacts but are excluded from training. Both CSV layers stay outside Git, all rows require independent text review and remain `training_eligible=false`, and no split or training occurred.

**2026-08-14 owner-message addendum:** The exact owner iMazing source identity and its 2,654 indexed incoming `MobileMoney` SMS rows were reverified before export. Raw messages remain in a private CSV; the review corpus replaces detected counterparties and direct values in text, collapses exact de-identified duplicates to 230 rows and assigns 167 template-family groups. Template grouping prevents identical formats from crossing future partitions, but it does not create independent participants: the entire corpus remains one owner lineage and may not be scattered across evaluation partitions. All rows require second review and stay `training_eligible=false`; no split or training occurred.

**2026-08-14 privacy-review correction:** A complete manual pass invalidated the earlier aggregate-only conclusion: unusual greeting/reference formats retained three owner-name occurrences, one login-code format bypassed the first secret rule, and sequential OCR substitutions corrupted one row's typed placeholders. The sanitizer now handles those contexts, quarantines 26 secret-bearing messages, and performs OCR replacements against original text in one pass. The regenerated owner corpus contains 2,628 raw retained rows, 116 distinct de-identified texts and 90 template families; the corrected screenshot corpus contains 13 well-formed de-identified rows. Independent second review approves all 129 corrected real-text rows, but approval does not enable training. A separate deterministic synthetic-clean pilot contains 30 groups/90 wholly fictitious rows balanced across the fixed three-class taxonomy. It remains pending second review and non-training. The prior 230-row/167-group figures are superseded, no split is frozen and no model training occurred.

**2026-08-14 Android owner-account addendum:** The two SMS Backup & Restore XML files are not independent datasets: the 342-row `MobileMoney` export is an exact subset of the 882-row phone export. A bounded, declaration-rejecting XML normalizer now admits only the explicitly approved `MobileMoney`, `T Cash`, `T-CASH` and `Telecel` incoming sender labels, maps them to MTN/Telecel provider families, removes exact overlaps and never writes unapproved conversation content. The private run retained 690 unique messages (342 MTN, 348 Telecel), ignored 192 unrelated rows and quarantined four security-code messages. Full text review added GHC/four-decimal and exact timestamp placeholders before approving 159 distinct Android texts. The first iPhone corpus was regenerated under the same rule and now contains 106 distinct texts. The combined review manifest approves 278 real de-identified rows. All accounts belong to one owner: provider/account/template diversity may strengthen train-only coverage but must not be represented as independent-person evaluation evidence. Additional online collection therefore prioritises distinct fraudulent/suspicious source groups, not more genuine scraping. No training eligibility, split or model run was created.

**2026-08-14 suspicious-image batch addendum:** Eleven later owner-supplied images are exact-unique and have no perceptual match within the locked Hamming-distance-six threshold. Conservative visual triage identifies seven primary Ghana MoMo fraud candidates, two adjacent Ugandan mobile-money phishing examples and two cash-in screenshots whose authenticity requires adjudication. Every image contains visible direct identifiers. Because filenames alone do not establish an original source page, permission scope or independent participant/source lineage, all 11 remain in rights-review-only private quarantine with `training_eligible=false`; they add zero controlled-real groups and receive no derivative, OCR export, split assignment or label approval. This preserves the owner's collection effort without converting an uncertain licence or source claim into training evidence.

**2026-08-14 permission/text-review correction:** The project owner subsequently grants internal model-development permission for exactly the 11-image batch. Permission does not establish original web lineage, so all 11 retain one conservative source group. OCR-first review avoids creating masked image derivatives: seven primary Ghana fraud screenshots receive exact private OCR truth and typed-placeholder de-identification; two Ugandan examples are excluded as out-of-domain and two normal-looking cash-in screenshots are excluded because authenticity cannot be established. The approved screenshot text layer now contains 20 rows across 12 controlled-real groups. The original synthetic-clean pilot is also rejected because 39 exact texts cross nominal groups and `Payment made` genuine wording uses the wrong preposition. A corrected v3 generator creates 90 unique, balanced, grammatically consistent records across 30 groups, all independently reviewed. The combined reviewed artifact contains 375 non-training rows. A content-hash-bound readiness report passes the 30-group synthetic minimum but fails the 30-group controlled-real minimum at 12 groups; therefore no eligibility decision, split or Colab training may occur.

**2026-08-14 unmapped-friend-batch addendum:** The project owner attests internal-development permission from 19 friends for a 24-file submission, but the friend-to-file mapping cannot be reconstructed. Two files are exact duplicates of previously registered fraudulent screenshots; visual and independent text review classifies all 22 newly unique screenshots as genuine. To prevent participant leakage, the 22 new records are assigned one conservative partitionable source group rather than 19 inferred groups. Three visually near-duplicate templates remain quarantined for image-model use while their distinct, manually verified text is retained with coarse full-image localization explicitly distinguished from field-localization ground truth. The reviewed corpus grows to 397 rows and controlled-real readiness to only 13/30 groups. The lost mapping cannot be repaired through arbitrary file assignment; at least 17 additional traceable source groups remain required before eligibility or split freezing.

## ADR-034 — Freeze the permission-mapped private text pilot while declaring sparse suspicious coverage

- **Date:** 2026-08-14
- **Status:** Accepted
- **Decision owners:** Project owner and Codex/data steward under the logical PR16 blueprint
- **Context:** The owner supplied 21 additional fraudulent-message screenshots, one per numbered friend folder, and attested permission from 21 distinct friends. The folder boundary preserves participant/source mapping. All files are exact-unique; one is perceptually similar to a prior screenshot at the locked distance-six threshold but contains distinct text. Combined review reaches 34 controlled-real groups, exceeding the pilot minimum of 30, but controlled-real labels are highly asymmetric: 31 groups contain fraud, three contain genuine and only one contains suspicious content. Owner SMS templates remain one participant lineage and cannot become independent evaluation groups.
- **Decision:** Admit the 21 records for OCR-first text review with separate pseudonymous participant and source-group identities, internal-only scope, coarse full-image OCR localization and no image derivative. Retain the cross-batch perceptual match for distinct text only. Freeze source groups with seed `20260814`: controlled-real at approximately 70/15/15, synthetic-clean at 80/20/0 and all owner records train-only. Require each controlled class to appear in every split only when at least three independent groups carry that class. Keep the test controlled-real only and inaccessible to the development loader. Preserve two earlier private split attempts as superseded audit evidence after they exposed avoidable test-class/record-skew problems; private version 3 is authoritative.
- **Consequences:** The authoritative manifest contains 418 assignments: 362 train, 51 validation and five locked test. The five test records are four fraudulent and one genuine across five independent controlled-real groups. Suspicious controlled-real evidence appears only in train because its single group cannot be split without leakage; synthetic suspicious records support validation but do not substitute for controlled-real final evidence. PR17 may use only train/validation after explicit owner confirmation. No PR17/PR18 Colab work, locked-test access, model fit or metric has occurred. Image-model use remains separately blocked because these OCR-first originals have no approved image derivatives.
- **Related requirements/phases:** Logical PR16-PR18 and PR20; NFR-DATA-001, NFR-PRIV-001, NFR-AUD-001, ADR-019, ADR-021, ADR-033.
- **Supersedes:** The PR16 unmapped-friend addendum's 17-group readiness blocker. It does not supersede the internal-only rights boundary, participant grouping, locked-test rule or image-derivative exclusion.

## ADR-035 — Bind PR17 OCR benchmarking to a development-only private image bundle

- **Date:** 2026-08-14
- **Status:** Accepted
- **Decision owners:** Codex/model steward under the logical PR17 blueprint and ADR-034
- **Context:** The authoritative private text split contains 63 screenshot OCR truths: 25 train, 33 validation and five locked controlled-real test records. PR17 requires a reproducible comparison of pretrained Tesseract 5, EasyOCR and PaddleOCR plus a conservative Ghana MoMo parser, but raw images and exact OCR truth must remain outside Git and the locked test must be inaccessible to model selection. Most source images have no separately approved training derivative, while two approved mixed-thread crops have governed hashes. No approved tampered-image derivative slice exists.
- **Decision:** Materialise a private, content-addressed development bundle only from explicit PR16 train/validation bindings. Verify every source or governed-derivative image hash and truth identity, reject unknown/test bindings, and omit all locked-test bytes from the archive. Benchmark required engines on CPU in Google Colab using deterministic preprocessing, a three-source-group screening pass and then the full 33-record clean validation set. Record the exact runtime engine versions and explicit incompatibilities. Select only from validation using the versioned weighted CER/WER/field/latency contract; keep a selected bundle `experimental` unless every configured gate passes. Preserve raw OCR, parsed values and images privately; repository evidence contains only hashes, safe counts and redacted failure categories. Treat the missing tampered slice as an explicit blocker rather than fabricate robustness metrics.
- **Consequences:** PR17 preparation is reproducible without exposing private values or the five locked records. No benchmark metric, engine winner, validated bundle or production OCR claim exists until the pinned Colab notebook completes. Tesseract's exact installed version is measured at runtime rather than inferred from the notebook. PR19 may consume only a compatible content-verified bundle and must preserve an explicit unavailable/experimental state if PR17 gates do not pass.
- **Related requirements/phases:** Logical PR17, PR19 and PR20; FR-OCR-001, FR-OCR-002, FR-OCR-003, NFR-ACC-001, NFR-PRIV-001, NFR-AUD-001, NFR-DATA-001, ADR-014, ADR-019, ADR-034.
- **Supersedes:** None; it implements ADR-034's train/validation-only PR17 boundary and preserves the locked-test and image-derivative exclusions.

**2026-08-14 dependency-repair addendum:** The first owner-operated PR17 Colab attempt failed during pip resolution before engine initialisation or private bundle extraction. Official package metadata establishes the conflict: PaddleOCR 3.7.0 requires PaddleX 3.7.x, whose base requirement is NumPy `>=1.24,<2.4`, while the shared runtime lock pinned NumPy 2.5.2. Pin NumPy 2.3.5, preserve all other direct OCR pins, and enforce the PaddleOCR/NumPy interval in the executable Colab lock contract. This failed attempt contains no benchmark metric, data access, training, selection or locked-test evidence.

**2026-08-14 portable-archive addendum:** The repaired Colab environment initialized all 15 declared OCR configurations with no adapter failure, then failed before the first screen-record image could be opened. The private ZIP had been created on Windows with backslashes in all 117 archive member names, while `development-manifest.json` correctly declared POSIX paths. Linux extraction therefore created literal backslash filenames. Package private development bundles only through the deterministic repository packager, which verifies private-path confinement, manifest lock state, member hashes, duplicates and POSIX paths before writing sorted fixed-metadata ZIP entries. Colab must reject any archive containing a backslash rather than normalize only its safety check. The portable archive preserves the same 58 development records and excludes all five locked-test records. This failed attempt accessed the development manifest but no private image bytes, completed no benchmark row, trained nothing and produced no metric or selection.

**2026-08-14 runtime-restart addendum:** A subsequent fresh Colab pass installed the pinned environment, then failed during the first repository import because new Pillow files and an older already-imported `PIL._typing` coexisted in the live kernel. Treat in-process replacement of an imported critical distribution as requiring a runtime restart. Before pip, capture critical distribution versions and loaded module names using only the standard library. After pip, probe Pillow, NumPy, OpenCV, pandas and scikit-learn in both the current kernel and a clean child process. Fail before private archive access if the child process is inconsistent; otherwise require one explicit session restart whenever an imported distribution changed or the current process is inconsistent. The next full pass may proceed only when versions are unchanged and both probes pass. This attempt initialized no OCR engine, accessed no private archive or locked test and produced no benchmark row, metric, training or selection.
