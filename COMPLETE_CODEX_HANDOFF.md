> Historical execution notice: this document is preserved for context/evidence.
> It must not select the current task. Read `FINAL_COMPLETION_OVERRIDE.md` and
> `IMPLEMENTATION_STATUS.md` first.

# Complete Codex Handoff — MoMo-FDVS

This consolidated file mirrors the modular implementation package. The modular files remain the preferred source because Codex can read only the specifications relevant to the current phase.

## Contents

1. MoMo-FDVS Codex Implementation Package — `README_FIRST.md`
2. AGENTS.md — Mandatory Codex Instructions — `AGENTS.md`
3. 00 — Source of Truth and Scope Freeze — `00_SOURCE_OF_TRUTH_AND_SCOPE.md`
4. 01 — Codex Master Implementation Plan — `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`
5. 02 — System Requirements Specification — `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md`
6. 03 — Architecture and Repository Specification — `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md`
7. 04 — Database and Private Storage Specification — `04_DATABASE_AND_STORAGE_SPEC.md`
8. 05 — REST API Contract — `05_API_CONTRACT.md`
9. 06 — UI/UX Implementation Specification — `06_UI_UX_IMPLEMENTATION_SPEC.md`
10. 07 — OCR, Image Analysis, Machine Learning and Verification Specification — `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md`
11. 08 — Security, Privacy and Audit Specification — `08_SECURITY_PRIVACY_AUDIT_SPEC.md`
12. 09 — Testing, QA and Release Plan — `09_TESTING_QA_RELEASE_PLAN.md`
13. 10 — GitHub Workflow and Codex Session Protocol — `10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md`
14. 11 — Deployment and Operations Runbook — `11_DEPLOYMENT_RUNBOOK.md`
15. 12 — Final Independent Inspection Protocol — `12_FINAL_INSPECTION_PROTOCOL.md`
16. 13 — Documentation and Chapter Four Evidence Plan — `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`
17. IMPLEMENTATION_STATUS.md — `IMPLEMENTATION_STATUS.md`
18. DECISION_LOG.md — `DECISION_LOG.md`
19. CHANGELOG.md — `CHANGELOG.md`

---

<!-- BEGIN FILE: README_FIRST.md -->

# MoMo-FDVS Codex Implementation Package

## Project

**Design and Implementation of an AI-Powered Mobile Money Fraud Detection and Verification System Using OCR, Image Analysis and Machine Learning**

This package is the implementation handoff for Codex. It turns the approved Chapter Three scope into an executable, testable and auditable software-development programme.

The target product contains:

- an Expo/React Native mobile application for Mobile Money users and merchants;
- a React web portal for administrators and fraud investigators;
- a Python/Flask REST API;
- PostgreSQL for relational data and audit history;
- private receipt-image storage;
- OpenCV and Tesseract for preprocessing, OCR and field extraction;
- image-forensics features and a TensorFlow/Keras tampering classifier;
- a scikit-learn structured fraud classifier;
- reference-record verification;
- explainable risk aggregation;
- transaction history, reports, notifications and a reasoned case-review workflow.

## Start here

1. Create or open the GitHub repository.
2. Copy this entire package into the repository root.
3. Keep `AGENTS.md`, `IMPLEMENTATION_STATUS.md`, `DECISION_LOG.md`, and `CHANGELOG.md` at the repository root.
4. Place the numbered specification files under `docs/implementation/` if desired; do not alter their content before the first Codex preflight.
5. Give Codex the contents of `prompts/START_CODEX_PROMPT.txt`.
6. Codex must complete one numbered phase at a time, run the required checks, update the status files, commit, and push.
7. At a later session, use `prompts/CONTINUE_CODEX_PROMPT.txt`.
8. After the final phase, Codex must complete `templates/FINAL_HANDOFF.md`. Provide the repository name, final branch or pull request, and exact commit SHA for independent inspection.

## Required reading order for Codex

1. `AGENTS.md`
2. `00_SOURCE_OF_TRUTH_AND_SCOPE.md`
3. `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`
4. `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md`
5. `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md`
6. `04_DATABASE_AND_STORAGE_SPEC.md`
7. `05_API_CONTRACT.md`
8. `06_UI_UX_IMPLEMENTATION_SPEC.md`
9. `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md`
10. `08_SECURITY_PRIVACY_AUDIT_SPEC.md`
11. `09_TESTING_QA_RELEASE_PLAN.md`
12. `10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md`
13. `11_DEPLOYMENT_RUNBOOK.md`
14. `12_FINAL_INSPECTION_PROTOCOL.md`
15. `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`
16. `IMPLEMENTATION_STATUS.md`
17. `DECISION_LOG.md`
18. `requirements_traceability.csv`
19. `backlog.csv`

## Non-negotiable product boundaries

- **Fraud risk and transaction verification are separate outputs.**
  - Fraud risk: `GENUINE`, `SUSPICIOUS`, or `FRAUDULENT`.
  - Verification status: `VERIFIED`, `UNVERIFIED`, or `MISMATCH`.
- The prototype must not claim direct confirmation from MTN, Telecel or AT Money unless a real, authorised integration is added and documented.
- The MVP verifies against stored or imported reference records.
- The system must never fabricate model metrics, test results, deployments, pushes or integrations.
- A missing or unavailable model must produce an explicit partial-analysis state, not a fabricated prediction.
- Raw real receipts, credentials, access tokens, model secrets and private datasets must never be committed to Git.
- Every high-risk result and reviewer action must be explainable and auditable.
- Reviewer decisions must not overwrite the original automated result.
- Chapter Three wireframes remain low-fidelity design artefacts; implemented interfaces and screenshots belong in Chapter Four.

## Inputs the project owner must eventually supply

The implementation can begin without these items, but production deployment or final evaluation may require them:

- preferred product name/logo and final visual identity;
- GitHub repository name and access;
- a private PostgreSQL connection string for staging/production;
- private object-storage credentials;
- authorised, anonymised receipt samples and labels;
- approved reference-transaction data or import files;
- email/push-provider credentials if external notifications are enabled;
- test user email addresses and deployment domains;
- supervisor-approved model evaluation dataset and reporting format.

Codex must create safe local substitutes, mock adapters and sample data when an external credential or private dataset is unavailable. It must record the limitation in `IMPLEMENTATION_STATUS.md` and `FINAL_HANDOFF.md`.

## Package contents

| File | Purpose |
|---|---|
| `AGENTS.md` | Mandatory Codex operating rules |
| `00_SOURCE_OF_TRUTH_AND_SCOPE.md` | Scope freeze and terminology |
| `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md` | End-to-end phased implementation plan |
| `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md` | Testable user, system and non-functional requirements |
| `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md` | Monorepo, modules and engineering conventions |
| `04_DATABASE_AND_STORAGE_SPEC.md` | PostgreSQL schema, constraints and file storage |
| `05_API_CONTRACT.md` | REST API contract and response conventions |
| `06_UI_UX_IMPLEMENTATION_SPEC.md` | Mobile and web screen-by-screen UI specification |
| `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md` | OCR, image, ML, verification and risk pipelines |
| `08_SECURITY_PRIVACY_AUDIT_SPEC.md` | Threat model and security controls |
| `09_TESTING_QA_RELEASE_PLAN.md` | Automated, manual, performance and release testing |
| `10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md` | Branch, commit, push, PR and handoff rules |
| `11_DEPLOYMENT_RUNBOOK.md` | Local, staging and production deployment |
| `12_FINAL_INSPECTION_PROTOCOL.md` | Independent audit and repair loop |
| `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md` | Evidence to capture for the final report |
| `IMPLEMENTATION_STATUS.md` | Persistent cross-session progress tracker |
| `DECISION_LOG.md` | Architecture decision record |
| `CHANGELOG.md` | Human-readable change history |
| `requirements_traceability.csv` | Requirement-to-code-to-test mapping |
| `backlog.csv` | Phase-by-phase implementation tasks |
| `templates/` | Handoff and pull-request templates |
| `prompts/` | Start, continue and audit-repair prompts |
| `samples/` | Safe import and dataset-manifest examples |
| `.env.example` | Environment-variable contract |

## Final handoff for independent inspection

After Codex reports completion, provide:

- GitHub repository in `owner/repository` form;
- final branch or pull-request number;
- exact final commit SHA;
- staging API and admin URLs, if deployed;
- a non-sensitive test-account plan;
- Codex's completed `FINAL_HANDOFF.md`;
- any known blocker involving unavailable credentials or datasets.

The final inspection will review the repository at the exact SHA, not an unspecified moving branch.

<!-- END FILE: README_FIRST.md -->


---

<!-- BEGIN FILE: AGENTS.md -->

# AGENTS.md — Mandatory Codex Instructions

These instructions apply to the entire repository. A more specific `AGENTS.md` in a subdirectory may add constraints but may not weaken these rules.

## 1. Mission

Implement the complete MoMo-FDVS product described in the implementation package. Deliver working, tested and documented software, not a UI-only prototype and not a collection of disconnected demonstrations.

## 2. Source-of-truth precedence

When requirements conflict, use this order:

1. `00_SOURCE_OF_TRUTH_AND_SCOPE.md`
2. `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md`
3. `05_API_CONTRACT.md`
4. `04_DATABASE_AND_STORAGE_SPEC.md`
5. `07_OCR_IMAGE_ML_VERIFICATION_SPEC.md`
6. `06_UI_UX_IMPLEMENTATION_SPEC.md`
7. `08_SECURITY_PRIVACY_AUDIT_SPEC.md`
8. `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`
9. `backlog.csv`
10. Existing implementation

Do not silently change the product scope or stack. Record a necessary deviation in `DECISION_LOG.md`, explain why, and keep backward-compatible behaviour where possible.

## 3. Fixed technology direction

- Mobile: Expo + React Native + TypeScript.
- Administrator/investigator portal: React + TypeScript + Vite.
- API: Python 3.12 + Flask application factory + blueprints.
- Persistence: PostgreSQL + SQLAlchemy + Alembic/Flask-Migrate.
- OCR/image processing: Tesseract + OpenCV + Pillow.
- ML: TensorFlow/Keras for image classification; scikit-learn for structured classification.
- Local orchestration: Docker Compose.
- Version control: Git and GitHub.

Do not replace Flask with FastAPI/Django, PostgreSQL with Firebase/MongoDB, React Native with Flutter, or the selected ML stack without explicit written approval.

## 4. Product invariants

1. Fraud risk and transaction verification are different fields, different UI blocks and different database records.
2. The prototype uses stored/imported reference transactions. It does not claim live MNO verification.
3. Automated outputs are immutable evidence. Human review adds a decision; it does not rewrite the model output.
4. Every prediction stores the model version, feature schema version, probability values, thresholds and reason codes.
5. Every receipt stores a cryptographic hash; duplicate and near-duplicate checks must be possible.
6. Every protected action enforces role and object ownership on the server.
7. Raw images are private and are never served by a public static path.
8. Real private data, `.env` files, tokens, credentials and large model/data artifacts are excluded from Git.
9. No model accuracy, F1 score, pass count, deployment or Git push may be claimed without actual evidence.
10. A missing model or integration must return an explicit degraded/partial state, never a fake success.

## 5. Work one phase at a time

Before coding:

1. Run repository preflight.
2. Read `IMPLEMENTATION_STATUS.md`.
3. Select the next incomplete phase whose prerequisites are complete.
4. Create or switch to the required phase branch.
5. Write a short plan in the session log or pull-request description.
6. Confirm that the intended work does not cross a documented scope boundary.

During coding:

- Keep commits coherent and reviewable.
- Add or update tests with each behaviour.
- Add migrations for every database change.
- Update API documentation and generated clients when contracts change.
- Keep accessibility, empty, loading, error and permission-denied states in scope.
- Preserve a clean separation between route/controller, service, repository, model and ML code.
- Do not leave commented-out production code, unexplained TODOs, hard-coded secrets or debug bypasses.

Before ending a session:

