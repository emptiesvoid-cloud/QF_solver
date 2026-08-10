"""Run a bounded-memory TET10 Newmark refinement near 10,000 elements.

This is an opt-in V&V campaign. It uses summary post-processing because a full
element field is not required to compare the two time grids and would dominate
memory on a 50k-DOF model. The linear backend is selectable for diagnosis.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.verification.code_aster_tet10_dynamic import (
    CodeAsterTet10DynamicsCampaign,
    _newmark_analysis,
    _pulse_table,
)
from docs_support import plot_deformed_model


def _model_with_newmark(
    base: FiniteElementModel,
    root: np.ndarray,
    tip: np.ndarray,
    *,
    time_step: float,
    steps: int,
    linear_method: str,
) -> FiniteElementModel:
    table = _pulse_table(time_step, steps)
    analysis = _newmark_analysis(time_step, steps, table, tip)
    analysis.update(
        {
            "linear_method": linear_method,
            "postprocess_mode": "summary",
        }
    )
    return FiniteElementModel.from_raw(
        nodes=base.nodes.tolist(),
        elements=[{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in base.elements],
        materials=base.materials,
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root],
        loads=[{"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)} for node in tip],
        analysis=analysis,
        verification_profile="quick",
    )


def _history(result: object, tip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = result.solver["time_history"]
    times = np.asarray([row["time"] for row in rows], dtype=float)
    labels = [f"tip_{int(node)}" for node in tip]
    values = np.asarray(
        [np.mean([float(row["probes"][label]["displacement"]) for label in labels]) for row in rows], dtype=float
    )
    return times, values


def run(
    output: Path,
    *,
    mesh_size: float = 0.07,
    steps_per_period: tuple[int, int] = (10, 20),
    linear_method: str = "direct",
) -> dict[str, object]:
    """Run two controlled time grids on one refined TET10 mesh."""
    output.mkdir(parents=True, exist_ok=True)
    campaign = CodeAsterTet10DynamicsCampaign(output, mesh_size=0.20)
    base, root, tip = campaign._model(mesh_size, "linear_static", total_load=-1.0)
    # Lowest TET10 frequency from the controlled same-family convergence study.
    reference_frequency_hz = 20.581342039450544
    rows: list[dict[str, object]] = []
    final_model: FiniteElementModel | None = None
    final_result: object | None = None
    for steps_per_period_value in steps_per_period:
        step = 1.0 / reference_frequency_hz / steps_per_period_value
        model = _model_with_newmark(
            base,
            root,
            tip,
            time_step=step,
            steps=steps_per_period_value,
            linear_method=linear_method,
        )
        result = solve_model(model, enforce_policy=False)
        times, displacement = _history(result, tip)
        rows.append(
            {
                "steps_per_period": steps_per_period_value,
                "time_step_s": step,
                "times_s": times.tolist(),
                "mean_tip_uz_m": displacement.tolist(),
                "maximum_residual": max(float(value) for value in result.solver["residual_history"]),
                "maximum_energy_drift": max(
                    abs(float(value["relative_energy_drift"])) for value in result.solver["time_history"]
                ),
                "effective_factorization_reused": result.solver["effective_factorization_reused"],
            }
        )
        final_model, final_result = model, result
    coarse_time = np.asarray(rows[0]["times_s"], dtype=float)
    coarse_displacement = np.asarray(rows[0]["mean_tip_uz_m"], dtype=float)
    fine_time = np.asarray(rows[1]["times_s"], dtype=float)
    fine_displacement = np.asarray(rows[1]["mean_tip_uz_m"], dtype=float)
    reference = np.interp(fine_time, coarse_time, coarse_displacement)
    rms = float(np.linalg.norm(fine_displacement - reference) / max(np.linalg.norm(fine_displacement), 1.0e-30))
    rows[0]["normalized_rms_to_fine"] = rms
    rows[1]["normalized_rms_to_fine"] = 0.0
    assert final_model is not None and final_result is not None
    scale = plot_deformed_model(
        final_model,
        final_result,
        output / "tet10_newmark_refined_deformation.png",
        title=f"TET10 Newmark - {len(base.elements)} elements, pas fin",
    )
    figure, axis = plt.subplots(figsize=(7.4, 4.7))
    for row, color in zip(rows, ("#D55E00", "#0072B2"), strict=True):
        axis.plot(row["times_s"], row["mean_tip_uz_m"], color=color, label=f"{row['steps_per_period']} pas/periode")
    axis.set(xlabel="Temps [s]", ylabel="UZ moyen au bout [m]", title="TET10 Newmark - raffinement temporel")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "tet10_newmark_refined_time.png", dpi=180)
    plt.close(figure)
    summary: dict[str, object] = {
        "study_id": "VNV-TET10-DYNAMIC-MESH-TIME-REFINEMENT-022",
        "status": "PASS" if rms <= 0.05 else "WARNING",
        "model": {"element_type": "TET10", "elements": len(base.elements), "nodes": base.node_count, "dofs": base.node_count * 3},
        "newmark": {"reference_frequency_hz": reference_frequency_hz, "levels": rows, "relative_rms_increment": rms, "acceptance_limit": 0.05, "deformation_scale": scale},
        "limitations": [f"Internal QF_solver mesh/time proof with {linear_method} and summary post-processing.", "The external same-mesh Code_Aster campaign remains the external dynamic oracle."],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results") / "VNV-TET10-DYNAMIC-MESH-TIME-REFINEMENT-022")
    parser.add_argument("--mesh-size", type=float, default=0.07)
    parser.add_argument("--steps-per-period", type=int, nargs=2, metavar=("COARSE", "FINE"), default=(10, 20))
    parser.add_argument("--linear-method", choices=("direct", "cg"), default="direct")
    args = parser.parse_args()
    summary = run(
        args.output,
        mesh_size=args.mesh_size,
        steps_per_period=tuple(args.steps_per_period),
        linear_method=args.linear_method,
    )
    print(f"{summary['study_id']}: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
