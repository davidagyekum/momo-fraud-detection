from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pathspec
import pytest

import momo_fdvs_ml.governance as governance
from momo_fdvs_ml.governance import (
    FIXTURE_TO_SCHEMA,
    GovernanceError,
    assert_participant_not_withdrawn,
    governance_report,
    load_and_validate_registry,
    load_withdrawal_ledger,
    validate_fixture_payload,
    validate_schema_documents,
    validate_taxonomy,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPOSITORY_ROOT / "data"


def _ignore_spec() -> pathspec.PathSpec:
    return pathspec.PathSpec.from_lines(
        "gitignore",
        (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines(),
    )


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _copied_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(DATA_ROOT, root / "data")
    return root / "data"


def test_complete_governance_report_is_fail_closed_and_non_executing() -> None:
    report = governance_report(DATA_ROOT)

    assert report["registry_entry_count"] == 6
    assert report["enabled_dataset_count"] == 0
    assert report["schema_count"] == 6
    assert report["fixture_count"] == 6
    assert report["withdrawal_fixture_entry_count"] == 1
    assert report["taxonomy_total_percent"] == 100
    assert report["acquisition_executed"] is False
    assert report["training_executed"] is False


def test_registry_has_exact_sources_cards_schemas_and_explicit_restrictions() -> None:
    registry = load_and_validate_registry(DATA_ROOT)
    entries = registry["datasets"]
    assert isinstance(entries, list)
    assert all(isinstance(entry, dict) and entry["enabled"] is False for entry in entries)
    states = {
        entry["dataset_id"]: entry["acquisition_status"]
        for entry in entries
        if isinstance(entry, dict)
    }
    assert states["paysim"] == "registered"
    assert states["momtsim-v1"] == "registered"
    assert states["momtsim-v2"] == "registered"
    assert all(
        states[dataset_id] == "not_acquired" for dataset_id in ("stfd", "fsts", "ghana-private")
    )
    assert all(
        isinstance(entry, dict) and entry["redistribution"] in {"blocked", "internal_only"}
        for entry in entries
    )


def test_registry_rejects_unapproved_enablement(tmp_path: Path) -> None:
    registry = _json(DATA_ROOT / "registry.yaml")
    entries = registry["datasets"]
    assert isinstance(entries, list) and isinstance(entries[0], dict)
    blocked_entry = next(
        entry for entry in entries if isinstance(entry, dict) and entry["dataset_id"] == "stfd"
    )
    entries.remove(blocked_entry)
    entries.insert(0, blocked_entry)
    blocked_entry["enabled"] = True
    temporary_root = tmp_path / "data"
    temporary_root.mkdir()
    (temporary_root / "registry.yaml").write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(GovernanceError, match="cannot be enabled"):
        load_and_validate_registry(temporary_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(registry_version="old"), "unsupported"),
        (lambda value: value.update(datasets=[]), "must contain entries"),
        (lambda value: value.update(datasets=["bad"]), "must be objects"),
    ],
)
def test_registry_rejects_invalid_top_level_documents(
    tmp_path: Path, mutation: object, message: str
) -> None:
    root = _copied_data_root(tmp_path)
    registry = _json(root / "registry.yaml")
    assert callable(mutation)
    mutation(registry)
    (root / "registry.yaml").write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        load_and_validate_registry(root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("display_name", "", "non-empty string"),
        ("required", "yes", "flags must be booleans"),
        ("acquisition_status", "downloaded", "invalid acquisition status"),
        ("allowed_purposes", [], "allowed purposes"),
        ("prohibited_uses", [1], "prohibited uses"),
    ],
)
def test_registry_rejects_invalid_entry_fields(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    root = _copied_data_root(tmp_path)
    registry = _json(root / "registry.yaml")
    datasets = registry["datasets"]
    assert isinstance(datasets, list) and isinstance(datasets[0], dict)
    datasets[0][field] = value
    (root / "registry.yaml").write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        load_and_validate_registry(root)


def test_registry_rejects_duplicate_missing_and_bad_special_entries(tmp_path: Path) -> None:
    for alteration, message in (
        ("duplicate", "IDs must be unique"),
        ("missing", "exact canonical"),
        ("fsts", "optional and disabled"),
        ("ghana", "require consent"),
    ):
        root = _copied_data_root(tmp_path / alteration)
        registry = _json(root / "registry.yaml")
        datasets = registry["datasets"]
        assert isinstance(datasets, list)
        if alteration == "duplicate":
            assert isinstance(datasets[1], dict) and isinstance(datasets[0], dict)
            datasets[1]["dataset_id"] = datasets[0]["dataset_id"]
        elif alteration == "missing":
            datasets.pop()
        elif alteration == "fsts":
            entry = next(item for item in datasets if item["dataset_id"] == "fsts")
            entry["required"] = True
        else:
            entry = next(item for item in datasets if item["dataset_id"] == "ghana-private")
            entry["redistribution"] = "blocked"
        (root / "registry.yaml").write_text(json.dumps(registry), encoding="utf-8")
        with pytest.raises(GovernanceError, match=message):
            load_and_validate_registry(root)


def test_registry_rejects_missing_paths_and_card_sections(tmp_path: Path) -> None:
    root = _copied_data_root(tmp_path)
    registry = _json(root / "registry.yaml")
    datasets = registry["datasets"]
    assert isinstance(datasets, list) and isinstance(datasets[0], dict)
    datasets[0]["card_path"] = "data/cards/missing.md"
    (root / "registry.yaml").write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(GovernanceError, match="path does not exist"):
        load_and_validate_registry(root)

    root = _copied_data_root(tmp_path / "card")
    (root / "cards" / "paysim.md").write_text("# PaySim\n", encoding="utf-8")
    with pytest.raises(GovernanceError, match="card is missing"):
        load_and_validate_registry(root)


def test_portable_schemas_align_with_executable_required_fields() -> None:
    hashes = validate_schema_documents(DATA_ROOT)
    assert set(hashes) == set(FIXTURE_TO_SCHEMA.values())
    assert all(len(value) == 64 for value in hashes.values())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("$schema", "draft-07", "JSON Schema 2020-12"),
        ("type", "array", "strict object"),
        ("additionalProperties", True, "strict object"),
        ("required", [], "required fields drifted"),
        ("properties", {}, "properties drifted"),
    ],
)
def test_schema_documents_reject_contract_drift(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    root = _copied_data_root(tmp_path)
    path = root / "schemas" / "transaction.schema.json"
    schema = _json(path)
    schema[field] = value
    path.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        validate_schema_documents(root)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "must contain an object"),
        ({"bad": float("nan")}, "unable to load governed document"),
    ],
)
def test_governed_document_loader_rejects_invalid_content(
    tmp_path: Path, payload: object, message: str
) -> None:
    path = tmp_path / "document.json"
    if isinstance(payload, list):
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text("not json", encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        governance._load_json(path)


def test_all_fictitious_fixtures_validate() -> None:
    for filename, schema_name in FIXTURE_TO_SCHEMA.items():
        validate_fixture_payload(schema_name, _json(DATA_ROOT / "fixtures" / filename))


def test_private_screenshot_requires_consent_scope_and_canonical_label() -> None:
    screenshot = _json(DATA_ROOT / "fixtures" / "screenshot.fixture.json")
    private = copy.deepcopy(screenshot)
    private["provenance"] = "controlled_real"
    private["participant_id_hash"] = "7" * 64
    private["consent_scope"] = "internal_only"
    validate_fixture_payload("screenshot", private)

    missing_scope = copy.deepcopy(private)
    del missing_scope["consent_scope"]
    with pytest.raises(GovernanceError, match="missing consent_scope"):
        validate_fixture_payload("screenshot", missing_scope)

    invalid_label = copy.deepcopy(private)
    invalid_label["image_class"] = "genuine"
    with pytest.raises(GovernanceError, match="unaltered or tampered"):
        validate_fixture_payload("screenshot", invalid_label)


def test_nullable_balances_remain_null_in_portable_transaction_fixture() -> None:
    transaction = _json(DATA_ROOT / "fixtures" / "transaction.fixture.json")
    validate_fixture_payload("transaction", transaction)
    assert transaction["old_balance_initiator"] is None
    assert transaction["new_balance_recipient"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("step", True, "step must be an integer"),
        ("amount", -1, "outside the allowed range"),
        ("initiator_id", "REAL_PERSON", "pseudonymous"),
        ("old_balance_initiator", "10", "must be numeric"),
        ("label_is_fraud", True, "must be 0 or 1"),
        ("dataset_source", "unknown", "source is not registered"),
        ("transaction_type", "", "non-empty string"),
    ],
)
def test_transaction_fixture_rejects_unsafe_values(field: str, value: object, message: str) -> None:
    payload = _json(DATA_ROOT / "fixtures" / "transaction.fixture.json")
    payload[field] = value
    with pytest.raises(GovernanceError, match=message):
        validate_fixture_payload("transaction", payload)


