"""Structural h-convergence for oriented orthotropic TET4 and TET10 solids."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.solvers.static import LinearStaticSolver
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.large.assembler import ChunkedScipyAssembler
from solveur.large.audit import inspect_large_model
from solveur.large.model import LargeModel
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.vnv_manifest import write_vnv_manifest
from solveur.core.solvers.linear import LinearSystemSolver


class OrthotropicStructuralConvergenceCampaign:
    """Compare both tetrahedral families on an off-axis 3D cantilever."""

    study_id = "VNV-ORTHOTROPIC-SOLID-CONVERGENCE-003"
    sizes = (0.34, 0.25, 0.18, 0.13)
    tet4_extended_sizes = (0.105, 0.08)
    reference_size = 0.09

    def __init__(self, output_dir: str | Path, *, solver_method: str = "direct"):
        self.output_dir = Path(output_dir).resolve()
        self.factory = BenchmarkMeshFactory()
        self.full_result_element_limit = 12_000
        self.solver_method = str(solver_method).lower()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        reference = self._solve("TET10", self.reference_size, "reference_tet10")
        family_sizes = {
            "TET4": self.sizes + self.tet4_extended_sizes,
            "TET10": self.sizes,
        }
        families = {
            family: [
                self._solve(family, size, f"{family.lower()}_h{level}")
                for level, size in enumerate(sizes, start=1)
            ]
            for family, sizes in family_sizes.items()
        }
        reference_tip = float(reference["tip_uz_m"])
        reference_energy = float(reference["strain_energy_j"])
        for rows in families.values():
            for row in rows:
                row["tip_error"] = _relative(float(row["tip_uz_m"]), reference_tip)
                row["energy_error"] = _relative(float(row["strain_energy_j"]), reference_energy)
        checks = self._checks(families)
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "research",
            "covered_specifications": ["SPEC-COMP-SOLID-006"],
            "problem": {
                "geometry": "2.0 x 1.0 x 0.5 m cantilever",
                "material_angle_deg": 30.0,
                "load": "uniform terminal traction TZ=-1 MPa",
                "reference": "separate TET10 mesh at h=0.09 m",
                "tet4_extended_targets": "approximately 5,000, 10,000 and finer summary-only levels",
                "full_result_element_limit": self.full_result_element_limit,
            },
            "reference": reference,
            "families": families,
            "checks": checks,
            "limitations": [
                "The fine TET10 solution is a numerical reference, not a closed-form three-dimensional oracle.",
                "The campaign covers one homogeneous orientation and bending-dominated loading.",
                "Point stresses at mathematical singularities require a separate distance-based convergence study.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _solve(self, family: str, size: float, stem: str) -> dict[str, object]:
        mesh = self.factory.box_tetra(
            self.output_dir / f"{stem}.msh",
            length=2.0,
            width=1.0,
            height=0.5,
            mesh_size=size,
            order=1 if family == "TET4" else 2,
        )
        setup_path = self.output_dir / f"{stem}.setup.json"
        write_json_file(setup_path, _setup(family, self.solver_method))
        imported = GmshModelImporter().import_model(mesh, setup_path)
        if family == "TET4" and self.solver_method == "large_cg":
            return self._solve_large_tet4(imported.model, stem, size)
        compact = len(imported.model.elements) > self.full_result_element_limit
        result = enforce_qualification_policy(
            LinearStaticSolver().solve(imported.model, detail_level="summary" if compact else "full"),
            imported.model,
        )
        audit = result.audit
        if audit is None:
            raise RuntimeError("Orthotropic convergence run did not produce an audit.")
        equilibrium = audit.equilibrium
        selected = np.flatnonzero(np.isclose(imported.model.nodes[:, 0], 2.0))
        tip = float(np.mean([result.displacements[result.dofs.index(int(node), "UZ")] for node in selected]))
        row = {
            "family": family,
            "mesh_size": size,
            "nodes": imported.model.node_count,
            "elements": len(imported.model.elements),
            "tip_uz_m": tip,
            "strain_energy_j": float(equilibrium["secant_internal_energy"]),
            "free_relative_residual": float(equilibrium["free_relative_residual"]),
            "serialization": "summary" if compact else "full",
        }
        if compact:
            write_json_file(
                self.output_dir / f"{stem}.summary.json",
                {
                    "status": result.status,
                    "analysis": result.analysis,
                    "family": family,
                    "mesh_size": size,
                    "node_count": imported.model.node_count,
                    "element_count": len(imported.model.elements),
                    "tip_uz_m": tip,
                    "strain_energy_j": row["strain_energy_j"],
                    "free_relative_residual": row["free_relative_residual"],
                    "solver": result.solver,
                    "audit": {
                        "boundary": audit.boundary,
                        "equilibrium": audit.equilibrium,
                        "checks": [check.to_dict() for check in audit.checks],
                        "notes": audit.notes,
                    },
                },
            )
            write_json_file(
                self.output_dir / f"{stem}.mesh_summary.json",
                {
                    "node_count": imported.model.node_count,
                    "element_count": len(imported.model.elements),
                    "element_type": family,
                    "serialization": "summary",
                },
            )
        else:
            JsonModelWriter().write(imported.model, self.output_dir / f"{stem}.model.json")
            JsonResultWriter().write(result, self.output_dir / f"{stem}.result.json")
        return row

    def _solve_large_tet4(self, model: object, stem: str, size: float) -> dict[str, object]:
        """Solve a TET4 convergence level through the vectorized large-model path."""
        large_model = _large_model_with_integrated_loads(model)
        assembly = ChunkedScipyAssembler(chunk_size=4096).assemble(large_model)
        free = np.setdiff1d(np.arange(large_model.ndof, dtype=np.int64), assembly.fixed_dofs)
        if free.size == 0:
            raise RuntimeError("Large orthotropic TET4 level has no free degree of freedom.")
        reduced = assembly.stiffness[free, :][:, free]
        solution, info = LinearSystemSolver().solve(
            reduced,
            assembly.loads[free],
            method="cg",
            parameters={
                "assume_spd": True,
                "rtol": 1.0e-8,
                "atol": 0.0,
                "maxiter": 20_000,
                "preconditioner": "jacobi",
            },
        )
        displacement = np.zeros(large_model.ndof, dtype=float)
        displacement[free] = solution
        audit = inspect_large_model(
            large_model,
            stiffness=assembly.stiffness,
            loads=assembly.loads,
            displacement=displacement,
        )
        if audit.status == "FAIL":
            raise RuntimeError("Large orthotropic TET4 audit failed: " + "; ".join(audit.errors))
        tip_nodes = np.flatnonzero(np.isclose(large_model.nodes[:, 0], 2.0))
        tip = float(np.mean(displacement[3 * tip_nodes + 2]))
        solution_details = audit.details.get("solution", {})
        row = {
            "family": "TET4",
            "mesh_size": size,
            "nodes": large_model.node_count,
            "elements": large_model.element_count,
            "tip_uz_m": tip,
            "strain_energy_j": float(solution_details["strain_energy"]),
            "free_relative_residual": float(solution_details["free_relative_residual"]),
            "serialization": "summary",
            "solver_backend": "large_vectorized_scipy_cg",
            "solver_iterations": int(info.iterations),
            "solver_residual": float(info.residual_norm),
        }
        write_json_file(
            self.output_dir / f"{stem}.summary.json",
            {
                "status": "PASS",
                "analysis": "linear_static",
                "family": "TET4",
                "mesh_size": size,
                "node_count": large_model.node_count,
                "element_count": large_model.element_count,
                "tip_uz_m": tip,
                "strain_energy_j": row["strain_energy_j"],
                "free_relative_residual": row["free_relative_residual"],
                "solver": info.to_dict(),
                "audit": audit.to_dict(),
            },
        )
        write_json_file(
            self.output_dir / f"{stem}.mesh_summary.json",
            {
                "node_count": large_model.node_count,
                "element_count": large_model.element_count,
                "element_type": "TET4",
                "serialization": "summary",
                "solver_backend": "large_vectorized_scipy_cg",
            },
        )
        return row

    @staticmethod
    def _checks(families: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
        tet4, tet10 = families["TET4"], families["TET10"]
        return [
            _upper("tet4_finest_tip_error", float(tet4[-1]["tip_error"]), 0.25),
            _upper("tet4_finest_energy_error", float(tet4[-1]["energy_error"]), 0.25),
            _upper("tet10_finest_tip_error", float(tet10[-1]["tip_error"]), 0.025),
            _upper("tet10_finest_energy_error", float(tet10[-1]["energy_error"]), 0.025),
            _upper("tet4_final_tip_increment", _increment(tet4, "tip_uz_m"), 0.20),
            _upper("tet10_final_tip_increment", _increment(tet10, "tip_uz_m"), 0.02),
            _upper("tet4_error_trend_violations", _trend_violations(tet4), 1.0),
            _upper("tet10_error_trend_violations", _trend_violations(tet10), 1.0),
            _lower("tet4_tip_error_reduction", float(tet4[0]["tip_error"]) / float(tet4[-1]["tip_error"]), 2.0),
            _lower("tet10_tip_error_reduction", float(tet10[0]["tip_error"]) / float(tet10[-1]["tip_error"]), 5.0),
            _upper("maximum_free_residual", _maximum_residual(families), 1.0e-8),
        ]

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
        for family, marker in (("TET4", "s"), ("TET10", "o")):
            rows = summary["families"][family]
            sizes = [row["mesh_size"] for row in rows]
            axes[0].loglog(sizes, [row["tip_error"] for row in rows], marker=marker, label=family)
            axes[1].loglog(sizes, [row["energy_error"] for row in rows], marker=marker, label=family)
        for axis, title in zip(axes, ("Fleche terminale", "Energie de deformation"), strict=True):
            axis.invert_xaxis()
            axis.set(xlabel="Taille nominale h [m]", ylabel="Ecart relatif", title=title)
            axis.grid(True, which="both", alpha=0.25)
            axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "orthotropic_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Verdict automatise : **{summary['status']}**",
            "",
            "Porte-a-faux 3D orthotrope a 30 deg. La reference est calculee sur un maillage TET10 separe a h=0,09 m.",
            "",
            "| Famille | h [m] | Elements | UZ [m] | Ecart UZ | Ecart energie | Residu libre |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for family in ("TET4", "TET10"):
            for row in summary["families"][family]:
                lines.append(
                    f"| {family} | {row['mesh_size']:.2f} | {row['elements']} | {row['tip_uz_m']:.8e} | "
                    f"{100 * row['tip_error']:.4f} % | {100 * row['energy_error']:.4f} % | "
                    f"{row['free_relative_residual']:.3e} |"
                )
        lines.extend(["", "![Convergence](orthotropic_convergence.png)", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _large_model_with_integrated_loads(model: Any) -> LargeModel:
    """Build a large TET4 container without losing distributed-load work."""
    dofs = model.dof_manager()
    integrated = GlobalAssembler().assemble_loads(model, dofs)
    nonzero = np.flatnonzero(np.abs(integrated) > 1.0e-30)
    material_names = tuple(sorted(model.materials))
    material_ids = np.asarray(
        [material_names.index(element.material) for element in model.elements],
        dtype=np.int64,
    )
    component_by_dof = {"UX": 0, "UY": 1, "UZ": 2}
    fixed_nodes: list[int] = []
    fixed_components: list[int] = []
    for condition in model.fixed_dofs:
        for name in condition.dofs:
            fixed_nodes.append(int(condition.node))
            fixed_components.append(component_by_dof[str(name)])
    analysis = {
        "type": model.analysis.type,
        "method": "cg",
        "parameters": dict(model.analysis.parameters),
    }
    return LargeModel(
        nodes=model.nodes,
        tet4=np.asarray([element.nodes for element in model.elements], dtype=np.int64),
        material_ids=material_ids,
        materials=model.materials,
        material_names=material_names,
        fixed_nodes=np.asarray(fixed_nodes, dtype=np.int64),
        fixed_components=np.asarray(fixed_components, dtype=np.int8),
        load_nodes=(nonzero // 3).astype(np.int64),
        load_components=(nonzero % 3).astype(np.int8),
        load_values=np.asarray(integrated[nonzero], dtype=float),
        analysis=analysis,
        schema_version=model.schema_version,
        units=model.units,
        verification_profile=model.verification_profile,
    )


def _setup(family: str, solver_method: str = "direct") -> dict[str, Any]:
    angle = np.deg2rad(30.0)
    orientation = [
        [float(np.cos(angle)), float(-np.sin(angle)), 0.0],
        [float(np.sin(angle)), float(np.cos(angle)), 0.0],
        [0.0, 0.0, 1.0],
    ]
    requested_method = str(solver_method).lower()
    method = "cg" if requested_method == "large_cg" else requested_method
    parameters: dict[str, object] = {}
    if method in {"cg", "conjugate_gradient"}:
        parameters = {
            "assume_spd": True,
            "spd_dense_check_max_dofs": 0,
            "rtol": 1.0e-8,
            "maxiter": 20_000,
            "preconditioner": "jacobi",
        }
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": method, "parameters": parameters},
        "materials": {
            "solid": {
                "type": "orthotropic_3d",
                "E1": 135.0e9,
                "E2": 10.0e9,
                "E3": 8.0e9,
                "nu12": 0.28,
                "nu13": 0.22,
                "nu23": 0.35,
                "G12": 5.2e9,
                "G13": 4.1e9,
                "G23": 3.3e9,
                "density": 1580.0,
                "orientation": orientation,
            }
        },
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": family, "material": "solid"}],
            },
            {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [0.0, 0.0, -1.0e6]}]},
        ],
    }


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _increment(rows: list[dict[str, object]], key: str) -> float:
    return _relative(float(rows[-1][key]), float(rows[-2][key]))


def _trend_violations(rows: list[dict[str, object]]) -> float:
    errors = [float(row["tip_error"]) + float(row["energy_error"]) for row in rows]
    return float(sum(current > previous for previous, current in zip(errors, errors[1:])))


def _maximum_residual(families: dict[str, list[dict[str, object]]]) -> float:
    return max(float(row["free_relative_residual"]) for rows in families.values() for row in rows)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
