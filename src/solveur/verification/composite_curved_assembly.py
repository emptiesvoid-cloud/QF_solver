"""Curved and folded-assembly verification for projected laminate axes."""

from __future__ import annotations

from math import atan2, cos, degrees, radians, sin
from pathlib import Path

import numpy as np

from mitc4.mesh import QuadMesh

from solveur.api import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.composite_structural import _laminate_definition
from solveur.verification.vnv_manifest import write_vnv_manifest


class CompositeCurvedAssemblyCampaign:
    """Verify projected axes on a cylinder and convergence of a folded panel."""

    study_id = "VNV-COMP-CURVED-ASSEMBLY-006"
    curved_meshes = ((8, 4), (16, 8), (24, 12), (32, 16))
    folded_meshes = ((8, 2), (16, 4), (24, 6), (32, 8), (48, 12), (64, 16))

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        curved_runs = [
            self._run_model(_cylindrical_panel(nx, ny), nx, ny, "curved")
            for nx, ny in self.curved_meshes
        ]
        distorted_mesh = _cylindrical_panel(32, 16, distortion=0.10)
        distorted = self._run_model(
            distorted_mesh,
            32,
            16,
            "curved_distorted",
            verification_profile="quick",
        )
        folded_runs = [
            self._run_model(_folded_panel(nx, ny), nx, ny, "folded")
            for nx, ny in self.folded_meshes
        ]
        curved_increment = _last_increment(curved_runs, "weighted_tip_uz")
        folded_increment = _last_increment(folded_runs, "weighted_tip_uz")
        distortion_gap = _relative(
            float(distorted["weighted_tip_uz"]),
            float(curved_runs[-1]["weighted_tip_uz"]),
        )
        checks = [
            _upper(
                "curved_reference_angle_error_deg",
                max(float(row["reference_angle_error_deg"]) for row in curved_runs),
                1.0e-10,
            ),
            _upper("curved_final_mesh_increment", curved_increment, 2.0e-2),
            _upper("folded_final_mesh_increment", folded_increment, 2.0e-2),
            _upper("ten_percent_distortion_response_gap", distortion_gap, 5.0e-2),
            _equal(
                "warped_facet_qualification_gate",
                str(distorted["run_verdict"]),
                "FAIL",
            ),
            _upper(
                "maximum_free_relative_residual",
                max(
                    float(row["residual_relative"])
                    for row in curved_runs + folded_runs + [distorted]
                ),
                1.0e-8,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "models": {
                "curved_panel": curved_runs,
                "curved_panel_distorted": distorted,
                "folded_assembly": folded_runs,
            },
            "checks": checks,
            "orientation_rule": (
                "Project the normalized global reference_direction into each facet plane, "
                "then add its signed local angle to every ply angle."
            ),
            "scope_limit": (
                "The projection is undefined where reference_direction is parallel to a "
                "facet normal. This campaign covers a faceted cylindrical panel and a "
                "two-face folded assembly under combined nodal loading. It is an internal "
                "verification, not an external benchmark or damage qualification."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(curved_runs, folded_runs, distorted)
        self._plot_geometries(_cylindrical_panel(24, 12), _folded_panel(24, 6))
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_model(
        self,
        mesh: QuadMesh,
        nx: int,
        ny: int,
        kind: str,
        verification_profile: str = "engineering",
    ) -> dict[str, object]:
        material = _laminate_definition([0.0, 45.0, -45.0, 90.0], 8.0e-3)
        material["reference_direction"] = [1.0, 1.0, 0.0]
        left = _nodes_at_x(mesh, 0.0)
        right = _nodes_at_x(mesh, 1.0)
        weights = _edge_weights_3d(mesh, right)
        loads: list[dict[str, object]] = []
        for index, node in enumerate(right):
            loads.extend(
                (
                    {"node": node, "dof": "UX", "value": 1000.0 * weights[index]},
                    {"node": node, "dof": "UZ", "value": -20.0 * weights[index]},
                )
            )
        model = FiniteElementModel.from_raw(
            nodes=mesh.nodes,
            elements=[
                {"type": "MITC4", "nodes": quad, "material": "laminate"}
                for quad in mesh.quads
            ],
            materials={"laminate": material},
            fixed_dofs=[
                {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
                for node in left
            ],
            loads=loads,
            verification_profile=verification_profile,
        )
        mesh_report = check_mesh(model)
        result = solve_model(model, enforce_policy=verification_profile != "quick")
        offsets = np.asarray(
            [float(item["material_angle_offset_deg"]) for item in result.element_results]
        )
        angle_error = (
            _curved_angle_error(mesh, result.element_results)
            if kind.startswith("curved") and kind != "curved_distorted"
            else 0.0
        )
        return {
            "kind": kind,
            "nx": nx,
            "ny": ny,
            "elements": int(len(mesh.quads)),
            "dofs": int(result.dofs.ndof),
            "weighted_tip_ux": _weighted_displacement(result, right, weights, "UX"),
            "weighted_tip_uz": _weighted_displacement(result, right, weights, "UZ"),
            "orientation_offset_min_deg": float(np.min(offsets)),
            "orientation_offset_max_deg": float(np.max(offsets)),
            "reference_angle_error_deg": angle_error,
            "mesh_status": mesh_report.status,
            "run_verdict": result.run_verdict.value,
            "failed_audit_checks": [
                check.name for check in result.audit.checks if check.status == "FAIL"
            ],
            "residual_relative": float(result.audit.equilibrium["free_relative_residual"]),
        }

    def _plot_convergence(
        self,
        curved: list[dict[str, object]],
        folded: list[dict[str, object]],
        distorted: dict[str, object],
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axis = plt.subplots(figsize=(8.4, 5.2))
        for rows, label, marker in (
            (curved, "Panneau cylindrique", "o"),
            (folded, "Assemblage plie", "s"),
        ):
            final = float(rows[-1]["weighted_tip_uz"])
            axis.semilogx(
                [int(row["elements"]) for row in rows],
                [float(row["weighted_tip_uz"]) / final for row in rows],
                marker=marker,
                label=label,
            )
        axis.scatter(
            [int(distorted["elements"])],
            [float(distorted["weighted_tip_uz"]) / float(curved[-1]["weighted_tip_uz"])],
            marker="x",
            s=70,
            color="#bc4749",
            label="Cylindre distordu 10 %",
        )
        axis.axhline(1.0, color="#555555", linestyle="--", linewidth=1.0)
        axis.set(
            xlabel="Nombre d'elements MITC4",
            ylabel="UZ pondere / UZ du maillage fin",
            title="Convergence des structures composites facettisees",
        )
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_curved_assembly_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_geometries(self, curved: QuadMesh, folded: QuadMesh) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure = plt.figure(figsize=(10.2, 4.8))
        for index, (mesh, title) in enumerate(
            ((curved, "Panneau cylindrique"), (folded, "Assemblage plie")),
            start=1,
        ):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            for quad in mesh.quads:
                loop = np.append(quad, quad[0])
                axis.plot(
                    mesh.nodes[loop, 0],
                    mesh.nodes[loop, 1],
                    mesh.nodes[loop, 2],
                    color="#326fa8",
                    linewidth=0.35,
                )
            axis.set_title(title)
            axis.set(xlabel="X", ylabel="Y", zlabel="Z")
            axis.set_box_aspect((1.0, 0.55, 0.35))
            axis.view_init(elev=24.0, azim=-58.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_curved_assembly_meshes.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Le vecteur global `reference_direction=[1,1,0]` est projete dans",
            "le plan de chaque facette. Son angle local est ajoute aux angles des plis.",
            "",
            "| Modele | Maillage | Elements | UX pointe | UZ pointe | Angle min/max | Residu |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        models = summary["models"]
        rows = models["curved_panel"] + [models["curved_panel_distorted"]] + models["folded_assembly"]
        for row in rows:
            lines.append(
                f"| {row['kind']} | {row['nx']}x{row['ny']} | {row['elements']} | "
                f"{row['weighted_tip_ux']:.6e} | {row['weighted_tip_uz']:.6e} | "
                f"{row['orientation_offset_min_deg']:.3f}/"
                f"{row['orientation_offset_max_deg']:.3f} deg | "
                f"{row['residual_relative']:.3e} |"
            )
        lines.extend(
            [
                "",
                "![Convergence](composite_curved_assembly_convergence.png)",
                "",
                "![Maillages](composite_curved_assembly_meshes.png)",
                "",
                "La campagne verifie la coherence interne, la convergence et la",
                "robustesse numerique a une perturbation de maillage. Le cas perturbe",
                "produit des facettes gauches : son resultat brut est publie, mais le",
                "verdict de qualification reste FAIL, comme exige par la politique.",
                "Une correlation externe",
                "sur coque composite courbe reste necessaire avant de relever la maturite.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _cylindrical_panel(nx: int, ny: int, distortion: float = 0.0) -> QuadMesh:
    length, radius, opening = 1.0, 0.5, radians(60.0)
    nodes = []
    for i in range(nx + 1):
        x = length * i / nx
        for j in range(ny + 1):
            theta = -0.5 * opening + opening * j / ny
            if 0 < i < nx and 0 < j < ny:
                theta += (
                    distortion
                    * opening
                    / ny
                    * sin(np.pi * x / length)
                    * sin(2.0 * np.pi * j / ny)
                )
            nodes.append(
                [
                    x,
                    radius * sin(theta),
                    radius * (cos(theta) - cos(0.5 * opening)),
                ]
            )
    return QuadMesh(np.asarray(nodes), _structured_quads(nx, ny))


def _folded_panel(nx: int, ny: int) -> QuadMesh:
    length, width, fold = 1.0, 0.15, radians(60.0)
    nodes = []
    for i in range(nx + 1):
        x = length * i / nx
        for j in range(2 * ny + 1):
            if j <= ny:
                y, z = width * j / ny, 0.0
            else:
                transverse = width * (j - ny) / ny
                y = width + transverse * cos(fold)
                z = transverse * sin(fold)
            nodes.append([x, y, z])
    return QuadMesh(np.asarray(nodes), _structured_quads(nx, 2 * ny))


def _structured_quads(nx: int, ny: int) -> np.ndarray:
    rows = ny + 1
    return np.asarray(
        [
            [i * rows + j, (i + 1) * rows + j, (i + 1) * rows + j + 1, i * rows + j + 1]
            for i in range(nx)
            for j in range(ny)
        ],
        dtype=int,
    )


def _nodes_at_x(mesh: QuadMesh, value: float) -> list[int]:
    return [
        index
        for index, point in enumerate(mesh.nodes)
        if abs(float(point[0]) - value) <= 1.0e-12
    ]


def _edge_weights_3d(mesh: QuadMesh, nodes: list[int]) -> np.ndarray:
    order = np.argsort(mesh.nodes[nodes, 1])
    ordered_nodes = [nodes[int(index)] for index in order]
    nodes[:] = ordered_nodes
    segments = np.linalg.norm(np.diff(mesh.nodes[nodes], axis=0), axis=1)
    weights = np.zeros(len(nodes))
    weights[:-1] += 0.5 * segments
    weights[1:] += 0.5 * segments
    return weights / np.sum(weights)


def _weighted_displacement(result: object, nodes: list[int], weights: np.ndarray, dof: str) -> float:
    return float(
        sum(
            weights[index] * result.displacements[result.dofs.index(node, dof)]
            for index, node in enumerate(nodes)
        )
    )


def _curved_angle_error(mesh: QuadMesh, results: list[dict[str, object]]) -> float:
    radius, opening = 0.5, radians(60.0)
    errors = []
    for index, result in enumerate(results):
        center = np.mean(mesh.nodes[mesh.quads[index]], axis=0)
        theta = atan2(float(center[1]), float(center[2]) + radius * cos(0.5 * opening))
        expected = degrees(atan2(cos(theta), 1.0))
        errors.append(abs(float(result["material_angle_offset_deg"]) - expected))
    return max(errors, default=0.0)


def _last_increment(rows: list[dict[str, object]], key: str) -> float:
    return _relative(float(rows[-1][key]), float(rows[-2][key]))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "status": "PASS" if value <= limit else "FAIL",
    }


def _equal(identifier: str, value: str, expected: str) -> dict[str, object]:
    return {
        "id": identifier,
        "value": value,
        "expected": expected,
        "status": "PASS" if value == expected else "FAIL",
    }
