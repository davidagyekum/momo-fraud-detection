# PR17 Parser-Ceiling Mismatch Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a validation-only parser-ceiling v4 report that attributes amount, recipient, and reference failures using aggregate-only evidence while preserving parser v1 outputs and the sealed-test boundary.

**Architecture:** Extract amount discovery into a private immutable snapshot shared by `parse_amount` and the diagnostic, while the parser continues to consume only its existing active pool. Extend the existing parser-ceiling report additively with dual-pool amount counts, field-specific text attribution, immutable run identity, strict allowlists, and deterministic validation before atomic output.

**Tech Stack:** Python 3.12, frozen dataclasses, regular expressions, `Decimal`, JSON/SHA-256, pytest, Ruff, mypy, repository ML verification, output-free Colab notebook policy.

## Global Constraints

- Work only on `codex/p17-ocr-benchmark`, based on approved design commit `e7f329ce4443e763ad7871225073d79a1404f3af` or a documented descendant.
- Preserve every public parser output, confidence, warning, semantic reason, and inconclusive decision for identical input.
- The diagnostic may read only the development bundle's `validation` partition; the five locked-test records remain physically unavailable.
- Do not initialize OCR engines, import model runtimes, train, promote, or alter parser behavior.
- Persist no transcript, truth value, observed value, candidate value, record ID, source-group ID, filename, or private path.
- Keep `RUN_BENCHMARK = False`; the owner instruction is: first four code cells, ending with parser-ceiling; stop before adapter code cell.
- Use `ghana-ocr-parser-ceiling-report-v4` and `ghana-ocr-mismatch-attribution-v1` exactly.
- Preserve all parser-ceiling v3 aggregate meanings, including flat warning counts across every parse.
- Every category map uses fixed keys; each partition and bucket total must equal its truth-scored denominator.
- Timestamp attribution contains only `deferred_insufficient_support`.
- Use RED -> GREEN for every production behavior and record the intended RED output in the implementation handoff.
- Use `apply_patch` for repository edits; do not rewrite unrelated user changes.
- Do not claim private v4 evidence until the owner-operated aggregate run returns and its self-hash verifies.

---

## File Structure

- Modify `ml/src/momo_fdvs_ml/ocr_parser.py`: own the private amount-candidate snapshot and keep `parse_amount` behavior unchanged.
- Modify `ml/src/momo_fdvs_ml/ocr_benchmark.py`: own v4 attribution categories, reference spans, report identity, validation, aggregation, and output.
- Modify `ml/tests/test_ocr_parser.py`: characterize parser parity and test dual-pool snapshot discovery.
- Modify `ml/tests/test_ocr_benchmark.py`: test v4 identity, attribution, denominators, privacy, and invalid boundaries.
- Modify `ml/notebooks/colab/06_benchmark_ocr.ipynb`: pin the final code commit and pass it explicitly to the v4 diagnostic.
- Modify `ml/notebooks/colab/notebook_report.json`: record the canonical output-free notebook hash.
- Modify `IMPLEMENTATION_STATUS.md`, `requirements_traceability.csv`, and `CHANGELOG.md`: record local implementation state without inventing private results.
- Create `docs/handoffs/2026-08-15-PR17-mismatch-attribution-v4-implementation.md`: record RED/GREEN evidence, exact SHAs, privacy state, and owner-run command boundary.

### Task 1: Preserve Parser Outputs and Expose Both Amount Pools

**Files:**
- Modify: `ml/tests/test_ocr_parser.py`
- Modify: `ml/src/momo_fdvs_ml/ocr_parser.py`

**Interfaces:**
- Consumes: existing `_AMOUNT_TOKEN`, `_normalize_amount()`, `_clean()`, `_confidence()`, and `parse_amount()` behavior.
- Produces: frozen `AmountCandidateSnapshot` and private `_amount_candidate_snapshot(text: str) -> AmountCandidateSnapshot` for Task 2.

- [ ] **Step 1: Add a passing parser-output characterization table**

Add a parametrized test that captures full `ParsedField` output for labelled, fallback, missing, repeated, ambiguous, invalid, spacing, punctuation, and Unicode-marker cases:

