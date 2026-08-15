# PR17 Parser-Ceiling Mismatch Attribution Design

**Date:** 2026-08-15  
**Status:** Approved design, pending written-spec review  
**Phase:** PR17 Stage 2, validation-only diagnostic

## Goal

Extend the validation parser-ceiling diagnostic so aggregate evidence distinguishes candidate-discovery failures from parser-selection failures without changing parser outputs. The diagnostic must inspect both transaction-labelled and broad currency candidates for amount, use boundary-aware transcript evidence for reference, and use the established name-or-wallet comparison subfield for recipient.

The report may persist only allowlisted aggregate counts and reproducibility metadata. It must never persist transcripts, field values, candidate values, record identifiers, source-group identifiers, private paths, or per-record outcomes.

This is measurement work only. It does not tune parsing, initialize OCR engines, train models, access the locked test partition, or claim an accuracy improvement.

## Constraints and non-goals

- Preserve every public `ParserResult` and `ParsedField` value, warning, confidence, semantic reason, and inconclusive decision for the same input.
- Preserve all parser-ceiling v3 fields and semantics, including flat warning compatibility and warning attribution by selected observed field.
- Operate only on the private development bundle's validation partition.
- Keep `RUN_BENCHMARK = False`; the owner-operated notebook path remains cells 1-4 and stops before all OCR adapters.
- Do not use secondary recipient truth to override the selected primary comparison subfield.
- Defer timestamp repair because only one validation record currently has timestamp truth.
- Do not add parser candidates, relax normalization, alter candidate precedence, or change matching behavior.
- Do not add a public parser-candidate API. Candidate evidence remains private and in memory.

## Chosen architecture

### Additive v4 report

`run_ocr_parser_ceiling_diagnostic` will emit `ghana-ocr-parser-ceiling-report-v4`. Version 4 retains every v3 aggregate and adds:

- `diagnostic_contract_version`;
- immutable implementation and manifest identity;
- `amount_candidate_pool_presence`;
- nested `amount_candidate_count_buckets`; and
- `mismatch_attribution_counts` for amount, recipient, reference, and deferred timestamp support.

The diagnostic remains part of the parser-ceiling report instead of becoming a companion report. This avoids a second private-bundle loading path, duplicated hashing rules, and a second owner-run workflow.

### Shared immutable amount-candidate snapshot

Extract current amount discovery into a private frozen `AmountCandidateSnapshot` containing:

```python
labelled_raw_candidates: tuple[str, ...]
labelled_valid_normalized: tuple[str, ...]
labelled_distinct_normalized: tuple[str, ...]
currency_raw_candidates: tuple[str, ...]
currency_valid_normalized: tuple[str, ...]
currency_distinct_normalized: tuple[str, ...]
active_source: Literal["labelled", "currency_fallback"]
active_valid_normalized: tuple[str, ...]
active_distinct_normalized: tuple[str, ...]
```

The broad currency pool contains every match of the existing Ghana-currency token, including matches that also occur in the labelled pool. The active pool preserves parser v1 precedence exactly: any raw labelled match activates the labelled pool; otherwise the broad currency pool is active as `currency_fallback`. A record with no raw candidates therefore still has `active_source="currency_fallback"` and empty active tuples.

`parse_amount` consumes only `active_*` and must reproduce its current output exactly. The diagnostic may inspect both pools but immediately reduces them to aggregate counters. Snapshot strings never enter a report, log, exception, or persisted intermediate file.

### Field-specific transcript evidence

Containment checks are private diagnostic predicates, not parser normalization changes.

Recipient-name evidence uses Unicode NFKC, whitespace collapse, surrounding punctuation removal, and uppercase comparison. Recipient-wallet evidence extracts phone-shaped candidates and applies the established Ghana phone normalization to each candidate. In both cases, the diagnostic uses only `FieldComparison.observed_field`; it never searches the other recipient subfield for a more favorable result.

Reference evidence is line-bounded. Each transcript line is normalized with NFKC and inspected independently. A reference-like span:

- never crosses a hard line boundary;
- normalizes to 5-50 characters from `A-Z`, `0-9`, `.`, `_`, `/`, and `-`;
- contains at least one digit; and
- is bounded by non-reference characters or line edges.

Unanchored reference-like tokens treat whitespace as a boundary. Internal whitespace may be removed only inside one candidate span captured after an existing reference anchor on the same line. This supports a spaced anchored reference without manufacturing a value by joining unrelated words or adjacent lines. Truth is considered present only when it exactly equals one normalized candidate span.