def test_transaction_fixture_rejects_unknown_fields() -> None:
    payload = _json(DATA_ROOT / "fixtures" / "transaction.fixture.json")
    payload["unexpected"] = "value"
    with pytest.raises(GovernanceError, match="unknown unexpected"):
        validate_fixture_payload("transaction", payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("image_id", "REAL_001", "FIXTURE IDs"),
        ("consent_scope", "none", "consent_scope is required"),
        ("capture_channel", "email", "capture_channel is invalid"),
        ("os_family", "windows", "os_family is invalid"),
        ("theme", "blue", "theme is invalid"),
        ("split", "holdout", "split is invalid"),
        ("tamper_target", "phone", "target/method is invalid"),
        ("benign_transform", "rotate", "benign transform is invalid"),
        ("sha256", "bad", "lowercase SHA-256"),
        ("resolution", [0, 100], "two positive integers"),
    ],
)
def test_screenshot_fixture_rejects_invalid_values(field: str, value: object, message: str) -> None:
    payload = _json(DATA_ROOT / "fixtures" / "screenshot.fixture.json")
    payload[field] = value
    with pytest.raises(GovernanceError, match=message):
        validate_fixture_payload("screenshot", payload)


def test_screenshot_fixture_enforces_tamper_and_provenance_invariants() -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "screenshot.fixture.json")
    cases: list[tuple[dict[str, object], str]] = []

    unaltered = copy.deepcopy(fixture)
    unaltered["tamper_target"] = "amount"
    unaltered["tamper_method"] = "replacement"
    cases.append((unaltered, "cannot declare tamper"))

    tampered = copy.deepcopy(fixture)
    tampered["image_class"] = "tampered"
    cases.append((tampered, "require a target and method"))

    synthetic_linked = copy.deepcopy(fixture)
    synthetic_linked["participant_id_hash"] = "7" * 64
    cases.append((synthetic_linked, "cannot carry participant"))

    external_linked = copy.deepcopy(fixture)
    external_linked["provenance"] = "stfd"
    cases.append((external_linked, "require licence scope"))

    for payload, message in cases:
        with pytest.raises(GovernanceError, match=message):
            validate_fixture_payload("screenshot", payload)


