"""Standard-library-only guards for installing pinned packages in Google Colab."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Final

RESTART_REPORT_VERSION: Final = "colab-runtime-restart-report-v1"
IMPORT_PROBE_VERSION: Final = "colab-runtime-import-probe-v1"
DISTRIBUTION_MODULE_PREFIXES: Final[dict[str, tuple[str, ...]]] = {
    "Pillow": ("PIL",),
    "numpy": ("numpy",),
    "opencv-python-headless": ("cv2",),
    "pandas": ("pandas",),
    "scikit-learn": ("sklearn",),
}


def distribution_snapshot() -> dict[str, str | None]:
    """Read critical installed versions without importing their runtime modules."""

    snapshot: dict[str, str | None] = {}
    for distribution in DISTRIBUTION_MODULE_PREFIXES:
        try:
            snapshot[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            snapshot[distribution] = None
    return snapshot


def runtime_restart_report(
    *,
    before: Mapping[str, str | None],
    after: Mapping[str, str | None],
    loaded_modules: Sequence[str],
    current_process_healthy: bool,
) -> dict[str, object]:
    """Report whether pip changed a distribution already imported by this process."""

    changed = sorted(
        distribution
        for distribution in set(before) | set(after)
        if before.get(distribution) != after.get(distribution)
    )
    loaded_changed = sorted(
        distribution
        for distribution in changed
        if any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in loaded_modules
            for prefix in DISTRIBUTION_MODULE_PREFIXES.get(distribution, ())
        )
    )
    return {
        "schema_version": RESTART_REPORT_VERSION,
        "changed_distributions": changed,
        "current_process_healthy": current_process_healthy,
        "loaded_changed_distributions": loaded_changed,
        "restart_required": bool(loaded_changed) or not current_process_healthy,
    }


def _probe_pillow() -> None:
    importlib.import_module("PIL.Image")
    importlib.import_module("PIL.ImageDraw")
    importlib.import_module("PIL.ImageText")
    typing_module = importlib.import_module("PIL._typing")
    if "_Ink" not in vars(typing_module):
        raise ImportError("Pillow typing contract is incomplete")


def runtime_import_probe() -> dict[str, object]:
    """Import binary/runtime boundaries in a clean child process."""

    probes: dict[str, Callable[[], object]] = {
        "Pillow": _probe_pillow,
        "numpy": lambda: importlib.import_module("numpy.strings"),
        "opencv": lambda: importlib.import_module("cv2"),
        "pandas": lambda: importlib.import_module("pandas"),
        "scikit-learn": lambda: importlib.import_module("sklearn"),
    }
    failures: list[str] = []
    for name, probe in probes.items():
        try:
            probe()
        except (ImportError, AttributeError, OSError):
            failures.append(name)
    return {
        "schema_version": IMPORT_PROBE_VERSION,
        "probes": list(probes),
        "failures": failures,
        "healthy": not failures,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", required=True)
    parser.parse_args(argv)
    report = runtime_import_probe()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["healthy"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
