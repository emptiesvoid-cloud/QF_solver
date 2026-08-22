"""Run the large TET4 total-Lagrangian Phase-2 buckling probe safely."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from solveur.io.manifest import write_json_file
from solveur.verification.tet4_total_lagrangian_buckling import (
    TotalLagrangianBucklingCampaign,
    euler_cantilever_critical_load,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nx", type=int, default=160)
    parser.add_argument("--ny", type=int, default=40)
    parser.add_argument("--nz", type=int, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET4-TL-PHASE2-LARGE-011"),
    )
    parser.add_argument("--max-memory-fraction", type=float, default=0.70)
    args = parser.parse_args()
    _validate_args(args)
    elements = 6 * args.nx * args.ny * args.nz
    estimate = estimate_peak_memory(elements)
    available = _available_memory()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    preflight = {
        "study_id": "VNV-TET4-TL-PHASE2-LARGE-011",
        "status": "PREFLIGHT",
        "cells": [args.nx, args.ny, args.nz],
        "elements": elements,
        "estimated_peak_memory_bytes": estimate,
        "available_memory_bytes": available,
        "max_memory_fraction": args.max_memory_fraction,
        "safe_to_run": available <= 0 or estimate < args.max_memory_fraction * available,
        "method": "current_vectorized_total_lagrangian_tet4_tangent",
        "external_correlation": "not_run_by_this_probe",
    }
    write_json_file(output / "preflight.json", preflight)
    if not preflight["safe_to_run"]:
        preflight["status"] = "RESOURCE_GUARD_BLOCKED"
        write_json_file(output / "preflight.json", preflight)
        print(json.dumps(preflight, indent=2), flush=True)
        return 2

    campaign = TotalLagrangianBucklingCampaign(output)
    reference = euler_cantilever_critical_load(1.0e6, 0.5 * 0.5**3 / 12.0, 4.0)
    started = time.perf_counter()
    print(
        f"Starting TET4-TL Phase-2 probe: {elements} elements, output={output}",
        flush=True,
    )
    row, _nodes, _connectivity, _mode = campaign.evaluate_level(
        (args.nx, args.ny, args.nz), reference
    )
    elapsed = time.perf_counter() - started
    row["wall_time_seconds"] = elapsed
    row["estimated_peak_memory_bytes"] = estimate
    row["available_memory_at_preflight_bytes"] = available
    summary: dict[str, Any] = {
        "study_id": "VNV-TET4-TL-PHASE2-LARGE-011",
        "status": "PASS_LARGE_RESEARCH_PROBE",
        "maturity": "research",
        "method": "total_lagrangian_saint_venant_kirchhoff_tet4",
        "reference": {
            "type": "euler_clamped_free_column",
            "formula": "pi^2 E I / (4 L^2)",
            "critical_load": reference,
        },
        "preflight": preflight,
        "level": row,
        "external_correlation": {
            "status": "NOT_RUN",
            "reason": "This phase-2 probe measures QF_solver scalability; a same-mesh external run is a separate ticket.",
        },
        "limitations": [
            "This is a large research probe, not a stable promotion.",
            "The current vectorized tangent path is used; memory is estimated, not sampled continuously.",
            "No postbuckling path is solved at this mesh level in this run.",
            "No external same-mesh correlation is included.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    campaign._plot_convergence([row], reference)
    _write_report(output, summary)
    write_vnv_manifest(output, str(summary["study_id"]))
    print(
        f"{summary['study_id']}: {summary['status']} -> {output}",
        flush=True,
    )
    return 0


def estimate_peak_memory(element_count: int) -> int:
    """Estimate a conservative peak for the current dense-per-element tangent path."""
    local_tangent = element_count * 144 * 8
    connectivity_and_gradients = element_count * (4 * 8 + 12 * 8 + 12 * 8)
    sparse_triplets = 3 * local_tangent
    return int(2.0 * (local_tangent + connectivity_and_gradients + sparse_triplets))


def _available_memory() -> int:
    try:
        import psutil

        return int(psutil.virtual_memory().available)
    except ImportError:
        return 0


def _validate_args(args: argparse.Namespace) -> None:
    if min(args.nx, args.ny, args.nz) <= 0:
        raise ValueError("nx, ny and nz must be strictly positive.")
    if not 0.1 <= args.max_memory_fraction <= 0.9:
        raise ValueError("max-memory-fraction must be between 0.1 and 0.9.")


def _write_report(output: Path, summary: dict[str, Any]) -> None:
    row = summary["level"]
    preflight = summary["preflight"]
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**",
        "",
        "Sonde de raffinement TET4 total-lagrangien Phase 2.",
        "",
        "| Mesure | Valeur |",
        "| --- | ---: |",
        f"| Elements | {row['elements']} |",
        f"| DDL | {row['dofs']} |",
        f"| Charge critique | {row['critical_load']:.8e} |",
        f"| Ecart Euler | {100.0 * row['euler_relative_error']:.6f} % |",
        f"| Increment precedent | {row.get('change_from_previous', 'not applicable')} |",
        f"| det(F) minimal | {row['minimum_det_f']:.8f} |",
        f"| Temps total | {row['wall_time_seconds']:.2f} s |",
        f"| Memoire estimee | {preflight['estimated_peak_memory_bytes'] / 1e9:.3f} GB |",
        "",
        "![Point de raffinement large](buckling_convergence.png)",
        "",
        "La correlation externe et le post-flambement a ce niveau sont des tickets separes.",
        "Le resultat ne change pas le statut `research` et ne vaut pas promotion stable.",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
