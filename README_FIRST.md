> Historical execution notice: this document is preserved for context/evidence.
> It must not select the current task. Read `FINAL_COMPLETION_OVERRIDE.md` and
> `IMPLEMENTATION_STATUS.md` first.

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
