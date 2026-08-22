"""Run one explicit large Cook refinement point without the full V&V campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.compat.mitc4.convergence import cook_large_point


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the memory-bounded MITC4 Cook refinement case.")
    parser.add_argument("--mesh", type=int, default=200, help="Elements per Cook side (default: 200).")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-MITC4-LINEAR-V1/VNV-MITC4-COOK-001-200x200"),
        help="Output directory.",
    )
    arguments = parser.parse_args()
    if arguments.mesh < 2:
        parser.error("--mesh must be at least 2")
    point = cook_large_point(arguments.mesh, arguments.mesh)
    arguments.output.mkdir(parents=True, exist_ok=True)
    payload = point.to_dict()
    payload["study_id"] = "VNV-MITC4-COOK-001"
    payload["assessment"] = (
        "REFERENCE_REVIEW_REQUIRED"
        if point.relative_error > 0.05
        else "WITHIN_CURRENT_THRESHOLD_REVIEW_REQUIRED"
    )
    payload["recommendation"] = (
        "Do not claim full Cook acceptance until the reference value and boundary conditions are independently audited."
    )
    (arguments.output / "result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    plot_name = _write_convergence_plot(arguments.output, payload)
    (arguments.output / "report.md").write_text(
        "# VNV-MITC4-COOK-001 - refinement point\n\n"
        f"Mesh: `{arguments.mesh}x{arguments.mesh}` ({point.element_count} elements).\n\n"
        f"Displacement: `{point.value:.9e}`. Reference: `{point.reference:.9e}`. "
        f"Relative error: `{point.relative_error:.3%}`.\n\n"
        f"Solver: `{point.solver_method}`, iterations: `{point.solver_iterations}`, "
        f"relative residual: `{point.solver_relative_residual:.3e}`.\n\n"
        f"Assessment: **{payload['assessment']}**.\n\n{payload['recommendation']}\n\n"
        f"![Convergence Cook]({plot_name})\n",
        encoding="utf-8",
    )
    print(f"Cook {arguments.mesh}x{arguments.mesh}: {point.relative_error:.3%}")
    print(f"output: {arguments.output.resolve()}")
    return 0


def _write_convergence_plot(output: Path, point: dict[str, object]) -> str:
    baseline = output.parent / "campaign_summary.json"
    points: list[dict[str, object]] = []
    if baseline.is_file():
        data = json.loads(baseline.read_text(encoding="utf-8"))
        points.extend(data["structural_convergence"]["cook"]["points"])
    points.append(point)
    unique = {int(item["element_count"]): item for item in points}
    ordered = [unique[key] for key in sorted(unique)]
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    axis.loglog(
        [int(item["element_count"]) for item in ordered],
        [float(item["relative_error"]) for item in ordered],
        "o-",
        color="#006d77",
        label="erreur a la reference Cook actuelle",
    )
    axis.axhline(0.05, color="#ae2012", linestyle="--", label="seuil historique 5 %")
    axis.set_xlabel("nombre d'elements")
    axis.set_ylabel("erreur relative")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    name = "cook_convergence_200x200.png"
    figure.savefig(output / name, dpi=160)
    plt.close(figure)
    return name


if __name__ == "__main__":
    raise SystemExit(main())
