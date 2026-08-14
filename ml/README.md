# MoMo-FDVS machine-learning workspace

This workspace contains governed data tooling plus the structured and image model packages. Reportable fitting remains Google Colab-only; local verification exercises schemas, preprocessing, packaging orchestration and inference contracts without fitting a model.

## Execution profiles

- `unit`: schemas, deterministic tests and verification; never fits a model.
- `smoke`: bounded to at most 1,000 fictitious transaction rows, 20 synthetic images and one epoch; produces non-promotable JSON evidence only.
- `full`: reportable fitting and packaging in Google Colab only.

Both training commands now require `--profile full --acknowledge-full-training I_ACKNOWLEDGE_FULL_COLAB_TRAINING`. FULL is rejected in CI and outside a detected Colab runtime even when the acknowledgement is supplied. The acknowledgement is a safety rail, not a secret or an authorisation to use data.

## P10 commands

From the repository root with the Python 3.12 virtual environment active:

```powershell
.venv\Scripts\python.exe scripts\verify.py --ml
```

To reproduce the committed controlled dataset in another directory:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml generate --output .local/p10-controlled --seed 20260810
.venv\Scripts\python.exe -m momo_fdvs_ml validate --manifest .local/p10-controlled/manifest.csv --root .local/p10-controlled
```

`.local/` is ignored by Git. Never point the generator or validator at a directory containing private data unless its consent, licence, retention and anonymisation records have been approved.

See [data/README.md](data/README.md) for governance rules and [COLAB_TRAINING_HANDOFF.md](COLAB_TRAINING_HANDOFF.md) for the boundary before training.

## Logical PR11 governance validation

The canonical registry and portable fixtures live under the repository-root `data/` directory. This validation performs no download, scraping, private-data access or model fitting:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml validate-governance `
  --root data `
  --recorded-report data/governance_report.json
```

Source entries remain disabled until their registry permission, licence and acquisition status passes the fail-closed policy. Controlled-real screenshots additionally require a pseudonymous participant hash and explicit consent scope; committed examples must remain fictitious and participant-free.

## Logical PR12 Colab foundation

The standard clean-session notebooks are under `ml/notebooks/colab/`. They use generic `/content` paths, an immutable checkout, exact repository locks, allowlisted runtime inventory, atomic checkpoint mirroring and a complete `colab-run-manifest-v1` record.

Validate them locally without mounting Drive or running the smoke fit:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml colab-lock-report `
  --repository-root . `
  --recorded-report ml/colab_lock_report.json
.venv\Scripts\python.exe -m momo_fdvs_ml validate-notebooks `
  --root ml/notebooks/colab `
  --recorded-report ml/notebooks/colab/notebook_report.json
```

The smoke notebook uses only existing fictitious/controlled train and validation fixtures. It touches no locked test partition, downloads nothing and cannot promote its output. See [the runtime-loss recovery runbook](COLAB_RUNTIME_RECOVERY.md) before executing it in Colab.

## Logical PR13 acquisition readiness

The PR13 tooling intentionally contains no network downloader. It reports governance blockers without opening source bytes and can later register only already-authorised local/private bytes from an approved root:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml acquisition-readiness `
  --data-root data `
  --recorded-report data/acquisition_readiness_report.json
```

PaySim, MoMTSim v1, the separately versioned MoMTSim v2 derivative and STFD are registered but disabled/non-promotable; FSTS and Ghana-private retain their separate prerequisites. Registration never downloads or mutates source bytes, quarantines mismatches and emits only non-promotable content-addressed manifests plus redacted profiles. See [the acquisition runbook](../data/ACQUISITION_REGISTRATION_RUNBOOK.md).

## Logical PR14 frozen transaction features

`03_build_transaction_features.ipynb` is a thin, output-free Colab wrapper around `transaction_pipeline.py` and `transaction_etl.py`. It processes one exact registered source at a time, freezes chronological train/tuning/calibration/locked-test step ranges, derives history only from strictly earlier steps, fits neutral values/category vocabularies on train only and writes features, labels and opaque provenance into separate atomic Parquet shards. The pre-PR20 loader refuses the locked-test partition.

The local/CI fixture gate can exercise the complete path without external bytes:

```powershell
.venv\Scripts\python.exe scripts\verify_ml.py
```

Do not run `build-transaction-features` against an unregistered source or a Git path. Full outputs belong only in restricted VM/Drive storage. This PR14 command performs preprocessing, not training; logical PR15 remains a separate owner-operated Colab stop point.