```python
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Amount GHS 10.00", ("10.00", "10.00", True, ())),
        ("Balance GHS 10.00", ("10.00", "10.00", True, ())),
        ("Amount GHS 10.00 and total GHS 20.00", ("10.00 | 20.00", None, False, ("AMOUNT_AMBIGUOUS",))),
        ("Amount GHS 10.00 and fee GHS 10.00", ("10.00", "10.00", True, ())),
        ("Amount: GHS 1,001.2", ("1,001.2", "1001.20", True, ())),
        ("Amount GHS 10.123", (None, None, False, ("AMOUNT_NOT_FOUND",))),
        ("No currency candidate", (None, None, False, ("AMOUNT_NOT_FOUND",))),
        ("Paid GH\u00a2 5.00", ("5.00", "5.00", True, ())),
    ],
)
def test_amount_parser_output_parity(
    text: str,
    expected: tuple[str | None, str | None, bool, tuple[str, ...]],
) -> None:
    field = parse_amount(text)
    assert (field.raw, field.normalized, field.available, field.warnings) == expected
```

- [ ] **Step 2: Run the characterization test before refactoring**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py::test_amount_parser_output_parity -q --no-cov
```

Expected: PASS. If an expected tuple differs from current behavior, correct the test to the measured current output before continuing; do not alter production code.

- [ ] **Step 3: Add the failing dual-pool snapshot test**

Import `momo_fdvs_ml.ocr_parser as ocr_parser` and add:

```python
def test_amount_candidate_snapshot_keeps_suppressed_currency_pool_private() -> None:
    snapshot = ocr_parser._amount_candidate_snapshot(
        "Amount GHS 20.00\nTransfer value GHS 10.00"
    )
    assert snapshot.labelled_distinct_normalized == ("20.00",)
    assert snapshot.currency_distinct_normalized == ("20.00", "10.00")
    assert snapshot.active_source == "labelled"
    assert snapshot.active_distinct_normalized == ("20.00",)
```

- [ ] **Step 4: Run the snapshot test and verify the intended RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py::test_amount_candidate_snapshot_keeps_suppressed_currency_pool_private -q --no-cov
```

Expected: FAIL because `_amount_candidate_snapshot` does not exist.

- [ ] **Step 5: Implement the immutable snapshot and refactor `parse_amount`**

Add the exact private structure and helper near `_normalize_amount`:

```python
@dataclass(frozen=True)
class AmountCandidateSnapshot:
    labelled_raw_candidates: tuple[str, ...]
    labelled_valid_normalized: tuple[str, ...]
    labelled_distinct_normalized: tuple[str, ...]
    currency_raw_candidates: tuple[str, ...]
    currency_valid_normalized: tuple[str, ...]
    currency_distinct_normalized: tuple[str, ...]
    active_source: Literal["labelled", "currency_fallback"]
    active_valid_normalized: tuple[str, ...]
    active_distinct_normalized: tuple[str, ...]


def _ordered_distinct(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _amount_candidate_snapshot(text: str) -> AmountCandidateSnapshot:
    labelled_patterns = (
        rf"(?:amount|total|paid|payment|cash\s*in|cash\s*out|transferred|sent|received)"
        rf"[^\n]{{0,36}}?{_AMOUNT_TOKEN}",
        rf"{_AMOUNT_TOKEN}[^\n]{{0,24}}?(?:paid|sent|received|transferred)",
    )
    labelled_raw = tuple(
        _clean(match.group(1))
        for pattern in labelled_patterns
        for match in re.finditer(pattern, text, re.IGNORECASE)
    )
    currency_raw = tuple(
        _clean(match.group(1)) for match in re.finditer(_AMOUNT_TOKEN, text, re.IGNORECASE)
    )
    labelled_valid = tuple(
        normalized
        for raw in labelled_raw
        if (normalized := _normalize_amount(raw)) is not None
    )
    currency_valid = tuple(
        normalized
        for raw in currency_raw
        if (normalized := _normalize_amount(raw)) is not None
    )
    active_source: Literal["labelled", "currency_fallback"] = (
        "labelled" if labelled_raw else "currency_fallback"
    )
    active_valid = labelled_valid if labelled_raw else currency_valid
    return AmountCandidateSnapshot(
        labelled_raw,
        labelled_valid,
        _ordered_distinct(labelled_valid),
        currency_raw,
        currency_valid,
        _ordered_distinct(currency_valid),
        active_source,
        active_valid,
        _ordered_distinct(active_valid),
    )
```

Import `Literal` from `typing`. Replace `parse_amount`'s local discovery with `snapshot = _amount_candidate_snapshot(text)`, reconstruct the existing raw/value pairs from the active pool, and keep the exact confidence bases (`0.92` labelled, `0.72` fallback), warning codes, raw joining order, and ambiguity rule.

