"""Bounded, noninteractive pytest launcher for local development only.

This is a workflow/resource monitor, not a sandbox. It intentionally exposes
fixed pytest scopes instead of an arbitrary command execution interface.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping, Sequence

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in an incomplete dev install
    psutil = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "development_autonomous_policy.json"
SERIES_RE = re.compile(r"^dev-[a-z0-9][a-z0-9-]{7,48}$")
PREFLIGHT_RE = re.compile(r"^pf-[a-z0-9]{12}$")
STANDARD_SCOPES = {"unit", "integration"}
WORKTREE_SCOPES = {"fem_exploratory", "math_non_fem"}
OWNER_ENV_KEYS = {
    "WPC02_AR_NATIVE_OWNER_GO_TOKEN",
    "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256",
    "QF_SOLVER_RUN_EVIDENCE",
    "QF_SOLVER_RUN_RECOVERED_EVIDENCE",
    "QF_SOLVER_EVIDENCE_ARCHIVE_ROOT",
}
NATIVE_GUARD_ENV_KEYS = (
    "QF_SOLVER_NO_NATIVE_EXECUTION",
    "WPC01_NO_NATIVE_EXECUTION",
    "WPC01_SPATIAL_NO_FEM_TEST",
    "WPC01_SPATIAL_TERMINAL_REHEARSAL",
)
D01_NATIVE_NODEIDS = (
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M1]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M2]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]",
)
D01_ATTEMPT_BASES = (
    "baseline",
    "source_change",
    "instrumentation_change",
    "launcher_correction",
    "new_diagnostic_hypothesis",
)
D01_OWNER_BUDGETS = {
    "timeout_seconds": 180,
    "rss_soft_limit_mib": 2048,
    "output_total_limit_mib": 64,
}


class PolicyError(ValueError):
    """A development run is outside the repository policy."""


@dataclass(frozen=True)
class ProcessResult:
    status: str
    return_code: int | None
    elapsed_seconds: float
    peak_rss_bytes: int
    peak_process_count: int
    stdout_bytes: int
    stderr_bytes: int
    archive_bytes: int
    temporary_bytes: int
    stop_reason: str | None


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"policy field {name} must be a positive number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise PolicyError(f"policy field {name} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise PolicyError(f"policy field {name} must be a positive number")
    return number


def _positive_integer(value: Any, name: str) -> int:
    number = _positive_number(value, name)
    if not number.is_integer():
        raise PolicyError(f"policy field {name} must be an integer")
    return int(number)


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    if not _is_within(path.resolve(), ROOT.resolve()):
        raise PolicyError("development policy must be stored inside this worktree")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read development policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != "qfsolver-development-autonomous-v2":
        raise PolicyError("unsupported development policy schema")
    if policy.get("mode") != "DEVELOPMENT_AUTONOMOUS":
        raise PolicyError("this launcher only accepts DEVELOPMENT_AUTONOMOUS")
    store = Path(str(policy.get("run_store", "")))
    if store.as_posix() != ".codex/development-runs":
        raise PolicyError("run_store must be the dedicated .codex/development-runs directory")
    _positive_number(policy.get("minimum_free_disk_mib"), "minimum_free_disk_mib")
    poll = _positive_number(policy.get("poll_interval_seconds"), "poll_interval_seconds")
    if poll > 5:
        raise PolicyError("poll_interval_seconds must not exceed 5")
    if not isinstance(policy.get("mandate_id"), str) or not policy["mandate_id"].startswith("DEVELOPMENT_AUTONOMOUS-"):
        raise PolicyError("a development-only mandate ID is required")
    scopes = policy.get("standard_scopes")
    expected_roots = {"unit": "tests/unit", "integration": "tests/integration"}
    if not isinstance(scopes, dict) or set(scopes) != set(expected_roots):
        raise PolicyError("only the fixed unit and integration scopes are accepted here")
    for name, scope in scopes.items():
        if not isinstance(scope, dict):
            raise PolicyError(f"scope {name} must be an object")
        for field in (
            "timeout_seconds",
            "rss_soft_limit_mib",
            "process_tree_limit",
            "output_total_limit_mib",
            "output_stream_limit_mib",
            "temporary_limit_mib",
            "archive_size_limit_mib",
            "max_attempts_per_series",
        ):
            _positive_number(scope.get(field), f"scopes.{name}.{field}")
        for field in ("process_tree_limit", "max_attempts_per_series"):
            _positive_integer(scope.get(field), f"scopes.{name}.{field}")
        if scope.get("pytest_root") != expected_roots[name]:
            raise PolicyError(f"scope {name} is bound to its fixed repository test directory")
        if name in STANDARD_SCOPES and scope.get("markers") != "not evidence and not benchmark and not large":
            raise PolicyError(f"scope {name} must exclude controlled evidence, benchmark, and large tests")
        if scope["output_total_limit_mib"] > 2 * scope["output_stream_limit_mib"]:
            raise PolicyError(f"scope {name} total output limit exceeds its two stream limits")
    worktrees = policy.get("worktrees")
    if not isinstance(worktrees, dict) or set(worktrees) != {"d01", "c01", "e01"}:
        raise PolicyError("the authorized worktree registry must contain exactly d01, c01, and e01")
    required_budget_fields = (
        "timeout_seconds",
        "rss_soft_limit_mib",
        "process_tree_limit",
        "output_total_limit_mib",
        "output_stream_limit_mib",
        "temporary_limit_mib",
        "archive_size_limit_mib",
    )
    for worktree_id, entry in worktrees.items():
        if not isinstance(entry, dict):
            raise PolicyError(f"worktree {worktree_id} must be an object")
        expected_mode = "math_non_fem" if worktree_id == "e01" else "fem_exploratory"
        if entry.get("mode") != expected_mode:
            raise PolicyError(f"worktree {worktree_id} has an unauthorized execution mode")
        for field in ("root", "git_root", "branch", "baseline_commit", "source_root", "pytest_root"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise PolicyError(f"worktree {worktree_id} requires {field}")
        if not re.fullmatch(r"[0-9a-f]{40}", entry["baseline_commit"]):
            raise PolicyError(f"worktree {worktree_id} baseline_commit must be a full Git SHA-1")
        if Path(entry["root"]).resolve() != Path(entry["git_root"]).resolve():
            raise PolicyError(f"worktree {worktree_id} root and git_root must be identical")
        nodeids = entry.get("allowed_nodeids")
        if not isinstance(nodeids, list) or not nodeids or len(nodeids) != len(set(nodeids)):
            raise PolicyError(f"worktree {worktree_id} requires unique exact nodeids")
        if entry.get("allow_native_vv_skip_override") is not (worktree_id == "d01"):
            raise PolicyError("only exact D01 development nodes may lift their native-V&V skip")
        attempt_limit = _positive_integer(entry.get("attempt_limit_per_nodeid"), f"worktrees.{worktree_id}.attempt_limit_per_nodeid")
        if attempt_limit != 3:
            raise PolicyError("this Owner mandate permits at most three attempts per nodeid")
        budgets = entry.get("budgets")
        if not isinstance(budgets, dict):
            raise PolicyError(f"worktree {worktree_id} requires a budgets object")
        for field in required_budget_fields:
            _positive_number(budgets.get(field), f"worktrees.{worktree_id}.budgets.{field}")
        for field in ("process_tree_limit",):
            _positive_integer(budgets[field], f"worktrees.{worktree_id}.budgets.{field}")
        if budgets["output_total_limit_mib"] > 2 * budgets["output_stream_limit_mib"]:
            raise PolicyError(f"worktree {worktree_id} aggregate output exceeds its two stream caps")
        expected_test_root = "tests/unit" if worktree_id in {"c01", "e01"} else "tests/verification"
        if entry["pytest_root"] != expected_test_root:
            raise PolicyError(f"worktree {worktree_id} is bound to the wrong test class")
        for nodeid in nodeids:
            if not isinstance(nodeid, str) or "::" not in nodeid:
                raise PolicyError(f"worktree {worktree_id} contains a non-nodeid target")
            test_path = Path(nodeid.split("::", maxsplit=1)[0])
            if test_path.is_absolute() or ".." in test_path.parts or not nodeid.startswith(expected_test_root + "/"):
                raise PolicyError(f"worktree {worktree_id} nodeid escapes its approved test root")
            if worktree_id == "e01" and re.search(r"(?i)(tet|hex|beam|assembly|fem)", nodeid):
                raise PolicyError("E01 allowlist may contain only non-FEM constitutive-math tests")
    d01 = worktrees["d01"]
    d01_budgets = d01["budgets"]
    if any(
        type(d01_budgets.get(field)) is not int or d01_budgets[field] != expected
        for field, expected in D01_OWNER_BUDGETS.items()
    ):
        raise PolicyError("D01 timeout, soft RSS, and aggregate-output budgets must match the Owner envelope exactly")
    if d01["allowed_nodeids"] != list(D01_NATIVE_NODEIDS):
        raise PolicyError("D01 development permission is limited to the exact M1/M2/M3 diagnostic nodes")
    if d01.get("attempt_limits_per_nodeid") != {
        D01_NATIVE_NODEIDS[0]: 1,
        D01_NATIVE_NODEIDS[1]: 1,
        D01_NATIVE_NODEIDS[2]: 3,
    }:
        raise PolicyError("D01 per-nodeid attempt limits must match the new Owner envelope exactly")
    if d01.get("development_mandate_id") != "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01":
        raise PolicyError("D01 requires its distinct, development-only v2 mandate")
    if d01.get("require_clean_worktree") is not True:
        raise PolicyError("D01 requires a clean source worktree")
    ledger_config = d01.get("node_attempt_ledger")
    if not isinstance(ledger_config, dict) or set(ledger_config) != {"path", "predecessor"}:
        raise PolicyError("D01 requires a separate ledger linked to its immutable predecessor")
    ledger_path = ledger_config.get("path")
    if not isinstance(ledger_path, str) or not re.fullmatch(r"node-attempt-ledger-d01-v2\.json", ledger_path):
        raise PolicyError("D01 v2 ledger path must be the fixed mandate-specific filename")
    predecessor = ledger_config.get("predecessor")
    if (
        not isinstance(predecessor, dict)
        or set(predecessor) != {"path", "sha256", "mandate_id"}
        or predecessor.get("path") != "node-attempt-ledger.json"
        or not isinstance(predecessor.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", predecessor["sha256"])
        or predecessor.get("mandate_id") != policy["mandate_id"]
    ):
        raise PolicyError("D01 v2 predecessor ledger identity is invalid")
    return policy


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_targets(
    scope_name: str,
    target: str | None,
    policy: Mapping[str, Any],
    *,
    worktree_id: str | None = None,
) -> list[str]:
    if scope_name in WORKTREE_SCOPES:
        if worktree_id not in policy["worktrees"]:
            raise PolicyError("a registered worktree ID is required for this scope")
        entry = policy["worktrees"][worktree_id]
        if entry["mode"] != scope_name:
            raise PolicyError(f"worktree {worktree_id} is not authorized for {scope_name}")
        if not target or target not in entry["allowed_nodeids"]:
            raise PolicyError("target must be one exact nodeid in the registered worktree allowlist")
        path_text = target.split("::", maxsplit=1)[0]
        candidate = (Path(entry["root"]) / path_text).resolve()
        scope_root = (Path(entry["root"]) / entry["pytest_root"]).resolve()
        if not _is_within(candidate, scope_root) or not candidate.is_file():
            raise PolicyError("registered nodeid resolves outside its canonical worktree test root")
        return [target]

    if scope_name not in STANDARD_SCOPES:
        raise PolicyError(f"unsupported development scope: {scope_name}")
    if worktree_id is not None:
        raise PolicyError("standard local scopes do not accept an external worktree ID")
    scope = policy["standard_scopes"][scope_name]
    scope_root = (ROOT / scope["pytest_root"]).resolve()
    if target is None:
        raise PolicyError("standard development scopes require one explicit test function; broad suites are not auto-enabled")
    if "::" not in target or not target.rsplit("::", maxsplit=1)[-1].startswith("test_"):
        raise PolicyError("standard development scopes require one exact pytest test-function nodeid")
    path_text = target.split("::", maxsplit=1)[0]
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise PolicyError("test target must be repository-relative and cannot traverse parents")
    candidate = (ROOT / relative).resolve()
    if (
        not _is_within(candidate, scope_root)
        or not candidate.is_file()
        or candidate.suffix != ".py"
        or not candidate.name.startswith("test_")
    ):
        raise PolicyError(f"target must be a test module below {scope['pytest_root']}")
    return [target]


def build_pytest_command(
    scope_name: str,
    targets: Sequence[str],
    temp_dir: Path,
    *,
    repository_root: Path = ROOT,
    source_root: Path | None = None,
    controller_root: Path = ROOT,
    allow_native_skip_override: bool = False,
    collect_only: bool = False,
    junit_xml_path: Path | None = None,
) -> list[str]:
    if scope_name in WORKTREE_SCOPES:
        if len(targets) != 1 or source_root is None:
            raise PolicyError("registered worktree execution requires one exact nodeid and a source root")
        native_override = "True" if allow_native_skip_override else "False"
        bootstrap = "\n".join(
            (
                "from pathlib import Path",
                "import sys",
                "src = Path(sys.argv[1]).resolve()",
                "root = Path(sys.argv[2]).resolve()",
                "controller = Path(sys.argv[3]).resolve()",
                "mode = sys.argv[4]",
                "target = sys.argv[5]",
                "sys.path.insert(0, str(src))",
                "sys.path.insert(0, str(controller / 'scripts'))",
                "import solveur",
                "origin = Path(solveur.__file__).resolve()",
                "expected = (src / 'solveur' / '__init__.py').resolve()",
                "print('QF_DEV_SOLVER_ORIGIN=' + str(origin))",
                "if origin != expected:",
                "    raise SystemExit('wrong solveur import origin: ' + str(origin))",
                "import pytest",
                "from development_autonomous_pytest_plugin import ExactNodeGate",
                f"gate = ExactNodeGate((target,), allow_native_skip_override=(mode == 'd01' and {native_override}))",
                "raise SystemExit(pytest.main(sys.argv[6:], plugins=[gate]))",
            )
        )
        command = [
            sys.executable,
            "-B",
            "-c",
            bootstrap,
            str(source_root),
            str(repository_root),
            str(controller_root),
            "d01" if allow_native_skip_override else "registered",
            targets[0],
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(temp_dir),
        ]
        if collect_only:
            command.append("--collect-only")
        if junit_xml_path is not None:
            command.append(f"--junitxml={junit_xml_path.resolve()}")
        command.append(targets[0])
        return command
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(temp_dir),
    ]
    if scope_name in STANDARD_SCOPES:
        command.extend(["-m", "not evidence and not benchmark and not large"])
    if collect_only:
        command.append("--collect-only")
    if junit_xml_path is not None:
        command.append(f"--junitxml={junit_xml_path.resolve()}")
    command.extend(targets)
    return command


def build_child_environment(
    temp_dir: Path,
    base: Mapping[str, str] | None = None,
    *,
    source_root: Path | None = None,
    d01_source_sha: str | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    for key in tuple(environment):
        if key in OWNER_ENV_KEYS or (key.startswith("QF_") and ("OWNER" in key or "QUALIFICATION" in key)):
            environment.pop(key, None)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTEST_PLUGINS", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONSTARTUP", None)
    environment["QF_SOLVER_RUN_EVIDENCE"] = "0"
    environment["QF_SOLVER_RUN_RECOVERED_EVIDENCE"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["TMP"] = str(temp_dir)
    environment["TEMP"] = str(temp_dir)
    environment["TMPDIR"] = str(temp_dir)
    if source_root is not None:
        environment["PYTHONPATH"] = str(source_root)
    if d01_source_sha is not None:
        environment["QF_WP_D01_BJ_SOURCE_SHA"] = d01_source_sha
    environment["QF_DEVELOPMENT_AUTONOMOUS"] = "1"
    return environment


def _native_guard_environment(environment: Mapping[str, str]) -> dict[str, Any]:
    """Record no-native marker states without persisting arbitrary env values."""
    values: dict[str, str] = {}
    for index, name in enumerate(NATIVE_GUARD_ENV_KEYS):
        value = environment.get(name)
        if value is None:
            values[name] = "UNSET"
        elif index < 2:
            values[name] = "ACTIVE" if value not in ("", "0", "false", "False") else "INACTIVE"
        else:
            values[name] = "ACTIVE" if value == "1" else "INACTIVE"
    active = [
        name
        for name in NATIVE_GUARD_ENV_KEYS[:2]
        if values[name] == "ACTIVE"
    ]
    active.extend(name for name in NATIVE_GUARD_ENV_KEYS[2:] if values[name] == "ACTIVE")
    return {"values": values, "active_markers": active}


def _validate_native_guard_environment(
    parent_environment: Mapping[str, str],
    child_environment: Mapping[str, str],
) -> dict[str, Any]:
    """Require the child to preserve the no-native guard state checked preflight."""
    parent_state = _native_guard_environment(parent_environment)
    child_state = _native_guard_environment(child_environment)
    if child_state != parent_state:
        raise PolicyError(
            "child environment changed an explicit no-native marker after development preflight"
        )
    return child_state


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _archive_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _directory_size(path: Path) -> int:
    return _archive_size(path) if path.exists() else 0


def _file_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        {"path": item.relative_to(path).as_posix(), "bytes": item.stat().st_size, "sha256": _sha256(item)}
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]


def _unpack_numeric_bytes(dtype: str, raw: bytes) -> list[int | float | bool] | tuple[list[float], list[float]] | None:
    match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype)
    if match is None:
        return None
    kind, size_text = match.groups()
    size = int(size_text)
    prefix = dtype[0] if dtype[0] in "<>=" else "="
    formats = {
        ("b", 1): "?",
        ("i", 1): "b",
        ("i", 2): "h",
        ("i", 4): "i",
        ("i", 8): "q",
        ("u", 1): "B",
        ("u", 2): "H",
        ("u", 4): "I",
        ("u", 8): "Q",
        ("f", 2): "e",
        ("f", 4): "f",
        ("f", 8): "d",
    }
    if kind == "c":
        component_format = {8: "f", 16: "d"}.get(size)
        if component_format is None:
            return None
        if len(raw) % size:
            return None
        components = list(struct.unpack(f"{prefix}{len(raw) // (size // 2)}{component_format}", raw))
        return components[::2], components[1::2]
    item_format = formats.get((kind, size))
    if item_format is None or len(raw) % size:
        return None
    return list(struct.unpack(f"{prefix}{len(raw) // size}{item_format}", raw))


def _flatten_json_array(value: Any, shape: list[int], kind: str) -> list[int | float | bool] | None:
    if not shape:
        if kind == "b":
            return [value] if isinstance(value, bool) else None
        if kind in "iu":
            return [value] if isinstance(value, int) and not isinstance(value, bool) else None
        return [value] if _finite_number(value) else None
    if not isinstance(value, list) or len(value) != shape[0]:
        return None
    flattened: list[int | float | bool] = []
    for item in value:
        child = _flatten_json_array(item, shape[1:], kind)
        if child is None:
            return None
        flattened.extend(child)
    return flattened


def _valid_numeric_array_snapshot(value: Any, expected_shape: list[int]) -> bool:
    shape = value.get("shape") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or not isinstance(shape, list)
        or any(not isinstance(size, int) or isinstance(size, bool) for size in shape)
        or shape != expected_shape
        or "values" not in value
    ):
        return False
    dtype = value.get("dtype")
    dtype_match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype) if isinstance(dtype, str) else None
    encoded = value.get("raw_bytes_base64")
    digest = value.get("raw_representation_sha256")
    if dtype_match is None or not isinstance(encoded, str) or not isinstance(digest, str):
        return False
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return False
    if any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in expected_shape):
        return False
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return False
    expected_bytes = math.prod(expected_shape) * int(dtype_match.group(2))
    if len(raw) != expected_bytes:
        return False
    identity = json.dumps(
        {"dtype": dtype, "shape": expected_shape, "order": "C"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    if hashlib.sha256(identity + b"\0" + raw).hexdigest() != digest:
        return False
    unpacked = _unpack_numeric_bytes(dtype, raw)
    kind = dtype_match.group(1)
    if kind == "c":
        if not isinstance(unpacked, tuple) or not isinstance(value["values"], dict):
            return False
        real = _flatten_json_array(value["values"].get("real"), expected_shape, "f")
        imag = _flatten_json_array(value["values"].get("imag"), expected_shape, "f")
        return real == unpacked[0] and imag == unpacked[1]
    flattened = _flatten_json_array(value["values"], expected_shape, kind)
    return isinstance(unpacked, list) and flattened == unpacked


def _valid_csr_snapshot(value: Any, expected_shape: list[int]) -> bool:
    shape = value.get("shape") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("format") != "CSR_COPY_WITH_STORED_ORDER"
        or not isinstance(shape, list)
        or any(not isinstance(size, int) or isinstance(size, bool) for size in shape)
        or shape != expected_shape
        or not isinstance(value.get("nnz_stored"), int)
        or isinstance(value.get("nnz_stored"), bool)
        or value["nnz_stored"] <= 0
        or not isinstance(value.get("arrays"), dict)
    ):
        return False
    nnz = value["nnz_stored"]
    arrays = value["arrays"]
    if set(arrays) != {"data", "indices", "indptr"}:
        return False
    digest = hashlib.sha256()
    digest.update(json.dumps({"shape": expected_shape}, sort_keys=True).encode("ascii"))
    expected_lengths = {"data": nnz, "indices": nnz, "indptr": expected_shape[0] + 1}
    for name in ("data", "indices", "indptr"):
        item = arrays[name]
        if not isinstance(item, dict) or not isinstance(item.get("values"), list):
            return False
        dtype = item.get("dtype")
        dtype_match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype) if isinstance(dtype, str) else None
        encoded = item.get("raw_bytes_base64")
        if dtype_match is None or not isinstance(encoded, str) or len(item["values"]) != expected_lengths[name]:
            return False
        if (name == "data" and dtype_match.group(1) != "f") or (
            name != "data" and dtype_match.group(1) not in "iu"
        ):
            return False
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return False
        if len(raw) != expected_lengths[name] * int(dtype_match.group(2)):
            return False
        unpacked = _unpack_numeric_bytes(dtype, raw)
        if not isinstance(unpacked, list) or unpacked != item["values"]:
            return False
        if name == "data":
            if any(not _finite_number(number) for number in item["values"]):
                return False
        elif any(not isinstance(index, int) or isinstance(index, bool) or index < 0 for index in item["values"]):
            return False
        digest.update(name.encode("ascii"))
        digest.update(dtype.encode("ascii"))
        digest.update(raw)
    if digest.hexdigest() != value.get("stored_representation_sha256"):
        return False
    indices = arrays["indices"]["values"]
    indptr = arrays["indptr"]["values"]
    return (
        indptr[0] == 0
        and indptr[-1] == nnz
        and all(left <= right for left, right in zip(indptr, indptr[1:]))
        and all(index < expected_shape[1] for index in indices)
    )


def _same_csr_snapshot(left: Any, right: Any) -> bool:
    """Compare validated CSR evidence by its exact stored representation."""
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return all(left.get(field) == right.get(field) for field in ("format", "shape", "nnz_stored", "arrays"))


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_d01_junit_payload(
    xml_path: Path,
    target: str,
    expected_source_sha: str,
    pytest_return_code: int = 0,
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Require durable numerical record_property payloads for a D01 result."""
    mesh_match = re.search(r"\[(M[123])\]$", target)
    if mesh_match is None:
        return False, ["target has no registered D01 mesh suffix"], None
    mesh_id = mesh_match.group(1)
    if not xml_path.is_file():
        return False, ["pytest JUnit XML is missing"], None
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError, ValueError, RecursionError) as exc:
        return False, [f"pytest JUnit XML is unreadable: {type(exc).__name__}: {exc}"], None
    expected_module, expected_name = target.split("::", 1)
    expected_classname = expected_module.replace("\\", "/").removesuffix(".py").replace("/", ".")
    if root.tag != "testsuites" or len(root) != 1 or root[0].tag != "testsuite":
        return False, ["JUnit document does not have the expected single testsuites/testsuite structure"], None
    suite = root[0]
    cases = suite.findall("./testcase")
    if suite.get("tests") != "1" or len(cases) != 1:
        return False, [f"expected one JUnit testcase in one-test suite, found {len(cases)}"], None
    case = cases[0]
    if case.get("classname") != expected_classname or case.get("name") != expected_name:
        return False, ["JUnit testcase classname/name does not match the exact requested nodeid"], None
    if case.find("./skipped") is not None or suite.get("skipped") != "0":
        return False, ["JUnit testcase was skipped; a zero pytest exit code is not a scenario PASS"], None
    case_failures = int(case.find("./failure") is not None)
    case_errors = int(case.find("./error") is not None)
    try:
        suite_failures = int(suite.get("failures", ""))
        suite_errors = int(suite.get("errors", ""))
    except ValueError:
        return False, ["JUnit suite failure/error counters are malformed"], None
    if suite_failures != case_failures or suite_errors != case_errors:
        return False, ["JUnit suite counters do not match the exact testcase state"], None
    if pytest_return_code == 0 and (case_failures or case_errors):
        return False, ["JUnit reports a failed testcase despite pytest's successful exit code"], None
    property_items = case.findall("./properties/property")
    property_names = [item.get("name") for item in property_items]
    properties = {
        item.get("name"): item.get("value", item.text or "")
        for item in property_items
        if item.get("name")
    }
    required = (
        "wp_d01_cg_source_operands_json",
        "wp_d01_cg_projected_damping_m2_json",
        "wp_d01_cg_projected_damping_m4_json",
        "wp_d01_bj_experimental_results_json",
    )
    if any(property_names.count(name) != 1 for name in required):
        return False, ["JUnit must contain exactly one of every required numerical property"], None
    missing = [name for name in required if not properties.get(name)]
    if missing:
        return False, ["JUnit numerical properties missing: " + ", ".join(missing)], None
    decoded: dict[str, Any] = {}
    for name in required:
        try:
            decoded[name] = json.loads(
                properties[name],
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
            )
        except (json.JSONDecodeError, TypeError, ValueError, RecursionError) as exc:
            return False, [f"JUnit property {name} is not strict JSON: {exc}"], None
    expected_elements, expected_free_dofs = {"M1": (8, 48), "M2": (16, 96), "M3": (32, 192)}[mesh_id]
    matrix_shape = [expected_free_dofs, expected_free_dofs]
    source = decoded["wp_d01_cg_source_operands_json"]
    source_sha_values = [
        decoded["wp_d01_cg_source_operands_json"].get("source_sha") if isinstance(decoded["wp_d01_cg_source_operands_json"], dict) else None,
        decoded["wp_d01_cg_projected_damping_m2_json"].get("source_sha") if isinstance(decoded["wp_d01_cg_projected_damping_m2_json"], dict) else None,
        decoded["wp_d01_cg_projected_damping_m4_json"].get("source_sha") if isinstance(decoded["wp_d01_cg_projected_damping_m4_json"], dict) else None,
        decoded["wp_d01_bj_experimental_results_json"].get("source_sha") if isinstance(decoded["wp_d01_bj_experimental_results_json"], dict) else None,
    ]
    if expected_source_sha != expected_source_sha.lower() or not re.fullmatch(r"[0-9a-f]{40}", expected_source_sha):
        return False, ["expected source identity is not a full lowercase Git commit SHA"], None
    if source_sha_values != [expected_source_sha] * len(required):
        return False, ["numerical JUnit properties do not all bind to the exact D01 source commit"], None
    source_mesh = source.get("mesh") if isinstance(source, dict) else None
    operators = source.get("operators") if isinstance(source, dict) else None
    if (
        not isinstance(source_mesh, dict)
        or source_mesh.get("id") != mesh_id
        or source_mesh.get("elements") != expected_elements
        or source_mesh.get("free_dofs") != expected_free_dofs
        or not isinstance(source.get("operator_identity"), str)
        or not source["operator_identity"]
        or not isinstance(operators, dict)
        or not {"M", "K", "C_used_by_experiment"}.issubset(operators)
        or not isinstance(source.get("exact_numeric_arrays"), dict)
    ):
        return False, ["source-operator payload lacks the expected FEM mesh or exact M/K/C operands"], None
    if any(not _valid_csr_snapshot(operators[name], matrix_shape) for name in ("M", "K", "C_used_by_experiment")):
        return False, ["source M/K/C sparse snapshots are empty, malformed, or fail their stored-byte hashes"], None
    source_arrays = source["exact_numeric_arrays"]
    if (
        not _valid_numeric_array_snapshot(source_arrays.get("frequencies_hz"), [6])
        or not _valid_numeric_array_snapshot(source_arrays.get("normalized_equilibrium_residuals"), [6])
        or not _valid_numeric_array_snapshot(source_arrays.get("reduced_force"), [expected_free_dofs])
        or not isinstance(source_arrays.get("responses_full_free_complex"), list)
        or len(source_arrays["responses_full_free_complex"]) != 6
        or any(not _valid_numeric_array_snapshot(item, [expected_free_dofs]) for item in source_arrays["responses_full_free_complex"])
    ):
        return False, ["source numerical arrays are missing, empty, malformed, or fail their exact-byte hashes"], None
    for mode_count, property_name in (
        (2, "wp_d01_cg_projected_damping_m2_json"),
        (4, "wp_d01_cg_projected_damping_m4_json"),
    ):
        projection = decoded[property_name]
        if (
            not isinstance(projection, dict)
            or projection.get("mesh_id") != mesh_id
            or projection.get("mode_count") != mode_count
            or projection.get("source_sha") != expected_source_sha
            or projection.get("frozen_symmetry_threshold") != 1.0e-12
            or projection.get("acceptance_verdict") != "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTANCE_OVERRIDE"
            or not isinstance(projection.get("exact_numeric_arrays"), dict)
        ):
            return False, [f"projected-damping payload for {mode_count} modes is incomplete or mismatched"], None
        projected_arrays = projection["exact_numeric_arrays"]
        projected_shapes = {
            "mode_matrix": [expected_free_dofs, mode_count],
            "eigenvalues_rad2_s2": [mode_count],
            "damping_times_modes": [expected_free_dofs, mode_count],
            "projected_mass": [mode_count, mode_count],
            "projected_stiffness": [mode_count, mode_count],
            "projected_mass_gram": [mode_count, mode_count],
            "projected_damping": [mode_count, mode_count],
            "expected_projected_rayleigh_from_cached_operators": [mode_count, mode_count],
        }
        if (
            any(not _valid_numeric_array_snapshot(projected_arrays.get(name), shape) for name, shape in projected_shapes.items())
            or not _valid_csr_snapshot(projection.get("input_damping"), matrix_shape)
        ):
            return False, [f"projected-damping exact operands for {mode_count} modes are missing, malformed, or hash-invalid"], None
        if not _same_csr_snapshot(operators["C_used_by_experiment"], projection["input_damping"]):
            return False, [f"projected-damping input for {mode_count} modes does not exactly match source C_used_by_experiment"], None
    payload = decoded["wp_d01_bj_experimental_results_json"]
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("mesh"), dict)
        or payload["mesh"].get("id") != mesh_id
        or payload["mesh"].get("elements") != expected_elements
        or payload["mesh"].get("free_dofs") != expected_free_dofs
    ):
        return False, ["experimental payload mesh identity does not match the nodeid"], None
    if (
        payload.get("retained_mode_counts") != [2, 4]
        or payload.get("qualification") != "NOT_CERTIFIED"
        or payload.get("source_sha") != expected_source_sha
        or payload.get("c4_official_status") != "NOT_EVALUATED_BY_DESIGN"
        or payload.get("c4_complete_spectrum_captured") is not False
    ):
        return False, ["experimental payload mode counts or non-qualification marker are unexpected"], None
    responses = payload.get("responses")
    if not isinstance(responses, dict) or set(responses) != {"uncorrected", "corrected"}:
        return False, ["experimental response groups are missing or malformed"], None
    frequencies = payload.get("frequencies_hz")
    if not _valid_d01_experimental_frequency_grid(frequencies):
        return False, ["experimental payload must contain 0 Hz followed by five finite, positive, increasing frequencies"], None
    if source_arrays["frequencies_hz"]["values"] != frequencies:
        return False, ["source-operator and response payload frequency grids differ"], None
    for treatment, rows in responses.items():
        if not isinstance(rows, list) or len(rows) != 12:
            return False, [f"{treatment} payload must contain 12 rows (6 frequencies × 2 truncations)"], None
        if any(not isinstance(row, dict) for row in rows):
            return False, [f"{treatment} payload contains a non-object response row"], None
        if [row.get("mode_count") for row in rows] != [2] * 6 + [4] * 6:
            return False, [f"{treatment} payload does not preserve the expected 2/4-mode order"], None
        if [row.get("frequency_hz") for row in rows] != frequencies * 2:
            return False, [f"{treatment} response rows do not match the frozen frequency grid and order"], None
        for row in rows:
            tip = row.get("tip_uy_m")
            if (
                not isinstance(tip, dict)
                or not _finite_number(tip.get("real"))
                or not _finite_number(tip.get("imag"))
                or any(
                    not _finite_number(row.get(name)) or row[name] < 0
                    for name in ("relative_full_free_displacement_error", "normalized_free_equilibrium_residual", "direct_reference_residual")
                )
                or any(
                    row.get(name) is not None and not _finite_number(row.get(name))
                    for name in ("relative_tip_amplitude_error", "tip_phase_error_rad")
                )
                or not isinstance(row.get("energy"), dict)
                or not all(_finite_number(row["energy"].get(key)) for key in ("average_input_power_W", "average_rayleigh_dissipation_W"))
                or (row["energy"].get("absolute_balance_gap_W") is not None and not _finite_number(row["energy"].get("absolute_balance_gap_W")))
            ):
                return False, [f"{treatment} response row lacks finite displacement/error/residual metrics"], None
            if treatment == "uncorrected" and (not isinstance(row.get("wp05_diagnostic"), dict) or not row["wp05_diagnostic"]):
                return False, ["uncorrected response row lacks WP05 diagnostic evidence"], None
            if treatment == "corrected" and (
                row.get("correction_error_ratio_status") is None
                or not isinstance(row.get("correction_degraded_error"), bool)
                or not isinstance(row.get("wp_d01_diagnostics"), dict)
                or not row["wp_d01_diagnostics"]
                or (row.get("correction_error_ratio") is not None and (not _finite_number(row["correction_error_ratio"]) or row["correction_error_ratio"] < 0))
            ):
                return False, ["corrected response row lacks a valid correction ratio or D01 diagnostic"], None
    operator_identities = [
        source.get("operator_identity"),
        decoded["wp_d01_cg_projected_damping_m2_json"].get("operator_identity"),
        decoded["wp_d01_cg_projected_damping_m4_json"].get("operator_identity"),
    ]
    if not isinstance(payload.get("operator_identity"), str) or not payload["operator_identity"] or operator_identities != [payload["operator_identity"]] * 3:
        return False, ["source operators, projected damping and harmonic result payloads do not share one operator identity"], None
    return True, [], {
        "mesh_id": mesh_id,
        "elements": expected_elements,
        "free_dofs": expected_free_dofs,
        "property_names": list(required),
        "response_rows_per_treatment": 12,
        "symmetry_threshold": 1.0e-12,
    }


