# P10 Session Plan — Dataset Governance and Reproducibility

- Date: 2026-08-10
- Branch: `codex/p10-dataset-governance`
- Base SHA: `5ed38ac84bda4b3948f7893d2647096d3d70a0ed`
- Scope: P10-T001 through P10-T010; FR-ML-005 through FR-ML-007 and NFR-DATA-001.

## Plan

1. Establish a typed, manifest-driven ML data package and explicit consent, licence, retention and private-data rules.
2. Generate deterministic generic Ghana-style demonstration receipts and controlled tamper variants without protected provider branding or personal data.
3. Assign source groups to train/validation/test before derived variants, validate parent/group isolation, and prevent training-only augmentation outside the training split.
4. Validate paths, hashes, image decoding, duplicate/conflicting labels, class distribution, provenance and anonymisation; produce canonical manifest and split hashes.
5. Commit only small sanitised controlled fixtures, add a reproducible dataset report and Colab boundary instructions, run the registered ML and repository gates, and publish P10.

## Scope boundary

P10 creates governed inputs and reproducibility tooling only. It does not fit, tune, evaluate or export either the structured classifier or CNN. Per ADR-014 and the project owner's instruction, work stops after P10 publication and before the first P11/P12 training run so execution can move to Google Colab.
