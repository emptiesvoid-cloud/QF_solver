"""Structural mesh-convergence verification for the experimental MITC4 laminate."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mitc4.mesh import MeshFactory, QuadMesh

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.vnv_manifest import write_vnv_manifest


class CompositeStructuralConvergenceCampaign:
    """Verify membrane and bending convergence on genuinely meshed laminates."""

    study_id = "VNV-COMP-STRUCTURAL-CONVERGENCE-002"
    membrane_meshes = ((2, 1), (4, 2), (8, 4), (16, 8))
    cross_ply_meshes = ((4, 1), (8, 2), (16, 4), (24, 6), (32, 8))
    angle_ply_meshes = ((4, 1), (8, 2), (16, 4), (24, 6), (32, 8), (48, 12), (64, 16))

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        membrane = [self._membrane_case(nx, ny) for nx, ny in self.membrane_meshes]
        cross_ply_runs = [
            self._bending_case(nx, ny, [0.0, 90.0, 90.0, 0.0])
            for nx, ny in self.cross_ply_meshes
        ]
        angle_ply_runs = [
            self._bending_case(nx, ny, [45.0, -45.0, -45.0, 45.0])
            for nx, ny in self.angle_ply_meshes
        ]
        cross_ply = [row for row, _, _ in cross_ply_runs]
        angle_ply = [row for row, _, _ in angle_ply_runs]
        checks = [
            _upper("membrane_maximum_error", max(float(row["relative_error"]) for row in membrane), 1.0e-10),
            _upper("cross_ply_final_bending_error", float(cross_ply[-1]["relative_error"]), 2.0e-3),
            _equal("cross_ply_monotone_convergence", _monotone(cross_ply), True),
            _equal("angle_ply_monotone_convergence", _monotone(angle_ply), True),
            _upper("angle_ply_final_mesh_increment", _last_response_increment(angle_ply), 2.0e-3),
            _lower("cross_ply_thin_response_ratio", float(cross_ply[-1]["response_ratio"]), 0.998),
            _upper(
                "maximum_free_relative_residual",
                max(float(row["residual_relative"]) for row in membrane + cross_ply + angle_ply),
                1.0e-8,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "models": {
                "membrane_0_90_s": membrane,
                "bending_0_90_s": cross_ply,
                "bending_plus_minus_45_s": angle_ply,
            },
            "checks": checks,
            "external_correlation": {
                "status": "PASS_SEPARATE_STUDY",
                "study_id": "VNV-COMP-CALCULIX-S8R-003",
                "external_solver": "CalculiX 2.20 S8R COMPOSITE",
                "remaining_oracle": "Code_Aster DKT/DST DEFI_COMPOSITE",
                "comparison_type": "same_geometry_and_layup_convergence_not_same_element",
            },
            "reference_applicability": {
                "cross_ply": "Analytical Reissner-Mindlin beam reference used as acceptance oracle.",
                "angle_ply": (
                    "The one-dimensional beam value is informative only because the laminate "
                    "has bending-twisting coupling. Acceptance uses monotone mesh convergence "
                    "and the final mesh increment."
                ),
                "angle_ply_final_1d_reference_gap": float(angle_ply[-1]["relative_error"]),
            },
            "scope_limit": (
                "Linear static flat laminates. Analytical beam references are used away from "
                "stress singularities; no damage or progressive failure."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(membrane, cross_ply, angle_ply)
        _, fine_mesh, fine_result = cross_ply_runs[-1]
        self._plot_deformation(fine_mesh, fine_result)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _membrane_case(self, nx: int, ny: int) -> dict[str, object]:
        length, width, thickness = 1.0, 0.2, 4.0e-3
        membrane_force = 1.0e4
        mesh = MeshFactory.rectangular_plate(nx, ny, length, width)
        material_data = _laminate_definition([0.0, 90.0, 90.0, 0.0], thickness)
        left = _nodes_at_x(mesh, 0.0)
        right = _nodes_at_x(mesh, length)
        fixed = [{"node": node, "dofs": ["UZ", "RX", "RY", "RZ"]} for node in range(len(mesh.nodes))]
        fixed.extend({"node": node, "dofs": ["UX"]} for node in left)
        fixed.append({"node": left[0], "dofs": ["UY"]})
        edge_weights = _edge_weights(mesh, right)
        loads = [
            {"node": node, "dof": "UX", "value": membrane_force * edge_weights[index]}
            for index, node in enumerate(right)
        ]
        model = _shell_model(mesh, material_data, fixed, loads)
        result = solve_model(model)
        displacement = float(np.mean([result.displacements[result.dofs.index(node, "UX")] for node in right]))
        material = MaterialFactory.create(material_data)
        reference_strain = np.linalg.solve(material.membrane_matrix, np.array([membrane_force, 0.0, 0.0]))
        reference = float(reference_strain[0] * length)
        return _result_row(nx, ny, mesh, displacement, reference, result)

    def _bending_case(
        self,
        nx: int,
        ny: int,
        angles: list[float],
    ) -> tuple[dict[str, object], QuadMesh, object]:
        length, width, thickness = 1.0, 0.1, 1.0e-2
        force = 1.0
        mesh = MeshFactory.rectangular_plate(nx, ny, length, width)
        material_data = _laminate_definition(angles, thickness)
        left = _nodes_at_x(mesh, 0.0)
        right = _nodes_at_x(mesh, length)
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in left]
        loads = [{"node": node, "dof": "UZ", "value": -force / len(right)} for node in right]
        model = _shell_model(mesh, material_data, fixed, loads)
        result = solve_model(model)
        displacement = float(np.mean([result.displacements[result.dofs.index(node, "UZ")] for node in right]))
        material = MaterialFactory.create(material_data)
        bending_stiffness = 1.0 / np.linalg.inv(material.bending_matrix)[0, 0]
        shear_stiffness = 1.0 / np.linalg.inv(material.shear_matrix)[0, 0]
        reference = -force * (
            length**3 / (3.0 * bending_stiffness * width) + length / (shear_stiffness * width)
        )
        return _result_row(nx, ny, mesh, displacement, reference, result), mesh, result

    def _plot_convergence(
        self,
        membrane: list[dict[str, object]],
        cross_ply: list[dict[str, object]],
        angle_ply: list[dict[str, object]],
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, (oracle_axis, convergence_axis) = plt.subplots(1, 2, figsize=(10.8, 4.6))
        for rows, label, marker in (
            (membrane, "Membrane [0/90]s", "o"),
            (cross_ply, "Flexion [0/90]s", "s"),
        ):
            oracle_axis.loglog(
                [int(row["elements"]) for row in rows],
                [max(float(row["relative_error"]), 1.0e-16) for row in rows],
                marker=marker,
                label=label,
            )
        oracle_axis.set(
            xlabel="Nombre d'elements MITC4",
            ylabel="Erreur relative",
            title="Correlation analytique applicable",
        )
        oracle_axis.grid(True, which="both", alpha=0.25)
        oracle_axis.legend()

        finest_response = float(angle_ply[-1]["response"])
        convergence_axis.semilogx(
            [int(row["elements"]) for row in angle_ply],
            [float(row["response"]) / finest_response for row in angle_ply],
            marker="^",
            color="#2a9d3f",
            label="Flexion [+45/-45]s",
        )
        convergence_axis.axhline(1.0, color="#555555", linestyle="--", linewidth=1.0)
        convergence_axis.set(
            xlabel="Nombre d'elements MITC4",
            ylabel="Reponse / reponse du maillage fin",
            title="Stabilisation du modele couple",
        )
        convergence_axis.grid(True, which="both", alpha=0.25)
        convergence_axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_structural_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, mesh: QuadMesh, result: object) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        displacement = np.array(
            [
                [
                    result.displacements[result.dofs.index(node, dof)]
                    for dof in ("UX", "UY", "UZ")
                ]
                for node in range(len(mesh.nodes))
            ]
        )
        scale = 0.18 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = mesh.nodes + scale * displacement
        figure = plt.figure(figsize=(8.4, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for quad in mesh.quads:
            loop = np.append(quad, quad[0])
            axis.plot(mesh.nodes[loop, 0], mesh.nodes[loop, 1], mesh.nodes[loop, 2], color="#9a9a9a", linewidth=0.35)
            axis.plot(deformed[loop, 0], deformed[loop, 1], deformed[loop, 2], color="#326fa8", linewidth=0.65)
        axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z amplifie [m]")
        axis.set_title(f"[0/90]s, maillage {len(mesh.quads)} MITC4, amplification x{scale:.1f}")
        axis.view_init(elev=24.0, azim=-62.0)
        axis.set_box_aspect((1.0, 0.22, 0.22))
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_bending_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "| Modele | Maillage | Elements | Reponse QF | Reference | Erreur |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for name, rows in summary["models"].items():
            for row in rows:
                lines.append(
                    f"| {name} | {row['nx']}x{row['ny']} | {row['elements']} | "
                    f"{row['response']:.8e} | {row['reference']:.8e} | {row['relative_error']:.3e} |"
                )
        lines.extend(
            [
                "",
                "La membrane reproduit le champ constant. La flexion [0/90]s converge",
                "vers la reference de poutre Reissner-Mindlin construite avec les rigidites",
                "effectives du stratifie.",
                "",
                "Le stratifie [+45/-45]s converge monotoniquement, mais son couplage",
                "flexion-torsion n'est pas completement represente par l'oracle poutre 1D.",
                "Son acceptation repose donc sur l'increment entre les deux maillages les",
                "plus fins; l'ecart a la formule 1D reste publie comme limite de modele.",
                "",
                "La correlation externe est executee dans l'etude separee",
                "VNV-COMP-CALCULIX-S8R-003 avec CalculiX 2.20 S8R composite.",
                "",
                "![Convergence structurelle](composite_structural_convergence.png)",
                "",
                "![Maillage et deformee](composite_bending_deformation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _laminate_definition(angles: list[float], thickness: float) -> dict[str, object]:
    ply_thickness = thickness / len(angles)
    return {
        "type": "shell_laminate",
        "plies": [
            {
                "name": f"ply-{index + 1}",
                "E1": 135.0e9,
                "E2": 10.0e9,
                "nu12": 0.3,
                "G12": 5.0e9,
                "G13": 4.5e9,
                "G23": 3.8e9,
                "density": 1600.0,
                "thickness": ply_thickness,
                "angle_deg": angle,
                "strengths": {"Xt": 1.5e9, "Xc": 1.2e9, "Yt": 50.0e6, "Yc": 200.0e6, "S12": 75.0e6},
            }
            for index, angle in enumerate(angles)
        ],
    }


def _shell_model(
    mesh: QuadMesh,
    material: dict[str, object],
    fixed_dofs: list[dict[str, object]],
    loads: list[dict[str, object]],
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=mesh.nodes,
        elements=[{"type": "MITC4", "nodes": quad, "material": "laminate"} for quad in mesh.quads],
        materials={"laminate": material},
        fixed_dofs=fixed_dofs,
        loads=loads,
    )


def _nodes_at_x(mesh: QuadMesh, value: float) -> list[int]:
    return [index for index, point in enumerate(mesh.nodes) if abs(float(point[0]) - value) <= 1.0e-12]


def _edge_weights(mesh: QuadMesh, nodes: list[int]) -> np.ndarray:
    coordinates = np.asarray([mesh.nodes[node, 1] for node in nodes])
    order = np.argsort(coordinates)
    weights = np.zeros(len(nodes))
    sorted_coordinates = coordinates[order]
    for index in range(len(nodes) - 1):
        length = sorted_coordinates[index + 1] - sorted_coordinates[index]
        weights[order[index]] += 0.5 * length
        weights[order[index + 1]] += 0.5 * length
    return weights


def _result_row(nx: int, ny: int, mesh: QuadMesh, response: float, reference: float, result: object) -> dict[str, object]:
    error = abs(response - reference) / max(abs(reference), np.finfo(float).tiny)
    maximum_index = max(
        (
            float(item["failure_summary"]["critical_by_criterion"]["tsai_wu"]["index"])
            for item in result.element_results
            if "failure_summary" in item
        ),
        default=0.0,
    )
    return {
        "nx": nx,
        "ny": ny,
        "elements": int(len(mesh.quads)),
        "dofs": int(result.dofs.ndof),
        "response": response,
        "reference": reference,
        "response_ratio": response / reference,
        "relative_error": error,
        "maximum_tsai_wu_index": maximum_index,
        "residual_relative": float(result.audit.equilibrium["free_relative_residual"]),
    }


def _monotone(rows: list[dict[str, object]]) -> bool:
    errors = [float(row["relative_error"]) for row in rows]
    return all(current <= previous * (1.0 + 1.0e-10) for previous, current in zip(errors, errors[1:]))


def _last_response_increment(rows: list[dict[str, object]]) -> float:
    previous = float(rows[-2]["response"])
    current = float(rows[-1]["response"])
    return abs(current - previous) / max(abs(current), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}


def _equal(identifier: str, value: bool, expected: bool) -> dict[str, object]:
    return {"id": identifier, "value": value, "expected": expected, "status": "PASS" if value is expected else "FAIL"}