## Reproducibility identity

The v4 diagnostic API requires `implementation_commit_sha` as an explicit 40-character lowercase hexadecimal input. The pinned, output-free notebook passes its immutable `TARGET_COMMIT`; the diagnostic does not infer identity from a mutable path, notebook state, or ambient Git checkout.

The diagnostic loads and verifies the private development manifest, then propagates:

```json
{
  "implementation_commit_sha": "<40 lowercase hex>",
  "parser_version": "ghana-momo-parser-v1",
  "field_schema_version": "ghana-momo-ocr-fields-v1",
  "development_manifest_sha256": "<verified manifest self-hash>",
  "source_split_manifest_sha256": "<verified source split hash>",
  "diagnostic_contract_version": "ghana-ocr-mismatch-attribution-v1",
  "partition": "validation",
  "locked_test_accessed": false,
  "training_executed": false
}
```

Both manifest hashes must be canonical 64-character lowercase hexadecimal values. A missing, malformed, or self-inconsistent identity fails before report creation. No Drive path or run-root path is report metadata.

## Aggregate definitions

### Amount pool presence

For every truth-scored amount record, update these integer counters:

- `labelled_nonempty`: labelled distinct valid normalized set is nonempty;
- `currency_nonempty`: broad-currency distinct valid normalized set is nonempty;
- `both_nonempty`: both distinct valid sets are nonempty;
- `labelled_active`: raw labelled candidates activated labelled precedence; and
- `currency_fallback_active`: no raw labelled candidate existed, so the broad pool was active.

These are presence counters, not a mutually exclusive partition. Each must be between zero and the amount denominator. `both_nonempty` cannot exceed either nonempty counter, and `labelled_active + currency_fallback_active` must equal the amount denominator.

### Amount candidate-count buckets

For each truth-scored amount record, count distinct valid normalized candidates separately in `labelled`, `currency`, and `active`. Each pool increments exactly one bounded bucket:

- `0`
- `1`
- `2`
- `3_plus`

Each pool's four buckets must independently sum to the amount truth-scored denominator. Counting distinct valid values aligns the active bucket with the parser's ambiguity decision and does not inflate counts when one amount is repeated.

### Amount mismatch attribution

Apply this ordered, mutually exclusive classification to every truth-scored amount record:

1. `exact_selected`: current parser output equals normalized truth.
2. `no_valid_currency_candidate`: both labelled and broad currency valid sets are empty.
3. `truth_in_active_pool_not_exact`: truth is in the active valid set, but the parser result is not exact; this includes unresolved ambiguity and does not imply a winner was selected.
4. `truth_in_suppressed_currency_pool`: labelled precedence is active, truth is absent from the labelled valid set, and truth is present in the broad currency valid set.
5. `truth_absent_all_candidate_pools`: at least one valid candidate exists, but truth is in neither valid set.

The five counters must sum to the amount truth-scored denominator.

### Recipient mismatch attribution

Use the selected `FieldComparison.observed_field`. Name truth may use only `recipient`; wallet truth may use only `recipient_wallet`. An unexpected observed field fails closed.

Apply this ordered classification:

1. `exact_selected`;
2. `truth_present_parser_unavailable`;
3. `truth_absent_parser_unavailable`;
4. `selected_contains_truth`;
5. `truth_contains_selected`;
6. `truth_present_not_selected`;
7. `truth_absent_transcript`.

Availability takes precedence over selected-value containment. "Contains" is strict and excludes equality. The seven counters must sum to the recipient truth-scored denominator. Secondary truth presence remains a separate v3-compatible aggregate and cannot affect the classification.

### Reference mismatch attribution

Use the same ordered categories as recipient, but compute truth presence only from the line-bounded reference-like spans defined above:

1. `exact_selected`;
2. `truth_present_parser_unavailable`;
3. `truth_absent_parser_unavailable`;
4. `selected_contains_truth`;
5. `truth_contains_selected`;
6. `truth_present_not_selected`;
7. `truth_absent_transcript`.

Selected-value prefix/suffix relationships are evaluated after exact and availability checks. They never join transcript spans. The seven counters must sum to the reference truth-scored denominator.

### Timestamp deferral

`mismatch_attribution_counts.timestamp` has exactly one key: `deferred_insufficient_support`. It increments once for every truth-scored timestamp record and must equal the timestamp denominator. No timestamp mismatch subtype or parser repair is inferred.

## Validation, privacy, and error handling

