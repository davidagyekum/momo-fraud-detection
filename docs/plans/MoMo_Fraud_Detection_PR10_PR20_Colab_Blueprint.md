# MoMo Fraud Detection
## PR10–PR20 Colab-First Implementation Blueprint

**Status:** implementation specification for Codex  
**Scope:** work beginning around logical PR10 and ending with the PR20 research release  
**Training policy:** complete model training runs in Google Colab; laptops and GitHub Actions run only linting, tests, tiny fixtures, one-epoch smoke jobs, bundle loading, and inference  
**Repository note:** the project repository and PR history were not visible to the connected GitHub account when this plan was prepared. The next Codex session must verify PRs 1–12 and reconcile gaps rather than assume their contents.

---

# 1. Executive decisions

These decisions are architectural requirements.

1. **The system is not one classifier.** It contains separate pipelines for screenshot tampering, OCR/field parsing, semantic consistency, structured transaction risk, and a risk-policy layer.
2. **A screenshot cannot safely satisfy the complete PaySim/MoMTSim feature contract.** It usually lacks sender history, transaction velocity, balances, and graph context. Missing fields must not be replaced with zeros or invented values.
3. **Use explicit evidence modes:** `screenshot_only`, `transaction_only`, `combined`, and `inconclusive`.
4. **Use careful labels:** screenshot classes are `unaltered` and `tampered`, not “genuine” and “fake.” An unaltered screenshot does not prove that the underlying transaction happened.
5. **Use careful result terms:** `low_risk`, `medium_risk`, `high_risk`, and `inconclusive`.
6. **Do not claim provider verification.** Use “no visible manipulation detected” or “possible manipulation detected.” Do not say “verified genuine” unless an actual documented provider-side service confirms the transaction/reference.
7. **Full training runs in Colab.** Local and CI environments may perform only unit/integration tests, tiny smoke jobs, and inference.
8. **Notebooks remain thin.** Reusable logic belongs under `src/`; notebooks configure and call it.
9. **Raw datasets and private screenshots never enter Git.** Git stores code, schemas, manifests, checksums, tiny fictitious fixtures, reports, and model cards.
10. **Freeze final tests before model selection and open them once in PR20.** Repeated test use invalidates the final academic result.
11. **Do not naively average unrelated scores.** Until a properly paired multimodal dataset exists, use a transparent policy that combines only available signals.
12. **Do not interpret synthetic class ratios as Ghanaian fraud prevalence.** PaySim and MoMTSim are research datasets, not production-rate estimates.

---

# 2. Correct target architecture

```text
                               USER / BACKEND
                                      |
                    +-----------------+-----------------+
                    |                                   |
             Screenshot supplied                 Structured context supplied
                    |                                   |
                    v                                   v
       +---------------------------+        +-----------------------------+
       | Image-forensics pipeline  |        | Transaction-risk pipeline   |
       | - file validation         |        | - schema validation         |
       | - tamper classifier       |        | - causal feature builder    |
       | - tamper localizer        |        | - calibrated risk model     |
       +-------------+-------------+        +---------------+-------------+
                     |                                      |
                     v                                      |
       +---------------------------+                        |
       | OCR and parser            |                        |
       | - pretrained OCR engine   |                        |
       | - field normalization     |                        |
       | - confidence/errors       |                        |
       +-------------+-------------+                        |
                     |                                      |
                     v                                      |
       +---------------------------+                        |
       | Semantic consistency      |                        |
       | - amount/reference/date   |                        |
       | - status/template rules   |                        |
       | - contradictions          |                        |
       +-------------+-------------+                        |
                     |                                      |
                     +------------------+-------------------+
                                        v
                          +-----------------------------+
                          | Evidence-aware risk policy  |
                          | - no invented signals       |
                          | - calibrated thresholds     |
                          | - reason codes              |
                          | - inconclusive state        |
                          +---------------+-------------+
                                          |
                                          v
                          +-----------------------------+
                          | Result                      |
                          | risk band                   |
                          | evidence availability       |
                          | extracted fields            |
                          | flags/explanations          |
                          | optional tamper heatmap      |
                          +-----------------------------+
```

## 2.1 Analysis modes

| Mode | Inputs | Signals permitted | Signals that must be null/unavailable |
|---|---|---|---|
| `screenshot_only` | image | image score/localization, OCR, semantic checks | transaction risk |
| `transaction_only` | structured transaction and history | transaction model and transaction reasons | image/OCR |
| `combined` | image plus structured context | all successfully computed signals | failed components only |
| `inconclusive` | invalid, unreadable, or insufficient evidence | failure/validation reasons | any score that cannot be computed safely |

## 2.2 Output meaning

- `low_risk`: no configured high/medium-risk evidence was found in the evidence supplied and evidence quality was sufficient.
- `medium_risk`: one or more uncertain/suspicious signals require caution or review.
- `high_risk`: a configured high-severity signal or major contradiction was found.
- `inconclusive`: evidence was invalid, unreadable, missing, or component confidence was insufficient.

No result authorizes a withdrawal, refund, or transfer. Users should verify through official provider channels and never share a PIN or OTP.

---

# 3. Dataset portfolio and exact use

One dataset cannot cover the system.

## 3.1 Required and optional datasets

| Dataset | Canonical source | Size/distribution | License/access | Required use | Critical limitation |
|---|---|---:|---|---|---|
| **PaySim** | Kaggle `ealaxi/paysim1`; simulator `EdgarLopezPhD/PaySim` | 6,362,620 rows; 8,213 fraud; about 0.129% fraud | Kaggle card: CC BY-SA 4.0 | primary highly imbalanced structured baseline | canonical card warns against old/new sender/recipient balances for fraud detection; exclude those four fields and `isFlaggedFraud` from the primary model |
| **MoMTSim v1** | Mendeley DOI `10.17632/zhj366m53p.2` | 1,720,181 rows; 175,518 fraud; 10.203% | CC BY 4.0 | secondary structured experiment | synthetic prevalence is not production prevalence |
| **MoMTSim v2** | same Mendeley DOI | 4,225,958 rows; 2,233,118 fraud; 52.843% | CC BY 4.0 | stress/generalization experiment | extreme fraud fraction; never present score as real Ghanaian probability |
| **STFD** | Hugging Face `Zegkim/STFD` | about 2.96 GB; smartphone screenshots, mobile-payment/banking scenes, masks | card shows CC BY 4.0; usage notice is stricter, academic/password/no redistribution | recommended generic screenshot-forgery pretraining/localization | not Ghana-specific; follow the stricter notice |
| **FSTS** | Hugging Face `Zegkim/FSTS`; GitHub `ZeqinYu/FSTS` | about 46 GB and 588k rows in Hub conversion | CC BY-NC 4.0 | optional deterministic subset pretraining | too large for default student Colab workflow |
| **Ghanaian MoMo screenshot dataset** | controlled project collection | target below | private until consent/privacy/brand/release review | mandatory domain adaptation and final image/OCR evaluation | must be consented, minimized, anonymized, group-split, and never scraped from private users |

## 3.2 Canonical locations

- PaySim: `https://www.kaggle.com/datasets/ealaxi/paysim1`
- PaySim simulator: `https://github.com/EdgarLopezPhD/PaySim`
- MoMTSim: `https://data.mendeley.com/datasets/zhj366m53p/2`
- MoMTSim article: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12036017/`
- STFD: `https://huggingface.co/datasets/Zegkim/STFD`
- FSTS code: `https://github.com/ZeqinYu/FSTS`
- FSTS data: `https://huggingface.co/datasets/Zegkim/FSTS`
- CSA MoMo guidance: `https://csa.gov.gh/mobile_money_fraud.php`
- Ghana Data Protection Commission: `https://dataprotection.org.gh/privacy-policy/`
- Bank of Ghana fraud-report page: `https://www.bog.gov.gh/news/publication-of-banks-sdis-and-psps-2024-fraud-report/`

## 3.3 Rules for public data

- Use canonical sources and register exact version/hash.
- Do not treat mirrors as equivalent without validation.
- Do not concatenate PaySim/MoMTSim and describe the result as one realistic population.
- Preserve source-specific experiments and report per-source metrics.
- Follow the strictest visible license/access restriction.
- Do not redistribute restricted archives.
- Do not use public screenshot-forgery data as a substitute for Ghana-domain evaluation.

## 3.4 Rules for private data

- Do not scrape social media or private chats.
- Use controlled low-value transactions and consenting participants.
- Never collect PINs, OTPs, passwords, or Ghana Card numbers.
- Use pseudonymous IDs and separate identity/withdrawal mappings.
- Keep consent records separate from model data.
- De-identify working copies before modeling.
- Separate consent to analyze from consent to publish.
- Provide withdrawal/deletion procedure.

---

# 4. Original Ghanaian screenshot dataset

## 4.1 Size milestones

| Milestone | Source groups | Content per group | Approximate images | Purpose |
|---|---:|---|---:|---|
| pipeline pilot | 30 controlled real + 20 synthetic clean | at least 1 clean + 2 edits | 150+ | validate governance, de-identification, masks, OCR, deletion |
| minimum study | 250 controlled real | 1 unaltered + 3 tampered | 1,000 | preliminary domain model and OCR benchmark |
| recommended PR20 target | 600 controlled real + 150 synthetic clean | 1 clean + 4 tampered | 3,750 | main study |
| hard-negative extension | benign transformed clean copy for 60% of 750 bases | compression/crop/resize without semantic change | +450; total 4,200 | prevent compression from being learned as fraud |
| stretch | 1,500 bases | 1 clean + 4 edits plus hard negatives | 7,500+ | broader publication-quality study |

A **source group** contains the original base screenshot and every derivative. The group never crosses splits.

## 4.2 Exact recommended split

### Controlled-real bases: 600

- training: **420 groups (70%)**
- validation: **90 groups (15%)**
- locked final test: **90 groups (15%)**

### Synthetic-clean bases: 150

- training augmentation: **120 groups (80%)**
- validation augmentation: **30 groups (20%)**
- final test: **0 groups (0%)**

The final test is controlled-real only:

- full view: 90 unaltered + 360 tampered = **450 images**;
- balanced fixed view: 90 unaltered + one preselected tampered derivative per group = **180 images**;
- the balanced derivative selection is frozen before training.

Report both views.

## 4.3 Diversity targets

- no provider/template family above **60%** of controlled-real bases;
- no exact template version above **35%**;
- at least **10 physical devices** where feasible;
- no device above **15%**;
- screenshot widths: 25% ≤720 px, 50% 721–1080 px, 25% >1080 px;
- at least **25% dark-theme** where supported;
- include SMS, notification, app receipt, and history channels where available;
- no single channel above 60% when multiple channels exist;
- include sender-side and receiver-side views when lawful and feasible.

Unmet quotas are disclosed in the dataset card rather than hidden.

## 4.4 Tamper taxonomy

Each tampered sample has a semantic target and editing method.

### Semantic-target distribution

- amount: **25%**
- recipient name/wallet: **20%**
- reference/transaction ID: **15%**
- date/time: **10%**
- status: **10%**
- sender/provider/header: **5%**
- multi-field: **15%**

Total: **100%**.

### Editing-method distribution

- direct style-matched replacement: **40%**
- splicing: **20%**
- removal plus insertion: **15%**
- copy-move: **10%**
- inpainting-assisted replacement: **10%**
- manual multi-operation composite: **5%**

Total: **100%**.

### Generator mix

