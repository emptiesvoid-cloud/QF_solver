"""Driver for the controlled 026-G12 lot-2 performance diagnosis.

The implementation is split so the public script entry point and child-process
CLI remain stable while each Python module stays within the repository's
architecture limit.
"""

from __future__ import annotations

# These imports intentionally preserve the historical script import surface.
# ruff: noqa: F401

import sys
from pathlib import Path as _Path

_IMPL_ROOT = _Path(__file__).resolve().parents[2]
if str(_IMPL_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPL_ROOT))

try:
    from .g12_lot2_core import (
        Any,
        BASELINE_SHA,
        CONTRACT_ID,
        Callable,
        ConstraintReduction,
        DEFAULT_TARGETS,
        DEFAULT_TIMEOUT_SECONDS,
        GlobalAssembler,
        LinearStaticSolver,
        Path,
        ROOT,
        THREAD_KEYS,
        _RssSampler,
        _TimingAssembler,
        _assembly_only_case,
        _checksum,
        _csr_storage_bytes,
        _environment,
        _hex20_reference,
        _log_slope,
        _make_model,
        _run_once,
        _run_with_constraint_timer,
        _run_with_load_balance_timer,
        _same_domain_model,
        _tet10_reference,
        _timed_validation,
        _warmup,
        _write,
        argparse,
        assembler_module,
        build_diagnostic_report,
        build_model,
        cProfile,
        hashlib,
        json,
        load_module,
        math,
        np,
        os,
        platform,
        pstats,
        psutil,
        run_measured_case,
        subprocess,
        tempfile,
        threading,
        time,
        tracemalloc,
    )
except ImportError:  # Direct execution by the child-process driver.
    from qualification.runners.g12_lot2_core import (
        Any,
        BASELINE_SHA,
        CONTRACT_ID,
        Callable,
        ConstraintReduction,
        DEFAULT_TARGETS,
        DEFAULT_TIMEOUT_SECONDS,
        GlobalAssembler,
        LinearStaticSolver,
        Path,
        ROOT,
        THREAD_KEYS,
        _RssSampler,
        _TimingAssembler,
        _assembly_only_case,
        _checksum,
        _csr_storage_bytes,
        _environment,
        _hex20_reference,
        _log_slope,
        _make_model,
        _run_once,
        _run_with_constraint_timer,
        _run_with_load_balance_timer,
        _same_domain_model,
        _tet10_reference,
        _timed_validation,
        _warmup,
        _write,
        argparse,
        assembler_module,
        build_diagnostic_report,
        build_model,
        cProfile,
        hashlib,
        json,
        load_module,
        math,
        np,
        os,
        platform,
        pstats,
        psutil,
        run_measured_case,
        subprocess,
        tempfile,
        threading,
        time,
        tracemalloc,
    )


def _portable_profile_function(function: tuple[str, int, str]) -> str:
    filename, line_number, name = function
    normalized = str(filename).replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    for marker in ("/src/", "/scripts/", "/site-packages/"):
        if marker in normalized:
            normalized = marker.lstrip("/") + normalized.split(marker, 1)[1]
            break
    else:
        normalized = _Path(normalized).name
    return str((normalized, int(line_number), name))