1. Run all phase-specific checks.
2. Run the repository verification command.
3. Inspect `git diff`, `git status` and migration state.
4. Update `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `DECISION_LOG.md` when applicable, and `CHANGELOG.md`.
5. Complete the session handoff using `templates/SESSION_HANDOFF.md`.
6. Commit with a conventional commit message.
7. Push the branch to GitHub.
8. Report the exact base SHA, head SHA, branch, test commands and results.
9. If push fails, state that it failed and preserve the local commit; do not say it was pushed.

## 6. Required branch and commit conventions

- Stable branch: `main`
- Integration branch when used: `develop`
- Phase branches: `codex/pNN-short-description`
- Repair branches: `codex/audit-fix-NN-short-description`

Conventional commit examples:

- `feat(auth): implement refresh-token rotation`
- `feat(ocr): add confidence-aware field parser`
- `fix(upload): reject polyglot and oversized files`
- `test(verification): cover amount and phone mismatches`
- `docs(handoff): record phase P07 verification evidence`

Never force-push shared branches. Never rewrite `main` history.

## 7. Quality gates

A phase is incomplete unless all applicable gates pass:

- formatting and linting;
- static typing;
- unit tests;
- integration/API tests;
- database migration upgrade from a clean database;
- database migration upgrade from the previous revision;
- frontend build;
- mobile type check and test suite;
- required end-to-end flow;
- security checks introduced for the phase;
- documentation and traceability update.

Waiving a gate requires a blocker entry with owner, impact, workaround and next action.

## 8. Security rules

- Treat uploaded receipts as hostile input.
- Validate extension, decoded image content, dimensions, file size and generated filename.
- Do not trust client-supplied MIME type or ownership identifiers.
- Never put secrets in mobile or browser bundles.
- Store mobile tokens only in secure device storage.
- Use secure, HTTP-only cookie-based refresh for the web portal where feasible.
- Enforce HTTPS outside local development.
- Apply rate limits to login, password reset, upload, analysis and export endpoints.
- Redact secrets, full tokens, password material and sensitive receipt values from logs.
- Use structured audit events for privileged and evidential actions.
- Use parameterised ORM operations; do not build raw SQL from untrusted values.

## 9. ML and data rules

- Split source groups before preprocessing, augmentation or feature fitting.
- Keep train, validation and test groups independent.
- Fit scalers/encoders only on training data, preferably inside an sklearn pipeline.
- Apply augmentation to training images only.
- Record dataset manifest hash, split seed and code commit for each training run.
- Use reproducible seeds where supported.
- Evaluate per class; macro F1 and confusion matrix are mandatory.
- Do not promote a model solely because overall accuracy is high.
- Load only trusted model artifacts and verify their stored hash.
- Do not commit private datasets or large model binaries. Use a documented artifact location and checksum.
- Clearly label results trained only on synthetic or controlled data.

## 10. UI rules

- Implement actual polished interfaces, but preserve Chapter Three's low-fidelity wireframes as design artefacts.
- Display risk class and verification status independently.
- Do not use colour as the only status signal.
- Every screen must have loading, empty, error, offline/retry and permission-denied states where relevant.
- Destructive and reviewer actions require confirmation.
- Investigator decisions require a reason.
- Do not expose raw internal probabilities without an understandable explanation.
- A user may only see their own transactions and reports.

## 11. Documentation rules

- Keep public API examples free of real credentials or personally identifiable information.
- Update schema and API docs when code changes.
- Capture evidence requested by `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`.
- Mermaid diagrams in the repository are useful engineering references, but final academic UML/ER diagrams must be exported cleanly with no crossing lines and must match the implemented system.

## 12. Stop and report rather than guess when

- a required private key, external account or production credential is missing;
- a dataset licence or consent status is uncertain;
- a migration could destroy data;
- an API contract change would break completed clients;
- model metrics cannot be reproduced;
- the requested action would expose private receipts or credentials;
- the repository state differs materially from the handoff;
- there are unrelated local modifications that could be overwritten.

Use a safe mock or adapter only when the specification permits it, document the substitution, and continue independent work.

<!-- END FILE: AGENTS.md -->


---

<!-- BEGIN FILE: 00_SOURCE_OF_TRUTH_AND_SCOPE.md -->

# 00 — Source of Truth and Scope Freeze

## 1. Product identity

**System name:** MoMo-FDVS  
**Full title:** Design and Implementation of an AI-Powered Mobile Money Fraud Detection and Verification System Using OCR, Image Analysis and Machine Learning

## 2. Problem statement

Mobile Money users and merchants may receive screenshots or digital receipts that have been edited, cropped, reused, fabricated or paired with transaction details that do not match a trusted reference record. Manual inspection is slow and inconsistent. MoMo-FDVS provides an evidence-based prototype that:

1. extracts transaction details from a receipt image;
2. analyses visual and structural signs of manipulation;
3. uses versioned machine-learning models and rules to estimate fraud risk;
4. compares extracted details with stored or imported reference transactions;
5. presents a separate fraud-risk result and verification result;
6. retains evidence, explanations, model versions and human review decisions.

The system is decision support. It is not a guarantee that a transaction is genuine, and it does not replace an authorised Mobile Network Operator investigation.

## 3. Actors and roles

### 3.1 User / Merchant (`USER`)

A Mobile Money user or merchant who can:

- register, log in, reset a password and manage a profile;
- capture or upload a receipt;
- inspect and correct low-confidence OCR fields;
- start analysis;
- view the result, evidence and history for their own submissions;
- download a summary;
- receive notifications;
- report a suspicious transaction for review.

### 3.2 System Administrator (`ADMIN`)

An authorised operator who can:

- manage users and roles;
- view system dashboards and operational status;
- manage supported receipt templates;
- manage fraud rules and thresholds;
- register and activate model versions;
- import authorised reference transactions;
- view audit information and operational reports.

An administrator does not automatically receive authority to make an investigation decision unless also assigned the investigator capability.

### 3.3 Fraud Investigation Officer (`INVESTIGATOR`)

An authorised reviewer who can:

- view assigned or queued cases;
- inspect the original receipt, OCR fields, image evidence, rules, model outputs and verification evidence;
- add notes;
- confirm, dismiss or escalate a case;
- provide a mandatory reason;
- generate a case report.

### 3.4 External/secondary services

- private object storage;
- PostgreSQL;
- optional notification delivery adapter;
- future MNO integration adapter, disabled in the prototype unless authorised.

## 4. Fixed output taxonomy

### 4.1 Fraud risk class

- `GENUINE`: available evidence suggests a low fraud risk.
- `SUSPICIOUS`: evidence is incomplete, conflicting or above the suspicious threshold.
- `FRAUDULENT`: evidence exceeds the calibrated fraud threshold.

The UI must state that these are automated risk assessments.

### 4.2 Verification status

- `VERIFIED`: a reference record was found and required fields matched within configured tolerances.
- `UNVERIFIED`: no usable reference record was available, or verification could not be completed.
- `MISMATCH`: a reference record was found but one or more critical fields did not match.

Verification status is not a synonym for fraud risk. A transaction can be `GENUINE + UNVERIFIED`, `SUSPICIOUS + VERIFIED`, or another valid combination.

### 4.3 Processing state

Recommended state machine:

`DRAFT -> UPLOADED -> OCR_READY -> OCR_REVIEWED -> QUEUED -> PROCESSING -> COMPLETED`

Exceptional terminal or recoverable states:

- `PARTIAL`: at least one analysis subsystem was unavailable; available evidence is preserved.
- `FAILED`: processing could not produce a usable result.
- `CANCELLED`: user/system cancelled before analysis completion.

State transitions must be validated on the server.

### 4.4 Case state

`OPEN -> IN_REVIEW -> CONFIRMED | DISMISSED | ESCALATED`

A terminal decision may be superseded only through an explicit, audited reopen procedure; never by directly editing the original row.

## 5. In-scope features

### Foundation

- monorepo and repeatable local environment;
- API, database migrations and private storage abstraction;
- mobile and web applications;
- role-based authentication and password reset;
- health, readiness and version endpoints;
- structured errors, logging and audit events.

### Receipt analysis

- camera/gallery receipt selection;
- upload validation and immutable original storage;
- SHA-256 and perceptual hashes;
- image quality checks;
- OCR preprocessing variants;
- Tesseract OCR with token/field confidence;
- extraction and normalisation of:
  - provider/network where detectable;
  - transaction/reference ID;
  - amount and currency;
  - sender/receiver names;
  - sender/receiver phone numbers;
  - date and time;
  - transaction status text;
- user correction of low-confidence fields;
- metadata, compression, noise, crop/layout, duplicate and text-alignment evidence;
- TensorFlow/Keras image tampering probability;
- scikit-learn structured fraud probability/class;
- versioned rules;
- risk aggregation and human-readable reason codes.

### Verification

- import authorised reference transaction files;
- validate, preview, commit and audit imports;
- reference matching by provider and transaction ID;
- field comparison with configurable tolerances;
- duplicate reference/reused receipt detection;
- `VERIFIED`, `UNVERIFIED` and `MISMATCH` output.

### User experience

- result summary and evidence detail;
- history, search and filters;
- downloadable analysis summary;
- in-app notifications;
- suspicious transaction reporting.

### Administration and investigation

- dashboard and queues;
- users/roles;
- template/rule/model registries;
- reference data imports;
- case review and reports;
- audit logs;
- system-status page.

### Testing and deployment

- automated unit, integration, contract and E2E tests;
- security and upload-abuse tests;
- model training/evaluation pipeline;
- Docker-based local environment;
- staging deployment configuration;
- release documentation and independent inspection.

## 6. Explicitly out of scope for the prototype

- claiming or displaying live confirmation from any MNO without a real authorised API;
- money transfer, wallet balance, reversal or payment initiation;
- automatic reporting to law-enforcement or account blocking;
- facial recognition or national-ID verification;
- scraping private SMS messages without explicit consent and a separately approved design;
- production-grade forensic certainty;
- training on private receipts without consent, anonymisation and lawful access;
- silently sending full receipt images to a third-party AI service;
- a fully autonomous final fraud verdict without human-review capability;
- storing authentication secrets in a mobile or browser bundle;
- publicly accessible receipt URLs;
- editing the original model result after a human decision.

## 7. Assumptions

- The initial supported receipt layouts can be generic/demo templates plus any authorised, anonymised samples supplied by the owner.
- Reference verification uses CSV/imported records until an authorised adapter is added.
- In-app notifications satisfy the MVP; push/email are optional adapters.
- The first deployment may target one organisation, but the schema should not prevent a future organisation/tenant boundary.
- English is the first UI language. Text must be centralised to support later localisation.
- Receipt amounts use Ghana cedi by default but currency is stored explicitly.
- The system is online-first; upload drafts may be retained locally, but full offline analysis is not required.

## 8. Success criteria

The implementation is complete only when:

1. a new user can register, authenticate, upload a valid receipt, review OCR fields, run analysis and see a persisted result;
2. the result separately displays fraud risk, risk score, verification status and reasons;
3. a reference import can make a test transaction return `VERIFIED` or `MISMATCH` correctly;
4. an unauthorised user cannot read another user's receipt or result;
5. an investigator can review a reported/high-risk case and record a reasoned decision;
6. a model version and feature/rule evidence are traceable from every result;
7. a clean database can be migrated and seeded;
8. CI passes and the documented local verification command succeeds;
9. staging can be deployed without committing secrets;
10. the final handoff contains reproducible evidence rather than unsupported claims.

<!-- END FILE: 00_SOURCE_OF_TRUTH_AND_SCOPE.md -->


---

<!-- BEGIN FILE: 01_CODEX_MASTER_IMPLEMENTATION_PLAN.md -->

# 01 — Codex Master Implementation Plan

## 1. Purpose

This is the execution plan Codex must follow from an empty or partially existing repository through final deployment and inspection. It is intentionally organised into bounded phases so that each session produces a pushed, testable increment and a precise handoff. It is not permission to skip detailed specifications in the other files.

## 2. Delivery strategy

The project uses a Scrum-inspired incremental process. One Codex session should normally complete one phase or one clearly declared subset of a phase. Codex must not begin a later phase while a prerequisite phase has unresolved critical defects.

### Critical path

`P00 -> P01 -> P02 -> P03 -> P06 -> P07 -> P08 -> P09 -> P10 -> P11/P12 -> P13 -> P14/P15/P16 -> P17 -> P18 -> P19 -> P20`

`P04` and `P05` may proceed after `P03` and can run in parallel with some backend work, but the API contract remains the source of truth.

## 3. Delivery modes

### Mode A — New repository

Codex creates the monorepo, initial branch structure, local environment and all applications.

### Mode B — Existing partial repository

Codex first inventories what exists, maps it to the requirements, preserves correct work, writes an explicit gap report and then follows the phases. It must not delete working code merely to match a preferred template.

## 4. Repository-level definition of done

The whole project is complete only when all of the following are true:

- every `MUST` requirement in `02_SYSTEM_REQUIREMENTS_SPECIFICATION.md` is implemented or has an explicitly approved exception;
- `requirements_traceability.csv` maps every requirement to code, database/API/UI artefacts and tests;
- all database migrations run from zero and from the previous released revision;
- the mobile application completes the primary user journey;
- the web portal completes the administrator and investigator journeys;
- OCR, image analysis, structured ML, reference verification and risk aggregation are integrated through one persisted analysis run;
- model and dataset claims are reproducible;
- role and ownership tests prevent cross-user access;
- raw receipts are private;
- CI and the root verification command pass;
- deployment instructions are verified on staging or clearly document the one remaining external credential blocker;
- `FINAL_HANDOFF.md` is complete and references an exact pushed SHA.

## 5. Cross-phase engineering rules

1. **Contract first.** Update the OpenAPI/API contract before changing client-visible behaviour.
2. **Migration first.** Add a migration before code begins depending on a new column or table.
3. **Tests with behaviour.** Do not postpone core tests to P18.
4. **No fabricated intelligence.** Until a model is trained, return a declared model-unavailable or baseline-rule result.
5. **Safe defaults.** Unknown provider, missing field, no reference record or insufficient image quality must not silently become `GENUINE`.
6. **Evidence preservation.** Store original evidence and append derived evidence; do not mutate originals.
7. **Traceability.** Every risk result must point to an analysis run, receipt, model version, rule version and verification result.
8. **Idempotency.** Repeating a create/analyse request with the same idempotency key must not create uncontrolled duplicates.
9. **Separation of concerns.** UI, API, service, repository, persistence and ML layers must remain independently testable.
10. **Honest handoff.** A blocker is acceptable; a false completion statement is not.

## 6. Recommended phase branch map

| Phase | Branch |
|---|---|
| P00 | `codex/p00-preflight-foundation` |
| P01 | `codex/p01-api-infrastructure` |
| P02 | `codex/p02-database-storage` |
| P03 | `codex/p03-auth-rbac` |
| P04 | `codex/p04-mobile-shell` |
| P05 | `codex/p05-admin-shell` |
| P06 | `codex/p06-receipt-upload` |
| P07 | `codex/p07-ocr-review` |
| P08 | `codex/p08-reference-verification` |
| P09 | `codex/p09-image-forensics` |
| P10 | `codex/p10-dataset-tooling` |
| P11 | `codex/p11-structured-model` |
| P12 | `codex/p12-cnn-model` |
| P13 | `codex/p13-risk-orchestration` |
| P14 | `codex/p14-history-reports-notifications` |
| P15 | `codex/p15-case-governance` |
| P16 | `codex/p16-dashboard-analytics` |
| P17 | `codex/p17-ui-accessibility` |
| P18 | `codex/p18-hardening-qa` |
| P19 | `codex/p19-deployment-release` |
| P20 | `codex/p20-final-handoff` |

## 7. Phase execution template

For every phase Codex must:

1. confirm prerequisites and current SHA;
2. name the requirement IDs addressed;
3. implement the smallest complete vertical slice;
4. add tests and fixtures;
5. run phase gates;
6. update traceability, status, decision log and changelog;
7. capture requested screenshots/evidence;
8. commit and push;
9. complete the session handoff.

The following sections define the work.


## P00 — Repository preflight, scope lock and execution foundation

**Goal:** Establish an auditable starting point without losing any existing work.

**Prerequisites:** Git installed; repository path available or permission to initialise a new repository.

### Required work

1. Record repository remote, default branch, current branch, HEAD SHA, worktree status, tracked languages, package managers and existing CI.
2. Search for existing mobile, web, API, database, ML, documentation and deployment code. Produce `docs/implementation/P00_GAP_ANALYSIS.md` mapping retained, missing, conflicting and obsolete elements.
3. Copy or preserve this implementation package in the repository. Ensure root `AGENTS.md` applies.
4. Create `IMPLEMENTATION_STATUS.md`, `DECISION_LOG.md`, `CHANGELOG.md` and traceability/backlog files if absent; never reset completed evidence.
5. Create `.gitignore`, `.editorconfig`, `.gitattributes`, root README and a security note. Exclude `.env*` except `.env.example`, private uploads, datasets, model binaries, caches, build output and coverage output.
6. Choose and document Node and Python versions. Use Python 3.12 unless the target machine demonstrates an incompatible dependency; record any change.
7. Create cross-platform scripts: `scripts/bootstrap.py`, `scripts/verify.py`, `scripts/check_secrets.py` and `scripts/doctor.py`. Initially, scripts may report unimplemented project sections but must fail honestly.
8. Create GitHub issue labels/milestones or a local equivalent derived from `backlog.csv`. Do not spend the phase implementing features.
9. Create the phase branch, commit the foundation, push it and record the remote branch.

### Deliverables

1. Gap analysis and repository inventory
2. Root engineering policy and ignore files
3. Status/decision/changelog/traceability baseline
4. Cross-platform project scripts
5. First pushed phase branch

### Phase verification

1. `python scripts/doctor.py` reports toolchain and missing dependencies
2. `python scripts/check_secrets.py` finds no committed secret
3. `git status --short` is clean after commit
4. Repository can be cloned and documentation paths resolve

### Exit criterion

The exact starting SHA and all retained work are documented; the next developer can reproduce the repository state.


## P01 — Monorepo, API skeleton and local infrastructure

**Goal:** Create a runnable architecture with health checks before domain features.

**Prerequisites:** P00 complete.

### Required work

1. Create the monorepo layout defined in `03_ARCHITECTURE_AND_REPOSITORY_SPEC.md`: `apps/mobile`, `apps/admin`, `services/api`, `ml`, `docs`, `infra`, `scripts` and shared contract locations.
2. Create the Python project with Flask application factory, configuration classes, environment validation, blueprints, structured JSON errors, request IDs and `/api/v1/health`, `/ready` and `/version` endpoints.
3. Create initial OpenAPI generation and an API-contract check. API documentation must be generated from the actual request/response schemas.
4. Create PostgreSQL and API services in Docker Compose. Add health checks, named volumes and a Tesseract-equipped API image.
5. Add SQLAlchemy session management, database readiness check and a placeholder initial migration.
6. Add structured application logging with correlation/request IDs and sensitive-field redaction.
7. Add strict development CORS for known local mobile/admin origins; never use wildcard credentials in production.
8. Create backend formatting, linting, typing and test configuration.
9. Create a root command that starts local dependencies and a root verification command that invokes existing checks.
10. Document Windows, macOS/Linux and Docker bootstrap steps.

### Deliverables

1. Runnable Flask API
2. PostgreSQL local service
3. OpenAPI skeleton
4. Backend CI-ready quality configuration
5. Local setup documentation

### Phase verification

1. Health endpoint returns service version and no secret data
2. Ready endpoint fails when PostgreSQL is unavailable and passes when available
3. Unknown route returns standard JSON error envelope
4. Clean Docker build succeeds
5. Backend lint/type/unit smoke tests pass

### Exit criterion

A clean clone can start the API and database and receive healthy responses using documented commands.


## P02 — Relational schema, migrations, seeds and private storage abstraction

**Goal:** Build the persistent evidence model before feature code.

**Prerequisites:** P01 complete.

### Required work

1. Implement all tables, enums, constraints, relationships and indexes specified in `04_DATABASE_AND_STORAGE_SPEC.md`.
2. Use UUID primary keys, timezone-aware UTC timestamps and explicit enum/check constraints. Define creation/update conventions.
3. Implement Alembic/Flask-Migrate revisions with deterministic names and downgrade paths where safe.
4. Create a storage interface with local-private and S3-compatible implementations. The API chooses the adapter by configuration.
5. Implement generated object keys, SHA-256 hashing, content metadata, private retrieval and deletion/retention hooks.
6. Create seed commands for roles, a bootstrap administrator, demo receipt templates, default fraud rules and test reference records. Bootstrap credentials must come from environment variables and must be changed.
7. Create database factories/fixtures for users, transactions, receipts, OCR results, analyses, models, reference records, cases, notifications and audits.
8. Add soft-deactivation where required; do not soft-delete immutable audit/evidence rows.
9. Add migration tests from an empty database and schema-integrity tests.
10. Generate an engineering ER diagram from the implemented schema and note differences from the Chapter Three diagram.

### Deliverables

1. Versioned schema and migrations
2. Storage adapter interface
3. Seed and fixture tooling
4. Implemented-schema ER reference
5. Database tests

### Phase verification

1. Upgrade from zero to head succeeds
2. Downgrade/upgrade smoke path succeeds for reversible migrations
3. Uniqueness, foreign key and check constraints reject invalid rows
4. Private storage does not expose a public path
5. Deletion/retention routines preserve audit requirements

### Exit criterion

Every persistent object required by later phases has a stable schema and test fixture.


## P03 — Authentication, session security, ownership and RBAC

**Goal:** Secure all identities and establish role boundaries before sensitive features.

**Prerequisites:** P02 complete.

### Required work

1. Implement registration, login, refresh, logout/revocation, current-user, forgot-password and reset-password endpoints.
2. Hash passwords using a suitable adaptive password hash. Never log passwords or reset tokens.
3. Implement short-lived access tokens and rotated refresh tokens. Store only a hash/fingerprint of server-tracked refresh tokens where revocation is required.
4. Implement role decorators/policies for `USER`, `ADMIN` and `INVESTIGATOR`, including combined capabilities.
5. Implement object-level ownership policies so a user cannot access another user's transaction by changing an ID.
6. Implement web refresh through a secure HTTP-only cookie and CSRF protection for cookie-authenticated state changes; keep browser access tokens in memory where used.
7. Define mobile secure-token storage contract for Expo SecureStore. No token in AsyncStorage.
8. Rate-limit login, refresh, password reset and registration; make authentication errors non-enumerating.
9. Audit login success/failure, password reset, role changes, account deactivation and refresh-token revocation.
10. Add admin user-management endpoints only after server-side role checks are complete.
11. Create test accounts through seed tooling, not hard-coded production credentials.

### Deliverables

1. Complete authentication API
2. RBAC/ownership policy layer
3. Reset-token workflow
4. Auth audit events
5. OpenAPI/auth test suite

### Phase verification

1. Register/login/refresh/logout/reset happy paths
2. Expired/revoked/altered tokens rejected
3. Wrong role receives 403; unauthenticated receives 401
4. Cross-user ID access receives 404/403 without leaking object existence
5. Rate limit and generic reset response tested
6. Cookie security/CSRF behaviour tested for web portal

### Exit criterion

No receipt or admin feature can be reached without the correct authenticated role and ownership.


## P04 — Mobile application shell, design system and authentication experience

**Goal:** Create the user-facing mobile foundation with production-quality navigation and states.

**Prerequisites:** P03 API contract stable.

### Required work

1. Scaffold Expo React Native TypeScript and Expo Router using the repository's pinned Node/package-manager version.
2. Create theme tokens for spacing, typography, radius, elevation and semantic statuses. Use icons/text in addition to colour.
3. Create reusable components: screen shell, header, button, input, password input, form error, card, status badge, alert, skeleton, empty state, retry state, confirmation sheet and secure image preview.
4. Implement splash/session restoration, login, registration, forgot-password, reset-password, profile and logout flows.
5. Use React Hook Form and Zod (or the documented selected equivalents) with shared validation semantics.
6. Use TanStack Query for server state, a small dedicated auth/session store and Expo SecureStore for tokens.
7. Create bottom-tab/navigation skeleton: Home, History, Notifications and Profile, plus the central Upload/Scan action.
8. Implement offline/network awareness, API error mapping, global error boundary and retry behaviour.
9. Add accessibility labels, focus order, keyboard handling, dynamic-text support and safe-area support.
10. Create component/unit tests and a smoke E2E path through authentication using a test API.

### Deliverables

1. Runnable mobile app
2. Auth screens and secure session
3. Reusable mobile component library
4. Navigation and state handling
5. Mobile test baseline

### Phase verification

1. Type check, lint and tests pass
2. Token is stored only in secure storage
3. Session restoration and logout work
4. Form validation and server errors are accessible
5. Common Android viewport has no overflow or hidden controls

### Exit criterion

A user can securely authenticate and reach a stable application shell.


## P05 — Administrator and investigator web portal shell

**Goal:** Create the role-aware web workspace before dashboard features.

**Prerequisites:** P03 API contract stable.

### Required work

1. Scaffold React + TypeScript + Vite with React Router and a route-level permission guard.
2. Create a responsive design system and reusable data-table, filter, pagination, dialog, drawer, form, badge, chart-container, skeleton and error components.
3. Implement administrator/investigator login, session refresh, logout and permission-aware navigation.
4. Create shell routes for Dashboard, Transactions, Cases, Users, Reference Imports, Templates, Rules, Models, Reports, Audit Logs and System Status.
5. Implement a no-access page, 404 page, global error boundary and session-expired behaviour.
6. Use TanStack Query for server state and React Hook Form/Zod for forms.
7. Create secure download handling for private reports/evidence through authenticated API calls.
8. Add responsive breakpoints for desktop and tablet; tables must have accessible mobile/tablet alternatives where needed.
9. Set up unit/component tests and Playwright smoke tests.
10. Generate a production build in CI.

### Deliverables

1. Runnable web portal shell
2. Role-aware navigation
3. Reusable web component library
4. Auth/session workflow
5. Web test baseline

### Phase verification

1. Admin and investigator see only allowed navigation/actions
2. Refresh/logout/session expiry tested
3. Keyboard navigation and visible focus tested
4. Responsive routes render without horizontal document overflow
5. Production build succeeds

### Exit criterion

Authorised staff can securely enter a complete, role-aware portal shell.


## P06 — Receipt capture, hostile-file validation and private upload

**Goal:** Implement secure receipt acquisition as the first end-to-end user feature.

**Prerequisites:** P02, P03 and P04 complete.

### Required work

1. Implement camera/gallery selection with Expo ImagePicker and runtime permissions.
2. Implement client preview, replace/remove action, accepted-format guidance and quality hints without trusting client validation.
3. Create multipart upload API with authentication, idempotency key and ownership.
4. Allowlist JPEG, PNG and WEBP. Validate extension, magic/decode result, dimensions, animated/multi-frame behaviour, decompression-bomb limits and configured maximum bytes.
5. Apply EXIF orientation only to a derived copy; retain the immutable original.
6. Generate server-side object keys; never use the user's filename as a storage path.
7. Compute SHA-256 and perceptual hash. Record exact duplicate candidates but do not expose other users' data.
8. Create transaction and receipt rows atomically; roll back database/storage consistently on failure.
9. Implement authenticated thumbnail/original retrieval through short-lived signed access or an API stream; enforce ownership/role.
10. Create upload progress, success, invalid-file, too-large, poor-quality, duplicate-warning and retry UI states.
11. Audit upload, rejection and protected file access.

### Deliverables

1. Secure upload API
2. Private storage integration
3. Mobile capture/preview/upload screens
4. Receipt metadata and hashes
5. Upload abuse tests

### Phase verification

1. Valid formats upload and persist
2. Renamed non-image, corrupt file, oversized image and extreme dimensions are rejected
3. Path traversal filename has no effect
4. Cross-user image retrieval is blocked
5. Duplicate hash is detected without leaking owner information
6. Storage/database rollback tested

### Exit criterion

An authenticated user can submit a receipt safely and reopen its private preview.


## P07 — OCR preprocessing, extraction, confidence and correction workflow

**Goal:** Turn uploaded images into reviewable structured transaction fields.

**Prerequisites:** P06 complete; Tesseract available in local/container environment.

### Required work

1. Implement image quality metrics and preprocessing variants: orientation correction, scale normalisation, grayscale/CLAHE, denoise, sharpen, Otsu/adaptive threshold and optional deskew.
2. Run Tesseract `image_to_data` or equivalent to retain token text, bounding boxes and confidence.
3. Score preprocessing variants by OCR confidence and required-field coverage; retain the chosen variant and summary, not only final text.
4. Create provider/template detection with a generic fallback. Store template/parser versions.
5. Implement parsers and normalisers for transaction ID, amount/currency, names, phone numbers, date/time and status text.
6. Store raw OCR text, token data, extracted values, per-field confidence, parser version and warnings.
7. Create API response for OCR review. Mark fields below the configured confidence threshold.
8. Implement mobile OCR Review screen with side-by-side/zoomable receipt, editable fields, confidence/warning indicators and confirmation.
9. Preserve original OCR value and correction audit trail. Do not overwrite raw OCR evidence.
10. Add fixture-based OCR regression tests, including rotated, noisy, low-contrast and cropped receipts.
11. Measure required-field extraction on the controlled evaluation set and report the actual value without inflating it.

### Deliverables

1. Versioned OCR pipeline
2. Field parser and confidence model
3. Mobile OCR review/correction flow
4. OCR fixtures and evaluation report
5. OCR audit evidence

### Phase verification

1. Known fixtures extract expected fields within normalised tolerance
2. Low-confidence fields are flagged
3. Correction creates an audit record and preserves original values
4. Invalid state transition to analysis before OCR review is rejected
5. Tesseract-unavailable path returns explicit partial/failure status

### Exit criterion

A user can review accurate structured fields and correct uncertain values before final analysis.


## P08 — Reference-record import and transaction verification

**Goal:** Implement the prototype's actual verification mechanism without claiming live MNO access.

**Prerequisites:** P07 complete; P05 shell available for import UI.

### Required work

1. Implement reference-import batches with file hash, source label, uploader, row counts, status and audit trail.
2. Define a CSV template and validation: provider, transaction reference, amount, currency, sender/receiver phone/name, timestamp, status and optional source-system ID.
3. Implement preview-before-commit. Invalid rows must be downloadable with reasons; a bad row must not silently corrupt good data.
4. Normalise references, phone numbers, amounts, currency and timestamps consistently with OCR output.
5. Implement exact candidate lookup by provider/reference and safe fallback rules where documented.
6. Compare critical fields using configured amount/timestamp tolerances and normalised exact/fuzzy text comparisons.
7. Return a structured verification result with status, field-level comparisons, matched reference ID, confidence/warnings and rules version.
8. Implement duplicate reference, repeated receipt and transaction-reuse indicators.
9. Create admin import/list/detail UI and user result verification section.
10. Seed safe demonstration reference data and tests.
11. Label all UI and documentation as stored/imported reference verification.

### Deliverables

1. Reference CSV contract
2. Validated import workflow
3. Versioned verification engine
4. Field-level comparison evidence
5. Admin/user verification UI

### Phase verification

1. Matching record returns VERIFIED
2. No record returns UNVERIFIED
3. Critical mismatch returns MISMATCH with exact reasons
4. Duplicate import is idempotent or explicitly rejected
5. Invalid rows and file-level errors are reported
6. Unauthorised import and reference reads are blocked

### Exit criterion

Verification works end to end using authorised stored/imported records and makes no live-MNO claim.


## P09 — Deterministic image-forensics and manipulation evidence

**Goal:** Create explainable visual evidence independent of a trained CNN.

**Prerequisites:** P06 and P07 complete.

### Required work

1. Implement metadata inspection: format, dimensions, EXIF presence, encoder hints and suspicious inconsistencies. Treat absence of metadata as neutral, not fraud.
2. Implement exact/near duplicate checks using SHA-256 and perceptual hash distance.
3. Implement JPEG recompression/error-level analysis on derived images with controlled quality settings and summary statistics.
4. Implement noise/residual inconsistency features across regions, with safeguards for tiny/low-quality images.
5. Implement crop/completeness and aspect/template-layout checks.
6. Use OCR bounding boxes to derive text baseline, spacing, alignment, font-size proxy and overlap features.
7. Create per-signal evidence records with value, threshold, severity, confidence, reason code and version.
8. Optionally create private heatmap/diagnostic derivatives for investigators; never expose them publicly.
9. Create a transparent rule-evaluation layer. No single weak heuristic may set `FRAUDULENT` by itself.
10. Add controlled manipulated fixtures and regression tests.
11. Document limitations of ELA, metadata and template heuristics.

### Deliverables

1. Versioned deterministic image-analysis service
2. Evidence/reason-code catalogue
3. Investigator diagnostic artefacts
4. Manipulated-image test fixtures
5. Limitations documentation

### Phase verification

1. Exact and near duplicates detected
2. Known edits trigger expected evidence without asserting certainty
3. Metadata absence alone does not mark fraud
4. Original image remains byte-identical
5. Private diagnostic derivative access is role/ownership protected

### Exit criterion

Every receipt can produce an explainable, versioned set of image-evidence features even before CNN inference.


## P10 — Dataset governance, controlled sample generation and reproducible splits

**Goal:** Create the data foundation needed for honest model development.

**Prerequisites:** P07 and P09 feature schemas sufficiently stable.

### Required work

1. Create `ml/data/README.md`, dataset card template, consent/licence fields and private-data handling instructions.
2. Implement a manifest-driven dataset loader using the sample columns in `samples/receipt_dataset_manifest.csv`.
3. Create a generic Ghana-style demonstration receipt generator that does not copy protected provider branding unless authorised.
4. Create controlled tampering operations for research fixtures: amount/reference/recipient replacement, crop, clone/paste, misalignment, font mismatch and recompression.
5. Tag every synthetic/controlled sample, parent/source group, manipulation operations and generation seed.
6. Create train/validation/test splits by source/parent group before augmentation. Prevent variants of one receipt appearing in multiple splits.
7. Add data validation for missing files, duplicate hashes, conflicting labels, class distribution, corrupt images and private identifiers.
8. Create anonymisation checks for phone/reference/name fields used in research data.
9. Store manifests and small sanitised fixtures in Git; keep raw private images outside Git.
10. Produce a reproducible dataset report with counts, class distribution, source types, split hashes and known limitations.

### Deliverables

1. Dataset card and governance rules
2. Manifest-driven loader
3. Controlled sample generator
4. Leakage-resistant split files
5. Dataset validation report

### Phase verification

1. No source group crosses splits
2. Augmentation is applied only after split and only to training
3. Dataset loader rejects missing/conflicting records
4. Private-pattern scanner flags unapproved identifiers
5. Regenerating with the same seed reproduces manifest hashes

### Exit criterion

Model training can be reproduced from a documented, leakage-controlled and lawfully usable dataset.


## P11 — Structured-feature fraud classifier

**Goal:** Train and integrate the scikit-learn model for structured evidence.

**Prerequisites:** P08-P10 complete; stable feature schema.

### Required work

1. Define a versioned feature schema covering OCR confidence/coverage, field validity, image heuristics, duplicate indicators, template consistency and verification comparisons.
2. Build an sklearn Pipeline/ColumnTransformer so encoders/imputers/scalers are fit only on training data.
3. Train a RandomForest baseline with class weighting and deterministic seeds. Compare only a small justified set of alternatives if useful; avoid unnecessary model shopping.
4. Use group-aware validation and a held-out test set. Tune on training/validation only.
5. Report confusion matrix, per-class precision/recall/F1, macro F1, balanced accuracy and probability calibration diagnostics.
6. Select and document class thresholds using validation data and project risk priorities.
7. Create a model card with data scope, feature schema, metrics, limitations, intended use and prohibited claims.
8. Persist the model in a trusted artifact format, store SHA-256, library versions, training commit and feature schema hash.
9. Register model metadata in `MODEL_VERSIONS`; never auto-activate a model that failed acceptance gates.
10. Implement deterministic inference service and contract tests.
11. Add a CLI to train, evaluate, register and activate models with explicit confirmation.

### Deliverables

1. Reproducible training pipeline
2. Structured model artifact and card
3. Evaluation report
4. Version registry integration
5. Inference service

### Phase verification

1. Training repeatability within documented tolerance
2. Pipeline rejects schema drift/missing mandatory features
3. Held-out set is never used during fit/tuning
4. Artifact hash verified before load
5. Inference output probabilities are valid and version traceable

### Exit criterion

A registered structured classifier produces reproducible, honest and versioned predictions.


## P12 — CNN receipt-tampering classifier

**Goal:** Train and integrate the TensorFlow/Keras image model.

**Prerequisites:** P10 complete; sufficient authorised/controlled image data.

### Required work

1. Define input resolution, colour handling, normalisation and augmentation policy.
2. Implement a transfer-learning baseline such as MobileNetV3Small with a small classification head; document any architecture change.
3. Freeze/unfreeze in controlled stages and use early stopping/model checkpoints based on validation metrics.
4. Use group-separated splits and training-only augmentation.
5. Address class imbalance through justified class weights or sampling; do not duplicate test data.
6. Report per-class metrics, macro F1, confusion matrix, ROC/PR information where meaningful and calibration.
7. Create a model card and explicit synthetic-only limitation where applicable.
8. Export a `.keras` artifact, compute hash and register preprocessing/model metadata.
9. Implement inference with deterministic preprocessing and safe fallback when the artifact is absent or incompatible.
10. Create optional investigator heatmap/attention diagnostic only as a supporting visual, not proof of manipulation.
11. Add performance measurement for CPU inference in the deployment container.

### Deliverables

1. Reproducible CNN training/evaluation pipeline
2. Versioned image-model artifact and card
3. CNN inference service
4. CPU performance report
5. Safe unavailable-model behaviour

### Phase verification

1. Training/test group separation asserted
2. Preprocessing parity between training and inference
3. Artifact hash/version check
4. Corrupt/unsupported image returns controlled error
5. Inference latency recorded on target container
6. Absent model produces PARTIAL, not fabricated probability

### Exit criterion

The image model is versioned, reproducible and safely integrated or explicitly marked unavailable.


## P13 — End-to-end analysis orchestration, rules and risk aggregation

**Goal:** Combine all evidence into one auditable analysis result.

**Prerequisites:** P07-P09 complete; P11/P12 available or explicit unavailable adapters.

### Required work

1. Implement `AnalysisOrchestrator` with validated state transitions and idempotent analysis requests.
2. Snapshot corrected OCR fields, parser/template versions, feature schema, rule set, model versions and thresholds at analysis start.
3. Run verification, deterministic image analysis, CNN inference and structured-model inference through typed service interfaces.
4. Persist subsystem start/end/error status and timings. A subsystem failure must not destroy successful evidence.
5. Implement the preliminary configurable score `R = 100 * (0.40*p_img + 0.40*p_ml + 0.20*p_rule)` while preserving the raw components.
6. Calibrate and store thresholds; initial defaults may be `GENUINE < 35`, `SUSPICIOUS 35–69.99`, `FRAUDULENT >= 70` only until validated.
7. Define rule probability/severity mapping and ensure no circular feature leakage from the final label.
8. Create top reason-code selection and plain-language explanations.
9. Display verification separately, but allow a critical mismatch/reuse rule to contribute explicitly to fraud risk.
10. Return `PARTIAL` when required components are unavailable. Use conservative messaging for insufficient evidence.
11. Add full analysis API and mobile progress/result screens.
12. Create golden end-to-end fixtures for low-risk, suspicious, fraudulent, verified, unverified, mismatch and partial outcomes.

### Deliverables

1. Analysis orchestrator
2. Versioned risk aggregation
3. Persisted analysis-run evidence
4. Mobile progress/result/evidence views
5. End-to-end golden tests

### Phase verification

1. Idempotent retry does not duplicate a completed result
2. All component versions and timings are persisted
3. Risk and verification fields remain separate
4. Threshold boundaries tested
5. Subsystem failure produces PARTIAL with retained evidence
6. Reason codes match underlying evidence
7. Ownership and role access enforced

### Exit criterion

One user upload can complete the full persisted OCR-to-result journey with explainable outputs.


## P14 — History, search, downloadable reports and notifications

**Goal:** Complete the everyday user workflow after analysis.

**Prerequisites:** P13 complete.

### Required work

1. Implement paginated user transaction history with date, provider, risk, verification and status filters.
2. Implement transaction detail that reconstructs result from persisted evidence rather than rerunning models.
3. Create a server-generated analysis summary PDF or equivalent downloadable report containing masked identifying data, result, reasons, verification comparisons, model/rule versions and disclaimer.
4. Authorise every report download; use a short-lived generated file or streamed response.
5. Implement in-app notification records for analysis completion, high-risk results and case-status changes.
6. Implement notification list, unread count, mark-read and deep link to the relevant transaction/case.
7. Add optional notification-delivery adapter interface; keep external push/email disabled when credentials are absent.
8. Create mobile History, Transaction Detail, Report, Notifications and notification-settings screens.
9. Add retention and regeneration rules for downloadable reports.
10. Audit report generation/download and notification-delivery state changes.

### Deliverables

1. History/search API and UI
2. Persisted detail reconstruction
3. Downloadable analysis summary
4. In-app notifications
5. Audit coverage

### Phase verification

1. Pagination/filter combinations correct
2. Users cannot download another user's report
3. Historical detail remains stable after model activation changes
4. PDF/report masks configured fields
5. Notification read/unread and deep links work
6. External adapter failure does not lose in-app notification

### Exit criterion

Users can find, understand and export their previous analyses and receive lifecycle notifications.


## P15 — Fraud reporting, investigation and governance administration

**Goal:** Complete human review and controlled system configuration.

**Prerequisites:** P13 and P05 complete.

### Required work

1. Implement user suspicious-transaction report creation with category, description and linked transaction.
2. Automatically create or queue cases for configured high-risk outcomes without duplicating a user report.
3. Implement case assignment, status transitions, notes and reasoned confirm/dismiss/escalate decisions.
4. Keep human decision fields separate from automated risk and verification records.
5. Implement investigator Case Queue and Case Detail with private original/derived evidence, OCR comparison, model/rule evidence, verification comparison and timeline.
6. Implement administrator user/role management with last-admin safeguards and audited role changes.
7. Implement receipt-template registry, rule registry and thresholds with draft/active/retired version states.
8. Implement model registry views and controlled activation/rollback; activation requires artefact hash and readiness checks.
9. Implement reference-import administration from P08.
10. Implement case report generation and audit timeline.
11. Apply field masking according to role and purpose.

### Deliverables

1. User report workflow
2. Investigator case queue/detail/decision
3. Admin registries and user management
4. Model/rule activation controls
5. Case reports and timelines

### Phase verification

1. Decision requires reason and valid state
2. Automated result remains unchanged after decision
3. Duplicate case creation prevented
4. Investigator cannot access admin-only configuration
5. Last active administrator cannot be accidentally removed
6. Model/rule rollback produces audited version change

### Exit criterion

Flagged evidence can be reviewed and governed without compromising original automated evidence.


## P16 — Operational dashboard, analytics, audit and system status

**Goal:** Provide useful monitoring without leaking sensitive data or recomputing history.

**Prerequisites:** P13-P15 complete.

### Required work

1. Implement dashboard aggregates: total analyses, processing states, risk-class counts, verification counts, cases by status, average latency and model availability.
2. Implement date/provider filters and safe trend charts.
3. Implement transaction search/list for authorised staff with masked values and role-limited detail.
4. Implement audit-log search by actor, action, target, date and request ID; full sensitive payloads must not be logged.
5. Implement system-status page for database, storage, Tesseract, active models and optional notification adapters.
6. Implement operational reports/export with row limits, authorisation and audit.
7. Use database indexes/aggregations appropriate for 100,000 analysis records; avoid loading all rows into application memory.
8. Add empty, loading, partial-data and unavailable-component states.
9. Add chart/table accessibility and downloadable tabular alternatives.
10. Add analytics correctness and permission tests.

### Deliverables

1. Admin dashboard
2. Operational search and exports
3. Audit-log UI
4. System status UI
5. Analytics tests

### Phase verification

1. Aggregate values match seeded ground truth
2. Date/provider filters correct
3. Export limits and role permissions enforced
4. Dashboard avoids unbounded queries
5. Sensitive values masked in logs/UI
6. Status correctly reports unavailable dependencies

### Exit criterion

Administrators can monitor the platform and investigate operational evidence safely.


## P17 — UI completion, accessibility, responsive and visual QA

**Goal:** Turn all implemented flows into a coherent, polished and defensible interface.

**Prerequisites:** P04-P16 feature-complete.

### Required work

1. Perform a screen inventory against `06_UI_UX_IMPLEMENTATION_SPEC.md`; implement every missing loading, empty, error, retry, offline, permission and destructive-confirmation state.
2. Apply final brand tokens while keeping semantic status accessible through text and icons.
3. Ensure risk and verification presentation is consistent on cards, detail pages, PDFs and dashboards.
4. Improve receipt image zoom/pan, OCR field-to-image highlighting and evidence explanations.
5. Review mobile keyboard, small-screen, safe-area, orientation and dynamic-text behaviour.
6. Review admin at required desktop/tablet widths; eliminate layout overflow and inaccessible table interactions.
7. Add accessibility labels, landmarks, form descriptions, focus management, contrast checks and reduced-motion support.
8. Run visual regression or screenshot comparison for critical screens.
9. Capture final UI screenshots separately from Chapter Three wireframes.
10. Conduct a user-journey review with non-technical copy and remove debug/internal terminology.

### Deliverables

1. Complete final UI
2. Accessibility review
3. Responsive/viewport evidence
4. Visual regression baseline
5. Final screenshots

### Phase verification

1. Critical journeys complete by keyboard/screen-reader-friendly controls
2. No colour-only status
3. No viewport overflow at agreed sizes
4. All forms announce errors
5. Screenshot/visual checks reviewed
6. Mobile primary analysis starts within the specified principal-action target

### Exit criterion

The mobile and web interfaces are complete, consistent, accessible and ready for evaluation.


## P18 — Full hardening, security, performance and regression QA

**Goal:** Prove the system under adverse and end-to-end conditions.

**Prerequisites:** Feature complete through P17.

### Required work

1. Run the complete test matrix in `09_TESTING_QA_RELEASE_PLAN.md` on a clean clone and clean database.
2. Add missing backend unit/integration tests to meet coverage targets, prioritising auth, ownership, upload, verification, risk and case decisions.
3. Complete mobile and admin unit/component tests and critical Playwright/Detox-or-equivalent flows.
4. Run upload abuse, IDOR, role bypass, token, rate-limit, injection, export and private-file tests.
5. Run dependency vulnerability audit, secret scan and static analysis; triage findings rather than hiding them.
6. Run performance tests for login/history/upload/analysis and dashboard queries. Record hardware/environment and actual results.
7. Run 25-concurrent-analysis prototype test or document the measured limit and bottleneck honestly.
8. Verify backup/restore, migration rollback plan and storage/database consistency recovery.
9. Test model artifact corruption, missing Tesseract, database interruption, storage failure and partial-analysis recovery.
10. Review logs for PII/secrets and validate audit completeness.
11. Create `docs/qa/P18_TEST_REPORT.md` with commands, versions, pass counts, failures and accepted risks.

### Deliverables

1. Complete regression suite
2. Security test report
3. Performance report
4. Backup/recovery evidence
5. Defect list and resolutions

### Phase verification

1. Root verification command passes
2. Critical security test suite passes
3. No unresolved critical/high defect
4. Coverage reports meet targets or exception is documented
5. Performance results are measured and reproducible
6. Clean clone verification succeeds

### Exit criterion

The codebase has objective evidence of correctness, security and operational resilience.


## P19 — Staging deployment, release engineering and rollback

**Goal:** Deploy a reproducible release without exposing secrets or private receipts.

**Prerequisites:** P18 gates pass.

### Required work

1. Create production Docker image with pinned dependencies, non-root runtime, Tesseract language data and health checks.
2. Create staging configuration for API, managed PostgreSQL and private S3-compatible storage. Use environment secrets, never committed credentials.
3. Deploy the administrator portal with correct API origin and security headers.
4. Create Expo EAS configuration and an internal Android build; iOS build is conditional on account access.
5. Run database migrations as an explicit release step; do not rely on multiple web workers racing migrations.
6. Create bootstrap-admin process, CORS/CSRF/cookie domain configuration and signed/private storage verification.
7. Configure HTTPS, request/body limits, log retention and backup schedule.
8. Run staging smoke/E2E tests with safe test data.
9. Create release tag, release notes, deployment manifest and exact image/build identifiers.
10. Test rollback of application version and document database rollback limitations.
11. Do not claim deployment when external account access is unavailable; provide ready-to-run manifests and exact blocker.

### Deliverables

1. Staging API/admin/mobile build or deploy-ready manifests
2. Release and rollback runbook
3. Environment/secrets checklist
4. Staging smoke evidence
5. Tagged release candidate

### Phase verification

1. Health/readiness from staging
2. End-to-end safe receipt flow on staging
3. Private image URL not public
4. Migration revision matches application
5. Rollback rehearsal documented
6. No secret exposed in frontend/mobile bundles or repository

### Exit criterion

A reproducible release candidate is deployed or is blocked only by an explicitly identified external credential.


## P20 — Final documentation, evidence, cleanup and inspection handoff

**Goal:** Freeze a reviewable final state and make independent inspection efficient.

**Prerequisites:** P19 complete or approved deployment blocker recorded.

### Required work

1. Resolve remaining TODO/FIXME markers or convert them into documented non-critical issues.
2. Update architecture, implemented ERD, API, state-machine and sequence documentation to match code.
3. Complete requirements traceability with exact code paths and test names.
4. Complete model cards, dataset cards, security report, test report, deployment report and limitations.
5. Capture final Chapter Four evidence listed in `13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md`.
6. Verify academic diagrams can be regenerated cleanly with no crossing lines and reflect actual relationships/multiplicities.
7. Run clean-clone bootstrap and full verification one final time.
8. Ensure worktree is clean, branch is pushed and CI is green at the exact final SHA.
9. Complete `templates/FINAL_HANDOFF.md` with branch, base/head SHA, tree status, tests, deployment, accounts, artifacts, known limitations and reproduction commands.
10. Open or update the final pull request; do not merge unless instructed.
11. Provide a concise repair prompt template for any later audit findings.

### Deliverables

1. Final handoff
2. Complete traceability
3. Updated diagrams/docs
4. Final verification evidence
5. Exact pushed review SHA

### Phase verification

1. Clean clone setup passes
2. Full verification and CI pass at final SHA
3. All MUST requirements are implemented or approved exceptions
4. Final handoff links resolve
5. Git status clean and remote contains exact SHA

### Exit criterion

An independent reviewer can inspect, run and assess the system without relying on undocumented context.


## 8. Milestone review points

To preserve review time and tokens, use three optional milestone audits plus the final audit:

- **Milestone A:** after P07 — foundation, security, upload and OCR.
- **Milestone B:** after P13 — complete analytical pipeline.
- **Milestone C:** after P17 — complete user/admin product.
- **Final:** after P20 — repository, CI, deployment and documentation inspection.

For each audit, provide the repository, branch/pull request and exact SHA. Do not ask the reviewer to infer which commit should be checked.

## 9. Project-owner decisions that must not be guessed

Codex should continue with safe defaults where allowed, but it must record these unresolved owner decisions:

- final brand name, logo and colour identity;
- whether end-user self-registration remains open in production;
- authorised provider receipt templates;
- approved real dataset and consent/licence status;
- production reference-record source;
- deployment provider/accounts;
- data-retention period;
- notification provider;
- whether administrators may also act as investigators;
- final risk thresholds after evaluation;
- final password/session policy if the institution sets one.

## 10. Feature prioritisation under deadline pressure

The minimum academically defensible vertical slice, in order, is:

1. secure authentication and private upload;
2. OCR extraction and correction;
3. deterministic image evidence;
4. stored/imported reference verification;
5. one reproducible structured fraud model;
6. risk aggregation with explanations;
7. history and investigator review;
8. automated tests and deployment.

The CNN is important to the declared scope but must not delay delivery of an honest baseline. When an adequate image dataset is unavailable, Codex must complete the training pipeline, controlled dataset tooling and unavailable-model state, then document the limitation rather than inventing performance.

## 11. Final acceptance decision

The final audit classifies findings as:

- **BLOCKER:** cannot run, data/security loss, false core claim or missing primary journey.
- **CRITICAL:** exploitable access/control failure, public private data, invalid model/data methodology or destructive migration.
- **HIGH:** major requirement missing, incorrect result, broken admin/investigator workflow or unreproducible evaluation.
- **MEDIUM:** incomplete edge case, weak UX/accessibility, insufficient test or documentation gap.
- **LOW:** maintainability, wording, minor visual or non-critical optimisation.

Release requires zero open blocker/critical findings and an explicit decision on every high finding.

<!-- END FILE: 01_CODEX_MASTER_IMPLEMENTATION_PLAN.md -->


---

<!-- BEGIN FILE: 02_SYSTEM_REQUIREMENTS_SPECIFICATION.md -->

# 02 — System Requirements Specification

## 1. Requirement language

- **MUST:** required for final acceptance unless the owner explicitly approves an exception.
- **SHOULD:** expected for the complete prototype; a missed target must be measured and explained.
- **MAY:** optional extension and must not delay MUST requirements.

Every requirement has a stable identifier. Codex must keep `requirements_traceability.csv` current with implementation paths, API routes, database objects, UI screens and test names.

## 2. Primary use cases

### UC-U01 — Register and authenticate

**Primary actor:** User  
**Precondition:** Registration is enabled or an account exists.  
**Main flow:** User registers or logs in; server validates input; session is issued; user enters the mobile home screen.  
**Alternatives:** Duplicate email, invalid password, throttled request, disabled account, expired session.  
**Postcondition:** Authenticated session exists or a safe error is displayed.

### UC-U02 — Upload and review a receipt

**Primary actor:** User  
**Precondition:** User is authenticated.  
**Main flow:** Select camera/gallery; preview image; submit; server validates and stores original; OCR runs; low-confidence fields are displayed; user corrects and confirms.  
**Alternatives:** Permission denied, corrupt/oversized image, poor image quality, OCR unavailable, unknown template.  
**Postcondition:** A protected receipt and confirmed structured field snapshot exist.

### UC-U03 — Analyse a transaction

**Primary actor:** User  
**Precondition:** Receipt and OCR review are complete.  
**Main flow:** User starts analysis; system runs image evidence, models, rules and reference verification; system persists versions, probabilities, reasons and status; user sees result.  
**Alternatives:** Model missing, reference absent, subsystem failure, duplicate request.  
**Postcondition:** `COMPLETED`, `PARTIAL` or `FAILED` analysis record exists.

### UC-U04 — View history and report suspicion

**Primary actor:** User  
**Precondition:** User has one or more analyses.  
**Main flow:** Filter history; open detail; download summary; optionally report suspicion.  
**Alternatives:** Empty history, report already exists, report generation failure.  
**Postcondition:** History is unchanged; optional case is created/linked.

### UC-A01 — Import reference transactions

**Primary actor:** Administrator  
**Main flow:** Upload CSV; validate; preview; download invalid rows if any; commit valid import; audit.  
**Postcondition:** Versioned import batch and reference records exist.

### UC-A02 — Govern templates, rules and models

**Primary actor:** Administrator  
**Main flow:** View versions; create draft; validate; activate or roll back; audit.  
**Postcondition:** Active version changes without altering historical evidence.

### UC-I01 — Review a flagged case

**Primary actor:** Investigator  
**Main flow:** Open queue; inspect receipt/OCR/image/ML/rule/verification evidence; add note; confirm/dismiss/escalate with reason; generate report.  
**Postcondition:** Human decision is appended; original automated result is unchanged.

## 3. Functional and non-functional requirements

### User account

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-USER-001` | MUST | The system shall allow a user to register with name, email and password when self-registration is enabled. | A valid unique email creates a USER account; duplicate/invalid input returns a non-sensitive validation error. |
| `FR-USER-002` | MUST | The system shall allow a user to authenticate, refresh a session and log out. | Valid credentials create a session; refresh rotates credentials; logout makes the refresh credential unusable. |
| `FR-USER-003` | MUST | The system shall provide a single-use, expiring password-reset flow. | Reset request does not reveal account existence; valid unused token resets the password; reused/expired token fails. |