Before writing a report, the implementation must validate:

- every new map has exactly its fixed allowlisted keys;
- every count is a non-negative integer and not a boolean;
- amount attribution totals equal the amount denominator;
- labelled, currency, and active bucket totals each equal the amount denominator;
- amount pool-presence relationships and active-source partition are valid;
- recipient, reference, and timestamp attribution totals equal their denominators;
- existing field-outcome and recipient-subtype totals still hold;
- all reproducibility identities are present, canonical, and verified;
- `raw_text_persisted`, `field_values_persisted`, `record_identifiers_persisted`, `locked_test_accessed`, and `training_executed` are all `false`; and
- the canonical report self-hash is computed after every field is present.

Errors raise `OCRBenchmarkError` and fail before output creation. No exception message may interpolate a private value, transcript fragment, candidate, record ID, source-group ID, filename, or private path. The diagnostic must not initialize or import an OCR adapter or model runtime.

## Notebook and evidence flow

The owner-operated Colab path remains:

1. install the repository package from an immutable implementation commit;
2. mount the owner's private development bundle;
3. validate the archive and manifest without printing rows;
4. run only the parser-ceiling v4 cell and print aggregate JSON.

The notebook remains output-free in Git, pins the implementation commit, passes that commit explicitly to the diagnostic, and keeps `RUN_BENCHMARK = False`. It stops before OCR adapters and cannot request the test partition.

Only an owner-returned, hash-valid aggregate v4 report may update repository evidence. If the private run is unavailable during the fast lane, documentation records `private_v4_execution_pending=true`, parser v1 remains experimental, and work proceeds to PR18 using confirmed/corrected OCR fields and explicit partial/inconclusive behavior.

## Test-first implementation strategy

### RED tests

Before production changes, add failing tests for:

- truth present in the broad currency pool but suppressed by labelled precedence;
- truth present in an ambiguous active pool;
- no valid candidate and truth absent from all pools;
- each labelled/currency/active bucket boundary;
- two reference fragments on separate lines that must not combine;
- anchored reference whitespace, punctuation, Unicode normalization, unrelated adjacent tokens, and strict prefix/suffix ordering;
- recipient name/wallet `observed_field` alignment and secondary-truth non-interference;
- missing or malformed implementation/manifest identity;
- an unallowlisted category and a denominator mismatch before file creation;
- attempted leakage of a field value, record ID, source-group ID, path, or transcript fragment; and
- timestamp categories other than `deferred_insufficient_support`.

Each RED run must fail for the intended missing behavior, not an unrelated fixture or import error.

### GREEN and regression tests

- Lock current `parse_amount` outputs before extracting the shared helper.
- Prove parity for raw value, normalized value, confidence, availability, and warnings across labelled, fallback, absent, repeated, invalid, single, ambiguous, spacing, punctuation, and Unicode cases.
- Prove every new category partition and bucket denominator.
- Prove v3-compatible aggregates retain established values for a fixed synthetic bundle.
- Prove canonical report hashing is deterministic.
- Prove invalid parser availability and recipient observed-field states fail closed.
- Prove no OCR adapter/model import or initialization occurs.
- Prove the diagnostic API cannot request the locked test partition.
- Run focused parser/benchmark tests, the full ML gate, notebook-policy tests, and the secret/prohibited-artifact scan.

## Stop/go rule after the private run

Implement at most one parser behavior change only when v4 is hash-valid and privacy-safe, all totals match, one cause is clearly dominant with non-trivial support, and the change is one bounded behavior testable without locked-test access.

Freeze parser v1 and the OCR bundle as experimental when causes are diffuse, support is too small, private-record inspection would be required, or the proposed repair broadens several behaviors. Do not repeatedly tune the same 33 validation records. PR18 must continue using user-confirmed fields and explicit `PARTIAL`/`INCONCLUSIVE` states either way.

## Documentation and delivery

After implementation and fresh verification:

- update `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, `CHANGELOG.md`, and the session handoff with measured local evidence only;
- pin the notebook to the immutable implementation commit;
- update repository evidence only after the owner supplies aggregate v4 output;
- record exact base/head SHAs, commands, results, locked-test state, and external blockers;
- commit coherently and push `codex/p17-ocr-benchmark` without rewriting history; and
- open the missing PR17 pull request before branching PR18 from the final PR17 head.

Stage 2 implementation is locally complete when its RED/GREEN and repository gates pass, but private evidence remains explicitly pending until the owner-operated v4 run returns a self-hash-verifiable aggregate report.
