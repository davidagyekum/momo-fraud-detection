# MoMo-FDVS

MoMo-FDVS is an evidence-based prototype for analysing Mobile Money receipt images. It combines OCR, deterministic image checks, versioned machine-learning outputs, configurable rules, and comparison with stored or imported reference transactions.

The currently implemented public contract produces two independent outcomes:

- fraud risk: `GENUINE`, `SUSPICIOUS`, or `FRAUDULENT`;
- verification status: `VERIFIED`, `UNVERIFIED`, or `MISMATCH`.

The prototype does not claim a live connection to MTN, Telecel, AT Money, or another Mobile Network Operator. Verification is based on authorised stored/imported reference records.

Logical PR10 reconciliation adds an additive evidence contract with explicit `screenshot_only`, `transaction_only`, `combined` and `inconclusive` modes. New image evidence uses `unaltered`/`tampered`, and new policy results use low/medium/high/inconclusive risk bands. Existing public/database enums remain in force until a separately migrated API version. See [the evidence and execution contract](docs/architecture/PR10_EVIDENCE_EXECUTION_CONTRACT.md).

Logical PR11 adds a fail-closed dataset registry, portable transaction/image/OCR/edit/split/run schemas, fictitious fixtures and executable consent/withdrawal governance. Every registered source remains disabled and unacquired until its permission, licence and registration evidence is approved. See [the data-access rules](DATA_ACCESS.md) and [governed data workspace](data/README.md).

## Repository status

The repository is frozen as a **locally verified academic prototype submission candidate**. The final accepted OCR-first journey persists deterministic screenshot risk without fabricated transaction fields, while optional stored/imported-record comparison remains separate. New OCR text assessments use `ghana-momo-obvious-scam-rules-v2` under `analysis-risk-policy-demo-v3`.

Start with the [academic submission entry point](docs/submission/README.md), [evidence index](docs/submission/CHAPTER4_EVIDENCE_INDEX.md), [limitations and non-claims](docs/submission/LIMITATIONS_AND_NON_CLAIMS.md), and [exact implementation status](IMPLEMENTATION_STATUS.md).

This is not a hosted or production deployment. Native-device acceptance, live MNO verification, an accepted active image model and several original product gates remain explicitly unavailable or incomplete.

## Implemented architecture

- Mobile: Expo + React Native + TypeScript
- Staff portal: React + TypeScript + Vite
- API and worker: Python 3.12 + Flask
- Persistence: PostgreSQL + SQLAlchemy + Alembic/Flask-Migrate
- OCR and image processing: Tesseract + OpenCV + Pillow
- Machine learning: TensorFlow/Keras and scikit-learn
- Local orchestration: Docker Compose

The detailed source of truth starts with [00_SOURCE_OF_TRUTH_AND_SCOPE.md](00_SOURCE_OF_TRUTH_AND_SCOPE.md). Repository-wide implementation rules are in [AGENTS.md](AGENTS.md).

## Verification commands

Use the Python 3.12 launcher on Windows when `python` resolves to an older runtime:

```powershell
py -3.12 scripts/doctor.py
py -3.12 scripts/check_secrets.py
py -3.12 scripts/verify.py --quick
py -3.12 scripts/verify.py --backend
py -3.12 scripts/verify.py --ml
```

On macOS/Linux with Python 3.12 selected:

```bash
python scripts/doctor.py
python scripts/check_secrets.py
python scripts/verify.py --quick
python scripts/verify.py --backend
```

The registered full gates require the repository's supported runtimes and Docker services. See [the local run guide](docs/LOCAL_RUN_GUIDE.md), [current recorded counts](IMPLEMENTATION_STATUS.md), and [P0.3 acceptance evidence](docs/evidence/P0_3_TEXT_RULE_HARDENING.md). A host toolchain mismatch or unavailable Docker dependency is reported as a failure; it is never converted into a skipped success.

The deterministic final ZIP is built and verified with `scripts/build_submission_package.py`; see the [submission artifact policy](docs/submission/SUBMISSION_ARTIFACT_POLICY.md).

## Local bootstrap

```powershell
py -3.12 scripts/bootstrap.py
```

This creates ignored local directories for private storage, temporary files, and model artifacts. Add `--create-env` to copy `.env.example` to an ignored `.env` when one does not already exist. It never overwrites an existing `.env`.

## Data and security

Never commit real receipts, reference data containing personal information, datasets, completed consent records, credentials, `.env`, access tokens, model secrets, or large model artifacts. See [SECURITY.md](SECURITY.md) for reporting and handling rules.