### User profile

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-USER-004` | SHOULD | The user shall be able to view and update permitted profile and notification settings. | Allowed fields persist; protected role/security fields cannot be changed by the user. |

### Privacy

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-USER-005` | MUST | The user shall be able to request deletion or deactivation according to the configured retention policy. | Account action is audited; evidential/audit retention is applied and the user can no longer authenticate when deactivated. |
| `NFR-PRIV-001` | MUST | The system shall minimise, mask and restrict receipt-derived personal data according to role and purpose. | UI/report/log inspection confirms configured masking and no unnecessary values. |

### Authentication

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUTH-001` | MUST | Passwords shall be stored only as adaptive password hashes. | No plaintext password appears in database/logs; verification succeeds only for the correct password. |
| `FR-AUTH-002` | MUST | Protected API routes shall validate an unexpired access credential. | Missing, malformed, expired or revoked credentials are rejected consistently. |
| `FR-AUTH-005` | MUST | Authentication and password-reset endpoints shall be rate limited and shall not permit account enumeration. | Repeated requests are throttled; unknown and known reset emails receive equivalent public responses. |

### Authorization

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUTH-003` | MUST | Server-side role policies shall distinguish USER, ADMIN and INVESTIGATOR permissions. | Automated tests demonstrate allow/deny outcomes for every protected route. |
| `FR-AUTH-004` | MUST | Server-side object ownership shall prevent users from reading or modifying another user's transactions, images, reports or notifications. | Changing an object ID cannot expose another user's data. |

### Administration

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUTH-006` | MUST | Only an authorised administrator shall assign or revoke roles. | Role changes are validated, audited and protected against removal of the last active administrator. |
| `FR-ADM-001` | MUST | Administrators shall manage users, account status and authorised roles. | Actions are permission checked and audited. |
| `FR-ADM-002` | MUST | Administrators shall manage versioned receipt templates and parsers' configuration metadata. | Draft/active/retired states are enforced; historical analyses retain old version. |
| `FR-ADM-003` | MUST | Administrators shall manage versioned fraud rules and thresholds. | Activation/rollback is audited and validated. |
| `FR-ADM-004` | MUST | Administrators shall view registered model versions and readiness/activation status. | Missing/corrupt artifact is visibly unavailable. |

### Receipt capture

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-001` | MUST | The mobile application shall allow a user to capture a receipt with the camera or choose an image from the gallery. | Both sources produce a preview and can be submitted with runtime permission handling. |

### Upload security

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-002` | MUST | The API shall accept only configured JPEG, PNG and WEBP receipt images within configured byte and dimension limits. | Valid images pass; corrupt, disguised, oversized and extreme-dimension payloads fail before persistence. |

### Storage

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-003` | MUST | The server shall assign generated object keys and store original receipt images privately. | The original is not placed under a public web root and cannot be accessed without authorisation. |

### Evidence integrity

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-004` | MUST | The system shall calculate and persist a SHA-256 hash for each original receipt. | Re-reading the stored original reproduces the recorded hash. |

### Duplicate detection

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-005` | MUST | The system shall calculate a perceptual hash and identify exact or near-duplicate candidates without exposing other users' data. | Controlled duplicates are flagged; response contains no foreign owner identity. |

### Transactional integrity

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-006` | MUST | Receipt storage and database creation shall fail consistently without leaving uncontrolled orphan records or objects. | Injected storage/database failures are recovered or recorded for cleanup. |

### Receipt quality

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-UPL-007` | SHOULD | The system shall calculate basic image-quality warnings before OCR. | Blur, very low contrast or too-small text fixtures produce warnings without automatically being labelled fraudulent. |

### OCR preprocessing

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-001` | MUST | The system shall create versioned derived preprocessing variants without modifying the original image. | Original hash remains unchanged; variants record operations and version. |

### OCR recognition

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-002` | MUST | The system shall retain raw OCR text, token bounding boxes and confidence values. | OCR result can be reconstructed and inspected from persisted evidence. |

### Field extraction

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-003` | MUST | The system shall extract transaction reference, amount/currency, relevant names/phones, date/time, provider where detectable and status text where present. | Controlled fixtures populate the expected normalised fields or an explicit missing-field warning. |

### Normalisation

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-004` | MUST | The system shall normalise Ghanaian phone formats, currency amounts, dates/times and transaction references consistently. | Equivalent input formats map to a canonical representation used by verification. |

### Confidence review

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-005` | MUST | The mobile application shall mark low-confidence or invalid fields for user review. | Fields below threshold or failing validation are visibly identified and editable. |

### Correction audit

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-006` | MUST | User corrections shall preserve the original OCR value and create an audit trail. | Both original and corrected values, actor and timestamp remain available. |

### Template fallback

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-007` | MUST | Unknown receipt layouts shall use a generic parser and return explicit limitations rather than fail silently. | Unknown-provider fixture reaches review with warnings and retained raw OCR. |

### OCR readiness

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-OCR-008` | MUST | The system shall prevent final analysis until required OCR review/state conditions are met. | Invalid state transition returns a descriptive conflict response. |

### Image analysis

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-IMG-001` | MUST | The system shall record metadata/format evidence without treating missing metadata alone as fraud. | Metadata evidence has neutral/positive/negative interpretation and version. |
| `FR-IMG-002` | MUST | The system shall calculate versioned recompression/error-level summary features on derived images. | Feature values and algorithm settings are persisted; original is unchanged. |
| `FR-IMG-003` | MUST | The system shall calculate noise/residual consistency features when image quality permits. | Unsupported/low-quality conditions yield not-applicable warnings rather than invented values. |
| `FR-IMG-004` | MUST | The system shall calculate layout, crop/completeness and OCR text-alignment evidence. | Controlled misalignment/crop fixtures trigger expected reason codes. |
| `FR-IMG-005` | MUST | Each image-evidence signal shall store value, version, threshold/rule, severity and reason code. | Investigator view can trace a displayed reason to its persisted signal. |
| `FR-IMG-006` | MUST | No single weak heuristic shall alone force a fraudulent classification unless configured as a documented critical rule. | Unit tests prove weak signals aggregate without bypassing the risk policy. |

### Forensic derivatives

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-IMG-007` | SHOULD | Private diagnostic derivatives may be generated for authorised review. | Only owner/authorised staff can retrieve them and access is audited. |

### Model governance

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-001` | MUST | Every ML model shall be registered with type, version, artifact hash, feature/preprocessing schema, training commit and status. | An inference record can resolve the exact registered artifact and metadata. |

### Structured ML

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-002` | MUST | The structured classifier shall output class probabilities and a predicted risk class using a versioned feature pipeline. | Probabilities sum within tolerance; schema mismatch fails safely. |

### Image ML

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-003` | MUST | The image classifier shall output a tampering probability or an explicit unavailable/error state. | Absent/corrupt artifact produces PARTIAL analysis and no fabricated probability. |

### Model activation

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-004` | MUST | Only an authorised administrator shall activate or roll back a model version after readiness checks. | Activation requires an available hash-verified artifact and creates an audit event. |

### Evaluation honesty

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-005` | MUST | The system documentation shall report actual held-out metrics and label synthetic-only evaluations. | No placeholder metric is displayed as measured performance. |

### Reproducibility

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-006` | MUST | Training runs shall record dataset/split hashes, seed, dependencies and code commit. | A model card contains all required reproduction identifiers. |

### Data leakage prevention

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ML-007` | MUST | Dataset source groups shall be split before augmentation or preprocessing fit. | Automated data tests fail when one parent/source group appears across splits. |

### Reference import

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-VER-001` | MUST | An administrator shall be able to upload a reference-transaction CSV for preview and validation. | The preview reports valid/invalid rows before commit. |
| `FR-VER-002` | MUST | Committed imports shall record source label, file hash, uploader, row counts and import status. | Import batch is traceable and duplicate handling is deterministic. |

### Verification

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-VER-003` | MUST | The system shall locate a candidate reference record using canonical provider/reference fields when available. | A known seeded reference is found despite equivalent formatting. |
| `FR-VER-004` | MUST | The system shall compare amount, currency, relevant phone/name values and timestamp within versioned tolerances. | Field-level results show match/mismatch/not-available and the applied tolerance. |
| `FR-VER-005` | MUST | The system shall return VERIFIED, UNVERIFIED or MISMATCH and persist the evidence. | Each controlled scenario returns the expected status and comparison details. |
| `FR-VER-006` | MUST | The user interface shall state that prototype verification is based on stored/imported records. | No user-facing copy claims live MNO confirmation. |
| `FR-VER-007` | MUST | Fraud risk and verification status shall remain separate in storage, API and UI. | Tests assert both fields exist and one cannot overwrite/derive the other automatically. |

### Reuse detection

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-VER-008` | SHOULD | The system shall flag repeated reference or receipt reuse according to versioned rules. | Seeded reuse scenario produces a reason code and is visible to investigators. |

### Risk aggregation

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-RISK-001` | MUST | The system shall persist raw image, structured-model and rule components used in risk aggregation. | Final score is reproducible from persisted versioned inputs. |
| `FR-RISK-002` | MUST | The initial risk function shall be configurable and default to 40% image, 40% structured ML and 20% rules until calibrated. | Configuration/version is stored with the analysis; boundary tests pass. |
| `FR-RISK-003` | MUST | Risk thresholds shall be versioned and selected from validation evidence. | Each result stores the threshold version; later threshold changes do not alter history. |

### Explainability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-RISK-004` | MUST | Every result shall provide a small ordered list of plain-language reason codes grounded in evidence. | Displayed reasons map to persisted evidence and do not reveal hidden sensitive data. |
| `NFR-AUD-001` | MUST | Every automated result shall retain enough evidence, versions and timestamps to be reconstructed. | Golden test reconstructs score and reasons from persisted records. |

### Partial analysis

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-RISK-005` | MUST | A failed/unavailable subsystem shall produce a PARTIAL state and disclose missing evidence. | Available evidence persists; UI does not present full-confidence success. |

### Analysis idempotency

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-RISK-006` | MUST | Repeated analysis requests with the same idempotency key and unchanged input shall not create uncontrolled duplicate analyses. | Concurrent/retry test returns the same or a controlled existing run. |

### Historical immutability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-RISK-007` | MUST | Completed results shall not be silently recomputed when models, rules or thresholds change. | Historical detail uses stored snapshots; reanalysis creates a new linked run. |

### History

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-HIST-001` | MUST | Users shall see only their own paginated transaction history. | Pagination and ownership tests pass. |
| `FR-HIST-002` | MUST | History shall support date, risk, verification, provider and processing-status filters. | Combined filters return seeded expected rows. |

### Reports

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-HIST-003` | MUST | A user shall be able to download an authorised analysis summary with masked sensitive values and disclaimers. | Report content matches persisted result; cross-user download fails. |

### Notifications

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-HIST-004` | MUST | The system shall create in-app notifications for analysis completion, configured high-risk outcomes and case-status changes. | Each event creates at most the configured notification and links to the correct object. |
| `FR-HIST-005` | MUST | Users shall be able to view unread counts and mark their own notifications read. | Read state changes only for the authenticated user. |

### Report stability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-HIST-006` | MUST | Historical reports shall retain the result/model/rule versions used at the time. | Changing active models does not change an old report. |

### Fraud reporting

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-CASE-001` | MUST | A user shall be able to report one of their analysed transactions as suspicious with a category and description. | Valid report creates/links a case; foreign/unanalysed transaction fails. |

### Case management

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-CASE-002` | MUST | Configured high-risk results may create or queue a case without duplicating an existing open case. | Idempotency test prevents duplicate case rows. |
| `FR-CASE-003` | MUST | An investigator shall be able to inspect all authorised evidence and timeline information. | Case detail loads original result, OCR, image, ML, rule and verification evidence. |

### Case decision

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-CASE-004` | MUST | Confirm, dismiss and escalate actions shall require an investigator reason and valid state transition. | Missing reason/invalid transition fails; valid action is audited. |

### Evidence immutability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-CASE-005` | MUST | Human review shall not overwrite the original automated risk or verification result. | Database/API tests show separate reviewer-decision fields. |

### Case report

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-CASE-006` | SHOULD | An investigator shall be able to generate an authorised case report. | Report contains evidence summary, decision, reason and timestamps. |

### Dashboard

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ADM-005` | MUST | The portal shall display risk, verification, case and processing aggregates for an authorised date range. | Seeded aggregate tests match expected counts. |

### Audit

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ADM-006` | MUST | Administrators shall search audit events by actor, action, target, date and request ID. | Filters work without exposing secret payloads. |
| `FR-AUD-001` | MUST | Security-sensitive, evidential and privileged actions shall create append-only audit events. | Required action catalogue is covered by tests. |
| `FR-AUD-002` | MUST | Audit records shall include actor, action, target, timestamp, request ID and safe metadata. | Records are queryable and exclude passwords/tokens/raw secrets. |

### System status

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-ADM-007` | MUST | Administrators shall see readiness of database, storage, Tesseract, active models and optional notification adapters. | Disabled/unavailable dependency is reported accurately. |

### Error handling

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUD-003` | MUST | All API errors shall use a consistent envelope with code, message, request ID and field details when safe. | Contract tests cover validation, auth, conflict, not-found and server errors. |

### Observability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUD-004` | SHOULD | Analysis subsystem timings and failure states shall be recorded. | Completed/partial runs show stage timing and error code without sensitive stack traces. |

### Health

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `FR-AUD-005` | MUST | The API shall expose liveness, readiness and version endpoints. | Readiness reflects database/storage/model prerequisites; version identifies build. |

### Performance

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-PERF-001` | MUST | Login and normal history requests should complete within 2 seconds under defined prototype load. | Performance report records p50/p95 on specified hardware and identifies any exception. |
| `NFR-PERF-002` | MUST | A normal receipt analysis should complete within about 10 seconds under defined prototype conditions. | Measured stage timings and p95 are reported; inability is documented, not hidden. |

### Scalability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-PERF-003` | SHOULD | The prototype logical design shall support 25 concurrent analyses and 100,000 stored analysis records without schema redesign. | Load/query tests record results and indexes/query plans for critical paths. |

### Security

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-SEC-001` | MUST | All non-local traffic shall use HTTPS and secure session/cookie settings. | Staging security check confirms HTTPS and secure flags. |
| `NFR-SEC-002` | MUST | Secrets shall be provided through environment/secret management and excluded from client bundles and Git. | Secret scan and bundle inspection pass. |
| `NFR-SEC-003` | MUST | Receipt files shall be treated as hostile and stored privately. | Upload-abuse and private-access tests pass. |

### Reliability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-REL-001` | SHOULD | The deployed prototype shall target 99% availability during agreed operating hours. | Monitoring/deployment report states measured availability or current limitation. |
| `NFR-REL-002` | MUST | Database writes that form one domain action shall be transactional where required. | Failure injection shows no invalid half-completed domain state. |

### Accuracy

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-ACC-001` | SHOULD | The OCR pipeline shall target at least 90% required-field accuracy on the declared evaluation set. | Evaluation script calculates actual field accuracy and dataset scope. |
| `NFR-ACC-002` | SHOULD | The fraud classifier shall target macro F1 of at least 0.85 on a leakage-controlled held-out test set. | Evaluation report calculates actual macro F1 and per-class metrics; synthetic-only scope is labelled. |

### Usability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-USE-001` | MUST | A signed-in user shall begin receipt analysis in no more than three principal actions. | Documented usability walkthrough counts principal actions. |

### Accessibility

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-USE-002` | MUST | Status shall not be communicated by colour alone and critical interfaces shall support accessible labels and keyboard/focus behaviour. | Manual/automated accessibility review passes documented criteria. |

### Maintainability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-MNT-001` | MUST | Routes, services, repositories, persistence, storage and ML components shall be modular and independently testable. | Architecture review and tests show no direct UI-to-database or route-to-model-file coupling. |

### Interoperability

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-INT-001` | MUST | The platform shall expose versioned JSON REST APIs and portable import/export formats. | All routes are under `/api/v1`; OpenAPI and CSV contracts are versioned. |

### Backup/recovery

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-BACK-001` | MUST | Database and private storage backup/restore procedures shall be documented and tested on staging/local data. | A restore rehearsal is recorded in the QA report. |

### Compatibility

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-COMP-001` | SHOULD | The mobile app shall support the agreed current Android test range and the admin portal current major evergreen browsers. | Final compatibility matrix records actual tested versions. |

### Data governance

| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| `NFR-DATA-001` | MUST | Private real receipt data shall not be committed to Git and shall have documented consent/licence and retention status. | Repository scan passes; dataset card records source/permission/retention. |


## 4. Business rules

1. The user owns the transaction they create; ownership cannot be transferred through a client request.
2. One receipt original belongs to one submitted transaction. Reanalysis creates a new analysis run, not a new original.
3. Corrected OCR fields are a new confirmed snapshot; raw OCR remains immutable.
4. Reference matching is based on the confirmed snapshot, not unreviewed raw OCR.
5. A `MISMATCH` is verification evidence and may contribute to fraud risk through a versioned rule, but does not directly overwrite risk class.
6. An `UNVERIFIED` result means insufficient reference evidence, not fraud.
7. The active model/rule/template version is captured at analysis start.
8. A completed analysis is historical evidence. Later configuration changes affect only new analyses or an explicit reanalysis.
9. A reviewer decision is a separate conclusion with actor, reason and timestamp.
10. Audit events and evidential outputs are append-only except for legally required retention processes.
11. Full phone numbers, transaction references and receipt images are shown only where role and purpose justify it.
12. External delivery failure never removes the in-app notification or the underlying result.
13. Import rows are never silently coerced into a different amount/reference; normalisation and validation are visible.
14. Every object returned by the API is scoped by authenticated role and ownership, never merely by a client-supplied user ID.

## 5. State-transition requirements

### Transaction/analysis

| Current state | Allowed next state | Trigger |
|---|---|---|
| `DRAFT` | `UPLOADED` | Original passes upload validation |
| `UPLOADED` | `OCR_READY`, `FAILED` | OCR completes or irrecoverably fails |
| `OCR_READY` | `OCR_REVIEWED` | User confirms/corrects fields |
| `OCR_REVIEWED` | `QUEUED`, `PROCESSING` | Analysis request accepted |
| `QUEUED` | `PROCESSING`, `CANCELLED` | Worker starts or cancellation is allowed |
| `PROCESSING` | `COMPLETED`, `PARTIAL`, `FAILED` | Orchestration finishes |
| `COMPLETED` | none | New analysis requires explicit reanalysis record |
| `PARTIAL` | none or explicit reanalysis | Preserve original partial evidence |
| `FAILED` | explicit retry/reanalysis | Never mutate into a hidden success |

### Case

| Current state | Allowed next state |
|---|---|
| `OPEN` | `IN_REVIEW`, `DISMISSED` |
| `IN_REVIEW` | `CONFIRMED`, `DISMISSED`, `ESCALATED` |
| `CONFIRMED` | audited reopen only |
| `DISMISSED` | audited reopen only |
| `ESCALATED` | audited follow-up or closure policy |

Invalid transitions return HTTP 409 with the standard error envelope and create no partial domain update.

## 6. Requirement acceptance process

A requirement is marked `Done` only when:

- implementation path is recorded;
- relevant database/API/UI artefacts are recorded;
- automated or manual test evidence is named;
- the test has actually run at the reported SHA;
- no unresolved blocker contradicts the requirement;
- user-facing wording matches the scope boundaries.

A requirement may be marked `Blocked` only with a blocker owner, reason, impact, safe fallback and next action.

<!-- END FILE: 02_SYSTEM_REQUIREMENTS_SPECIFICATION.md -->


---

<!-- BEGIN FILE: 03_ARCHITECTURE_AND_REPOSITORY_SPEC.md -->

# 03 — Architecture and Repository Specification

## 1. Architectural style

MoMo-FDVS uses a layered client-server architecture with an explicit background analysis worker:

1. **Mobile presentation layer:** Expo/React Native user application.
2. **Web presentation layer:** React/Vite administrator and investigator portal.
3. **API/application layer:** Flask REST API handling authentication, validation, policies, orchestration requests and read models.
4. **Analysis worker:** Python process that claims queued analysis runs from PostgreSQL and executes OCR, image, ML, rule and verification services.
5. **Data layer:** PostgreSQL plus private object storage.
6. **AI/verification layer:** Tesseract/OpenCV, TensorFlow/Keras, scikit-learn, rules and reference matching.

The analysis worker is separate from web request workers so CPU-heavy receipt processing does not block login/history/admin traffic. To avoid adding a mandatory Redis dependency, the prototype uses a PostgreSQL-backed queue based on `analysis_runs` and safe row claiming (`FOR UPDATE SKIP LOCKED` or the SQLAlchemy equivalent). An adapter boundary permits later replacement with Celery/RQ without changing domain services.

## 2. Target monorepo

```text
/
├── AGENTS.md
├── README.md
├── README_FIRST.md
├── IMPLEMENTATION_STATUS.md
├── DECISION_LOG.md
├── CHANGELOG.md
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .env.example
├── docker-compose.yml
├── package.json                 # optional root workspace scripts
├── pnpm-workspace.yaml          # or chosen pinned workspace manager
├── apps/
│   ├── mobile/
│   │   ├── app/                 # Expo Router routes
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   ├── hooks/
│   │   │   ├── lib/
│   │   │   ├── state/
│   │   │   ├── theme/
│   │   │   └── types/
│   │   ├── assets/
│   │   ├── tests/
│   │   ├── app.config.ts
│   │   └── package.json
│   └── admin/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   ├── hooks/
│       │   ├── lib/
│       │   ├── routes/
│       │   ├── theme/
│       │   └── types/
│       ├── tests/
│       ├── playwright/
│       ├── vite.config.ts
│       └── package.json
├── packages/
│   ├── api-client/              # generated TypeScript client/types
│   ├── eslint-config/
│   └── tsconfig/
├── services/
│   └── api/
│       ├── pyproject.toml
│       ├── migrations/
│       ├── src/momo_fdvs/
│       │   ├── __init__.py       # create_app
│       │   ├── config.py
│       │   ├── extensions.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   ├── cli.py
│       │   ├── api/
│       │   │   └── v1/
│       │   ├── auth/
│       │   ├── domain/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── policies/
│       │   ├── storage/
│       │   ├── analysis/
│       │   ├── ocr/
│       │   ├── image_analysis/
│       │   ├── verification/
│       │   ├── risk/
│       │   ├── ml_runtime/
│       │   ├── reports/
│       │   └── worker/
│       └── tests/
│           ├── unit/
│           ├── integration/
│           ├── contract/
│           ├── security/
│           └── fixtures/
├── ml/
│   ├── pyproject.toml
│   ├── configs/
│   ├── data/
│   ├── notebooks/               # exploration only; production logic elsewhere
│   ├── src/momo_ml/
│   │   ├── data/
│   │   ├── features/
│   │   ├── structured/
│   │   ├── image_model/
│   │   ├── evaluation/
│   │   └── registry/
│   ├── tests/
│   └── reports/
├── infra/
│   ├── docker/
│   ├── render/                  # provider-default manifests, if selected
│   ├── nginx/                   # optional
│   └── storage/
├── docs/
│   ├── implementation/
│   ├── architecture/
│   ├── api/
│   ├── diagrams/
│   ├── model-cards/
│   ├── dataset-cards/
│   ├── qa/
│   └── deployment/
├── scripts/
│   ├── bootstrap.py
│   ├── doctor.py
│   ├── verify.py
│   ├── check_secrets.py
│   ├── generate_api_client.py
│   ├── seed_demo.py
│   └── export_diagrams.py
└── samples/
```

The exact workspace manager may be npm, pnpm or another approved tool, but it must be pinned and used consistently. Do not commit two competing lockfiles.

## 3. Backend package responsibilities

### 3.1 `api/v1`

Blueprints/controllers only:

- parse and validate request;
- call a policy check;
- invoke a service;
- serialise the response;
- map known exceptions to the standard error envelope.

Controllers must not contain SQL queries, image-processing code, model loading or business-score calculations.

### 3.2 `schemas`

Flask-Smorest/Marshmallow request and response schemas, or the documented equivalent selected during P01. Schemas define:

- request validation;
- response projection;
- OpenAPI documentation;
- field masking at the response boundary where appropriate.

The generated OpenAPI document is the client contract. Breaking changes require a version or explicit migration.

### 3.3 `services`

Application use cases and transaction boundaries:

- register/login/reset;
- create receipt submission;
- confirm OCR review;
- queue analysis;
- list history;
- create report/case;
- administer versions/imports.

Services may coordinate repositories and domain components but must not depend on Flask global request objects.

### 3.4 `repositories`

Database access only:

- typed query methods;
- ownership-aware lookup helpers;
- pagination;
- aggregate queries;
- row locking/claiming;
- no HTTP concepts.

### 3.5 `domain`

Pure domain enums, value objects, state-transition rules, reason-code catalogue and errors. Domain functions should be testable without Flask or a database where practical.

### 3.6 `policies`

Central server-side authorisation:

- role/capability rules;
- object ownership;
- investigator assignment/queue access;
- sensitive-field projection;
- last-administrator protection.

A controller calling a repository directly and forgetting a policy is not acceptable. Use service methods that require an authenticated principal.

### 3.7 `storage`

Interface:

```python
class PrivateObjectStorage(Protocol):
    def put(self, *, key: str, stream: BinaryIO, content_type: str) -> StoredObject: ...
    def open(self, *, key: str) -> BinaryIO: ...
    def delete(self, *, key: str) -> None: ...
    def exists(self, *, key: str) -> bool: ...
    def stat(self, *, key: str) -> ObjectMetadata: ...
