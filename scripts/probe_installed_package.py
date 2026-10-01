"""Check only installed imports and the verify-all refusal, never launch solves."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import sys
from pathlib import Path


def _safe_path_is_active() -> bool:
    if bool(getattr(sys.flags, "safe_path", False)):
        return True
    checkout = Path(__file__).resolve().parents[1]
    cwd = Path.cwd().resolve()
    for entry in sys.path:
        if not entry:
            return False
        candidate = Path(entry).resolve()
        if any(candidate == parent or parent in candidate.parents for parent in (checkout, cwd)):
            return False
    return True


def probe(mapping_path: Path, version: str, output: Path) -> dict:
    # Native -P on 3.11+, or the audited path-sanitizing bootstrap on 3.10.
    safe_path = _safe_path_is_active()
    if not safe_path or sys.prefix == sys.base_prefix:
        raise ValueError("The installed probe requires a separate venv and safe-path mode.")
    import qf_solver
    import solveur
    from solveur.cli import main as cli
    from solveur.cli import verification

    distribution = importlib.metadata.distribution("qf-solver")
    if distribution.version != version:
        raise ValueError("Installed distribution version mismatch.")
    package_origin = Path(solveur.__file__).resolve()
    for module in (solveur, qf_solver, verification, cli):
        if not Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):
            raise ValueError("QF Solver was imported outside the installed environment.")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    verified = []
    for row in mapping:
        if row["path"].startswith("src/"):
            candidate = Path(str(distribution.locate_file(row["path"].removeprefix("src/"))))
            path = candidate.resolve(strict=True)
            if not path.is_relative_to(Path(sys.prefix).resolve()) or candidate.is_symlink():
                raise ValueError("An installed source escaped the environment.")
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != row["sha256"] or len(payload) != row["bytes"]:
                raise ValueError(f"Installed bytes mismatch: {row['path']}")
            verified.append(row["path"])
    events = []

    def audit(event: str, arguments: tuple) -> None:
        if event == "subprocess.Popen" or event in ("os.system", "os.posix_spawn", "os.spawn"):
            events.append({"event": event, "arguments": repr(arguments)})

    sys.addaudithook(audit)
    cli_checks = []
    for command in (["--version"], ["--help"]):
        text = io.StringIO()
        with contextlib.redirect_stdout(text), contextlib.redirect_stderr(text):
            try:
                code = cli.main(command)
            except SystemExit as exc:
                code = exc.code
        if code not in (0, None):
            raise ValueError("The installed CLI smoke check failed.")
        cli_checks.append({"arguments": command, "exit_code": code or 0, "output": text.getvalue()})
    requested = output.with_suffix(".verify_all_report.json")
    if requested.exists() or output.exists():
        raise ValueError("Probe outputs already exist.")
    text = io.StringIO()
    with contextlib.redirect_stdout(text), contextlib.redirect_stderr(text):
        code = cli.main(["verify-all", "--json-report", str(requested)])
    if code != 2 or "VERIFY-ALL UNSUPPORTED" not in text.getvalue() or events or requested.exists():
        raise ValueError("The installed verify-all boundary failed.")
    result = {"status": "PASS", "pid": os.getpid(), "cwd": str(Path.cwd()),
              "python_prefix": sys.prefix, "solveur_origin": str(package_origin),
              "qf_solver_origin": str(Path(qf_solver.__file__).resolve()),
              "verification_origin": str(Path(verification.__file__).resolve()),
              "verified_installed_sources": len(verified), "version": distribution.version,
              "cli_smoke": cli_checks, "verify_all_exit_code": code,
              "verify_all_output": text.getvalue(), "report_created": False,
              "python_subprocess_audit_events": events,
              "trace_scope": "PYTHON_AUDIT_HOOK_DURING_CLI_CHECKS_NOT_SYSTEM_WIDE_OS_TRACE",
              "dependency_isolation": "SYSTEM_AND_USER_SITE_DEPENDENCIES_ALLOWED_QF_ORIGIN_AND_BYTES_VERIFIED",
              "safe_path": safe_path,
              "runtime_versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib", "pip")}}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.mapping, args.version, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
