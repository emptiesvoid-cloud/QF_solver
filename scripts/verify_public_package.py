"""Build and inspect an explicit frozen package candidate, never a release."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tarfile
import time
import zipfile
from datetime import datetime, timezone
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

if __package__:
    from scripts.git_tools import git_run
    from scripts.plan_public_package import _relative_path, package_input_gaps, scan_selected_payloads, select_paths
else:
    from git_tools import git_run
    from plan_public_package import (
        _relative_path, package_input_gaps, scan_selected_payloads, select_paths,
    )


REQUIRED_TOOLS = frozenset({
    "scripts/verify_public_package.py", "scripts/probe_installed_package.py", "scripts/plan_public_package.py",
    "scripts/git_tools.py", "scripts/audit_public_release.py", "scripts/audit_release_archive.py",
    "scripts/review_vocabulary.py",
})


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_record(path: Path, record: Any) -> None:
    """Write generated evidence with immediate flush; never replace a raw input."""
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def frozen_inputs(root: Path, contract_path: Path) -> tuple[dict[str, Any], dict[str, bytes], list[dict[str, Any]], str]:
    """Verify a prospective, clean source/contract lineage before any build."""
    head = git_run(["rev-parse", "HEAD"], cwd=root, check=True, text=True).stdout.strip()
    relative = contract_path.resolve(strict=True).relative_to(root.resolve()).as_posix()
    committed = git_run(["show", f"{head}:{relative}"], cwd=root, check=True).stdout
    current = contract_path.read_bytes()
    if current != committed and current.replace(b"\r\n", b"\n") != committed:
        raise ValueError("The execution contract differs from its committed bytes.")
    if git_run(["status", "--porcelain", "--untracked-files=all"], cwd=root, check=True).stdout.strip():
        raise ValueError("The candidate checkout must be clean before execution.")
    contract = json.loads(committed)
    required = {
        "status": "FROZEN_CANDIDATE_BUILD", "package_build_allowed": True,
        "publication_allowed": False, "structural_solves_allowed": False,
        "whole_repository_gate_waivers_allowed": False,
    }
    if any(contract.get(key) != value for key, value in required.items()):
        raise ValueError("The contract does not authorize this bounded candidate build.")
    source = contract["source_sha"]
    if len(source) != 40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("An exact source commit is required.")
    if git_run(["merge-base", "--is-ancestor", source, head], cwd=root).returncode:
        raise ValueError("The frozen source is not an ancestor of the execution commit.")
    contract_commit = git_run(["log", "-1", "--format=%H", head, "--", relative], cwd=root, check=True, text=True).stdout.strip()
    if source == contract_commit or git_run(["merge-base", "--is-ancestor", source, contract_commit], cwd=root).returncode:
        raise ValueError("The contract must be frozen prospectively after the source commit.")
    if set(contract["tool_bindings"]) != REQUIRED_TOOLS:
        raise ValueError("Every build, probe and strict-scan tool must be bound explicitly.")
    # Later evidence commits may be present, but the frozen build code cannot drift.
    rows: dict[str, tuple[str, str]] = {}
    for entry in git_run(["ls-tree", "-r", "-z", source], cwd=root, check=True).stdout.split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            mode, kind, blob = metadata.decode().split()
            rows[name.decode()] = (mode if kind == "blob" else kind, blob)
    selected = select_paths(rows, contract["selection"])
    paths = [*selected, *contract["tool_bindings"]]
    if git_run(["diff", "--name-only", source, head, "--", *paths], cwd=root, check=True).stdout.strip():
        raise ValueError("Selected sources or build tools changed after the frozen source.")
    for path, expected in contract["tool_bindings"].items():
        _relative_path(path)
        payload = git_run(["show", f"{source}:{path}"], cwd=root, check=True).stdout
        if digest(payload) != expected:
            raise ValueError(f"Tool binding mismatch: {path}")
    payloads = {path: git_run(["cat-file", "blob", rows[path][1]], cwd=root, check=True).stdout for path in selected}
    if package_input_gaps(payloads, source_paths=list(rows)):
        raise ValueError("Required package metadata inputs are missing from the selection.")
    if scan_selected_payloads(payloads)["status"] != "PASS":
        raise ValueError("The strict selected-source scan failed.")
    metadata = tomllib.loads(payloads["pyproject.toml"].decode())
    if metadata["project"]["version"] != contract["package_version"]:
        raise ValueError("Package version does not match the frozen contract.")
    mapping = [{"path": path, "mode": rows[path][0], "git_blob": rows[path][1],
                "sha256": digest(payloads[path]), "bytes": len(payloads[path])} for path in selected]
    return contract | {"contract_sha256": digest(committed)}, payloads, mapping, head


def archive_payloads(path: Path, *, wheel: bool) -> dict[str, bytes]:
    """Reject archive aliases, duplicate paths and non-regular file entries."""
    result: dict[str, bytes] = {}
    folded: set[str] = set()
    if wheel:
        with zipfile.ZipFile(path) as archive:
            entries = [(item.filename, archive.read(item), (item.external_attr >> 16) & 0o170000)
                       for item in archive.infolist() if not item.is_dir()]
        entries = [(name, payload, mode in (0, 0o100000)) for name, payload, mode in entries]
    else:
        with tarfile.open(path, "r:gz") as archive:
            entries = []
            for item in archive.getmembers():
                if item.isdir():
                    continue
                if not item.isfile():
                    raise ValueError("A source archive contains a non-regular entry.")
                stream = archive.extractfile(item)
                if stream is None:
                    raise ValueError("A source archive member cannot be read.")
                member_path = PurePosixPath(item.name)
                if len(member_path.parts) < 2:
                    raise ValueError("A source archive requires a single top-level directory.")
                entries.append((member_path.relative_to(member_path.parts[0]).as_posix(), stream.read(), True))
            roots = {PurePosixPath(item.name).parts[0] for item in archive.getmembers()}
            if len(roots) != 1:
                raise ValueError("A source archive contains multiple top-level directories.")
    for name, payload, regular in entries:
        _relative_path(name)
        if not regular or name.casefold() in folded:
            raise ValueError("An archive contains duplicate, colliding or non-regular entries.")
        folded.add(name.casefold())
        result[name] = payload
    return result


def verify_archives(dist: Path, selected: dict[str, bytes], version: str) -> dict[str, Any]:
    wheels, sources = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Exactly one wheel and one source distribution are required.")
    wheel, sdist = archive_payloads(wheels[0], wheel=True), archive_payloads(sources[0], wheel=False)
    missing = [name for name, payload in selected.items() if sdist.get(name) != payload]
    modules = {name.removeprefix("src/"): payload for name, payload in selected.items() if name.startswith("src/")}
    missing.extend(name for name, payload in modules.items() if wheel.get(name) != payload)
    metadata_paths = [name for name in wheel if name.endswith(".dist-info/METADATA")]
    if len(metadata_paths) != 1 or BytesParser().parsebytes(wheel[metadata_paths[0]])["Version"] != version:
        raise ValueError("Wheel metadata version mismatch.")
    if BytesParser().parsebytes(sdist.get("PKG-INFO", b""))["Version"] != version:
        raise ValueError("Source metadata version mismatch.")
    for name, payload in selected.items():
        if name.startswith(("examples/", "qualification/", "requirements/")):
            matches = [data for path, data in wheel.items() if path.endswith(".data/data/" + name)]
            if matches != [payload]:
                missing.append(name)
    generated_sdist = {"PKG-INFO", "setup.cfg"} | {
        "src/qf_solver.egg-info/" + name for name in (
            "PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt", "requires.txt", "top_level.txt",
        )
    }
    extras = sorted(set(sdist) - selected.keys() - generated_sdist)
    unexpected_wheel = [name for name in wheel if name not in modules
                        and not name.startswith(("qf_solver-" + version + ".dist-info/", "qf_solver-" + version + ".data/data/"))]
    data_inputs = {name for name in selected if name.startswith(("examples/", "qualification/", "requirements/"))}
    for name in wheel:
        if ".data/data/" in name and name.split(".data/data/", 1)[1] not in data_inputs:
            unexpected_wheel.append(name)
    scans = {"wheel": scan_selected_payloads(wheel), "sdist": scan_selected_payloads(sdist)}
    if missing or extras or unexpected_wheel or any(scan["status"] != "PASS" for scan in scans.values()):
        raise ValueError(f"Package content mismatch: missing={missing}, sdist extras={extras}, wheel extras={unexpected_wheel}, scans={scans}")
    return {"status": "PASS", "wheel": wheels[0].name, "sdist": sources[0].name,
            "selected_files": len(selected), "wheel_modules": len(modules), "scans": scans,
            "binaries": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
                         for path in [wheels[0], sources[0]]]}


def run_command(command: list[str], cwd: Path, logs: Path, records: list[dict[str, Any]], *, expected: int = 0) -> None:
    """Record actual arguments, PID, UTC, exit and immediately preserved logs."""
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(key, None)
    number = len(records) + 1
    out, err = logs / f"{number:02d}.stdout.log", logs / f"{number:02d}.stderr.log"
    record: dict[str, Any] = {"command": command, "cwd": str(cwd), "started_utc": utc(), "expected_exit_code": expected}
    started = time.monotonic()
    with out.open("xb") as stdout, err.open("xb") as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr)
        record["pid"] = process.pid
        records.append(record)
        write_record(logs.parent / "commands.json", records)
        record["exit_code"] = process.wait()
        stdout.flush()
        stderr.flush()
    record.update({"ended_utc": utc(), "wall_seconds": time.monotonic() - started,
                   "stdout": {"path": out.name, "sha256": digest(out.read_bytes()), "bytes": out.stat().st_size},
                   "stderr": {"path": err.name, "sha256": digest(err.read_bytes()), "bytes": err.stat().st_size}})
    write_record(logs.parent / "commands.json", records)
    if record["exit_code"] != expected:
        raise ValueError(f"Candidate command {number} returned {record['exit_code']} instead of {expected}; raw logs preserved.")


_PORTABLE_SAFE_PATH_BOOTSTRAP = "\n".join((
    "import sys",
    "from pathlib import Path",
    "probe = Path(sys.argv[1]).resolve(strict=True)",
    "checkout = probe.parent.parent.resolve(strict=True)",
    "cwd = Path.cwd().resolve()",
    "blocked = (checkout, cwd)",
    "def allowed(entry):",
    "    if not entry:",
    "        return False",
    "    candidate = Path(entry).resolve()",
    "    return not any(candidate == parent or parent in candidate.parents for parent in blocked)",
    "sys.path[:] = [entry for entry in sys.path if allowed(entry)]",
    "del sys.argv[1]",
    "sys.argv[0] = str(probe)",
    "namespace = {'__name__': '__main__', '__file__': str(probe)}",
    "exec(compile(probe.read_bytes(), str(probe), 'exec'), namespace)",
))


def installed_probe_command(python: Path, probe: Path, mapping: Path, version: str, output: Path) -> list[str]:
    """Exclude checkout/cwd imports while retaining declared dependency paths.

    Python 3.11+'s ``-P`` provides safe-path startup. Python 3.10 uses a ``-c``
    bootstrap that removes the checkout and current directory from ``sys.path``
    before executing the probe, without enabling isolated mode or hiding site
    packages. The probe independently verifies its import origin and source
    bytes in either mode.
    """
    arguments = ["--mapping", str(mapping), "--version", version, "--output", str(output)]
    if sys.version_info >= (3, 11):
        return [str(python), "-P", str(probe), *arguments]
    if sys.version_info < (3, 10):
        raise ValueError("The package audit runner requires Python 3.10+ for safe-path probes.")
    return [str(python), "-c", _PORTABLE_SAFE_PATH_BOOTSTRAP, str(probe), *arguments]


def run_candidate(root: Path, contract_path: Path, output: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output) or output.exists():
        raise ValueError("Use a new external artifact directory; existing outputs are never overwritten.")
    contract, payloads, mapping, head = frozen_inputs(root, contract_path)
    output.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    result: dict[str, Any] = {"status": "RUNNING", "source_sha": contract["source_sha"], "execution_sha": head,
                              "contract_sha256": contract["contract_sha256"], "started_utc": utc(),
                              "whole_repository_gates_changed": False, "publication_performed": False,
                              "structural_solves_run": False, "ledger_changed": False, "release_version_claim": False,
                              "runtime": {"python": sys.version, "executable": sys.executable,
                                          "build": importlib.metadata.version("build"),
                                          "setuptools": importlib.metadata.version("setuptools"),
                                          "wheel": importlib.metadata.version("wheel")}}
    write_record(output / "result.json", result)
    try:
        stage, logs, dist, neutral = [output / name for name in ("selected_source", "logs", "dist", "outside_checkout")]
        for path in (stage, logs, dist, neutral):
            path.mkdir()
        for row in mapping:
            path = stage / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payloads[row["path"]])
            if os.name != "nt":
                path.chmod(0o755 if row["mode"] == "100755" else 0o644)
        write_record(output / "source_mapping.json", mapping)
        run_command([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist), str(stage)], neutral, logs, records)
        packages = verify_archives(dist, payloads, contract["package_version"])
        write_record(output / "package_check.json", packages)
        environment = output / "installed_env"
        run_command([sys.executable, "-m", "venv", "--system-site-packages", str(environment)], neutral, logs, records)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run_command([str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index", str(dist / packages["wheel"])], neutral, logs, records)
        console_directory = environment / ("Scripts" if os.name == "nt" else "bin")
        for command in ("qf-solver", "solveur-ef", "mitc4-solver"):
            launcher = console_directory / (command + ".exe" if os.name == "nt" else command)
            run_command([str(launcher), "--version"], neutral, logs, records)
        run_command([str(console_directory / ("qf-solver.exe" if os.name == "nt" else "qf-solver")), "--help"], neutral, logs, records)
        probe = root / "scripts" / "probe_installed_package.py"
        for label, cwd in (("outside_checkout", neutral), ("inside_checkout", root)):
            run_command(installed_probe_command(python, probe, output / "source_mapping.json",
                        contract["package_version"], output / f"{label}_probe.json"), cwd, logs, records)
        result.update({"status": "PASS_CANDIDATE_PACKAGE_ONLY", "package_check": packages,
                       "probes": [json.loads((output / f"{label}_probe.json").read_text()) for label in ("outside_checkout", "inside_checkout")],
                       "limitations": contract["limitations"]})
    except Exception as exc:
        result.update({"status": "FAIL_CLOSED_CANDIDATE_BUILD", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        result["ended_utc"] = utc()
        write_record(output / "result.json", result)
        files = sorted(path for path in output.iterdir() if path.is_file()) + sorted((output / "logs").glob("*.log")) + sorted((output / "dist").glob("*"))
        write_record(output / "manifest.json", {"files": [{"path": path.relative_to(output).as_posix(),
                     "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())} for path in files if path.is_file()],
                     "includes_build_install_logs": True, "generated_worktrees_and_venv_are_not_evidence_inputs": True})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run_candidate(args.root, args.contract, args.output), indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
