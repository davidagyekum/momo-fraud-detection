from __future__ import annotations

import hashlib

import pytest

from momo_fdvs_ml.transaction_pipeline import (
    MODEL_FEATURES,
    PARTITIONS,
    CanonicalTransaction,
    StepStatistic,
    TransactionPipelineError,
    canonicalize_transaction,
    iter_causal_feature_records,
    plan_temporal_splits,
    source_mapping,
    stfd_external_pretraining_manifest,
    validate_model_columns,
    validate_source_header,
)

SOURCE_HASH = "a" * 64


def _paysim_row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "step": "1",
        "type": "TRANSFER",
        "amount": "125.50",
        "nameOrig": "C100",
        "oldbalanceOrg": "300.0",
        "newbalanceOrig": "174.5",
        "nameDest": "M200",
        "oldbalanceDest": "0.0",
        "newbalanceDest": "125.5",
        "isFraud": "0",
        "isFlaggedFraud": "0",
    }
    row.update(updates)
    return row


def _transaction(
    row_id: str,
    step: int,
    *,
    initiator: str = "C1",
    recipient: str = "M1",
    amount: float = 10.0,
    transaction_type: str = "TRANSFER",
    source: str = "paysim",
) -> CanonicalTransaction:
    return CanonicalTransaction(
        dataset_source=source,
        source_row_id=hashlib.sha256(row_id.encode()).hexdigest(),
        step=step,
        transaction_type=transaction_type,
        amount=amount,
        initiator_id=initiator,
        recipient_id=recipient,
        label_is_fraud=0,
    )


def _plan(step_count: int = 8):
    return plan_temporal_splits(
        dataset_id="paysim",
        source_sha256=SOURCE_HASH,
        step_statistics=[StepStatistic(step, 2, 1) for step in range(1, step_count + 1)],
        minimum_positive_count=0,
    )


def test_registered_source_mappings_and_exact_headers() -> None:
    paysim = source_mapping("paysim")
    v1 = source_mapping("momtsim-v1")
    v2 = source_mapping("momtsim-v2")

    validate_source_header(paysim, paysim.expected_columns)
    validate_source_header(v1, v1.expected_columns)
    validate_source_header(v2, v2.expected_columns)
    assert paysim.transaction_type == "type"
    assert v1.expected_columns == v2.expected_columns
    assert "isFlaggedFraud" in paysim.forbidden_primary_columns
    assert "oldBalInitiator" in v1.forbidden_primary_columns


def test_source_mapping_and_header_reject_unknown_or_drift() -> None:
    with pytest.raises(TransactionPipelineError, match="unsupported"):
        source_mapping("other")
    mapping = source_mapping("paysim")
    with pytest.raises(TransactionPipelineError, match="columns or ordering"):
        validate_source_header(mapping, reversed(mapping.expected_columns))


def test_canonical_mapping_is_opaque_stable_and_validated() -> None:
    mapping = source_mapping("paysim")
    first = canonicalize_transaction(
        _paysim_row(), mapping=mapping, source_sha256=SOURCE_HASH, source_row_number=1
    )
    repeated = canonicalize_transaction(
        _paysim_row(), mapping=mapping, source_sha256=SOURCE_HASH, source_row_number=1
    )
    next_row = canonicalize_transaction(
        _paysim_row(), mapping=mapping, source_sha256=SOURCE_HASH, source_row_number=2
    )

    assert first == repeated
    assert first.source_row_id != next_row.source_row_id
    assert first.source_row_id not in {first.initiator_id, first.recipient_id}
    assert first.transaction_type == "TRANSFER"
    assert first.amount == 125.5
    assert first.label_is_fraud == 0


@pytest.mark.parametrize(
    ("row", "source_hash", "row_number", "message"),
    [
        (_paysim_row(), "bad", 1, "source_sha256"),
        (_paysim_row(), SOURCE_HASH, 0, "source_row_number"),
        (
            {key: value for key, value in _paysim_row().items() if key != "amount"},
            SOURCE_HASH,
            1,
            "missing",
        ),
        (_paysim_row(step="one"), SOURCE_HASH, 1, "step must be an integer"),
        (_paysim_row(step="-1"), SOURCE_HASH, 1, "non-negative"),
        (_paysim_row(isFraud="2"), SOURCE_HASH, 1, "zero or one"),
        (_paysim_row(amount="many"), SOURCE_HASH, 1, "amount must be numeric"),
        (_paysim_row(amount="nan"), SOURCE_HASH, 1, "finite"),
        (_paysim_row(type=""), SOURCE_HASH, 1, "non-empty"),
    ],
)
def test_canonical_mapping_rejects_invalid_rows(
    row: dict[str, object], source_hash: str, row_number: int, message: str
) -> None:
    with pytest.raises(TransactionPipelineError, match=message):
        canonicalize_transaction(
            row,
            mapping=source_mapping("paysim"),
            source_sha256=source_hash,
            source_row_number=row_number,
        )


