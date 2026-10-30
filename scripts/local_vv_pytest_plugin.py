"""Minimal pytest plugin for exact-node selection evidence in local V&V runs."""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest


def pytest_collection_finish(session: pytest.Session) -> None:
    expected = os.environ.get("QF_LOCAL_VV_EXPECTED_NODEID", "")
    selection_path_text = os.environ.get("QF_LOCAL_VV_SELECTION_PATH", "")
    expected_source_root = os.environ.get("QF_LOCAL_VV_EXPECTED_SOURCE_ROOT", "")
    collected = [item.nodeid.replace("\\", "/") for item in session.items]
    if not expected or not selection_path_text or not expected_source_root:
        pytest.exit("local V&V selection guard is not configured", returncode=pytest.ExitCode.USAGE_ERROR)

    import_error = None
    path_before_import = tuple(sys.path)
    try:
        solveur_module = importlib.import_module("solveur")
    except Exception as exc:
        solveur_module = None
        import_error = f"{type(exc).__name__}: {exc}"
    path_unchanged = tuple(sys.path) == path_before_import
    observed_source = getattr(solveur_module, "__file__", None)
    expected_import = (Path(expected_source_root) / "solveur" / "__init__.py").resolve()
    source_import = str(Path(observed_source).resolve()) if isinstance(observed_source, str) else None
    source_import_ok = source_import == str(expected_import)
    selection_path = Path(selection_path_text)
    payload = {
        "schema": "qf-local-vv-pytest-selection-v1",
        "expected_nodeid": expected,
        "collected_nodeids": collected,
        "exact_match": collected == [expected],
        "source_import": source_import,
        "expected_source_import": str(expected_import),
        "source_import_ok": source_import_ok and import_error is None and path_unchanged,
        "import_error": import_error,
        "sys_path_unchanged": path_unchanged,
    }
    try:
        with selection_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        pytest.exit("selection record already exists; refusing overwrite", returncode=pytest.ExitCode.USAGE_ERROR)

    if collected != [expected] or not source_import_ok or import_error is not None or not path_unchanged:
        pytest.exit(
            "node selection or in-process solveur source identity does not match",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
