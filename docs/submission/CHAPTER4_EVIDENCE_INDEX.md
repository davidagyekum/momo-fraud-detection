# Chapter Four Implementation Evidence Index

## How to use this index

This index maps the implemented prototype to safe repository evidence. The complete machine-readable inventory is [EVIDENCE_MANIFEST.csv](../evidence/EVIDENCE_MANIFEST.csv). Historical plans, specifications and wireframes explain intent; they are not proof that a feature ran.

Evidence classes used here:

- **Accepted implementation evidence:** executed behavior tied to a Git SHA and local/controlled environment.
- **Historical implementation evidence:** valid evidence for an earlier phase; later accepted regressions provide the stronger current gate.
- **Experimental evidence:** pipeline/model/data work whose limitations prevent a product-readiness claim.
- **Design evidence:** proposed wireframes, plans and architecture references; not actual UI/runtime proof.
- **Outstanding:** an original requirement without complete final evidence.

## 4.2 Development environment and repository structure

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [README](../../README.md), [local run guide](../LOCAL_RUN_GUIDE.md), [implemented architecture](../architecture/P01_FOUNDATION.md) | Accepted/local | Documents the fixed stack, Docker topology and repeatable local startup. No hosted environment is implied. |
| `FINAL_SUBMISSION_PACKAGE_MANIFEST.json` inside the generated ZIP | Accepted/exact revision | Identifies the exact pushed commit and per-file hashes. |

## 4.3 Database and private storage

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [Implemented ER model](../architecture/P02_IMPLEMENTED_ER.md) | Historical implementation | Matches the implemented relational foundation; current migration acceptance reaches `20260817_0006`. |
| [P0.2 migration evidence](../evidence/P0_2_SCREENSHOT_ONLY_ANALYSIS.md) | Accepted implementation | Empty and representative previous-revision upgrades reached head; drift check was clean. |
| [Backup and retention design](../deployment/P02_BACKUP_AND_RETENTION.md) | Design/partial | Procedure exists; restore rehearsal remains outstanding. |

## 4.4 Backend, API, access control and audit

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P0.1 conclusion/component evidence](../evidence/P0_1_CONCLUSION_COMPONENT_SEMANTICS.md) | Accepted implementation | Fraud-risk conclusiveness and component availability are independent without rewriting history. |
| [P0.2 screenshot-only evidence](../evidence/P0_2_SCREENSHOT_ONLY_ANALYSIS.md) | Accepted implementation | Persists message-only risk without fabricated transaction fields. |
| [PR18 analysis product](../evidence/PR18_ANALYSIS_PRODUCT.json) | Accepted aggregate | Immutable orchestration, ownership, private evidence and categorical null-score behavior. |
| [PR19 security acceptance](../security/PR19_SECURITY_ACCEPTANCE.md) | Accepted/local | 31 database security scenarios with zero skips plus web/mobile policy and secret checks at the recorded phase SHA. |

## 4.5 Mobile application

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P1 OCR-first mobile report](../evidence/P1_OCR_FIRST_MOBILE.md) | Accepted implementation | Primary screenshot-only action, optional comparison, accessible states and risk/verification separation. |
| [360x800](../evidence/mobile/p1-ocr-risk-360x800.png), [390x844](../evidence/mobile/p1-ocr-risk-390x844.png), [768x1024](../evidence/mobile/p1-ocr-risk-768x1024.png), [1440x900](../evidence/mobile/p1-ocr-risk-1440x900.png) | Accepted actual UI | Fictitious-data Chromium/Expo-web screenshots; no native-device claim. |
| `docs/design/**` | Design evidence | Low-fidelity/concept artifacts only; do not reproduce as implemented-screen evidence. |

## 4.6 Administrator and investigator portal

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [PR19 acceptance](../qa/PR19_ACCEPTANCE.md) | Accepted/local | 40 portal tests, three Playwright role/access flows and production build at the recorded PR19 SHA. |
| [Desktop dashboard](../evidence/admin/p05-admin-dashboard-desktop.png), [tablet dashboard](../evidence/admin/p05-admin-dashboard-tablet.png), [narrow dashboard](../evidence/admin/p05-admin-dashboard-narrow.png) | Historical actual UI | Safe controlled portal screenshots; later regression gates are the stronger behavioral evidence. |
| Full user/template/rule mutation UI | Outstanding | Read-only/partial management coverage remains in review and is not described as complete. |

