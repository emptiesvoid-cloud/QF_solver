"""Process supervision, exact pytest selection, and non-overwriting receipt I/O."""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .manifest import LocalVVError, RESULT_MARKER, _checkout_path, _execution_environment, load_json, sha256_file


def _junit_cases(path: Path) -> list[ET.Element]:
    root = ET.parse(path).getroot()
    if root.tag == "testsuite":
        return list(root.iter("testcase"))
    if root.tag == "testsuites":
        return list(root.iter("testcase"))
    raise LocalVVError(f"unrecognized JUnit root element: {root.tag}")


def classify_junit(
    junit_path: Path,
    expected_nodeid: str,
    selected_nodeids: list[str] | None,
    exit_code: int | None,
    *,
    timed_out: bool = False,
    interrupted: bool = False,
) -> str:
    if interrupted:
        return "INTERRUPTED"
    if timed_out:
        return "TIMEOUT"
    if selected_nodeids != [expected_nodeid]:
        return "INFRA_ERROR"
    if not junit_path.is_file():
        return "INFRA_ERROR"
    try:
        cases = _junit_cases(junit_path)
    except (ET.ParseError, LocalVVError, OSError):
        return "INFRA_ERROR"
    expected_name = expected_nodeid.split("::", maxsplit=1)[1]
    if len(cases) != 1 or cases[0].get("name") != expected_name:
        return "INFRA_ERROR"
    testcase = cases[0]
    if testcase.find("failure") is not None:
        return "FAIL"
    if testcase.find("error") is not None:
        return "INFRA_ERROR"
    if testcase.find("skipped") is not None:
        return "INCONCLUSIVE"
    if exit_code == 0:
        return "PYTEST_PASS_ONLY"
    return "INFRA_ERROR"


def extract_numeric_payload(stdout_path: Path) -> tuple[str, dict[str, Any] | None]:
    marked_lines = [
        line
        for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith(RESULT_MARKER)
    ]
    if not marked_lines:
        return "NOT_EXPOSED", None
    if len(marked_lines) != 1:
        raise LocalVVError("stdout must contain at most one structured numeric result marker")
    payload = json.loads(
        marked_lines[0][len(RESULT_MARKER) :],
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )
    if not isinstance(payload, dict):
        raise LocalVVError("numeric result marker must contain a JSON object")
    if not isinstance(payload.get("schema"), str) or not payload["schema"]:
        raise LocalVVError("numeric result marker must declare a non-empty schema")
    if not isinstance(payload.get("case_id"), str) or not payload["case_id"]:
        raise LocalVVError("numeric result marker must declare a non-empty case_id")
    return "EXPOSED_JSON", payload


def supervise_process(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
    output_limit_bytes: int,
) -> dict[str, Any]:
    if not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
        raise LocalVVError("invalid argument vector")
    if not stdout_path.parent.is_dir() or not stderr_path.parent.is_dir():
        raise LocalVVError("log directory was not prepared")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    started = time.monotonic()
    timed_out = False
    output_limited = False
    interrupted = False
    process: subprocess.Popen[bytes] | None = None
    with stdout_path.open("xb") as stdout_stream, stderr_path.open("xb") as stderr_stream:
        try:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
                shell=False,
                close_fds=True,
                creationflags=creationflags,
            )
            while process.poll() is None:
                if time.monotonic() - started > timeout_seconds:
                    timed_out = True
                    break
                if stdout_path.stat().st_size > output_limit_bytes or stderr_path.stat().st_size > output_limit_bytes:
                    output_limited = True
                    break
                time.sleep(0.05)
        except KeyboardInterrupt:
            interrupted = True
        finally:
            if process is not None and process.poll() is None:
                try:
                    if os.name == "nt":
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        process.wait(timeout=1.0)
                    else:
                        process.terminate()
                        process.wait(timeout=1.0)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait()
    if stdout_path.stat().st_size > output_limit_bytes or stderr_path.stat().st_size > output_limit_bytes:
        output_limited = True
    return {
        "exit_code": process.returncode if process is not None and process.poll() is not None else None,
        "timed_out": timed_out,
        "output_limited": output_limited,
        "interrupted": interrupted,
        "duration_seconds": round(time.monotonic() - started, 6),
        "stdout_bytes": stdout_path.stat().st_size,
        "stderr_bytes": stderr_path.stat().st_size,
    }


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _check_evidence_root(manifest: dict[str, Any]) -> Path:
    requested_root = Path(manifest["evidence_root"])
    if not requested_root.is_absolute():
        raise LocalVVError("evidence root is not absolute")
    current = Path(requested_root.anchor)
    for part in requested_root.parts[1:]:
        current = current / part
        if current.exists():
            attributes = getattr(current.stat(), "st_file_attributes", 0)
            if current.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise LocalVVError(f"evidence path crosses a symlink/reparse point: {current}")
    evidence_root = requested_root.resolve(strict=False)
    for key in ("science", "runner", "tests"):
        checkout = _checkout_path(manifest, key)
        if evidence_root == checkout or evidence_root.is_relative_to(checkout):
            raise LocalVVError("evidence root must be outside every checkout")
    current = Path(evidence_root.anchor)
    for part in evidence_root.parts[1:]:
        current = current / part
        if current.exists():
            attributes = getattr(current.stat(), "st_file_attributes", 0)
            if current.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise LocalVVError(f"evidence path crosses a symlink/reparse point: {current}")
    return evidence_root


def _write_hash_inventory(directory: Path) -> list[dict[str, str]]:
    inventory = []
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    for file_path in files:
        attributes = getattr(file_path.stat(), "st_file_attributes", 0)
        if file_path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise LocalVVError(f"evidence output contains a symlink/reparse point: {file_path}")
        inventory.append({"path": file_path.relative_to(directory).as_posix(), "sha256": sha256_file(file_path)})
    return inventory


def _read_selection(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data, _ = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    nodeids = data.get("collected_nodeids")
    if not isinstance(nodeids, list) or not all(isinstance(item, str) for item in nodeids):
        return None
    if data.get("exact_match") is not True or data.get("source_import_ok") is not True:
        return None
    if not isinstance(data.get("source_import"), str):
        return None
    return data


def _case_command(
    manifest: dict[str, Any], case: dict[str, Any], run_dir: Path
) -> tuple[list[str], Path, dict[str, str]]:
    science_root = _checkout_path(manifest, "science")
    tests_root = _checkout_path(manifest, case.get("test_checkout", "tests"))
    runner_root = _checkout_path(manifest, "runner")
    python = manifest["environment"]["python"]["executable"]
    junit = run_dir / "junit.xml"
    argv = [
        python,
        "-m",
        "pytest",
        "-q",
        "-s",
        "--noconftest",
        "-p",
        "no:cacheprovider",
        "-p",
        "local_vv_pytest_plugin",
        "-c",
        str(tests_root / "pyproject.toml"),
        "-o",
        "pythonpath=",
        "-o",
        "addopts=",
        f"--junitxml={junit}",
        case["nodeid"],
    ]
    environment = _execution_environment(manifest, run_dir)
    environment["PYTHONPATH"] = os.pathsep.join((str(science_root / "src"), str(runner_root / "scripts")))
    environment["QF_LOCAL_VV_EXPECTED_NODEID"] = case["nodeid"]
    return argv, tests_root, environment