def _valid_d01_experimental_frequency_grid(frequencies: Any) -> bool:
    """Accept the frozen experiment grid: one static point, then five positive points."""
    if not isinstance(frequencies, list) or len(frequencies) != 6:
        return False
    if any(not _finite_number(value) for value in frequencies):
        return False
    numeric = [float(value) for value in frequencies]
    return (
        numeric[0] == 0.0
        and all(value > 0.0 for value in numeric[1:])
        and all(left < right for left, right in zip(numeric, numeric[1:]))
    )


def _d01_final_state(current_state: str, payload_complete: bool | None) -> str:
    """Never expose a pytest PASS when the required numerical archive is absent."""
    if current_state == "PASS" and payload_complete is not True:
        return "RESULT_ARCHIVE_INCOMPLETE"
    return current_state


def _process_snapshot(pid: int) -> tuple[int, int]:
    if psutil is None:
        raise PolicyError("psutil is required for monitored development execution")
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0, 0
    alive = []
    rss = 0
    for process in processes:
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                alive.append(process)
                rss += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return len(alive), rss


def _terminate_tree(pid: int) -> None:
    if psutil is None:
        return
    try:
        root = psutil.Process(pid)
        children = root.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    processes = list(reversed(children)) + [root]
    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _gone, alive = psutil.wait_procs(processes, timeout=2)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    psutil.wait_procs(alive, timeout=2)