def test_split_groups_must_be_disjoint() -> None:
    split = _json(DATA_ROOT / "fixtures" / "split-manifest.fixture.json")
    groups = split["groups"]
    assert isinstance(groups, dict)
    groups["test"] = list(groups["train"])  # type: ignore[arg-type]
    with pytest.raises(GovernanceError, match="unique and disjoint"):
        validate_fixture_payload("split-manifest", split)


def test_ocr_truth_rejects_bad_field_shapes_bbox_and_realistic_text() -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "ocr-truth.fixture.json")
    cases: list[tuple[dict[str, object], str]] = []
    bad_field = copy.deepcopy(fixture)
    bad_field["amount"] = "10"
    cases.append((bad_field, "must be an object"))
    bad_bbox = copy.deepcopy(fixture)
    assert isinstance(bad_bbox["amount"], dict)
    bad_bbox["amount"]["bbox"] = [0, -1, 2, 3]
    cases.append((bad_bbox, "bbox is invalid"))
    realistic = copy.deepcopy(fixture)
    realistic["full_transcript"] = "Payment completed"
    cases.append((realistic, "demonstrably fictitious"))
    for payload, message in cases:
        with pytest.raises(GovernanceError, match=message):
            validate_fixture_payload("ocr-truth", payload)


def test_edit_manifest_rejects_missing_or_malformed_operations() -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "edit-manifest.fixture.json")
    cases: list[tuple[dict[str, object], str]] = []
    no_operations = copy.deepcopy(fixture)
    no_operations["operations"] = []
    cases.append((no_operations, "requires operations"))
    non_object = copy.deepcopy(fixture)
    non_object["operations"] = ["bad"]
    cases.append((non_object, "must be objects"))
    no_target = copy.deepcopy(fixture)
    assert isinstance(no_target["operations"], list)
    assert isinstance(no_target["operations"][0], dict)
    no_target["operations"][0]["target"] = "none"
    cases.append((no_target, "real target and method"))
    bad_bbox = copy.deepcopy(fixture)
    assert isinstance(bad_bbox["operations"], list)
    assert isinstance(bad_bbox["operations"][0], dict)
    bad_bbox["operations"][0]["bbox"] = [1, 2]
    cases.append((bad_bbox, "bbox is invalid"))
    bad_seed = copy.deepcopy(fixture)
    bad_seed["seed"] = True
    cases.append((bad_seed, "seed must be an integer"))
    for payload, message in cases:
        with pytest.raises(GovernanceError, match=message):
            validate_fixture_payload("edit-manifest", payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "v0", "versioned and frozen"),
        ("frozen", False, "versioned and frozen"),
        ("manifest_sha256", "bad", "lowercase SHA-256"),
        ("groups", [], "must be an object"),
    ],
)
def test_split_manifest_rejects_invalid_metadata(field: str, value: object, message: str) -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "split-manifest.fixture.json")
    fixture[field] = value
    with pytest.raises(GovernanceError, match=message):
        validate_fixture_payload("split-manifest", fixture)