def _child_case(args: argparse.Namespace) -> int:
    def factory() -> tuple[Any, dict[str, Any]]:
        return build_model(args.family, args.target)

    try:
        report = run_measured_case(factory, label=f"{args.family} target {args.target}", repetitions=args.repetitions, measure_memory=False)
    except Exception as exc:  # pragma: no cover - surfaced as machine-readable child failure
        report = {"label": f"{args.family} target {args.target}", "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
    _write(args.output, report)
    print(json.dumps({"status": report.get("status"), "label": report.get("label")}))
    return 0 if report.get("status") == "PASS" else 1


def _child_fair_case(args: argparse.Namespace) -> int:
    try:
        report = run_measured_case(lambda: _same_domain_model(args.family), label=f"fair {args.family}", repetitions=args.repetitions, measure_memory=False)
    except Exception as exc:  # pragma: no cover
        report = {"label": f"fair {args.family}", "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
    _write(args.output, report)
    print(json.dumps({"status": report.get("status"), "label": report.get("label")}))
    return 0 if report.get("status") == "PASS" else 1


def _profile_case(args: argparse.Namespace) -> int:
    profiler = cProfile.Profile()

    def factory() -> tuple[Any, dict[str, Any]]:
        return build_model(args.family, args.target)

    started = time.perf_counter()
    try:
        report = profiler.runcall(_run_once, factory, f"profile {args.family} target {args.target}", measure_memory=False)
        status = "PASS"
        error = None
    except Exception as exc:  # pragma: no cover
        report = None
        status = "FAIL"
        error = {"error_type": type(exc).__name__, "error": str(exc)}
    elapsed = time.perf_counter() - started
    if report is not None:
        stats = pstats.Stats(profiler)
        entries = []
        total_cumulative = max((values[3] for values in stats.stats.values()), default=elapsed)
        for function, values in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:20]:
            primitive_calls, calls, self_time, cumulative, _ = values
            entries.append({"function": _portable_profile_function(function), "calls": int(calls), "primitive_calls": int(primitive_calls), "self_seconds": float(self_time), "cumulative_seconds": float(cumulative), "percent_profile_cumulative": float(100.0 * cumulative / max(total_cumulative, 1.0e-12))})
        payload = {"schema_version": 1, "contract_id": CONTRACT_ID, "status": status, "family": args.family, "target_dofs": args.target, "environment": _environment(), "profiled_case": report, "profiled_wall_seconds": elapsed, "top_functions": entries}
    else:
        payload = {"schema_version": 1, "contract_id": CONTRACT_ID, "status": status, "family": args.family, "target_dofs": args.target, "environment": _environment(), **(error or {})}
    _write(args.output, payload)
    print(json.dumps({"status": status, "target": args.target}))
    return 0 if status == "PASS" else 1


def _spawn(command: list[str], output: Path, timeout: float) -> tuple[dict[str, Any] | None, str, int | None, str]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    child_process = psutil.Process(process.pid) if psutil is not None else None
    peak = 0
    started = time.perf_counter()
    while process.poll() is None:
        if child_process is not None:
            try:
                peak = max(peak, int(child_process.memory_info().rss))
            except psutil.Error:
                pass
        if time.perf_counter() - started >= timeout:
            process.kill()
            stdout, stderr = process.communicate()
            return None, "RESOURCE_LIMITED", peak or None, stderr.strip() or stdout.strip()
        time.sleep(0.05)
    stdout, stderr = process.communicate()
    if output.is_file():
        try:
            return json.loads(output.read_text(encoding="utf-8")), ("PASS" if process.returncode == 0 else "FAIL"), peak or None, stderr.strip() or stdout.strip()
        except json.JSONDecodeError as exc:
            return None, "FAIL", peak or None, f"invalid child JSON: {exc}"
    return None, "FAIL", peak or None, stderr.strip() or stdout.strip()


def run_scaling_driver(output: Path, targets: tuple[int, ...], repetitions: int, timeout: float) -> dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="qf_g12_lot2_") as temporary:
        for target in targets:
            child_output = Path(temporary) / f"TET4_{target}.json"
            command = [sys.executable, str(Path(__file__).resolve()), "--mode", "case", "--family", "TET4", "--target", str(target), "--repetitions", str(repetitions), "--output", str(child_output)]
            report, status, peak, detail = _spawn(command, child_output, timeout)
            if report is None:
                rows.append({"family": "TET4", "target_dofs": target, "status": status, "timeout_seconds": timeout, "peak_rss_bytes": peak, "reason": detail or "child did not produce a report"})
            else:
                report["family"] = "TET4"
                report["target_dofs"] = target
                report["case_peak_rss_bytes"] = peak
                report["case_peak_rss_scope"] = "parent sampler over child warmup and measured repetitions"
                rows.append(report)
            if status == "RESOURCE_LIMITED":
                break
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "environment": _environment(), "status": "PASS_WITH_RESOURCE_LIMIT" if any(row["status"] == "RESOURCE_LIMITED" for row in rows) else "PASS", "timeout_seconds": timeout, "scaling_route": "linear_static", "rows": rows, "resource_policy": {"stop_after_first_timeout": True, "timeout_seconds": timeout}}


