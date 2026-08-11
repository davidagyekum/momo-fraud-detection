# IMPLEMENTATION_STATUS.md

> Codex must update this file at the end of every session. Do not mark a phase complete without its exit criteria and pushed evidence.

## Current repository state

- Repository: `davidagyekum/momo-fraud-detection`
- Default branch: `main`
- Current work branch: `codex/p13-dataset-acquisition-validation`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- PR13 immutable implementation SHA: `aad3f01b6c0aa0605e22d788761927114c1fe2ea`
- PR13 PaySim rights-decision SHA: `2a53bfc835bbc149852f7762463823f1b67c8242`
- PR13 PaySim acquisition/registration code SHA: `9ac904bd9164a1c8848ad300addc1b2a89b7e144`
- PR13 PaySim step-reconciliation code SHA: `af248bd6b71e77bdf9ddaa4dc3457856f1cff87a`
- PR13 corrected Colab pin SHA: `6b9945c6b03d394b9304045fa1ab02e928bb1951`
- PR13 PaySim registration evidence SHA: `f2ccf7aba8d18154df12ed13b9cb4d1eec96b334`
- PR13 MoMTSim rights/schema review SHA: `53f852f99204185ebd11781edcf19b77b98ec982`
- PR13 MoMTSim acquisition/registration evidence SHA: `91da9dd3841cca880974c5cbfc76bd82acddf07d`
- P12 training code SHA: `02d8967136853c5c46eaa0babe44a7327c843a32`
- Last updated: `2026-08-11`
- CI status: `Logical PR13 registered ML gate passes locally with 311 tests at 90.53% coverage; hosted jobs remain unable to start because the repository owner's Actions account is locked by a billing issue`
- Deployment status: `Not deployed`
- Current phase: `Logical PR13 dataset acquisition and validation — In Progress; PaySim and MoMTSim v1 registered, MoMTSim v2 quarantined for 20 exact duplicate rows, and three image sources retain separate gates`
- Next exact task: `Review and implement a content-addressed deterministic MoMTSim v2 derived-dataset policy before any deduplication/re-registration, while keeping v2 disabled and preserving the immutable quarantine evidence.`

## PR10-PR13 reconciliation status

- Blueprint: `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` (2,446 lines; repository copy verified equal to the supplied source after newline normalisation).
- Audit: `docs/audits/pr10-pr12-gap.md`.
- Result: logical PR10, PR11 and PR12 foundations are complete with local and owner-operated Colab evidence. Correct historical work is preserved; the failed historical P12 image artifact remains inactive and PR13 acquisition remains separately gated.
- Compatibility boundary: current public risk/verification enums and Keras/scikit-learn stack remain effective until versioned migrations are implemented and tested.
- Training boundary: no additional full run is allowed before the reconciliation foundations, governed dataset and newly frozen partitions pass.

## Logical PR13 dataset acquisition and validation

- Readiness: deterministic metadata-only inventory reports PaySim and MoMTSim v1 `registered`, MoMTSim v2 `quarantined`, and STFD/FSTS/Ghana-private `not_acquired`; all six sources remain disabled.
- Registration: strict request/manifest contracts, approved-root confinement, content-addressed file/directory/ZIP inventory, transaction/image validators, redacted safe profiles and non-mutating quarantine are implemented without a network client.
- Hostile-input controls: path traversal, symlink substitution, duplicate normalised ZIP members, archive expansion, malformed/oversized images, schema/count/class drift, mask pairing and identity mismatches fail closed.
- Evidence boundary: PaySim's corrected owner-operated Colab run registered 6,362,620 rows. Official Mendeley browser acquisition then established exact v1/v2 package/file hashes and schemas: v1 registered at 1,720,181 rows with zero duplicates; v2 matched 4,225,958 rows but quarantined for 20 exact duplicates. Safe evidence is in `docs/evidence/PR13_MOMTSIM_ACQUISITION_REGISTRATION.json`; STFD, FSTS and Ghana-private retain separate access/terms/consent gates.
- Colab boundary: `02_dataset_acquisition_validation.ipynb` is output-free and registration-only; it cannot download, create splits, train, inspect locked tests or promote an artifact.
- Honesty boundary: the first PaySim quarantine and MoMTSim v2 duplicate-row quarantine remain preserved. PaySim and MoMTSim v1 are registered but disabled/non-promotable; no split, training, locked-test, metric or promotion claim is made.
- Verification: the registered ML gate passes format, lint, strict mypy, 311 tests at 90.53% branch-aware coverage, governance/readiness/notebook drift and controlled-dataset checks; the latest secret/prohibited-artifact scan passes 484 candidates.
- Current registry hash after MoMTSim acquisition/validation: `fee3a28144f43ffc0627fef3cac6197cdcda1d9a852dbd4d62b5395450982e43`.