```

Implementations:

- `LocalPrivateStorage` for development/tests;
- `S3PrivateStorage` for staging/production.

Neither implementation returns a permanent public URL. Downloads are streamed through an authorised endpoint or use a short-lived signed URL after policy checks.

### 3.8 `ocr`

Pure or service-style functions for:

- image quality;
- preprocessing variants;
- Tesseract invocation;
- token data;
- template detection;
- field parsing/normalisation;
- confidence/warnings.

Tesseract process failures must be translated to a controlled domain error.

### 3.9 `image_analysis`

Versioned feature extractors. Each extractor returns a common evidence structure rather than directly assigning the final class.

### 3.10 `ml_runtime`

- artifact resolver;
- SHA-256 verification;
- structured model adapter;
- TensorFlow model adapter;
- version/schema compatibility;
- unavailable/corrupt model result.

Loading is lazy and cached per process, but activation changes must invalidate or reload safely.

### 3.11 `verification`

Reference candidate lookup and field comparison. The module knows nothing about MNO claims; its source is an authorised local/import adapter.

### 3.12 `risk`

- rule evaluation;
- component-probability normalisation;
- configurable weighted score;
- threshold mapping;
- top reason selection;
- partial-evidence policy.

### 3.13 `worker`

Worker loop:

1. check database/storage/model readiness;
2. claim one `QUEUED` run atomically;
3. set `PROCESSING`, worker ID and heartbeat;
4. execute orchestrator stages;
5. persist each stage and evidence transactionally;
6. set `COMPLETED`, `PARTIAL` or `FAILED`;
7. create in-app notification;
8. release resources;
9. requeue or fail stale jobs according to retry policy.

Use bounded retries for transient failures and no automatic retry for invalid/corrupt input. Store a stable error code, not an internal stack trace, in user-visible fields.

## 4. Flask and API conventions

- Use an application factory: `create_app(config_name=None)`.
- Initialise extensions in `extensions.py`.
- Register versioned blueprints under `/api/v1`.
- Keep CLI commands available through the app factory.
- Configuration comes from environment variables validated at startup.
- Production startup uses Gunicorn or the selected WSGI server; never Flask's development server.
- Use one database session per request/worker unit of work.
- Always rollback after an exception.
- Return UTC timestamps in ISO 8601 with `Z`/offset.
- Use UUID strings in external APIs.
- Use snake_case JSON consistently unless a documented generated-client policy chooses otherwise.
- Use decimal-safe serialisation for money; do not use binary floating point for persisted amounts.
- Support `Idempotency-Key` on upload, analyse, report and reference-import commit routes.
- Attach `X-Request-ID` to every response and log entry.
- Pagination uses opaque/simple cursor or validated page/limit consistently. The initial contract may use `page`/`page_size` with a maximum of 100.
- Never return ORM objects directly.

## 5. Standard response conventions

### 5.1 Success resource

```json
{
  "data": {
    "id": "uuid",
    "type": "transaction",
    "attributes": {}
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

A simpler `{"data": ..., "meta": ...}` contract is acceptable and is used throughout `05_API_CONTRACT.md`. Do not mix unrelated envelope styles.

### 5.2 Error

```json
{
  "error": {
    "code": "RECEIPT_INVALID_IMAGE",
    "message": "The selected file is not a supported receipt image.",
    "field_errors": {
      "receipt": ["Upload a JPEG, PNG or WEBP image."]
    },
    "request_id": "uuid"
  }
}
```

- 400: malformed request/business validation;
- 401: missing/invalid authentication;
- 403: authenticated but not permitted;
- 404: object not found or deliberately hidden by ownership policy;
- 409: state/idempotency/version conflict;
- 413: payload too large;
- 415: unsupported media;
- 422: schema/semantic validation where chosen consistently;
- 429: rate limit;
- 500: unexpected server error with generic public message;
- 503: required dependency unavailable.

## 6. Generated TypeScript client

- Export the OpenAPI document during backend CI.
- Generate TypeScript types/client into `packages/api-client`.
- Commit generated code only if the project chooses a deterministic generator and CI checks that it is current.
- Mobile and admin must use this client or shared generated types. Hand-written duplicate response types are prohibited for core resources.
- A contract change must update:
  1. backend schema;
  2. OpenAPI snapshot;
  3. generated client;
  4. client code;
  5. contract tests.

## 7. Analysis job architecture

### 7.1 Enqueue

`POST /api/v1/transactions/{id}/analyses`:

- verifies ownership/state;
- resolves idempotency key;
- snapshots active configuration IDs;
- creates `analysis_run` with `QUEUED`;
- returns `202 Accepted` and polling URL.

### 7.2 Claim

Worker query selects the oldest eligible queued row and locks it without blocking other workers. Store:

- `claimed_by`;
- `claimed_at`;
- `heartbeat_at`;
- `attempt_count`.

### 7.3 Recovery

A maintenance command identifies stale `PROCESSING` jobs whose heartbeat exceeded the configured interval:

- requeue transient/infrastructure failures below retry limit;
- mark failed when attempts exhausted;
- never duplicate completed evidence;
- audit recovery.

### 7.4 Progress

Persist named stages:

- `PREPARE_INPUT`;
- `OCR_SNAPSHOT`;
- `REFERENCE_VERIFICATION`;
- `IMAGE_FEATURES`;
- `CNN_INFERENCE`;
- `STRUCTURED_FEATURES`;
- `STRUCTURED_INFERENCE`;
- `RULE_EVALUATION`;
- `RISK_AGGREGATION`;
- `FINALISE`.

The mobile app polls the analysis resource using increasing intervals while active. It displays friendly stage text without exposing internal sensitive details.

## 8. Configuration hierarchy

1. code defaults safe for tests only;
2. environment variables;
3. database versioned configuration for templates/rules/thresholds/models;
4. per-run immutable snapshot.

Do not store secrets in the versioned configuration tables. Secrets remain in environment/secret management.

Important environment groups:

- application identity/build;
- database;
- JWT/session;
- CORS/CSRF;
- private storage;
- upload limits;
- Tesseract path/language;
- model artifact root;
- worker/retry;
- notification adapters;
- masking/retention;
- observability.

## 9. Money, phone and time

- Persist money as `NUMERIC(18,2)` or a documented compatible precision plus currency code.
- Use `Decimal` in Python.
- Store canonical Ghana phone format such as E.164 `+233...` where enough information exists; preserve masked/raw evidence separately when required.
- Store all timestamps as timezone-aware UTC.
- Retain the original OCR date/time string and the normalised timestamp plus a warning when timezone is inferred.

## 10. Logging and audit separation

### Operational logs

For debugging and metrics; may be rotated/deleted. Include request ID and safe context. Exclude receipt text, full phone/reference values, passwords, tokens and raw model features containing identifiers.

### Audit events

Persistent evidence of important actions. Store:

- actor ID and role;
- action code;
- target type/ID;
- request ID;
- outcome;
- safe metadata;
- UTC timestamp;
- source IP/user-agent hash or minimised representation according to privacy policy.

Audit events are append-only. A privileged export of audit data is itself audited.

## 11. Dependency readiness

`/health` proves the process is alive. `/ready` evaluates:

- database query;
- storage read/write/delete probe or configured non-destructive check;
- Tesseract executable/version;
- active structured model artifact;
- active CNN artifact;
- optional notification adapter.

Readiness may return a component matrix. The API itself may remain ready for non-analysis routes while an ML component is degraded; document the policy and expose `analysis_available` separately.

## 12. Engineering diagrams to maintain

Codex must maintain code-aligned engineering diagrams:

- deployment/container diagram;
- analysis data-flow diagram;
- state diagrams;
- implemented ERD;
- sequence diagrams for upload/OCR, analysis and case review.

Use Mermaid for repository maintainability where helpful. For academic submission, reproduce/export standards-based UML/ER diagrams with clear routing, no crossing through boxes/ellipses and correct multiplicities.

<!-- END FILE: 03_ARCHITECTURE_AND_REPOSITORY_SPEC.md -->


---

<!-- BEGIN FILE: 04_DATABASE_AND_STORAGE_SPEC.md -->

# 04 — Database and Private Storage Specification

## 1. Database principles

- PostgreSQL is the source of truth for structured state, evidence metadata, versions, permissions and audit history.
- Private object storage is the source of truth for original receipt bytes, derived forensic images, generated reports and large model artifacts.
- The database stores object keys and hashes, never an assumption that a local public URL is permanent.
- UUIDs are used for externally visible primary keys.
- All timestamps are timezone-aware UTC.
- Money uses fixed precision (`NUMERIC`) and an explicit three-letter currency code.
- JSONB is used for versioned evidence whose shape evolves, but core searchable/filterable values remain typed columns.
- Completed evidence rows are append-only. Corrections, reanalysis and human decisions create new linked rows.
- Foreign keys, uniqueness, checks and state transitions are enforced in both application logic and database constraints where practical.
- Migrations are the only supported way to alter production schema.

## 2. Extensions and conventions

Recommended PostgreSQL extensions:

- `pgcrypto` for UUID generation if database-generated UUIDs are selected;
- `citext` for case-insensitive unique email;
- optionally `pg_trgm` for controlled fuzzy name comparison/search.

Conventions:

- table/column names: snake_case;
- primary key: `id UUID`;
- timestamps: `created_at`, `updated_at`, plus domain timestamps;
- enum-like values: PostgreSQL enum or `VARCHAR` plus CHECK; choose one consistent migration-friendly policy;
- JSONB default: `{}` or `[]` only where an empty object/list is meaningful;
- optimistic locking/version number on mutable configuration resources;
- no `ON DELETE CASCADE` from a user to immutable evidence unless the retention policy explicitly requires it.

## 3. Identity and access tables

### 3.1 `users`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `email` | CITEXT | unique, not null |
| `password_hash` | VARCHAR(255) | not null |
| `full_name` | VARCHAR(150) | not null |
| `phone_e164` | VARCHAR(20) | nullable, masked in most views |
| `status` | VARCHAR(20) | `ACTIVE`, `DISABLED`, `PENDING`; indexed |
| `email_verified_at` | TIMESTAMPTZ | nullable |
| `last_login_at` | TIMESTAMPTZ | nullable |
| `password_changed_at` | TIMESTAMPTZ | not null |
| `token_version` | INTEGER | not null default 1 |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |

Do not store a plaintext password, reset token or current access token.

### 3.2 `roles`

| Column | Type | Constraints |
|---|---|---|
| `code` | VARCHAR(30) | PK: `USER`, `ADMIN`, `INVESTIGATOR` |
| `description` | VARCHAR(255) | not null |

### 3.3 `user_roles`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | FK users.id |
| `role_code` | VARCHAR(30) | FK roles.code |
| `granted_by` | UUID | FK users.id, nullable only for bootstrap |
| `granted_at` | TIMESTAMPTZ | not null |

Composite PK `(user_id, role_code)`. The service layer prevents removal of the last active administrator.

### 3.4 `admin_profiles`

Optional profile data for staff.

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | PK/FK users.id |
| `staff_reference` | VARCHAR(100) | nullable, unique when present |
| `department` | VARCHAR(100) | nullable |
| `notes` | TEXT | restricted, nullable |

### 3.5 `refresh_sessions`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `family_id` | UUID | indexed, supports rotation/reuse detection |
| `token_hash` | CHAR(64) | unique, not null |
| `expires_at` | TIMESTAMPTZ | indexed |
| `revoked_at` | TIMESTAMPTZ | nullable |
| `revoke_reason` | VARCHAR(50) | nullable |
| `replaced_by_id` | UUID | self FK, nullable |
| `user_agent_hash` | CHAR(64) | nullable |
| `ip_hash` | CHAR(64) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Only the token hash/fingerprint is stored.

### 3.6 `password_reset_tokens`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `token_hash` | CHAR(64) | unique, not null |
| `expires_at` | TIMESTAMPTZ | not null |
| `used_at` | TIMESTAMPTZ | nullable |
| `requested_ip_hash` | CHAR(64) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

## 4. Receipt submission and OCR tables

### 4.1 `transactions`

This represents a user-submitted transaction/receipt analysis subject, not an MNO reference record.

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `status` | VARCHAR(30) | validated processing state, indexed |
| `provider_code` | VARCHAR(50) | nullable, indexed |
| `display_reference_masked` | VARCHAR(100) | nullable |
| `latest_analysis_run_id` | UUID | nullable deferred FK analysis_runs.id |
| `created_at` | TIMESTAMPTZ | not null, indexed |
| `updated_at` | TIMESTAMPTZ | not null |

Index `(user_id, created_at DESC)` and filter-supporting indexes for status/provider.

### 4.2 `receipts`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, unique |
| `object_key` | VARCHAR(500) | unique, not null |
| `original_filename` | VARCHAR(255) | display only, sanitised |
| `media_type` | VARCHAR(50) | not null |
| `size_bytes` | BIGINT | positive check |
| `width_px` | INTEGER | positive check |
| `height_px` | INTEGER | positive check |
| `sha256` | CHAR(64) | indexed |
| `perceptual_hash` | VARCHAR(32) | indexed |
| `quality_score` | NUMERIC(5,4) | nullable |
| `quality_warnings` | JSONB | not null default `[]` |
| `storage_version` | VARCHAR(30) | not null |
| `created_at` | TIMESTAMPTZ | not null |

Do not make `sha256` globally unique: two users may submit the same receipt. Detection is an analysis concern.

### 4.3 `receipt_derivatives`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `receipt_id` | UUID | FK receipts.id, indexed |
| `kind` | VARCHAR(50) | `THUMBNAIL`, `OCR_VARIANT`, `ELA`, `NOISE_MAP`, `HEATMAP`, etc. |
| `version` | VARCHAR(50) | not null |
| `object_key` | VARCHAR(500) | unique, not null |
| `sha256` | CHAR(64) | not null |
| `metadata` | JSONB | settings/dimensions; not null default `{}` |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(receipt_id, kind, version, sha256)` where practical.

### 4.4 `receipt_templates`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `provider_code` | VARCHAR(50) | indexed |
| `name` | VARCHAR(150) | not null |
| `version` | VARCHAR(50) | not null |
| `status` | VARCHAR(20) | `DRAFT`, `ACTIVE`, `RETIRED` |
| `config` | JSONB | expected anchors/regions/regex/config |
| `parser_version` | VARCHAR(100) | not null |
| `created_by` | UUID | FK users.id |
| `activated_by` | UUID | FK users.id, nullable |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |
| `row_version` | INTEGER | optimistic locking |

Unique `(provider_code, version)`. At most one active template per provider/parser policy, enforced by partial unique index or service transaction.

### 4.5 `ocr_results`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `receipt_id` | UUID | FK receipts.id, indexed |
| `template_id` | UUID | FK receipt_templates.id, nullable |
| `engine_name` | VARCHAR(50) | e.g. `tesseract` |
| `engine_version` | VARCHAR(100) | not null |
| `pipeline_version` | VARCHAR(100) | not null |
| `selected_variant` | VARCHAR(50) | not null |
| `raw_text` | TEXT | not null default empty |
| `token_data` | JSONB | text/bounds/confidence |
| `extracted_fields` | JSONB | original parser output |
| `field_confidences` | JSONB | per-field 0..1 |
| `warnings` | JSONB | not null default `[]` |
| `required_field_accuracy_hint` | NUMERIC(5,4) | nullable; not a final evaluation metric |
| `created_at` | TIMESTAMPTZ | not null |

Re-running OCR creates another row. Do not update the original result in place.

### 4.6 `ocr_confirmations`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `ocr_result_id` | UUID | FK ocr_results.id, indexed |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `confirmed_fields` | JSONB | canonical field snapshot |
| `corrections` | JSONB | old/new/reason per field |
| `confirmed_by` | UUID | FK users.id |
| `confirmed_at` | TIMESTAMPTZ | not null |
| `schema_version` | VARCHAR(50) | not null |

One transaction may have multiple confirmations only when an explicit re-review creates a new version. The analysis run references exactly one confirmation.

## 5. Analysis configuration and execution tables

### 5.1 `model_versions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `model_type` | VARCHAR(30) | `STRUCTURED`, `IMAGE` |
| `name` | VARCHAR(150) | not null |
| `version` | VARCHAR(100) | not null |
| `status` | VARCHAR(20) | `DRAFT`, `READY`, `ACTIVE`, `RETIRED`, `FAILED` |
| `artifact_uri` | VARCHAR(1000) | private location |
| `artifact_sha256` | CHAR(64) | not null |
| `input_schema_hash` | CHAR(64) | not null |
| `preprocessing_version` | VARCHAR(100) | not null |
| `framework_versions` | JSONB | Python/library versions |
| `metrics` | JSONB | measured metrics and evaluation scope |
| `dataset_manifest_hash` | CHAR(64) | nullable |
| `split_hash` | CHAR(64) | nullable |
| `training_commit_sha` | VARCHAR(40) | nullable |
| `model_card_key` | VARCHAR(500) | nullable |
| `created_by` | UUID | FK users.id, nullable for CLI import |
| `activated_by` | UUID | FK users.id, nullable |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(model_type, name, version)`. Partial unique index for one active version per model type/name.

### 5.2 `fraud_rule_sets`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `version` | VARCHAR(100) | unique |
| `status` | VARCHAR(20) | draft/active/retired |
| `risk_weights` | JSONB | includes image/ML/rule weights |
| `thresholds` | JSONB | class thresholds |
| `description` | TEXT | not null |
| `created_by` | UUID | FK users.id |
| `activated_by` | UUID | nullable FK |
| `activated_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `row_version` | INTEGER | not null |

### 5.3 `fraud_rules`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `rule_set_id` | UUID | FK fraud_rule_sets.id, indexed |
| `code` | VARCHAR(100) | not null |
| `description` | TEXT | not null |
| `severity` | VARCHAR(20) | informational/low/medium/high/critical |
| `condition` | JSONB | versioned declarative rule definition |
| `score_contribution` | NUMERIC(6,4) | non-negative |
| `reason_template` | TEXT | not null |
| `enabled` | BOOLEAN | not null |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(rule_set_id, code)`.

### 5.4 `analysis_runs`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `ocr_confirmation_id` | UUID | FK ocr_confirmations.id |
| `status` | VARCHAR(20) | `QUEUED`, `PROCESSING`, `COMPLETED`, `PARTIAL`, `FAILED`, `CANCELLED`; indexed |
| `current_stage` | VARCHAR(50) | indexed |
| `template_id` | UUID | snapshot FK, nullable |
| `rule_set_id` | UUID | FK fraud_rule_sets.id |
| `structured_model_id` | UUID | FK model_versions.id, nullable |
| `image_model_id` | UUID | FK model_versions.id, nullable |
| `idempotency_key_hash` | CHAR(64) | indexed |
| `request_fingerprint` | CHAR(64) | not null |
| `attempt_count` | INTEGER | not null default 0 |
| `claimed_by` | VARCHAR(100) | nullable |
| `claimed_at` | TIMESTAMPTZ | nullable |
| `heartbeat_at` | TIMESTAMPTZ | nullable |
| `queued_at` | TIMESTAMPTZ | not null |
| `started_at` | TIMESTAMPTZ | nullable |
| `completed_at` | TIMESTAMPTZ | nullable |
| `risk_score` | NUMERIC(6,3) | check 0..100, nullable |
| `risk_class` | VARCHAR(20) | nullable, indexed |
| `component_scores` | JSONB | raw image/structured/rule values |
| `top_reasons` | JSONB | ordered reason codes/text |
| `configuration_snapshot` | JSONB | immutable settings not covered by FKs |
| `error_code` | VARCHAR(100) | nullable |
| `error_message_safe` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(transaction_id, idempotency_key_hash)` when the key is present. Index for queue claim `(status, queued_at)`.

### 5.5 `analysis_stage_runs`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `stage` | VARCHAR(50) | not null |
| `status` | VARCHAR(20) | queued/running/completed/skipped/failed |
| `attempt` | INTEGER | not null |
| `started_at` | TIMESTAMPTZ | nullable |
| `completed_at` | TIMESTAMPTZ | nullable |
| `duration_ms` | INTEGER | nullable |
| `error_code` | VARCHAR(100) | nullable |
| `details` | JSONB | safe stage metadata |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, stage, attempt)`.

### 5.6 `image_analyses`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, unique |
| `algorithm_version` | VARCHAR(100) | not null |
| `metadata_evidence` | JSONB | not null |
| `duplicate_evidence` | JSONB | not null |
| `compression_evidence` | JSONB | not null |
| `noise_evidence` | JSONB | not null |
| `layout_evidence` | JSONB | not null |
| `quality_evidence` | JSONB | not null |
| `engineered_features` | JSONB | versioned structured values |
| `image_tamper_probability` | NUMERIC(7,6) | nullable, 0..1 |
| `warnings` | JSONB | not null default `[]` |
| `created_at` | TIMESTAMPTZ | not null |

### 5.7 `fraud_predictions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `model_version_id` | UUID | FK model_versions.id |
| `prediction_type` | VARCHAR(30) | `STRUCTURED`, `IMAGE` |
| `predicted_class` | VARCHAR(20) | nullable |
| `probabilities` | JSONB | class/probability map |
| `feature_schema_hash` | CHAR(64) | not null |
| `feature_snapshot` | JSONB | identifier-minimised |
| `inference_ms` | INTEGER | nullable |
| `status` | VARCHAR(20) | success/unavailable/error |
| `error_code` | VARCHAR(100) | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, prediction_type)`.

### 5.8 `rule_evaluations`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, indexed |
| `rule_id` | UUID | FK fraud_rules.id |
| `triggered` | BOOLEAN | not null |
| `observed_value` | JSONB | safe feature/value |
| `score_contribution` | NUMERIC(6,4) | not null |
| `reason_code` | VARCHAR(100) | not null |
| `reason_text` | TEXT | not null |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(analysis_run_id, rule_id)`.

## 6. Reference verification tables

### 6.1 `reference_import_batches`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `source_label` | VARCHAR(200) | not null |
| `original_filename` | VARCHAR(255) | not null |
| `file_sha256` | CHAR(64) | indexed |
| `object_key` | VARCHAR(500) | private original import, nullable by retention policy |
| `status` | VARCHAR(20) | uploaded/validated/committed/failed |
| `total_rows` | INTEGER | non-negative |
| `valid_rows` | INTEGER | non-negative |
| `invalid_rows` | INTEGER | non-negative |
| `invalid_report_key` | VARCHAR(500) | nullable |
| `uploaded_by` | UUID | FK users.id |
| `validated_at` | TIMESTAMPTZ | nullable |
| `committed_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Idempotency policy may make `(source_label, file_sha256)` unique.

### 6.2 `reference_transactions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `import_batch_id` | UUID | FK reference_import_batches.id, indexed |
| `provider_code` | VARCHAR(50) | not null, indexed |
| `transaction_reference` | VARCHAR(150) | canonical, not null, indexed |
| `amount` | NUMERIC(18,2) | non-negative |
| `currency` | CHAR(3) | not null default `GHS` |
| `sender_name_normalised` | VARCHAR(200) | nullable |
| `sender_phone_e164` | VARCHAR(20) | nullable |
| `receiver_name_normalised` | VARCHAR(200) | nullable |
| `receiver_phone_e164` | VARCHAR(20) | nullable |
| `occurred_at` | TIMESTAMPTZ | nullable, indexed |
| `transaction_status` | VARCHAR(50) | nullable |
| `source_system_id` | VARCHAR(150) | nullable |
| `raw_row` | JSONB | restricted original row |
| `created_at` | TIMESTAMPTZ | not null |

Unique policy: `(provider_code, transaction_reference, source_system_id)` when source ID exists; otherwise `(provider_code, transaction_reference, import_batch_id)`.

### 6.3 `verification_results`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `analysis_run_id` | UUID | FK analysis_runs.id, unique |
| `reference_transaction_id` | UUID | FK reference_transactions.id, nullable |
| `status` | VARCHAR(20) | `VERIFIED`, `UNVERIFIED`, `MISMATCH`; indexed |
| `verifier_version` | VARCHAR(100) | not null |
| `candidate_method` | VARCHAR(100) | not null |
| `field_comparisons` | JSONB | match/mismatch/NA, tolerances and masked values |
| `matched_field_count` | INTEGER | non-negative |
| `mismatched_field_count` | INTEGER | non-negative |
| `warnings` | JSONB | not null default `[]` |
| `created_at` | TIMESTAMPTZ | not null |

## 7. Cases, reports, notifications and audit

### 7.1 `fraud_cases`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `transaction_id` | UUID | FK transactions.id, indexed |
| `source` | VARCHAR(30) | `USER_REPORT`, `AUTO_HIGH_RISK`, `ADMIN` |
| `reporter_id` | UUID | FK users.id, nullable |
| `category` | VARCHAR(100) | not null |
| `description` | TEXT | nullable |
| `status` | VARCHAR(20) | indexed |
| `assigned_to` | UUID | FK users.id, nullable, indexed |
| `opened_at` | TIMESTAMPTZ | not null |
| `closed_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |
| `updated_at` | TIMESTAMPTZ | not null |

Partial unique index prevents more than one open/in-review case for the same transaction and configured source policy.

### 7.2 `case_events`

Append-only timeline.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID | FK fraud_cases.id, indexed |
| `actor_id` | UUID | FK users.id |
| `event_type` | VARCHAR(50) | opened/assigned/note/status/decision/reopened |
| `from_status` | VARCHAR(20) | nullable |
| `to_status` | VARCHAR(20) | nullable |
| `reason` | TEXT | mandatory for decision |
| `metadata` | JSONB | safe |
| `created_at` | TIMESTAMPTZ | not null |

### 7.3 `case_decisions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID | FK fraud_cases.id, indexed |
| `decided_by` | UUID | FK users.id |
| `outcome` | VARCHAR(20) | confirmed/dismissed/escalated |
| `reason` | TEXT | not null |
| `supersedes_id` | UUID | self FK, nullable |
| `created_at` | TIMESTAMPTZ | not null |

The original automated analysis is not updated.

### 7.4 `report_artifacts`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `report_type` | VARCHAR(30) | analysis/case/operations |
| `owner_user_id` | UUID | FK users.id, nullable |
| `transaction_id` | UUID | nullable FK |
| `case_id` | UUID | nullable FK |
| `object_key` | VARCHAR(500) | unique, private |
| `sha256` | CHAR(64) | not null |
| `status` | VARCHAR(20) | generating/ready/failed/expired |
| `generated_by` | UUID | FK users.id, nullable for system |
| `generated_at` | TIMESTAMPTZ | nullable |
| `expires_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | not null |

Check that exactly the required target fields are present for each report type.

### 7.5 `notifications`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK users.id, indexed |
| `type` | VARCHAR(50) | not null |
| `title` | VARCHAR(200) | not null |
| `message` | TEXT | not null |
| `target_type` | VARCHAR(50) | nullable |
| `target_id` | UUID | nullable |
| `read_at` | TIMESTAMPTZ | nullable |
| `delivery_status` | JSONB | per adapter; no secret payload |
| `created_at` | TIMESTAMPTZ | not null, indexed |

Index `(user_id, read_at, created_at DESC)`.

### 7.6 `audit_logs`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `actor_id` | UUID | nullable FK users.id for system/anonymous |
| `actor_role_snapshot` | JSONB | not null default `[]` |
| `action` | VARCHAR(100) | indexed |
| `target_type` | VARCHAR(50) | indexed |
| `target_id` | UUID | nullable, indexed |
| `outcome` | VARCHAR(20) | success/failure/denied |
| `request_id` | UUID | indexed |
| `ip_hash` | CHAR(64) | nullable |
| `user_agent_hash` | CHAR(64) | nullable |
| `metadata` | JSONB | safe, redacted |
| `created_at` | TIMESTAMPTZ | not null, indexed |

Application code never updates or deletes individual audit rows. Retention/archival is a separately authorised administrative procedure.

### 7.7 `idempotency_records`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `principal_id` | UUID | FK users.id |
| `scope` | VARCHAR(100) | route/action |
| `key_hash` | CHAR(64) | not null |
| `request_hash` | CHAR(64) | not null |
| `resource_type` | VARCHAR(50) | nullable |
| `resource_id` | UUID | nullable |
| `response_status` | INTEGER | nullable |
| `expires_at` | TIMESTAMPTZ | indexed |
| `created_at` | TIMESTAMPTZ | not null |

Unique `(principal_id, scope, key_hash)`. Reuse with a different request hash returns conflict.

## 8. Index plan

At minimum:

- users.email unique;
- transactions `(user_id, created_at DESC)`;
- transactions `(status, created_at)`;
- receipts.sha256 and perceptual_hash;
- ocr_results `(receipt_id, created_at DESC)`;
- analysis_runs `(status, queued_at)` for worker claim;
- analysis_runs `(transaction_id, created_at DESC)`;
- analysis_runs `(risk_class, completed_at)`;
- verification_results `(status, created_at)` through join/index;
- reference_transactions `(provider_code, transaction_reference)`;
- reference_transactions.occurred_at;
- fraud_cases `(status, assigned_to, opened_at)`;
- notifications `(user_id, read_at, created_at DESC)`;
- audit_logs `(created_at DESC)`, `(actor_id, created_at DESC)`, `(action, created_at DESC)`;
- model/rules/template partial unique active indexes.

Codex must use `EXPLAIN (ANALYZE, BUFFERS)` on critical dashboard/history/reference queries with representative data before final release.

## 9. Migration policy

Every schema change includes:

1. model change;
2. migration;
3. upgrade test from clean database;
4. upgrade test from previous revision;
5. downgrade where safe;
6. data backfill plan when required;
7. deployment note;
8. rollback limitations.

Destructive operations require a two-step release where possible:

- release A adds new field/table and dual-write/backfill;
- release B switches reads and later removes old data after verification.

Never auto-run migrations from every web worker. Run one explicit release/migration task.

## 10. Seed policy

Safe development seeds may create:

- one admin;
- one investigator;
- two users;
- generic templates;
- one active rule set;
- inactive/unavailable demo model records;
- fake reference records;
- fake receipt/analysis metadata only when fixture storage exists.

Credentials come from environment or are generated and printed once in local development. Production startup must not create known default credentials.

## 11. Private object-storage layout

Recommended key format:

```text
receipts/{user_uuid}/{transaction_uuid}/original/{receipt_uuid}.{ext}
receipts/{user_uuid}/{transaction_uuid}/derived/{kind}/{version}/{uuid}.{ext}
imports/reference/{batch_uuid}/original.csv
imports/reference/{batch_uuid}/invalid_rows.csv
reports/users/{user_uuid}/{report_uuid}.pdf
reports/cases/{case_uuid}/{report_uuid}.pdf
models/{model_type}/{name}/{version}/{sha256}/{artifact_name}
model-cards/{model_uuid}.md
```

Rules:

- object keys are generated server-side;
- no email, phone, name or transaction reference in a key;
- buckets/containers are private;
- server-side encryption is enabled when available;
- content type is recorded but never trusted as validation;
- access logs or API audit events cover sensitive retrieval;
- signed URLs expire quickly and are issued only after policy checks;
- local development storage lives outside the repository and web static root.

## 12. Retention and deletion

A configurable retention policy must define:

- account/profile retention;
- original receipt retention;
- derived forensic artifact retention;
- reference import retention;
- report expiration;
- model/dataset artifact retention;
- audit retention;
- backup retention.

User deletion does not silently destroy evidence needed for an open case or audit. Apply one of:

- legal/approved retention with access restriction;
- anonymisation/pseudonymisation;
- scheduled deletion after the retention basis ends.

Codex must not invent a legal retention period. It must implement configuration and document the owner's pending policy.

## 13. Backup and consistency

- Database: automated managed backup or documented `pg_dump` schedule.
- Object storage: versioning/lifecycle where available.
- Consistency report identifies database objects whose storage key is missing and private objects without a live database reference.
- Restoration rehearsal uses non-production data.
- Model artifact restore includes hash verification.
- Backup files are encrypted and excluded from Git.

## 14. Database acceptance checklist

- [ ] clean migration to head;
- [ ] previous-version migration to head;
- [ ] all foreign keys and check constraints tested;
- [ ] money precision tests;
- [ ] state transition tests;
- [ ] active-version uniqueness tests;
- [ ] cross-user ownership queries tested;
- [ ] critical indexes verified;
- [ ] worker claim concurrency tested;
- [ ] storage rollback/orphan reconciliation tested;
- [ ] audit append-only policy tested;
- [ ] backup/restore rehearsal recorded.

<!-- END FILE: 04_DATABASE_AND_STORAGE_SPEC.md -->


---

<!-- BEGIN FILE: 05_API_CONTRACT.md -->

# 05 — REST API Contract

## 1. Contract rules

- Base path: `/api/v1`
- Content type: JSON except multipart upload and binary report/image streams.
- Authentication: bearer access token for mobile/API calls; the admin portal uses the documented access/refresh-cookie pattern.
- Timestamps: ISO 8601 UTC.
- IDs: UUID strings.
- Money: string decimal plus currency, for example `"amount": "125.00", "currency": "GHS"`.
- Pagination: `page` starts at 1; `page_size` default 20, maximum 100.
- Sorting/filter values are allowlisted.
- Mutating endpoints that may be retried accept `Idempotency-Key`.
- Every response includes or returns `X-Request-ID`.
- The generated OpenAPI contract is authoritative. Examples below define intended behaviour, not an excuse to let code and documentation diverge.

## 2. Common envelopes

### Success

```json
{
  "data": {},
  "meta": {
    "request_id": "4e01ec26-3e79-4b88-bbbe-97f62ca24557"
  }
}
```

### Collection

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 42,
    "request_id": "..."
  }
}
```

### Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Review the highlighted fields.",
    "field_errors": {
      "email": ["Enter a valid email address."]
    },
    "request_id": "..."
  }
}
```

Internal stack traces, SQL, object keys, filesystem paths and model secrets must never appear in public errors.

## 3. System endpoints

### `GET /health`

**Auth:** none  
**Purpose:** liveness only.

```json
{
  "data": {
    "status": "ok",
    "service": "momo-fdvs-api"
  },
  "meta": {"request_id": "..."}
}
```

### `GET /ready`

**Auth:** none or deployment-protected according to environment  
**Purpose:** dependency/readiness matrix.

```json
{
  "data": {
    "ready": true,
    "components": {
      "database": {"status": "ready"},
      "storage": {"status": "ready"},
      "tesseract": {"status": "ready", "version": "masked-or-safe"},
      "structured_model": {"status": "ready", "version": "rf-1.0.0"},
      "image_model": {"status": "degraded", "reason": "not_activated"}
    },
    "analysis_available": true,
    "full_analysis_available": false
  },
  "meta": {"request_id": "..."}
}
```

Do not reveal credentials, paths or sensitive infrastructure details.

### `GET /version`

Returns application version, build commit and API contract version.

## 4. Authentication and profile

### `POST /auth/register`

**Auth:** none  
**Rate limit:** strict  
**Request:**

```json
{
  "full_name": "Demo User",
  "email": "demo@example.test",
  "password": "long-password"
}
```

**Response:** `201`; user projection and session tokens/cookie according to client.  
**Errors:** 400/422 validation, 409 duplicate when safe, 429.

### `POST /auth/login`

```json
{
  "email": "demo@example.test",
  "password": "long-password"
}
```

**Response:** `200`

```json
{
  "data": {
    "access_token": "mobile-or-memory-token",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "full_name": "Demo User",
      "email": "demo@example.test",
      "roles": ["USER"],
      "status": "ACTIVE"
    }
  },
  "meta": {"request_id": "..."}
}
```

For the web portal, refresh is set as a secure HTTP-only cookie and is not readable by JavaScript.

### `POST /auth/refresh`

Rotates refresh session. Detects reuse and revokes the token family.

### `POST /auth/logout`

Revokes the current refresh session/family as configured and clears the web cookie.

### `POST /auth/forgot-password`

```json
{"email": "demo@example.test"}
```

Always returns a generic accepted response.

### `POST /auth/reset-password`

```json
{
  "token": "single-use-reset-token",
  "new_password": "new-long-password"
}
```

### `GET /me`

Returns profile, roles, permissions and notification preferences.

### `PATCH /me`

Allowlisted fields only: name, phone, notification preferences. Role/status/password are not accepted here.

### `POST /me/change-password`

Requires current password and revokes other refresh sessions.

## 5. Transaction and receipt lifecycle

### `POST /transactions`

**Auth:** USER  
**Content type:** `multipart/form-data`  
**Headers:** `Idempotency-Key` required  
**Fields:**

- `receipt`: required image file;
- `source`: `CAMERA` or `GALLERY`;
- `client_captured_at`: optional ISO timestamp;
- `client_metadata`: optional safe device/app metadata, size-limited.

**Response:** `201`

```json
{
  "data": {
    "transaction": {
      "id": "uuid",
      "status": "UPLOADED",
      "created_at": "..."
    },
    "receipt": {
      "id": "uuid",
      "media_type": "image/jpeg",
      "size_bytes": 481223,
      "width_px": 1080,
      "height_px": 1920,
      "quality_warnings": []
    },
    "next_action": {
      "type": "RUN_OCR",
      "endpoint": "/api/v1/transactions/uuid/ocr"
    }
  },
  "meta": {"request_id": "..."}
}
```

The response never exposes the private object key or another user's duplicate details.

**Errors:** 400 invalid image, 413 too large, 415 unsupported media, 409 idempotency conflict, 503 storage unavailable.

### `GET /transactions/{transaction_id}/receipt`

**Auth:** owner, authorised ADMIN/INVESTIGATOR  
Streams or redirects through a short-lived private URL after policy check. Optional query `variant=thumbnail|original|ela|noise_map|heatmap`. Staff-only variants are permission checked.

### `DELETE /transactions/{transaction_id}`

Optional pre-analysis user deletion/cancellation only. Completed evidence follows retention policy rather than unqualified hard deletion. Contract must make the allowed state explicit.

## 6. OCR

### `POST /transactions/{transaction_id}/ocr`

**Auth:** owner  
**Idempotency:** required or server-deduplicated  
Runs the OCR pipeline synchronously for the prototype or returns `202` if the implementation moves OCR to a job. The client must handle both consistently.

**Response when complete:** `200`

```json
{
  "data": {
    "transaction_id": "uuid",
    "status": "OCR_READY",
    "ocr_result_id": "uuid",
    "provider": {
      "value": "GENERIC_MOMO",
      "confidence": 0.82,
      "requires_review": false
    },
    "fields": {
      "transaction_reference": {
        "value": "ABC123456",
        "confidence": 0.94,
        "valid": true,
        "requires_review": false
      },
      "amount": {
        "value": "125.00",
        "currency": "GHS",
        "confidence": 0.71,
        "valid": true,
        "requires_review": true
      },
      "receiver_phone": {
        "value": "+233240000001",
        "masked": "+233 24 *** 0001",
        "confidence": 0.88,
        "requires_review": false
      }
    },
    "warnings": ["AMOUNT_LOW_CONFIDENCE"],
    "preview_url": "/api/v1/transactions/uuid/receipt?variant=thumbnail"
  },
  "meta": {"request_id": "..."}
}
```

### `GET /transactions/{transaction_id}/ocr-review`

Returns current raw extraction projection, field confidence and validation warnings. It does not expose all raw token data to normal users unless needed for the UI.

### `POST /transactions/{transaction_id}/ocr-confirmations`

**Auth:** owner  
**Headers:** `Idempotency-Key`  
**Request:**

```json
{
  "ocr_result_id": "uuid",
  "fields": {
    "provider_code": "GENERIC_MOMO",
    "transaction_reference": "ABC123456",
    "amount": "125.00",
    "currency": "GHS",
    "sender_name": "Demo Sender",
    "sender_phone": "+233240000002",
    "receiver_name": "Demo Receiver",
    "receiver_phone": "+233240000001",
    "occurred_at": "2026-08-08T14:30:00Z",
    "status_text": "Successful"
  },
  "correction_reasons": {
    "amount": "Corrected after checking the receipt image"
  }
}
```

**Response:** `201`, confirmation ID and `OCR_REVIEWED` state.

Server validates that the referenced OCR result belongs to the transaction/user and that required fields are canonical.

## 7. Analysis

### `POST /transactions/{transaction_id}/analyses`

**Auth:** owner  
**Headers:** `Idempotency-Key` required  
**Precondition:** OCR reviewed.

**Response:** `202`

```json
{
  "data": {
    "analysis_run_id": "uuid",
    "transaction_id": "uuid",
    "status": "QUEUED",
    "current_stage": "WAITING",
    "poll_url": "/api/v1/analyses/uuid",
    "estimated_message": "Your receipt is queued for analysis."
  },
  "meta": {"request_id": "..."}
}
```

### `GET /analyses/{analysis_run_id}`

**Auth:** owner, authorised staff

Active response:

```json
{
  "data": {
    "id": "uuid",
    "status": "PROCESSING",
    "current_stage": "IMAGE_FEATURES",
    "progress": {
      "completed_stages": 3,
      "total_stages": 9
    },
    "started_at": "..."
  },
  "meta": {"request_id": "..."}
}
```

Completed response:

```json
{
  "data": {
    "id": "uuid",
    "status": "COMPLETED",
    "risk": {
      "class": "SUSPICIOUS",
      "score": 57.4,
      "label": "Suspicious",
      "disclaimer": "This is an automated risk assessment, not a final legal determination.",
      "reasons": [
        {
          "code": "REFERENCE_AMOUNT_MISMATCH",
          "title": "Amount does not match the reference record",
          "severity": "HIGH"
        },
        {
          "code": "TEXT_ALIGNMENT_INCONSISTENCY",
          "title": "Some receipt text is not aligned as expected",
          "severity": "MEDIUM"
        }
      ]
    },
    "verification": {
      "status": "MISMATCH",
      "label": "Reference mismatch",
      "basis": "STORED_IMPORTED_RECORD",
      "summary": "A reference record was found, but the amount differed."
    },
    "evidence_summary": {
      "ocr_field_coverage": 0.93,
      "image_model_status": "SUCCESS",
      "structured_model_status": "SUCCESS",
      "rules_triggered": 2
    },
    "versions": {
      "ocr_pipeline": "ocr-1.0.0",
      "template": "generic-1.0.0",
      "image_model": "image-1.0.0",
      "structured_model": "rf-1.0.0",
      "rule_set": "rules-1.0.0"
    },
    "completed_at": "..."
  },
  "meta": {"request_id": "..."}
}
```

A normal user receives an understandable summary, not every raw internal feature. Authorised evidence endpoints provide more detail.

### `GET /analyses/{analysis_run_id}/evidence`

**Auth:** owner receives user-safe evidence; ADMIN/INVESTIGATOR receives role-appropriate detailed evidence.  
Returns sections:

- OCR and corrections;
- image evidence/reasons;
- model outputs/status/version;
- rule evaluations;
- reference field comparisons;
- stage timing;
- human review status when present.

### `POST /transactions/{transaction_id}/reanalyses`

Optional explicit reanalysis after a completed/partial/failed run. Requires reason and creates a new run linked to the previous one. Never overwrites.

## 8. User history, reports and notifications

### `GET /transactions`

**Auth:** owner  
**Query:**

- `page`, `page_size`;
- `date_from`, `date_to`;
- `risk_class`;
- `verification_status`;
- `provider_code`;
- `status`;
- `search` limited to user's masked/reference-safe fields.

Returns transaction cards with latest persisted result.

### `GET /transactions/{transaction_id}`

Returns user-safe transaction detail, receipt thumbnail endpoint, OCR snapshot, latest/result history, report/case status and available actions.

### `POST /transactions/{transaction_id}/reports`

Generates or returns an idempotent analysis summary artifact.

### `GET /reports/{report_id}/download`

Authorised binary stream. `Content-Disposition` uses a generated safe filename.

### `GET /notifications`

Owner's paginated notifications with unread filter.

### `GET /notifications/unread-count`

Small unread-count response.

### `POST /notifications/{notification_id}/read`

Marks one owned notification as read.

### `POST /notifications/read-all`

Marks the authenticated user's notifications read; idempotent.

## 9. User fraud reports

### `POST /transactions/{transaction_id}/fraud-reports`

**Auth:** owner  
**Request:**

```json
{
  "category": "PAYMENT_NOT_RECEIVED",
  "description": "The sender showed this receipt, but the expected payment was not received."
}
```

**Response:** `201` with case ID/status. If an open case exists, return/link it according to idempotency policy rather than creating duplicates.

### `GET /fraud-reports/{case_id}`

Owner receives limited case status/timeline for cases they reported. Staff use the admin case endpoints.

## 10. Staff dashboard and transaction search

All routes below require ADMIN and/or INVESTIGATOR as declared.

### `GET /admin/dashboard`

Query `date_from`, `date_to`, `provider_code`.

Returns:

- analyses by risk/status;
- verification counts;
- case counts;
- average/p95 processing time where available;
- active model/rule/template status;
- recent operational warnings.

### `GET /admin/transactions`

Paginated staff search with masked default projection. Full evidence requires a separate authorised detail call.

### `GET /admin/transactions/{transaction_id}`

Role-projected detail. Every access is audited.

### `GET /admin/system-status`

Dependency matrix, worker heartbeat/queue depth, active versions and safe storage/database status.

## 11. Staff user management

### `GET /admin/users`

ADMIN only; filter by status/role/search.

### `POST /admin/users`

Creates staff/user account according to policy. Temporary-password delivery is not included in the response/log.

### `PATCH /admin/users/{user_id}`

Allowlisted profile/status changes with optimistic version.

### `PUT /admin/users/{user_id}/roles`

Replaces/updates roles. Prevents last-admin removal and self-lockout according to policy.

### `POST /admin/users/{user_id}/revoke-sessions`

Revokes active refresh sessions.

## 12. Reference imports and records

### `POST /admin/reference-imports`

ADMIN; multipart CSV, idempotency key. Stores private original and returns batch with `UPLOADED`.

### `POST /admin/reference-imports/{batch_id}/validate`

Parses/normalises without committing reference rows.

```json
{
  "data": {
    "batch_id": "uuid",
    "status": "VALIDATED",
    "total_rows": 100,
    "valid_rows": 94,
    "invalid_rows": 6,
    "errors": [
      {"row": 4, "field": "amount", "code": "INVALID_DECIMAL"}
    ],
    "invalid_rows_download": "/api/v1/admin/reference-imports/uuid/invalid-rows"
  },
  "meta": {"request_id": "..."}
}
```

### `POST /admin/reference-imports/{batch_id}/commit`

Commits valid rows atomically or in documented batches with reconciliation. Requires optimistic status and idempotency.

### `GET /admin/reference-imports`

### `GET /admin/reference-imports/{batch_id}`

### `GET /admin/reference-imports/{batch_id}/invalid-rows`

### `GET /admin/reference-transactions`

Masked/searchable; do not expose raw imported row indiscriminately.

### `GET /admin/reference-transactions/{id}`

ADMIN/INVESTIGATOR according to purpose; audited.

## 13. Receipt templates

### `GET /admin/receipt-templates`

### `POST /admin/receipt-templates`

Creates DRAFT version.

### `GET /admin/receipt-templates/{id}`

### `PATCH /admin/receipt-templates/{id}`

Draft only or creates a new version; do not mutate active historical version.

### `POST /admin/receipt-templates/{id}/validate`

Validates configuration and optional safe fixture.

### `POST /admin/receipt-templates/{id}/activate`

ADMIN only, optimistic lock, audit.

### `POST /admin/receipt-templates/{id}/retire`

Cannot break historical references.

## 14. Rules and thresholds

### `GET /admin/rule-sets`

### `POST /admin/rule-sets`

Creates DRAFT version with risk weights/thresholds.

### `GET /admin/rule-sets/{id}`

### `PATCH /admin/rule-sets/{id}`

Draft only.

### `POST /admin/rule-sets/{id}/validate`

Validates weights, threshold ordering, reason codes and referenced features.

### `POST /admin/rule-sets/{id}/activate`

Checks weights sum policy and model/feature compatibility. Audit.

### `POST /admin/rule-sets/{id}/retire`

## 15. Model registry

### `GET /admin/models`

Filter by type/status.

### `POST /admin/models/register`

Registers metadata for an already uploaded/private artifact or a controlled server-side artifact import. Never accepts arbitrary executable code.

### `GET /admin/models/{id}`

Returns safe model card/metrics/readiness.

### `POST /admin/models/{id}/verify`

Recomputes artifact hash, checks framework/schema/preprocessing compatibility and performs a safe smoke inference.

### `POST /admin/models/{id}/activate`

ADMIN, only `READY`, audit, cache invalidation.

### `POST /admin/models/{id}/retire`

Historical predictions retain the FK.

## 16. Investigator case API

### `GET /admin/cases`

ADMIN/INVESTIGATOR; filter by status, assignment, risk, provider, date, source.

### `GET /admin/cases/{case_id}`

Returns case, masked user/transaction information, original result, OCR, image evidence, model outputs, rule evaluations, verification comparisons, reports and timeline. Receipt variants use protected endpoints.

### `POST /admin/cases/{case_id}/assign`

Valid investigator target, optimistic state.

### `POST /admin/cases/{case_id}/start-review`

Moves OPEN to IN_REVIEW.

### `POST /admin/cases/{case_id}/notes`

Adds append-only note/event.

### `POST /admin/cases/{case_id}/decisions`

```json
{
  "outcome": "ESCALATED",
  "reason": "The amount and receiver details conflict with the imported reference record.",
  "expected_case_version": 4
}
```

Response returns the new case state and decision ID. The automated result remains untouched.

### `POST /admin/cases/{case_id}/reports`

### `GET /admin/cases/{case_id}/reports/{report_id}/download`

## 17. Audit and operational reports

### `GET /admin/audit-logs`

ADMIN; query actor, action, target type/ID, outcome, date and request ID. Metadata is already redacted.

### `GET /admin/reports/operations`

Generates bounded operational CSV/PDF summaries. Large export must be asynchronous or strictly capped.

## 18. Webhook/notification adapters

External push/email is optional. When implemented:

- use an authenticated outbound adapter;
- do not include full receipt images or unmasked transaction data in message bodies;
- store provider message ID and delivery status, not provider secrets;
- retry bounded transient errors;
- preserve in-app notification;
- verify inbound webhook signatures before updating delivery status.

## 19. API permission matrix

| Resource/action | USER owner | ADMIN | INVESTIGATOR |
|---|---:|---:|---:|
| Register/login/self profile | Yes | Yes | Yes |
| Upload/view own receipt | Yes | Configured staff view | Case/authorised view |
| Correct own OCR | Yes | No by default | No by default |
| Start own analysis | Yes | Optional support | No by default |
| View own history/report | Yes | Authorised | Authorised case |
| Report own transaction | Yes | View | Review |
| Manage users/roles | No | Yes | No |
| Import reference records | No | Yes | Read if needed |
| Manage templates/rules/models | No | Yes | Read active evidence |
| View dashboard | No | Yes | Limited/yes |
| Review/decide case | No | Optional capability | Yes |
| View audit logs | No | Yes | Limited case timeline |

The server enforces this matrix. Hiding a button is not authorisation.

## 20. Contract tests

For every endpoint Codex must test:

- success response schema;
- authentication;
- role permission;
- object ownership;
- validation/error envelope;
- idempotency/conflict where relevant;
- pagination/filter limits;
- audit event where required;
- no private object key/secret leakage;
- OpenAPI snapshot/generation consistency.

No endpoint is complete when only its happy path works.

<!-- END FILE: 05_API_CONTRACT.md -->


---

<!-- BEGIN FILE: 06_UI_UX_IMPLEMENTATION_SPEC.md -->

# 06 — UI/UX Implementation Specification

## 1. Product experience goals

The interface must help a non-technical Mobile Money user answer four separate questions:

1. What information did the system read from the receipt?
2. Does the receipt appear visually or structurally suspicious?
3. Does the transaction information match an available stored/imported reference record?
4. What should the user do next?

The interface must never collapse these into a single unexplained “fake/real” badge.

## 2. Design principles

- **Clarity over novelty:** plain language, familiar controls and concise explanations.
- **Evidence before verdict:** show the main reasons behind a result.
- **Separate statuses:** risk class and verification status have distinct cards, icons and labels.
- **Privacy by default:** mask full phone/reference values in lists and reports.
- **Progressive disclosure:** users see a simple summary first; detailed evidence is available on demand.
- **No colour-only communication:** every status has text and icon/shape.
- **Recoverability:** upload, OCR and network errors provide a clear next action.
- **Honest uncertainty:** `UNVERIFIED`, `PARTIAL` and low-confidence states are explained.
- **Role-specific complexity:** normal users do not see raw feature vectors; investigators can inspect detailed evidence.
- **Chapter separation:** low-fidelity wireframes remain in Chapter Three; implemented high-fidelity interfaces and screenshots are recorded for Chapter Four.

## 3. Design tokens

Codex must create shared semantic tokens rather than scattering values.

### 3.1 Semantic status tokens

Suggested semantics, not fixed brand colours:

- success / low risk;
- warning / suspicious;
- danger / high risk;
- neutral / unverified;
- info / processing;
- disabled;
- focus;
- surface/background/border/text hierarchy.

A status component includes:

- icon;
- text label;
- semantic colour;
- optional short explanation;
- accessible name.

### 3.2 Typography

- readable body size with dynamic-text support on mobile;
- clear heading hierarchy;
- tabular or aligned numerals for amounts/score;
- minimum touch-target and line-height standards;
- no all-caps paragraphs.

### 3.3 Components

Mobile and web implementations may differ internally but should share terminology:

- `RiskBadge`
- `VerificationBadge`
- `ProcessingStatus`
- `EvidenceReason`
- `MaskedValue`
- `ReceiptThumbnail`
- `ReceiptViewer`
- `ConfidenceIndicator`
- `EmptyState`
- `ErrorState`
- `RetryPanel`
- `PermissionNotice`
- `ConfirmationDialog`
- `AuditTimeline`
- `ModelVersionTag` for staff only
- `Pagination`
- `FilterBar`
- `FormField`
- `Skeleton`

## 4. Mobile information architecture

### Auth stack

- Splash / session restore
- Welcome/Login
- Register
- Forgot Password
- Reset Password
- Terms/Privacy summary when required

### Authenticated tabs

1. **Home**
2. **History**
3. **Upload/Scan** — central primary action or prominent home action
4. **Notifications**
5. **Profile**

Feature routes open above the tabs:

- Receipt Source
- Receipt Preview
- Upload/OCR Progress
- OCR Review
- Analysis Progress
- Result Summary
- Evidence Detail
- Transaction Detail
- Report Preview/Download
- Fraud Report Form
- Help/How Results Work

## 5. Mobile screen specifications

### M01 — Splash and session restoration

**Purpose:** Restore a valid session without flashing protected content.

**Content:**

- product mark/name;
- neutral loading indicator;
- no sensitive user data.

**States:**

- valid session -> Home;
- expired access with valid refresh -> rotate/continue;
- no session -> Login;
- offline with previously known session -> show reconnect guidance, do not pretend protected data is current;
- fatal config error -> support message with request/build ID.

### M02 — Login

**Fields:**

- email;
- password with show/hide;
- remember-device wording only if behaviour is defined.

**Actions:**

- Login;
- Forgot password;
- Create account when registration enabled.

**Requirements:**

- generic invalid-credentials message;
- disabled submit while request is active;
- keyboard-friendly;
- no token or password logged;
- accessible errors tied to fields;
- rate-limit message with safe retry timing.

### M03 — Registration

**Fields:**

- full name;
- email;
- optional phone according to project policy;
- password;
- confirm password;
- consent/terms checkbox only when real policy text exists.

**Feedback:**

- password requirements before submission;
- duplicate email response not over-specific if enumeration policy uses generic messaging;
- successful registration routes according to verification/session policy.

### M04 — Forgot/reset password

- request email;
- generic accepted state;
- token/deep-link reset screen;
- new password/confirmation;
- expired/used token state;
- success -> login or session according to policy.

### M05 — Home

**Primary objective:** Start a new check in no more than three principal actions.

**Sections:**

1. Greeting/profile shorthand.
2. Primary “Check a receipt” button.
3. “How it works” three-step strip: Upload -> Review details -> See risk and verification.
4. Recent analyses (maximum 3–5).
5. Notification/attention card for incomplete OCR review or case update.
6. Small disclaimer that results are automated decision support.

**Empty state:** Explain the first upload without showing fake analytics.

### M06 — Receipt source

Options:

- Take photo;
- Choose from gallery;
- Cancel.

Permission-denied state includes “Open settings” only when platform permits. Explain accepted formats and privacy.

### M07 — Receipt preview and quality check

**Content:**

- zoomable preview;
- replace/remove;
- selected source;
- file-size/quality guidance;
- privacy note.

**Client-side warnings:**

- likely blurry;
- too dark;
- receipt edges not visible;
- very small image.

Warnings do not block unless client detects an obviously unusable file; server remains authoritative.

**Primary action:** Upload and extract details.

### M08 — Upload/OCR progress

Use stages with user-friendly text:

- Securing receipt;
- Improving readability;
- Reading transaction details;
- Preparing fields for review.

Include cancel only if server supports safe cancellation. A background/app resume returns to the persisted transaction.

Error states:

- unsupported/corrupt;
- too large;
- network interrupted;
- storage unavailable;
- OCR unavailable;
- unknown layout.

Each error has a safe retry/replace action and request ID for support.

### M09 — OCR review

This is a critical screen.

**Layout:**

- receipt image at top or switchable pane;
- tap/zoom/pan;
- field form below;
- low-confidence fields first or clearly marked;
- original OCR value available in a non-confusing detail;
- confidence expressed as “Check this field” rather than raw percentages for normal users.

**Fields:**

- provider/network;
- transaction reference;
- amount and currency;
- sender name/phone where present;
- receiver name/phone where present;
- date/time;
- receipt status text.

**Rules:**

- canonical formatting preview;
- mask values in summary but permit the owner to review their own full entered values;
- validation errors explain expected format;
- correction reasons may be automatically captured; user-facing reason field only where useful;
- confirmation creates immutable snapshot.

**Primary action:** Confirm details and analyse.

### M10 — Analysis progress

Poll the analysis resource and display:

- queued;
- checking reference information;
- checking image consistency;
- running automated fraud checks;
- preparing result.

Do not show a fake linear percentage when stage duration is unknown. Show completed stage count or indeterminate progress.

Support:

- app background/resume;
- network loss/retry;
- partial completion;
- “You may leave this screen; the result will appear in History” when notifications/history support it.

### M11 — Result summary

Order matters.

#### A. Fraud risk card

- label: Genuine / Suspicious / Fraudulent;
- score as supporting information, not the only signal;
- one-line interpretation;
- icon + semantic status;
- “Automated assessment” label.

#### B. Verification card

- Verified / Unverified / Mismatch;
- basis: “Checked against stored/imported reference records”;
- concise field comparison summary;
- never imply live MNO confirmation.

#### C. Main reasons

2–4 top reason cards with:

- plain title;
- short explanation;
- severity;
- optional “See evidence”.

#### D. Recommended next step

Examples:

- low risk + verified: keep/report summary;
- low risk + unverified: confirm through an authorised channel if payment remains uncertain;
- suspicious: compare receipt with wallet/statement or ask for a trusted reference;
- fraudulent/high risk: do not rely on the receipt alone; report for review.

Avoid legal/financial guarantees.

#### E. Actions

- View evidence;
- Download summary;
- Report suspicious transaction;
- Back to Home/History.

#### F. Disclaimer

“MoMo-FDVS provides an automated risk assessment. It does not itself reverse, confirm or complete a Mobile Money transfer.”

### M12 — Evidence detail

User-safe sections:

1. Confirmed transaction details.
2. OCR confidence/fields reviewed.
3. Image checks (plain-language outcomes).
4. Automated model checks (status and high-level result).
5. Reference comparison.
6. Versions/date/request ID in a collapsed technical section.
7. Human review/case status when applicable.

Do not expose:

- other users' duplicate details;
- private object keys;
- raw secrets;
- unbounded raw feature vectors;
- model code paths.

### M13 — History

**List item:**

- date/time;
- masked reference;
- amount;
- provider;
- risk badge;
- verification badge;
- processing/case indicator.

**Controls:**

- search;
- date range;
- risk;
- verification;
- provider;
- status;
- reset filters.

**States:** first-time empty, filtered empty, loading skeleton, retry, pagination/end.

### M14 — Transaction detail

Reconstruct from persisted result:

- receipt thumbnail;
- confirmed details;
- latest risk + verification;
- result timestamp/model/rule versions;
- analysis run history/reanalysis if supported;
- report and case status;
- safe actions.

Historical output must not change when an active model changes.

### M15 — Report preview/download

- explain masked fields;
- display generation/ready/failure state;
- download/share using platform-safe mechanisms;
- do not store report publicly;
- provide report generated timestamp and result version.

### M16 — Report suspicious transaction

Fields:

- category;
- description;
- confirmation that the linked analysis will be shared with authorised reviewers;
- submit.

States:

- existing open case -> open status instead of duplicate;
- success with case ID/status;
- invalid/permission error.

### M17 — Notifications

- unread/read sections or filter;
- type icon and plain title;
- timestamp;
- deep link;
- mark read;
- empty state;
- no full sensitive transaction values in preview text.

### M18 — Profile, privacy and help

Sections:

- profile;
- password/security;
- notification preferences;
- privacy/data explanation;
- “How results work”;
- app version/build;
- logout;
- deletion/deactivation request according to policy.

## 6. Mobile reusable feature modules

Suggested feature folders:

```text
features/
├── auth/
├── receipt-capture/
├── ocr-review/
├── analysis/
├── history/
├── notifications/
├── fraud-reporting/
└── profile/
```

Each contains:

- API hooks;
- screens/components;
- validation schemas;
- query keys;
- tests;
- feature-specific types only where not generated.

## 7. Administrator/investigator portal information architecture

### Shared shell

- skip link;
- header with environment indicator and current role;
- side navigation;
- breadcrumb;
- global session/error handling;
- role-based navigation;
- no hidden-only security.

### Routes

1. Login
2. Dashboard
3. Transactions
4. Cases
5. Users
6. Reference Imports
7. Receipt Templates
8. Fraud Rules
9. Model Registry
10. Reports
11. Audit Logs
12. System Status
13. Profile/Security

Investigators may see a reduced shell: Dashboard, Cases, authorised Transactions, Reports/Profile.

## 8. Web screen specifications

### W01 — Staff login

- organisation/product identity;
- email/password;
- no public registration;
- password reset according to policy;
- generic errors and rate-limit handling;
- environment label for staging.

### W02 — Dashboard

Top summary cards:

- total analyses;
- suspicious/fraudulent count;
- verified/unverified/mismatch;
- open/in-review cases;
- average/p95 analysis time;
- queue/degraded component warning.

Charts/tables:

- analyses over time by risk;
- verification distribution;
- provider distribution;
- cases by status;
- recent high-risk/case queue;
- active model/rule/template versions.

Controls:

- date range;
- provider;
- refresh;
- tabular export where authorised.

Every chart has textual/table alternative and empty/partial-data state.

### W03 — Transactions

Data table columns:

- submitted at;
- masked user;
- provider;
- masked reference;
- amount;
- risk;
- verification;
- processing state;
- case;
- actions.

Features:

- server pagination/filter/sort;
- accessible filter drawer;
- saved filters optional;
- no full receipt displayed in list;
- authorised detail access audited.

### W04 — Staff transaction detail

Sections:

- summary;
- user/receipt information with role masking;
- confirmed OCR;
- risk/verification;
- evidence;
- analysis stages/timings;
- model/rule/template versions;
- linked cases/reports;
- audit access link.

Receipt viewer supports zoom and approved diagnostic variants. It must not load a public URL.

### W05 — Case queue

Columns/cards:

- case age;
- source;
- risk/verification;
- provider/amount;
- assigned investigator;
- status;
- priority;
- last activity.

Controls:

- status/assignment/source/provider/date/risk filters;
- “My cases”;
- claim/start review where permitted.

### W06 — Case detail

Three-column/section design:

1. **Evidence workspace**
   - original receipt;
   - OCR overlays;
   - diagnostic variants;
   - reference comparisons.
2. **Automated findings**
   - risk and verification separately;
   - model status/probabilities as staff evidence;
   - rule triggers;
   - versions/limitations.
3. **Case actions/timeline**
   - assignment;
   - notes;
   - confirm/dismiss/escalate;
   - mandatory reason;
   - generated report.

Destructive/terminal action requires confirmation and current case version to prevent lost updates.

### W07 — Users and roles

- search/filter status/role;
- create staff/user according to policy;
- enable/disable;
- role assignment;
- revoke sessions;
- last-admin safeguard;
- audit history link;
- never display password/reset token.

### W08 — Reference imports

Wizard:

1. Choose file/source label.
2. Upload securely.
3. Validate/preview counts.
4. Inspect errors/download invalid rows.
5. Confirm commit.
6. View imported batch/result.

Show explicitly: “Verification uses the reference data imported here; this is not a live provider connection.”

### W09 — Reference transaction detail/list

- masked default;
- provider/reference/amount/status/timestamp;
- import batch/source;
- authorised raw-row expansion only when needed;
- related verification uses;
- no edit of committed evidential rows; correction is a new import/version or authorised correction event.

### W10 — Receipt templates

- provider/name/version/status;
- draft editor for anchors/regions/regex/config;
- validation against safe fixture;
- activate/retire;
- diff between versions;
- active badge;
- no direct edit of active historical version.

A structured form is preferred to a raw JSON textarea. An advanced JSON editor may exist behind validation.

### W11 — Fraud rules and thresholds

- rule-set versions/status;
- weights and thresholds;
- rule list with reason code, severity and contribution;
- validation checks;
- scenario preview against safe fixture;
- activate/rollback;
- immutable active versions.

UI must warn that changing thresholds affects future analyses only.

### W12 — Model registry

- model type/name/version;
- artifact readiness/hash;
- framework/preprocessing/schema versions;
- measured metrics and dataset scope;
- synthetic-only warning;
- active/retired status;
- verify/activate/rollback actions;
- model card view.

Never provide arbitrary server path entry or executable upload without a controlled artifact-import design.

### W13 — Reports

- analysis/case/operations reports;
- filters;
- status;
- generated by/date;
- authorised download;
- row limit and export audit;
- failed report retry.

### W14 — Audit logs

- actor;
- action;
- target;
- outcome;
- request ID;
- timestamp;
- safe metadata detail;
- filters/pagination;
- no delete/edit;
- export only when authorised and audited.

### W15 — System status

Cards:

- API/build;
- database;
- storage;
- Tesseract;
- worker queue/heartbeat;
- structured model;
- image model;
- notification adapters;
- migration revision.

Clearly distinguish:

- Ready;
- Degraded;
- Unavailable;
- Disabled by configuration.

Do not expose secrets, internal hostnames or private filesystem paths.

## 9. Copy and terminology

Use:

- “Check a receipt”
- “Review extracted details”
- “Fraud risk”
- “Verification status”
- “Checked against stored/imported reference records”
- “Automated assessment”
- “Needs review”
- “Analysis partially completed”

Avoid:

- “100% genuine”
- “Guaranteed fake”
- “Confirmed by MTN/Telecel/AT” without real integration
- “AI knows”
- “No fraud”
- “Bank verified” unless true
- unexplained acronyms in normal-user screens.

## 10. Accessibility requirements

### Mobile

- all touch controls have accessible names/roles;
- minimum practical touch target;
- form errors announced and tied to inputs;
- image alternatives describe purpose, not raw sensitive text;
- dynamic text does not clip;
- focus moves to error/heading after navigation;
- reduce motion where requested;
- status includes text/icon.

### Web

- semantic landmarks/headings;
- skip link;
- keyboard-operable menus/dialogs/tables/actions;
- visible focus;
- dialog focus trap and restoration;
- form labels/descriptions/errors;
- sortable table headers announced;
- charts have summaries/tables;
- contrast checked;
- no hover-only information.

## 11. Responsive test matrix

Codex records exact final viewports, with at least:

### Mobile

- small Android phone;
- common 360–390 CSS/density-equivalent width;
- large Android phone;
- portrait and critical landscape/image-viewer behaviour;
- dynamic font at larger setting.

### Web

- 1280×720;
- 1366×768;
- 1440×900;
- tablet around 768×1024;
- narrow window where supported.

No horizontal document overflow. Wide tables may use contained horizontal scrolling with sticky labels or card alternatives, not overflow the page.

## 12. UI state checklist for every data screen

- initial loading;
- background refresh;
- empty;
- filtered empty;
- success;
- validation error;
- permission denied;
- not found;
- network/server error;
- retry;
- degraded/partial data;
- stale data indicator where relevant;
- destructive confirmation;
- optimistic/pessimistic update behaviour;
- session expiry.

## 13. Visual QA evidence

For each critical screen Codex captures:

- route/screen name;
- role/account used;
- viewport/device;
- build/SHA;
- state represented;
- screenshot path;
- console/runtime errors;
- accessibility notes.

Critical screenshot set:

- mobile login;
- mobile home;
- receipt preview;
- OCR review;
- analysis progress;
- each risk class;
- each verification status;
- partial analysis;
- history/detail/report;
- admin dashboard;
- case queue/detail/decision dialog;
- reference import;
- template/rule/model registries;
- audit/system status.

## 14. UI acceptance journeys

### Journey A — New user

Register -> Login -> Home -> Upload -> OCR review -> Analysis -> Result -> History -> Report.

### Journey B — Verification mismatch

Import reference -> User analyses corresponding edited receipt -> Mismatch displayed separately from fraud risk -> Investigator opens evidence.

### Journey C — Partial analysis

Disable image model -> Analyse -> PARTIAL result explains unavailable component -> Existing evidence preserved -> Status visible in portal.

### Journey D — Human review

User reports -> Investigator starts review -> Adds note -> Escalates with reason -> User receives status notification -> Original automated result unchanged.

### Journey E — Permission denial

Normal user attempts staff route/object ID -> no data leak; staff with wrong role cannot activate models or decide cases.

All journeys must be demonstrated against the final staging/local build and named in the final handoff.

<!-- END FILE: 06_UI_UX_IMPLEMENTATION_SPEC.md -->


---

<!-- BEGIN FILE: 07_OCR_IMAGE_ML_VERIFICATION_SPEC.md -->

# 07 — OCR, Image Analysis, Machine Learning and Verification Specification

## 1. Analytical philosophy

MoMo-FDVS is a hybrid evidence system. No single component is sufficient:

- OCR reads visible text but does not prove authenticity.
- Image forensics can reveal inconsistencies but can be affected by normal compression, screenshots and device processing.
- Machine learning estimates patterns found in its training scope but cannot generalise beyond the evidence without validation.
- Reference matching can confirm consistency with an available record but cannot operate when no trustworthy record exists.
- Human review is required for consequential or ambiguous cases.

Every component must return both a machine-readable result and an explicit limitation/status.

## 2. End-to-end pipeline

```text
Private original receipt
    ↓