def run_profile_driver(output: Path, targets: tuple[int, ...], timeout: float) -> dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="qf_g12_profile_") as temporary:
        for target in targets:
            child_output = Path(temporary) / f"profile_TET4_{target}.json"
            command = [sys.executable, str(Path(__file__).resolve()), "--mode", "profile", "--family", "TET4", "--target", str(target), "--repetitions", "1", "--output", str(child_output)]
            report, status, peak, detail = _spawn(command, child_output, timeout)
            if report is None:
                rows.append({"family": "TET4", "target_dofs": target, "status": status, "timeout_seconds": timeout, "peak_rss_bytes": peak, "reason": detail or "profile child did not produce a report"})
            else:
                report["case_peak_rss_bytes"] = peak
                rows.append(report)
            if status == "RESOURCE_LIMITED":
                break
    completed = [row for row in rows if row.get("status") == "PASS"]
    largest = max((row["target_dofs"] for row in completed), default=None)
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "environment": _environment(), "status": "PASS_WITH_RESOURCE_LIMIT" if len(completed) < len(rows) else "PASS", "timeout_seconds": timeout, "profiles": rows, "largest_completed_target_dofs": largest}


def run_fair_driver(output: Path, repetitions: int, timeout: float) -> dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="qf_g12_fair_") as temporary:
        for family in ("TET4", "TET10", "HEX8", "HEX20"):
            child_output = Path(temporary) / f"fair_{family}.json"
            command = [sys.executable, str(Path(__file__).resolve()), "--mode", "fair-case", "--family", family, "--repetitions", str(repetitions), "--output", str(child_output)]
            report, status, peak, detail = _spawn(command, child_output, timeout)
            if report is None:
                rows.append({"family": family, "status": status, "peak_rss_bytes": peak, "reason": detail or "fair child did not produce a report"})
            else:
                report["family"] = family
                report["case_peak_rss_bytes"] = peak
                report["case_peak_rss_scope"] = "parent sampler over child warmup and measured repetitions"
                rows.append(report)
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "environment": _environment(), "status": "PASS" if all(row.get("status") == "PASS" for row in rows) else "FAIL", "rows": rows, "memory_measurement": "parent sampler; timing runs have no RSS/tracemalloc instrumentation"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("case", "fair", "fair-case", "profile", "scaling-driver", "profile-driver", "aggregate"), default="scaling-driver")
    parser.add_argument("--family", default="TET4")
    parser.add_argument("--target", type=int, default=3_000)
    parser.add_argument("--targets", nargs="+", type=int, default=list(DEFAULT_TARGETS))
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path, default=Path("qualification/0_2_6/g12_lot2_evidence.json"))
    parser.add_argument("--scaling-input", type=Path, default=Path("qualification/0_2_6/g12_lot2_scaling.json"))
    parser.add_argument("--profiles-input", type=Path, default=Path("qualification/0_2_6/g12_lot2_profiles.json"))
    parser.add_argument("--fair-input", type=Path, default=Path("qualification/0_2_6/g12_lot2_high_order_fair.json"))
    args = parser.parse_args()
    if args.mode == "aggregate":
        _write(args.output, build_diagnostic_report(args.scaling_input, args.profiles_input, args.fair_input))
        return 0
    if args.mode == "case":
        return _child_case(args)
    if args.mode == "fair":
        _write(args.output, run_fair_driver(args.output, args.repetitions, args.timeout))
        return 0
    if args.mode == "fair-case":
        return _child_fair_case(args)
    if args.mode == "profile":
        return _profile_case(args)
    if args.mode == "profile-driver":
        _write(args.output, run_profile_driver(args.output, tuple(args.targets), args.timeout))
    elif args.mode == "scaling-driver":
        _write(args.output, run_scaling_driver(args.output, tuple(args.targets), args.repetitions, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