def run_supervised_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    output_dir: Path,
    temporary_dir: Path | None = None,
    limits: Mapping[str, Any],
    poll_interval: float = 0.25,
) -> ProcessResult:
    """Run a child noninteractively with bounded capture and monitored resources."""
    if psutil is None:
        raise PolicyError("psutil is required; install the project test/dev dependencies before launching")
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    total_cap = int(limits["output_total_limit_mib"] * 1024 * 1024)
    stream_cap = int(limits["output_stream_limit_mib"] * 1024 * 1024)
    archive_cap = int(limits["archive_size_limit_mib"] * 1024 * 1024)
    temporary_dir = output_dir if temporary_dir is None else temporary_dir
    temporary_cap = int(limits.get("temporary_limit_mib", limits["archive_size_limit_mib"]) * 1024 * 1024)
    free_disk_floor = int(limits.get("minimum_free_disk_mib", 0) * 1024 * 1024)
    rss_cap = int(limits["rss_soft_limit_mib"] * 1024 * 1024)
    process_cap = int(limits["process_tree_limit"])
    timeout = float(limits["timeout_seconds"])

    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
        bufsize=0,
    )
    state_lock = threading.Lock()
    output_exceeded = threading.Event()
    capture = {"observed": {"stdout": 0, "stderr": 0}, "saved": {"stdout": 0, "stderr": 0}, "total_saved": 0}
    reader_errors: list[str] = []

    def pump(pipe: BinaryIO, path: Path, name: str) -> None:
        try:
            with path.open("wb") as output:
                while True:
                    chunk = pipe.read(64 * 1024)
                    if not chunk:
                        break
                    with state_lock:
                        capture["observed"][name] += len(chunk)
                        allowed = min(
                            len(chunk),
                            max(0, stream_cap - capture["saved"][name]),
                            max(0, total_cap - capture["total_saved"]),
                        )
                        if allowed:
                            output.write(chunk[:allowed])
                            capture["saved"][name] += allowed
                            capture["total_saved"] += allowed
                        if allowed < len(chunk):
                            output_exceeded.set()
                output.flush()
        except (OSError, ValueError) as exc:
            reader_errors.append(f"{name}: {exc}")
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=pump, args=(process.stdout, stdout_path, "stdout"), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, stderr_path, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()

    started = time.monotonic()
    peak_rss = 0
    peak_processes = 0
    stop_reason: str | None = None
    try:
        while True:
            if output_exceeded.is_set():
                stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            elapsed = time.monotonic() - started
            if elapsed > timeout:
                stop_reason = "WALL_TIMEOUT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            if process.poll() is not None:
                break
            process_count, rss = _process_snapshot(process.pid)
            peak_processes = max(peak_processes, process_count)
            peak_rss = max(peak_rss, rss)
            if process_count > process_cap:
                stop_reason = "PROCESS_TREE_LIMIT_EXCEEDED"
            elif rss > rss_cap:
                stop_reason = "RSS_SOFT_LIMIT_EXCEEDED"
            elif _directory_size(output_dir) > archive_cap:
                stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
            elif _directory_size(temporary_dir) > temporary_cap:
                stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
            elif free_disk_floor and shutil.disk_usage(cwd).free < free_disk_floor:
                stop_reason = "MINIMUM_FREE_DISK_FLOOR_CROSSED"
            if stop_reason is not None:
                _terminate_tree(process.pid)
                break
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)

    try:
        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    for reader in readers:
        reader.join(timeout=5)
    elapsed = time.monotonic() - started
    archive_bytes = _directory_size(output_dir)
    temporary_bytes = _directory_size(temporary_dir)
    if archive_bytes > archive_cap and stop_reason is None:
        stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
    if temporary_bytes > temporary_cap and stop_reason is None:
        stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
    if output_exceeded.is_set() and stop_reason is None:
        stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
    if reader_errors and stop_reason is None:
        stop_reason = "OUTPUT_CAPTURE_ERROR"
    if stop_reason:
        status = stop_reason
    elif return_code == 0:
        status = "PASS"
    else:
        status = "PYTEST_FAILED"
    with state_lock:
        stdout_bytes = int(capture["saved"]["stdout"])
        stderr_bytes = int(capture["saved"]["stderr"])
    return ProcessResult(
        status=status,
        return_code=return_code,
        elapsed_seconds=elapsed,
        peak_rss_bytes=peak_rss,
        peak_process_count=peak_processes,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        archive_bytes=archive_bytes,
        temporary_bytes=temporary_bytes,
        stop_reason=stop_reason or ("; ".join(reader_errors) if reader_errors else None),
    )


