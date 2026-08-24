"""Bounded performance characterization for the common nonlinear driver."""

from __future__ import annotations

import tracemalloc
from pathlib import Path
from time import perf_counter

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.j2_structural import J2StructuralCyclicCampaign


class J2NonlinearPerformanceCampaign:
    """Measure bounded cost indicators for the shared J2 nonlinear path.

    This is a characterization campaign, not a scalability claim.  It keeps
    the model deliberately small and records the scope so results cannot be
    mistaken for multi-million-DOF evidence.
    """

    campaign_id = "VNV-J2-NONLINEAR-PERFORMANCE-006"
    element_types = ("TET4", "TET10")

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_case(family) for family in self.element_types]
        status = "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) else "FAIL"
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": {
                "purpose": "bounded nonlinear driver characterization",
                "elements": list(self.element_types),
                "scalability_claim": False,
                "external_correlation": False,
            },
            "cases": rows,
            "interpretation": (
                "The measurements characterize total solve cost and state storage on small J2 bars. "
                "They do not qualify large-scale, parallel or multi-million-DOF performance."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        return summary

    def _run_case(self, family: str) -> dict[str, object]:
        mesh_path = BenchmarkMeshFactory().box_tetra(
            self.output_dir / f"j2_performance_{family.lower()}.msh",
            length=1.0,
            width=0.2,
            height=0.2,
            mesh_size=0.18,
            order=2 if family == "TET10" else 1,
            anchors=True,
        )
        setup_path = self.output_dir / f"{family.lower()}.setup.json"
        write_json_file(setup_path, J2StructuralCyclicCampaign._setup(family))
        model = GmshModelImporter().import_model(mesh_path, setup_path).model

        tracemalloc.start()
        started = perf_counter()
        result = solve_model(model)
        elapsed = perf_counter() - started
        _, peak_python_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        data = result.to_dict()
        steps = data["solver"]["steps"]
        residuals = [float(step["relative_residual"]) for step in steps]
        residual_history = [
            value for step in steps for value in step.get("residual_history", [])
        ]
        state_count = sum(len(item.get("integration_points", [])) for item in data["material_states"])
        finite = bool(np.all(np.isfinite(result.displacements)))
        return {
            "element_type": family,
            "status": "PASS" if result.status == "PASS" and finite else "FAIL",
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "dof_count": int(result.displacements.size),
            "integration_point_state_count": state_count,
            "elapsed_seconds": float(elapsed),
            "peak_python_memory_bytes": int(peak_python_bytes),
            "increments": len(steps),
            "total_newton_iterations": int(sum(int(step["iterations"]) for step in steps)),
            "maximum_relative_residual": max(residuals, default=float("inf")),
            "final_relative_residual": residuals[-1] if residuals else float("inf"),
            "residual_samples": len(residual_history),
            "notes": [
                "Timing includes model solve only after mesh import.",
                "Memory is Python allocation peak from tracemalloc, not process RSS.",
            ],
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Cette campagne est une caracterisation bornee; elle ne constitue pas une preuve de scalabilite HPC.",
            "",
            "| Element | DDL | Etats Gauss | Temps [s] | Iterations Newton | Residu final | Memoire Python [octets] |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["cases"]:
            lines.append(
                f"| `{row['element_type']}` | {row['dof_count']} | {row['integration_point_state_count']} | "
                f"{row['elapsed_seconds']:.6f} | {row['total_newton_iterations']} | "
                f"{row['final_relative_residual']:.6e} | {row['peak_python_memory_bytes']} |"
            )
        lines.extend(["", str(summary["interpretation"]), ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