- [ ] **Step 6: Run parser tests and verify GREEN plus parity**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py -q --no-cov
```

Expected: all parser tests PASS, including the characterization and snapshot tests.

- [ ] **Step 7: Commit the parser-internal refactor**

```powershell
git add ml/src/momo_fdvs_ml/ocr_parser.py ml/tests/test_ocr_parser.py
git commit -m "refactor(ocr): expose private amount candidate pools"
```

### Task 2: Add v4 Identity and Amount Attribution

**Files:**
- Modify: `ml/tests/test_ocr_benchmark.py`
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`

**Interfaces:**
- Consumes: `AmountCandidateSnapshot`, `_amount_candidate_snapshot()`, `FieldComparison`, verified development-manifest self-hash, and `source_split_manifest_sha256`.
- Produces: v4 report identity, `amount_candidate_pool_presence`, nested `amount_candidate_count_buckets`, and amount `mismatch_attribution_counts`.

- [ ] **Step 1: Add common immutable implementation identity to test calls**

At module scope add:

```python
IMPLEMENTATION_COMMIT_SHA = "1" * 40
```

Pass `implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA` to every existing `run_ocr_parser_ceiling_diagnostic` test call. Update existing schema assertions from v3 to v4 only after the RED assertions below are installed.

- [ ] **Step 2: Add failing report-identity and dual-pool amount assertions**

Extend the aggregate diagnostic test to assert:

```python
assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v4"
assert report["diagnostic_contract_version"] == "ghana-ocr-mismatch-attribution-v1"
assert report["implementation_commit_sha"] == IMPLEMENTATION_COMMIT_SHA
assert report["development_manifest_sha256"] == json.loads(
    manifest_path.read_text(encoding="utf-8")
)["manifest_sha256"]
assert report["source_split_manifest_sha256"] == json.loads(
    manifest_path.read_text(encoding="utf-8")
)["source_split_manifest_sha256"]
```

Add a synthetic truth record where `Amount GHS 20.00` is labelled and `GHS 10.00` appears elsewhere while truth is `10.00`, then assert:

```python
assert report["mismatch_attribution_counts"]["amount"] == {
    "exact_selected": 0,
    "no_valid_currency_candidate": 0,
    "truth_in_active_pool_not_exact": 0,
    "truth_in_suppressed_currency_pool": 1,
    "truth_absent_all_candidate_pools": 0,
}
assert report["amount_candidate_count_buckets"] == {
    "labelled": {"0": 0, "1": 1, "2": 0, "3_plus": 0},
    "currency": {"0": 0, "1": 0, "2": 1, "3_plus": 0},
    "active": {"0": 0, "1": 1, "2": 0, "3_plus": 0},
}
```

- [ ] **Step 3: Add failing identity-boundary tests**

Parametrize malformed commit SHAs (`"f" * 39`, `"F" * 40`, and a non-hex string) and mutate private manifest copies to remove/malformed `source_split_manifest_sha256`. Recompute the manifest self-hash only for the missing-source-hash cases so the test reaches the intended identity check. Assert `OCRBenchmarkError` and `not output.exists()` without matching private values.

- [ ] **Step 4: Run the new tests and verify intended RED failures**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "parser_ceiling and (identity or suppressed or aggregate_redacted)" -q --no-cov
```

Expected: FAIL because the function rejects the new keyword or the v4 keys are absent.

- [ ] **Step 5: Implement constants, identity validation, and amount helpers**

In `ocr_benchmark.py`:

```python
OCR_PARSER_CEILING_REPORT_VERSION: Final = "ghana-ocr-parser-ceiling-report-v4"
OCR_MISMATCH_ATTRIBUTION_VERSION: Final = "ghana-ocr-mismatch-attribution-v1"
_COMMIT_SHA: Final = re.compile(r"[0-9a-f]{40}")
_SHA256: Final = re.compile(r"[0-9a-f]{64}")
_COUNT_BUCKETS: Final = ("0", "1", "2", "3_plus")
_AMOUNT_ATTRIBUTION_CATEGORIES: Final = (
    "exact_selected",
    "no_valid_currency_candidate",
    "truth_in_active_pool_not_exact",
    "truth_in_suppressed_currency_pool",
    "truth_absent_all_candidate_pools",
)
```

Add private helpers with these signatures:

```python
def _candidate_count_bucket(values: Sequence[str]) -> str:
    count = len(values)
    if count == 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    return "3_plus"