- about **80% programmatic/reproducible** edits;
- about **20% manual controlled** edits;
- every manual edit still requires a manifest and mask;
- no “fake” watermark or label cue in model input;
- all manipulated identities/references are fictitious or anonymized.

## 4.5 Benign hard negatives

Generate clean variants with no semantic edits:

- JPEG/WebP recompression;
- forwarding/compression effects;
- moderate resize;
- safe crop retaining relevant content;
- mild blur/noise;
- metadata stripping;
- screen photography/mild moiré where available.

Label them `unaltered` with `benign_transform` metadata.

## 4.6 Collection/governance policy

1. Obtain informed consent before collection.
2. Use controlled small transactions.
3. Record a pseudonymous participant ID.
4. Do not put names/phone numbers in filenames.
5. Store raw originals in a restricted folder and create de-identified derivatives.
6. Redact/replace full phone numbers, names, balances, and references unless essential and explicitly authorized.
7. Separate internal research consent from public release permission.
8. Support withdrawal by participant identifier.
9. Retain identifiable raw images only as long as necessary. A working default is deletion or irreversible de-identification within 90 days after acceptance, subject to supervisor/institution approval.
10. Keep the private dataset restricted until rights, consent, privacy, and brand review are complete.

## 4.7 Required record schema

```yaml
image_id: string
source_group_id: string
parent_image_id: string | null
provenance: controlled_real | synthetic_template | stfd | fsts
participant_id_hash: string | null
provider_family: string
template_family: string
template_version: string | unknown
capture_channel: sms | notification | app_receipt | history | other
device_family: string
os_family: android | ios | other
resolution: [width, height]
theme: light | dark | unknown
image_class: unaltered | tampered
tamper_target: none | amount | recipient | reference | datetime | status | header | multi
tamper_method: none | replacement | splicing | removal_insertion | copy_move | inpainting | composite
benign_transform: none | jpeg | webp | resize | crop | blur | screen_photo | other
mask_path: string | null
transcript_path: string
ground_truth_fields_path: string
split: train | validation | test
consent_scope: internal_only | release_approved | synthetic_not_applicable
sha256: string
```

Ground truth:

```json
{
  "amount": {"raw": "GHS 50.00", "normalized": 50.0, "bbox": [0, 0, 0, 0]},
  "recipient_name": {"raw": "TEST USER", "normalized": "test user", "bbox": [0, 0, 0, 0]},
  "recipient_wallet": {"raw": "024XXXX123", "normalized": "024xxxx123", "bbox": [0, 0, 0, 0]},
  "reference": {"raw": "ABC123XYZ", "normalized": "ABC123XYZ", "bbox": [0, 0, 0, 0]},
  "timestamp": {"raw": "2026-08-10 14:31", "normalized": "2026-08-10T14:31:00+00:00", "bbox": [0, 0, 0, 0]},
  "status": {"raw": "successful", "normalized": "successful", "bbox": [0, 0, 0, 0]},
  "full_transcript": "..."
}
```

## 4.8 Annotation quality

- 100% of clean source images receive field-level ground truth.
- Tampered derivatives inherit changes from a machine-readable edit manifest and receive manual spot checks.
- **20%** of screenshot/transcription records are independently double-annotated.
- **10%** of masks are independently reviewed.
- amount and reference adjudicated agreement target: **≥98%**.
- disagreements are adjudicated before any record enters the locked test.

---

# 5. Structured transaction data design

## 5.1 Harmonized schema

```yaml
step: integer
transaction_type: string
amount: float
initiator_id: string
recipient_id: string
old_balance_initiator: float | null
new_balance_initiator: float | null
old_balance_recipient: float | null
new_balance_recipient: float | null
label_is_fraud: integer
dataset_source: paysim | momtsim_v1 | momtsim_v2
source_row_id: string
```

`dataset_source` is metadata. Do not feed it to the primary pooled model because the model could learn source identity.

## 5.2 Model contracts

### `transaction_core`

Uses fields a real backend can reasonably provide at decision time:

- transaction type;
- amount and `log1p(amount)`;
- step/hour and cyclical time;
- causal historical aggregates;
- new-recipient indicator;
- time since previous transaction;
- prior 1h/6h/24h count and amount;
- unique recipients in prior 24h;
- amount versus prior median/quantiles;
- transfer/cash-out sequence features where supported;
- graph-degree features calculated strictly from earlier records.

This model is never called in `screenshot_only` mode.

### `transaction_full_research`

May use balance fields on compatible MoMTSim experiments only when they are available at inference and shown not to be target leakage. It remains research-only unless a real backend supplies the same contract.

## 5.3 Forbidden features

- target or target-derived fields;
- `isFlaggedFraud`;
- PaySim old/new origin/destination balances in the primary benchmark;
- raw initiator/recipient IDs as categories;
- aggregates that include current/future rows;
- fields unavailable to the intended inference request;
- dataset source name in the primary pooled model;
- random placeholders or zero-filled missing context.

Raw IDs may be used temporarily to compute causal aggregates, then removed from the model matrix.

## 5.4 Exact split

For each dataset, sort by unique `step` and split chronologically:

- **70% train** — fitting and train-only weighting/sampling;
- **10% tuning validation** — hyperparameters/model selection;
- **10% calibration/threshold** — probability calibration and operating points;
- **10% locked final test** — one-time PR20 evaluation.

The split builder must:

1. divide unique time steps, not randomly shuffled rows;
2. preserve strict chronological order;
3. minimally adjust a boundary if a partition has too few positive cases;
4. require at least 100 positive records in tuning/calibration/test where the data permits;
5. save row IDs/hashes, step ranges, counts, prevalence, and SHA-256 manifest;
6. freeze the manifest before model results are known.

## 5.5 Dataset experiments

1. PaySim internal train/tune/calibrate/test.
2. MoMTSim v1 internal experiment.
3. MoMTSim v2 separate stress experiment.
4. Cross-dataset generalization using compatible features.
5. Optional pooled model with source identity excluded and per-source reporting.
6. Feature ablations: base, time, causal history, and research-only balances where valid.

## 5.6 Class-imbalance policy

- Preserve natural source proportions in tuning/calibration/test.
- Apply class weights or `scale_pos_weight` only during training.
- For expensive forest experiments, keep all training fraud and reproducibly sample legitimate training rows; record ratio/seed.
- Do not use SMOTE on validation/test.
- SMOTE is optional train-only ablation, not default.
- Report unmodified-test confusion matrices and PR curves.

## 5.7 Candidate models

Required:

- dummy/prevalence baseline;
- logistic regression;
- histogram gradient boosting;
- XGBoost main candidate;
- Random Forest/Extra Trees secondary candidate, using a documented subset if memory requires it.

Select on validation evidence, calibration, latency, model size, and operating trade-offs—not accuracy alone.

## 5.8 Metrics

Primary:

- average precision/PR-AUC;
- recall at defined false-positive rate;
- precision at defined recall;
- F2 where missed fraud is weighted more heavily.

Secondary:

- ROC-AUC;
- precision, recall, F1;
- confusion matrix;
- Brier score/calibration curve;
- latency/model size;
- metrics by transaction type and amount band.

Always report prevalence beside PR-AUC. Accuracy is informational only.

---
# 6. Colab-first training architecture

## 6.1 Execution profiles

| Profile | Where | Data | Permitted work |
|---|---|---|---|
| `unit` | laptop/CI | tiny fictitious fixtures | lint, types, unit/schema tests |
| `smoke` | laptop/CI/Colab | ≤1,000 transaction rows and ≤20 synthetic images | preprocessing, one epoch/fit, export/reload, one inference |
| `full` | Google Colab | registered full data | preprocessing, model search, calibration, full evaluation, export |

A full command requires:

```bash
export MOMO_RUN_PROFILE=full
export MOMO_FULL_TRAINING_ACKNOWLEDGED=1
```

It also validates the configured data root is the Colab working path and fails closed elsewhere. GitHub Actions never sets the acknowledgment.

Recommended commands:

```bash
make lint
make test
make smoke
python -m momo_fraud.cli train-transaction --config configs/transaction/paysim.yaml --profile full
python -m momo_fraud.cli train-image --config configs/image/ghana_finetune.yaml --profile full
```

## 6.2 Drive and VM layout

Private Drive root:

```text
MyDrive/momo-fraud/
├── datasets/
│   ├── archives/{paysim,momtsim,stfd,fsts,ghana-private}/
│   ├── processed/
│   └── manifests/
├── checkpoints/{transaction,image}/
├── runs/<run_id>/{run_manifest.json,metrics.json,plots,reports,logs}/
├── model_registry/{candidate,approved,retired}/
└── private-governance/{consent-records,withdrawal-log,access-log}/
```

Colab VM:

```text
/content/momo-work/
├── repo/
├── data/
├── cache/
├── outputs/
└── checkpoints/
```

Workflow:

1. mount Drive;
2. clone/update repo into the VM;
3. copy only needed archives/shards to VM-local disk;
4. unpack/train locally on the VM;
5. checkpoint locally and synchronize verified checkpoints/results to Drive;
6. avoid training directly against thousands of small Drive files;
7. assume the VM can disappear and make every full notebook restart-safe;
8. do not assume a particular GPU model or runtime duration.

## 6.3 Reproducible environment

Commit:

```text
pyproject.toml
requirements/base.lock
requirements/colab.lock
requirements/dev.lock
Dockerfile
```

Requirements:

- pin direct dependencies and resolved versions;
- record Python, CUDA, accelerator, RAM, framework/package versions, Git commit, config, seed, and notebook in every run;
- use deterministic seeds for Python/NumPy/framework;
- record any nondeterministic operations;
- run `pip check`;
- never silently upgrade dependencies inside a result-producing run;
- use a supported Colab runtime and preflight compatibility rather than depending forever on one past runtime.

Preflight:

```python
assert_python_supported()
assert_repo_state_recorded()
assert_dataset_hashes_match()
assert_split_manifest_frozen()
assert_training_not_using_locked_test()
print_runtime_inventory()
```

## 6.4 Secrets

- Kaggle token: Colab Secret `KAGGLE_API_TOKEN`.
- Hugging Face token: Colab Secret only when needed.
- STFD password/private-data credentials: never printed or saved in notebook output.
- No secrets in cells, `.env.example`, Drive logs, screenshots, manifests, or Git.
- Add secret scanning in CI and pre-commit.

## 6.5 Acquisition

### PaySim

Use official Kaggle tooling or `kagglehub` with slug `ealaxi/paysim1`. Record filenames, byte sizes, hashes, schema, rows, class counts, and archive identity. Never overwrite an existing version with different bytes.

### MoMTSim

Register version 2 of DOI `10.17632/zhj366m53p.2`. Support either an approved runtime URL or a manual Drive upload. Identify v1/v2 by schema and registered distributions, record hashes/counts, and quarantine mismatches.

### STFD

Request academic access, store the protected archive privately, do not redistribute it, and record hash/access restriction. Use it only after confirming the project fits the stated terms.

### FSTS

Skip by default. If enabled, select deterministic published shards/row IDs, cap the subset for current Colab capacity, save IDs/hashes, and respect non-commercial terms.

### Ghana private data

Upload de-identified working copies only to model-development storage. Keep identity mappings and consent records separately restricted. Reject filenames containing direct identifiers and run automated plus manual PII review.

## 6.6 Notebooks

