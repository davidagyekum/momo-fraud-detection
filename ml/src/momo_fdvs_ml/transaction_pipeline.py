"""Leakage-safe canonical transaction mapping, temporal splits and causal features."""

from __future__ import annotations

import hashlib
import heapq
import json
import math
from bisect import bisect_left, bisect_right
from collections import defaultdict, deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Final

PARTITIONS: Final = ("train", "tuning", "calibration", "locked_test")
BASE_FEATURES: Final = (
    "transaction_type",
    "amount",
    "log_amount",
    "step",
    "hour_sin",
    "hour_cos",
    "initiator_role",
    "recipient_role",
)
CAUSAL_FEATURES: Final = (
    "time_since_previous",
    "time_since_previous_missing",
    "prior_1h_count",
    "prior_1h_amount",
    "prior_6h_count",
    "prior_6h_amount",
    "prior_24h_count",
    "prior_24h_amount",
    "prior_24h_mean",
    "prior_24h_median",
    "prior_24h_summary_missing",
    "amount_to_prior_median",
    "amount_to_prior_median_missing",
    "unique_recipients_prior_24h",
    "is_new_recipient",
    "sequence_pattern",
    "causal_graph_degree_prior_24h",
)
MODEL_FEATURES: Final = (*BASE_FEATURES, *CAUSAL_FEATURES)
COMMON_FORBIDDEN_MODEL_COLUMNS: Final = frozenset(
    {
        "label_is_fraud",
        "isFraud",
        "isFlaggedFraud",
        "dataset_source",
        "source_row_id",
        "initiator_id",
        "recipient_id",
        "nameOrig",
        "nameDest",
        "initiator",
        "recipient",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "oldBalInitiator",
        "newBalInitiator",
        "oldBalRecipient",
        "newBalRecipient",
    }
)


class TransactionPipelineError(ValueError):
    """Raised when transaction data violates the frozen PR14 contract."""


@dataclass(frozen=True)
class SourceMapping:
    """Exact source-column mapping into the harmonized transaction contract."""

    dataset_id: str
    step: str
    transaction_type: str
    amount: str
    initiator: str
    recipient: str
    label: str
    expected_columns: tuple[str, ...]
    forbidden_primary_columns: frozenset[str]


SOURCE_MAPPINGS: Final = {
    "paysim": SourceMapping(
        dataset_id="paysim",
        step="step",
        transaction_type="type",
        amount="amount",
        initiator="nameOrig",
        recipient="nameDest",
        label="isFraud",
        expected_columns=(
            "step",
            "type",
            "amount",
            "nameOrig",
            "oldbalanceOrg",
            "newbalanceOrig",
            "nameDest",
            "oldbalanceDest",
            "newbalanceDest",
            "isFraud",
            "isFlaggedFraud",
        ),
        forbidden_primary_columns=frozenset(
            {
                "oldbalanceOrg",
                "newbalanceOrig",
                "oldbalanceDest",
                "newbalanceDest",
                "isFlaggedFraud",
            }
        ),
    ),
    "momtsim-v1": SourceMapping(
        dataset_id="momtsim-v1",
        step="step",
        transaction_type="transactionType",
        amount="amount",
        initiator="initiator",
        recipient="recipient",
        label="isFraud",
        expected_columns=(
            "step",
            "transactionType",
            "amount",
            "initiator",
            "oldBalInitiator",
            "newBalInitiator",
            "recipient",
            "oldBalRecipient",
            "newBalRecipient",
            "isFraud",
        ),
        forbidden_primary_columns=frozenset(
            {
                "oldBalInitiator",
                "newBalInitiator",
                "oldBalRecipient",
                "newBalRecipient",
            }
        ),
    ),
    "momtsim-v2": SourceMapping(
        dataset_id="momtsim-v2",
        step="step",
        transaction_type="transactionType",
        amount="amount",
        initiator="initiator",
        recipient="recipient",
        label="isFraud",
        expected_columns=(
            "step",
            "transactionType",
            "amount",
            "initiator",
            "oldBalInitiator",
            "newBalInitiator",
            "recipient",
            "oldBalRecipient",
            "newBalRecipient",
            "isFraud",
        ),
        forbidden_primary_columns=frozenset(
            {
                "oldBalInitiator",
                "newBalInitiator",
                "oldBalRecipient",
                "newBalRecipient",
            }
        ),
    ),
}