def _git_identity(
    root: Path = ROOT,
    *,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    top_level = git("rev-parse", "--show-toplevel")
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    if not top_level or Path(top_level).resolve() != root.resolve() or not head or not tree:
        raise PolicyError("registered project root is not the Git worktree being executed")
    if expected_branch is not None and branch != expected_branch:
        raise PolicyError(f"worktree branch mismatch: expected {expected_branch}, got {branch}")
    if baseline_commit is not None:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PolicyError("registered baseline is not an ancestor of this worktree HEAD")
    return {
        "root": str(root.resolve()),
        "branch": branch,
        "head": head,
        "tree": tree,
        "status_short": git("status", "--short", "--untracked-files=all"),
    }


def _next_attempt(
    series_dir: Path,
    series_id: str,
    scope_name: str,
    maximum: int,
    *,
    worktree_id: str | None = None,
    target: str | None = None,
) -> tuple[int, Path]:
    series_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = series_dir / "series.json"
    metadata = {
        "schema": "qfsolver-development-series-v2",
        "series_id": series_id,
        "scope": scope_name,
        "worktree_id": worktree_id,
        "target": target,
    }
    try:
        with metadata_path.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f"development series metadata is unreadable: {exc}") from exc
        if existing != metadata:
            raise PolicyError("development series ID is already bound to a different scope")
    prior = [path for path in series_dir.glob("attempt-[0-9][0-9][0-9][0-9]") if path.is_dir()]
    number = len(prior) + 1
    if number > maximum:
        raise PolicyError(f"development series exhausted its {maximum}-attempt budget")
    attempt_dir = series_dir / f"attempt-{number:04d}"
    try:
        attempt_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise PolicyError("another invocation is already using this development series") from exc
    return number, attempt_dir


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    """Acquire an OS-released lock; a stale lock file never blocks a later run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        else:  # pragma: no cover - exercised on non-Windows development hosts
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised on non-Windows development hosts
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


def _worktree_source_fingerprint(root: Path, target: str) -> str:
    """Hash the loaded solver, its Python helpers, test, conftests, and project config."""
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        raise PolicyError("cannot inventory worktree source files for retry identity")
    target_module = target.split("::", maxsplit=1)[0]
    files: set[str] = set()
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw).replace("\\", "/"))
        relative_text = relative.as_posix()
        if (
            relative_text.startswith("src/solveur/") and relative.suffix == ".py"
            or relative_text.startswith("experiments/") and relative.suffix == ".py"
            or relative_text == target_module
            or relative_text in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            files.add(relative_text)
    if target_module not in files:
        raise PolicyError("approved test module is absent from the source fingerprint inventory")
    digest = hashlib.sha256()
    for relative_text in sorted(files):
        path = (root / Path(relative_text)).resolve()
        if not _is_within(path, root.resolve()) or not path.is_file():
            raise PolicyError(f"source file escapes or is unavailable: {relative_text}")
        digest.update(relative_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _reserve_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    mandate_id: str,
    worktree_id: str,
    target: str,
    series_id: str,
    source_fingerprint: str,
    reason: str,
    maximum: int,
    predecessor: Mapping[str, str] | None = None,
    controller_fingerprint: str | None = None,
    attempt_basis: str | None = None,
    hypothesis_id: str | None = None,
) -> tuple[str, int]:
    key = f"{mandate_id}:{worktree_id}:{target}"
    schema = "qfsolver-development-node-ledger-v2" if predecessor is not None else "qfsolver-development-node-ledger-v1"
    with _exclusive_file_lock(lock_path):
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PolicyError(f"development attempt ledger is unreadable: {exc}") from exc
        else:
            ledger = {"schema": schema, "mandate_id": mandate_id, "entries": {}}
            if predecessor is not None:
                ledger["predecessor"] = dict(predecessor)
        if (
            not isinstance(ledger, dict)
            or ledger.get("schema") != schema
            or ledger.get("mandate_id") != mandate_id
            or not isinstance(ledger.get("entries"), dict)
            or (predecessor is not None and ledger.get("predecessor") != dict(predecessor))
        ):
            raise PolicyError("development attempt ledger identity/schema mismatch")
        attempts = ledger["entries"].setdefault(key, [])
        if not isinstance(attempts, list):
            raise PolicyError("development attempt ledger entry is malformed")
        if len(attempts) >= maximum:
            raise PolicyError(f"development mandate exhausted {maximum} attempts for this nodeid")
        if worktree_id == "d01" and mandate_id.endswith("-v2-d01"):
            if attempt_basis not in D01_ATTEMPT_BASES or controller_fingerprint is None:
                raise PolicyError("D01 v2 attempts require a classified change basis and controller fingerprint")
            if attempt_basis == "new_diagnostic_hypothesis":
                if not hypothesis_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", hypothesis_id):
                    raise PolicyError("a new diagnostic hypothesis requires a concise unique hypothesis ID")
                if any(item.get("hypothesis_id") == hypothesis_id for item in attempts):
                    raise PolicyError("D01 diagnostic hypothesis ID has already been used for this nodeid")
            elif hypothesis_id is not None:
                raise PolicyError("hypothesis_id is only valid for the new_diagnostic_hypothesis basis")
            if not attempts and attempt_basis != "baseline":
                raise PolicyError("the first D01 v2 attempt must be classified as baseline")
            if attempts:
                if attempt_basis == "baseline":
                    raise PolicyError("baseline is only valid for the first D01 attempt")
                last = attempts[-1]
                same_inputs = (
                    last.get("source_fingerprint") == source_fingerprint
                    and last.get("controller_fingerprint") == controller_fingerprint
                )
                if attempt_basis in {"source_change", "instrumentation_change"} and last.get("source_fingerprint") == source_fingerprint:
                    raise PolicyError(f"{attempt_basis} requires a changed D01 source fingerprint")
                if attempt_basis == "launcher_correction" and last.get("controller_fingerprint") == controller_fingerprint:
                    raise PolicyError("launcher_correction requires a changed controller fingerprint")
                if same_inputs and attempt_basis != "new_diagnostic_hypothesis":
                    raise PolicyError("identical D01 inputs require a separately identified new diagnostic hypothesis")
                if same_inputs and last.get("attempt_basis") == attempt_basis and last.get("hypothesis_id") == hypothesis_id:
                    raise PolicyError("identical D01 attempt basis/hypothesis refused")
        elif attempts:
            last = attempts[-1]
            if last.get("source_fingerprint") == source_fingerprint and last.get("reason") == reason:
                raise PolicyError("identical repeat refused: change the source or document a new diagnostic hypothesis")
        number = len(attempts) + 1
        attempts.append(
            {
                "attempt": number,
                "series_id": series_id,
                "source_fingerprint": source_fingerprint,
                "controller_fingerprint": controller_fingerprint,
                "attempt_basis": attempt_basis,
                "hypothesis_id": hypothesis_id,
                "reason": reason,
                "state": "RESERVED",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        _atomic_json(ledger_path, ledger)
    return key, number


def _complete_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    key: str,
    attempt_number: int,
    state: str,
    finished_at_utc: str,
    post_fingerprint: str,
) -> None:
    with _exclusive_file_lock(lock_path):
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            attempts = ledger["entries"][key]
            record = attempts[attempt_number - 1]
        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise PolicyError(f"cannot finalize development attempt ledger: {exc}") from exc
        record["state"] = state
        record["finished_at_utc"] = finished_at_utc
        record["post_source_fingerprint"] = post_fingerprint
        _atomic_json(ledger_path, ledger)


def _registered_worktree(
    worktree_id: str,
    target: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, Path, dict[str, Any], str]:
    try:
        entry = policy["worktrees"][worktree_id]
    except KeyError as exc:
        raise PolicyError("unknown registered worktree") from exc
    root = Path(entry["root"]).resolve(strict=True)
    git_root = Path(entry["git_root"]).resolve(strict=True)
    if root != git_root:
        raise PolicyError("registered worktree/Git root identity changed")
    source_root = (root / entry["source_root"]).resolve(strict=True)
    expected_init = (source_root / "solveur" / "__init__.py").resolve(strict=True)
    if not _is_within(source_root, root) or not expected_init.is_file():
        raise PolicyError("registered solver package is missing or outside its source root")
    test_module = (root / target.split("::", maxsplit=1)[0]).resolve(strict=True)
    test_root = (root / entry["pytest_root"]).resolve(strict=True)
    if not _is_within(test_module, test_root) or not test_module.is_file():
        raise PolicyError("registered test module is missing or escaped its worktree")
    identity = _git_identity(
        root,
        expected_branch=entry["branch"],
        baseline_commit=entry["baseline_commit"],
    )
    if entry.get("require_clean_worktree") and identity["status_short"]:
        raise PolicyError("registered D01 source worktree must be clean before preflight or FEM execution")
    fingerprint = _worktree_source_fingerprint(root, target)
    return entry, root, source_root, identity, fingerprint


def _run_root(policy: Mapping[str, Any]) -> Path:
    root = (ROOT / policy["run_store"]).resolve()
    if not _is_within(root, ROOT.resolve()) or _is_within(root, (ROOT / "qualification").resolve()):
        raise PolicyError("development run store must be inside the worktree and outside qualification")
    return root


def _node_ledger_context(
    policy: Mapping[str, Any],
    store: Path,
    worktree_id: str,
) -> tuple[Path, Path, str, dict[str, str] | None]:
    entry = policy["worktrees"][worktree_id]
    if worktree_id != "d01" or "node_attempt_ledger" not in entry:
        return (
            store / "node-attempt-ledger.json",
            store / "node-attempt-ledger.lock",
            str(policy["mandate_id"]),
            None,
        )

    config = entry["node_attempt_ledger"]
    predecessor = dict(config["predecessor"])
    predecessor_path = (store / predecessor["path"]).resolve()
    if not _is_within(predecessor_path, store.resolve()) or not predecessor_path.is_file():
        raise PolicyError("the historical D01 ledger predecessor is missing or outside the run store")
    predecessor_hash = _sha256(predecessor_path)
    if predecessor_hash != predecessor["sha256"]:
        raise PolicyError("the historical D01 ledger changed; refusing to start a new envelope")
    try:
        historical = json.loads(predecessor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"the historical D01 ledger is unreadable: {exc}") from exc
    if (
        not isinstance(historical, dict)
        or historical.get("schema") != "qfsolver-development-node-ledger-v1"
        or historical.get("mandate_id") != predecessor["mandate_id"]
        or not isinstance(historical.get("entries"), dict)
    ):
        raise PolicyError("the historical D01 ledger does not match its declared predecessor identity")
    historical_m3_key = f"{predecessor['mandate_id']}:d01:{D01_NATIVE_NODEIDS[2]}"
    historical_m3 = historical["entries"].get(historical_m3_key)
    if not isinstance(historical_m3, list) or len(historical_m3) != 3:
        raise PolicyError("the historical ledger does not contain exactly three preserved M3 attempts")
    ledger_path = (store / config["path"]).resolve()
    if not _is_within(ledger_path, store.resolve()) or ledger_path == predecessor_path:
        raise PolicyError("the new D01 ledger must be separate from the historical ledger")
    return (
        ledger_path,
        ledger_path.with_suffix(".lock"),
        str(entry["development_mandate_id"]),
        predecessor,
    )


def _series_root(store: Path, scope_name: str, worktree_id: str | None) -> Path:
    if worktree_id is not None:
        if worktree_id not in {"d01", "c01", "e01"}:
            raise PolicyError("unknown worktree output namespace")
        return store / "worktrees" / worktree_id
    if scope_name not in STANDARD_SCOPES:
        raise PolicyError("standard output namespace requires a fixed local test scope")
    return store / "standard" / scope_name


def _controller_provenance() -> dict[str, Any]:
    files = {
        "runner": Path(__file__).resolve(),
        "pytest_plugin": Path(__file__).with_name("development_autonomous_pytest_plugin.py").resolve(),
        "policy": POLICY_PATH.resolve(),
    }
    return {
        "identity": _git_identity(ROOT),
        "sha256": {name: _sha256(path) for name, path in files.items()},
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "pytest_version": importlib.metadata.version("pytest"),
            "psutil_version": importlib.metadata.version("psutil") if psutil is not None else None,
        },
    }


def _preflight_directory(store: Path, worktree_id: str, preflight_id: str) -> Path:
    if not PREFLIGHT_RE.fullmatch(preflight_id):
        raise PolicyError("preflight ID must use the generated pf-<12 lowercase hex> format")
    directory = (store / "worktrees" / worktree_id / "preflight" / preflight_id).resolve()
    if not _is_within(directory, store.resolve()):
        raise PolicyError("preflight evidence path escapes the development run store")
    return directory


def preflight_pytest(
    worktree_id: str,
    target: str,
    preflight_id: str | None = None,
) -> dict[str, Any]:
    """Collect one exact registered node without reserving a FEM attempt."""
    policy = load_policy()
    if worktree_id != "d01":
        raise PolicyError("collect-only preflight is currently enabled only for the D01 native nodes")
    targets = resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id)
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, policy
    )
    store = _run_root(policy)
    ledger_path, _ledger_lock, mandate_id, predecessor = _node_ledger_context(policy, store, worktree_id)
    if predecessor is None or mandate_id != entry["development_mandate_id"]:
        raise PolicyError("D01 preflight is not bound to its distinct development envelope")
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    inherited = dict(os.environ)
    guard_state = _native_guard_environment(inherited)
    if guard_state["active_markers"]:
        raise PolicyError(
            "D01 preflight refused before collection because explicit no-FEM environment markers are active"
        )
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk for D01 preflight: {free_bytes} bytes; requires {minimum_free}")

    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, worktree_id, preflight_id)
    if receipt_dir.exists():
        raise PolicyError("preflight ID already exists; refusing to overwrite a prior receipt")
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir(parents=True)
    output_dir.mkdir()
    command = build_pytest_command(
        "fem_exploratory",
        targets,
        temporary_dir,
        repository_root=execution_root,
        source_root=source_root,
        controller_root=ROOT,
        allow_native_skip_override=True,
        collect_only=True,
    )
    if "--collect-only" not in command:
        raise PolicyError("D01 readiness preflight must be pytest collect-only")
    environment = build_child_environment(
        temporary_dir,
        base=inherited,
        source_root=source_root,
        d01_source_sha=identity["head"],
    )
    child_guard_state = _validate_native_guard_environment(inherited, environment)
    limits = dict(entry["budgets"])
    limits["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
    started = datetime.now(timezone.utc).isoformat()
    record_path = receipt_dir / "preflight.json"
    initial = {
        "schema": "qfsolver-development-d01-preflight-v1",
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": mandate_id,
        "worktree_id": worktree_id,
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "bodies_executed": False,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "solver_origin_expected": str((source_root / "solveur" / "__init__.py").resolve()),
        "controller_provenance": _controller_provenance(),
        "native_guard_environment": child_guard_state,
        "command": command,
        "budgets": limits,
        "budget_semantics": {
            "wall_timeout": "watchdog-triggered process-tree termination; best-effort OS control",
            "rss": "sampled soft monitor; not a hard memory/commit limit",
            "process_count": "sampled process-tree monitor; not a job-object boundary",
            "captured_output": "application-enforced byte caps on captured stdout/stderr",
            "temporary_and_archive_size": "sampled size monitoring; not an NTFS quota",
        },
        "free_disk_before_bytes": free_bytes,
        "predecessor_ledger": predecessor,
        "predecessor_ledger_sha256_verified": _sha256(store / predecessor["path"]),
    }

    scenario_lock = _exclusive_file_lock(store / "locks" / "fem-exploratory.lock")
    with scenario_lock:
        try:
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temporary_dir,
                limits=limits,
                poll_interval=float(policy["poll_interval_seconds"]),
            )
        except OSError as exc:
            _atomic_json(
                record_path,
                {
                    **initial,
                    "state": "PREFLIGHT_LAUNCH_FAILED",
                    "started_at_utc": started,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "launch_error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise PolicyError(f"D01 collect-only preflight could not launch: {exc}") from exc

    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    combined = stdout + "\n" + stderr
    origin_line = f"QF_DEV_SOLVER_ORIGIN={initial['solver_origin_expected']}"
    collected_exact_node = target in combined.splitlines()
    after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
        worktree_id, target, policy
    )
    if after_identity != identity or after_fingerprint != source_fingerprint or after_entry != entry:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif result.status != "PASS":
        state = "PREFLIGHT_FAILED"
    elif origin_line not in combined:
        state = "PREFLIGHT_WRONG_SOLVER_ORIGIN"
    elif not collected_exact_node:
        state = "PREFLIGHT_NODEID_NOT_CONFIRMED"
    else:
        state = "PREFLIGHT_PASS"
    final = {
        **initial,
        "state": state,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "collected_nodeids": [target] if collected_exact_node else [],
        "solver_origin_observed": origin_line if origin_line in combined else None,
        "return_code": result.return_code,
        "elapsed_seconds": result.elapsed_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "peak_process_count": result.peak_process_count,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "stdout_sha256": _sha256(stdout_path),
        "stderr_sha256": _sha256(stderr_path),
        "archive_bytes": result.archive_bytes,
        "temporary_bytes": result.temporary_bytes,
        "stop_reason": result.stop_reason,
        "identity_after": after_identity,
        "source_fingerprint_after": after_fingerprint,
        "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
    }
    _atomic_json(record_path, final)
    receipt_sha256 = _sha256(record_path)
    _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    return {
        "preflight_id": preflight_id,
        "state": state,
        "bodies_executed": False,
        "nodeid": target if collected_exact_node else None,
        "receipt": str(record_path),
        "receipt_sha256": receipt_sha256,
        "metrics": final,
    }


def _validate_d01_preflight_receipt(
    store: Path,
    preflight_id: str,
    *,
    target: str,
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    guard_state: Mapping[str, Any],
) -> tuple[Path, str]:
    receipt_dir = _preflight_directory(store, "d01", preflight_id)
    record_path = receipt_dir / "preflight.json"
    sha_path = receipt_dir / "preflight.sha256.json"
    if not record_path.is_file() or not sha_path.is_file():
        raise PolicyError("a successful exact-node collect-only preflight receipt is required before reserving FEM")
    try:
        receipt = json.loads(record_path.read_text(encoding="utf-8"))
        sidecar = json.loads(sha_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"D01 preflight receipt is unreadable: {exc}") from exc
    actual_hash = _sha256(record_path)
    if sidecar.get("sha256") != actual_hash:
        raise PolicyError("D01 preflight receipt checksum mismatch")
    if (
        receipt.get("schema") != "qfsolver-development-d01-preflight-v1"
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("bodies_executed") is not False
        or receipt.get("target") != target
        or receipt.get("preflight_id") != preflight_id
        or receipt.get("identity") != dict(identity)
        or receipt.get("source_fingerprint") != source_fingerprint
        or receipt.get("controller_provenance") != dict(controller_provenance)
        or receipt.get("native_guard_environment") != dict(guard_state)
        or receipt.get("solver_origin_observed") != receipt.get("solver_origin_expected")
        or receipt.get("collected_nodeids") != [target]
    ):
        raise PolicyError("D01 preflight does not match this exact source, controller, environment and nodeid")
    return record_path, actual_hash


def run_pytest(
    scope_name: str,
    target: str | None,
    series_id: str | None,
    *,
    worktree_id: str | None = None,
    reason: str | None = None,
    preflight_id: str | None = None,
    attempt_basis: str | None = None,
    hypothesis_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    policy = load_policy()
    is_registered = scope_name in WORKTREE_SCOPES
    targets = resolve_targets(scope_name, target, policy, worktree_id=worktree_id)
    entry: dict[str, Any] | None = None
    source_root: Path | None = None
    source_fingerprint: str | None = None
    ledger_context: tuple[Path, Path, str, dict[str, str] | None] | None = None
    if is_registered:
        if not worktree_id or not target or not reason or not reason.strip():
            raise PolicyError("registered worktree tests require one exact target, worktree, and documented reason")
        entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
            worktree_id,
            target,
            policy,
        )
        scope = dict(entry["budgets"])
        attempt_limit = int(entry.get("attempt_limits_per_nodeid", {}).get(target, entry["attempt_limit_per_nodeid"]))
        if worktree_id == "d01":
            if preflight_id is None:
                raise PolicyError("D01 FEM attempts require a successful exact-node collect-only preflight first")
            if attempt_basis not in D01_ATTEMPT_BASES:
                raise PolicyError("D01 FEM attempts require a classified attempt basis")
            ledger_context = _node_ledger_context(policy, _run_root(policy), worktree_id)
        elif preflight_id is not None:
            raise PolicyError("preflight receipt IDs are supported only for the D01 development envelope")
    else:
        execution_root = ROOT
        scope = policy["standard_scopes"][scope_name]
        identity = _git_identity(ROOT)
        attempt_limit = int(scope["max_attempts_per_series"])
    if is_registered and scope_name == "fem_exploratory":
        # The lock is shared by D01 and C01: at most one exploratory FEM/test
        # scenario started through this policy can be active at a time.
        scenario_lock = _exclusive_file_lock(_run_root(policy) / "locks" / "fem-exploratory.lock")
    else:
        scenario_lock = nullcontext()
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk: {free_bytes} bytes; requires {minimum_free}")
    inherited_environment = dict(os.environ)
    inherited_native_guard = _native_guard_environment(inherited_environment)
    if (
        worktree_id == "d01"
        and entry is not None
        and entry["allow_native_vv_skip_override"]
        and inherited_native_guard["active_markers"]
    ):
        markers = ", ".join(inherited_native_guard["active_markers"])
        raise PolicyError(
            "D01 native development is refused before reserving an attempt because explicit no-FEM "
            f"environment markers are active: {markers}"
        )
    if series_id is None:
        series_id = f"dev-{uuid.uuid4().hex[:12]}"
    if not SERIES_RE.fullmatch(series_id):
        raise PolicyError("series ID must use the development-only format dev-<lowercase-id>")
    store = _run_root(policy)
    series_dir = _series_root(store, scope_name, worktree_id) / series_id
    preflight_receipt: tuple[Path, str] | None = None
    controller_provenance = _controller_provenance()
    if worktree_id == "d01":
        assert preflight_id is not None and source_fingerprint is not None and target is not None
        preflight_receipt = _validate_d01_preflight_receipt(
            store,
            preflight_id,
            target=target,
            identity=identity,
            source_fingerprint=source_fingerprint,
            controller_provenance=controller_provenance,
            guard_state=_native_guard_environment(inherited_environment),
        )
    with scenario_lock:
        number, attempt_dir = _next_attempt(
            series_dir,
            series_id,
            scope_name,
            attempt_limit,
            worktree_id=worktree_id,
            target=targets[0] if is_registered else (target or "<scope>"),
        )
        node_ledger_path, node_ledger_lock, effective_mandate_id, ledger_predecessor = (
            ledger_context
            if ledger_context is not None
            else (
                store / "node-attempt-ledger.json",
                store / "node-attempt-ledger.lock",
                str(policy["mandate_id"]),
                None,
            )
        )
        ledger_key: str | None = None
        ledger_number: int | None = None
        if is_registered:
            assert worktree_id is not None and source_fingerprint is not None and reason is not None and target is not None
            try:
                ledger_key, ledger_number = _reserve_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    mandate_id=effective_mandate_id,
                    worktree_id=worktree_id,
                    target=target,
                    series_id=series_id,
                    source_fingerprint=source_fingerprint,
                    reason=reason.strip(),
                    maximum=attempt_limit,
                    predecessor=ledger_predecessor,
                    controller_fingerprint=_stable_fingerprint(controller_provenance),
                    attempt_basis=attempt_basis,
                    hypothesis_id=hypothesis_id,
                )
            except Exception:
                attempt_dir.rmdir()
                raise
        temp_dir = attempt_dir / "tmp"
        output_dir = attempt_dir / "output"
        temp_dir.mkdir()
        output_dir.mkdir()
        command = build_pytest_command(
            scope_name,
            targets,
            temp_dir,
            repository_root=execution_root,
            source_root=source_root,
            controller_root=ROOT,
            allow_native_skip_override=bool(entry and entry["allow_native_vv_skip_override"]),
            junit_xml_path=(output_dir / "pytest-results.xml") if worktree_id == "d01" else None,
        )
        environment = build_child_environment(
            temp_dir,
            base=inherited_environment,
            source_root=source_root,
            d01_source_sha=identity["head"] if worktree_id == "d01" else None,
        )
        child_native_guard = _validate_native_guard_environment(inherited_environment, environment)
        started_at = datetime.now(timezone.utc).isoformat()
        initial: dict[str, Any] = {
            "schema": "qfsolver-development-attempt-v2",
            "mode": "DEVELOPMENT_AUTONOMOUS",
            "mandate_id": effective_mandate_id,
            "series_id": series_id,
            "attempt": ledger_number or number,
            "scope": scope_name,
            "worktree_id": worktree_id,
            "target": targets,
            "reason": reason.strip() if reason else None,
            "attempt_basis": attempt_basis,
            "hypothesis_id": hypothesis_id,
            "state": "RUNNING",
            "started_at_utc": started_at,
            "identity": identity,
            "controller_provenance": controller_provenance,
            "source_fingerprint": source_fingerprint,
            "solver_import_root": str(source_root.resolve()) if source_root else None,
            "solver_origin_expected": str((source_root / "solveur" / "__init__.py").resolve()) if source_root else None,
            "native_guard_environment": child_native_guard,
            "preflight_receipt": (
                {"path": str(preflight_receipt[0]), "sha256": preflight_receipt[1]}
                if preflight_receipt is not None
                else None
            ),
            "command": command,
            "budgets": dict(scope),
            "budget_semantics": {
                "wall_timeout": "watchdog-triggered process-tree termination; best-effort OS control",
                "rss": "sampled soft monitor; not a hard memory/commit limit",
                "process_count": "sampled process-tree monitor; not a job-object boundary",
                "captured_output": "application-enforced byte caps on captured stdout/stderr",
                "temporary_and_archive_size": "sampled size monitoring; not an NTFS quota",
                "free_disk": "preflight and sampled floor check",
                "attempt_limit": "persistent procedural ledger under the development run store",
            },
            "free_disk_before_bytes": free_bytes,
            "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
            "qualification_promotion": "PROHIBITED",
        }
        record_path = attempt_dir / "run.json"
        _atomic_json(record_path, initial)
        limits = dict(scope)
        limits["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
        try:
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temp_dir,
                limits=limits,
                poll_interval=float(policy["poll_interval_seconds"]),
            )
        except OSError as exc:
            finished_at = datetime.now(timezone.utc).isoformat()
            post_fingerprint = _worktree_source_fingerprint(execution_root, target) if is_registered and target else "NOT_CAPTURED"
            final = {
                **initial,
                "state": "LAUNCH_FAILED",
                "finished_at_utc": finished_at,
                "launch_error": f"{type(exc).__name__}: {exc}",
                "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
                "temporary_bytes": _directory_size(temp_dir),
                "output_inventory": _file_inventory(output_dir),
            }
            _atomic_json(record_path, final)
            if ledger_key and ledger_number:
                _complete_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    key=ledger_key,
                    attempt_number=ledger_number,
                    state="LAUNCH_FAILED",
                    finished_at_utc=finished_at,
                    post_fingerprint=post_fingerprint,
                )
            return {"series_id": series_id, "attempt": ledger_number or number, "state": "LAUNCH_FAILED", "record": str(record_path)}, 1
        finished_at = datetime.now(timezone.utc).isoformat()
        post_fingerprint = source_fingerprint
        state = result.status
        if is_registered and target:
            try:
                post_fingerprint = _worktree_source_fingerprint(execution_root, target)
            except PolicyError:
                post_fingerprint = "UNAVAILABLE"
            if post_fingerprint != source_fingerprint:
                state = "SOURCE_CHANGED_DURING_RUN"
        result_payload_complete = None
        result_payload_errors: list[str] = []
        result_payload_metadata: dict[str, Any] | None = None
        if worktree_id == "d01" and target is not None:
            result_payload_complete, result_payload_errors, result_payload_metadata = _validate_d01_junit_payload(
                output_dir / "pytest-results.xml",
                target,
                identity["head"],
                result.return_code,
            )
            state = _d01_final_state(state, result_payload_complete)
        final = {
            **initial,
            "state": state,
            "finished_at_utc": finished_at,
            "return_code": result.return_code,
            "elapsed_seconds": result.elapsed_seconds,
            "peak_rss_bytes": result.peak_rss_bytes,
            "peak_process_count": result.peak_process_count,
            "stdout_bytes": result.stdout_bytes,
            "stderr_bytes": result.stderr_bytes,
            "stdout_sha256": _sha256(output_dir / "stdout.log"),
            "stderr_sha256": _sha256(output_dir / "stderr.log"),
            "output_inventory": _file_inventory(output_dir),
            "result_payload_complete": result_payload_complete,
            "result_payload_errors": result_payload_errors,
            "result_payload_metadata": result_payload_metadata,
            "archive_bytes": result.archive_bytes,
            "temporary_bytes": result.temporary_bytes,
            "post_source_fingerprint": post_fingerprint,
            "stop_reason": result.stop_reason,
            "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
        }
        _atomic_json(record_path, final)
        if ledger_key and ledger_number:
            _complete_node_attempt(
                node_ledger_path,
                node_ledger_lock,
                key=ledger_key,
                attempt_number=ledger_number,
                state=state,
                finished_at_utc=finished_at,
                post_fingerprint=post_fingerprint,
            )
        return {
            "series_id": series_id,
            "attempt": ledger_number or number,
            "state": state,
            "record": str(record_path),
            "metrics": final,
        }, (0 if state == "PASS" else 1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight_parser = subparsers.add_parser(
        "preflight",
        help="collect one exact D01 native node without running its test body or consuming an attempt",
    )
    preflight_parser.add_argument("--worktree", choices=("d01",), required=True)
    preflight_parser.add_argument("--target", required=True)
    preflight_parser.add_argument("--preflight-id", help="optional unused pf-<12 lowercase hex> ID")
    test_parser = subparsers.add_parser("test", help="run one fixed development pytest scope")
    test_parser.add_argument("--scope", choices=("unit", "integration", "fem_exploratory", "math_non_fem"), required=True)
    test_parser.add_argument("--target", help="repository-relative test file/nodeid; FEM requires an exact approved nodeid")
    test_parser.add_argument("--series", help="development-only dev-* series ID for bounded follow-up attempts")
    test_parser.add_argument("--worktree", help="registered worktree ID (d01, c01, e01) for an exact development nodeid")
    test_parser.add_argument("--reason", help="short documented development hypothesis/reason for a registered nodeid attempt")
    test_parser.add_argument("--preflight-id", help="successful exact-node D01 collect-only receipt ID")
    test_parser.add_argument("--attempt-basis", choices=D01_ATTEMPT_BASES, help="D01 baseline/change/hypothesis classification")
    test_parser.add_argument("--hypothesis-id", help="unique ID required for a same-input new diagnostic hypothesis")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            result = preflight_pytest(args.worktree, args.target, args.preflight_id)
            exit_code = 0 if result["state"] == "PREFLIGHT_PASS" else 1
        else:
            result, exit_code = run_pytest(
                args.scope,
                args.target,
                args.series,
                worktree_id=args.worktree,
                reason=args.reason,
                preflight_id=args.preflight_id,
                attempt_basis=args.attempt_basis,
                hypothesis_id=args.hypothesis_id,
            )
    except PolicyError as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
