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