@dataclass(frozen=True)
class CanonicalTransaction:
    """A validated row whose raw actors are transient causal-computation inputs."""

    dataset_source: str
    source_row_id: str
    step: int
    transaction_type: str
    amount: float
    initiator_id: str
    recipient_id: str
    label_is_fraud: int


@dataclass(frozen=True)
class StepStatistic:
    """Safe aggregate for one source time step."""

    step: int
    row_count: int
    positive_count: int


@dataclass(frozen=True)
class PartitionSummary:
    """Frozen aggregate bounds for one chronological partition."""

    name: str
    minimum_step: int
    maximum_step: int
    unique_step_count: int
    row_count: int
    positive_count: int


@dataclass(frozen=True)
class TemporalSplitPlan:
    """Content-addressed temporal split created before any model selection."""

    schema_version: str
    dataset_id: str
    source_sha256: str
    ratios: tuple[float, float, float, float]
    minimum_positive_count: int
    positive_requirement_enforced: bool
    partitions: tuple[PartitionSummary, ...]
    manifest_sha256: str

    def partition_for_step(self, step: int) -> str:
        for partition in self.partitions:
            if partition.minimum_step <= step <= partition.maximum_step:
                return partition.name
        raise TransactionPipelineError(f"step {step} is outside the frozen split manifest")

    def safe_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "source_sha256": self.source_sha256,
            "ratios": list(self.ratios),
            "minimum_positive_count": self.minimum_positive_count,
            "positive_requirement_enforced": self.positive_requirement_enforced,
            "partitions": [partition.__dict__ for partition in self.partitions],
            "manifest_sha256": self.manifest_sha256,
            "frozen": True,
            "training_executed": False,
            "locked_test_accessed_for_decisions": False,
        }


@dataclass(frozen=True)
class TransactionFeatureRecord:
    """Model-safe features with label and opaque provenance kept separate."""

    source_row_id: str
    dataset_source: str
    partition: str
    label_is_fraud: int
    features: Mapping[str, object]


def source_mapping(dataset_id: str) -> SourceMapping:
    try:
        return SOURCE_MAPPINGS[dataset_id]
    except KeyError as exc:
        raise TransactionPipelineError(f"unsupported transaction dataset: {dataset_id}") from exc


def validate_source_header(mapping: SourceMapping, columns: Sequence[str]) -> None:
    if tuple(columns) != mapping.expected_columns:
        raise TransactionPipelineError(
            f"{mapping.dataset_id} columns or ordering do not match the registered source"
        )


def _parse_integer(value: object, *, field: str) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise TransactionPipelineError(f"{field} must be an integer") from exc
    return parsed


def _parse_amount(value: object) -> float:
    try:
        parsed = float(str(value))
    except (TypeError, ValueError) as exc:
        raise TransactionPipelineError("amount must be numeric") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise TransactionPipelineError("amount must be finite and non-negative")
    return parsed