def test_temporal_split_is_frozen_chronological_and_deterministic() -> None:
    stats = [StepStatistic(step, step + 2, step % 3) for step in range(10, 50)]
    first = plan_temporal_splits(
        dataset_id="paysim",
        source_sha256=SOURCE_HASH,
        step_statistics=reversed(stats),
        minimum_positive_count=0,
    )
    second = plan_temporal_splits(
        dataset_id="paysim",
        source_sha256=SOURCE_HASH,
        step_statistics=stats,
        minimum_positive_count=0,
    )

    assert first == second
    assert tuple(partition.name for partition in first.partitions) == PARTITIONS
    assert tuple(partition.unique_step_count for partition in first.partitions) == (28, 4, 4, 4)
    assert first.partitions[0].maximum_step < first.partitions[1].minimum_step
    assert first.partitions[1].maximum_step < first.partitions[2].minimum_step
    assert first.partitions[2].maximum_step < first.partitions[3].minimum_step
    assert first.partition_for_step(10) == "train"
    assert first.partition_for_step(49) == "locked_test"
    assert first.safe_dict()["locked_test_accessed_for_decisions"] is False
    assert len(first.manifest_sha256) == 64


def test_temporal_split_minimally_adjusts_for_positive_requirements() -> None:
    positives = [1] * 12 + [0, 0, 0, 0] + [1, 1, 1, 1]
    plan = plan_temporal_splits(
        dataset_id="paysim",
        source_sha256=SOURCE_HASH,
        step_statistics=[
            StepStatistic(index + 1, 3, positive) for index, positive in enumerate(positives)
        ],
        minimum_positive_count=2,
    )

    assert plan.positive_requirement_enforced is True
    assert all(partition.positive_count >= 2 for partition in plan.partitions[1:])
    assert tuple(partition.unique_step_count for partition in plan.partitions) != (14, 2, 2, 2)


def test_temporal_split_records_when_positive_requirement_is_infeasible() -> None:
    plan = plan_temporal_splits(
        dataset_id="momtsim-v1",
        source_sha256=SOURCE_HASH,
        step_statistics=[StepStatistic(step, 1, int(step == 8)) for step in range(1, 9)],
        minimum_positive_count=2,
    )
    assert plan.positive_requirement_enforced is False
    assert sum(partition.unique_step_count for partition in plan.partitions) == 8


@pytest.mark.parametrize(
    ("statistics", "minimum", "message"),
    [
        ([StepStatistic(1, 1, 0)] * 4, 0, "unique steps"),
        ([StepStatistic(step, 0, 0) for step in range(4)], 0, "invalid counts"),
        ([StepStatistic(step, 1, 2) for step in range(4)], 0, "invalid counts"),
        ([StepStatistic(step, 1, 0) for step in range(3)], 0, "at least four"),
        ([StepStatistic(step, 1, 0) for step in range(4)], -1, "non-negative"),
    ],
)
def test_temporal_split_rejects_invalid_statistics(
    statistics: list[StepStatistic], minimum: int, message: str
) -> None:
    with pytest.raises(TransactionPipelineError, match=message):
        plan_temporal_splits(
            dataset_id="paysim",
            source_sha256=SOURCE_HASH,
            step_statistics=statistics,
            minimum_positive_count=minimum,
        )


def test_split_lookup_rejects_unknown_step() -> None:
    with pytest.raises(TransactionPipelineError, match="outside"):
        _plan().partition_for_step(999)


def test_feature_contract_rejects_forbidden_duplicate_or_reordered_columns() -> None:
    assert validate_model_columns(MODEL_FEATURES) == MODEL_FEATURES
    with pytest.raises(TransactionPipelineError, match="forbidden"):
        validate_model_columns((*MODEL_FEATURES[:-1], "isFraud"))
    with pytest.raises(TransactionPipelineError, match="duplicate"):
        validate_model_columns((*MODEL_FEATURES, MODEL_FEATURES[0]))
    with pytest.raises(TransactionPipelineError, match="incomplete or reordered"):
        validate_model_columns(reversed(MODEL_FEATURES))


