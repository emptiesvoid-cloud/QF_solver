"""Near-100k TET4 refinement probe for Euler buckling acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.verification.calculix_tl_structural import run_calculix_buckling_level
from solveur.verification.tet4_total_lagrangian_buckling import (
    TotalLagrangianBucklingCampaign,
    euler_cantilever_critical_load,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class Tet4TlBucklingRefinementProbe:
    """Add one 64x16x16 point to the controlled Euler convergence study."""

    study_id = "VNV-TET4-TL-BUCKLING-H5-010"
    cells = (64, 16, 16)

    def __init__(self, output_dir: str | Path, baseline_summary: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.baseline_summary = Path(baseline_summary).resolve()
        self.project_root = Path(__file__).resolve().parents[2]

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        baseline = json.loads(self.baseline_summary.read_text(encoding="utf-8"))
        reference = euler_cantilever_critical_load(1.0e6, 0.5 * 0.5**3 / 12.0, 4.0)
        campaign = TotalLagrangianBucklingCampaign(self.output_dir)
        row, nodes, elements, mode = campaign.evaluate_level(self.cells, reference)
        previous = baseline["levels"][-1]
        row["change_from_24000"] = _relative(
            float(row["critical_load"]), float(previous["critical_load"])
        )
        factors = run_calculix_buckling_level(
            self.output_dir / "calculix_98304", nodes, elements
        )
        row["calculix_critical_load"] = factors[0]
        row["qf_calculix_relative_difference"] = _relative(
            float(row["critical_load"]), float(factors[0])
        )
        previous_error = float(previous["euler_relative_error"])
        checks = [
            _upper("euler_error_below_24000_level", float(row["euler_relative_error"]), previous_error),
            _upper("euler_error_below_five_percent", float(row["euler_relative_error"]), 0.05),
            _upper("qf_calculix_same_mesh", float(row["qf_calculix_relative_difference"]), 0.01),
            _lower("positive_precritical_jacobian", float(row["minimum_det_f"]), 0.9),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_REFINEMENT_ACCEPTANCE" if passed else "FAIL",
            "maturity": "research",
            "reference": baseline["reference"],
            "baseline_study": self._portable_path(self.baseline_summary),
            "previous_level": previous,
            "refined_level": row,
            "checks": checks,
            "interpretation": (
                "The 98,304-element point is a separate acceptance probe and is not part of fast CI."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(baseline["levels"], row, reference)
        self._plot_mode(nodes, elements, mode)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _portable_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.project_root).as_posix()
        except ValueError:
            return path.name

    def _plot_convergence(
        self, baseline: list[dict[str, object]], row: dict[str, object], reference: float
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        rows = [*baseline, row]
        elements = [int(item["elements"]) for item in rows]
        qf = [float(item["critical_load"]) for item in rows]
        figure, axis = plt.subplots(figsize=(7.8, 4.6))
        axis.semilogx(elements, qf, "o-", label="QF_solver TET4-TL")
        axis.scatter(
            [row["elements"]], [row["calculix_critical_load"]], marker="s", label="CalculiX C3D4"
        )
        axis.axhline(reference, color="#bc4749", linestyle="--", label="Euler")
        axis.set(xlabel="Nombre de tetraedres", ylabel="Charge critique")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "buckling_h5_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_mode(self, nodes: np.ndarray, elements: np.ndarray, mode: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        values = mode.reshape(-1, 3)
        scale = 0.8 / max(float(np.max(np.linalg.norm(values[:, 1:], axis=1))), 1.0e-30)
        deformed = nodes + scale * values
        exterior = _sample_edges(elements, 1000)
        figure = plt.figure(figsize=(9.0, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for coordinates, color, label in (
            (nodes, "#6c757d", "initial"),
            (deformed, "#d1495b", "mode amplifie"),
        ):
            for edge in exterior:
                axis.plot(*coordinates[list(edge)].T, color=color, linewidth=0.35, alpha=0.5)
            axis.scatter([], [], [], color=color, label=label)
        axis.set_box_aspect((4.0, 1.0, 1.0))
        axis.legend()
        axis.set_title("Premier mode tangent - 98 304 TET4")
        figure.tight_layout()
        figure.savefig(self.output_dir / "buckling_h5_mode.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        previous = summary["previous_level"]
        refined = summary["refined_level"]
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Point de raffinement d'acceptation a `64x16x16`, soit `98 304` TET4.",
            "",
            "| Niveau | TET4 | DDL | Pcr QF_solver | Ecart Euler | Pcr CalculiX | Ecart QF/CCX |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| precedent | {previous['elements']} | {previous['dofs']} | "
            f"{previous['critical_load']:.6f} | {100 * previous['euler_relative_error']:.3f} % | - | - |",
            f"| h5 | {refined['elements']} | {refined['dofs']} | "
            f"{refined['critical_load']:.6f} | {100 * refined['euler_relative_error']:.3f} % | "
            f"{refined['calculix_critical_load']:.6f} | "
            f"{100 * refined['qf_calculix_relative_difference']:.3f} % |",
            "",
            f"Variation 24 000 vers 98 304 TET4 : `{100 * refined['change_from_24000']:.3f} %`.",
            "",
            "![Convergence h5](buckling_h5_convergence.png)",
            "",
            "![Mode h5](buckling_h5_mode.png)",
            "",
        ]
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _sample_edges(elements: np.ndarray, maximum: int) -> np.ndarray:
    pairs = np.vstack(
        [elements[:, [i, j]] for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))]
    )
    edges = np.unique(np.sort(pairs, axis=1), axis=0)
    return edges[:: max(1, len(edges) // maximum)]


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
