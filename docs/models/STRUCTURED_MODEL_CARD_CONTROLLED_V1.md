# Model Card — structured-rf-controlled-v1

## Status and intended use

- Model type: structured Random Forest baseline
- Status after training: READY; never auto-activated
- Intended use: controlled MoMo-FDVS prototype evidence before human review
- Prohibited claims: provider-wide accuracy, production readiness, fraud proof
  or autonomous consequential decisions
- Dataset scope: controlled/synthetic only; no real customer or provider data

## Reproducibility

- Training commit: `a914f065070558b5b601e6f49cf1691ff7bf9d42`
- Random seed: `20260811`
- Feature schema: `structured-evidence-features-v1`
- Feature schema SHA-256: `5ce66b8b860b24c95f2a6933bb396128c1f083fe088171654404d4d066295699`
- P10 manifest SHA-256: `51d12132904f461fb4bec6a5d0eda9cff5dd94961a48129b7dd75359b38ead1f`
- P10 split SHA-256: `08008637eb661634eb93fee4d4ac74d82da598b2b0ff28f188f9641e47e933f9`
- Structured dataset SHA-256: `30a74b15fe34ef229edd7b28d25b334add7d79e2a73d06d9baae3ba560dda07f`
- Artifact SHA-256: `cc2137f85ac522bd5a4d58592779b2667a6b1ae2755015a8c1bd7977fa5c190b`

## Held-out controlled results

- Test source groups: `1`
- Test samples: `3`
- Macro F1: `1.0`
- Balanced accuracy: `1.0`
- Suspicious threshold (validation only): `0.05`
- Fraudulent threshold (validation only): `0.55`
- Confusion matrix labels: `['GENUINE', 'SUSPICIOUS', 'FRAUDULENT']`
- Confusion matrix: `[[1, 0, 0], [0, 1, 0], [0, 0, 1]]`

## Limitations

The held-out partition contains one controlled source group and one row per class.
Strong results demonstrate deterministic pipeline behaviour only. They do not
estimate generalisation to real receipts, provider layouts, user populations or
naturally occurring fraud. The probability vector is uncalibrated because the
validation partition is too small to fit a defensible calibrator. Human review and
authorised provider confirmation remain necessary for consequential cases.