```text
notebooks/colab/
00_environment_preflight.ipynb
01_acquire_and_register_datasets.ipynb
02_validate_and_profile_datasets.ipynb
03_build_transaction_features.ipynb
04_train_transaction_models.ipynb
05_build_ghana_screenshot_dataset.ipynb
06_benchmark_ocr.ipynb
07_pretrain_image_forensics.ipynb
08_finetune_ghana_image_model.ipynb
09_calibrate_risk_policy.ipynb
10_locked_final_evaluation.ipynb
11_export_release_bundles.ipynb
```

Rules:

- visible SMOKE/FULL parameter at top;
- core logic imported from `src/`;
- restart-and-run-all works;
- sensitive/large output cleared before commit;
- final notebook requires frozen bundle/test hashes;
- final notebook emits an immutable evaluation receipt.

## 6.7 Run IDs/manifests

Example:

```text
20260810T143100Z_tx-paysim_xgb_a1b2c3d_seed42
```

Manifest includes run timestamps, Git state, notebook/profile, runtime inventory, dataset and split hashes, config/hash, seed, features, artifacts/hashes, status, and session/resume history. A run without a valid manifest cannot be promoted or cited as reproducible.

## 6.8 Checkpoint policy

- checkpoint after preprocessing shards, epochs, or search trials;
- use atomic temp-write/rename;
- verify hash before resume;
- persist search state every trial;
- preserve the same run ID across resumed sessions;
- mark partial output as incomplete;
- synchronize verified artifacts to Drive at controlled intervals and completion.

---

# 7. Repository target structure

Adapt to the existing project instead of renaming correct working code unnecessarily.

```text
momo-fraud-detection/
├── apps/
│   ├── api/{main.py,routes,dependencies,middleware}/
│   └── web/{src,tests}/
├── src/momo_fraud/
│   ├── cli.py
│   ├── settings.py
│   ├── contracts/{requests.py,responses.py,reason_codes.py}/
│   ├── data/{registry.py,checksums.py,acquisition,validation,transaction,screenshots}/
│   ├── transaction/{features.py,splits.py,train.py,calibrate.py,evaluate.py,inference.py}/
│   ├── ocr/{base.py,tesseract.py,easyocr.py,paddleocr.py,preprocess.py,parser.py,evaluate.py}/
│   ├── image_forensics/{datasets.py,augmentations.py,classifier.py,localizer.py,train.py,evaluate.py,inference.py}/
│   ├── semantics/{rules.py,template_registry.py,consistency.py}/
│   ├── risk/{policy.py,thresholds.py,explanations.py}/
│   ├── registry/{bundles.py,integrity.py,compatibility.py}/
│   └── security/{image_validation.py,redaction.py,logging.py}/
├── configs/{datasets,transaction,ocr,image,risk}/
├── schemas/
├── notebooks/colab/
├── scripts/
├── data/{README.md,registry.yaml,manifests,fixtures}/
├── model_registry/{README.md,manifests}/
├── docs/{adr,architecture,audits,data-governance,dataset-cards,model-cards,runbooks,plans}/
├── reports/{generated,final}/
├── tests/{unit,integration,contract,leakage,security,fixtures}/
├── .github/workflows/
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── Dockerfile
└── README.md
```

Dataset registry entries include ID, canonical URL/version, license, redistribution, expected files/schema, sensitivity, required experiments, acquisition method, approval status, and optional expected count ranges. Private entries omit direct sensitive paths.

---

# 8. Artifact contracts

## 8.1 Transaction bundle

```text
transaction-core-<version>/
├── model.bin
├── preprocessor.bin
├── calibration.bin
├── feature_contract.json
├── thresholds.json
├── metrics.json
├── training_manifest.json
├── model_card.md
├── LICENSES.txt
└── bundle.sha256
```

The feature contract identifies every required, optional, and forbidden input, type, units, range, missing-value behavior, and availability timing.

## 8.2 Image bundle

```text
image-forensics-<version>/
├── classifier.onnx
├── localizer.onnx
├── preprocessing.json
├── class_map.json
├── thresholds.json
├── metrics.json
├── training_manifest.json
├── model_card.md
├── LICENSES.txt
└── bundle.sha256
```

Application code loads preprocessing from the bundle; it does not duplicate undocumented constants.

## 8.3 OCR/parser bundle

```text
ocr-parser-<version>/
├── engine.json
├── preprocessing.json
├── provider_templates.json
├── normalization_rules.json
├── benchmark_metrics.json
├── parser_test_corpus.jsonl
└── bundle.sha256
```

The committed parser corpus is fictitious.

## 8.4 Risk-policy bundle

```text
risk-policy-<version>/
├── policy.json
├── reason_codes.json
├── compatibility.json
├── calibration_report.md
└── bundle.sha256
```

The service rejects incompatible versions or explicitly disables a safe optional signal; it never silently mixes bundles.

## 8.5 Promotion states

- `candidate`: valid run artifact;
- `validated`: reproducibility, metrics, privacy, and compatibility checks pass;
- `approved`: release candidate;
- `retired`: retained for audit, no longer served.

Promote complete bundles, never isolated binaries.

---

# 9. OCR plan

## 9.1 Engines

Benchmark pretrained:

1. Tesseract 5;
2. EasyOCR;
3. PaddleOCR.

Do not train OCR from scratch in PR10–PR20. A fourth engine is optional and cannot delay the required benchmark.

## 9.2 Preprocessing grid

- original RGB;
- resolution-normalized RGB;
- grayscale/contrast normalization;
- adaptive thresholding for high-contrast SMS layouts;
- template/field-region crops.

Avoid processing that destroys decimal points or digits. Select variants on validation data and version them per template family.

## 9.3 OCR output

Return engine/version, full text, text confidence, boxes, parsed fields with raw/normalized values and confidence, and warnings. Preserve unknown/unavailable fields explicitly.

## 9.4 Metrics

- CER and WER;
- exact normalized match per field;
- exact amount to two decimals and absolute numeric error;
- parse success;
- CPU/accelerator latency;
- errors by template, resolution, theme, channel, and benign transform.

Weighted selector:

- amount exact: **30%**
- reference exact: **25%**
- timestamp exact: **15%**
- recipient normalized exact: **15%**
- CER/WER composite: **10%**
- median latency: **5%**

Validation release gates:

- amount exact ≥**95%**;
- reference exact ≥**90%**;
- timestamp exact ≥**90%**;
- recipient normalized exact ≥**90%**;
- required-field parse success ≥**90%**.

These are gates, not promised results. Failed gates are reported.

## 9.5 Confidence policy

- unavailable/low-confidence fields remain null;
- do not convert missing amount/reference to zero/empty strings;
- when amount and reference are both unavailable in screenshot-only mode, return `inconclusive` unless high image-tamper evidence independently triggers high risk;
- redact OCR text from logs by default.

---

# 10. Image-forensics plan

## 10.1 Tasks

Build:

1. global `unaltered`/`tampered` classifier;
2. pixel/region tamper localizer.

The classifier is a risk signal; localization supports explanation and checks whether the model focuses on edited text rather than logos/borders.

## 10.2 Baselines/candidates

- metadata/encoding heuristic baseline;
- simple image-feature baseline where feasible;
- MobileNetV3-Small-equivalent lightweight CNN;
- EfficientNet-B0-equivalent primary classifier;
- U-Net/DeepLab-style localizer with lightweight encoder.

Do not start with a huge vision transformer.

## 10.3 Inputs

- letterboxed global image: **512×512**;
- text-region crops: normally **384×384**;
- aggregate global/crop scores with a deterministic validation-fitted rule.

## 10.4 Safe augmentations

Allowed train-only: recompression, modest resize/resampling, mild blur/noise, small brightness/contrast, safe crop/pad, metadata stripping.

Disallowed by default: flips, large rotations, arbitrary perspective warps, character-erasing cutout, class-specific artifact creation, or transformations that expose the label.

## 10.5 Training stages

### A: generic pretraining

- approved STFD split or source-group-safe split;
- preserve masks;
- optional deterministic FSTS subset;
- no Ghana validation/final-test images.

### B: Ghana fine-tuning

- 420 controlled-real + 120 synthetic-clean train groups and derivatives;
- 90 controlled-real + 30 synthetic-clean validation groups;
- 90 controlled-real final-test groups inaccessible;
- balanced batches or class-weighted loss; validation prevalence unchanged.

Default classifier:

- AdamW;
- head LR `3e-4`;
- full-network LR `1e-5` to `3e-5`;
- weight decay `1e-4`;
- max 30 Ghana epochs;
- patience 7;
- mixed precision when supported;
- batch size 8/16/32 selected by preflight;
- seeds 42, 123, 2026.

Default localizer:

- combined BCE + Dice loss;
- foreground-aware sampling;
- max 40 epochs;
- patience 8;
- mask threshold selected on validation.

All deviations are versioned config changes.

## 10.6 Metrics and gates

Classification:

- AP/PR-AUC;
- macro F1;
- tampered recall;
- unaltered specificity;
- false-positive rate;
- balanced accuracy;
- calibration/Brier where probabilities are exposed;
- slices by provider/template/device/resolution/theme/target/method.

Localization:

- Dice;
- IoU;
- pixel precision/recall;
- hit-within-region;
- performance by tamper size.

Validation gates:

- macro F1 ≥**0.80**;
- tampered recall ≥**0.85**;
- unaltered specificity ≥**0.80**;
- localization Dice ≥**0.40**.

A failed gate means experimental status and conservative UI, not test manipulation.

## 10.7 Leakage checks

- perceptual near-duplicates do not cross partitions;
- all derivatives share a split;
- participant/source identity does not cross final-test boundary;
- masks/filenames/class directories are not model inputs;
- EXIF/software tags stripped/equalized in primary benchmark;
- benign transforms represented in train/validation;
- no watermark/label cue.

---

# 11. Semantic checks

Required deterministic checks:

- valid non-negative GHS amount and decimal precision;
- registered reference pattern when known;
- timestamp parseability and future-date plausibility after timezone normalization;
- provider/header/body consistency;
- recognized status: successful/failed/reversed/pending/unknown;
- duplicate/conflicting amounts;
- recipient name/wallet consistency where encoded;
- heatmap overlap with important fields;
- OCR/template agreement;
- screenshot versus structured amount/recipient/reference/timestamp/status in combined mode.

Unknown template is not automatically fraud. Return `template_unknown`, reduce confidence, or use `inconclusive` as policy requires.

---

# 12. Evidence-aware risk policy

## 12.1 No learned fusion yet

Do not train multimodal fusion until a paired dataset includes screenshots, reliable structured context, image-tamper labels, transaction-fraud outcomes, and enough data for an independent fusion calibration set. The proposed screenshot collection alone does not provide true transaction-fraud labels.

## 12.2 Signal object

```json
{
  "image": {"available": true, "tamper_probability": 0.0, "band": "low", "localization_quality": 0.0},
  "ocr": {"available": true, "quality": 0.0, "required_fields_present": true},
  "semantics": {"available": true, "severity": "none", "reason_codes": []},
  "transaction": {"available": false, "risk_probability": null, "band": null}
}
```

## 12.3 Initial logic

```text
if input validation fails:
    inconclusive
else if image available and image band high:
    high_risk
else if semantic contradiction major:
    high_risk
else if transaction available and transaction band high:
    high_risk
else if required OCR evidence unavailable:
    inconclusive
else if any available signal medium or semantic flag minor:
    medium_risk
else if all available signals low and evidence quality sufficient:
    low_risk
else:
    inconclusive
```

