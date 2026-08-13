"""Controlled TET10 geometry, Jacobian and quadrature verification campaign."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from solveur.elements.solid.tet10 import Tet10Element
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class Tet10GeometryCase:
    """One deterministic midside-node distortion level."""

    name: str
    scale: float
    expected_class: str


class Tet10GeometryQuadratureCampaign:
    """Measure TET10 integration accuracy as the geometric map becomes curved."""

    study_id = "VNV-TET10-GEOMETRY-QUADRATURE-011"
    cases = (
        Tet10GeometryCase("straight", 0.0, "accepted_straight"),
        Tet10GeometryCase("curved", 1.0, "accepted_curved"),
        Tet10GeometryCase("quality_limit", 1.2, "accepted_curved"),
        Tet10GeometryCase("distorted_warning", 7.0, "engineering_warning"),
    )

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3))

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._evaluate(case) for case in self.cases]
        invalid_rejected = self._invalid_geometry_is_rejected()
        checks = self._checks(rows, invalid_rejected)
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "purpose": "TET10 variable-Jacobian and quadrature consolidation",
            "production_rule": {
                "straight": "Hammer degree 2, 4 points",
                "curved": "positive Duffy order 4, 64 points",
                "reference": "positive Duffy order 8, 512 points",
            },
            "cases": rows,
            "invalid_geometry_rejected": invalid_rejected,
            "checks": checks,
            "scope_limit": (
                "Linear elasticity only. Path-dependent TET10 retains four Hammer states and "
                "remains outside this verification scope."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _evaluate(self, case: Tet10GeometryCase) -> dict[str, object]:
        coords = curved_tet10_fixture(case.scale)
        diagnostics = self.element.geometry_diagnostics(coords)
        automatic_rule = self.element.stiffness_integration_rule(coords)
        automatic = self.element.stiffness(coords)
        reference = self.element.stiffness(coords, quadrature_order=8)
        hammer = _stiffness_from_rule(self.element, coords, self.element.hammer_integration_rule())
        scale = max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
        return {
            **asdict(case),
            **diagnostics,
            "automatic_point_count": len(automatic_rule),
            "automatic_relative_error": float(np.linalg.norm(automatic - reference) / scale),
            "hammer_relative_error": float(np.linalg.norm(hammer - reference) / scale),
            "symmetry_error": _symmetry_error(automatic),
            "rigid_mode_residual": _rigid_mode_residual(automatic, coords),
            "affine_strain_error": _affine_strain_error(self.element, coords, automatic_rule),
        }

    def _invalid_geometry_is_rejected(self) -> bool:
        try:
            self.element.stiffness(curved_tet10_fixture(8.0))
        except ValueError as error:
            return "sampled jacobian" in str(error)
        return False

    @staticmethod
    def _checks(rows: list[dict[str, object]], invalid_rejected: bool) -> list[dict[str, object]]:
        straight, curved, limit, warning = rows
        return [
            _upper("straight_jacobian_variation", 1.0 - float(straight["sampled_jacobian_ratio"]), 1.0e-13),
            _equal("straight_uses_four_hammer_points", int(straight["automatic_point_count"]), 4),
            _upper("straight_quadrature_reference_error", float(straight["automatic_relative_error"]), 1.0e-12),
            _equal("curved_uses_positive_duffy_rule", int(curved["automatic_point_count"]), 64),
            _upper("curved_quadrature_reference_error", float(curved["automatic_relative_error"]), 1.0e-5),
            _lower(
                "curved_improvement_over_hammer",
                float(curved["hammer_relative_error"]) / float(curved["automatic_relative_error"]),
                100.0,
            ),
            _upper("quality_limit_mid_edge_deviation", float(limit["mid_edge_deviation_ratio_max"]), 0.05),
            _upper("quality_limit_quadrature_error", float(limit["automatic_relative_error"]), 1.0e-5),
            _upper("distorted_warning_quadrature_error", float(warning["automatic_relative_error"]), 0.01),
            _upper("maximum_symmetry_error", max(float(row["symmetry_error"]) for row in rows), 1.0e-13),
            _upper("maximum_rigid_mode_residual", max(float(row["rigid_mode_residual"]) for row in rows), 1.0e-10),
            _upper("maximum_affine_strain_error", max(float(row["affine_strain_error"]) for row in rows), 1.0e-11),
            _equal("invalid_sampled_jacobian_rejected", int(invalid_rejected), 1),
        ]

    def _plot(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        deviation = [float(row["mid_edge_deviation_ratio_max"]) for row in rows]
        automatic = [float(row["automatic_relative_error"]) for row in rows]
        hammer = [float(row["hammer_relative_error"]) for row in rows]
        figure, axis = plt.subplots(figsize=(7.8, 4.8))
        axis.semilogy(deviation, hammer, "s--", label="Hammer 4 points")
        axis.semilogy(deviation, automatic, "o-", label="Regle automatique")
        axis.axvline(0.05, color="#bc4749", linestyle=":", label="limite qualite courante")
        axis.set(xlabel="Deviation relative maximale des noeuds milieux", ylabel="Erreur relative sur K")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "tet10_quadrature_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Cette etude compare la regle de production a une quadrature Duffy positive d'ordre 8.",
            "",
            "| Cas | Courbure relative | Ratio detJ | Points | Erreur auto | Erreur Hammer |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["cases"]:
            lines.append(
                f"| {row['name']} | {row['mid_edge_deviation_ratio_max']:.6f} | "
                f"{row['sampled_jacobian_ratio']:.6f} | {row['automatic_point_count']} | "
                f"{row['automatic_relative_error']:.3e} | {row['hammer_relative_error']:.3e} |"
            )
        lines.extend(
            [
                "",
                "L'element invalide a Jacobien echantillonne negatif est rejete avant assemblage.",
                "Le cas fortement distordu reste une observation avec avertissement, pas un domaine accepte.",
                "",
                "![Erreur de quadrature TET10](tet10_quadrature_convergence.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _unit_coords() -> np.ndarray:
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
        ],
        dtype=float,
    )


def curved_tet10_fixture(scale: float = 1.0) -> np.ndarray:
    """Return the deterministic curved TET10 geometry shared by V&V studies."""
    offsets = np.zeros((10, 3), dtype=float)
    offsets[4] = [0.0, 0.04, 0.01]
    offsets[5] = [0.02, 0.02, 0.03]
    offsets[6] = [0.03, 0.0, 0.01]
    offsets[7] = [0.03, 0.01, 0.0]
    offsets[8] = [0.01, 0.03, 0.02]
    offsets[9] = [0.02, 0.01, 0.03]
    return _unit_coords() + scale * offsets


def _stiffness_from_rule(
    element: Tet10Element,
    coords: np.ndarray,
    rule: tuple[tuple[tuple[float, float, float, float], float], ...],
) -> np.ndarray:
    stiffness = np.zeros((30, 30), dtype=float)
    for point, weight in rule:
        b_matrix, determinant = element.b_matrix(coords, point)
        stiffness += weight * determinant * (b_matrix.T @ element.material.elasticity_matrix @ b_matrix)
    return 0.5 * (stiffness + stiffness.T)


def _symmetry_error(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix - matrix.T) / max(np.linalg.norm(matrix), np.finfo(float).tiny))


def _rigid_mode_residual(stiffness: np.ndarray, coords: np.ndarray) -> float:
    scale = max(float(np.linalg.norm(stiffness, ord=np.inf)), np.finfo(float).tiny)
    modes = []
    for axis in range(3):
        mode = np.zeros(30)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        modes.append(np.concatenate([np.cross(axis, point) for point in coords]))
    return max(float(np.linalg.norm(stiffness @ mode, ord=np.inf) / scale) for mode in modes)


def _affine_strain_error(
    element: Tet10Element,
    coords: np.ndarray,
    rule: tuple[tuple[tuple[float, float, float, float], float], ...],
) -> float:
    gradient = np.array([[1.0e-3, 2.0e-4, 0.0], [1.0e-4, -4.0e-4, 3.0e-4], [0.0, 2.0e-4, 5.0e-4]])
    displacement = np.concatenate([gradient @ point for point in coords])
    expected = np.array([1.0e-3, -4.0e-4, 5.0e-4, 3.0e-4, 5.0e-4, 0.0])
    errors = [np.linalg.norm(element.b_matrix(coords, point)[0] @ displacement - expected) for point, _ in rule]
    return float(max(errors) / np.linalg.norm(expected))


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}


def _equal(identifier: str, value: int, expected: int) -> dict[str, object]:
    return {"id": identifier, "value": value, "expected": expected, "status": "PASS" if value == expected else "FAIL"}
