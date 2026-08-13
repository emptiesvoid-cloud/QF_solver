"""Near-incompressible bending characterization for TET4 and TET10."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.tet10_structural_convergence import plot_tetra_vector
from solveur.verification.vnv_manifest import write_vnv_manifest


class Tet10NearIncompressibleCampaign:
    """Measure displacement-locking sensitivity as Poisson's ratio approaches 0.5."""

    study_id = "VNV-TET10-NEAR-INCOMPRESSIBLE-015"
    poisson_values = (0.30, 0.45, 0.49, 0.499)
    mesh_sizes = (1.10, 0.75, 0.50)

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.factory = BenchmarkMeshFactory()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        families = {family: self._family(family) for family in ("TET4", "TET10")}
        checks = self._checks(families)
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_CHARACTERIZATION" if passed else "FAIL",
            "maturity": "experimental",
            "purpose": "characterize volumetric-locking sensitivity of displacement tetrahedra",
            "poisson_values": list(self.poisson_values),
            "mesh_sizes": list(self.mesh_sizes),
            "families": families,
            "checks": checks,
            "interpretation": self._interpretation(families),
            "scope_limit": (
                "The campaign characterizes a slender 3D cantilever in small-strain linear "
                "elasticity. It does not qualify mixed u-p incompressible formulations."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _family(self, family: str) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        order = 1 if family == "TET4" else 2
        for level, mesh_size in enumerate(self.mesh_sizes, start=1):
            mesh = self.factory.box_tetra(
                self.output_dir / f"bending_{family.lower()}_h{level}.msh",
                length=8.0,
                width=1.0,
                height=1.0,
                mesh_size=mesh_size,
                order=order,
            )
            for poisson in self.poisson_values:
                prefix = f"bending_{family.lower()}_h{level}_nu{str(poisson).replace('.', 'p')}"
                model, result = self._solve(mesh, family, poisson, prefix)
                response = _mean_tip_displacement(model, result)
                reference = timoshenko_tip_displacement(poisson)
                rows.append(
                    {
                        "level": level,
                        "mesh_size": mesh_size,
                        "poisson": poisson,
                        "bulk_to_shear_ratio": bulk_to_shear_ratio(poisson),
                        "node_count": model.node_count,
                        "element_count": len(model.elements),
                        "response": response,
                        "reference": reference,
                        "normalized_compliance": response / reference,
                        "response_error": _relative(response, reference),
                        "free_relative_residual": _free_residual(result),
                    }
                )
                if family == "TET10" and level == len(self.mesh_sizes) and poisson == self.poisson_values[-1]:
                    VtuResultWriter().write(
                        result,
                        model,
                        self.output_dir / "tet10_nu0499_deformation.vtu",
                    )
                    plot_tetra_vector(
                        self.output_dir / "tet10_nu0499_deformation.png",
                        model,
                        np.asarray(result.displacements, dtype=float),
                        "TET10 flexion quasi-incompressible nu=0.499",
                    )
        finest = [row for row in rows if row["level"] == len(self.mesh_sizes)]
        return {
            "levels": rows,
            "finest": finest,
            "minimum_finest_compliance": min(float(row["normalized_compliance"]) for row in finest),
            "maximum_finest_error": max(float(row["response_error"]) for row in finest),
            "maximum_free_relative_residual": max(float(row["free_relative_residual"]) for row in rows),
        }

    def _solve(self, mesh: Path, family: str, poisson: float, prefix: str) -> tuple[object, object]:
        setup_path = self.output_dir / f"{prefix}.setup.json"
        write_json_file(setup_path, _bending_setup(family, poisson))
        imported = GmshModelImporter().import_model(mesh, setup_path)
        JsonModelWriter().write(imported.model, self.output_dir / f"{prefix}.model.json")
        result = enforce_qualification_policy(AnalysisRouter().solve(imported.model), imported.model)
        return imported.model, result

    @staticmethod
    def _checks(families: dict[str, dict[str, object]]) -> list[dict[str, object]]:
        tet10 = families["TET10"]
        all_rows = [row for family in families.values() for row in family["levels"]]
        return [
            _lower("all_responses_finite", float(all(np.isfinite(row["response"]) for row in all_rows)), 1.0),
            _upper(
                "all_free_residuals",
                max(float(family["maximum_free_relative_residual"]) for family in families.values()),
                1.0e-7,
            ),
            _lower("tet10_finest_compliance_retention", float(tet10["minimum_finest_compliance"]), 0.90),
            _upper("tet10_finest_reference_error", float(tet10["maximum_finest_error"]), 0.10),
        ]

    @staticmethod
    def _interpretation(families: dict[str, dict[str, object]]) -> dict[str, object]:
        tet4 = _finest_row(families["TET4"], 0.499)
        tet10 = _finest_row(families["TET10"], 0.499)
        return {
            "nu_0_499_tet4_compliance": tet4["normalized_compliance"],
            "nu_0_499_tet10_compliance": tet10["normalized_compliance"],
            "tet10_to_tet4_compliance_ratio": float(tet10["normalized_compliance"])
            / max(float(tet4["normalized_compliance"]), np.finfo(float).tiny),
            "qualification_statement": (
                "Passing this characterization does not extend the accepted domain to exact "
                "incompressibility; nu >= 0.499 remains outside autonomous-use scope."
            ),
        }

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
        for family, marker in (("TET4", "s"), ("TET10", "o")):
            data = summary["families"][family]
            for level in range(1, len(self.mesh_sizes) + 1):
                rows = [row for row in data["levels"] if row["level"] == level]
                axes[0].semilogx(
                    [row["bulk_to_shear_ratio"] for row in rows],
                    [row["normalized_compliance"] for row in rows],
                    marker=marker,
                    label=f"{family} h{level}",
                )
            rows = [row for row in data["levels"] if row["poisson"] == 0.499]
            axes[1].plot(
                [row["mesh_size"] for row in rows],
                [row["normalized_compliance"] for row in rows],
                marker=marker,
                label=family,
            )
        axes[0].axhline(1.0, color="black", linewidth=0.8)
        axes[0].set(xlabel="K/G", ylabel="Compliance calculee / Timoshenko", title="Sensibilite a nu")
        axes[1].axhline(1.0, color="black", linewidth=0.8)
        axes[1].invert_xaxis()
        axes[1].set(xlabel="Taille nominale h", ylabel="Compliance normalisee", title="Raffinement a nu=0.499")
        for axis in axes:
            axis.grid(True, alpha=0.25)
            axis.legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "tet10_near_incompressible.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Poutre 3D en flexion, formulation deplacement pure, trois maillages et quatre coefficients de Poisson.",
            "",
            "| Famille | nu | K/G | Compliance fine | Erreur fine |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for family, data in summary["families"].items():
            for row in data["finest"]:
                lines.append(
                    f"| {family} | {row['poisson']:.3f} | {row['bulk_to_shear_ratio']:.3f} | "
                    f"{row['normalized_compliance']:.6f} | {row['response_error']:.3e} |"
                )
        lines.extend(
            [
                "",
                "Le verdict PASS signifie que la caracterisation est reproductible et respecte les seuils declares.",
                "Il ne qualifie pas la limite incompressible; une formulation mixte reste necessaire pour ce domaine.",
                "",
                "![Sensibilite quasi-incompressible](tet10_near_incompressible.png)",
                "",
                "![Deformee TET10 nu 0.499](tet10_nu0499_deformation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def timoshenko_tip_displacement(poisson: float) -> float:
    """Closed-form tip displacement for the campaign's square cantilever."""
    length, width, height = 8.0, 1.0, 1.0
    young, traction = 70.0e9, -1000.0
    force = traction * width * height
    shear = young / (2.0 * (1.0 + poisson))
    inertia = width * height**3 / 12.0
    return force * length**3 / (3.0 * young * inertia) + force * length / ((5.0 / 6.0) * shear * width * height)


def bulk_to_shear_ratio(poisson: float) -> float:
    return 2.0 * (1.0 + poisson) / (3.0 * (1.0 - 2.0 * poisson))


def _bending_setup(family: str, poisson: float) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"solid": {"type": "isotropic_3d", "E": 70.0e9, "nu": poisson}},
        "groups": [
            {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": family, "material": "solid"}]},
            {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [0.0, 0.0, -1000.0]}]},
        ],
    }


def _mean_tip_displacement(model: object, result: object) -> float:
    nodes = np.asarray(model.nodes, dtype=float)
    selected = np.where(np.isclose(nodes[:, 0], np.max(nodes[:, 0])))[0]
    return float(np.mean([result.displacements[result.dofs.index(int(node), "UZ")] for node in selected]))


def _free_residual(result: object) -> float:
    return float(result.to_dict().get("audit", {}).get("equilibrium", {}).get("free_relative_residual", 0.0))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _finest_row(family: dict[str, object], poisson: float) -> dict[str, object]:
    return next(row for row in family["finest"] if row["poisson"] == poisson)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
