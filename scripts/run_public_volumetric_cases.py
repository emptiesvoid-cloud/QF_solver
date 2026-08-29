"""Run the generated QF cases from the public volumetric corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "qualification" / "0_2_6" / "public_volumetric_dataset_manifest.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "public_volumetric_qf_results.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *arguments], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _peak_rss(process: subprocess.Popen[str]) -> int | None:
    """Return the child RSS when psutil is available, without making it required."""

    try:
        import psutil  # type: ignore
    except ImportError:
        return None
    try:
        return int(psutil.Process(process.pid).memory_info().rss)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def _run_case(root: Path, case: dict[str, Any], timeout: float, output_dir: Path) -> dict[str, Any]:
    case_id = str(case["id"])
    case_path = root / str(case["qf_case"])
    result_path = output_dir / f"{case_id}.json"
    command = [
        sys.executable,
        "qf_solver.py",
        "solve",
        "--input",
        str(case_path),
        "--output",
        str(result_path),
        "--analysis",
        "linear_static",
        "--method",
        "direct",
    ]
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    peak_rss = 0
    timed_out = False
    while process.poll() is None:
        rss = _peak_rss(process)
        if rss is not None:
            peak_rss = max(peak_rss, rss)
        if time.perf_counter() - started >= timeout:
            timed_out = True
            process.kill()
            break
        time.sleep(0.2)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - started
    result: dict[str, Any] = {
        "id": case_id,
        "source_path": case.get("source_path"),
        "mesh_type": case.get("mesh_type"),
        "command": command,
        "timeout_seconds": timeout,
        "duration_seconds": elapsed,
        "peak_rss_bytes": peak_rss or None,
        "return_code": process.returncode,
        "stdout": stdout.strip()[-4000:],
        "stderr": stderr.strip()[-4000:],
    }
    if timed_out:
        result_path.unlink(missing_ok=True)
        result.update({"status": "TIMEOUT", "reason": f"QF execution exceeded {timeout:g} seconds"})
        return result
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        result_path.unlink(missing_ok=True)
        result.update({"status": "FAIL", "reason": f"missing or invalid QF result: {exc}"})
        return result
    qf_status = payload.get("status", "FAIL")
    run_verdict = payload.get("run_verdict")
    qualification = payload.get("qualification_summary", {})
    blocking_errors = qualification.get("blocking_errors", [])
    solver_failed = qf_status != "PASS" or run_verdict not in {"PASS", "WARNING"}
    if process.returncode != 0 and solver_failed:
        reason = "; ".join(str(item) for item in blocking_errors)
        result.update({
            "status": "FAIL",
            "solve_status": qf_status,
            "run_verdict": run_verdict,
            "reason": reason or stderr.strip() or stdout.strip() or f"exit code {process.returncode}",
        })
        result_path.unlink(missing_ok=True)
        return result
    result.update({
        "status": "PASS",
        "solve_status": qf_status,
        "run_verdict": run_verdict,
        "node_count": payload.get("node_count"),
        "element_count": payload.get("element_count"),
        "ndof": payload.get("ndof"),
        "max_displacement": payload.get("max_displacement"),
        "solver": {
            "backend": payload.get("solver", {}).get("backend"),
            "method": payload.get("solver", {}).get("method"),
            "iterations": payload.get("solver", {}).get("iterations"),
            "converged": payload.get("solver", {}).get("converged"),
            "residual_norm": payload.get("solver", {}).get("residual_norm"),
            "relative_residual_norm": payload.get("solver", {}).get("relative_residual_norm"),
            "termination_reason": payload.get("solver", {}).get("termination_reason"),
        },
        "qualification_summary": {
            "blocking_errors": qualification.get("blocking_errors", []),
            "warnings": qualification.get("warnings", []),
            "verification_profile": qualification.get("verification_profile"),
        },
        "qf_result_sha256": _sha256(result_path),
    })
    result_path.unlink(missing_ok=True)
    return result


def run(manifest_path: Path, output_path: Path, timeout: float) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir = output_path.parent / "public_volumetric_qf_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [record for record in manifest["records"] if record.get("status") == "PASS" and record.get("qf_case")]
    results = []
    for index, case in enumerate(cases, start=1):
        result = _run_case(ROOT, case, timeout, output_dir)
        results.append(result)
        print(f"[{index}/{len(cases)}] {result['id']} {result['status']} {result.get('ndof', '')}", flush=True)
    counts = {status: sum(row["status"] == status for row in results) for status in ("PASS", "EXPECTED_FAILURE", "FAIL", "TIMEOUT")}
    verdict_counts = {
        verdict: sum(row.get("run_verdict") == verdict for row in results)
        for verdict in ("PASS", "WARNING", "FAIL")
    }
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": _sha256(manifest_path),
        "dataset_manifest_id": manifest.get("manifest_id"),
        "source_commit": manifest.get("source", {}).get("commit"),
        "qf_source_sha": _git("rev-parse", "HEAD"),
        "qf_worktree_dirty": bool(_git("status", "--porcelain")),
        "solver_version": "0.2.6a0",
        "timeout_seconds": timeout,
        "cases_attempted": len(results),
        "status_counts": counts,
        "run_verdict_counts": verdict_counts,
        "results": results,
    }
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases_attempted": len(results), "status_counts": counts, "run_verdict_counts": verdict_counts}, indent=2))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output = args.output if args.output.is_absolute() else ROOT / args.output
    run(manifest, output, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
