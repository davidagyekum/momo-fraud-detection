from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import momo_fdvs_ml.colab_bootstrap as colab_bootstrap

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_PATH = REPOSITORY_ROOT / "ml/src/momo_fdvs_ml/colab_bootstrap.py"


def test_restart_report_requires_clean_process_only_for_changed_loaded_distributions() -> None:
    report = colab_bootstrap.runtime_restart_report(
        before={"Pillow": "11.3.0", "numpy": "2.0.2", "pandas": "3.0.3"},
        after={"Pillow": "12.3.0", "numpy": "2.3.5", "pandas": "3.0.3"},
        loaded_modules=("PIL._typing", "google.colab.drive", "pandas.io.formats"),
        current_process_healthy=True,
    )

    assert report == {
        "changed_distributions": ["Pillow", "numpy"],
        "current_process_healthy": True,
        "loaded_changed_distributions": ["Pillow"],
        "restart_required": True,
        "schema_version": "colab-runtime-restart-report-v1",
    }

    safe = colab_bootstrap.runtime_restart_report(
        before={"Pillow": "11.3.0"},
        after={"Pillow": "12.3.0"},
        loaded_modules=("google.colab.drive",),
        current_process_healthy=True,
    )
    assert safe["restart_required"] is False


def test_restart_report_rejects_an_internally_inconsistent_current_process() -> None:
    report = colab_bootstrap.runtime_restart_report(
        before={"Pillow": "12.3.0"},
        after={"Pillow": "12.3.0"},
        loaded_modules=("PIL._typing",),
        current_process_healthy=False,
    )

    assert report["changed_distributions"] == []
    assert report["current_process_healthy"] is False
    assert report["restart_required"] is True


def test_runtime_probe_cli_imports_pinned_binary_and_pillow_boundaries() -> None:
    snapshot = colab_bootstrap.distribution_snapshot()
    assert set(snapshot) == {
        "Pillow",
        "numpy",
        "opencv-python-headless",
        "pandas",
        "scikit-learn",
    }
    assert all(version is not None for version in snapshot.values())
    in_process_report = colab_bootstrap.runtime_import_probe()
    assert in_process_report["healthy"] is True
    assert in_process_report["failures"] == []

    completed = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
        [sys.executable, str(BOOTSTRAP_PATH), "--probe"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["schema_version"] == "colab-runtime-import-probe-v1"
    assert report["healthy"] is True
    assert report["failures"] == []
    assert report["probes"] == ["Pillow", "numpy", "opencv", "pandas", "scikit-learn"]