def canonicalize_transaction(
    raw: Mapping[str, object],
    *,
    mapping: SourceMapping,
    source_sha256: str,
    source_row_number: int,
) -> CanonicalTransaction:
    """Map a registered raw row and replace its identity with an opaque stable hash."""

    if len(source_sha256) != 64 or any(char not in "0123456789abcdef" for char in source_sha256):
        raise TransactionPipelineError("source_sha256 must be lowercase SHA-256")
    if source_row_number < 1:
        raise TransactionPipelineError("source_row_number must be positive")
    missing = [column for column in mapping.expected_columns if column not in raw]
    if missing:
        raise TransactionPipelineError(f"raw row is missing column(s): {', '.join(missing)}")
    step = _parse_integer(raw[mapping.step], field="step")
    label = _parse_integer(raw[mapping.label], field="label")
    if step < 0:
        raise TransactionPipelineError("step must be non-negative")
    if label not in {0, 1}:
        raise TransactionPipelineError("label must be zero or one")
    transaction_type = str(raw[mapping.transaction_type]).strip()
    initiator = str(raw[mapping.initiator]).strip()
    recipient = str(raw[mapping.recipient]).strip()
    if not transaction_type or not initiator or not recipient:
        raise TransactionPipelineError("transaction type and actor IDs must be non-empty")
    identity = f"{mapping.dataset_id}\0{source_sha256}\0{source_row_number}".encode()
    return CanonicalTransaction(
        dataset_source=mapping.dataset_id,
        source_row_id=hashlib.sha256(identity).hexdigest(),
        step=step,
        transaction_type=transaction_type.upper(),
        amount=_parse_amount(raw[mapping.amount]),
        initiator_id=initiator,
        recipient_id=recipient,
        label_is_fraud=label,
    )


def _split_positions(step_count: int) -> tuple[int, int, int]:
    if step_count < 4:
        raise TransactionPipelineError("at least four unique steps are required")
    positions = [int(step_count * ratio) for ratio in (0.7, 0.8, 0.9)]
    positions[0] = min(max(positions[0], 1), step_count - 3)
    positions[1] = min(max(positions[1], positions[0] + 1), step_count - 2)
    positions[2] = min(max(positions[2], positions[1] + 1), step_count - 1)
    return positions[0], positions[1], positions[2]


def _positive_adjusted_positions(
    positives: Sequence[int], targets: tuple[int, int, int], minimum: int
) -> tuple[tuple[int, int, int], bool]:
    total_steps = len(positives)
    cumulative = [0]
    for count in positives:
        cumulative.append(cumulative[-1] + count)
    if minimum == 0:
        return targets, True
    best: tuple[int, tuple[int, int, int]] | None = None
    for first in range(1, total_steps - 2):
        for second in range(first + 1, total_steps - 1):
            if cumulative[second] - cumulative[first] < minimum:
                continue
            lower_third = max(
                second + 1,
                bisect_left(cumulative, cumulative[second] + minimum, lo=second + 1),
            )
            upper_third = min(
                total_steps - 1,
                bisect_right(cumulative, cumulative[-1] - minimum) - 1,
            )
            if lower_third > upper_third:
                continue
            third = min(max(targets[2], lower_third), upper_third)
            candidate = (first, second, third)
            displacement = sum(
                abs(value - target) for value, target in zip(candidate, targets, strict=True)
            )
            scored = (displacement, candidate)
            if best is None or scored < best:
                best = scored
    if best is None:
        return targets, False
    return best[1], True


def _split_payload(
    *,
    dataset_id: str,
    source_sha256: str,
    ratios: tuple[float, float, float, float],
    minimum_positive_count: int,
    positive_requirement_enforced: bool,
    partitions: tuple[PartitionSummary, ...],
) -> dict[str, object]:
    return {
        "schema_version": "transaction-temporal-split-v1",
        "dataset_id": dataset_id,
        "source_sha256": source_sha256,
        "ratios": ratios,
        "minimum_positive_count": minimum_positive_count,
        "positive_requirement_enforced": positive_requirement_enforced,
        "partitions": [partition.__dict__ for partition in partitions],
    }


