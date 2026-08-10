# P11 Session Plan — Structured Fraud Classifier

- Date: 2026-08-10
- Branch: `codex/p11-structured-model`
- Base SHA: `593ebd91bdc2041c2574e72cd21ab661020853c2`
- Scope: P11-T001 through P11-T011; FR-ML-001, FR-ML-002, FR-ML-004 through FR-ML-007 and NFR-ACC-002.
- Training surface: Google Colab only, per ADR-014 and the project owner's instruction.
- Dataset scope: governed controlled/synthetic P10 data because no authorised real dataset is available.

## Plan

1. Define and hash an exact structured feature schema with forbidden-field and missingness guards.
2. Build a group-safe controlled structured dataset and a scikit-learn `ColumnTransformer`/`Pipeline` with training-only preprocessing and deterministic Random Forest baseline.
3. Implement held-out evaluation, validation-only threshold selection, calibration diagnostics, model-card/report generation and trusted artifact packaging.
4. Implement hash-verified inference plus administrator-only, confirmation-gated registration/activation/rollback with audit evidence.
5. Publish the code/notebook, execute the actual training in Google Colab at the exact code SHA, import only safe metrics/checksums (not the model binary), run all gates and publish P11.

## Scope boundary

The controlled-only evaluation may demonstrate pipeline correctness but cannot support provider-wide or production accuracy claims. P11 does not implement CNN training, final risk aggregation, user risk results or investigator model-registry UI. A model remains inactive until an authorised administrator explicitly activates a hash-verified artifact that passed readiness checks.
