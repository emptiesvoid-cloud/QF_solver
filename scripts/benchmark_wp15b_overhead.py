"""Prepare the WP15-B telemetry overhead benchmark; execution is opt-in."""

from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path
from typing import Any, cast

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.core.telemetry import ConsoleSink, JsonlSink, TelemetryEmitter


MODES = ("OFF", "CONSOLE_ONLY", "JSONL_ONLY", "CONSOLE_PLUS_JSONL")


def build_fixture() -> FiniteElementModel:
    """Build the tiny deterministic fixture used for mode comparisons."""

    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={
            "solid": {
                "type": "isotropic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "density": 10.0,
            }
        },
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in (0, 2, 3)
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis="linear_static",
    )


def _memory_snapshot() -> dict[str, int | None]:
    """Return boundary samples; a future runner may replace this with a sampler."""

    try:
        import psutil

        info = psutil.Process().memory_info()
        private = getattr(info, "uss", None)
        if private is None:
            private = getattr(info, "private", None)
        return {"rss": int(info.rss), "private": int(private) if private is not None else None}
    except (ImportError, OSError, AttributeError):
        return {"rss": None, "private": None}


def _make_emitter(mode: str, run_directory: Path, run_index: int) -> tuple[TelemetryEmitter | None, io.StringIO, Path | None]:
    console_output = io.StringIO()
    if mode == "OFF":
        return None, console_output, None

    sinks: list[Any] = []
    if mode in {"CONSOLE_ONLY", "CONSOLE_PLUS_JSONL"}:
        sinks.append(ConsoleSink(stream=console_output, profile="linear_static"))
    jsonl_path: Path | None = None
    if mode in {"JSONL_ONLY", "CONSOLE_PLUS_JSONL"}:
        run_directory.mkdir(parents=True, exist_ok=True)
        jsonl_path = run_directory / f"{mode.lower()}-{run_index:03d}.jsonl"
        sinks.append(JsonlSink(jsonl_path))
    return (
        TelemetryEmitter(
            analysis_id=f"wp15b-overhead-{mode.lower()}-{run_index:03d}",
            analysis_type="linear_static",
            route="linear_static",
            sinks=sinks,
        ),
        console_output,
        jsonl_path,
    )


def measure_mode(mode: str, run_directory: Path, run_index: int) -> dict[str, object]:
    """Measure one future benchmark repetition for a declared mode."""

    if mode not in MODES:
        raise ValueError(f"Unsupported mode {mode!r}; expected one of {MODES}.")
    emitter, console_output, jsonl_path = _make_emitter(mode, run_directory, run_index)
    before = _memory_snapshot()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    result = solve_model(build_fixture(), telemetry=emitter)
    wall_time_s = time.perf_counter() - wall_started
    cpu_time_s = time.process_time() - cpu_started
    if emitter is not None:
        emitter.close()
    after = _memory_snapshot()
    jsonl_bytes = jsonl_path.stat().st_size if jsonl_path is not None and jsonl_path.exists() else 0
    event_count = (
        len(jsonl_path.read_text(encoding="utf-8").splitlines())
        if jsonl_path is not None and jsonl_path.exists()
        else console_output.getvalue().count("event=")
    )
    return {
        "mode": mode,
        "run_index": run_index,
        "status": getattr(result, "status", None),
        "wall_time_s": wall_time_s,
        "cpu_time_s": cpu_time_s,
        "peak_rss_process": max((value for value in (before["rss"], after["rss"]) if value is not None), default=None),
        "peak_private_or_uss_process": max(
            (value for value in (before["private"], after["private"]) if value is not None),
            default=None,
        ),
        "telemetry_sample_peak_rss": after["rss"],
        "telemetry_sample_peak_private": after["private"],
        "event_count": event_count,
        "jsonl_bytes": jsonl_bytes,
        "console_event_count": console_output.getvalue().count("event="),
        "sink_degradation_status": emitter.health.status if emitter is not None else "DISABLED",
        "fixture": "tiny_deterministic_TET4",
    }


def run_benchmark(modes: tuple[str, ...], repeats: int, output: Path) -> dict[str, object]:
    """Run the opt-in benchmark and write a machine-readable report."""

    if repeats <= 0:
        raise ValueError("repeats must be positive.")
    run_directory = output.parent / f"{output.stem}_jsonl"
    rows = [measure_mode(mode, run_directory, index) for mode in modes for index in range(repeats)]
    report = {
        "schema_version": 1,
        "record_type": "wp15b_overhead_benchmark",
        "status": "MEASURED_NO_THRESHOLD",
        "modes": list(modes),
        "repeats": repeats,
        "threshold_frozen": False,
        "rows": rows,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, action="append", dest="modes")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/0_2_9/wp15b_overhead_benchmark.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    modes = tuple(args.modes) if args.modes else MODES
    report = run_benchmark(modes, args.repeats, args.output)
    rows = cast(list[dict[str, object]], report["rows"])
    print(json.dumps({"status": report["status"], "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