def test_split_manifest_rejects_missing_or_empty_groups() -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "split-manifest.fixture.json")
    groups = fixture["groups"]
    assert isinstance(groups, dict)
    del groups["test"]
    with pytest.raises(GovernanceError, match="missing test"):
        validate_fixture_payload("split-manifest", fixture)

    fixture = _json(DATA_ROOT / "fixtures" / "split-manifest.fixture.json")
    groups = fixture["groups"]
    assert isinstance(groups, dict)
    groups["train"] = []
    with pytest.raises(GovernanceError, match="non-empty string list"):
        validate_fixture_payload("split-manifest", fixture)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "v0", "unsupported run manifest"),
        ("profile", "production", "profile is invalid"),
        ("status", "ok", "status is invalid"),
        ("repo_dirty", True, "clean repository"),
        ("git_commit", "bad", "40 lowercase"),
        ("python_version", "3.11.9", "Python 3.12"),
        ("seed", True, "seed must be an integer"),
        ("started_at", "yesterday", "ISO-8601"),
        ("checkpoint_sha256s", ["a" * 64, "a" * 64], "unique list"),
    ],
)
def test_run_manifest_rejects_non_reproducible_metadata(
    field: str, value: object, message: str
) -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "run-manifest.fixture.json")
    fixture[field] = value
    with pytest.raises(GovernanceError, match=message):
        validate_fixture_payload("run-manifest", fixture)


def test_run_manifest_rejects_invalid_hash_and_unknown_schema() -> None:
    fixture = _json(DATA_ROOT / "fixtures" / "run-manifest.fixture.json")
    fixture["dependency_lock_sha256"] = "BAD"
    with pytest.raises(GovernanceError, match="lowercase SHA-256"):
        validate_fixture_payload("run-manifest", fixture)
    with pytest.raises(GovernanceError, match="unknown portable schema"):
        validate_fixture_payload("unknown", {})


