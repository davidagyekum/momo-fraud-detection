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

## 9. PR10-PR20 roadmap reconciliation

The implementation roadmap from the current analytical foundation through final evaluation is `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md`. Its logical PR numbers are milestones, not a request to rewrite or duplicate existing GitHub pull-request history.

The blueprint governs future data acquisition, Colab execution, split/calibration discipline, locked-test handling and transparent evidence-policy integration. The fixed product scope and current public contracts in this file and the higher-precedence specifications remain controlling until a documented, backward-compatible migration is implemented. In particular:

- stored/imported reference matching remains a separate verification record and must be labelled as non-live provider evidence;
- the current `GENUINE`/`SUSPICIOUS`/`FRAUDULENT` and `VERIFIED`/`UNVERIFIED`/`MISMATCH` contracts are not silently renamed;
- proposed `low_risk`/`medium_risk`/`high_risk`/`inconclusive` presentation terms require an API/database/UI compatibility decision;
- canonical tamper-task labels may migrate to `unaltered`/`tampered` only through a versioned schema and compatibility shim;
- TensorFlow/Keras and scikit-learn remain the required primary model stack unless explicitly approved otherwise.
