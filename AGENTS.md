# AGENTS.md — Mandatory Codex Instructions

These instructions apply to the entire repository. A more specific `AGENTS.md` in a subdirectory may add constraints but may not weaken these rules.

## 0. Current completion override

Before any task, read `FINAL_COMPLETION_OVERRIDE.md` and `IMPLEMENTATION_STATUS.md`.
The final override supersedes stale next-step instructions in historical master plans,
handoffs, completed Superpowers plans/specs and external review briefs. Those documents
remain evidence and may not restart completed phases. If the override is absent, stop
before modifying code.

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
8. `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` for reconciled logical PR10-PR20 sequencing, data and evaluation controls
9. `01_CODEX_MASTER_IMPLEMENTATION_PLAN.md`
10. `backlog.csv`
11. Existing implementation

The PR10-PR20 blueprint does not silently replace the fixed product taxonomy, API or database contracts above it. Where it proposes a breaking label, risk-band, endpoint or artifact change, record a compatibility decision and migration before implementation.

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