## Logical PR10 evidence/execution foundation

- Portable contract: `packages/evidence-contracts/evidence-result-v1.schema.json`.
- Runtime contract: explicit screenshot-only, transaction-only, combined and inconclusive modes; unavailable signals require null scores and labels.
- Compatibility: new `unaltered`/`tampered` and risk-band terms are additive; current database/API/artifact values remain unchanged through named projections.
- Execution policy: UNIT/SMOKE cannot enter existing fitting commands; FULL requires exact acknowledgement, detected Google Colab and a non-CI runtime.
- CI policy: workflow pins UNIT and registers the ML verification job.
- Verification: 111 ML tests at 92.00% coverage; 140 PostgreSQL-backed backend tests at 86.01% coverage; OpenAPI, ER, migration-current/check and targeted negative guard checks pass.
- Training/data boundary: no acquisition, private-data access, fitting, threshold selection or artifact registration occurred.

## Logical PR11 data governance and registry

- Canonical registry: six exact sources (PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private), all disabled and `not_acquired`; unknown rights remain blocked.
- Portable contracts: strict JSON Schema 2020-12 documents for transaction, screenshot, OCR truth, controlled edits, frozen splits and reproducible runs.
- Privacy governance: participant/consent templates, internal-versus-release scope, withdrawal/deletion, de-identification, roles, retention, incidents, publication checklist, data-access rules and threat model.
- Executable enforcement: registry/card/schema path and state checks; consent/provenance rules; withdrawal blocking; taxonomy total; fictitious fixture markers; PII filename, secret, prohibited artifact and 10 MiB file scans.
- Deterministic evidence: registry hash `e740b80253e6…`, six schema hashes, six fixture hashes, withdrawal fixture hash `33ecc617080b…`, taxonomy hash `a4a2efb21911…`; recorded report declares acquisition/training false.
- Verification: registered ML gate passes 193 tests at 93.15% branch-aware coverage with Ruff, strict mypy and all existing controlled dataset reports. Backend regression evidence is recorded in the current PR11 handoff.
- Boundary: no data was downloaded/scraped, no completed consent/private identifier was committed and no model was fit or registered.

## Logical PR12 reproducible Colab foundation

- Runtime contract: `colab-foundation-v1` enforces Python 3.12, SMOKE-only preflight, clean immutable Git checkout, exact dependency-lock hashes, generic Drive/VM roots and an allowlisted runtime inventory.
- Run evidence: strict `colab-run-manifest-v1` records the run ID, timestamps, Git state, dependencies, dataset/split/config/feature hashes, artifacts, immutable checkpoints and interrupted/resumed sessions.
- Recovery: same-directory atomic writes, verified Drive mirrors and hash-before-resume reject missing or corrupt checkpoints and preserve the original run ID across a lost runtime.
- Bounded smoke: deterministic fictitious train/validation-only transaction, OCR and one-epoch image-surrogate stages stay within 1,000 rows, 20 images and one epoch; JSON export/reload is verified and locked tests are excluded.
- Honesty boundary: every smoke bundle declares acquisition, full training and promotion false; it cannot be registered or cited as accuracy evidence and does not change the failed historical P12 artifact.
- Verification: registered ML gate passes locally with Ruff, strict mypy, lock/notebook drift checks and 281 tests at 93.13% branch-aware coverage. The owner-operated signed-in Colab preflight/smoke passed at clean code commit `b2e6b24a337c3cc1777c162cf64861d7e55d29f8`; prediction digest `43833f49…` and owner-reported manifest SHA-256 `bb0ebffb…` are recorded in `docs/evidence/PR12_COLAB_FOUNDATION_SMOKE.json`.
- Stop boundary: the Colab smoke completed with acquisition, FULL training and promotion false. No private data or locked test was accessed; PR13 acquisition and every reportable training workflow remain separately owner/governance gated.

## Phase status

