# Logical PR13 — Dataset acquisition, registration and validation plan

## Base and scope

- Branch: `codex/p13-dataset-acquisition-validation`
- Base SHA: `000bc65983d242cac8a8806a0cb116373bbcb4c2`
- Blueprint milestone: logical PR13
- Product/API/database taxonomy: unchanged

## Planned work

1. Add strict acquisition-request, content-addressed manifest, validation-result and safe-profile contracts.
2. Implement fail-closed source eligibility, local/private registration, archive identity, quarantine and dataset-specific validation services.
3. Cover PaySim, MoMTSim v1/v2, STFD, optional FSTS and Ghana-private through explicit adapters without accepting unknown mirrors or inferred versions.
4. Generate redacted inventory/profile reports and output-free Colab acquisition/validation notebooks.
5. Add no-network fake-archive tests for schema/count/hash drift, duplicates, invalid images/masks, deterministic subsets, idempotence and protected-data export refusal.
6. Register the checks in the ML gate and update governance/status/traceability/handoff documentation.

## Stop boundary

- Do not download, scrape, upload or register external/private dataset bytes in this implementation session.
- Keep every registry entry disabled and `not_acquired` while licence, permission, access or consent evidence is unverified.
- Do not access locked tests, build post-performance splits, train models or redistribute data.
- Stop after pushing the tested no-network foundation and report the exact source-specific evidence needed before an owner-operated Colab acquisition run.