def plan_temporal_splits(
    *,
    dataset_id: str,
    source_sha256: str,
    step_statistics: Iterable[StepStatistic],
    minimum_positive_count: int = 100,
) -> TemporalSplitPlan:
    """Freeze chronological step boundaries before model selection."""

    stats = tuple(sorted(step_statistics, key=lambda item: item.step))
    if not stats or len({item.step for item in stats}) != len(stats):
        raise TransactionPipelineError("step statistics must contain unique steps")
    if any(item.row_count < 1 or not 0 <= item.positive_count <= item.row_count for item in stats):
        raise TransactionPipelineError("step statistics contain invalid counts")
    if minimum_positive_count < 0:
        raise TransactionPipelineError("minimum_positive_count must be non-negative")
    targets = _split_positions(len(stats))
    positions, enforced = _positive_adjusted_positions(
        [item.positive_count for item in stats], targets, minimum_positive_count
    )
    slices = (
        stats[: positions[0]],
        stats[positions[0] : positions[1]],
        stats[positions[1] : positions[2]],
        stats[positions[2] :],
    )
    partitions = tuple(
        PartitionSummary(
            name=name,
            minimum_step=items[0].step,
            maximum_step=items[-1].step,
            unique_step_count=len(items),
            row_count=sum(item.row_count for item in items),
            positive_count=sum(item.positive_count for item in items),
        )
        for name, items in zip(PARTITIONS, slices, strict=True)
    )
    ratios = (0.7, 0.1, 0.1, 0.1)
    payload = _split_payload(
        dataset_id=dataset_id,
        source_sha256=source_sha256,
        ratios=ratios,
        minimum_positive_count=minimum_positive_count,
        positive_requirement_enforced=enforced,
        partitions=partitions,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return TemporalSplitPlan(
        schema_version="transaction-temporal-split-v1",
        dataset_id=dataset_id,
        source_sha256=source_sha256,
        ratios=ratios,
        minimum_positive_count=minimum_positive_count,
        positive_requirement_enforced=enforced,
        partitions=partitions,
        manifest_sha256=digest,
    )


def validate_model_columns(columns: Iterable[str]) -> tuple[str, ...]:
    materialised = tuple(columns)
    duplicates = sorted({name for name in materialised if materialised.count(name) > 1})
    if duplicates:
        raise TransactionPipelineError(f"duplicate model feature(s): {', '.join(duplicates)}")
    forbidden = sorted(set(materialised) & COMMON_FORBIDDEN_MODEL_COLUMNS)
    if forbidden:
        raise TransactionPipelineError(f"forbidden model feature(s): {', '.join(forbidden)}")
    if materialised != MODEL_FEATURES:
        raise TransactionPipelineError("model feature contract is incomplete or reordered")
    return materialised


def _actor_role(actor_id: str) -> str:
    prefix = actor_id[:1].upper()
    return {"C": "CUSTOMER", "M": "MERCHANT"}.get(prefix, "UNKNOWN")


def _window(
    history: deque[tuple[int, float, str, str]], minimum_step: int
) -> list[tuple[int, float, str, str]]:
    return [event for event in history if event[0] >= minimum_step]


def iter_causal_feature_records(
    rows: Iterable[CanonicalTransaction], *, split_plan: TemporalSplitPlan
) -> Iterator[TransactionFeatureRecord]:
    """Yield features using prior steps only; same-step rows update history together."""

    outgoing: dict[str, deque[tuple[int, float, str, str]]] = defaultdict(deque)
    graph: dict[str, deque[tuple[int, str]]] = defaultdict(deque)
    last_activity: dict[str, int] = {}
    expiry_heap: list[tuple[int, str]] = []
    current_step: int | None = None
    pending: list[CanonicalTransaction] = []

    def process_step(
        step: int, batch: Sequence[CanonicalTransaction]
    ) -> Iterator[TransactionFeatureRecord]:
        while expiry_heap and expiry_heap[0][0] < step - 24:
            expired_step, actor = heapq.heappop(expiry_heap)
            if last_activity.get(actor) == expired_step:
                outgoing.pop(actor, None)
                graph.pop(actor, None)
                last_activity.pop(actor)
        for actor in {row.initiator_id for row in batch}:
            while outgoing[actor] and outgoing[actor][0][0] < step - 24:
                outgoing[actor].popleft()
            while graph[actor] and graph[actor][0][0] < step - 24:
                graph[actor].popleft()
        for row in batch:
            history = outgoing[row.initiator_id]
            prior_1h = _window(history, step - 1)
            prior_6h = _window(history, step - 6)
            prior_24h = list(history)
            amounts = [event[1] for event in prior_24h]
            recipients = {event[2] for event in prior_24h}
            previous = history[-1] if history else None
            prior_median = median(amounts) if amounts else None
            angle = 2 * math.pi * (step % 24) / 24
            ratio = (
                row.amount / prior_median
                if prior_median is not None and prior_median != 0.0
                else None
            )
            features: dict[str, object] = {
                "transaction_type": row.transaction_type,
                "amount": row.amount,
                "log_amount": math.log1p(row.amount),
                "step": row.step,
                "hour_sin": math.sin(angle),
                "hour_cos": math.cos(angle),
                "initiator_role": _actor_role(row.initiator_id),
                "recipient_role": _actor_role(row.recipient_id),
                "time_since_previous": None if previous is None else step - previous[0],
                "time_since_previous_missing": int(previous is None),
                "prior_1h_count": len(prior_1h),
                "prior_1h_amount": sum(event[1] for event in prior_1h),
                "prior_6h_count": len(prior_6h),
                "prior_6h_amount": sum(event[1] for event in prior_6h),
                "prior_24h_count": len(prior_24h),
                "prior_24h_amount": sum(amounts),
                "prior_24h_mean": None if not amounts else sum(amounts) / len(amounts),
                "prior_24h_median": prior_median,
                "prior_24h_summary_missing": int(not amounts),
                "amount_to_prior_median": ratio,
                "amount_to_prior_median_missing": int(ratio is None),
                "unique_recipients_prior_24h": len(recipients),
                "is_new_recipient": int(row.recipient_id not in recipients),
                "sequence_pattern": (
                    f"START->{row.transaction_type}"
                    if previous is None
                    else f"{previous[3]}->{row.transaction_type}"
                ),
                "causal_graph_degree_prior_24h": len(
                    {counterparty for _, counterparty in graph[row.initiator_id]}
                ),
            }
            validate_model_columns(features)
            yield TransactionFeatureRecord(
                source_row_id=row.source_row_id,
                dataset_source=row.dataset_source,
                partition=split_plan.partition_for_step(step),
                label_is_fraud=row.label_is_fraud,
                features=features,
            )
        for row in batch:
            outgoing[row.initiator_id].append(
                (step, row.amount, row.recipient_id, row.transaction_type)
            )
            graph[row.initiator_id].append((step, row.recipient_id))
            graph[row.recipient_id].append((step, row.initiator_id))
            for actor in (row.initiator_id, row.recipient_id):
                last_activity[actor] = step
                heapq.heappush(expiry_heap, (step, actor))

    for row in rows:
        if row.dataset_source != split_plan.dataset_id:
            raise TransactionPipelineError("row source does not match split manifest")
        if current_step is not None and row.step < current_step:
            raise TransactionPipelineError("canonical rows must be ordered by non-decreasing step")
        if current_step is None:
            current_step = row.step
        if row.step != current_step:
            yield from process_step(current_step, pending)
            pending = []
            current_step = row.step
        pending.append(row)
    if current_step is not None:
        yield from process_step(current_step, pending)


def stfd_external_pretraining_manifest(
    *, inventory_sha256: str, pair_count: int
) -> dict[str, object]:
    """Return the only permitted PR14 assignment for STFD under ADR-030."""

    if len(inventory_sha256) != 64 or pair_count != 3932:
        raise TransactionPipelineError("STFD inventory identity or pair count drifted")
    payload = {
        "schema_version": "external-pretraining-split-v1",
        "dataset_id": "stfd",
        "inventory_sha256": inventory_sha256,
        "source_group_count": 1,
        "source_group_id": "single_external_pretraining_corpus_group",
        "assignment": "train_only",
        "pair_count": pair_count,
        "validation_partition_created": False,
        "test_partition_created": False,
        "internal_metrics_allowed": False,
        "training_executed": False,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**payload, "manifest_sha256": digest, "frozen": True}