def test_taxonomy_percentages_must_sum_to_one_hundred(tmp_path: Path) -> None:
    taxonomy = _json(DATA_ROOT / "tamper-taxonomy.json")
    distribution = taxonomy["planned_tampered_target_distribution_percent"]
    assert isinstance(distribution, dict)
    distribution["amount"] = 24
    temporary_root = tmp_path / "data"
    temporary_root.mkdir()
    (temporary_root / "tamper-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    with pytest.raises(GovernanceError, match="sum to 100"):
        validate_taxonomy(temporary_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(taxonomy_version="v0"), "unsupported"),
        (
            lambda value: value.update(planned_tampered_target_distribution_percent={}),
            "distribution is incomplete",
        ),
        (
            lambda value: value["planned_tampered_target_distribution_percent"].update(amount=True),
            "non-negative integers",
        ),
    ],
)
def test_taxonomy_rejects_invalid_documents(tmp_path: Path, mutation: object, message: str) -> None:
    root = _copied_data_root(tmp_path)
    taxonomy = _json(root / "tamper-taxonomy.json")
    assert callable(mutation)
    mutation(taxonomy)
    (root / "tamper-taxonomy.json").write_text(json.dumps(taxonomy), encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        validate_taxonomy(root)


def test_withdrawal_ledger_blocks_participant_and_rejects_unknown_hash() -> None:
    blocked = load_withdrawal_ledger(DATA_ROOT / "fixtures" / "withdrawal-ledger.fixture.json")
    assert_participant_not_withdrawn("7" * 64, blocked)
    with pytest.raises(GovernanceError, match="present in the withdrawal ledger"):
        assert_participant_not_withdrawn("6" * 64, blocked)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("participant_id_hash", "bad", "lowercase SHA-256"),
        ("withdrawn_at", "never", "ISO-8601"),
        ("scope", "unknown", "scope is invalid"),
        ("status", "unknown", "status is invalid"),
        ("request_reference", "", "non-empty string"),
    ],
)
def test_withdrawal_ledger_rejects_invalid_entries(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    ledger = _json(DATA_ROOT / "fixtures" / "withdrawal-ledger.fixture.json")
    entries = ledger["entries"]
    assert isinstance(entries, list) and isinstance(entries[0], dict)
    entries[0][field] = value
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(GovernanceError, match=message):
        load_withdrawal_ledger(path)


def test_withdrawal_ledger_rejects_version_shape_and_duplicates(tmp_path: Path) -> None:
    ledger = _json(DATA_ROOT / "fixtures" / "withdrawal-ledger.fixture.json")
    ledger["schema_version"] = "v0"
    path = tmp_path / "version.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(GovernanceError, match="unsupported withdrawal"):
        load_withdrawal_ledger(path)

    ledger = _json(DATA_ROOT / "fixtures" / "withdrawal-ledger.fixture.json")
    ledger["entries"] = "bad"
    path = tmp_path / "shape.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(GovernanceError, match="must be a list"):
        load_withdrawal_ledger(path)

    ledger = _json(DATA_ROOT / "fixtures" / "withdrawal-ledger.fixture.json")
    entries = ledger["entries"]
    assert isinstance(entries, list)
    entries.append(copy.deepcopy(entries[0]))
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(GovernanceError, match="must be unique"):
        load_withdrawal_ledger(path)


def test_withdrawal_check_rejects_invalid_hash() -> None:
    with pytest.raises(GovernanceError, match="lowercase SHA-256"):
        assert_participant_not_withdrawn("bad", frozenset())


def test_public_fixture_markers_reject_unmarked_and_non_synthetic_payloads() -> None:
    with pytest.raises(GovernanceError, match="lacks a fictitious marker"):
        governance._validate_public_fixture_markers("ocr-truth", {"value": "ordinary"})
    with pytest.raises(GovernanceError, match="controlled synthetic"):
        governance._validate_public_fixture_markers(
            "transaction", {"value": "FIXTURE", "dataset_source": "paysim"}
        )
    with pytest.raises(GovernanceError, match="synthetic and participant-free"):
        governance._validate_public_fixture_markers(
            "screenshot",
            {
                "value": "FIXTURE",
                "provenance": "controlled_real",
                "consent_scope": "internal_only",
            },
        )


@pytest.mark.parametrize(
    "private_path",
    [
        "data/raw/private.json",
        "data/private/private.json",
        "data/consent-records/completed.pdf",
        "data/withdrawal-records/ledger.json",
        "ml/data/authorised/private.png",
        "ml/checkpoints/model.bin",
    ],
)
def test_private_and_raw_paths_are_ignored(private_path: str) -> None:
    assert _ignore_spec().match_file(private_path)


def test_registry_itself_is_not_ignored() -> None:
    assert not _ignore_spec().match_file("data/registry.yaml")