| Phase | Name | Status | Branch/PR | Head SHA | Verification evidence | Blocker/notes |
|---|---|---|---|---|---|---|
| P00 | Repository preflight, scope lock and execution foundation | Complete | [PR #1](https://github.com/davidagyekum/momo-fraud-detection/pull/1) — merged | `41741877cce2a2efd69240c77707c55a7961bd0f` merge commit | P00 checks passed; GitHub merge verified in Chrome | Merged to `main` on 2026-08-09. |
| P01 | Monorepo, API skeleton and local infrastructure | Complete | [PR #2](https://github.com/davidagyekum/momo-fraud-detection/pull/2) — merged | `7a9efcc71780e1e0c9e72b5e0e2efd194771d0d1` merge commit | Ruff format/lint pass; strict mypy pass; 20 pytest tests pass at 91.81% coverage; OpenAPI drift pass; clean Docker image build; fresh PostgreSQL migration `20260809_0001`; API/database containers healthy; live health/readiness/version/error/CORS probes pass | Merged to `main` on 2026-08-09 using the passing local evidence; GitHub Actions billing limitation remains B-CI-001. |
| P02 | Relational schema, migrations, seeds and private storage abstraction | Complete | [PR #3](https://github.com/davidagyekum/momo-fraud-detection/pull/3) — merged | `0fa8d463eb74ef0f93597fb7cb13647a94ce83fa` merge commit | 30 tables; clean and previous-revision migration; downgrade/upgrade; 28 tests at 88.12% coverage; strict mypy/Ruff; ER drift; idempotent seed; Docker build/readiness pass | Merged to `main` on 2026-08-09 using passing local evidence; B-CI-001 remains external. |
| P03 | Authentication, session security, ownership and RBAC | Complete | [PR #4](https://github.com/davidagyekum/momo-fraud-detection/pull/4) — merged | `3a4f4ea50df3aacdedf6094e3108c453fca092cc` merge commit | 41 tests pass at 92.44% coverage; Ruff format/lint and strict mypy pass; OpenAPI and ER checks pass; secret scan passes; clean API image build and live Docker admin login/`/me` smoke pass | Merged on 2026-08-09; B-CI-001 remains an external hosted-runner blocker. |
| P04 | Mobile application shell, design system and authentication experience | Complete | [PR #5](https://github.com/davidagyekum/momo-fraud-detection/pull/5) — merged | `9e7594bb79ecd5805f3417d617fcef4c011669dd` merge commit | Mobile verification passes: format/lint/type; 25 Jest tests; security-critical coverage 89.77% statements/80% branches; token policy; static export; 45 backend regressions at 92.44%; real local API registration/login/profile/logout smoke; 360/390 viewport evidence | Merged on 2026-08-09 using passing local evidence. B-CI-001 and upstream dependency waiver B-SEC-002 remain external. |
| P05 | Administrator and investigator web portal shell | Complete | [PR #6](https://github.com/davidagyekum/momo-fraud-detection/pull/6) — merged | `1d7891fd2087a8f5412d864a66dafc939b967a60` merge commit | Admin verification passes: security policy, format/lint/strict type, 34 Vitest tests at 90.95% statement coverage, 3 Playwright smoke tests, production build; 47 backend tests at 92.45%; live ADMIN/INVESTIGATOR browser flow and 1440/768/390 evidence | Merged on 2026-08-10 using passing local evidence; B-CI-001 remains external. |
| P06 | Receipt capture, hostile-file validation and private upload | Complete | [PR #7](https://github.com/davidagyekum/momo-fraud-detection/pull/7) — merged | `62f411aee2bd39a7d2feb8e49073ca4bdcf04922` merge commit | 65 backend tests at 90.16%; 37 mobile tests above configured coverage; strict lint/type; OpenAPI; web export; 17 hostile/private upload tests; live upload/private-read probe; Chrome DOM/console flow | Merged on 2026-08-10 using passing local evidence; hosted checks remain blocked by B-CI-001. Chrome screenshot capture timed out and no screenshot is claimed. |
| P07 | OCR preprocessing, extraction, confidence and correction workflow | Complete | [PR #8](https://github.com/davidagyekum/momo-fraud-detection/pull/8) — merged | `19b38a04da7d4d977aaace85e80efc7612bbd88f` merge commit | 79 backend tests at 89.04% coverage; 46 mobile tests; strict lint/type and OpenAPI/export gates; real Tesseract controlled evaluation matched 20/20 required fields across five fixtures | Merged on 2026-08-10 using passing local evidence; all hosted jobs were prevented from starting by B-CI-001. Controlled OCR accuracy is not production/provider-wide evidence. |
| P08 | Reference-record import and transaction verification | Complete | [PR #9](https://github.com/davidagyekum/momo-fraud-detection/pull/9) — merged | `36d39e0d59b4b36672890e51e22233a8ca01604e` merge commit | 90 backend tests at 90.40% coverage; 36 admin tests at 91.58% statement coverage; 3 Playwright tests and production build; 48 mobile tests at 89.80% statement coverage and 23-route static export; Chrome upload/validate/confirm/commit flow with no console warnings or errors | Merged on 2026-08-10 using passing local evidence. All eight hosted jobs were prevented from starting by B-CI-001. Stored/imported references only, never live MNO verification. |
| P09 | Deterministic image-forensics and manipulation evidence | Complete | [PR #10](https://github.com/davidagyekum/momo-fraud-detection/pull/10) — merged | `5ed38ac84bda4b3948f7893d2647096d3d70a0ed` merge commit | Registered backend gate: 96 tests at 87.58% branch coverage, Ruff, strict mypy, OpenAPI and ER pass; clean and previous-revision migrations pass; mobile gate: 48 tests at 89.80% statement coverage and 23-route export | Merged on 2026-08-10 using passing local evidence. All eight hosted jobs had zero steps and were prevented from starting by B-CI-001. Supporting/contextual evidence only; no model was trained. |
| P10 | Dataset governance, controlled sample generation and reproducible splits | Complete | [PR #11](https://github.com/davidagyekum/momo-fraud-detection/pull/11) — merged | `2e2c1fd53863e09b03c52ae1d5f53c1111deec81` merge commit | Registered ML gate: 32 tests at 92.57% branch-aware coverage, Ruff, strict mypy, controlled-dataset validation and report-drift checks pass; 12 files across six isolated source groups reproduce manifest hash `51d12132…` and split hash `08008637…`; backend regression: 97 tests at 87.58% | Merged on 2026-08-10 using passing local evidence; all eight hosted jobs had zero steps and were prevented from starting by B-CI-001. No model was fit, evaluated or exported. |
| P11 | Structured-feature fraud classifier | Complete | [PR #13](https://github.com/davidagyekum/momo-fraud-detection/pull/13) — merged | `42a0ec69430f9a412211ada85a03d7c3171e4136` merge commit | ML gate: 71 tests at 91.03%; backend gate: 110 tests at 86.17%; signed-in Colab held-out macro F1/balanced accuracy 1.0 over three controlled samples; private artifact hash, registry lifecycle and real API inference pass | Merged on 2026-08-10 using passing local/Colab evidence. All eight hosted jobs had zero steps under B-CI-001. Controlled-only pipeline evidence; no provider-wide/production claim. |
| P12 | CNN receipt-tampering classifier | In Progress | historical `codex/p12-cnn-tampering`; foundation `codex/p12-colab-foundation` | historical training code `02d8967136853c5c46eaa0babe44a7327c843a32`; foundation code `b2e6b24a337c3cc1777c162cf64861d7e55d29f8` | Historical signed-in Colab held-out macro F1 `0.333333` failed acceptance; logical PR12 foundation smoke passed with manifest SHA-256 `bb0ebffb…`, prediction digest `43833f49…`, and acquisition/FULL/promotion false | Historical artifact remains inactive. The reproducibility foundation is complete, but the product classifier remains incomplete pending representative authorised data and a newly governed model version. |
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

- MUST requirements complete: `45 / 87`
- SHOULD requirements complete: `5 / 11`
- Blocked requirements: `None recorded`
- Traceability file last verified: `2026-08-11 — PaySim and MoMTSim v1 registered; MoMTSim v2 exact identity preserved under duplicate-row quarantine; all sources disabled and no training occurred`

## Current blockers

| ID | Phase | Blocker | Impact | Owner/input needed | Safe fallback | Next action |
|---|---|---|---|---|---|---|
| B-CI-001 | Cross-phase | GitHub Actions jobs fail before runner allocation because the repository owner's account is locked by a billing issue. | Hosted CI cannot independently reproduce local gates. | Repository owner resolves the GitHub Actions billing/account lock. | Keep pinned workflows and exact local evidence; do not misreport hosted checks as passing. | Resolve the account lock and rerun the latest workflow when available. |
| B-SEC-002 | P04 | `npm audit --omit=dev` reports 8 moderate and 15 high findings in the supported Expo SDK 57 / React Native 0.86 / Metro graph; npm's proposed automatic fixes downgrade to incompatible Expo 53 or React Native 0.72 lines. | The supported mobile dependency graph retains upstream advisories; no critical finding is reported, but the high findings cannot be silently waived. | Expo/React Native upstream and Codex maintainer monitoring supported patch releases. | Keep exact supported SDK pins, avoid `npm audit fix --force`, validate hostile receipts on the API, and do not run untrusted build inputs. | Re-run Expo compatibility and npm audit when a supported SDK 57 patch is available; upgrade only through Expo's supported matrix. |
| P12-ACCEPTANCE | P12 | The controlled-only Colab run completed but held-out macro F1 `0.333333` failed the configured `0.85` minimum. | The exported image model cannot be registered, activated or represented as usable product evidence. | Keep image inference explicitly unavailable with a null tamper probability and preserve the failed run for audit. | Project owner/data steward supplies representative, authorised grouped data after roadmap reconciliation. | Treat the run as experimental failure evidence; create a new model version only after the dataset and split gates pass. |
| PR13-MOMTSIM-V2-DUPLICATES | Logical PR13 | The exact official v2 CSV contains 20 exact duplicate rows and is quarantined. | v2 cannot enter splits, fitting, evaluation or promotion. | Preserve official bytes and quarantine evidence; use only registered PaySim/MoMTSim v1 for later governed design. | Codex/data steward reviews a content-addressed derived-dataset policy. | Define deterministic deduplication provenance and revalidation without mutating the source. |
| PR13-DATA-RIGHTS | Logical PR13 | STFD, FSTS and Ghana-private retain access/terms/consent and layout prerequisites. | PR13 cannot complete and PR14 frozen splits cannot start. | Keep all three entries disabled/not acquired. | Project owner/data steward follows `data/ACQUISITION_REGISTRATION_RUNBOOK.md`. | Review each remaining image source separately before acquisition. |

## Active known limitations

- No live MNO integration is part of the prototype.
- Real/supervisor-approved receipt dataset and production reference source are not yet supplied.
- Brand/deployment credentials are not yet supplied.
- Docker Desktop 29.6.2 with Compose v5.3.1 is installed per-user; the API container supplies Tesseract 5.3.0 and the PostgreSQL container supplies the database CLI.
- The unqualified Windows `python` command resolves to 3.11.7; use `py -3.12` for the selected Python 3.12 runtime. The unqualified Node.js is 22.11.0; activate pinned Node.js 24.14.0 for Expo work.
- Actual P11 training ran in signed-in Google Colab at immutable code SHA `a914f065070558b5b601e6f49cf1691ff7bf9d42`; P12 and future reportable training runs must also use Google Colab. Local execution remains limited to tests, packaging and inference verification.
- P11's held-out result contains only one controlled source group and three rows. It is pipeline-correctness evidence, not provider-wide accuracy, calibration or production readiness.
- P12 trained on only six controlled source groups/twelve images. The one-group/two-image held-out result failed acceptance and cannot estimate provider generalisation. The deterministic dataset report is now explicitly scoped to preflight; actual run evidence is stored separately under `docs/evidence`.

## Last completed session

- Handoff file: `docs/handoffs/2026-08-11-PR13-momtsim-registration-session.md`
- Summary: `Acquired exact official MoMTSim DOI packages through Chrome, registered v1, preserved v2 under a 20-duplicate-row quarantine, kept all sources disabled/non-promotable, and performed no split, training or locked-test access.`

## Next session startup

1. Read `AGENTS.md` and this file.
2. Fetch/prune and verify the current SHA/worktree.
3. Read `docs/handoffs/2026-08-11-PR13-momtsim-registration-session.md`, `docs/evidence/PR13_MOMTSIM_ACQUISITION_REGISTRATION.json` and `data/ACQUISITION_REGISTRATION_RUNBOOK.md`.
4. Confirm branch `codex/p13-dataset-acquisition-validation`, its pushed head and the immutable code SHA printed in the handoff/notebooks.
5. Preserve P12 acceptance `false`, held-out macro F1 `0.333333`, and artifact SHA-256 `3d074298835a28a9af92fca8b50cc618dc8eb67585e2b312c261121f43a70046`; do not activate or rerun it.
6. Verify `docs/evidence/PR12_COLAB_FOUNDATION_SMOKE.json` and preserve the owner-reported manifest SHA-256 `bb0ebffbbae57175d936563a7ee3a04bac1618f9e661ca480ab07393f963b279` as logical PR12 infrastructure evidence only.
7. Preserve PaySim as registered but disabled/non-promotable and preserve both the first quarantine and corrected registration artifacts; do not create splits, access locked tests or execute FULL training yet.
8. Preserve MoMTSim v1 as registered and v2 as quarantined under ADR-027. Do not mutate or deduplicate official v2 bytes; review a content-addressed deterministic derived-dataset policy before any re-registration.
