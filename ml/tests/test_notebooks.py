from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from momo_fdvs_ml.notebooks import (
    NotebookPolicyError,
    notebook_policy_report,
    require_clean_notebooks,
    validate_notebook,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_ROOT = REPOSITORY_ROOT / "ml/notebooks/colab"


def _notebook() -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "REPLACE_WITH_PUSHED_PR12_SHA"\n',
                    'sys.path.insert(0, str(repo / "ml/src"))\n',
                    "from momo_fdvs_ml.colab import ColabPaths\n",
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Stop boundary\n", "Stop before acquisition."],
            },
        ],
        "metadata": {"colab": {"provenance": []}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write(root: Path, notebook: dict[str, object], name: str = "fixture.ipynb") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(json.dumps(notebook), encoding="utf-8")
    return path


def test_committed_standard_notebooks_are_clean_and_match_recorded_report() -> None:
    report = require_clean_notebooks(NOTEBOOK_ROOT)
    recorded = json.loads((NOTEBOOK_ROOT / "notebook_report.json").read_text(encoding="utf-8"))
    assert report == recorded
    assert report["notebook_count"] == 4
    assert report["outputs_stripped"] is True
    assert report["execution_counts_stripped"] is True
    assert report["full_mode_selected"] is False


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(nbformat=3), "NB_FORMAT"),
        (lambda value: value.update(metadata={}), "NB_COLAB_METADATA"),
        (lambda value: value.update(cells=[]), "NB_CELLS"),
        (lambda value: value["cells"][0].update(execution_count=1), "NB_EXECUTION_COUNT"),
        (lambda value: value["cells"][0].update(outputs=[{"text": "output"}]), "NB_OUTPUT"),
        (
            lambda value: value["cells"][0].update(source=['RUN_PROFILE = "unit"\n']),
            "NB_PROFILE",
        ),
        (
            lambda value: value["cells"][0].update(
                source=['RUN_PROFILE = "smoke"\n', "from momo_fdvs_ml import cli\n"]
            ),
            "NB_COMMIT",
        ),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "x"\n',
                    "print('no package import')\n",
                ]
            ),
            "NB_THIN_WRAPPER",
        ),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "x"\n',
                    "from momo_fdvs_ml import cli\n",
                ]
            ),
            "NB_IMPORT_PATH",
        ),
        (lambda value: value.update(cells=value["cells"][:1]), "NB_STOP_BOUNDARY"),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "x"\n',
                    'API_TOKEN = "real-looking-value"\n',
                    "from momo_fdvs_ml import cli\n",
                ]
            ),
            "NB_SECRET",
        ),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "C:\\\\Users\\\\Person\\\\repo"\n',
                    "from momo_fdvs_ml import cli\n",
                ]
            ),
            "NB_PERSONAL_PATH",
        ),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "x"\n',
                    "!pip install package\n",
                    "from momo_fdvs_ml import cli\n",
                ]
            ),
            "NB_AD_HOC_INSTALL",
        ),
        (
            lambda value: value["cells"][0].update(
                source=[
                    'RUN_PROFILE = "smoke"\n',
                    'TARGET_COMMIT = "x"\n',
                    'MOMO_FDVS_EXECUTION_PROFILE = "full"\n',
                    "from momo_fdvs_ml import cli\n",
                ]
            ),
            "NB_FULL_MODE",
        ),
    ],
)
def test_notebook_policy_reports_unsafe_state(tmp_path: Path, mutation, code: str) -> None:  # type: ignore[no-untyped-def]
    notebook = copy.deepcopy(_notebook())
    mutation(notebook)
    path = _write(tmp_path, notebook)
    issues = validate_notebook(path, root=tmp_path)
    assert code in {issue.code for issue in issues}


def test_notebook_policy_reports_cell_shape_attachment_and_missing_code(tmp_path: Path) -> None:
    notebook = _notebook()
    notebook["cells"] = [
        "bad-cell",
        {
            "cell_type": "markdown",
            "metadata": {},
            "attachments": {"image": {}},
            "source": ["## Stop boundary\n", "momo_fdvs_ml"],
        },
    ]
    path = _write(tmp_path, notebook)
    codes = {issue.code for issue in validate_notebook(path, root=tmp_path)}
    assert {"NB_CELL_SHAPE", "NB_ATTACHMENT", "NB_CODE"}.issubset(codes)


def test_notebook_report_and_required_clean_gate_fail_on_issues(tmp_path: Path) -> None:
    notebook = _notebook()
    notebook["cells"][0]["outputs"] = [{"text": "unsafe"}]  # type: ignore[index]
    _write(tmp_path, notebook)
    report = notebook_policy_report(tmp_path)
    assert report["issue_count"] == 1
    assert report["outputs_stripped"] is False
    with pytest.raises(NotebookPolicyError, match="failed policy"):
        require_clean_notebooks(tmp_path)


def test_notebook_loader_rejects_missing_malformed_non_object_and_empty_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(NotebookPolicyError, match="unable to parse"):
        validate_notebook(tmp_path / "missing.ipynb", root=tmp_path)
    malformed = tmp_path / "malformed.ipynb"
    malformed.write_text("not-json", encoding="utf-8")
    with pytest.raises(NotebookPolicyError, match="unable to parse"):
        validate_notebook(malformed, root=tmp_path)
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(NotebookPolicyError, match="must contain"):
        validate_notebook(malformed, root=tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(NotebookPolicyError, match="directory is empty"):
        notebook_policy_report(empty)