def test_causal_features_use_strictly_prior_steps_and_document_no_history() -> None:
    rows = [
        _transaction("one", 1, recipient="M1", amount=10),
        _transaction("two", 2, recipient="M2", amount=30, transaction_type="CASH_OUT"),
        _transaction("three", 8, recipient="M1", amount=40),
        _transaction("four", 26, recipient="M3", amount=50),
    ]
    records = list(iter_causal_feature_records(rows, split_plan=_plan(30)))
    first, second, third, fourth = (record.features for record in records)

    assert first["time_since_previous"] is None
    assert first["time_since_previous_missing"] == 1
    assert first["prior_24h_mean"] is None
    assert first["amount_to_prior_median"] is None
    assert first["sequence_pattern"] == "START->TRANSFER"
    assert first["initiator_role"] == "CUSTOMER"
    assert first["recipient_role"] == "MERCHANT"

    assert second["time_since_previous"] == 1
    assert second["prior_1h_count"] == 1
    assert second["prior_6h_count"] == 1
    assert second["prior_24h_median"] == 10
    assert second["amount_to_prior_median"] == 3
    assert second["unique_recipients_prior_24h"] == 1
    assert second["is_new_recipient"] == 1
    assert second["sequence_pattern"] == "TRANSFER->CASH_OUT"
    assert second["causal_graph_degree_prior_24h"] == 1

    assert third["prior_1h_count"] == 0
    assert third["prior_6h_count"] == 1
    assert third["prior_24h_count"] == 2
    assert third["is_new_recipient"] == 0

    assert fourth["prior_24h_count"] == 2
    assert fourth["prior_24h_amount"] == 70
    assert fourth["prior_24h_mean"] == 35
    assert fourth["prior_24h_median"] == 35


def test_same_step_order_and_future_insertion_cannot_change_earlier_features() -> None:
    first = _transaction("same-a", 2, recipient="M1", amount=10)
    second = _transaction("same-b", 2, recipient="M2", amount=20)
    future = _transaction("future", 6, recipient="M3", amount=30)
    plan = _plan()

    forward = list(iter_causal_feature_records([first, second], split_plan=plan))
    reversed_batch = list(iter_causal_feature_records([second, first], split_plan=plan))
    with_future = list(iter_causal_feature_records([first, second, future], split_plan=plan))
    forward_by_id = {record.source_row_id: record.features for record in forward}
    reverse_by_id = {record.source_row_id: record.features for record in reversed_batch}

    assert forward_by_id == reverse_by_id
    assert all(record.features["prior_24h_count"] == 0 for record in forward)
    assert [record.features for record in with_future[:2]] == [
        record.features for record in forward
    ]


def test_causal_graph_uses_prior_incoming_edges_and_unknown_roles() -> None:
    incoming = _transaction("incoming", 1, initiator="X1", recipient="Z9")
    outgoing = _transaction("outgoing", 2, initiator="Z9", recipient="M1")
    records = list(iter_causal_feature_records([incoming, outgoing], split_plan=_plan()))

    assert records[1].features["causal_graph_degree_prior_24h"] == 1
    assert records[1].features["initiator_role"] == "UNKNOWN"


def test_inactive_actor_state_expires_outside_the_24_hour_window() -> None:
    records = list(
        iter_causal_feature_records(
            [
                _transaction("cold", 1, initiator="COLD", recipient="M1"),
                _transaction("new", 30, initiator="NEW", recipient="M2"),
            ],
            split_plan=_plan(32),
        )
    )
    assert records[1].features["prior_24h_count"] == 0
    assert records[1].features["causal_graph_degree_prior_24h"] == 0


def test_causal_features_reject_source_mismatch_or_unsorted_rows() -> None:
    plan = _plan()
    with pytest.raises(TransactionPipelineError, match="source does not match"):
        list(
            iter_causal_feature_records(
                [_transaction("other", 1, source="momtsim-v1")], split_plan=plan
            )
        )
    with pytest.raises(TransactionPipelineError, match="ordered"):
        list(
            iter_causal_feature_records(
                [_transaction("later", 2), _transaction("earlier", 1)], split_plan=plan
            )
        )


def test_causal_feature_record_keeps_label_and_provenance_outside_features() -> None:
    record = next(iter_causal_feature_records([_transaction("one", 1)], split_plan=_plan()))
    assert tuple(record.features) == MODEL_FEATURES
    assert record.source_row_id not in record.features.values()
    assert "dataset_source" not in record.features
    assert "label_is_fraud" not in record.features
    assert record.partition == "train"


def test_stfd_manifest_is_frozen_train_only_and_identity_bound() -> None:
    inventory = "1087bbc4ba2cd349f08e2a0a4c4ebbc78c209d603d625c2a5344c0ff50f220dc"
    first = stfd_external_pretraining_manifest(inventory_sha256=inventory, pair_count=3932)
    second = stfd_external_pretraining_manifest(inventory_sha256=inventory, pair_count=3932)

    assert first == second
    assert first["assignment"] == "train_only"
    assert first["source_group_count"] == 1
    assert first["validation_partition_created"] is False
    assert first["test_partition_created"] is False
    assert first["internal_metrics_allowed"] is False
    assert first["training_executed"] is False
    assert len(str(first["manifest_sha256"])) == 64

    with pytest.raises(TransactionPipelineError, match="drifted"):
        stfd_external_pretraining_manifest(inventory_sha256="b" * 64, pair_count=3931)