Decode/quality checks
    ↓
Preprocessing variants
    ↓
Tesseract tokens + confidence + bounding boxes
    ↓
Template detection and field parsing
    ↓
User confirms/corrects fields
    ↓
Analysis snapshot
    ├── Reference verification
    ├── Deterministic image evidence
    ├── CNN image tampering inference
    ├── Structured feature assembly
    ├── Random Forest inference
    └── Versioned rule evaluation
    ↓
Risk aggregation + top reasons
    ↓
Persisted risk result + separate verification result
    ↓
User result / investigator evidence
```

## 3. Receipt decoding and quality

### 3.1 Decode

- Read bytes from private storage.
- Verify expected SHA-256 before processing.
- Decode with Pillow/OpenCV using safe limits.
- Apply EXIF transpose to a derived image.
- Convert to a defined colour representation.
- Reject or safely flatten unsupported animation/multi-frame content according to upload policy.
- Record decoder/library versions.

### 3.2 Quality features

Suggested versioned features:

- width, height, aspect ratio;
- grayscale mean/std;
- contrast range;
- Laplacian variance or equivalent sharpness proxy;
- estimated text/edge density;
- clipping/overexposure/underexposure proportion;
- possible crop/edge completeness;
- compression format/quality proxy;
- OCR-scale suitability.

Quality features produce warnings such as:

- `IMAGE_TOO_SMALL`;
- `IMAGE_BLURRY`;
- `IMAGE_LOW_CONTRAST`;
- `RECEIPT_EDGES_MISSING`;
- `IMAGE_OVERCOMPRESSED`.

Quality warnings are not fraud labels.

## 4. OCR preprocessing

Create several deterministic variants from the same oriented input:

1. `BASE_RESIZED`
   - preserve aspect;
   - enlarge small text to target minimum scale;
   - avoid uncontrolled repeated interpolation.

2. `GRAY_CLAHE`
   - grayscale;
   - local contrast enhancement with versioned parameters.

3. `DENOISE_SHARPEN`
   - bounded denoise;
   - unsharp mask or controlled sharpening.

4. `OTSU_BINARY`
   - global Otsu threshold.

5. `ADAPTIVE_BINARY`
   - adaptive threshold for uneven lighting.

6. `DESKEWED_*`
   - optional deskew when a reliable angle is detected.

Store only necessary derivatives according to retention; always store preprocessing metadata.

### 4.1 Variant selection

For each variant run OCR and calculate a selection score from:

- mean/median token confidence;
- required-field parser coverage;
- valid transaction-reference candidate;
- valid amount candidate;
- date/time candidate;
- phone candidate;
- text length/density sanity;
- template anchor matches.

Do not select only by mean OCR confidence because a high-confidence irrelevant header can hide missing transaction fields. Store the winning variant plus candidate summary.

## 5. Tesseract invocation

- Use `image_to_data`/TSV-equivalent to retain word text, confidence and bounding box.
- Set language/config based on supported content; begin with English and documented receipt symbols.
- Use a small evaluated set of page-segmentation modes, not an unbounded brute-force search.
- Set a process timeout.
- Capture safe stderr/error code.
- Record Tesseract version and configuration.
- Never build a shell command with untrusted filename or options.

Token structure:

```json
{
  "text": "125.00",
  "confidence": 91.2,
  "x": 413,
  "y": 622,
  "width": 144,
  "height": 38,
  "line_id": "..."
}
```

## 6. Provider/template detection

Each template version defines:

- provider code;
- optional anchor phrases;
- expected field labels;
- expected regions/relative order;
- regex patterns;
- date formats;
- amount/currency formats;
- transaction-reference patterns;
- phone/name parsing hints;
- layout tolerances.

Detection returns:

- selected template ID/version;
- provider confidence;
- matched anchors;
- fallback warning.

The generic template must permit extraction when no provider-specific layout is available.

## 7. Field extraction and normalisation

### 7.1 Canonical field schema

```json
{
  "provider_code": "GENERIC_MOMO",
  "transaction_reference": "ABC123456",
  "amount": "125.00",
  "currency": "GHS",
  "sender_name": "DEMO SENDER",
  "sender_phone": "+233240000002",
  "receiver_name": "DEMO RECEIVER",
  "receiver_phone": "+233240000001",
  "occurred_at": "2026-08-08T14:30:00Z",
  "status_text": "SUCCESSFUL"
}
```

Every field also has:

- raw candidate;
- canonical value;
- confidence;
- source token IDs/bounds;
- validation state;
- warnings;
- parser version.

### 7.2 Transaction reference

- normalise whitespace/separators/case only when the provider rules permit;
- preserve raw value;
- enforce provider/generic length and character checks;
- avoid replacing ambiguous characters automatically unless confidence and context justify it; otherwise flag review.

### 7.3 Amount

- recognise `GH₵`, `GHS`, currency symbol variants and thousands separators;
- parse with `Decimal`;
- reject negative/unreasonable formats according to validation, not fraud logic;
- retain two-decimal canonical string;
- avoid selecting fees/balance as transaction amount by using label/layout context.

### 7.4 Phone

- remove display separators;
- convert recognised `0XXXXXXXXX` Ghana format to `+233XXXXXXXXX`;
- validate digit count/prefix conservatively;
- preserve raw;
- display masked in non-owner/staff list contexts.

### 7.5 Date/time

- parse template-known formats first;
- retain raw date/time;
- record inferred timezone warning;
- reject impossible dates;
- store canonical UTC when possible;
- do not invent a year/date missing from the receipt without explicit warning.

### 7.6 Names

- Unicode normalisation;
- collapse whitespace;
- uppercase/casefold comparison copy;
- preserve display/raw;
- avoid aggressive phonetic correction;
- fuzzy comparison belongs to verification, not OCR overwrite.

## 8. OCR confidence

Field confidence can combine:

- source token confidences;
- regex/format validity;
- label association;
- template-region match;
- candidate ambiguity;
- cross-field consistency.

The exact formula is versioned and evaluated. Initial review threshold may be `0.75`, but must remain configurable.

Required-field accuracy evaluation:

- exact or normalised match per required field;
- field present/absent;
- macro/micro field accuracy;
- per-field accuracy;
- provider/template breakdown;
- unreadable/unsupported category.

The target of 90% is a goal, not a value to report until measured on the declared set.

## 9. User correction

The confirmed field snapshot is authoritative input to verification and structured features, but correction itself is evidence:

Suggested features:

- correction count;
- corrected critical-field count;
- magnitude of amount/reference change;
- confidence before correction;
- time spent/repeated confirmation, only if privacy-approved and genuinely useful.

Do not treat a normal user correction as fraud by itself.

## 10. Deterministic image evidence

### 10.1 Metadata

Capture only safe technical fields:

- format;
- dimensions;
- colour mode;
- EXIF presence;
- software/encoder string when present;
- screenshot-like dimensions/format hints.

Rules:

- no metadata -> neutral;
- editing-software metadata -> supporting evidence only;
- metadata conflicts with decoded image -> stronger inconsistency, still contextual.

### 10.2 Exact and near duplicate

- SHA-256 equality for exact duplicate;
- perceptual hash/Hamming distance for near duplicate;
- compare within authorised system scope;
- return counts/reuse reason without exposing another user's identity;
- distinguish repeated legitimate user re-upload from suspicious reference reuse through policy.

### 10.3 Recompression / ELA

Procedure:

1. convert a derived copy to a controlled JPEG quality;
2. calculate absolute difference;
3. normalise safely;
4. summarise global and regional statistics;
5. optionally retain a private visual derivative.

Features may include mean, max percentile, regional variance and connected high-error region count. ELA is weak on already recompressed screenshots and must not be treated as proof.

### 10.4 Noise residual consistency

- create denoised estimate;
- calculate residual;
- partition into regions;
- compare regional statistics;
- exclude blank/text-heavy regions where appropriate;
- mark not-applicable for tiny/overcompressed images.

### 10.5 Layout and text consistency

Using OCR boxes/template:

- expected label-value relative positions;
- line baseline deviation;
- character/box height variation;
- spacing irregularity;
- overlapping boxes;
- inconsistent alignment within one field;
- unexpected missing/duplicated regions;
- crop/completeness.

These are numerical features plus reason codes.

### 10.6 Evidence object

```json
{
  "code": "TEXT_ALIGNMENT_INCONSISTENCY",
  "extractor_version": "layout-1.0.0",
  "status": "TRIGGERED",
  "severity": "MEDIUM",
  "observed": {"baseline_deviation": 0.24},
  "threshold": {"baseline_deviation": 0.18},
  "confidence": 0.72,
  "reason": "Some transaction text is not aligned with nearby fields.",
  "limitations": []
}
```

## 11. Dataset manifest

Minimum columns:

- `sample_id`;
- `relative_path` or private object ID;
- `sha256`;
- `source_group_id`;
- `parent_sample_id`;
- `source_type`: real_authorised / synthetic / controlled_tamper;
- `provider_code`;
- `label`: genuine / suspicious / fraudulent, or binary image label;
- `tamper_operations`;
- `split`: train / validation / test;
- `consent_or_licence_reference`;
- `contains_personal_data`;
- `anonymisation_status`;
- `generated_seed`;
- `notes`.

The manifest itself must not expose private names/phones/references.

## 12. Controlled sample generation

A generator may create generic receipt layouts with fake values, timestamps and references. It must not falsely represent samples as actual MNO receipts.

Controlled manipulations:

- replace amount;
- replace transaction reference;
- replace name/phone;
- clone/paste a text region;
- crop header/footer;
- shift/misalign a field;
- alter font-size/weight;
- add inconsistent blur/noise;
- recompress;
- compose a near-duplicate with one critical change.

For each derived image:

- retain parent/source group;
- record operations and coordinates;
- use deterministic seed;
- keep parent and all derivatives in one split;
- never apply the generator to test data after the split to inflate sample count.

## 13. Label policy

### Image model

Initial task: binary `ORIGINAL/UNTAMPERED` versus `CONTROLLED_TAMPERED`. If real labels are uncertain, report the model only as controlled-tamper detection.

### Structured model

Three classes:

- `GENUINE`: labelled/controlled low-risk evidence with trustworthy source;
- `SUSPICIOUS`: ambiguous, incomplete, low-quality or conflicting evidence requiring review;
- `FRAUDULENT`: confirmed/controlled manipulation or appropriately adjudicated fraudulent sample.

Labels from automated rules alone must not be used as ground truth for a model that then claims independence from those rules. Record label provenance and reviewer agreement where real data is used.

## 14. Split and leakage prevention

1. Group by original/source receipt or event.
2. Assign groups to train/validation/test.
3. Freeze split files and hash them.
4. Fit imputer/encoder/scaler only on training.
5. Apply augmentation only to training.
6. Tune only with training/validation.
7. Use test once for final model report.
8. Keep repeated imports/near duplicates in the same group.
9. Record random seed and library versions.
10. Add an automated assertion that group intersections are empty.

For small data, use stratified group cross-validation for development while preserving a final group-held-out test set.

## 15. Structured feature schema

Version the exact list and ordering. Candidate features:

### OCR/field features

- required field coverage;
- mean/min critical-field confidence;
- provider confidence;
- critical correction count;
- total correction count;
- transaction-reference validity;
- amount validity;
- phone validity;
- timestamp validity;
- status-text consistency;
- OCR text density/length;
- template anchor coverage.

### Image/quality features

- blur/sharpness;
- contrast;
- aspect ratio/template deviation;
- crop/completeness;
- metadata inconsistency count;
- ELA summary values;
- noise regional variance;
- text alignment/box variation;
- exact duplicate count;
- nearest perceptual-hash distance;
- CNN tamper probability and availability flag.

### Verification features

- reference candidate found;
- amount match;
- currency match;
- sender/receiver phone match;
- sender/receiver name similarity;
- timestamp difference;
- reference status match;
- mismatch count;
- reused reference count.

### Missingness

Include explicit missing/not-applicable indicators rather than silently converting all missing evidence to zero.

Do not include:

- final human case decision when predicting pre-review risk;
- final risk class;
- user identity;
- raw phone/reference/name;
- features calculated using the test label;
- post-outcome information unavailable at prediction time.

## 16. Structured classifier

### 16.1 Baseline

Use a scikit-learn Pipeline with:

- column selection;
- numeric imputation;
- categorical encoding;
- optional scaling where relevant;
- `RandomForestClassifier` with class weights and deterministic random state.

Random Forest is selected because it handles nonlinear interactions and mixed engineered evidence and can provide useful feature-importance diagnostics, but its probabilities may require calibration.

### 16.2 Output

Three probabilities:

```json
{
  "GENUINE": 0.22,
  "SUSPICIOUS": 0.61,
  "FRAUDULENT": 0.17
}
```

For the scalar risk component:

`p_ml = P(FRAUDULENT) + 0.5 × P(SUSPICIOUS)`

Clamp to `[0,1]`. Store the full probability vector and scalar transformation version.

### 16.3 Calibration

Evaluate probability reliability. If calibration improves validation performance, use a documented calibration method trained only on training/validation data. Store calibration as part of the artifact pipeline.

### 16.4 Explainability

For users, provide evidence-based reason codes from input features/rules, not unstable raw feature importance. For staff/model cards, permutation importance or a documented compatible explanation may be reported on validation/test data. Avoid claiming causality.

## 17. CNN image classifier

### 17.1 Initial configuration

- input: configurable, initial 224×224 RGB;
- deterministic decode/resize/normalise;
- backbone: MobileNetV3Small or documented compatible transfer-learning model;
- head: global pooling, regularisation and binary output;
- loss: binary cross-entropy or documented alternative;
- metrics: precision, recall, F1 derived from predictions, PR-AUC where useful;
- class weighting/sampling based on training distribution;
- early stopping and best validation checkpoint.

### 17.2 Training stages

1. Train classification head with frozen backbone.
2. Optionally unfreeze a small top block with low learning rate.
3. Select checkpoint on validation criterion.
4. Evaluate once on held-out test.
5. Export `.keras` artifact and preprocessing metadata.
6. Hash and register.

### 17.3 Output

`p_img = P(TAMPERED)`.

If the model is not available:

- status `UNAVAILABLE`;
- `p_img` remains null;
- aggregation follows the partial-evidence policy;
- UI discloses that the image model did not run.

### 17.4 Heatmaps

Grad-CAM or similar may be generated for investigators as an exploratory aid. It must be labelled as model attention/supporting evidence, not the precise location/proof of editing.

## 18. Reference verification

### 18.1 Candidate lookup

Preferred:

1. canonical provider + transaction reference;
2. source-system ID when supplied;
3. safe provider-specific fallback only when documented.

A fuzzy transaction-reference lookup must never silently choose among multiple candidates. Return ambiguous/unverified and require review.

### 18.2 Field comparison

For each field store:

- extracted/confirmed value, masked where appropriate;
- reference value, masked;
- comparison mode;
- tolerance;
- match result;
- score/similarity;
- reason.

Suggested policy:

- reference: exact canonical match;
- amount: exact decimal or configured small tolerance only if justified;
- currency: exact;
- phone: exact E.164 when present;
- name: normalised exact first, then documented fuzzy threshold;
- timestamp: absolute difference within configured minutes/hours;
- status: provider-normalised mapping.

### 18.3 Status

- candidate missing/ambiguous -> `UNVERIFIED`;
- candidate found and all required available comparisons match -> `VERIFIED`;
- candidate found and any critical comparison mismatches -> `MISMATCH`;
- candidate found but data insufficient -> `UNVERIFIED` with warnings.

Verification version/tolerances are persisted.

## 19. Rule engine

Rules are versioned and declarative where practical.

Examples:

- `REFERENCE_AMOUNT_MISMATCH`;
- `REFERENCE_RECEIVER_PHONE_MISMATCH`;
- `RECEIPT_EXACT_DUPLICATE`;
- `RECEIPT_NEAR_DUPLICATE_CRITICAL_FIELD_CHANGED`;
- `TRANSACTION_REFERENCE_REUSED`;
- `CRITICAL_OCR_FIELDS_MISSING`;
- `TEMPLATE_LAYOUT_INCONSISTENT`;
- `TEXT_ALIGNMENT_INCONSISTENCY`;
- `HIGH_CNN_TAMPER_PROBABILITY`;
- `MULTIPLE_MEDIUM_IMAGE_SIGNALS`;
- `IMAGE_QUALITY_INSUFFICIENT`.

For each rule:

- code;
- description;
- feature dependencies;
- condition;
- severity;
- score contribution;
- user-safe reason;
- staff detail;
- enabled state.

The normalised rule component:

`p_rule = min(1, sum(triggered_contributions) / configured_rule_scale)`

or a documented equivalent. Store the exact version and triggered contributions.

## 20. Risk aggregation

### 20.1 Default preliminary formula

When all components are available:

`R = 100 × (0.40 × p_img + 0.40 × p_ml + 0.20 × p_rule)`

Initial class thresholds, until validation:

- `R < 35`: `GENUINE`;
- `35 ≤ R < 70`: `SUSPICIOUS`;
- `R ≥ 70`: `FRAUDULENT`.

These are configuration defaults, not validated conclusions. Validation may change weights/thresholds through a new rule-set version.

### 20.2 Partial-evidence policy

Do not blindly renormalise missing components in a way that overstates confidence.

Store:

- available components;
- missing components;
- raw weighted sum;
- coverage/confidence;
- final policy.

Suggested safe policy:

- missing a mandatory active model -> `PARTIAL`;
- calculate a provisional score from available evidence for staff;
- normal user receives conservative class/wording such as `SUSPICIOUS` or “Needs review” when high-confidence low-risk conclusion cannot be supported;
- verification remains separately displayed;
- top reason includes `ANALYSIS_COMPONENT_UNAVAILABLE`.

The exact policy is versioned and tested.

### 20.3 Reason selection

Rank triggered evidence by:

- severity;
- contribution;
- confidence;
- user relevance;
- non-duplication.

Return 2–4 user reasons plus full staff evidence. Never generate a reason unsupported by stored evidence.

## 21. Model registry and artifacts

### Structured model

Prefer a safer serialisation format such as `skops.io` where supported. If joblib/pickle is used, load only artifacts produced by the project and verified by hash; never load an arbitrary user upload.

### TensorFlow model

Use `.keras` format with explicit preprocessing metadata.

### Registry readiness checks

- file exists in private storage;
- SHA-256 matches;
- framework version is compatible;
- input/preprocessing schema matches runtime;
- smoke inference passes;
- model card/metrics present;
- status is `READY`.

Activation is an audited admin action. A worker caches active artifacts but responds to activation changes safely.

## 22. Evaluation reports

### OCR report

- dataset description and split;
- number of receipts;
- required-field accuracy;
- per-field accuracy;
- provider/template breakdown;
- confidence calibration/review threshold;
- failure examples;
- synthetic/real scope.

### Structured model report

- class distribution;
- group split;
- confusion matrix;
- per-class precision/recall/F1;
- macro F1;
- balanced accuracy;
- calibration;
- threshold selection;
- limitations;
- exact artifact/hash/commit.

### CNN report

- source types;
- split/group policy;
- class distribution;
- confusion matrix;
- precision/recall/F1;
- PR/ROC information where meaningful;
- calibration/threshold;
- CPU inference latency;
- controlled/synthetic limitation.

### End-to-end report

- risk/verification combinations;
- partial/failure rate;
- false-positive/false-negative analysis;
- reason-code correctness;
- stage timings;
- user/investigator evaluation.

## 23. Required automated ML/data tests

- manifest schema validation;
- duplicate hash detection;
- empty group intersection across splits;
- augmentation train-only assertion;
- feature schema hash stability;
- fit/test leakage guard;
- deterministic seed/reproducibility smoke;
- model artifact hash check;
- preprocessing parity;
- probability bounds/sum;
- threshold boundaries;
- missing-feature behaviour;
- absent/corrupt model behaviour;
- golden inference fixtures;
- evaluation report generation.

## 24. Scientific and product limitations to state

- performance depends on the representativeness and legality of the dataset;
- controlled synthetic edits do not cover all real fraud techniques;
- screenshots naturally undergo compression and metadata loss;
- ELA/noise/layout checks are supporting evidence, not proof;
- OCR errors can propagate if the user does not correct them;
- a reference record is only as trustworthy/current as its source;
- absence of a reference record is not evidence of fraud;
- a model trained only on generic/demo receipts must not claim provider-wide production accuracy;
- human review and authorised provider confirmation remain necessary for consequential cases.

## 25. Analytical definition of done

- [ ] controlled data and manifests exist;
- [ ] split-leakage tests pass;
- [ ] OCR fields/confidence/corrections persist;
- [ ] deterministic image evidence persists;
- [ ] verification field comparisons persist;
- [ ] structured model pipeline is reproducible and registered;
- [ ] CNN pipeline is reproducible and registered or explicitly unavailable;
- [ ] risk score is reconstructable;
- [ ] reasons map to evidence;
- [ ] historical versions are immutable;
- [ ] actual metrics and limitations are documented;
- [ ] end-to-end golden fixtures pass.

<!-- END FILE: 07_OCR_IMAGE_ML_VERIFICATION_SPEC.md -->


---

<!-- BEGIN FILE: 08_SECURITY_PRIVACY_AUDIT_SPEC.md -->

# 08 — Security, Privacy and Audit Specification

## 1. Security objectives

1. Only authenticated, authorised actors can access protected resources.
2. A normal user can access only their own receipts, analyses, reports, cases and notifications.
3. Private receipt and model artifacts are never public by default.
4. Uploaded files cannot execute code, escape storage paths or exhaust resources unchecked.
5. Authentication secrets and production credentials never enter Git, logs or client bundles.
6. Automated evidence and privileged decisions are traceable.
7. Model/data pipelines do not load untrusted executable artifacts.
8. Security failures degrade safely and are visible to operators.

## 2. Data classification

### Restricted

- original receipt images;
- unmasked phone numbers;
- full transaction references;
- reference-transaction raw rows;
- authentication/session/reset material;
- model/storage/database secrets;
- investigator notes containing personal information;
- private datasets.

### Confidential

- OCR text and field values;
- image evidence;
- fraud probabilities/features;
- verification comparisons;
- user profiles;
- case reports;
- audit metadata.

### Internal

- model/rule/template versions;
- operational metrics;
- non-sensitive logs;
- deployment architecture.

### Public

- generic help text;
- API liveness status with no infrastructure details;
- academic description and anonymised aggregate results.

Every API schema and UI view should be reviewed against this classification.

## 3. Threat model

### 3.1 Account and session threats

- credential stuffing/brute force;
- account enumeration;
- stolen refresh token;
- refresh-token reuse;
- weak password reset;
- session fixation;
- role escalation;
- disabled account retaining access;
- last-admin removal.

### 3.2 Object-access threats

- IDOR by changing transaction/report/case IDs;
- staff opening records outside purpose/role;
- report/signed URL reuse;
- private receipt path guessing;
- over-broad list/search endpoints;
- mass assignment of owner/role/status fields.

### 3.3 Upload and image threats

- renamed executable/non-image;
- polyglot content;
- corrupt parser payload;
- path traversal filename;
- decompression bomb/extreme dimensions;
- excessive CPU/memory image;
- animated/multi-frame abuse;
- malicious metadata;
- duplicate/replay flooding;
- SVG/script content (not accepted);
- storage orphan/inconsistent state.

### 3.4 API/web threats

- SQL injection;
- XSS from OCR text/import data/case notes;
- CSRF in cookie-authenticated portal;
- CORS misconfiguration;
- request smuggling/proxy header misuse;
- denial of service/rate abuse;
- insecure error messages;
- unbounded pagination/export;
- insecure direct file download;
- missing idempotency.

### 3.5 ML/data threats

- untrusted pickle/model deserialisation;
- artifact substitution;
- training-data leakage;
- poisoned labels/data;
- private dataset committed;
- model inversion/excessive raw output;
- fake metrics or stale model activation;
- feature-schema drift;
- adversarial/unsupported image causing unreliable confidence.

### 3.6 Operations/supply-chain threats

- leaked `.env`;
- vulnerable dependency;
- malicious package;
- excessive CI permissions;
- unsigned/unverified deployment;
- database backup exposure;
- public object-storage bucket;
- logs containing tokens/PII;
- production debug mode;
- stale credentials;
- missing rollback.

## 4. Authentication controls

- adaptive password hashing with a project-approved cost/parameters;
- password minimum policy and rejection of obviously invalid values;
- generic login/reset errors;
- per-IP and per-account-aware throttling without exposing account existence;
- short access-token lifetime;
- refresh-token rotation;
- server-side refresh-session revocation;
- refresh-family reuse detection;
- reset token:
  - cryptographically random;
  - stored as hash;
  - single use;
  - short expiry;
  - invalidated after password change;
- revoke sessions on account disable and sensitive role/password changes;
- `token_version` or equivalent invalidation;
- secure web refresh cookie:
  - HTTP-only;
  - Secure in non-local environments;
  - SameSite policy documented;
  - narrow Path/Domain;
- CSRF token/double-submit or equivalent for cookie-authenticated state changes;
- mobile credentials in Expo SecureStore only;
- no API secret embedded in mobile/admin.

Optional MFA is out of the minimum prototype unless time allows, but architecture must not prevent it.

## 5. Authorisation controls

### 5.1 Central policy

Every service method receives a principal and calls a policy/ownership function. Do not trust:

- `user_id` from request body;
- hidden UI routes;
- client role claims not verified by server token/database;
- object IDs as proof of access.

### 5.2 Ownership lookup

Use queries such as:

```text
SELECT ... WHERE id = :id AND user_id = :principal_id
```

or a policy-scoped repository. For normal users, a foreign object should generally appear as not found to avoid enumeration.

### 5.3 Staff access

- ADMIN: configuration, users, imports, audit and operational views.
- INVESTIGATOR: case/evidence needed for review.
- Combined role only when assigned.
- Every full evidence access by staff is audited.
- Default lists mask personal values.
- Bulk export is separately authorised and audited.

### 5.4 State/action authorisation

Permission depends on role, ownership and current state. Example: a user cannot edit OCR after final analysis; an investigator cannot decide a closed case without authorised reopen.

## 6. File-upload controls

Server-side sequence:

1. authenticate and rate limit;
2. enforce content length before reading all bytes where possible;
3. stream to a controlled temporary/private location;
4. ignore user path; generate object key;
5. allowlist extension;
6. inspect magic/decode content;
7. decode with safe library limits;
8. enforce dimensions/pixel count/frame count;
9. reject unsupported format/polyglot indicators;
10. strip or ignore dangerous metadata in derived copies;
11. calculate hash;
12. move/write immutable original to private storage;
13. create database rows transactionally;
14. delete temp file;
15. audit outcome.

Accepted formats: JPEG, PNG, WEBP. Do not accept SVG, PDF, HTML or office documents as receipt images in the MVP.

Suggested configurable defaults:

- max upload: 10 MB;
- max pixel count: 25–40 million, chosen after testing;
- minimum dimensions sufficient for OCR;
- request timeout;
- per-user/day upload rate appropriate to prototype testing.

Values are configuration and must be justified by performance tests.

## 7. Private file delivery

- No permanent public URL.
- API checks role/ownership before stream or signed URL.
- Signed URL expires quickly and is scoped to one object/method.
- `Content-Disposition` uses generated filename.
- Use `X-Content-Type-Options: nosniff`.
- Image response content type comes from validated stored metadata.
- Staff diagnostic variants require staff permission.
- Download/report/image access creates an audit event where required.
- Cache headers prevent unintended shared caching for sensitive files.

## 8. API security

- HTTPS outside localhost.
- Strict CORS allowlist; credentials only with explicit origins.
- Security headers for web portal/API responses where applicable.
- Request/body limits at proxy and Flask.
- Schema validation rejects unknown sensitive fields or uses explicit allowlists.
- ORM parameterisation; raw SQL only with bound parameters.
- Encode/escape all OCR/import/case text in React; never use unsafe HTML.
- CSRF for cookie-authenticated mutations.
- Rate limits:
  - login/reset/register;
  - upload/OCR/analyse;
  - report/export;
  - reference import;
  - case decisions/model activation.
- Pagination maximums and export row limits.
- Idempotency for retry-prone mutations.
- Consistent error messages; no debug mode or trace in production.
- Validate forwarded headers only behind configured trusted proxy.
- Timeouts for Tesseract, model inference, storage and external adapters.

## 9. Input validation

Examples:

- email canonical validation and length;
- password length/maximum to avoid hashing DoS;
- UUID parsing;
- enum allowlists;
- decimal amount range/precision;
- date range and timezone;
- phone canonicalisation;
- transaction-reference allowed length/characters;
- note/description length;
- CSV row/column/total size;
- JSONB configuration schema;
- risk weights non-negative and expected sum;
- thresholds ordered;
- model version/hash format;
- safe sorting/filter fields.

Reject unknown role/status/owner fields in normal requests.

## 10. Output encoding and XSS

OCR text, imported names and investigator notes are untrusted text.

- React renders text, not HTML.
- Never use `dangerouslySetInnerHTML` for evidence/case content.
- Generated PDFs escape content.
- CSV exports defend against formula injection by prefixing dangerous leading characters (`=`, `+`, `-`, `@`) according to export policy.
- Filenames are generated.
- Content Security Policy is set on the web portal where deployment permits.
- No secret values in source maps or build-time public environment variables.

## 11. Model artifact security

- Model upload/registration is ADMIN-only.
- Store artifacts privately.
- Verify SHA-256 before load.
- Restrict supported model types/formats.
- Prefer non-executable/safe serialisation.
- Never load a user-provided pickle/joblib object directly.
- Run smoke inference with bounded resources.
- Record framework versions.
- A corrupt/mismatched artifact becomes unavailable; it does not crash every request.
- Model activation is audited.
- Workers reload active model only after successful readiness verification.

## 12. Secrets management

`.env.example` contains keys, not real values.

Secrets include:

- database URL;
- JWT/session secrets;
- CSRF secret;
- object-storage credentials;
- notification-provider keys;
- email credentials;
- admin bootstrap password;
- error-monitoring DSN where sensitive.

Rules:

- no secrets in Git history;
- no secrets in issue/PR descriptions;
- no secrets in screenshots;
- no `EXPO_PUBLIC_`/`VITE_` variable for private keys;
- rotate a secret immediately if exposure is suspected;
- CI receives least-privilege secrets;
- production and staging secrets differ;
- local developer `.env` excluded.

## 13. Logging and redaction

Never log:

- passwords;
- access/refresh/reset tokens;
- full Authorization/Cookie headers;
- full receipt OCR text by default;
- full phone/reference;
- raw import rows;
- object-storage credentials;
- private signed URLs;
- raw model artifacts/features with identifiers.

Log safe:

- request ID;
- route/method/status/duration;
- actor ID, not email where possible;
- target IDs;
- stable error codes;
- stage timings;
- model/rule/template version IDs;
- safe aggregate counts.

Implement a logging filter/redaction helper and tests with representative sensitive payloads.

## 14. Audit-event catalogue

At minimum audit:

### Authentication

- login success/failure;
- logout;
- refresh reuse/revocation;
- password reset requested/completed;
- account disabled/enabled;
- session revoke.

### Evidence

- receipt uploaded/rejected/viewed/downloaded;
- OCR confirmed/corrected;
- analysis queued/completed/partial/failed;
- report generated/downloaded;
- user fraud report.

### Privileged

- staff evidence accessed;
- user/role changed;
- reference import uploaded/validated/committed;
- template/rule/model created/activated/retired/rolled back;
- case assigned/note/decision/reopen;
- audit/export accessed;
- configuration changed.

Audit metadata is minimised and append-only.

## 15. Privacy controls

### 15.1 Minimisation

Collect only fields necessary for receipt analysis, verification, user contact and audit. Do not collect wallet PIN, OTP, balance or unrelated SMS content.

### 15.2 Masking

Default display examples:

- phone: `+233 24 *** 0001`;
- reference: `ABC1••••56`;
- email in staff lists: partially masked where full value is unnecessary.

Owners may view confirmed details for their own receipt. Staff full access is role/purpose controlled and audited.

### 15.3 Research data

- consent/licence documented;
- anonymise names, phones and references;
- separate private raw and derived research data;
- do not commit raw data;
- dataset manifest stores permission reference;
- revoke/delete according to policy;
- synthetic samples clearly labelled.

### 15.4 Data subject/account actions

Implement configurable deactivation/deletion workflow. Do not promise legal rights or periods not defined by the institution; provide technical support for export, deactivation, anonymisation and scheduled deletion.

### 15.5 Human decision transparency

Store original automated result, reviewer outcome and reason separately. The user-facing status should indicate whether a human review occurred.

## 16. Availability and abuse controls

- per-route rate limits;
- per-user concurrent analysis cap;
- queue depth and stale worker monitoring;
- bounded image/model/Tesseract resources;
- worker process isolation from web workers;
- database query timeouts/limits where appropriate;
- report/export limits;
- retry with exponential backoff for transient storage/notification failure;
- circuit/degraded state for unavailable model;
- health/readiness and worker heartbeat;
- backup and restore.

Do not endlessly retry invalid input.

## 17. Dependency and CI security

- lock dependency versions;
- automated dependency audit;
- secret scanning;
- static lint/type analysis;
- minimal container image;
- non-root container user;
- no unnecessary compiler/dev tools in runtime image where practical;
- container/image vulnerability scan if available;
- least-privilege GitHub Actions permissions;
- pin third-party actions to trusted versions/commit policy;
- protect `main` with required CI review where repository settings permit.

## 18. Security test catalogue

### Authentication

- brute/rate limit;
- generic unknown-user response;
- expired/altered token;
- refresh reuse;
- reset reuse/expiry;
- disabled user;
- session revoke.

### Authorisation

- cross-user transaction/receipt/report/notification;
- user staff endpoint;
- investigator admin config;
- admin investigator decision when capability absent;
- object ID enumeration;
- last-admin safeguard;
- optimistic case/config conflict.

### Upload

- corrupt;
- renamed executable;
- fake MIME;
- path traversal filename;
- oversized bytes;
- extreme dimensions/decompression bomb;
- animated/multi-frame;
- unsupported SVG/PDF;
- duplicate/replay;
- storage failure cleanup.

### Web/API

- mass assignment;
- SQL/injection payloads;
- XSS strings in OCR/import/note;
- CSRF;
- CORS;
- unbounded page/export;
- CSV formula injection;
- unsafe error;
- request ID/log injection.

### Artifact/data

- corrupt model;
- wrong artifact hash;
- unsupported model format;
- feature schema mismatch;
- private dataset path committed;
- split leakage.

### Operational

- secret scan;
- public storage check;
- production debug disabled;
- HTTPS/security headers;
- backup access;
- stale worker recovery.

## 19. Incident response outline

1. Detect through logs/monitoring/user report.
2. Preserve relevant audit evidence.
3. Revoke affected sessions/credentials.
4. Disable compromised adapter/model/config if needed.
5. Contain private storage/database access.
6. Assess affected users/data.
7. Rotate secrets.
8. Patch and test.
9. Restore/verify service.
10. Document timeline, impact and corrective action.

Codex prepares the runbook; the institution defines notification/legal obligations.

## 20. Security release gate

Release is blocked by:

- public receipt/reference/model storage;
- cross-user access;
- staff role bypass;
- committed real secret;
- arbitrary model deserialisation;
- plaintext password/token;
- production debug trace;
- destructive untested migration;
- unresolved critical dependency vulnerability with reachable impact;
- false live-MNO/verification claim;
- audit absence for reviewer/configuration decisions.

No “temporary” bypass may remain enabled in staging/production.

<!-- END FILE: 08_SECURITY_PRIVACY_AUDIT_SPEC.md -->


---

<!-- BEGIN FILE: 09_TESTING_QA_RELEASE_PLAN.md -->

# 09 — Testing, QA and Release Plan

## 1. Testing objectives

The test programme must prove:

- business correctness;
- role and ownership isolation;
- upload and storage safety;
- reproducible OCR/ML behaviour;
- separation of fraud risk and verification;
- immutable history and human-review evidence;
- UI usability/accessibility;
- deployment reproducibility;
- honest performance and model metrics.

Testing is continuous. P18 is the final hardening phase, not the first time tests are written.

## 2. Root verification command

Codex must implement:

```bash
python scripts/verify.py --all
```

It should run or orchestrate, with clear section output and a non-zero exit code on failure:

1. repository/secret checks;
2. backend format/lint/type;
3. backend tests and coverage;
4. migration tests;
5. OpenAPI generation/contract drift check;
6. ML/data tests that do not require unavailable private data;
7. admin install/lint/type/test/build;
8. mobile install/lint/type/test;
9. selected E2E smoke when dependencies are running;
10. Docker/config validation.

Support narrower options such as `--backend`, `--admin`, `--mobile`, `--ml`, `--e2e`, `--security` and `--quick`.

The script must print the actual command, duration and outcome. It must not hide skipped tests.

## 3. Test environments

### Unit

No external network; use pure functions, temporary storage and database fixtures where appropriate.

### Integration

Real PostgreSQL in a test container/database, local private storage and Tesseract fixtures. Models may use tiny deterministic test artifacts.

### E2E local

Docker Compose API/worker/database plus admin/mobile test build.

### Staging

Managed services and private storage with safe synthetic data. No real private receipts unless explicitly authorised.

All tests must distinguish `passed`, `failed`, `skipped` and `blocked`.

## 4. Backend test structure

```text
services/api/tests/
├── unit/
│   ├── domain/
│   ├── policies/
│   ├── normalisation/
│   ├── ocr/
│   ├── image_analysis/
│   ├── verification/
│   ├── risk/
│   └── reports/
├── integration/
│   ├── auth/
│   ├── transactions/
│   ├── storage/
│   ├── ocr/
│   ├── analysis/
│   ├── imports/
│   ├── cases/
│   └── admin/
├── contract/
├── security/
├── performance_smoke/
└── fixtures/
```

## 5. Backend unit tests

### Domain/state

- every valid/invalid transaction state transition;
- every valid/invalid case transition;
- risk threshold boundaries;
- partial-evidence policy;
- reason ranking;
- money/phone/date/reference normalisation;
- field comparison tolerances;
- duplicate/reuse policy.

### Policies

Matrix tests for:

- anonymous;
- owner;
- foreign user;
- admin;
- investigator;
- combined staff;
- disabled account;
- assigned/unassigned case.

### OCR

- preprocessing deterministic shape/output metadata;
- parser fixtures;
- ambiguous amount/reference;
- confidence threshold;
- unknown template fallback;
- correction diff/audit;
- timeout/error mapping.

### Image

- hash/perceptual hash;
- metadata neutral behaviour;
- ELA/noise/layout features;
- original bytes unchanged;
- unsupported-quality not-applicable states;
- reason-code construction.

### ML runtime

- artifact hash;
- schema compatibility;
- unavailable/corrupt;
- probability validation;
- preprocessing parity fixture;
- cache reload after activation.

### Verification

- exact match;
- no candidate;
- multiple/ambiguous candidate;
- amount/currency/name/phone/time mismatch;
- unavailable field;
- reuse flags.

### Reports

- masking;
- escaping;
- deterministic evidence version;
- no cross-user content.

## 6. Backend integration/API tests

For each route:

- success;
- request schema;
- error envelope;
- authentication;
- role;
- ownership;
- state;
- idempotency;
- audit;
- response schema;
- no private keys/fields.

Critical flows:

1. register/login/refresh/logout/reset;
2. upload/private retrieval;
3. OCR/confirmation;
4. reference import/commit;
5. queue/worker/complete analysis;
6. history/detail/report;
7. user fraud report;
8. case review/decision;
9. template/rule/model activation;
10. audit/system status.

Use actual database constraints, not mocked repositories, for integration tests.

## 7. Migration tests

CI creates:

1. an empty database -> upgrade to head;
2. database at previous release revision -> seed representative data -> upgrade to head;
3. schema comparison/integrity test;
4. downgrade/upgrade smoke for reversible migration;
5. destructive migration guard where applicable.

Test active-version partial indexes, FK behaviour and money precision.

## 8. Storage/upload tests

- valid JPEG/PNG/WEBP;
- incorrect MIME;
- renamed non-image;
- corrupt/truncated;
- path traversal filename;
- null-byte/Unicode filename;
- oversized bytes;
- extreme dimensions/decompression bomb;
- multi-frame/animated;
- unsupported PDF/SVG;
- temporary/storage/database failure;
- duplicate exact and near duplicate;
- object access owner/admin/investigator/foreign;
- report/diagnostic variant access;
- orphan reconciliation;
- signed URL expiration where used.

## 9. Worker/concurrency tests

- two workers cannot claim the same queued run;
- heartbeat updates;
- stale run requeue;
- max retry;
- invalid input no retry;
- completed run never duplicated;
- idempotent analysis request;
- database/storage/model failure -> partial/failed;
- notification created once;
- worker shutdown leaves recoverable state.

Use PostgreSQL transactions and concurrency, not a mock-only queue test.

## 10. Mobile tests

### Unit/component

- validation schemas;
- auth/session store;
- SecureStore adapter;
- API error mapping;
- RiskBadge/VerificationBadge semantics;
- OCR field review;
- history filters;
- notification state;
- report/fraud-report form;
- offline/retry state.

### Integration/screen

- login/session restore/logout;
- camera/gallery permission branches;
- upload progress/retry;
- OCR review and correction;
- analysis polling/background resume;
- result combinations;
- history/detail/report;
- report suspicion;
- notification deep link.

### E2E

Use a supported Expo/React Native E2E approach. At minimum automate the primary Android journey against a test API. When full device automation is blocked, provide a documented manual script plus component/integration evidence; do not call it automated E2E.

## 11. Admin portal tests

### Unit/component

- route guards;
- permissions;
- forms/validation;
- tables/filters/pagination;
- status components;
- dialogs/optimistic version conflict;
- charts/tabular alternatives;
- evidence masking.

### Playwright E2E

- staff login;
- dashboard;
- reference import;
- case queue/detail/decision;
- user role change safeguards;
- rule/model/template activation;
- audit filter;
- system status;
- permission denial;
- session expiry.

Capture screenshots/traces only with safe data.

## 12. API contract testing

- OpenAPI generation is deterministic.
- Stored contract snapshot changes only intentionally.
- Generated TypeScript client is current.
- Response examples validate.
- Mobile/admin compile against generated types.
- No undocumented public endpoint.
- Backward-incompatible changes are flagged.

## 13. ML/data tests

### Data

- manifest required columns/types;
- file existence/hash;
- duplicate label conflict;
- source-group split disjointness;
- class distribution report;
- private-identifier scan;
- augmentation train-only;
- reproducible generation seed.

### Structured model

- feature schema/hash;
- train-only fit;
- pipeline serialisation;
- probability shape/bounds;
- deterministic smoke;
- held-out evaluation path;
- missing/extra feature rejection;
- threshold mapping.

### CNN

- decode/preprocessing parity;
- group split;
- train-only augmentation;
- artifact load/hash;
- output range;
- corrupt/unavailable;
- batch/single parity;
- latency benchmark.

### Evaluation

- confusion matrix totals equal test size;
- per-class metrics generated;
- macro F1 calculated from predictions;
- no placeholder values;
- report identifies synthetic/real scope;
- artifact/commit/dataset hash included.

## 14. Security testing

Run the catalogue in `08_SECURITY_PRIVACY_AUDIT_SPEC.md`.

Automated tools may include:

- dependency audits for Python and Node;
- secret scanner such as Gitleaks or project script;
- static analysis/lint;
- container scan where available;
- OWASP ZAP baseline against staging/local API/web;
- manual IDOR/RBAC/CSRF/CORS checks.

Tool output must be triaged. A scanner returning zero findings is not proof of security.

## 15. Performance testing

### 15.1 Scenarios

1. login;
2. history first page;
3. receipt upload;
4. OCR;
5. final analysis;
6. dashboard summary;
7. reference lookup;
8. case detail;
9. report generation/download.

### 15.2 Metrics

- request count;
- error rate;
- p50, p95, p99;
- CPU/memory;
- database query count/time;
- worker queue wait;
- stage timings;
- model inference time;
- image size.

### 15.3 Prototype targets

- login/history normal request: around or below 2 seconds;
- normal end-to-end receipt analysis: around 10 seconds under declared conditions;
- 25 concurrent analyses as a design/load target;
- 100,000 analysis records without schema redesign.

Record actual hardware, dataset/image size, worker count and build SHA. When a target is missed, identify the bottleneck and report the actual result.

### 15.4 Tool

Use Locust, k6 or a documented equivalent. Commit scripts, not generated private results. Reports use safe synthetic data.

## 16. Coverage targets

Targets, not an invitation to write low-value tests:

- backend overall line coverage: at least 85%;
- backend critical auth/ownership/upload/verification/risk/case modules: at least 90%;
- mobile/admin unit/component coverage: at least 70% for testable business modules;
- ML/data critical validation paths: direct tests for every gate.

Coverage exceptions require justification. Do not include generated code/vendor files.

## 17. Accessibility QA

### Automated

- admin axe checks on critical pages;
- lint rules for JSX accessibility;
- mobile accessibility props/component tests where supported.

### Manual

- keyboard-only admin journey;
- visible focus;
- screen-reader spot check;
- form error announcement;
- status not colour-only;
- dynamic text on mobile;
- contrast review;
- reduced motion;
- chart/table alternative.

Record issues and resolutions.

## 18. Visual/responsive QA

Test the viewports listed in the UI spec.

For each:

- screenshot;
- no console/runtime error;
- no overflow;
- no clipped form action;
- correct loading/empty/error state;
- status semantics consistent;
- sensitive data masked.

Use visual regression for critical pages where feasible. Review diffs before updating baselines.

## 19. Compatibility matrix

Record actual final tests for:

- Android versions/devices/emulators;
- iOS if built;
- Chrome;
- Edge;
- Firefox;
- Safari if available;
- API Python runtime;
- PostgreSQL version;
- Tesseract version;
- CPU architecture/container.

Do not claim untested compatibility.

## 20. User acceptance scripts

### UAT-01 — Genuine and verified

Upload safe fixture -> review fields -> analyse -> low risk + verified -> report.

### UAT-02 — Suspicious and unverified

Low-quality/ambiguous safe fixture -> partial/conflicting evidence -> unverified -> reasons.

### UAT-03 — Fraudulent/mismatch controlled sample

Controlled critical edit -> reference mismatch/image/rule evidence -> high risk/mismatch -> report case.

### UAT-04 — OCR correction

Incorrect low-confidence OCR -> user corrects -> analysis uses corrected snapshot -> original retained.

### UAT-05 — Investigator review

Open case -> inspect evidence -> add note -> decision with reason -> user notified -> original result unchanged.

### UAT-06 — Security

Foreign user attempts object/report -> denied; normal user attempts admin route -> denied.

UAT participants/results must be documented honestly.

## 21. Defect severity and release rules

- **Blocker:** app cannot run, data loss, false core claim.
- **Critical:** exploitable auth/data exposure, destructive migration, arbitrary model execution.
- **High:** core journey wrong/missing, incorrect risk/verification, broken case workflow.
- **Medium:** edge-case, accessibility, test/documentation gap.
- **Low:** minor UX/maintainability.

Release:

- zero blocker/critical;
- all high resolved or explicitly accepted by owner with mitigation;
- CI green;
- clean migration;
- safe staging smoke;
- final test report complete.

## 22. Final QA report template

`docs/qa/P18_TEST_REPORT.md` must include:

- repository and SHA;
- date/environment;
- dependency/runtime versions;
- commands;
- suite names;
- pass/fail/skip counts;
- coverage;
- model/OCR evaluation references;
- performance results;
- security scan/manual results;
- accessibility/visual results;
- known defects/risks;
- release recommendation;
- links/paths to safe evidence.

Never write “all tests pass” without the actual commands and counts.

<!-- END FILE: 09_TESTING_QA_RELEASE_PLAN.md -->


---

<!-- BEGIN FILE: 10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md -->

# 10 — GitHub Workflow and Codex Session Protocol

## 1. Purpose

This workflow preserves work, limits repeated context, makes each Codex session reviewable and prevents token loss from re-explaining the project.

The repository files are persistent memory. Codex must read status/handoff documents instead of relying on a previous chat transcript.

## 2. Branch model

- `main`: stable/release-ready.
- `develop`: optional integration branch when the owner chooses PR-based integration before `main`.
- `codex/pNN-short-description`: one phase branch.
- `codex/audit-fix-NN-short-description`: fixes from an independent audit.
- `hotfix/...`: only for an actual deployed release issue.

One branch should have one coherent purpose. Do not combine unrelated phase work.

## 3. Starting a session

Codex must execute and report:

```bash
git remote -v
git fetch --all --prune
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