## 12.4 Thresholds

- image medium/high thresholds selected from Ghana validation precision-recall behavior;
- transaction probabilities calibrated on independent calibration data using sigmoid/isotonic as justified;
- transaction medium threshold selected by F2 subject to a documented FPR cap;
- high threshold selected by a documented precision target or an explicit fallback when infeasible;
- thresholds are dataset/model specific because synthetic prevalences differ;
- OCR confidence cutoffs come from validation error-rejection behavior;
- all thresholds stored in JSON bundles, never scattered as application constants.

## 12.5 Reason codes

Minimum registry:

```text
IMAGE_TAMPER_HIGH
IMAGE_TAMPER_MEDIUM
IMAGE_TAMPER_AMOUNT_REGION
IMAGE_TAMPER_REFERENCE_REGION
OCR_LOW_CONFIDENCE
OCR_AMOUNT_MISSING
OCR_REFERENCE_MISSING
REFERENCE_FORMAT_INVALID
TIMESTAMP_INVALID
TIMESTAMP_IN_FUTURE
STATUS_UNRECOGNIZED
TEMPLATE_UNKNOWN
PROVIDER_TEMPLATE_CONTRADICTION
SCREENSHOT_TRANSACTION_AMOUNT_MISMATCH
SCREENSHOT_TRANSACTION_RECIPIENT_MISMATCH
SCREENSHOT_TRANSACTION_REFERENCE_MISMATCH
TRANSACTION_BEHAVIOR_ANOMALY
TRANSACTION_NEW_RECIPIENT
TRANSACTION_VELOCITY_HIGH
TRANSACTION_SEQUENCE_ANOMALY
MODEL_UNAVAILABLE
MODEL_CONTRACT_MISMATCH
INSUFFICIENT_EVIDENCE
```

Each code has internal/user text, severity, applicable modes, and remediation.

---
# 13. API, security, and UI contract

## 13.1 Endpoints

```text
POST /api/v1/analyses/screenshot
POST /api/v1/analyses/transaction
POST /api/v1/analyses/combined
GET  /api/v1/analyses/{analysis_id}
GET  /api/v1/models/status
GET  /health/live
GET  /health/ready
```

The initial deployment may process synchronously if measured latency is acceptable, but the response contract must remain compatible with queued jobs.

## 13.2 Requests

Screenshot multipart:

```text
image: required
consent_to_process: required boolean
expected_amount: optional decimal
expected_recipient: optional string
expected_reference: optional string
client_request_id: optional UUID
```

Expected values are user-supplied comparison evidence, not verified truth.

Transaction JSON contains transaction type, amount, timestamp, pseudonymous initiator/recipient IDs, and prior history when available. Never accept PINs, OTPs, passwords, or authentication secrets.

Combined mode carries both and compares sufficiently confident normalized fields.

## 13.3 Response

Every completed response contains:

- analysis ID/time/mode;
- `risk_band` and evidence quality;
- `not_a_verification: true` unless provider verification exists;
- component availability/scores/bands/model versions;
- OCR fields with confidence;
- reason codes/messages;
- limitations;
- policy version.

Unavailable signals are explicit `null`, not omitted or zero.

## 13.4 Upload security

Default controls:

- PNG/JPEG/WebP only;
- inspect decoded content, not extension/MIME alone;
- maximum upload **15 MiB**;
- maximum decoded pixels **40 million**;
- reject zero-size, truncated, animated/multi-frame unless supported;
- decompression-bomb protection;
- safe orientation normalization;
- strip metadata from working copy;
- SHA-256 content ID;
- isolated non-executable temporary directory;
- cleanup after success/failure/timeout;
- rate/concurrency limits;
- never pass filenames to shell commands;
- model bundle path traversal/integrity checks.

Limits are configurable and visible to users.

## 13.5 Logging/retention

Log request ID, time, mode, model/policy versions, reason codes, component status, and latency. Do not log raw image, OCR text, phone number, name, reference, balance, consent record, or token. Process uploads ephemerally by default. Analysis consent is separate from research-contribution consent.

## 13.6 UI flow

1. choose evidence mode;
2. enter/upload evidence and accept privacy notice;
3. review extracted fields and confidence;
4. see risk band, evidence quality, reasons, limitations, and optional heatmap;
5. see technical details/model versions;
6. guidance: verify through official provider channels and never disclose PIN/OTP.

User corrections are stored separately from raw OCR output and do not rewrite evaluation evidence.

## 13.7 Accessibility/language

- do not use color alone;
- keyboard/screen-reader support and sufficient contrast;
- use “low risk,” not “safe”;
- use “inconclusive” for insufficient evidence;
- no “100% fraud,” “verified,” or certainty language;
- heatmap explained as model evidence, not proof.

## 13.8 Candidate performance targets

Report p50/p95 on named hardware:

- transaction inference p95 <**500 ms** excluding network;
- screenshot analysis p95 <**10 s** on selected accelerator and <**25 s** on documented CPU fallback;
- validation rejection <**500 ms**;
- bounded memory/concurrency.

Target misses are documented and may trigger asynchronous mode.

---

# 14. Testing, CI, and reproducibility

## 14.1 CI jobs

1. `quality`: format, lint, types, notebook cleanliness, schemas/docs.
2. `unit-tests`: pure logic, parsers, fixed seeds, no network.
3. `contract-tests`: API schemas, nullable signals, bundle compatibility, reason registry.
4. `data-safety`: no large/raw data, no PII filenames, no secrets, fixture provenance.
5. `leakage-tests`: causal history, group splits, forbidden features, final-test guards.
6. `smoke-ml`: tiny transaction/image fit, OCR mock/tiny fixture, export/reload, one API call.
7. `api-integration`: valid/invalid uploads, limits, modes, cleanup, unavailable models.
8. `frontend`: component, accessibility, upload/result flow with mocked API.
9. `container`: build, non-root, health/readiness, dependency inventory/SBOM where supported.

CI never downloads full datasets.

## 14.2 Fixtures

- ≤1,000 fictitious transaction rows;
- purpose-built screenshot fixtures with no real identities;
- clean/tampered/low-resolution/dark/malformed/unsupported examples;
- fixture card documents provenance and publication safety.

## 14.3 Reproducibility gate

Before a result enters the report:

- dataset/split/config/code hashes match;
- Git state recorded;
- metrics derived from machine-readable predictions;
- plots regenerated by scripts;
- bundle hash matches run manifest;
- bundle reload reproduces predictions within tolerance;
- no private or final-test data contamination.

## 14.4 Final-test controls

- final manifests stored separately;
- training notebooks fail on final-test paths;
- only `10_locked_final_evaluation.ipynb` loads them;
- release candidate hashes required;
- evaluation receipt written before metrics;
- no tuning after results.

---

# 15. PR10–PR12 reconciliation protocol

Because the repository was unavailable during planning and Codex may already have completed PR10–PR12:

1. inspect merged PRs 1–12, default branch, open PRs, CI, issues, architecture, and tests;
2. run the baseline suite;
3. create `docs/audits/pr10-pr12-gap.md`;
4. map each requirement to `complete`, `partial`, `absent`, or `conflicting`, with file/commit/PR evidence;
5. preserve correct existing work and naming;
6. do not rewrite Git history or open duplicate PRs solely for numbering;
7. place missing PR10–PR12 items in the next unmerged PR under a “reconciliation” section;
8. verify behavior/tests rather than assuming a similarly named file is complete.

Logical milestone numbers below describe scope. Actual GitHub PR numbers remain the source of truth.

---
# 16. Detailed pull-request roadmap

## PR10 — Architecture correction and Colab-only training

**Goal:** separate evidence pipelines, prohibit invented transaction features, define conservative result language, and move complete training to Colab.

**Suggested branch/title**

```text
feat/pr10-architecture-colab-policy
PR10: Define evidence-aware architecture and Colab-only training
```

**Work**

- add ADRs for Colab-only full training, evidence modes, unaltered-not-verified, and no invented missing features;
- add shared contracts for image, OCR, semantic, transaction, and policy results;
- add `screenshot_only`, `transaction_only`, `combined`, `inconclusive` modes;
- migrate canonical image labels from genuine/fake to unaltered/tampered;
- add risk bands and explicit nullable unavailable signals;
- add unit/smoke/full profiles and full-training guard;
- update architecture/README/limitations;
- document API migration and compatibility shim where existing code requires it.

**Tests**

- screenshot-only transaction score is null;
- transaction-only image/OCR signals unavailable;
- missing history/balance cannot become zero defaults;
- new canonical data rejects `genuine` label;
- full training blocked without acknowledgment;
- no rendered result says safe/verified/100%.

**Done when**

- ADRs are linked and behavior is enforced by tests;
- application compiles under new contracts;
- no production path manufactures transaction input from OCR;
- CI passes.

**Do not include:** dataset downloads, training claims, final thresholds, learned fusion.

---

## PR11 — Governance, schemas, and dataset registry

**Goal:** establish lawful, private, machine-readable data handling before acquisition/collection.

**Suggested branch/title**

```text
feat/pr11-data-governance-registry
PR11: Add dataset registry, privacy controls, and data schemas
```

**Work**

- create `data/registry.yaml` for PaySim, MoMTSim v1/v2, STFD, optional FSTS, and Ghana-private;
- add dataset cards with source/version/license/use/limits/class distribution/citation;
- add JSON schemas for transactions, screenshots, OCR truth, edit manifests, split manifests, and runs;
- add data dictionary and tamper taxonomy;
- add participant information/consent templates, internal-vs-public consent, withdrawal/deletion process, de-identification standard, access roles, retention schedule, incident contact, publication checklist;
- add threat model and `DATA_ACCESS.md`;
- add `.gitignore` for data/checkpoints/models/secrets/consent records;
- add large-file, secret, and PII-filename validators;
- add fictitious fixtures and provenance card.

**Tests**

- registry/schema validation;
- all fixtures validate;
- raw paths ignored;
- test harness proves secret/PII/large-file checks fail correctly;
- consent scope required for private records;
- taxonomy percentages sum to 100%.

**Done when**

- no collection starts without approved process;
- governance is executable in CI;
- public fixtures are demonstrably fictitious;
- licenses/redistribution are explicit.

**Do not include:** real screenshots, completed consent records, direct identifiers, unsupported legal claims.

---

## PR12 — Reproducible Colab foundation

**Goal:** make clean-session, restart-safe, manifest-producing Colab execution work before expensive runs.

**Suggested branch/title**

```text
feat/pr12-colab-foundation
PR12: Add reproducible Colab runtime and run manifests
```

**Work**

- add locked environments;
- add `00_environment_preflight.ipynb` and notebook template;
- configure Drive paths without personal hard-coding;
- add repo clone/update and commit recording;
- add runtime inventory/seeding;
- add run IDs/manifests, atomic writer, checkpoints, resume;
- add SMOKE/FULL parameters;
- load Colab Secrets without printing;
- add notebook lint/output checks;
- add tiny end-to-end smoke notebook;
- add lost-runtime recovery runbook;
- ensure CI never enters full mode.

**Smoke flow**

Mount Drive, install locked environment, inventory runtime, load fixtures, run tiny transaction preprocessing/fit, lightweight OCR, one tiny image epoch, export/reload bundles, and emit a complete run manifest.

**Tests**

