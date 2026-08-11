# Logical PR15 transaction-model implementation plan

Date: 2026-08-11

Branch: `codex/p15-transaction-models`

Base: `f4862e32756a9b9ebde106a2eaf4993ba875b33a`

## Scope

Implement the Colab-only `transaction_core` training, independent calibration,
threshold selection and trusted bundle export required by logical PR15. Training
may read only the PR14 `train`, `tuning` and `calibration` partitions. The
`locked_test` partition remains sealed until logical PR20.

## Work plan

1. Add a versioned binary transaction-model contract and fail-closed PR14 bundle validation.
2. Add dummy, logistic, histogram-boosting, XGBoost and secondary-forest candidates with bounded, config-driven searches.
3. Rank on tuning average precision and operating constraints; fit calibration on the independent calibration partition; select versioned medium/high thresholds without final-test access.
4. Export a content-hashed trusted bundle, safe report, model card and reload-parity evidence.
5. Add a thin output-free `04_train_transaction_models.ipynb`, CLI entry points and local fixture tests that cannot enter reportable fitting.
6. Run the repository ML gate, commit and push before owner-operated full Colab execution.

## Explicit boundaries

- No PR16 screenshot collection or private-data import.
- No locked-test path, label, prediction or metric access.
- No activation, deployment or production-readiness claim.
- PaySim and MoMTSim remain synthetic research sources; calibrated scores are not real-world fraud probabilities.
- The existing public `GENUINE`/`SUSPICIOUS`/`FRAUDULENT` compatibility contract is unchanged.

## Preflight note

Python 3.12, Git, Docker and the secret/prohibited-artifact scan pass. The
repository-wide quick doctor still reports the documented unqualified Node.js
22.11.0 versus pinned 24.14.0 and missing optional Tesseract/PostgreSQL CLIs;
those tools are outside this Python/Colab-only phase.