def _classify_amount_attribution(
    comparison: FieldComparison,
    snapshot: AmountCandidateSnapshot,
) -> str:
    if comparison.matched:
        return "exact_selected"
    truth = comparison.expected_normalized
    labelled = set(snapshot.labelled_distinct_normalized)
    currency = set(snapshot.currency_distinct_normalized)
    active = set(snapshot.active_distinct_normalized)
    if not labelled and not currency:
        return "no_valid_currency_candidate"
    if truth in active:
        return "truth_in_active_pool_not_exact"
    if snapshot.active_source == "labelled" and truth not in labelled and truth in currency:
        return "truth_in_suppressed_currency_pool"
    return "truth_absent_all_candidate_pools"
```

Update the diagnostic signature:

```python
def run_ocr_parser_ceiling_diagnostic(
    *,
    development_manifest_path: Path,
    output_path: Path,
    repository_root: Path,
    implementation_commit_sha: str,
    now: datetime | None = None,
) -> Path:
```

Validate the commit before private loading. Load the manifest, require its already-verified self-hash and canonical `source_split_manifest_sha256`, and propagate both hashes. Import `AmountCandidateSnapshot` and `_amount_candidate_snapshot` from `ocr_parser` without importing any adapter.

- [ ] **Step 6: Aggregate amount presence, buckets, and classification**

Initialize fixed zero-valued maps. For each non-`None` amount comparison, derive one snapshot from the transcript, increment valid-set presence counts, active-source count, three independent buckets, and exactly one amount attribution category. Keep candidate strings local to the loop.

- [ ] **Step 7: Run the focused amount/identity tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "parser_ceiling" -q --no-cov
```

Expected: amount/identity tests PASS; recipient/reference/timestamp v4 attribution may still be absent until Task 3.

- [ ] **Step 8: Commit the amount and identity slice**

```powershell
git add ml/src/momo_fdvs_ml/ocr_benchmark.py ml/tests/test_ocr_benchmark.py
git commit -m "feat(ocr): attribute amount candidate failures"
```

### Task 3: Add Recipient, Reference, and Timestamp Attribution

**Files:**
- Modify: `ml/tests/test_ocr_benchmark.py`
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`

**Interfaces:**
- Consumes: `FieldComparison.expected_normalized`, `.observed_normalized`, `.observed_field`, `.matched`, and `.available`.
- Produces: `_reference_like_spans()`, `_classify_text_attribution()`, and exhaustive recipient/reference/timestamp maps.

- [ ] **Step 1: Add failing reference-span regression tests**

Parametrize private helper expectations:

```python
@pytest.mark.parametrize(
    ("transcript", "expected"),
    [
        ("Reference: ABC 12345", ("ABC12345",)),
        ("Reference: (ABC12345).", ("ABC12345",)),
        ("Reference: AＢC12345", ("ABC12345",)),
        ("ABC\n12345", ("12345",)),
        ("unrelated ABC 12345 words", ("12345",)),
    ],
)
def test_reference_like_spans_preserve_boundaries(
    transcript: str, expected: tuple[str, ...]
) -> None:
    assert ocr_benchmark._reference_like_spans(transcript) == expected
```

Also add a report test with truth `ABC12345` and transcript fragments `ABC\n12345`; assert reference attribution is `truth_absent_parser_unavailable`, not truth-present.

- [ ] **Step 2: Add failing recipient observed-field tests**

Extend the wallet-primary monkeypatch test so the transcript contains the truth wallet while the selected wallet is different, and assert `truth_present_not_selected == 1`. Add a name-primary test with secondary wallet truth and prove only the name comparison determines attribution.

- [ ] **Step 3: Add failing containment-priority and timestamp tests**

Use synthetic `FieldComparison` instances or monkeypatched parser results to cover, in order, exact, unavailable-present, unavailable-absent, selected-contains-truth, truth-contains-selected, present-not-selected, and absent. Assert:

```python
assert report["mismatch_attribution_counts"]["timestamp"] == {
    "deferred_insufficient_support": report["field_scored_record_count"]["timestamp"]
}
```

- [ ] **Step 4: Run the new text-attribution tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "reference_like or observed_field or containment or timestamp" -q --no-cov
```

Expected: FAIL because the helpers and category maps do not exist.

- [ ] **Step 5: Implement line-bounded reference spans**