- deterministic fixture split/predictions within tolerance;
- corrupt checkpoint rejected and valid checkpoint resumes;
- secrets absent from notebook/logs;
- run manifest validates;
- restart-and-run-all works;
- full mode blocked locally/CI.

**Done when:** fresh Colab can execute smoke from top to bottom with complete artifacts and no private data.

---

## PR13 — Dataset acquisition, registration, and validation

**Goal:** reproducibly obtain/register approved data without committing bytes, and fail closed on wrong versions.

**Suggested branch/title**

```text
feat/pr13-dataset-acquisition-validation
PR13: Add reproducible dataset acquisition and validation
```

**Work**

- complete PR10–12 gap audit if needed;
- implement PaySim Kaggle acquisition;
- implement MoMTSim manual/approved-URL registration;
- implement STFD protected archive registration;
- implement optional deterministic FSTS subset registration;
- implement Ghana-private folder registration;
- add acquisition and validation notebooks;
- validate schema, types, counts, class distribution, duplicates, null/invalid values, image/mask integrity, checksums, and archive identity;
- add quarantine state and content-addressed manifests;
- add safe inventory/profile reports;
- add license/terms acknowledgment gates;
- add no-network fake-archive tests.

**PaySim checks**

- about 6.36M rows, 8,213 positives, 744 steps;
- expected transaction types/columns;
- target non-empty;
- mark `isFlaggedFraud` and four balances forbidden for primary benchmark.

**MoMTSim checks**

- v1 about 1.72M rows/175,518 positives;
- v2 about 4.23M rows/2,233,118 positives;
- required transaction/actor/balance/label fields;
- separate manifests.

**STFD/FSTS checks**

- image decode;
- mask/image dimensions;
- label/mask consistency;
- recoverable groups;
- no restricted content in reports;
- deterministic subset IDs.

**Artifacts**

```text
data/manifests/<dataset>.manifest.json
reports/generated/dataset_inventory.md
reports/generated/dataset_validation/<dataset>.json
reports/generated/dataset_profiles/<dataset>-safe-summary.json
```

**Tests:** hash/schema/count drift, idempotence, token redaction, deterministic subsets, protected-data export refusal.

**Done when:** PaySim and both MoMTSim files validate in Colab; STFD path is documented even if access pending; all bytes remain outside Git.

**Do not include:** training, post-performance split changes, redistribution, unknown mirror acceptance.

---

## PR14 — Transaction ETL, causal features, and frozen temporal splits

**Goal:** create memory-conscious, leakage-tested features and freeze 70/10/10/10 splits before model selection.

**Suggested branch/title**

```text
feat/pr14-transaction-data-pipeline
PR14: Build leakage-safe transaction features and temporal splits
```

**Work**

- canonical source mapping for PaySim/MoMTSim;
- use measured Polars/DuckDB/chunked processing for millions of rows;
- preserve immutable row IDs/source metadata;
- split by sorted unique `step`: 70 train, 10 tune, 10 calibration, 10 locked test;
- enforce minimum positives and minimal boundary adjustment;
- freeze manifests with ranges/counts/prevalence/hashes;
- build base and causal-history features;
- enforce forbidden fields;
- fit preprocessing on training only;
- generate safe train/tune EDA;
- add `03_build_transaction_features.ipynb`;
- write sharded Parquet outputs atomically;
- publish inference feature contract.

**Base features**

```text
transaction_type, amount, log_amount, step, hour_sin, hour_cos,
initiator_role, recipient_role
```

**Causal features**

```text
time_since_previous, count/sum prior 1h/6h/24h,
prior 24h mean/median, amount-to-median ratio,
unique recipients prior 24h, is_new_recipient,
sequence pattern, causal graph degree
```

Every window excludes current/future transactions. No-history uses a documented missing indicator and neutral representation, never an invented record.

**Leakage tests**

- current/future rows cannot influence earlier features;
- future-row insertion leaves earlier features unchanged;
- train-only preprocessing;
- no cross-partition row/step overlap;
- raw IDs/target/forbidden columns absent;
- calibration/test transforms never refit;
- deterministic missing-history behavior.

**Reports:** counts/prevalence, amount/type distributions, missingness, activity aggregates, drift, split statistics, excluded features/reasons. No raw IDs.

**Done when:** required datasets produce canonical/features in Colab, manifests are frozen, leakage suite passes, memory/runtime recorded, and final labels are not used for decisions.

---

## PR15 — Transaction training, calibration, and export

**Goal:** train baselines/candidates in Colab, calibrate independently, select policy thresholds, and export `transaction_core` without opening test.

**Suggested branch/title**

```text
feat/pr15-transaction-models
PR15: Train and calibrate transaction-risk models in Colab
```

**Work**

- adapters for dummy, logistic, histogram boosting, XGBoost, and secondary forest;
- config-driven resumable search;
- train-only class weighting/sampling;
- validation ranking;
- independent calibration partition;
- validation/calibration threshold selection;
- seeds 42/123/2026 for selected candidates;
- cross-dataset compatible-feature experiments;
- feature ablations;
- `04_train_transaction_models.ipynb`;
- versioned bundles/model cards;
- inference/reload tests;
- final-test access disabled.

**Default search maxima per dataset**

- logistic: 8 configurations;
- histogram boosting: 20;
- XGBoost: 30;
- forest: 12 on documented subset if needed.

Search spaces and values are saved. Early termination is allowed when ranking is stable and documented.

**Selection order**

1. average precision;
2. recall/FPR operating constraint;
3. calibration;
4. seed/time stability;
5. latency/size;
6. explanation support.

Accuracy does not select the model.

**Calibration**

Fit model on train, choose hyperparameters on tune, fit sigmoid and—if positive count supports it—isotonic on the independent calibration partition, select without final test, and save reliability/Brier artifacts. Calibration remains synthetic-source-specific.

**Threshold artifact**

- medium: maximize F2 subject to documented FPR cap;
- high: lowest threshold meeting documented precision target, otherwise explicit fallback;
- record selected metrics/rule and `not_real_world_probability: true`.

**Explainability**

Stable categories only: unusual amount, high velocity, new recipient, sequence anomaly. No raw IDs/PII and no proof language.

**Model card**

Intended/prohibited use, provenance/synthetic nature, features/exclusions, split, tune/calibration metrics, thresholds, imbalance handling, limitations/domain shift, privacy, inference requirements, version/hash.

**Tests**

- score contract supported;
- independent calibrator;
- final manifest cannot import;
- bundle reload parity;
- missing required context fails validation;
- no raw IDs in artifacts/explanations;
- model/policy version mismatch rejected.

**Done when:** PaySim and MoMTSim v1 runs exist; v2 completed or transparently deferred; candidate/baselines compared; calibrated bundle runs local smoke; test unopened; no Ghana probability claim.

---
## PR16 — Ghana screenshot collection, de-identification, and tamper generation

**Goal:** implement the private Ghana-domain dataset pipeline, complete a validated pilot, generate reproducible edits/masks, and freeze group-safe splits.

**Suggested branch/title**

```text
feat/pr16-ghana-screenshot-dataset
PR16: Build the controlled Ghanaian screenshot dataset pipeline
```

**Preconditions**

- governance/retention approved by supervisor/institution;
- access-controlled Drive exists;
- withdrawal/deletion operator assigned;
- no real screenshot/consent file will appear in Git or PR attachments.

**Work**

- private-data import with pseudonymous IDs and consent validation;
- filename/metadata/region de-identification;
- cryptographic and perceptual duplicate detection;
- fictitious synthetic-clean template generation;
- edit-manifest generators for amount, recipient, reference, date/time, status, header, and multi-field cases;
- replacement/splice/removal-insertion/copy-move/inpainting/manual-composite methods and masks;
- benign hard-negative generation;
- annotation/review queues;
- participant/source-group split generation;
- private notebook `05_build_ghana_screenshot_dataset.ipynb`;
- public-safe dataset card and private QA report;
- withdrawal/deletion propagation;
- separate `approved_internal` and `release_approved` states.

**Stages**

1. pipeline pilot: ≥30 controlled-real + 20 synthetic-clean groups;
2. minimum study: 250 controlled-real groups, about 1,000 images;
3. recommended: 600 controlled-real + 150 synthetic-clean, 3,750 primary images, plus 450 hard negatives when feasible.

PR16 can merge after a validated pipeline/pilot while collection continues, but PR20 reports actual achieved counts and any approved scope reduction.

**Edit manifest includes** source/output hash, target, method, tokenized old/new values, regions, mask hash, generator version/parameters, and review state. Manual edits require editor pseudonym, operations, mask, identity-safety confirmation, and review.

**Split procedure**

- group all derivatives by source;
- group repeated participant/source identities;
- controlled-real 70/15/15;
- synthetic-clean 80/20/0;
- stratify groups by provider/template/channel/device/theme as possible;
- generate restricted final manifest and publish aggregate counts/hash only;
- run perceptual duplicate checks;
- freeze before OCR/image selection.

**Workflow states**

```text
ingested → needs_deidentification → needs_transcription → needs_field_annotation
→ needs_mask_review → needs_second_annotation → needs_adjudication
→ approved_internal / release_review_pending / withdrawn / quarantined
```

**Tests**

- mask/change alignment;
- benign transform preserves semantics;
- no group/identity split leakage;
- PII filename/metadata checks;
- withdrawal removes/quarantines indexed derivatives and records receipt;
- manual edit without mask/review rejected;
- quota calculations correct;
- final path inaccessible to training loader.

**Done when:** governance recorded, safe pipeline works, private pilot passes QA/deletion/split checks, manifests frozen at chosen milestone, no private data leaks.

**Do not include:** scraping, high-value transfers, public brand/user data without review, “genuine transaction” label, post-result test curation.

---

## PR17 — OCR benchmark, parser, and semantic validation

**Goal:** benchmark pretrained OCR engines on grouped Ghana validation data, select a deployable version, parse fields robustly, and quantify failures.

**Suggested branch/title**

```text
feat/pr17-ocr-parser-benchmark
PR17: Benchmark OCR engines and implement MoMo field parsing
```

**Work**

- shared OCR adapter/result;
- Tesseract 5, EasyOCR, PaddleOCR adapters;
- preprocessing variants;
- template/channel detector with `unknown`;
- parsers for amount/currency, recipient, wallet, reference, timestamp/timezone, status, provider hints;
- box association and field confidence;
- deterministic semantic rules;
- evaluation code and `06_benchmark_ocr.ipynb`;
- CPU/accelerator latency;
- selected OCR/parser bundle;
- fictitious parser regression corpus;
- failure/inconclusive fallback.

**Data use:** develop on training annotations; select engine/preprocessing/confidence on validation only; locked Ghana test inaccessible. Primary selection uses controlled-real validation, with synthetic results supplementary.

**Normalization**

- preserve raw values;
- amount: documented GHS symbols/separators, reject ambiguity;
- recipient: case/whitespace normalization without deleting meaningful digits;
- reference: only known separators; digit/letter ambiguity lowers confidence;
- timestamp: known formats, explicit Africa/Accra/UTC handling, ambiguous order flagged;
- status: successful/failed/reversed/pending/unknown; unknown never defaults to success.

**Benchmark matrix:** controlled-real clean validation, one fixed tampered derivative per group, benign hard negatives, resolution/theme/channel/provider/template/tamper slices. Use a predeclared two-stage configuration screen if full grid is expensive.

**Selection:** weighted metric in Section 9 plus field gates, latency, install reliability, package size, CPU fallback, and license. Close engines favor amount/reference and simpler deployment.

