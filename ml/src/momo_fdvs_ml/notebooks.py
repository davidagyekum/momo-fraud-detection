"""Static policy validation for clean, restart-safe Colab notebooks."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

NOTEBOOK_POLICY_VERSION: Final = "colab-notebook-policy-v1"
SECRET_PATTERNS: Final = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "assigned credential": re.compile(
        r"(?im)^\s*[A-Z0-9_]*(?:TOKEN|PASSWORD|SECRET|API_KEY)\s*=\s*['\"][^'\"]{4,}['\"]"
    ),
}
PERSONAL_PATH_PATTERNS: Final = (
    re.compile(r"(?i)\b[A-Z]:\\+Users\\+"),
    re.compile(r"(?i)/Users/[^/]+/"),
    re.compile(r"(?i)/home/[^/]+/"),
)


class NotebookPolicyError(ValueError):
    """Raised when a notebook could leak state or cannot restart cleanly."""


@dataclass(frozen=True)
class NotebookIssue:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


def _load_notebook(path: Path) -> dict[str, object]:
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NotebookPolicyError(f"unable to parse notebook {path.name}") from exc
    if not isinstance(notebook, dict):
        raise NotebookPolicyError(f"notebook {path.name} must contain an object")
    return notebook


def _cell_source(cell: dict[str, object]) -> str:
    source = cell.get("source", [])
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    return ""


def validate_notebook(path: Path, *, root: Path) -> tuple[NotebookIssue, ...]:
    notebook = _load_notebook(path)
    relative = path.relative_to(root).as_posix()
    issues: list[NotebookIssue] = []

    def add(code: str, message: str) -> None:
        issues.append(NotebookIssue(relative, code, message))

    if notebook.get("nbformat") != 4 or notebook.get("nbformat_minor") != 5:
        add("NB_FORMAT", "notebook must use nbformat 4.5")
    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict) or "colab" not in metadata:
        add("NB_COLAB_METADATA", "notebook must include Colab metadata")
    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        add("NB_CELLS", "notebook must contain cells")
        return tuple(issues)
    code_cells: list[dict[str, object]] = []
    all_source: list[str] = []
    for index, raw_cell in enumerate(cells):
        if not isinstance(raw_cell, dict):
            add("NB_CELL_SHAPE", f"cell {index} must be an object")
            continue
        source = _cell_source(raw_cell)
        all_source.append(source)
        if raw_cell.get("cell_type") == "code":
            code_cells.append(raw_cell)
            if raw_cell.get("execution_count") is not None:
                add("NB_EXECUTION_COUNT", f"code cell {index} retains execution state")
            if raw_cell.get("outputs") != []:
                add("NB_OUTPUT", f"code cell {index} retains output")
        elif raw_cell.get("cell_type") == "markdown" and raw_cell.get("attachments"):
            add("NB_ATTACHMENT", f"markdown cell {index} retains an attachment")
    combined = "\n".join(all_source)
    if not code_cells:
        add("NB_CODE", "notebook must contain code cells")
    else:
        first_code = _cell_source(code_cells[0])
        if 'RUN_PROFILE = "smoke"' not in first_code:
            add("NB_PROFILE", "first code cell must visibly select the smoke profile")
        if "TARGET_COMMIT" not in first_code:
            add("NB_COMMIT", "first code cell must visibly configure an immutable commit")
    if "momo_fdvs_ml" not in combined:
        add("NB_THIN_WRAPPER", "notebook must delegate reusable logic to momo_fdvs_ml")
    if "## Stop boundary" not in combined:
        add("NB_STOP_BOUNDARY", "notebook must state its stop boundary")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(combined):
            add("NB_SECRET", f"notebook contains a possible {label}")
    if any(pattern.search(combined) for pattern in PERSONAL_PATH_PATTERNS):
        add("NB_PERSONAL_PATH", "notebook contains a personal absolute path")
    if re.search(r"(?im)^\s*[!%](?:pip|conda|apt)\s+install", combined):
        add("NB_AD_HOC_INSTALL", "notebook uses an ad-hoc package installation magic")
    if "MOMO_FDVS_EXECUTION_PROFILE" in combined and "full" in combined.lower():
        add("NB_FULL_MODE", "PR12 notebooks cannot select or acknowledge full execution")
    return tuple(issues)


def notebook_policy_report(root: Path) -> dict[str, object]:
    """Validate all standard Colab notebooks and return deterministic hashes."""

    notebook_paths = sorted(root.glob("*.ipynb"))
    if not notebook_paths:
        raise NotebookPolicyError("standard Colab notebook directory is empty")
    issues: list[NotebookIssue] = []
    hashes: dict[str, str] = {}
    for path in notebook_paths:
        issues.extend(validate_notebook(path, root=root))
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "policy_version": NOTEBOOK_POLICY_VERSION,
        "notebook_count": len(notebook_paths),
        "notebook_hashes": hashes,
        "issue_count": len(issues),
        "issues": [issue.as_dict() for issue in issues],
        "outputs_stripped": not any(issue.code == "NB_OUTPUT" for issue in issues),
        "execution_counts_stripped": not any(
            issue.code == "NB_EXECUTION_COUNT" for issue in issues
        ),
        "full_mode_selected": any(issue.code == "NB_FULL_MODE" for issue in issues),
    }


def require_clean_notebooks(root: Path) -> dict[str, object]:
    report = notebook_policy_report(root)
    if report["issue_count"] != 0:
        raise NotebookPolicyError("standard Colab notebooks failed policy validation")
    return report