Then:

1. read root `AGENTS.md`;
2. read `IMPLEMENTATION_STATUS.md`;
3. read the last session handoff;
4. inspect open PR/issue context when available;
5. verify the intended base branch/SHA;
6. check for unrelated modifications;
7. select one phase/sub-phase;
8. state the plan and requirement IDs;
9. create/switch branch.

Do not begin by reinstalling/rebuilding everything without first understanding repository state.

## 4. Working-tree safety

- Never discard a user's uncommitted changes.
- Never run destructive clean/reset commands without explicit approval.
- If unrelated changes exist, stop and report or isolate safely.
- Do not rewrite history or force push.
- Do not use `git add .` blindly before reviewing files.
- Inspect `git diff --check`, `git diff --stat`, and staged diff.
- Do not commit caches, datasets, raw receipts, secrets, reports containing PII, build output or large model artifacts.

## 5. Commit policy

Prefer small coherent commits that leave the branch testable. A phase may contain several commits, for example:

1. schema/migration;
2. backend behaviour/tests;
3. client UI/tests;
4. documentation/traceability.

Conventional commit structure:

```text
type(scope): imperative summary

Optional body:
- why the change was required
- important compatibility/security decision
- migration or rollout note
```

Types:

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `build`
- `ci`
- `chore`
- `perf`
- `security`

No “final”, “stuff”, “updates”, or misleading success language.

## 6. Push policy

At the end of every productive session:

```bash
git status --short
git diff --check
git log --oneline <base>..HEAD
git push -u origin <branch>
```

Codex reports:

- remote;
- branch;
- base SHA;
- head SHA;
- push command;
- push result.

If GitHub authentication/network is unavailable:

- create local commits;
- do not claim push;
- include exact push command for the user;
- mark `Push status: BLOCKED`;
- retain a clean, committed worktree where possible.

## 7. Pull requests

Create/update a draft PR per phase when connector/CLI access permits.

PR title:

```text
[P07] OCR preprocessing, field extraction and review
```

PR description uses `templates/PR_DESCRIPTION.md` and includes:

- scope and requirements;
- architecture/data/API changes;
- screenshots;
- migrations;
- tests and counts;
- security/privacy notes;
- known limitations;
- exact verification commands;
- checklist.

Do not mark ready for review while required phase gates fail.

## 8. CI required checks

Recommended check names:

- `repo-policy`
- `backend-lint-type`
- `backend-tests`
- `database-migrations`
- `openapi-contract`
- `ml-data-tests`
- `admin-quality-build`
- `mobile-quality`
- `security-secrets-dependencies`
- `docker-build`
- `e2e-smoke` when environment permits

Protect `main`/`develop` with required checks and review when repository settings permit.

## 9. Persistent session memory files

### `IMPLEMENTATION_STATUS.md`

Current phase, completed phases, requirement counts, branch/SHA, blockers and exact next task.

### `DECISION_LOG.md`

Every architectural or scope decision with context, options and consequence.

### `CHANGELOG.md`

User-visible/system-level changes, not every code refactor.

### `requirements_traceability.csv`

Requirement mapping and real test evidence.

### `docs/handoffs/YYYY-MM-DD-PNN-session.md`

Completed session handoff using the template.

Codex updates these before commit. A chat-only summary is insufficient.

## 10. Session size and token preservation

A session should target:

- one phase, or
- one vertical slice with a clear acceptance test.

When a phase is too large:

1. divide it into `P07A`, `P07B`, etc. in the status file;
2. keep one branch or create clearly dependent branches;
3. finish a compilable/testable boundary;
4. commit and push;
5. document the next exact file/test/task.

Do not attempt the entire project in one uncontrolled change. Re-reading only the relevant specs plus status is preferred to pasting the full plan into every prompt.

## 11. Required pre-commit review

Codex must inspect:

- new/changed files;
- generated files;
- secrets/private-data patterns;
- dependency changes;
- migration;
- public API changes;
- access-control paths;
- tests;
- docs/traceability;
- TODO/FIXME.

It must explain any large binary, generated artifact or dependency addition.

## 12. Required session verification

Run phase-specific tests and at minimum:

```bash
python scripts/verify.py --quick
```

When the phase changes core integrations, run:

```bash
python scripts/verify.py --all
```

A failing unrelated pre-existing test must be:

- verified as pre-existing at base SHA;
- recorded with evidence;
- not silently ignored;
- fixed when reasonably within scope or added as a blocker.

## 13. Handoff report

Every session writes a handoff containing:

- date/time;
- phase and scope;
- requirement IDs;
- base branch/SHA;
- work branch;
- final head SHA;
- changed files;
- migrations;
- API/schema/UI changes;
- tests with commands/counts;
- screenshots/evidence;
- security/privacy impact;
- known failures/blockers;
- next exact task;
- worktree status;
- push/PR status.

Use exact facts. “Tests passed” must include the command and count/output summary.

## 14. Final handoff

P20 completes `templates/FINAL_HANDOFF.md` and commits it at the final SHA. It includes:

- exact repo/branch/PR/SHA;
- full architecture;
- feature matrix;
- migrations;
- API docs;
- model/dataset cards;
- test/security/performance results;
- staging URLs/build IDs;
- test-account creation instructions;
- limitations and external blockers;
- reproduction commands;
- file paths to Chapter Four evidence;
- Git status and CI state.

## 15. Independent review loop

After a pushed milestone/final SHA:

1. owner provides repository name, branch/PR and SHA;
2. reviewer fetches exact files/PR/CI evidence;
3. reviewer returns findings by severity, file and acceptance criterion;
4. owner gives findings to Codex using `prompts/REPAIR_AFTER_AUDIT_PROMPT.txt`;
5. Codex creates an audit-fix branch;
6. each finding is mapped to commit/test;
7. Codex pushes and produces a repair handoff;
8. reviewer rechecks the new exact SHA.

Do not “fix” by merely changing the documentation when code is wrong.

## 16. Merge policy

Before merge:

- phase exit criteria complete;
- required checks green;
- migration reviewed;
- traceability updated;
- no secret/private data;
- PR diff reviewed;
- conflicts resolved without dropping changes;
- approved destination branch.

Use merge strategy chosen by owner. Preserve meaningful commit history or squash with a complete PR summary. Tag releases from the actual merged commit.

## 17. GitHub issues/backlog

Import or recreate `backlog.csv` as issues/milestones when useful. Each issue contains:

- task ID/phase;
- requirement IDs;
- acceptance criteria;
- dependencies;
- test evidence;
- status.

Close an issue only when the relevant commit is pushed and acceptance evidence exists.

## 18. Prohibited claims/actions

Codex must not:

- say it pushed without a successful push response;
- say CI passed without viewing the run/result;
- say deployed without a reachable deployment/build identifier;
- invent a PR URL;
- invent test counts;
- hide skipped tests;
- edit `IMPLEMENTATION_STATUS.md` to Done before implementation;
- force-push;
- commit `.env`, private receipts or live credentials;
- merge without instruction;
- continue on a different base SHA without documenting it.

<!-- END FILE: 10_GITHUB_WORKFLOW_AND_SESSION_PROTOCOL.md -->


---

<!-- BEGIN FILE: 11_DEPLOYMENT_RUNBOOK.md -->

# 11 — Deployment and Operations Runbook

## 1. Deployment targets

### Local development

- Docker Compose PostgreSQL;
- local private storage directory outside web root/repository;
- Flask API;
- separate analysis worker;
- React admin dev server;
- Expo mobile dev build;
- Tesseract installed in API/worker image.

### Staging

- containerised API;
- containerised worker from the same source image;
- managed PostgreSQL;
- private S3-compatible object storage;
- deployed React admin site;
- Expo internal Android build;
- HTTPS and environment-specific secrets;
- safe synthetic/demo data only.

### Production-like academic demonstration

May use the same architecture as staging. A full public production release is not required to claim implementation, but the configuration must not expose private receipts or secrets.

## 2. Environment separation

Use separate values for:

- database;
- JWT/session/CSRF secrets;
- storage bucket/prefix;
- allowed origins;
- admin accounts;
- model artifact paths;
- reference data;
- logging/monitoring;
- notification adapters.

Never point local/staging tests at production/private data by default.

## 3. Local bootstrap

Codex implements a cross-platform path:

```bash
cp .env.example .env
python scripts/doctor.py
python scripts/bootstrap.py
docker compose up -d postgres
# install API/ML/Node dependencies through documented commands
# run migrations and seed safe demo accounts/data
docker compose up api worker admin
```

Because Windows may be used, equivalent PowerShell-friendly commands must be documented. Avoid shell-only scripts as the sole path.

### Local services

Recommended compose services:

- `postgres`;
- `api`;
- `worker`;
- optional `admin` for production-like build;
- optional local object-storage emulator only when it does not complicate the MVP.

Mobile runs through Expo on host/device and uses a configured reachable API URL.

## 4. Docker image

Use one Python runtime image for API and worker with different commands.

Requirements:

- pinned Python base;
- system Tesseract packages/language data;
- OpenCV runtime libraries;
- non-root application user;
- dependency installation from lock/pin;
- only required runtime files;
- write access only to designated temp directory;
- health check;
- no source `.env`;
- model artifacts mounted/fetched privately, not baked with secrets;
- build metadata/commit label.

API command example conceptually:

```text
gunicorn "momo_fdvs:create_app()" --bind 0.0.0.0:$PORT --workers <measured>
```

Worker command conceptually:

```text
python -m momo_fdvs.worker run
```

Do not copy development caches, tests/private fixtures or local uploads into the runtime image unnecessarily.

## 5. Required environment variables

The actual contract is in `.env.example`.

Groups:

### Application

- environment;
- app version/build SHA;
- public API base;
- log level;
- trusted proxy setting.

### Database

- PostgreSQL URL;
- pool size/timeout;
- statement timeout where used.

### Auth

- JWT/access secret;
- refresh/session secret;
- CSRF secret;
- access/refresh/reset TTL;
- cookie domain/name/security;
- password hash parameters.

### CORS

- exact admin origins;
- mobile/API development origins where applicable;
- credentials policy.

### Storage

- adapter;
- local root or S3 endpoint/region/bucket/prefix;
- access credentials through secret manager;
- signed URL TTL;
- server-side encryption setting.

### Upload/OCR

- byte/dimension/pixel limits;
- Tesseract executable/language/timeouts;
- OCR confidence threshold.

### Models/risk

- model artifact root/bucket;
- active-model policy;
- worker concurrency;
- stage/retry/heartbeat timeouts;
- risk defaults only when no active database version exists.

### Notifications

- adapter enabled;
- provider credentials;
- sender identity;
- safe message settings.

### Observability

- error-monitoring DSN;
- metrics/log destination;
- PII-redaction mode.

## 6. Database release procedure

1. Verify backup.
2. Record current app and migration revision.
3. Deploy/run migration task once.
4. Check migration output and schema revision.
5. Run database readiness and a safe query.
6. Deploy API/worker compatible with the migration.
7. Run smoke tests.
8. Keep previous app image available.

Do not let every API instance run migrations at startup.

For a destructive migration, use the staged expansion/backfill/contraction policy from the database spec.

## 7. Model release procedure

1. Train/evaluate outside production web process.
2. Produce model card and artifact hash.
3. Upload to private artifact storage.
4. Register as `DRAFT`.
5. Verify hash/framework/schema/smoke inference.
6. Mark `READY`.
7. Administrator activates.
8. Workers reload after successful verification.
9. Monitor error/latency/result distribution.
10. Roll back to previous active version if needed.

No model activation is accomplished by replacing a file at an existing path without a new version record.

## 8. Rule/template release procedure

- create a draft version;
- validate configuration;
- test against safe fixtures/scenarios;
- record diff;
- activate transactionally;
- new analyses snapshot the new version;
- old analyses keep old version;
- rollback activates an earlier valid version and creates audit event.

## 9. Private object storage deployment check

- bucket/container is not public;
- public access block enabled where available;
- application credentials have only required prefix/action rights;
- server-side encryption enabled where available;
- signed URLs expire;
- CORS is narrow;
- lifecycle/retention configured;
- object key contains no PII;
- test unauthenticated URL fails;
- authorised download succeeds and is audited;
- backup/versioning policy documented.

## 10. Admin web deployment

- build with only public configuration such as API origin;
- never inject private secrets into `VITE_*`;
- HTTPS;
- security headers/CSP;
- source-map policy documented;
- correct refresh-cookie domain/SameSite/CSRF configuration;
- SPA route fallback;
- environment indicator on staging;
- error monitoring contains no sensitive data.

## 11. Mobile build

Use Expo EAS or the selected official build path.

Required:

- app identifier/package name;
- staging and release profiles;
- API URL per profile;
- no private API key in bundle;
- permissions limited to camera/gallery/network needed;
- privacy copy;
- version/build number;
- internal Android build for evaluation;
- iOS build only when account/access available;
- secure token storage;
- release notes and tested device matrix.

Do not embed storage/database/model credentials.

## 12. CORS, cookie and domain matrix

Document explicit values:

| Environment | Admin origin | API origin | Secure cookie | SameSite | CSRF |
|---|---|---|---:|---|---|
| Local | localhost dev URL | localhost/LAN API | false only for local | documented | enabled/testable |
| Staging | staging admin HTTPS | staging API HTTPS | true | documented | required |
| Production | production admin HTTPS | production API HTTPS | true | documented | required |

Mobile bearer-token requests do not require browser cookies, but API CORS and token security still apply.

## 13. Health and monitoring

### Health endpoints

- liveness;
- readiness;
- version/build;
- component matrix.

### Monitor

- API error rate/latency;
- database connectivity/pool;
- worker heartbeat;
- queued/stale analyses;
- stage failure/latency;
- storage failures;
- active model readiness;
- report/notification failure;
- disk/temp use;
- security/auth anomalies.

Alerts contain safe IDs, not receipt text or full transaction details.

## 14. Backup and restore

### Database

- managed backups or scheduled encrypted `pg_dump`;
- retention configured;
- restore to isolated environment;
- verify migration and row counts;
- test application against restored data.

### Storage

- versioning/lifecycle where available;
- inventory;
- restore selected test objects;
- reconcile hashes/database references.

### Models/config

- model artifact and cards backed up;
- database versions retain activation history;
- restore verifies SHA.

Document the last rehearsal date/result.

## 15. Staging smoke checklist

- [ ] API health/ready/version;
- [ ] database migration revision;
- [ ] admin login;
- [ ] mobile login;
- [ ] private upload;
- [ ] OCR review;
- [ ] stored reference import;
- [ ] full analysis result;
- [ ] risk/verification separation;
- [ ] history/report;
- [ ] user fraud report;
- [ ] investigator decision;
- [ ] audit entries;
- [ ] unauthorised object access denied;
- [ ] private object not public;
- [ ] worker recovery/heartbeat;
- [ ] no console/server secret leak.

Use only safe test data.

## 16. Release identifiers

Every release records:

- Git commit SHA;
- Git tag;
- API image digest;
- worker image digest;
- admin build ID;
- mobile build/version;
- database migration revision;
- active model IDs/hashes;
- active rule/template versions;
- OpenAPI contract hash;
- deployment timestamp;
- operator.

## 17. Rollback

### Application

Redeploy previous image/build after confirming database compatibility.

### Database

Prefer forward fix. Use downgrade only when migration is explicitly reversible and data safety verified. Document irreversible migrations.

### Model/rule/template

Activate previous verified version. Do not delete the problematic version; mark failed/retired and preserve audit.

### Mobile

Internal testing can install previous build. Public-store rollback constraints must be documented if applicable.

### Storage

Do not delete new originals during application rollback. Preserve evidence and reconcile after service stabilises.

## 18. Deployment blockers

A deployment may be blocked by:

- no GitHub/deployment account access;
- no database/object-storage credentials;
- no mobile signing/build account;
- no production domain;
- no authorised model/reference artifacts.

Codex must still deliver:

- manifests/config templates;
- Docker image build;
- local/staging-like verification;
- exact environment variables;
- exact commands;
- clear blocker/owner/next action.

It must not claim a deployment that did not occur.

## 19. Production-readiness limitations

The final document must state any:

- synthetic-only model evaluation;
- absent live MNO integration;
- unavailable push/email adapter;
- missing iOS build;
- unmeasured availability;
- incomplete legal retention policy;
- limited provider templates;
- performance target miss;
- manually executed rather than automated operation.

## 20. Release checklist

- [ ] P18 test report approved;
- [ ] zero blocker/critical security defects;
- [ ] secrets scan;
- [ ] backup verified;
- [ ] migration reviewed;
- [ ] private storage check;
- [ ] model/rule/template readiness;
- [ ] staging smoke;
- [ ] release identifiers recorded;
- [ ] rollback plan;
- [ ] final handoff updated;
- [ ] exact SHA pushed and CI green.

<!-- END FILE: 11_DEPLOYMENT_RUNBOOK.md -->


---

<!-- BEGIN FILE: 12_FINAL_INSPECTION_PROTOCOL.md -->

# 12 — Final Independent Inspection Protocol

## 1. Purpose

This protocol defines the handoff from Codex implementation to an independent repository inspection. It prevents a vague “finished” claim and makes the repair loop efficient.

An inspection is performed against an **exact pushed commit SHA**. A branch name alone is insufficient because it can move.

## 2. Owner handoff

Provide:

- GitHub repository in `owner/repository` form;
- target branch;
- pull-request number or URL when available;
- exact final commit SHA;
- base SHA/branch;
- Codex `FINAL_HANDOFF.md`;
- CI run/status at that SHA;
- staging API/admin URLs when deployed;
- mobile build identifier/download mechanism where appropriate;
- safe test-account creation instructions;
- known external blockers;
- any private evidence that cannot be placed in Git, described without revealing secrets.

Do not send passwords, API keys or database credentials in chat. Use safe test accounts or credential-entry instructions.

## 3. Inspection scope

### A. Repository integrity

- exact SHA exists remotely;
- work described in handoff exists;
- no unexpected generated/binary/private data;
- no secret patterns;
- branch/PR history coherent;
- status/decision/changelog current.

### B. Requirements traceability

- every MUST requirement has implementation path and test;
- no “Done” without evidence;
- scope matches Chapter Three;
- no live-MNO claim;
- risk/verification separation throughout.

### C. Architecture

- monorepo/modules match intended layers;
- Flask app factory/blueprints/services/repositories/policies;
- no controller-heavy ML/SQL;
- private storage abstraction;
- worker/job safety;
- generated API contract/client;
- configuration/secrets separation.

### D. Database

- migrations;
- constraints/multiplicities;
- active version uniqueness;
- immutable evidence;
- OCR correction history;
- reference import and verification;
- model/rule/template versions;
- case decision separation;
- audit;
- indexes;
- retention/backup documentation.

### E. API and access control

- auth/refresh/reset;
- RBAC;
- ownership/IDOR;
- state transitions;
- idempotency;
- validation/error envelope;
- private file/report access;
- staff actions/audit;
- pagination/export limits.

### F. Mobile UI

- auth;
- upload;
- OCR review;
- analysis progress;
- risk/verification result;
- evidence;
- history/report;
- fraud report;
- notifications/profile;
- secure token storage;
- loading/error/offline/accessibility.

### G. Admin/investigator UI

- role-aware shell;
- dashboard;
- transactions;
- cases/reasoned decision;
- users/roles;
- reference import;
- templates/rules/models;
- reports/audit/status;
- responsiveness/accessibility;
- private evidence access.

### H. OCR/image/ML/verification

- reproducible OCR;
- field confidence/correction;
- deterministic evidence;
- data manifest/splits;
- no leakage;
- actual metrics;
- artifact hashes/version registry;
- unavailable-model behaviour;
- verification field comparisons;
- risk reconstruction/reasons;
- limitations.

### I. Security/privacy

- upload controls;
- private storage;
- secret/client-bundle safety;
- auth/session;
- CSRF/CORS;
- XSS/export;
- model deserialisation;
- logs/redaction;
- staff access audit;
- dependency/secret scans.

### J. Tests/CI/performance/deployment

- test commands/results;
- clean migration;
- coverage;
- E2E;
- security;
- performance;
- staging smoke;
- image/build/migration identifiers;
- rollback.

### K. Documentation/academic evidence

- implemented diagrams match code;
- no crisscrossing/invalid multiplicities in final exported diagrams;
- wireframes distinguished from actual interfaces;
- Chapter Four screenshots/evaluation available;
- no unsupported claims.

## 4. Inspection methods

Depending on available access, the reviewer may:

- fetch repository files at the exact SHA;
- inspect PR diff and issue/CI results;
- search for code patterns, TODOs, secrets and endpoints;
- compare migrations/models/API/UI/tests;
- review screenshots/reports;
- run the repository locally when files/runtime access is available;
- exercise staging with safe credentials;
- inspect model/dataset reports and hashes.

A repository-only review cannot prove a deployment is reachable or that private artifacts exist; those items require the corresponding evidence.

## 5. Finding severity

### BLOCKER

- repository cannot be reproduced/run;
- primary user journey absent;
- destructive data loss;
- false implementation/deployment claim;
- final SHA not pushed.

### CRITICAL

- cross-user/staff bypass;
- public private receipt/reference data;
- committed live secret;
- plaintext passwords/tokens;
- arbitrary untrusted model execution;
- invalid destructive migration;
- fraud/verification outputs fundamentally wrong.

### HIGH

- major requirement missing;
- OCR/analysis/case flow broken;
- no version/evidence traceability;
- model/data leakage or fabricated metrics;
- no safe partial state;
- reference verification misrepresented as live;
- tests/CI not reproducible.

### MEDIUM

- important edge case;
- incomplete accessibility/error state;
- weak audit/test coverage;
- performance problem;
- documentation/schema mismatch.

### LOW

- maintainability;
- minor UX/copy;
- optimisation;
- non-critical documentation improvement.

## 6. Finding format

```markdown
### FINDING-ID — Title

**Severity:** High  
**Requirement(s):** FR-...  
**Location:** `path/to/file.py:L10-L42`  
**Evidence:** What was observed and how it was verified.  
**Impact:** What can go wrong.  
**Required correction:** Exact expected behaviour.  
**Acceptance test:** Command/scenario that proves the fix.  
**Suggested Codex phase:** Audit fix N.
```

Findings must distinguish:

- verified defect;
- probable defect requiring runtime confirmation;
- missing evidence;
- improvement.

## 7. Inspection report structure

1. Executive verdict.
2. Reviewed repository/branch/SHA.
3. Evidence available/unavailable.
4. Requirement completion summary.
5. Findings by severity.
6. Security/privacy assessment.
7. OCR/ML/data-methodology assessment.
8. UI/UX assessment.
9. Test/CI/deployment assessment.
10. Release recommendation.
11. Codex repair prompt.
12. Reinspection requirements.

## 8. Repair loop

For each finding Codex must:

1. reproduce/confirm;
2. map to requirement;
3. create `codex/audit-fix-NN-...`;
4. implement code/schema/docs as needed;
5. add regression test;
6. run relevant and full verification;
7. update traceability/status/changelog;
8. commit/push;
9. provide a finding-by-finding resolution table and new SHA.

A documentation-only change does not resolve a code/security defect.

## 9. Reinspection

Provide the new exact SHA. The reviewer verifies:

- the original finding;
- regression test;
- no introduced regression;
- CI status;
- changed requirements/docs;
- new deployment when needed.

The report marks each finding:

- Resolved;
- Partially resolved;
- Not resolved;
- Not verifiable;
- Accepted risk by owner.

## 10. Final acceptance

Recommend acceptance only when:

- no blocker/critical remains;
- high findings are resolved or explicitly accepted with mitigation;
- clean-clone/full verification evidence exists;
- final product journeys work;
- private data is protected;
- analytical claims are reproducible and limited to their evidence;
- exact final SHA is pushed;
- handoff and Chapter Four evidence are complete.

## 11. Important operational note

The reviewer does not automatically monitor GitHub or perform background work. After each desired milestone or final Codex session, the owner must provide the repository/branch/SHA or return with the handoff. The structured handoff keeps that message very short.

<!-- END FILE: 12_FINAL_INSPECTION_PROTOCOL.md -->


---

<!-- BEGIN FILE: 13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md -->

# 13 — Documentation and Chapter Four Evidence Plan

## 1. Purpose

Chapter Three presents proposed architecture, logical designs, UML, algorithms and low-fidelity wireframes. Chapter Four should present what was actually implemented, how it was implemented, and objective evidence from tests/evaluation.

Codex must collect implementation evidence as work progresses rather than trying to reconstruct it after completion.

## 2. Document truth rules

- Proposed design and actual implementation must be distinguishable.
- A feature not implemented must be labelled planned/partial, not described in past tense as complete.
- A test/metric must have a command/report and exact SHA.
- A deployment must have a build identifier/reachable evidence.
- Live MNO confirmation must not be claimed.
- Wireframes are not system interfaces.
- Actual system screenshots belong in implementation/results sections.
- Diagrams must match code/database and have clear routed connectors with no lines passing through boxes, actors, ellipses or text.

## 3. Evidence directory

Recommended:

```text
docs/evidence/
├── README.md
├── build/
├── api/
├── database/
├── mobile/
├── admin/
├── ocr/
├── image-analysis/
├── ml/
├── verification/
├── security/
├── testing/
├── performance/
└── deployment/
```

Each evidence item records:

- title;
- date;
- repository SHA;
- environment/build;
- command or steps;
- result;
- screenshot/report path;
- limitations;
- whether safe for academic submission.

Never store credentials or private receipts in evidence.

## 4. Architecture evidence

Capture:

- final repository tree;
- Flask app factory and blueprint registration;
- service/repository/policy boundaries;
- Docker Compose/container topology;
- worker queue/claim logic;
- private storage adapter;
- OpenAPI generation;
- deployment diagram.

Create a final implemented architecture diagram, separate from the original proposed diagram if material changes occurred.

## 5. Database evidence

Capture:

- migration history;
- final implemented ERD;
- table/constraint/index summary;
- sample anonymised rows;
- migration from clean database;
- active model/rule/template relationships;
- OCR original/correction relationship;
- analysis/version relationship;
- verification/reference relationship;
- case decision separate from automated result;
- audit append-only evidence.

### Diagram quality checklist

- entity names singular/plural consistently;
- PK/FK identified;
- crow's-foot/cardinality correct;
- no line crosses an entity box;
- minimal crossings overall;
- related entities grouped;
- legend;
- matches migration/schema exactly;
- readable at submission size.

## 6. UML evidence

### Use case

Separate:

- user/mobile use cases;
- administrator/investigator use cases.

Requirements:

- system boundary labelled;
- actors outside boundary;
- associations terminate at the correct ellipse;
- `include` only for compulsory reused behaviour;
- `extend` only for optional/conditional behaviour;
- no connector through another ellipse/text;
- use-case description table for every actor and use case.

### Class diagram

Use implemented domain classes, not every framework class.

Requirements:

- attributes and operations;
- visibility symbols;
- correct inheritance;
- relationship type;
- multiplicities;
- readable grouping;
- no crisscrossing through class boxes;
- mapping to database/service classes explained.

### Activity/sequence

Capture implemented flows:

- receipt upload/OCR review;
- final analysis;
- reference import;
- case decision.

Sequence participants should match actual mobile/admin/API/service/worker/database/storage interactions.

## 7. Mobile interface evidence

Capture at least:

1. Login.
2. Registration/reset.
3. Home.
4. Receipt source.
5. Preview/quality.
6. OCR progress/review.
7. Analysis progress.
8. Genuine + Verified.
9. Suspicious + Unverified.
10. Fraudulent + Mismatch controlled scenario.
11. Partial analysis.
12. Evidence detail.
13. History/detail.
14. Report.
15. Fraud report.
16. Notifications.
17. Profile/help.

For each screenshot:

- use fake/anonymised data;
- remove notification bars/device IDs when unnecessary;
- label screen name;
- show actual UI, not Figma wireframe;
- record device/viewport and SHA;
- ensure no debug overlay/console error.

## 8. Admin/investigator interface evidence

Capture:

- login;
- dashboard;
- transactions;
- case queue;
- case evidence;
- decision confirmation with required reason;
- users/roles;
- reference import preview/errors/commit;
- templates;
- rules/thresholds;
- model registry/card;
- reports;
- audit logs;
- system status;
- permission-denied page;
- tablet/desktop responsive examples.

## 9. OCR implementation evidence

Include:

- original safe fixture;
- selected preprocessing variants;
- OCR raw/token output sample;
- parsed fields/confidence;
- correction audit;
- unknown-template fallback;
- field-accuracy evaluation table;
- common failure examples;
- Tesseract/pipeline versions.

Do not use only perfect examples.

## 10. Image analysis evidence

For controlled safe samples:

- exact/near duplicate;
- metadata evidence;
- ELA/recompression summary;
- noise/layout features;
- OCR alignment;
- reason codes;
- optional investigator derivative;
- limitations.

Label forensic images as diagnostic/supporting evidence.

## 11. ML evidence

### Dataset

- dataset card;
- source/synthetic distribution;
- label provenance;
- group split;
- class distribution;
- anonymisation/permission;
- split hash;
- leakage-test result.

### Structured model

- pipeline;
- features;
- hyperparameters;
- confusion matrix;
- per-class metrics;
- macro F1;
- calibration;
- model card;
- artifact hash;
- training commit;
- limitation.

### CNN

- architecture/transfer learning;
- augmentation;
- training curves;
- confusion matrix;
- per-class metrics;
- inference time;
- model card;
- artifact hash;
- synthetic/controlled limitation.

No metric appears without its evaluation set and command/report.

## 12. Verification evidence

Demonstrate:

- CSV template;
- import validation;
- valid/invalid row report;
- committed batch;
- VERIFIED case;
- UNVERIFIED case;
- MISMATCH case;
- field-level comparison;
- reuse indicator;
- UI wording “stored/imported reference records”;
- no live-MNO claim.

## 13. Risk aggregation evidence

Show:

- versioned formula/weights;
- threshold version;
- component probabilities;
- rule contributions;
- computed score;
- top reasons;
- class boundary tests;
- partial evidence;
- historical stability after model/rule activation change.

Use a worked safe example whose arithmetic can be checked.

## 14. Security evidence

Include:

- password hash row (never password);
- token/secret storage design;
- role/ownership tests;
- invalid upload tests;
- private storage access;
- CSRF/CORS configuration;
- secret scan;
- dependency audit;
- log redaction test;
- model artifact hash check;
- audit events;
- no public receipt URL.

Do not publish exploit credentials or private data.

## 15. Testing evidence

- suite inventory;
- commands;
- pass/fail/skip counts;
- coverage;
- CI run at SHA;
- clean migration;
- E2E traces;
- UAT results;
- defects fixed;
- compatibility matrix;
- final QA report.

Screenshots of a terminal are supporting evidence; commit-linked reports and test output are stronger.

## 16. Performance evidence

- environment/hardware/container;
- image sizes;
- worker count;
- scenario scripts;
- p50/p95/error rate;
- stage timings;
- 25-concurrency result or actual measured limit;
- query plans/indexes;
- bottlenecks/optimisations;
- target misses honestly stated.

## 17. Deployment evidence

- staging URLs (where safe);
- app/build IDs;
- API image digest;
- database migration revision;
- active model/rule/template versions;
- health/readiness;
- private object check;
- smoke results;
- rollback rehearsal;
- deployment blocker if credentials unavailable.

## 18. Suggested Chapter Four structure

1. Introduction.
2. Development environment and repository structure.
3. Database implementation.
4. Backend/API implementation.
5. Mobile application implementation.
6. Administrator/investigator portal.
7. OCR pipeline.
8. Image-analysis implementation.
9. Dataset and model development.
10. Reference verification.
11. Risk aggregation/explainability.
12. Security and privacy implementation.
13. Testing/evaluation.
14. Deployment.
15. Limitations.
16. Chapter summary.

Follow the institution's approved final structure if it differs.

## 19. Final evidence manifest

Codex creates `docs/evidence/EVIDENCE_MANIFEST.csv`:

- evidence_id;
- requirement_id;
- chapter_section;
- title;
- file_path;
- type;
- SHA;
- environment;
- contains_sensitive_data;
- safe_for_submission;
- notes.

The final handoff points to this manifest.

## 20. Documentation acceptance checklist

- [ ] proposed vs implemented wording correct;
- [ ] no unsupported metrics;
- [ ] no live MNO claim;
- [ ] wireframes separate from interfaces;
- [ ] final UML/ER diagrams match implementation;
- [ ] no diagram crisscrossing through interfaces;
- [ ] screenshots safe and labelled;
- [ ] tests/metrics tied to SHA;
- [ ] limitations explicit;
- [ ] evidence manifest complete.

<!-- END FILE: 13_DOCUMENTATION_AND_CHAPTER4_EVIDENCE.md -->


---

<!-- BEGIN FILE: IMPLEMENTATION_STATUS.md -->

# IMPLEMENTATION_STATUS.md

> Codex must update this file at the end of every session. Do not mark a phase complete without its exit criteria and pushed evidence.

## Current repository state

- Repository: `TBD`
- Default branch: `TBD`
- Current work branch: `TBD`
- Base SHA: `TBD`
- Head SHA: `TBD`
- Last updated: `TBD`
- CI status: `Not configured`
- Deployment status: `Not deployed`
- Current phase: `P00 — Not Started`
- Next exact task: `Run repository preflight and complete P00 gap analysis.`

## Phase status

| Phase | Name | Status | Branch/PR | Head SHA | Verification evidence | Blocker/notes |
|---|---|---|---|---|---|---|
| P00 | Repository preflight, scope lock and execution foundation | Not Started |  |  |  |  |
| P01 | Monorepo, API skeleton and local infrastructure | Not Started |  |  |  |  |
| P02 | Relational schema, migrations, seeds and private storage abstraction | Not Started |  |  |  |  |
| P03 | Authentication, session security, ownership and RBAC | Not Started |  |  |  |  |
| P04 | Mobile application shell, design system and authentication experience | Not Started |  |  |  |  |
| P05 | Administrator and investigator web portal shell | Not Started |  |  |  |  |
| P06 | Receipt capture, hostile-file validation and private upload | Not Started |  |  |  |  |
| P07 | OCR preprocessing, extraction, confidence and correction workflow | Not Started |  |  |  |  |
| P08 | Reference-record import and transaction verification | Not Started |  |  |  |  |
| P09 | Deterministic image-forensics and manipulation evidence | Not Started |  |  |  |  |
| P10 | Dataset governance, controlled sample generation and reproducible splits | Not Started |  |  |  |  |
| P11 | Structured-feature fraud classifier | Not Started |  |  |  |  |
| P12 | CNN receipt-tampering classifier | Not Started |  |  |  |  |
| P13 | End-to-end analysis orchestration, rules and risk aggregation | Not Started |  |  |  |  |
| P14 | History, search, downloadable reports and notifications | Not Started |  |  |  |  |
| P15 | Fraud reporting, investigation and governance administration | Not Started |  |  |  |  |
| P16 | Operational dashboard, analytics, audit and system status | Not Started |  |  |  |  |
| P17 | UI completion, accessibility, responsive and visual QA | Not Started |  |  |  |  |
| P18 | Full hardening, security, performance and regression QA | Not Started |  |  |  |  |
| P19 | Staging deployment, release engineering and rollback | Not Started |  |  |  |  |
| P20 | Final documentation, evidence, cleanup and inspection handoff | Not Started |  |  |  |  |

Allowed status values: `Not Started`, `In Progress`, `Blocked`, `In Review`, `Complete`.

## Requirements summary

- MUST requirements complete: `0 / TBD`
- SHOULD requirements complete: `0 / TBD`
- Blocked requirements: `None recorded`
- Traceability file last verified: `Not yet`

## Current blockers

| ID | Phase | Blocker | Impact | Owner/input needed | Safe fallback | Next action |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Active known limitations

- No live MNO integration is part of the prototype.
- Real/supervisor-approved receipt dataset and production reference source are not yet supplied.
- Brand/deployment credentials are not yet supplied.

## Last completed session

- Handoff file: `None`
- Summary: `No implementation session recorded.`

## Next session startup

1. Read `AGENTS.md` and this file.
2. Fetch/prune and verify the current SHA/worktree.
3. Read the last handoff.
4. Continue only the next exact task or clearly update this file before changing direction.

<!-- END FILE: IMPLEMENTATION_STATUS.md -->


---

<!-- BEGIN FILE: DECISION_LOG.md -->

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

<!-- END FILE: DECISION_LOG.md -->


---

<!-- BEGIN FILE: CHANGELOG.md -->

# CHANGELOG.md

All notable project changes are recorded here. Use semantic sections and link each entry to the phase/PR/commit when available.

## Unreleased

### Added

- Initial implementation package, scope, requirements, architecture, database, API, UI, analytical, security, test, GitHub, deployment and inspection specifications.

### Changed

- None.

### Fixed

- None.

### Security

- Initial secure-development requirements established.

## Release entry template

## [version] — YYYY-MM-DD

### Added
### Changed
### Fixed
### Security
### Known limitations

**Repository SHA:**  
**Migration revision:**  
**Active model/rule/template versions:**  
**Deployment/build IDs:**

<!-- END FILE: CHANGELOG.md -->