**Tests**

- adapters share schema;
- parser corpus covers separators, masks, ambiguous characters, dates/statuses;
- unknown template not automatically high risk;
- future-date check uses explicit timezone/test clock;
- no silent OCR correction;
- failures return unavailable fields;
- low-confidence amount/reference activates inconclusive rule;
- logs redact text;
- bundle replay parity.

**Done when:** all required engines measured or incompatibility documented; selected configuration/version/thresholds and field metrics reported; test remains locked.

---

## PR18 — Image tamper classifier, localizer, and Ghana adaptation

**Goal:** train generic/Ghana-adapted image models in Colab, validate localization, select thresholds, and export deployable bundles without test access.

**Suggested branch/title**

```text
feat/pr18-image-forensics-models
PR18: Train screenshot tamper classification and localization models
```

**Work**

- group-safe loaders/samplers;
- global and crop inputs;
- safe augmentation/hard negatives;
- heuristic/lightweight/EfficientNet-like classifier baselines;
- lightweight U-Net/DeepLab-like localizer;
- STFD pretraining when approved;
- optional deterministic FSTS subset;
- Ghana fine-tuning/validation;
- balanced batches/weights and foreground sampling;
- early stopping/checkpointing/three seeds;
- validation calibration/thresholds;
- slice/leakage reports;
- notebooks `07_pretrain_image_forensics.ipynb`, `08_finetune_ghana_image_model.ipynb`;
- ONNX/chosen export and preprocessing contract;
- model card and safe qualitative gallery;
- local smoke inference.

**Experiment order**

1. metadata/heuristic baseline;
2. lightweight Ghana-only CNN;
3. EfficientNet-like Ghana-only candidate;
4. STFD-pretrained classifier + Ghana fine-tune;
5. STFD-pretrained localizer + Ghana fine-tune;
6. global+crop aggregation;
7. hard-negative ablation;
8. optional FSTS subset.

This establishes whether transfer learning helps rather than assuming larger data wins.

**Loss/sampling**

- classifier: BCE with validated weights; focal loss ablation;
- group-aware sampler;
- benign hard negatives remain unaltered;
- localizer initial loss `0.5 BCE + 0.5 Dice`;
- empty clean masks included;
- config/version required for any change.

**Slices:** controlled-real/synthetic, provider/template/channel/device/resolution/theme, benign transform, target/method, region size, programmatic/manual. Report counts/CIs and avoid overinterpreting small slices.

**Qualitative fixed gallery:** original, truth mask, heatmap, score; TP/TN/FP/FN; check focus on edited text rather than logos/borders. Git uses only synthetic/release-approved images.

**Robustness:** recompression, resize, blur/noise, crop/pad, metadata stripping, screen-photo subset. Measure false-positive changes.

**Export validation:** framework vs export on ≥100 validation samples, numerical tolerance, preprocessing parity, CPU/accelerator latency, correct de-letterboxed heatmaps, bundle hash.

**Tests**

- no partition crossing;
- transforms preserve label/mask;
- clean masks remain empty;
- export parity;
- thresholds derive from validation artifact;
- final loader unavailable;
- no filenames/EXIF cues;
- heatmap coordinates correct;
- offline bundle loading.

**Done when:** baselines/candidates have manifests, transfer benefit quantified, validation metrics/slices honest, gates met or experimental status assigned, bundle deployed in smoke, test locked.

---

## PR19 — Risk engine, API, UI, and deployment

**Goal:** integrate approved bundles securely while preserving evidence boundaries, conservative language, and auditable reasons.

**Suggested branch/title**

```text
feat/pr19-risk-api-ui-integration
PR19: Integrate evidence-aware risk analysis across API and UI
```

**Backend work**

- bundle registry/integrity/compatibility;
- screenshot/transaction/combined services;
- versioned policy and threshold loading;
- reasons/explanations;
- timeouts/failure isolation;
- Section 13 endpoints/schemas;
- safe upload processing/cleanup/rate limits;
- minimized logs;
- liveness/readiness/model status;
- model/upload/retention/concurrency config;
- async-compatible response/job contract;
- safe unavailable/contract-mismatch behavior;
- fictitious OpenAPI examples;
- latency instrumentation.

**Frontend work**

- mode selection;
- accessible upload/transaction forms;
- privacy/consent notice;
- extracted-field review preserving raw OCR;
- four risk states and evidence quality;
- reasons/limitations;
- optional heatmap and text alternative;
- model/policy technical details;
- partial failure/retry states;
- responsive/mobile design;
- no-PIN/no-OTP warning;
- official verification guidance without endorsement implication.

**Startup sequence:** verify hashes, runtime compatibility, policy/model constraints, self-test vectors, readiness; degraded mode only when policy supports it and response exposes missing signal. Never load an unversioned fallback.

**Failure behavior**

- missing image model: screenshot generally inconclusive unless major semantic evidence; combined may use transaction but image unavailable explicit;
- missing OCR: high image tamper can still yield high; otherwise screenshot often inconclusive;
- parser missing amount/reference: inconclusive unless independent high signal;
- missing transaction model: screenshot may operate; transaction signal null;
- policy/bundle incompatibility: fail safely.

**Combined comparison:** compare only present/confident normalized amount/reference/recipient/timestamp/status. Low-confidence OCR mismatch cannot become major without corroboration.

**Security tests:** MIME spoofing, malformed/truncated/decompression bomb/path traversal, repeated multipart, oversize/animation, concurrency, log redaction, temp cleanup, corrupt bundle, invalid JSON numbers, rate limits, safe errors.

**Contract/UI tests:** null unavailable signals, corrections separate, unknown template safe, insufficient evidence inconclusive, low risk includes limitation, versions/reasons complete, keyboard/screen reader, no color-only or certainty wording.

**Deployment:** non-root Docker, environment reference, model mount/download and rollback runbooks, dependency inventory, demo-only seed data, no training at startup.

**Done when:** all modes end-to-end, policy reproducible from stored signals, tests pass, container runs offline with mounted bundles, latency/resources documented, raw uploads not retained by default.

**Do not include:** hard-coded thresholds, naïve score average, hidden degraded mode, implied provider endorsement, OCR/raw image logs, training in app container.

---

## PR20 — Locked final evaluation and research release

**Goal:** freeze candidate, open locked tests once, produce final metrics/CIs/ablations/robustness, package release, and report limitations without post-test tuning.

**Suggested branch/title**

```text
release/pr20-final-evaluation
PR20: Run locked evaluation and package the research release
```

**Preconditions**

- model/policy bundle hashes approved;
- no open preprocessing/feature/model/calibration/threshold/evaluation changes;
- test manifests/hashes frozen;
- evaluation protocol/metric definitions/report templates committed;
- validation decisions complete;
- team signs access checklist;
- evaluation candidate commit tagged internally.

**Before evaluation**

- add final protocol;
- add guarded final notebook;
- add group/block bootstrap CI code;
- add frozen metric/table/figure/ablation configs;
- add evaluation receipt/hashing;
- complete model/dataset/policy/system card templates;
- add export notebook, release container, and inspection checklist.

**One-time procedure**

1. fresh Colab runtime;
2. exact commit/clean state;
3. locked dependencies;
4. restricted Drive;
5. verify all hashes;
6. write receipt before loading labels;
7. predict once and save immutable per-record predictions;
8. compute metrics/figures from predictions;
9. store restricted artifacts;
10. commit only aggregate/non-sensitive approved outputs;
11. no retraining/threshold change.

If a genuine software/data bug invalidates the run, quarantine/document it and justify any rerun transparently. Do not erase unfavorable results.

**Transaction final metrics**

Rows/prevalence, AP, ROC-AUC, precision/recall/F1/F2 at bands, FPR/FNR, confusion matrices, Brier/calibration, precision-at-recall/recall-at-FPR, type/amount slices, latency/size, baseline comparison, compatible cross-dataset performance, documented temporal/block CIs. Emphasize synthetic limitations.

**Screenshot final metrics**

Use 90 controlled-real groups:

- full 450-image view;
- balanced fixed 180-image view;
- AP, macro F1, tamper recall, clean specificity, FPR, balanced accuracy, confusion, calibration;
- Dice/IoU/pixel metrics;
- provider/template/channel/device/resolution/theme/target/method/benign transform/manual-programmatic slices;
- 95% bootstrap CIs resampled by source group, not derivative image.

**OCR final metrics:** CER/WER, field exact matches, parse success, confidence rejection, latency, slices, clean versus tampered fields.

**End-to-end evaluation:** predeclared screenshot-only, transaction-only, combined matching/mismatching, OCR failure, unknown template, missing model, malicious upload. Report risk-band behavior, inconclusive rate, reason coverage, failure behavior, latency/memory, retention/log checks. Do not create one mixed “fraud accuracy” across different targets.

**Frozen ablations**

- transaction: base/time/history/balance-research, weighting/sampling, raw/calibrated;
- image: Ghana-only/STFD, global/crop/combined, with/without hard negatives, classifier/localizer support, programmatic/mixed edits;
- OCR: engines/preprocessing/global-vs-region;
- policy: image, semantic, transaction, transparent combined controlled scenarios.

**Error/robustness analysis:** deterministic FP/FN sample, compression/resize/blur/crop/screen photo, unknown templates, localizer focus, synthetic artifacts, domain shift, component-level causes. Public figures use only synthetic/release-approved samples.

**Final documents**

```text
docs/model-cards/{transaction,image,ocr,risk-policy}-<version>.md
docs/system-card.md
docs/dataset-cards/{paysim,momtsim,stfd,ghana-private}.md
reports/final/{methodology,results,error-analysis,limitations,reproducibility,release-checklist}.md
```

**Release gates:** reproducible metrics, no leakage, bundle integrity, security/privacy/accessibility pass, clean deployment smoke, complete cards/licenses, no private data, prominent limits, component status clearly research/experimental/validated-for-demo.

**Post-test rule:** no tuning, no removing difficult samples except an objective pre-existing quality rule; any next model is a new version requiring a new untouched evaluation protocol/test.

**Done when:** receipt/predictions/results/CIs reproduce; targets remain separate; release artifacts are private-data-free; final container/UI/API pass; failures and limitations disclosed; release tag identifies exact commit/artifact hashes.

---
# 17. Milestone dependency and artifact matrix

| Logical PR | Depends on | Colab full run? | Primary output | Locked test access? |
|---|---|---:|---|---:|
| PR10 | existing application | No | architecture contracts and ADRs | No |
| PR11 | PR10 | No | governance, schemas, registry | No |
| PR12 | PR10–11 | Smoke only | reproducible Colab foundation | No |
| PR13 | PR11–12 | Acquisition/validation | dataset manifests | No |
| PR14 | PR13 | Yes, preprocessing | temporal split and feature manifests | Creates but does not read test labels for decisions |
| PR15 | PR14 | Yes, transaction training | calibrated transaction candidate bundle | No |
| PR16 | PR11–13 | Yes, private data processing | Ghana dataset and frozen grouped splits | Creates/restricts test |
| PR17 | PR16 | Yes, OCR benchmark | OCR/parser bundle | No |
| PR18 | PR13, PR16 | Yes, image training | image classifier/localizer bundle | No |
| PR19 | PR15, PR17, PR18 | No full training; integration benchmarks | risk policy, API, UI, container | No |
| PR20 | all | Yes, one-time evaluation/export | final metrics, reports, release bundles | **Yes—once** |