Add a compiled anchor pattern that reuses the current reference anchor vocabulary and a boundary-bounded unanchored token pattern. Normalize each line independently with NFKC. Remove whitespace only inside a same-line anchored capture; never join lines or arbitrary adjacent unanchored tokens. Filter spans to the exact allowed alphabet, length 5-50, and at least one digit. Return ordered distinct normalized spans.

Use this concrete shape, with the anchored extractor generating candidate prefixes within its one-line capture so `Reference: ABC 12345 status text` can yield `ABC12345` without treating arbitrary unanchored words as one reference:

```python
_REFERENCE_ALLOWED: Final = re.compile(r"[A-Z0-9._/-]{5,50}")
_REFERENCE_UNANCHORED: Final = re.compile(
    r"(?<![A-Z0-9._/-])([A-Z0-9._/-]{5,50})(?![A-Z0-9._/-])",
    re.IGNORECASE,
)
_REFERENCE_LINE_ANCHOR: Final = re.compile(
    r"(?:transaction\s*(?:id|reference|ref)|reference|ref\b|receipt\s*id)"
    r"\s*(?:is\s*)?(?:[:#=-]\s*|\s+)"
    r"([A-Z0-9._/-][A-Z0-9._/\-\s]{4,100})",
    re.IGNORECASE,
)


def _valid_reference_span(value: str) -> str | None:
    normalized = re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).upper()
    if _REFERENCE_ALLOWED.fullmatch(normalized) is None or not any(
        character.isdigit() for character in normalized
    ):
        return None
    return normalized


def _reference_like_spans(text: str) -> tuple[str, ...]:
    spans: list[str] = []
    for raw_line in text.splitlines():
        line = unicodedata.normalize("NFKC", raw_line)
        anchored = _REFERENCE_LINE_ANCHOR.search(line)
        if anchored is not None:
            # Apply the existing anchor vocabulary to this line only. Split
            # the post-anchor capture into tokens and test bounded prefixes;
            # never combine content from another line.
            tokens = anchored.group(1).split()
            for end in range(1, len(tokens) + 1):
                if (value := _valid_reference_span(" ".join(tokens[:end]))) is not None:
                    spans.append(value)
        else:
            # Without an anchor, whitespace remains a boundary and tokens
            # are evaluated independently.
            for match in _REFERENCE_UNANCHORED.finditer(line):
                if (value := _valid_reference_span(match.group(1))) is not None:
                    spans.append(value)
    return tuple(dict.fromkeys(spans))
```

Add `import unicodedata` at the top of `ocr_benchmark.py` for this normalization.

- [ ] **Step 6: Implement field-specific truth presence and ordered classification**

Add:

```python
_TEXT_ATTRIBUTION_CATEGORIES: Final = (
    "exact_selected",
    "truth_present_parser_unavailable",
    "truth_absent_parser_unavailable",
    "selected_contains_truth",
    "truth_contains_selected",
    "truth_present_not_selected",
    "truth_absent_transcript",
)

def _classify_text_attribution(
    comparison: FieldComparison,
    *,
    truth_present: bool,
) -> str:
    if comparison.matched:
        return "exact_selected"
    if not comparison.available:
        return (
            "truth_present_parser_unavailable"
            if truth_present
            else "truth_absent_parser_unavailable"
        )
    observed = comparison.observed_normalized
    if observed is None:
        raise OCRBenchmarkError("parser comparison availability state is invalid")
    truth = comparison.expected_normalized
    if truth != observed and truth in observed:
        return "selected_contains_truth"
    if truth != observed and observed in truth:
        return "truth_contains_selected"
    return "truth_present_not_selected" if truth_present else "truth_absent_transcript"
```

Implement availability before containment. Recipient name truth uses normalized text containment; wallet truth uses normalized extracted phone candidates; reference truth uses exact membership in `_reference_like_spans`. Reject any recipient observed field outside the subtype's required field.

- [ ] **Step 7: Aggregate recipient/reference and deferred timestamp categories**

Initialize all fixed keys at zero. Increment one category only for each scored comparison. Increment timestamp `deferred_insufficient_support` once per scored timestamp. Preserve the existing v3 warning and truth-subtype loops unchanged.

