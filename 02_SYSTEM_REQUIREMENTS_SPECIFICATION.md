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
