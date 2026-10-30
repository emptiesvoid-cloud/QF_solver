"""Run an isolated, non-numerical import-origin diagnostic for QF Solver."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .contracts import ContractError


_RUNNER_ROOT = Path(__file__).resolve().parents[2]
_CHILD = _RUNNER_ROOT / "scripts" / "wp12_runner" / "import_probe_child.py"
_SAFE_ENVIRONMENT_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")


def probe_solver_import(python_executable: Path, science_root: Path) -> dict[str, Any]:
    """Import only ``solveur`` in a clean child and verify its filesystem origin."""
    python = python_executable.resolve(strict=True)
    source = science_root.resolve(strict=True)
    if not python.is_file() or not _CHILD.is_file() or _CHILD.is_symlink():
        raise ContractError("import probe executable or child script is missing or unsafe")
    environment = {key: os.environ[key] for key in _SAFE_ENVIRONMENT_KEYS if key in os.environ}
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "BLIS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    completed = subprocess.run(
        [str(python), "-I", str(_CHILD), str(source)],
        cwd=_RUNNER_ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        raise ContractError(
            "isolated import-origin diagnostic failed: " + completed.stderr.decode("utf-8", errors="replace")[-500:]
        )
    try:
        report = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("isolated import-origin diagnostic returned invalid JSON") from exc
    if not isinstance(report, dict) or report.get("state") != "SOURCE_IMPORT_VERIFIED":
        raise ContractError("isolated import did not resolve from the pinned scientific checkout")
    if report.get("fem_or_analysis_api_called") is not False:
        raise ContractError("import diagnostic unexpectedly called a scientific analysis API")
    return report