- [ ] **Step 8: Run all focused parser and benchmark tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py ml/tests/test_ocr_benchmark.py -q --no-cov
```

Expected: all focused tests PASS.

- [ ] **Step 9: Commit field attribution**

```powershell
git add ml/src/momo_fdvs_ml/ocr_benchmark.py ml/tests/test_ocr_benchmark.py
git commit -m "feat(ocr): add bounded field mismatch attribution"
```

### Task 4: Fail Closed on Schema, Totals, and Privacy

**Files:**
- Modify: `ml/tests/test_ocr_benchmark.py`
- Modify: `ml/src/momo_fdvs_ml/ocr_benchmark.py`

**Interfaces:**
- Consumes: complete pre-hash v4 report and `field_scored_record_count`.
- Produces: `_validate_parser_ceiling_report(report: Mapping[str, object]) -> None`, called before self-hash and `_write_json`.

- [ ] **Step 1: Add failing exact-allowlist tests**

Build a valid synthetic report through the diagnostic, remove `report_sha256`, then mutate copies with:

```python
report["debug_transcript"] = "PRIVATE TRANSCRIPT FRAGMENT"
report["mismatch_attribution_counts"]["amount"]["PRIVATE_AMOUNT_10_00"] = 1
report["amount_candidate_count_buckets"]["active"]["4"] = 1
```

Call `_validate_parser_ceiling_report` and assert a stable generic `OCRBenchmarkError` for each mutation. Assert the exception string contains none of the injected strings.

- [ ] **Step 2: Add failing denominator and count-type tests**

Mutate a valid report so one partition sum is wrong, one presence count exceeds the amount denominator, one `both_nonempty` exceeds `labelled_nonempty`, one count is `True`, and one count is negative. Assert rejection before output creation.

- [ ] **Step 3: Add failing metadata/privacy-flag tests**

Remove each identity field, change each five privacy/training/lock flags to `True`, and add forbidden top-level fields named `record_id`, `source_group_id`, `truth_value`, `candidate_values`, `private_path`, and `full_transcript`. Assert generic fail-closed errors without echoing values.

- [ ] **Step 4: Run validation tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_benchmark.py -k "allowlist or denominator or privacy or count_type or metadata" -q --no-cov
```

Expected: FAIL because the report validator is absent.

- [ ] **Step 5: Implement exact nested report validation**

Define fixed top-level and nested key sets. Validate types without coercion (`isinstance(value, int) and not isinstance(value, bool)`), non-negativity, identities, privacy flags, existing outcome totals, subtype totals, active-source partition, presence relationships, all bucket totals, all attribution totals, and timestamp's single key.

Use one structural helper so the same exact-key/count rules apply everywhere:

```python
def _require_count_map(
    value: object,
    *,
    keys: Sequence[str],
    label: str,
) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise OCRBenchmarkError(f"OCR parser ceiling {label} keys are invalid")
    counts: dict[str, int] = {}
    for key in keys:
        count = value[key]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise OCRBenchmarkError(f"OCR parser ceiling {label} count is invalid")
        counts[key] = count
    return counts


def _require_partition_total(
    counts: Mapping[str, int],
    *,
    denominator: int,
    label: str,
) -> None:
    if sum(counts.values()) != denominator:
        raise OCRBenchmarkError(f"OCR parser ceiling {label} total is invalid")
```

Define `_PARSER_CEILING_REPORT_KEYS` as the exact pre-hash set of every retained v3 field plus the v4 identity and attribution fields. `_validate_parser_ceiling_report` first compares `set(report)` to that constant, then calls these helpers for each nested map. It obtains each denominator only from a validated `field_scored_record_count` map and never includes invalid values in errors.

Error messages identify only the safe structural field name, never the invalid value. Call the validator immediately before computing `report_sha256`; write only after validation succeeds.

- [ ] **Step 6: Add deterministic self-hash and no-adapter regression assertions**

Assert two identical synthetic runs with a fixed aware clock have the same canonical content and valid self-hashes. Monkeypatch adapter constructors or adapter-import boundaries to raise if touched, then prove the parser-ceiling diagnostic succeeds without them.

