# Codex Session Handoff

## Session identity

- Date: 2026-08-14, Africa/Lagos
- Phase: Logical PR16 private Ghana text dataset review and synthetic-clean pilot
- Base SHA: `9d77ed28fd8de4a92e91a8788ddde0d96305bcd8`
- Work branch: `codex/p16-ghana-screenshot-dataset`
- Final head/push state: reported after the session commit

## Scope completed

- Completed the full privacy/utility review of the owner-message and screenshot-OCR text corpora.
- Hardened owner de-identification for names in greetings and malformed references, transaction-reference payloads, suffix currency, IP addresses and repeated exact values.
- Expanded fail-closed secret detection to login-code formats and quarantined 26 of the 2,654 indexed messages.
- Replaced sequential OCR sensitive-field substitution with a single original-text pass, preventing short values from corrupting already inserted placeholders.
- Regenerated private corpora outside Git: 2,628 retained owner rows, 116 distinct owner texts across 90 template families, and 13 corrected screenshot-OCR texts.
- Created an independent private review artifact approving 129 de-identified real-text rows. Approval does not grant training eligibility.
- Generated a deterministic balanced synthetic-clean pilot outside Git: 30 groups, 90 wholly fictitious rows, 30 per fixed class.
- Did not freeze a split, train a model, access a locked test or claim a metric.

## Security/privacy

- Manual review found three owner-name residuals, one unrecognised login-code format and one malformed OCR placeholder row; all were corrected before second-review approval.
- Raw owner messages, exact OCR truth, screenshots, private indexes and all CSV artifacts remain outside Git under the owner-controlled private root.
- The reviewed private manifest records 129 approvals, zero exclusions, `contains_raw_values=false`, `training_eligible=false` and `splits_frozen=false`.
- The synthetic manifest records `fictitious_values_only=true`, `second_review_required=true`, `training_eligible=false` and `splits_frozen=false`.

## Safe aggregate evidence

| Artifact | Safe result |
|---|---|
| Owner source | 2,654 indexed; 2,628 retained; 26 secret-bearing rows quarantined |
| Owner de-identified corpus | 116 distinct texts; 90 template groups; 52 transaction confirmations; 64 official-service messages |
| Screenshot OCR corpus | 13 de-identified texts; 10 fraudulent, 2 genuine, 1 suspicious; zero malformed nested placeholders |
| Independent real-text review | 129 approved; 0 excluded; 0 training eligible |
| Synthetic-clean pilot | 30 groups; 90 records; balanced 30/30/30; pending second review; 0 training eligible |

Exact safe hashes are recorded in `docs/evidence/PR16_GHANA_PRIVATE_PILOT.json`.

## Verification

- Focused Ghana-pipeline suite: 94 passed.
- Full registered ML gate: PASS; format, Ruff, strict mypy, 486 tests, 90.01% branch-aware coverage, governance, locks, notebook and deterministic data checks.
- Secret/prohibited-artifact scan: PASS; 527 candidate files scanned.
- Repository `--ml` orchestration: ML section PASS, overall non-zero only because the shared doctor found Node 22.23.2/npm 10.9.8 instead of pinned Node 24.14.0/npm 10.9.0. Tesseract/PostgreSQL CLI are optional for this ML-only text change and remain available through the documented containers where required.

## Remaining gates

- Independently review all 90 synthetic-clean rows.
- Expand the controlled-real screenshot pilot from 10 to at least 30 permission-attested source groups, with stronger genuine and suspicious coverage.
- Make an explicit eligibility decision only after review/minimum gates pass.
- Freeze group-safe partitions only after eligibility; keep the owner lineage out of independent evaluation partitions.
- Stop and notify the project owner before any Google Colab training.