## Logical PR15 transaction models

`transaction_model.py` verifies the exact PR14 report, split, preprocessor and
non-test shard hashes before fitting. Its bounded search includes dummy,
logistic, histogram-boosting, XGBoost and secondary-forest adapters; model
selection uses tuning average precision first. The chronological calibration
partition is split into independent calibrator-fit and threshold-selection
halves. Every exported bundle remains source-specific, inactive,
non-promotable and labelled `not_real_world_probability` until the one-time
PR20 final evaluation.

Full fitting is available only through the pinned, owner-operated
`04_train_transaction_models.ipynb`. The CLI guard requires detected Google
Colab FULL mode and the exact acknowledgement token:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml train-transaction-core `
  --dataset-root C:\approved-private\pr14\paysim `
  --output-dir C:\approved-private\pr15\transaction-core-paysim-pr15-v1 `
  --model-version transaction-core-paysim-pr15-v1 `
  --training-commit-sha <40-hex-pushed-commit> `
  --notebook ml/notebooks/colab/04_train_transaction_models.ipynb `
  --dependency-lock-sha256 <64-hex-lock-hash> `
  --config ml/configs/transaction_core_default.json `
  --profile full `
  --acknowledge-full-training I_ACKNOWLEDGE_FULL_COLAB_TRAINING
```

This example documents the contract; it must not be run on the laptop or in
CI. `train`, `tuning` and `calibration` are the only accepted partitions. The
PR14 loader and PR15 verifier both reject `locked_test` before PR20. PR15's
binary score does not fabricate the fixed public three-class probability
vector; ADR-032 preserves the compatibility boundary for PR19.

## Logical PR17 OCR benchmark and parser

`ocr_parser.py` implements conservative Ghana MoMo amount, recipient/wallet,
reference, timestamp, status and provider parsing. It preserves raw OCR
evidence, flags ambiguous reference characters and date order, never defaults
an unknown status to success, and returns an inconclusive result when critical
fields are missing or below the frozen confidence threshold.

`ocr_benchmark.py` provides a shared adapter result for Tesseract 5, EasyOCR
and PaddleOCR, deterministic preprocessing, CER/WER and exact normalized field
metrics, the Section 9 weighted selector, release gates, a two-stage validation
screen and integrity-checked selected-bundle replay. The private bundle builder
accepts only explicit records returned by the PR16 train/validation loader; a
test ID or unknown binding fails closed.

The v2 benchmark contract requires zero failures and 100% record coverage for
every competing configuration, plus one complete compatible finalist for each
required engine. PaddleOCR PP-OCRv6 CPU inference disables MKLDNN to avoid the
Paddle 3.3.1 oneDNN PIR incompatibility. The Colab bootstrap rejects Tesseract
4 and builds exact official Tesseract 5.5.3 source when Jammy cannot supply
major 5.

The output-free `06_benchmark_ocr.ipynb` is owner-operated in Google Colab. It
expects the content-hashed private development ZIP in
`MyDrive/momo-fraud/private-governance/ghana-private/`, benchmarks three source
groups before the full 33-record controlled-real validation pass, and writes
only private Drive reports. It does not train a recognizer. The five-record
locked test is absent from the ZIP and unavailable through every PR17 loader.
No approved tampered screenshot derivatives currently exist, so the required
tampered slice remains an explicit blocker instead of a fabricated metric.

The first completed Colab validation is retained only as failed evidence: its
field-region finalists covered eight of 33 records, PaddleOCR failed 33/33 and
Tesseract was unsupported 4.1.1. The resulting v1 experimental bundle is not a
valid winner or accuracy claim. The repaired v2 notebook still requires an
owner-operated clean-validation rerun; locked test and recognizer training
remain prohibited.

## P12 pre-training commands

Validate the frozen binary image task and exact 224×224 RGB preprocessing contract:

```powershell
$env:PYTHONPATH = "ml/src"
.venv\Scripts\python.exe -m momo_fdvs_ml validate-image `
  --manifest ml/data/controlled/manifest.csv `
  --root ml/data/controlled `
  --recorded-report ml/data/controlled/image_dataset_report.json
```

`train-image` exists for the pinned Colab notebook and is protected by the execution guard. Do not execute it locally or record a metric before an owner-approved, governed Colab run. The `.keras` output is private and must remain outside Git.