- [ ] **Step 7: Run the entire focused suite and static checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py ml/tests/test_ocr_benchmark.py -q --no-cov
.\.venv\Scripts\python.exe -m ruff check ml/src/momo_fdvs_ml/ocr_parser.py ml/src/momo_fdvs_ml/ocr_benchmark.py ml/tests/test_ocr_parser.py ml/tests/test_ocr_benchmark.py
.\.venv\Scripts\python.exe -m mypy ml/src/momo_fdvs_ml/ocr_parser.py ml/src/momo_fdvs_ml/ocr_benchmark.py
```

Expected: all commands exit zero.

- [ ] **Step 8: Commit the validated v4 code contract**

```powershell
git add ml/src/momo_fdvs_ml/ocr_benchmark.py ml/tests/test_ocr_benchmark.py
git commit -m "fix(ocr): fail closed on parser diagnostic output"
git rev-parse HEAD
```

Record this exact SHA as the immutable implementation commit used in Task 5.

### Task 5: Pin the Owner Notebook to the Immutable v4 Code Commit

**Files:**
- Modify: `ml/notebooks/colab/06_benchmark_ocr.ipynb`
- Modify: `ml/notebooks/colab/notebook_report.json`
- Test: `ml/tests/test_notebooks.py`

**Interfaces:**
- Consumes: exact Task 4 implementation commit from `git rev-parse HEAD`.
- Produces: output-free owner cell that passes `implementation_commit_sha=TARGET_COMMIT` and remains blocked before OCR adapters.

- [ ] **Step 1: Capture and verify the implementation SHA**

Run:

```powershell
$implementationSha = git rev-parse HEAD
if ($implementationSha -notmatch '^[0-9a-f]{40}$') { throw 'Implementation SHA is invalid' }
$implementationSha
```

- [ ] **Step 2: Add notebook-policy assertions before changing the notebook**

In `test_notebooks.py`, load `06_benchmark_ocr.ipynb` and assert its combined source includes `implementation_commit_sha=TARGET_COMMIT`, `RUN_BENCHMARK = False`, and the parser-ceiling call before any `TesseractAdapter`, `EasyOCRAdapter`, or `PaddleOCRAdapter` construction. Assert all code-cell outputs are empty and execution counts are `None`.

```python
def test_pr17_parser_ceiling_notebook_is_pinned_and_stops_before_adapters() -> None:
    notebook = json.loads((NOTEBOOK_ROOT / "06_benchmark_ocr.ipynb").read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell.get("cell_type") == "code"]
    source = "\n".join(
        "".join(cell.get("source", [])) if isinstance(cell.get("source"), list)
        else str(cell.get("source", ""))
        for cell in code_cells
    )
    assert "implementation_commit_sha=TARGET_COMMIT" in source
    assert "RUN_BENCHMARK = False" in source
    diagnostic_position = source.index("run_ocr_parser_ceiling_diagnostic(")
    adapter_position = min(
        source.index(name)
        for name in ("TesseractAdapter", "EasyOCRAdapter", "PaddleOCRAdapter")
    )
    assert diagnostic_position < adapter_position
    assert all(cell.get("execution_count") is None for cell in code_cells)
    assert all(cell.get("outputs") == [] for cell in code_cells)
```

- [ ] **Step 3: Run the new notebook test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_notebooks.py -k "parser_ceiling" -q --no-cov
```

Expected: FAIL because the diagnostic call does not yet pass `TARGET_COMMIT`.

- [ ] **Step 4: Patch notebook cells 1 and 4**

Use `apply_patch` to replace the old `TARGET_COMMIT` with `$implementationSha`'s literal value and change the call to:

```python
parser_ceiling_path = run_ocr_parser_ceiling_diagnostic(
    development_manifest_path=development_manifest,
    output_path=run_root / "ocr-parser-ceiling-report.json",
    repository_root=repo,
    implementation_commit_sha=TARGET_COMMIT,
)
```

Add assertions for schema v4, diagnostic contract version, implementation SHA, both manifest hashes, category denominator totals, self-hash, and all five false privacy/training/lock flags. Leave `RUN_BENCHMARK = False` and all outputs empty.

- [ ] **Step 5: Update the canonical notebook hash**

Run `Get-FileHash ml/notebooks/colab/06_benchmark_ocr.ipynb -Algorithm SHA256`, lowercase the result, and patch only the `06_benchmark_ocr.ipynb` value in `notebook_report.json`.

- [ ] **Step 6: Verify notebook policy and tests**

Run:

```powershell
$env:PYTHONPATH = "ml/src"
.\.venv\Scripts\python.exe -m momo_fdvs_ml validate-notebooks --root ml/notebooks/colab --recorded-report ml/notebooks/colab/notebook_report.json
.\.venv\Scripts\python.exe -m pytest ml/tests/test_notebooks.py -q --no-cov
```

Expected: policy reports zero issues and notebook tests PASS.

- [ ] **Step 7: Commit the output-free owner runner**

