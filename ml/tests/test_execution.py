from __future__ import annotations

from pathlib import Path

import pytest

from momo_fdvs_ml.execution import (
    FULL_TRAINING_ACKNOWLEDGEMENT,
    ExecutionGuardError,
    ExecutionProfile,
    assert_ci_profile_is_safe,
    detect_execution_context,
    require_training_execution,
)

COLAB_ENVIRONMENT = {
    "COLAB_RELEASE_TAG": "release-colab_20260801",
    "COLAB_BACKEND_VERSION": "next",
}


def test_ci_workflow_pins_unit_profile_and_registers_ml_gate() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    workflow = (repository_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "MOMO_FDVS_EXECUTION_PROFILE: unit" in workflow
    assert "python scripts/verify_ml.py" in workflow
    assert "MOMO_FDVS_EXECUTION_PROFILE: full" not in workflow


def test_detect_execution_context_is_conservative() -> None:
    assert detect_execution_context({}).is_colab is False
    assert detect_execution_context({"COLAB_RELEASE_TAG": "present"}).is_colab is False
    assert detect_execution_context(COLAB_ENVIRONMENT).is_colab is True
    assert detect_execution_context({"CI": "true"}).is_ci is True
    assert detect_execution_context({"GITHUB_ACTIONS": "true"}).is_ci is True


@pytest.mark.parametrize("profile", [ExecutionProfile.UNIT, ExecutionProfile.SMOKE])
def test_unit_and_smoke_profiles_cannot_fit_models(profile: ExecutionProfile) -> None:
    with pytest.raises(ExecutionGuardError, match="requires --profile full"):
        require_training_execution(
            profile,
            acknowledgement=FULL_TRAINING_ACKNOWLEDGEMENT,
            environment=COLAB_ENVIRONMENT,
        )


def test_full_training_is_blocked_locally_even_with_acknowledgement() -> None:
    with pytest.raises(ExecutionGuardError, match="only in Google Colab"):
        require_training_execution(
            ExecutionProfile.FULL,
            acknowledgement=FULL_TRAINING_ACKNOWLEDGEMENT,
            environment={},
        )


def test_full_training_is_blocked_in_ci_even_if_colab_variables_are_present() -> None:
    with pytest.raises(ExecutionGuardError, match="prohibited in CI"):
        require_training_execution(
            ExecutionProfile.FULL,
            acknowledgement=FULL_TRAINING_ACKNOWLEDGEMENT,
            environment={**COLAB_ENVIRONMENT, "CI": "true"},
        )


def test_full_training_requires_exact_acknowledgement() -> None:
    with pytest.raises(ExecutionGuardError, match="exact deliberate acknowledgement"):
        require_training_execution(
            ExecutionProfile.FULL,
            acknowledgement="yes",
            environment=COLAB_ENVIRONMENT,
        )


def test_acknowledged_colab_full_training_context_is_permitted() -> None:
    context = require_training_execution(
        ExecutionProfile.FULL,
        acknowledgement=FULL_TRAINING_ACKNOWLEDGEMENT,
        environment=COLAB_ENVIRONMENT,
    )
    assert context.is_colab is True
    assert context.is_ci is False


def test_ci_profile_guard_rejects_full_and_invalid_values() -> None:
    assert_ci_profile_is_safe({"CI": "true", "MOMO_FDVS_EXECUTION_PROFILE": "unit"})
    assert_ci_profile_is_safe({"CI": "true", "MOMO_FDVS_EXECUTION_PROFILE": "smoke"})
    with pytest.raises(ExecutionGuardError, match="cannot select"):
        assert_ci_profile_is_safe({"CI": "true", "MOMO_FDVS_EXECUTION_PROFILE": "full"})
    with pytest.raises(ExecutionGuardError, match="unknown"):
        assert_ci_profile_is_safe({"CI": "true", "MOMO_FDVS_EXECUTION_PROFILE": "turbo"})
