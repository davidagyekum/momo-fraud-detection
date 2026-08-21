# MoMo-FDVS Academic Submission Entry Point

## Submission verdict

This repository is frozen as a **locally verified academic prototype submission candidate**. The implemented OCR-first workflow accepts a controlled screenshot, preserves immutable OCR evidence, produces a deterministic and explainable fraud-risk assessment, optionally compares confirmed transaction details with stored/imported reference records, and retains the two outcomes separately in result, history, notification and private-report surfaces.

This is not a production-release claim and it is not a claim that every aspirational requirement in the original specification is complete. At freeze time, traceability records `89 / 108` MUST and `6 / 12` SHOULD requirements complete. The exact limitations and non-claims are binding parts of the submission.

## Exact submitted revision

The generated ZIP is authoritative for its own revision. Open `FINAL_SUBMISSION_PACKAGE_MANIFEST.json` at the ZIP root to obtain:

- repository and branch;
- exact 40-character Git commit;
- commit timestamp;
- file count and total source bytes;
- SHA-256, size and path for every packaged file;
- the core submission limitations.

The ZIP is generated only after local `HEAD` equals its pushed upstream. It contains the exact committed Git tree plus the generated manifest; it never packages the mutable working tree.

## Review order

1. Read [limitations and non-claims](LIMITATIONS_AND_NON_CLAIMS.md).
2. Use the [Chapter Four evidence index](CHAPTER4_EVIDENCE_INDEX.md) to distinguish implemented evidence from plans and wireframes.
3. Inspect the machine-readable [evidence manifest](../evidence/EVIDENCE_MANIFEST.csv).
4. Review the exact phase and requirement state in [IMPLEMENTATION_STATUS.md](../../IMPLEMENTATION_STATUS.md).
5. Review measured local acceptance in [P0.3 evidence](../evidence/P0_3_TEXT_RULE_HARDENING.md) and [PR19 acceptance](../qa/PR19_ACCEPTANCE.md).
6. Follow [the local run guide](../LOCAL_RUN_GUIDE.md) for the controlled Docker demonstration.
7. Follow the [artifact policy](SUBMISSION_ARTIFACT_POLICY.md) to rebuild or independently verify the ZIP.

## Implemented demonstration boundary

The strongest accepted product journey is:

```text
fictitious account -> private controlled screenshot upload -> OCR
-> v2 deterministic text-risk preview -> screenshot-only persistence
-> separate fraud risk and verification statuses -> History
```

The same local product also contains authentication/RBAC, hostile upload validation, OCR confirmation, stored/imported reference import and comparison, deterministic image evidence, analysis history, private reports, notifications, fraud cases, investigator decisions, audit/system views and local four-service Docker orchestration. The evidence index states which parts have current acceptance evidence and which original requirements remain only partial.

## Safety and evidence integrity

- No real receipt, credential, token, private reference row, consent record, private dataset or model binary is included.
- New OCR assessments use `ghana-momo-obvious-scam-rules-v2`; the active deterministic policy is `analysis-risk-policy-demo-v3`.
- Historical v1 text-risk evidence remains immutable and is not recomputed from stored OCR text.
- A deterministic policy score is not presented as a probability.
- Verification is based only on stored/imported reference records and does not authenticate a transaction with an MNO.
- The failed P12 image-model artifact remains inactive and unavailable.

## Owner actions after the freeze

Academic submission/upload, supervisor review, and any institution-specific report formatting are owner actions. Hosted CI, hosted deployment, native-device validation, representative model/data work, performance/load evidence and restore rehearsal require new external evidence and must not be inferred from this package.