## 17.1 Promotion gates between PRs

- PR13 cannot begin full acquisition until PR11 registry/license fields exist.
- PR14 cannot freeze splits until PR13 validation passes.
- PR15 cannot train from an ad hoc notebook table; it must use PR14 manifests/features.
- PR17 and PR18 cannot use Ghana data before PR16 approves records and freezes group-safe splits.
- PR19 cannot hard-code development model paths or thresholds; it loads versioned bundles.
- PR20 cannot execute until the release candidate commit, bundles, policy, and protocol are frozen.

---

# 18. Exact experiment and reporting matrix

## 18.1 Transaction experiments

| ID | Train source | Evaluation before PR20 | Final test in PR20 | Purpose |
|---|---|---|---|---|
| TX-A | PaySim train | PaySim tune/calibration | PaySim locked 10% | extreme-imbalance baseline |
| TX-B | MoMTSim v1 train | v1 tune/calibration | v1 locked 10% | broader fraud-scenario model |
| TX-C | MoMTSim v2 train | v2 tune/calibration | v2 locked 10% if approved | high-fraud stress test |
| TX-D1 | PaySim | compatible non-final external partition | predeclared compatible external test | domain generalization |
| TX-D2 | MoMTSim v1 | compatible non-final external partition | predeclared compatible external test | reverse generalization |
| TX-E | pooled compatible train partitions | per-source tune/calibration | per-source locked tests | optional pooled research model |

For each required candidate, run seeds 42, 123, and 2026 after hyperparameter selection. Report mean, standard deviation, and selected deployable artifact policy.

## 18.2 Screenshot experiments

| ID | Generic pretraining | Ghana train | Ghana validation | PR20 test |
|---|---|---|---|---|
| IMG-B1 | none | controlled-real + synthetic clean | grouped validation | grouped controlled-real final |
| IMG-P1 | STFD classifier | same | same | same |
| IMG-P2 | STFD localizer | same | same | same |
| IMG-C1 | selected pretraining | global + crops | same | same |
| IMG-H1 | selected pretraining | with hard negatives | same | same |
| IMG-F1 optional | deterministic FSTS subset | same | same | same |

## 18.3 OCR experiments

| Engine | Preprocessing screen | Full validation | PR20 final |
|---|---:|---:|---:|
| Tesseract 5 | Yes | Yes | selected engine plus comparison summary |
| EasyOCR | Yes | Yes | comparison summary |
| PaddleOCR | Yes | Yes | comparison summary |

The selected engine receives the full final field/slice report. Alternatives receive enough final comparison to support the engine-selection claim, without changing the selection.

## 18.4 Result terminology matrix

| Evidence/label | Permitted statement | Prohibited statement |
|---|---|---|
| image `unaltered` prediction | “No visible manipulation detected at this operating point.” | “The transaction is genuine.” |
| image `tampered` prediction | “Possible image manipulation was detected.” | “Fraud definitely occurred.” |
| structured high risk | “The supplied transaction context resembles high-risk synthetic patterns.” | “This is a confirmed fraudulent transaction.” |
| low combined risk | “No configured high-risk evidence was found in the supplied evidence.” | “Safe to release funds.” |
| inconclusive | “The evidence was insufficient or unreadable.” | “Not fraud.” |

---

# 19. Risk register

| Risk | Likelihood | Impact | Mitigation | Evidence to retain |
|---|---|---|---|---|
| Colab session loss | high | medium | VM-local work, checkpoints, atomic Drive sync, resumable trials | session list and checkpoint hashes |
| Dataset license/terms conflict | medium | high | registry, stricter terms, no redistribution, supervisor review | dataset card and access record |
| PII leakage from screenshots | medium | high | consent, de-identification, private storage, CI guards, log redaction | QA and deletion receipts |
| Train/test derivative leakage | high without controls | critical | source/participant grouping, perceptual hash checks, locked manifest | leakage report |
| PaySim balance leakage | high if copied from tutorials | high | explicit forbidden-feature test | feature contract/test |
| Synthetic prevalence misinterpreted | high | high | label scores carefully, report prevalence, no Ghana probability claim | model/system cards |
| Model learns logos/templates | medium | high | diverse sources, masks, slice analysis, qualitative heatmaps | slice and localization report |
| Benign compression treated as tamper | high | medium | hard negatives and robustness testing | benign-transform metrics |
| OCR digit confusion | high | high | engine benchmark, field confidence, inconclusive fallback | field metrics/error analysis |
| Unknown provider/template | high in deployment | medium | explicit unknown path, conservative policy | unknown-template tests |
| Threshold overfitting | medium | high | independent calibration, frozen thresholds, final test once | threshold artifact |
| Combined score has no scientific meaning | high if naïvely averaged | high | transparent policy; no learned fusion without paired labels | risk-policy card |
| Repository drift from plan | medium | medium | PR10–12 gap audit, adapt structure, behavior-based acceptance | audit mapping |
| Model bundle tampering | low/medium | high | SHA-256, compatibility/integrity checks, read-only mount | startup verification log |
| User treats app as provider verification | high | high | UI language, limitations, official verification guidance | UX tests and screenshots |
| Insufficient Ghana sample diversity | medium | high | quotas, dataset card shortfalls, slice CIs | collection report |
| Final-test contamination | medium | critical | path guard, one notebook, receipt, team checklist | evaluation receipt |

---

# 20. Human-required actions versus Codex actions

Codex can implement the repository, tests, notebooks, schemas, acquisition scripts, preprocessing, training code, evaluation code, API, UI, Docker setup, and documentation. Certain actions require a human project member because they involve identity, consent, private accounts, or third-party access.

## 20.1 Human-required actions

1. Grant Codex access to the actual project repository and confirm the default branch/PR state.
2. Approve or obtain institutional/supervisor approval for the collection and retention plan.
3. Obtain informed consent and conduct controlled transactions.
4. Maintain the participant identity/withdrawal mapping in restricted storage.
5. Add Kaggle/Hugging Face credentials to Colab Secrets.
6. Accept source licenses/terms and request STFD access.
7. Open the committed notebooks in the project’s Colab/Drive environment and authorize Drive access when required.
8. Review private de-identification and annotation samples.
9. Approve the frozen final-evaluation checklist before the one-time run.
10. Decide whether any Ghana dataset sample has public-release permission.

## 20.2 Codex actions

1. Inspect current code and merged PRs before editing.
2. Implement one logical PR at a time, preserving correct existing architecture.
3. Add tests with every behavior change.
4. Prepare Colab notebooks that run from a clean session.
5. Never insert credentials or private data into Git.
6. Generate and import non-sensitive run metadata/reports after Colab runs.
7. Commit intentionally, push the branch, and open/update the PR.
8. Report exact commands, test outcomes, changed files, artifacts, and unresolved issues.
9. Stop a pipeline on validation/leakage/integrity failure instead of bypassing it.
10. Keep final-test access disabled until PR20 prerequisites are met.

Codex must not pretend it completed a Colab run that required credentials or private data unless the run artifacts and manifests actually exist.

---

# 21. Codex operating protocol

Use this protocol for every PR.

## 21.1 Before editing

1. Fetch the default branch and inspect repository status.
2. Read README, architecture docs, contributing rules, package manifests, and relevant prior PRs.
3. Run the current test/lint baseline and record pre-existing failures.
4. Search for existing implementations before creating new modules.
5. Check whether the logical PR has already been partly or fully implemented.
6. Update `docs/audits/pr10-pr12-gap.md` when reconciling previous work.
7. State the exact scope and non-goals in the PR description draft.

## 21.2 While editing

- Prefer small, reviewable commits grouped by concern.
- Do not mix unrelated refactors with the milestone.
- Add or update tests before declaring behavior complete.
- Keep configs versioned; do not hide decisions in notebook cells.
- Keep notebooks thin and restartable.
- Keep generated data/model files out of Git.
- Do not weaken a test merely to make CI pass.
- Do not alter frozen split manifests after modeling begins.
- Use fictitious fixtures only.
- Document migration when changing APIs or labels.

## 21.3 Before pushing

Run the applicable commands, adapting to the repository’s actual toolchain:

```bash
pre-commit run --all-files
make lint
make test
make smoke
make api-test
make frontend-test
make container-test
```

Also verify:

```bash
git status --short
git diff --check
python scripts/validate_no_large_files.py
python scripts/validate_no_pii_filenames.py
```

Inspect the complete diff and remove accidental notebook outputs, caches, credentials, data files, absolute local paths, and debug logging.

## 21.4 Push and PR

- push a named branch;
- open a PR against the current default branch;
- do not force-push shared branches unless explicitly required;
- include tests and artifacts in the description;
- link the logical milestone and any reconciliation items;
- wait for CI only in the sense of reading currently available results—do not claim future background completion;
- address review feedback in focused commits;
- do not merge unless the user/project workflow authorizes Codex to merge.

## 21.5 Required session report

At the end of each Codex session, output:

```text
PR / branch:
Commit(s):
Implemented:
Files changed:
Tests run and exact results:
Colab work prepared or executed:
Artifacts and hashes:
Data/privacy checks:
Known limitations:
Open blockers requiring human action:
Next exact step:
```

---

# 22. Master handoff prompt for Codex

Copy the block below into Codex after giving it access to the repository.

