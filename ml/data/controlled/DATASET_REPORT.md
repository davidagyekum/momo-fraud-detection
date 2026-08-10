# P10 Controlled Dataset Report

- Manifest schema: `receipt-dataset-manifest-v1`
- Generator: `generic-ghana-receipt-generator-v1`
- Generation seed: `20260810`
- Canonical manifest SHA-256: `51d12132904f461fb4bec6a5d0eda9cff5dd94961a48129b7dd75359b38ead1f`
- Source-group split SHA-256: `08008637eb661634eb93fee4d4ac74d82da598b2b0ff28f188f9641e47e933f9`
- Samples: `12` across `6` source groups
- Split samples: `{"test": 2, "train": 8, "validation": 2}`
- Labels: `{"fraudulent": 6, "genuine": 6}`
- Source types: `{"controlled_tamper": 6, "synthetic": 6}`
- Validation: `0 errors`; no source group crosses splits
- Training executed: `false`
- Model metrics: `not available`

## Scope and limitations

- All committed images are generic controlled demonstrations.
- They do not represent provider-wide layouts, users or real fraud prevalence.
- Controlled edits do not cover all real manipulation techniques.
- No model was fit or evaluated in P10; no performance claim is available.
