"""Fail-closed UNIT/SMOKE/FULL execution-profile policy."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

EXECUTION_POLICY_VERSION: Final = "colab-execution-policy-v1"
FULL_TRAINING_ACKNOWLEDGEMENT: Final = "I_ACKNOWLEDGE_FULL_COLAB_TRAINING"


class ExecutionGuardError(RuntimeError):
    """Raised before an operation that the selected execution profile cannot perform."""


class ExecutionProfile(StrEnum):
    """Cost and evidence boundary for repository ML commands."""

    UNIT = "unit"
    SMOKE = "smoke"
    FULL = "full"


@dataclass(frozen=True)
class ExecutionContext:
    """The non-secret runtime facts used by the accidental-execution guard."""

    is_ci: bool
    is_colab: bool


@dataclass(frozen=True)
class SmokeLimits:
    """Hard resource ceilings for non-reportable smoke fitting."""

    max_transaction_rows: int = 1_000
    max_images: int = 20
    max_epochs: int = 1


DEFAULT_SMOKE_LIMITS: Final = SmokeLimits()


def detect_execution_context(environment: Mapping[str, str] | None = None) -> ExecutionContext:
    """Detect CI and Colab conservatively from well-known runtime variables."""

    values = os.environ if environment is None else environment
    is_ci = (
        values.get("CI", "").lower() in {"1", "true", "yes"}
        or values.get("GITHUB_ACTIONS", "").lower() == "true"
    )
    is_colab = bool(values.get("COLAB_RELEASE_TAG")) and bool(values.get("COLAB_BACKEND_VERSION"))
    return ExecutionContext(is_ci=is_ci, is_colab=is_colab)


def require_training_execution(
    profile: ExecutionProfile,
    *,
    acknowledgement: str | None,
    environment: Mapping[str, str] | None = None,
) -> ExecutionContext:
    """Permit reportable fitting only in acknowledged, non-CI Google Colab FULL mode."""

    if not isinstance(profile, ExecutionProfile):
        raise ExecutionGuardError("training profile must use the canonical execution enum")
    context = detect_execution_context(environment)
    if profile is not ExecutionProfile.FULL:
        raise ExecutionGuardError(
            "model fitting requires --profile full; unit and smoke never run reportable training"
        )
    if context.is_ci:
        raise ExecutionGuardError("full training is prohibited in CI")
    if not context.is_colab:
        raise ExecutionGuardError("full training is permitted only in Google Colab")
    if acknowledgement != FULL_TRAINING_ACKNOWLEDGEMENT:
        raise ExecutionGuardError(
            "full training requires the exact deliberate acknowledgement token"
        )
    return context


def assert_ci_profile_is_safe(environment: Mapping[str, str] | None = None) -> None:
    """Reject a CI configuration that attempts to select FULL mode."""

    values = os.environ if environment is None else environment
    context = detect_execution_context(values)
    selected = values.get("MOMO_FDVS_EXECUTION_PROFILE", ExecutionProfile.UNIT.value).lower()
    try:
        profile = ExecutionProfile(selected)
    except ValueError as exc:
        raise ExecutionGuardError("unknown MOMO_FDVS_EXECUTION_PROFILE") from exc
    if context.is_ci and profile is ExecutionProfile.FULL:
        raise ExecutionGuardError("CI cannot select the full execution profile")


def require_smoke_execution(
    profile: ExecutionProfile,
    *,
    transaction_rows: int,
    image_count: int,
    epochs: int,
    uses_locked_test: bool,
    limits: SmokeLimits = DEFAULT_SMOKE_LIMITS,
) -> None:
    """Permit only bounded, fictitious, non-reportable smoke fitting."""

    if profile is not ExecutionProfile.SMOKE:
        raise ExecutionGuardError("tiny fitting requires the explicit smoke profile")
    for value, name in (
        (transaction_rows, "transaction row count"),
        (image_count, "image count"),
        (epochs, "epoch count"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ExecutionGuardError(f"smoke {name} must be a positive integer")
    if transaction_rows > limits.max_transaction_rows:
        raise ExecutionGuardError("smoke transaction row cap exceeded")
    if image_count > limits.max_images:
        raise ExecutionGuardError("smoke image cap exceeded")
    if epochs > limits.max_epochs:
        raise ExecutionGuardError("smoke epoch cap exceeded")
    if uses_locked_test:
        raise ExecutionGuardError("smoke execution cannot access a locked test partition")