```text
You are implementing the MoMo fraud-detection project from logical PR10 through PR20.

AUTHORITATIVE SPECIFICATION
Read `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` in full before editing. If it is not yet in the repository, use the supplied blueprint file and add it under that path in the first active PR.

CURRENT STATE
The project may already be around GitHub PR12. PR1–PR10 are reported complete, but you must verify actual merged code and PRs. Do not rewrite history and do not create duplicate PRs only to match the logical numbering.

FIRST TASK
1. Inspect the repository, merged PRs 1–12, open PRs, CI, architecture, tests, and documentation.
2. Run the current test/lint baseline.
3. Create or update `docs/audits/pr10-pr12-gap.md` mapping every PR10–PR12 requirement in the blueprint to `complete`, `partial`, `absent`, or `conflicting`, with file/commit/PR evidence.
4. Preserve correct existing work.
5. Put missing logical PR10–PR12 requirements into the next active PR under a reconciliation section.

NON-NEGOTIABLE ARCHITECTURE
- Separate image tamper analysis, OCR/parser, semantic checks, structured transaction risk, and the risk-policy layer.
- Screenshot-only mode must never invent balance/history features and must return the transaction score as null.
- Canonical image labels are `unaltered` and `tampered`, not genuine/fake.
- Results are `low_risk`, `medium_risk`, `high_risk`, or `inconclusive`.
- Never say a screenshot or transaction is “verified genuine” unless an actual documented provider-side verification service confirms it.
- Use a transparent policy in PR19; do not train multimodal fusion without a properly paired labeled dataset.

TRAINING POLICY
- Full training runs in Google Colab only.
- Laptop and GitHub Actions run lint, tests, tiny fixtures, one-epoch smoke jobs, bundle loading, and inference.
- Reusable logic belongs under `src/`; notebooks are thin wrappers.
- Do not commit raw datasets, private screenshots, consent records, credentials, large checkpoints, or model binaries outside the approved registry/release mechanism.
- All full runs must create run manifests, hashes, checkpoints, and reproducible configs.

DATA POLICY
- PaySim canonical source: Kaggle `ealaxi/paysim1`; simulator source `EdgarLopezPhD/PaySim`.
- Primary PaySim benchmark excludes old/new sender/recipient balance fields and `isFlaggedFraud`.
- MoMTSim source: Mendeley DOI `10.17632/zhj366m53p.2`; treat v1 and v2 separately.
- STFD is recommended for generic screenshot-forgery pretraining subject to its access terms; FSTS is optional and subsetted.
- Final domain evaluation requires a controlled, consented, private Ghanaian MoMo screenshot dataset.
- Preserve source groups and participant/source identity groups across screenshot splits.
- Transaction split is chronological 70% train, 10% tuning, 10% calibration/threshold, 10% locked test.
- Ghana controlled-real split is 70/15/15 by source group; synthetic clean bases are 80/20/0.
- Locked tests are opened once in PR20.

EXECUTION ORDER
Follow the logical milestone order in the blueprint:
PR10 architecture policy;
PR11 governance/registry;
PR12 Colab foundation;
PR13 acquisition/validation;
PR14 transaction ETL/features/splits;
PR15 transaction models/calibration;
PR16 Ghana screenshot pipeline;
PR17 OCR benchmark/parser;
PR18 image classifier/localizer;
PR19 risk/API/UI integration;
PR20 locked evaluation/release.
If earlier logical work is already merged, audit it and proceed to the first incomplete milestone.

FOR EACH PR
- Work only on that PR’s scope and declared reconciliation items.
- Add tests and documentation.
- Run the repository’s real lint/test/smoke commands.
- Inspect the full diff for data, PII, secrets, notebook output, and large files.
- Commit intentionally, push the branch, and open/update the GitHub PR.
- In the PR description include objective, implementation, tests, Colab status, artifacts/hashes, privacy/security review, limitations, and next milestone.
- Do not claim a Colab training result unless its run manifest and artifacts exist.
- Do not access the locked test before PR20.

FAIL-CLOSED RULES
Stop and report instead of bypassing:
- dataset hash/schema mismatch;
- train/validation/test leakage;
- missing consent scope for private data;
- corrupt model/checkpoint;
- incompatible model/policy bundle;
- missing required structured inference fields;
- final-test path used by a training/tuning notebook;
- secrets or PII detected in tracked files.

END-OF-SESSION REPORT
Always report PR/branch, commits, implemented items, files changed, exact tests/results, Colab work prepared/executed, artifacts/hashes, privacy checks, limitations, human blockers, and the next exact step.

Begin now with repository inspection and the PR10–PR12 gap audit. Do not assume the repository matches the blueprint merely because filenames are similar.
```

---

# 23. Pull-request description template

```markdown
## Objective

## Logical milestone
PRXX — <name>

## Reconciliation items
- [ ] None
- [ ] Missing PR10–PR12 requirements listed below

## What changed

## Architecture/data decisions

## Files/modules

## Tests run
| Command | Result |
|---|---|
| `...` | pass/fail |

## Colab status
- [ ] Not required
- [ ] Smoke notebook run
- [ ] Full run completed
- Run ID(s):
- Run manifest hash(es):

## Artifacts
| Artifact | Location | SHA-256 | Committed? |
|---|---|---|---|

## Dataset/split versions

## Privacy and security checks
- [ ] No raw/private data in Git
- [ ] No PII in fixtures/logs
- [ ] No secrets
- [ ] License/terms checked
- [ ] Final test not accessed

## API/UI changes

## Performance/metrics
State whether these are fixture, validation, calibration, or locked-test results.

## Known limitations

## Migration/rollback

## Definition-of-done checklist

## Next milestone
```

---

# 24. Final repository inspection checklist

After PR20, inspect the complete repository and release rather than reviewing PR20 alone.

## Architecture

- [ ] evidence modes are explicit;
- [ ] unavailable signals are null;
- [ ] no OCR-to-transaction feature fabrication;
- [ ] no provider-verification claim;
- [ ] transparent risk policy;
- [ ] component/version compatibility enforced.

## Data

- [ ] canonical sources and versions documented;
- [ ] raw data absent from Git;
- [ ] PaySim forbidden features absent from primary model;
- [ ] temporal transaction splits frozen;
- [ ] screenshot source/participant grouping enforced;
- [ ] test manifests locked;
- [ ] consent/de-identification/withdrawal process audited;
- [ ] all released examples have publication permission or are synthetic.

## Modeling

- [ ] dummy and simple baselines included;
- [ ] class imbalance handled train-only;
- [ ] calibration independent of base-model fitting;
- [ ] thresholds versioned;
- [ ] three-seed stability reported;
- [ ] PR-AUC and prevalence reported;
- [ ] image localization evidence included;
- [ ] OCR field metrics included;
- [ ] no final-test tuning.

## Colab/reproducibility

- [ ] notebooks run from clean runtime;
- [ ] lock files present;
- [ ] runtime inventories and run manifests present;
- [ ] checkpoints are resumable;
- [ ] artifacts are hashed;
- [ ] plots generated from machine-readable results;
- [ ] local/CI full training remains blocked.

## API/security/privacy

- [ ] upload validation and decompression limits;
- [ ] temporary-file cleanup;
- [ ] no raw OCR text or PII in default logs;
- [ ] rate/concurrency limits;
- [ ] corrupt bundles rejected;
- [ ] service runs non-root;
- [ ] no credentials in image/repo;
- [ ] no retention by default;
- [ ] health/readiness distinguish model availability.

## UI/accessibility

- [ ] risk not color-only;
- [ ] `inconclusive` path clear;
- [ ] not-verification limitation visible;
- [ ] no “safe” or “100%” language;
- [ ] keyboard/screen-reader tests pass;
- [ ] no PIN/OTP request;
- [ ] official verification guidance present.

## Release/report

- [ ] final evaluation receipt exists;
- [ ] confidence intervals group-aware;
- [ ] separate targets are not merged into one accuracy;
- [ ] dataset/model/system/policy cards complete;
- [ ] licenses and notices included;
- [ ] failed targets disclosed;
- [ ] private data absent;
- [ ] release tag points to exact commit and artifact hashes;
- [ ] clean deployment smoke test passes.

---

# 25. Methodology statement suitable for the project report

The project should describe its methodology substantially as follows:

> The system was evaluated as a collection of distinct evidence pipelines rather than a single authenticity classifier. Structured transaction-risk models were trained on PaySim and MoMTSim using chronological partitions and inference-compatible, leakage-tested features. Screenshot manipulation detection and OCR were evaluated on a controlled, consented Ghanaian mobile-money screenshot dataset split by source group, with generic screenshot-forgery data used only for transfer learning where permitted. OCR used pretrained engines rather than a newly trained recognizer. A transparent versioned policy combined only available signals and could return an inconclusive result. Final test sets were frozen before model selection and evaluated once after all models, calibration, and thresholds were locked.

Threats to validity must include:

- synthetic transaction data and non-production prevalence;
- limited Ghanaian provider/template/device coverage;
- controlled tampering may not reproduce all adversarial techniques;
- an unaltered screenshot does not prove the transaction occurred;
- OCR and image models can fail on unseen templates, compression, or low resolution;
- no provider-side transaction verification unless separately integrated;
- group/sample sizes may make some slice estimates uncertain;
- results are research/demo evidence, not authorization for financial action.

---

# 26. Research basis and source notes

Accessed for this plan on **10 August 2026**.

## PaySim

- Canonical Kaggle dataset: `https://www.kaggle.com/datasets/ealaxi/paysim1`
- Simulator repository: `https://github.com/EdgarLopezPhD/PaySim`
- Dataset-scale references report 6,362,620 transactions and 8,213 fraud records. The calculated prevalence is:

```text
8,213 / 6,362,620 × 100 = 0.129082%
```

- The canonical data card states that fraudulent transactions are cancelled and warns against using old/new sender and recipient balances for fraud detection. This blueprint therefore excludes those four columns from the primary PaySim benchmark and also excludes the rule-derived `isFlaggedFraud` field.

## MoMTSim

- Mendeley Data version 2: `https://data.mendeley.com/datasets/zhj366m53p/2`
- Article: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12036017/`
- DOI: `10.17632/zhj366m53p.2`
- Published dataset version date listed by Mendeley: 29 October 2024.
- Article counts and calculated prevalences:

```text
v1: 175,518 / 1,720,181 × 100 = 10.203461%
v2: 2,233,118 / 4,225,958 × 100 = 52.842882%
```

These are synthetic experiment distributions, not estimated Ghanaian fraud rates.

## Screenshot forgery

- STFD: `https://huggingface.co/datasets/Zegkim/STFD`
- FSTS repository: `https://github.com/ZeqinYu/FSTS`
- FSTS dataset: `https://huggingface.co/datasets/Zegkim/FSTS`

STFD includes smartphone screenshots, mobile-payment/online-banking scenes, multiple manipulation types, and pixel-level masks. Its visible license card and usage notice should both be reviewed; this plan follows the stricter academic/no-redistribution notice. FSTS is a much larger optional non-commercial dataset and is not required for the default Colab path.

## OCR

- Tesseract: `https://github.com/tesseract-ocr/tesseract`
- EasyOCR: `https://github.com/JaidedAI/EasyOCR`
- PaddleOCR: `https://github.com/PaddlePaddle/PaddleOCR`
- docTR, optional reference: `https://github.com/mindee/doctr`

The required implementation benchmarks pretrained OCR engines and does not train a recognizer from scratch.

## Colab and Kaggle tooling

- Colab FAQ: `https://research.google.com/colaboratory/faq.html`
- Colab runtime versions: `https://research.google.com/colaboratory/runtime-version-faq.html`
- KaggleHub: `https://github.com/Kaggle/kagglehub`
- Kaggle API/CLI: `https://github.com/Kaggle/kaggle-api`

Colab documentation explains that resources are dynamic/not guaranteed and VMs are ephemeral. The plan therefore uses VM-local active data, Drive-backed archives/checkpoints, restart-safe runs, and no assumption about a particular accelerator.

## Ghana-specific context and data protection

- Cyber Security Authority MoMo guidance: `https://csa.gov.gh/mobile_money_fraud.php`
- CSA advisory portal: `https://www.csa.gov.gh/`
- Data Protection Commission privacy principles: `https://dataprotection.org.gh/privacy-policy/`
- Bank of Ghana 2024 fraud-report publication page: `https://www.bog.gov.gh/news/publication-of-banks-sdis-and-psps-2024-fraud-report/`

CSA guidance supports the user-facing advice to verify details and never disclose a PIN/OTP. DPC principles support lawful, purpose-limited, necessary, transparent, consent-aware processing and deletion/anonymization when data is no longer required. BoG/CSA materials guide local scenario design; they are not transaction-row training datasets.

## Split/calibration methodology

- scikit-learn time-series split documentation: `https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html`
- scikit-learn stratified group split documentation: `https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html`
- scikit-learn probability calibration: `https://scikit-learn.org/stable/modules/calibration.html`
- average precision: `https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html`

The project’s exact split is a custom manifest-based chronological/grouped implementation, not a claim that these library classes alone satisfy all requirements.

---

# 27. Immediate next action

1. Put this blueprint at `docs/plans/MoMo_Fraud_Detection_PR10_PR20_Colab_Blueprint.md` in the actual repository.
2. Give Codex repository access.
3. Use the master handoff prompt in Section 22.
4. Make Codex’s first output the PR10–PR12 gap audit and baseline test report.
5. Proceed with the first incomplete logical milestone; do not start full model training until PR11–PR14 data governance, registry, validation, and split gates are complete.