```powershell
git add ml/notebooks/colab/06_benchmark_ocr.ipynb ml/notebooks/colab/notebook_report.json ml/tests/test_notebooks.py
git commit -m "docs(colab): pin parser attribution diagnostic"
```

### Task 6: Run Full Gates and Record the Pending Private-Run Handoff

**Files:**
- Modify: `IMPLEMENTATION_STATUS.md`
- Modify: `requirements_traceability.csv`
- Modify: `CHANGELOG.md`
- Create: `docs/handoffs/2026-08-15-PR17-mismatch-attribution-v4-implementation.md`

**Interfaces:**
- Consumes: fresh focused/full verification output and exact code/notebook SHAs.
- Produces: truthful public handoff with `private_v4_execution_pending=true` until owner evidence exists.

- [ ] **Step 1: Run the required fresh verification gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ml/tests/test_ocr_parser.py ml/tests/test_ocr_benchmark.py -q --no-cov
.\.venv\Scripts\python.exe scripts/verify_ml.py
.\.venv\Scripts\python.exe scripts/check_secrets.py
```

Record exact exit codes, test counts, coverage, and scan candidate count. Do not reuse older counts.

- [ ] **Step 2: Run repository wrapper and record environmental blockers exactly**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/verify.py --ml
```

If the ML section passes but host doctor still reports the known Node/npm or host-Tesseract mismatch, record that exact nonzero boundary; do not call the wrapper green and do not alter dependency pins in this PR17 task.

- [ ] **Step 3: Inspect changes and prohibited content**

Run:

```powershell
git diff --check
git status --short
git diff -- ml/src/momo_fdvs_ml/ocr_parser.py ml/src/momo_fdvs_ml/ocr_benchmark.py ml/tests/test_ocr_parser.py ml/tests/test_ocr_benchmark.py ml/notebooks/colab/06_benchmark_ocr.ipynb
```

Confirm no private values, paths, outputs, record rows, model artifacts, or unrelated changes are present.

- [ ] **Step 4: Update status, traceability, changelog, and handoff**

Use measured results only. State:

```text
schema_version=ghana-ocr-parser-ceiling-report-v4
diagnostic_contract_version=ghana-ocr-mismatch-attribution-v1
parser_behavior_changed=false
locked_test_accessed=false
training_executed=false
private_v4_execution_pending=true
```

The handoff must name the implementation commit, notebook commit, exact gates, `RUN_BENCHMARK=False`, and this owner instruction: first four code cells, ending with parser-ceiling; stop before adapter code cell. Do not update aggregate evidence with synthetic test results.

- [ ] **Step 5: Commit documentation and push PR17**

```powershell
git add IMPLEMENTATION_STATUS.md requirements_traceability.csv CHANGELOG.md docs/handoffs/2026-08-15-PR17-mismatch-attribution-v4-implementation.md
git commit -m "docs(handoff): record parser attribution implementation"
git push origin codex/p17-ocr-benchmark
```

- [ ] **Step 6: Verify the pushed head**

Run:

```powershell
$localHead = git rev-parse HEAD
$remoteHead = git rev-parse origin/codex/p17-ocr-benchmark
if ($localHead -ne $remoteHead) { throw 'Remote PR17 head does not match local head' }
git status --short --branch
```

Expected: identical SHAs and a clean tracking branch.

- [ ] **Step 7: Open the missing PR17 pull request**

First run `gh pr list --head codex/p17-ocr-benchmark --base main`. If no PR exists, create one with a body that states the exact head, the logical PR10-PR17 ancestry, local gates, experimental OCR status, private v4 pending state, locked-test false, and GitHub Actions billing blocker:

```powershell
gh pr create --base main --head codex/p17-ocr-benchmark --title "feat(ocr): complete governed OCR benchmark and parser diagnostics" --body-file docs/handoffs/2026-08-15-PR17-mismatch-attribution-v4-implementation.md
```

Do not merge, force-push, or branch PR18 from `main`. PR18 must start from this final PR17 head.

## Owner-Operated Evidence Checkpoint

After Task 6, the owner instruction is: first four code cells, ending with parser-ceiling; stop before adapter code cell. The owner returns the aggregate v4 JSON. Verify the canonical self-hash, identity fields, exact category allowlists, denominator totals, and false privacy/training/locked-test flags before updating repository evidence.

If one cause is dominant with non-trivial support, design at most one bounded parser behavior change through a new test-first cycle. Otherwise freeze parser v1 as experimental and immediately create the separate PR18 analysis-product design from the final PR17 head.
