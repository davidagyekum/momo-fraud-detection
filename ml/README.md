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
