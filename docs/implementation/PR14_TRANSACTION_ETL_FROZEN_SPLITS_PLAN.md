# Logical PR14 implementation plan — transaction ETL, causal features and frozen splits

Date: 2026-08-11  
Branch: `codex/p14-frozen-splits`  
Base: logical PR13 pushed head `8276a94d64803afab65d9b3113f89617ebab32e4`

## Scope

1. Define exact PaySim, MoMTSim v1 and MoMTSim v2-derivative mappings into the harmonized transaction contract while preserving source identity only as restricted provenance.
2. Build deterministic chronological partitions from sorted unique `step` values: 70% train, 10% tuning, 10% calibration and 10% locked test, with minimal positive-count boundary adjustment where feasible.
3. Generate opaque immutable row IDs, aggregate-only frozen manifests, separate sealed locked-test material and no public/raw actor identifiers.
4. Build base and causal-history features using only strictly earlier steps; same-step, current and future records cannot affect a row.
5. Keep raw actor IDs transient, exclude target/source/forbidden balance fields from the model matrix, and publish the inference feature contract.
6. Write restart-safe sharded Parquet outputs in owner-operated Colab and record runtime/memory, content hashes and safe EDA without opening locked-test labels for model decisions.
7. Add a train-only external-pretraining manifest for all 3,932 STFD pairs as one corpus group; no internal STFD validation/test partition is allowed.

## Verification

- canonical mapping/schema and forbidden-field tests;
- deterministic/minimally adjusted chronological boundary tests;
- no cross-partition step or row overlap;
- future-row insertion and same-step-order invariance;
- deterministic no-history behavior;
- preprocessing fit only on train and never refit for tuning/calibration/test;
- locked-test import guard and aggregate-report redaction;
- notebook output/policy checks, Ruff, strict mypy, full ML tests and secret/artifact scan.

## Boundaries

- Do not fit or compare a fraud model, calibrate probabilities, choose thresholds, access locked-test outputs for decisions, or claim metrics.
- Do not combine PaySim and MoMTSim into a single claimed population; preserve source-specific partitions and reporting.
- Do not commit raw/derived full datasets, raw identifiers, private paths, screenshots, masks, credentials, Parquet shards or locked-test labels.
- Do not change the public product taxonomy, API or database contracts.
- Stop and notify the project owner before logical PR15 begins the first Google Colab transaction-training run.
