# Logical PR10 Evidence and Execution Foundation Plan

- Date: 2026-08-10
- Branch: `codex/p10-evidence-execution-foundation`
- Base: `080f8d750e16c0969d8f6ce5ff11fd406523d236`
- Scope: the first implementation slice from the ordered PR10–PR12 reconciliation backlog

## In scope

1. Add versioned evidence-mode contracts for screenshot-only, transaction-only, combined and inconclusive results.
2. Preserve the implemented public risk and image-model taxonomies through explicit compatibility projections while making new canonical labels unaltered/tampered and new policy bands low/medium/high/inconclusive.
3. Enforce nullable unavailable signals and prohibit manufactured transaction values.
4. Add explicit UNIT/SMOKE/FULL execution profiles and a fail-closed full-training guard that requires Google Colab, rejects CI and requires deliberate acknowledgement.
5. Apply the guard to current training entry points, preserve immutable historical notebooks, register ML CI verification and cover the behaviour with tests. Future notebooks must pin a commit containing the guarded CLI and use the new flags.
6. Update architecture, ADR, status, traceability, changelog and session handoff evidence.

## Out of scope

- API/database/UI taxonomy migration or removal of stored-reference `VERIFIED` semantics.
- Dataset registry, downloads, participant collection, locked-test access or private data handling.
- Model fitting, threshold selection, artifact registration or any new accuracy claim.
- The PR12 run-manifest/checkpoint/resume notebook foundation, which remains the next reconciliation slice.

## Verification target

- Registered ML gate, registered backend gate, OpenAPI drift check, secret/artifact scan and diff checks.
- Targeted evidence-contract, execution-guard, CLI and CI-policy tests.
