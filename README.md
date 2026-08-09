# MoMo-FDVS

MoMo-FDVS is an evidence-based prototype for analysing Mobile Money receipt images. It combines OCR, deterministic image checks, versioned machine-learning outputs, configurable rules, and comparison with stored or imported reference transactions.

The system produces two independent outcomes:

- fraud risk: `GENUINE`, `SUSPICIOUS`, or `FRAUDULENT`;
- verification status: `VERIFIED`, `UNVERIFIED`, or `MISMATCH`.

The prototype does not claim a live connection to MTN, Telecel, AT Money, or another Mobile Network Operator. Verification is based on authorised stored/imported reference records.

## Repository status

The repository is in P00, the preflight and execution-foundation phase. Product applications and services intentionally begin in P01. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [the P00 gap analysis](docs/implementation/P00_GAP_ANALYSIS.md) for the exact state.

## Planned architecture

- Mobile: Expo + React Native + TypeScript
- Staff portal: React + TypeScript + Vite
- API and worker: Python 3.12 + Flask
- Persistence: PostgreSQL + SQLAlchemy + Alembic/Flask-Migrate
- OCR and image processing: Tesseract + OpenCV + Pillow
- Machine learning: TensorFlow/Keras and scikit-learn
- Local orchestration: Docker Compose

The detailed source of truth starts with [00_SOURCE_OF_TRUTH_AND_SCOPE.md](00_SOURCE_OF_TRUTH_AND_SCOPE.md). Repository-wide implementation rules are in [AGENTS.md](AGENTS.md).

## P00 commands

Use the Python 3.12 launcher on Windows when `python` resolves to an older runtime:

```powershell
py -3.12 scripts/doctor.py
py -3.12 scripts/check_secrets.py
py -3.12 scripts/verify.py --quick
```

On macOS/Linux with Python 3.12 selected:

```bash
python scripts/doctor.py
python scripts/check_secrets.py
python scripts/verify.py --quick
```

`python scripts/verify.py --all` will intentionally fail until later application phases exist. It reports missing sections instead of representing them as successful or silently skipped.

## Local bootstrap

```powershell
py -3.12 scripts/bootstrap.py
```

This creates ignored local directories for private storage, temporary files, and model artifacts. Add `--create-env` to copy `.env.example` to an ignored `.env` when one does not already exist. It never overwrites an existing `.env`.

## Data and security

Never commit real receipts, reference data containing personal information, datasets, credentials, `.env`, access tokens, model secrets, or large model artifacts. See [SECURITY.md](SECURITY.md) for reporting and handling rules.

