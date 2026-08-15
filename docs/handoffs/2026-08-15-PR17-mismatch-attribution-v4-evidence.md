# Codex Session Handoff

## Session identity

- Date: `2026-08-15`
- Phase/sub-phase: Logical PR17 parser-ceiling v4 owner evidence closure
- Repository: `davidagyekum/momo-fraud-detection`
- Base branch: `main`
- Work branch: `codex/p17-ocr-benchmark`
- Starting head SHA: `f1912cb74617f0690120467271de3c53b9fcfb08`
- Immutable diagnostic runtime SHA: `bf042c3a0f6e18a2777f85d7b9d3d5131ae31d93`
- Output-free notebook commit SHA: `8afac88b18b61641e82597f41e2a305edc55c534`
- Owner-operated report SHA-256: `2405ea0e774396840a9d586e7e9c403b139215e8833296c17923ffde51a20c73`
- Pull request: [PR #15](https://github.com/davidagyekum/momo-fraud-detection/pull/15)

## Scope completed

- Requirement IDs: `NFR-ACC-001`, `NFR-PRIV-001`, `NFR-AUD-001`, logical PR17 mismatch attribution
- Goal: validate and attach the owner-operated aggregate-only v4 result, then make the parser-change stop/go decision without inspecting private values
- Actual work: independently recomputed the canonical report self-hash; verified immutable code, development-manifest and source-split identities; checked exact category and bucket allowlists; proved all outcome, attribution and candidate-bucket totals conserve their denominators; checked all five privacy/training/locked-test flags are false; attached the exact aggregate report to versioned evidence; and accepted ADR-037 to freeze parser v1 unchanged and experimental.

## Changed files

| Path | Change | Why |
|---|---|---|
| `docs/evidence/PR17_OCR_BENCHMARK_PREPARATION.json` | Added exact v4 aggregate and advanced the evidence schema to v5 | Preserve owner-operated evidence without private values or per-record rows |
| `docs/evidence/EVIDENCE_MANIFEST.csv` | Updated evidence hash and summary | Keep the evidence registry content-addressed |
| `IMPLEMENTATION_STATUS.md` | Marked private v4 complete and set the PR18 transition | Remove the obsolete owner-run instruction |
| `requirements_traceability.csv` | Recorded exact accuracy/privacy limits | Keep requirement evidence truthful |
| `DECISION_LOG.md` | Added ADR-037 | Freeze parser v1 rather than invent a private-example-driven repair |
| `CHANGELOG.md` | Added the verified v4 result | Preserve auditable project history |
| This handoff | Recorded evidence and next boundary | Enable safe continuation from final PR17 head |

## Database, API and UI

- Database/migrations: none
- API/OpenAPI/client changes: none
- Mobile/admin UI changes: none
- Breaking product-contract change: none

## OCR/ML evidence

- Report schema: `ghana-ocr-parser-ceiling-report-v4`
- Diagnostic contract: `ghana-ocr-mismatch-attribution-v1`
- Parser: `ghana-momo-parser-v1`, unchanged and experimental
- Data identities: development manifest `1ba8c58e1c29b77a46ba3cc54da7843dd84f090fdb2e731704091162d556d644`; source split `3c2bd2e3727b62f0a61f01a7eebcbe49da7ed0ac124a8f765d471533d867d941`
- Scored support: amount 32, recipient 32, reference 20, timestamp 1; record count 33; all-required support 1
- Outcomes remain amount 6 exact/23 mismatch/3 unavailable, recipient 1/23/8, reference 1/13/6 and timestamp 0/0/1.
- Amount attribution: 6 `exact_selected`, 2 `no_valid_currency_candidate`, 24 `truth_absent_all_candidate_pools`, 0 `truth_in_active_pool_not_exact`, 0 `truth_in_suppressed_currency_pool`.
- Recipient attribution: 15 `selected_contains_truth`, 8 `truth_present_not_selected`, 7 `truth_present_parser_unavailable`, 1 exact and 1 truth-absent unavailable.
- Reference attribution: 10 `selected_contains_truth`, 5 `truth_absent_parser_unavailable`, 3 `truth_absent_transcript`, 1 exact and 1 truth-present unavailable.
- Timestamp: one `deferred_insufficient_support` record.
- Candidate buckets each total 32. Labelled candidates are nonempty in 29 records, currency candidates in 30 and both in 29; raw labelled activation is 29 and currency fallback activation is 3.
- The canonical report self-hash recomputes exactly. Every mutually exclusive attribution total equals its truth-scored denominator.

## Decision and limitations

- Amount precedence/selection repair is rejected by the evidence: both amount selection-error categories are zero, while truth is absent from all valid pools in 24/32 records.
- Recipient/reference over-selection has non-trivial support, but the aggregate-only contract intentionally exposes no values or template examples from which to derive one safe termination rule.
- Inspecting private values to invent a parser rule would violate the governed evidence boundary. ADR-037 therefore freezes parser v1 unchanged and experimental.
- No accuracy improvement, deployability, provider-wide performance, training, model promotion or locked-test claim is made.
- Timestamp/all-required support remains one; no approved tampered-image validation slice exists; the selected OCR bundle remains experimental/non-promotable.

## Security and privacy

- `raw_text_persisted=false`
- `field_values_persisted=false`
- `record_identifiers_persisted=false`
- `locked_test_accessed=false`
- `training_executed=false`
- Repository evidence contains only allowlisted aggregate counts, version identifiers and hashes. No transcript, truth/candidate value, record identifier, filename, private path or per-record outcome is committed.

## Verification performed

| Command | Result | Evidence |
|---|---|---|
| Canonical Python SHA-256 and invariant validation over the owner-returned JSON | PASS | recomputed `2405ea0e…`; no invariant failure |
| `scripts/verify_ml.py` | PASS | 714 tests; 90.15% branch-aware coverage; formatting, Ruff, strict mypy, governance, lock, notebook and controlled-data gates pass |
| `scripts/check_secrets.py` | PASS | 561 candidate files scanned |
| `scripts/verify.py --ml` | PARTIAL / expected host-doctor failure | nested secret and ML gates pass; wrapper exits 1 because Node 22.23.2/npm 10.9.8 differ from pins, host Tesseract is absent and optional PostgreSQL CLI is absent |
| CSV/JSON parsing, evidence-file hash and `git diff --check` | PASS | evidence schema v5 parses; manifest hash is `4893cb96…`; traceability CSV parses; diff has no whitespace error |

## Known blockers

| ID | Impact | Safe fallback | Next action |
|---|---|---|---|
| PR17-TAMPERED-SLICE | Robustness selection remains unavailable | Keep OCR bundle experimental | Govern image derivatives before robustness evaluation |
| PR17-PARSER-EXPERIMENTAL | Exact-field and required-field gates fail | Preserve partial/inconclusive behavior | Carry explicit unavailability into PR18/PR19 |
| HOST-DOCTOR | Repository wrapper may remain non-zero locally | Use passing registered ML/secret gates and record exact mismatch | Install pinned host tools separately; do not alter PR17 pins |
| GITHUB-ACTIONS-BILLING | Hosted jobs cannot start | Preserve local evidence and open PR | Repository owner resolves account billing lock |

## Git evidence

```text
starting head: f1912cb74617f0690120467271de3c53b9fcfb08
runtime: bf042c3a0f6e18a2777f85d7b9d3d5131ae31d93
notebook: 8afac88b18b61641e82597f41e2a305edc55c534
report: 2405ea0e774396840a9d586e7e9c403b139215e8833296c17923ffde51a20c73
evidence payload commit: 5aa69528e5d23c67f82ae98363d9e237b4edfc91
publication correction: the commit containing this line cannot self-embed its own SHA; the exact final branch head is authoritative in PR #15 metadata and its current_pr_head=<40-hex SHA> body marker
```

## Next exact task

Complete PR17 evidence publication on PR #15. Then start logical PR18 analysis-product design from the final PR17 head—not from `main`. Preserve parser v1 and the selected OCR bundle as experimental, consume OCR fields only through explicit partial/inconclusive states and do not access any locked-test partition before PR20.