## 4.7 OCR and deterministic text risk

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P07 OCR evidence](../evidence/P07_OCR_EVIDENCE.md) | Historical controlled implementation | 20/20 declared fields across five synthetic fixtures; not provider-wide accuracy. |
| [OCR text-risk repair](../evidence/OCR_TEXT_FRAUD_REPAIR.md) | Historical implementation | Introduced the privacy-safe obvious-scam assessment and categorical policy integration. |
| [P0.3 text-rule hardening](../evidence/P0_3_TEXT_RULE_HARDENING.md) | Final accepted implementation | V2 Unicode/clause locality and thresholds, frozen v1 validation, complete local gates and a controlled browser persistence journey. |

## 4.8 Image analysis and machine learning

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P09 deterministic image evidence](../evidence/P09_IMAGE_FORENSICS_EVIDENCE.md) | Historical implementation | Supporting metadata/duplicate/recompression/noise/layout evidence; not proof of tampering. |
| [P11 structured evaluation](../evidence/P11_STRUCTURED_EVALUATION.json) and [model card](../models/STRUCTURED_MODEL_CARD_CONTROLLED_V1.md) | Experimental/controlled | Pipeline passed a tiny three-row controlled-synthetic held-out set. Current release model remains not activated; no provider-wide claim. |
| [P12 image evaluation](../evidence/P12_IMAGE_EVALUATION.json) and [model card](../models/IMAGE_MODEL_CARD_CONTROLLED_V1.md) | Experimental failure | Macro F1 `0.333333` failed acceptance. Artifact is inactive/unavailable and omitted from Git/package. |
| PR12-PR17 JSON/Markdown records in `docs/evidence/` | Experimental/data-governance | Reproducibility, acquisition and preprocessing evidence only, with each record's own limitations. |

## 4.9 Stored-reference verification

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P0.2 screenshot-only/combined evidence](../evidence/P0_2_SCREENSHOT_ONLY_ANALYSIS.md) | Accepted implementation | Demonstrates `NOT_ATTEMPTED` for screenshot-only and preserves the existing stored-reference combined flow. |
| [PR19 acceptance](../qa/PR19_ACCEPTANCE.md) | Accepted/local | Controlled import/comparison/product journey evidence. |
| Live provider confirmation | Outstanding/out of prototype scope | No MNO API exists; UI wording must remain “stored/imported reference records.” |

## 4.10 Risk aggregation, history, reports and cases

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P0.3 text-rule hardening](../evidence/P0_3_TEXT_RULE_HARDENING.md) | Final accepted implementation | Active ruleset v2 and deterministic policy v3; score is not a probability. |
| [P1 mobile evidence](../evidence/P1_OCR_FIRST_MOBILE.md) | Final accepted UI | High fraud risk and verification Not attempted persist as separate statuses in result/detail/history. |
| [PR19 acceptance](../qa/PR19_ACCEPTANCE.md) | Accepted/local | Controlled private report, fraud report, assignment, review, note, decision, notification and staff journey. |
| Complete history filters and automatic high-risk case creation | Outstanding | Remain explicit P14/P15 review items. |

## 4.11 Security and privacy

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [PR19 security acceptance](../security/PR19_SECURITY_ACCEPTANCE.md) | Accepted/local | Ownership, RBAC, hostile upload, refresh/CSRF, private artifacts, immutable evidence and secret scans. |
| [Submission artifact policy](SUBMISSION_ARTIFACT_POLICY.md) | Final freeze control | Exact Git tree only; rejects private/generated/model/archive content and verifies per-file hashes. |
| External penetration/non-local environment assessment | Outstanding | Not claimed. |

## 4.12 Testing, evaluation and local release

| Evidence | Classification | Submission interpretation |
|---|---|---|
| [P0.3 complete verification](../evidence/P0_3_TEXT_RULE_HARDENING.md) | Final accepted local regression | Backend 233, mobile 73, admin 40 plus 3 Playwright, ML 714, security 31 zero-skip, E2E, two migration paths and release verifier passed at the recorded SHA. |
| [PR19 QA](../qa/PR19_ACCEPTANCE.md), [local release](../deployment/PR19_LOCAL_RELEASE.md), [rollback](../deployment/PR19_ROLLBACK.md) | Historical accepted/local | Four-service local release evidence; not staging/production evidence. |
| Hosted CI, native devices, performance/load, restore rehearsal | Outstanding | See [limitations](LIMITATIONS_AND_NON_CLAIMS.md). |

## 4.13 Limitations and conclusion

The Chapter Four conclusion must use the wording boundaries in [Final Limitations and Non-Claims](LIMITATIONS_AND_NON_CLAIMS.md). In particular, it must not convert controlled accuracy, local Docker health, stored-reference comparison or deterministic forensic signals into claims of provider-wide accuracy, hosted deployment, live MNO confirmation or proven image-model capability.
