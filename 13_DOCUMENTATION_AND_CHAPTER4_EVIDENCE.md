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
