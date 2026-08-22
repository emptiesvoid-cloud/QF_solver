"""Independent verification of the laminate A/B/D and inertia operators."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.materials import ClassicalLaminate, LaminaPly, LaminateShellMaterial, OrthotropicLamina
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-LAMINATE-ABD-001"
_RELATIVE_LIMIT = 1.0e-12
_ZERO_COUPLING_LIMIT = 1.0e-9


def run_mitc3_laminate_abd_audit() -> dict[str, Any]:
    """Compare public laminate operators with independent thickness quadrature."""
    lamina = OrthotropicLamina(
        E1=130.0e9,
        E2=9.0e9,
        nu12=0.28,
        G12=5.0e9,
        G13=4.0e9,
        G23=3.5e9,
        density=1550.0,
    )
    symmetric = _laminate(lamina, (0.0, 90.0, 90.0, 0.0))
    unsymmetric = _laminate(lamina, (0.0, 90.0))
    symmetric_reference = _gauss_through_thickness(symmetric)
    unsymmetric_reference = _gauss_through_thickness(unsymmetric)
    symmetric_metrics = _compare_laminate(symmetric, symmetric_reference)
    unsymmetric_metrics = _compare_laminate(unsymmetric, unsymmetric_reference)
    orientation = _orientation_check(lamina)
    checks = {
        "symmetric_abd_matches_independent_quadrature": all(
            value <= (_ZERO_COUPLING_LIMIT if name == "B_relative_difference" else _RELATIVE_LIMIT)
            for name, value in symmetric_metrics.items()
        ),
        "unsymmetric_abd_matches_independent_quadrature": all(
            value <= _RELATIVE_LIMIT for value in unsymmetric_metrics.values()
        ),
        "symmetric_layup_has_zero_b_coupling": symmetric.is_symmetric(1.0e-12),
        "unsymmetric_layup_retains_b_coupling": not unsymmetric.is_symmetric(1.0e-12),
        "abd_positive_definite": bool(np.all(np.linalg.eigvalsh(symmetric.stiffness_matrix) > 0.0)),
        "orientation_projection_exact": orientation["angle_error_deg"] <= 1.0e-12,
        "orientation_material_matrix_matches": orientation["matrix_relative_error"] <= _RELATIVE_LIMIT,
    }
    return {
        "study_id": STUDY_ID,
        "status": "PASS_INDEPENDENT_ABD" if all(checks.values()) else "FAIL",
        "purpose": "independent through-thickness verification of A/B/D, density and projected orientation",
        "integration": "16-point Gauss-Legendre per ply, independently evaluated in z",
        "acceptance": {
            "relative_operator_limit": _RELATIVE_LIMIT,
            "symmetric_zero_coupling_absolute_limit": _ZERO_COUPLING_LIMIT,
        },
        "symmetric_layup": {
            "angles_deg": [0.0, 90.0, 90.0, 0.0],
            "metrics": symmetric_metrics,
            "coupling_norm": float(np.linalg.norm(symmetric.coupling_matrix)),
        },
        "unsymmetric_layup": {
            "angles_deg": [0.0, 90.0],
            "metrics": unsymmetric_metrics,
            "coupling_norm": float(np.linalg.norm(unsymmetric.coupling_matrix)),
        },
        "orientation": orientation,
        "checks": checks,
        "limitations": [
            "This audit verifies the laminate constitutive and inertia operators; it does not prove the shell interpolation or external structural correlation.",
            "Ply failure, delamination, damage and interlaminar stresses remain outside this audit.",
        ],
    }


def write_mitc3_laminate_abd_audit(output_dir: str | Path) -> dict[str, Any]:
    """Write JSON, Markdown and a fingerprinted V&V manifest."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = run_mitc3_laminate_abd_audit()
    (root / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (root / "report.md").write_text(_markdown(report), encoding="utf-8")
    write_vnv_manifest(root, STUDY_ID)
    return report


def _laminate(lamina: OrthotropicLamina, angles: tuple[float, ...]) -> ClassicalLaminate:
    thickness = 2.5e-3
    return ClassicalLaminate(
        tuple(LaminaPly(lamina, thickness, angle, f"ply-{index + 1}") for index, angle in enumerate(angles))
    )


def _gauss_through_thickness(laminate: ClassicalLaminate) -> dict[str, np.ndarray | float]:
    points, weights = np.polynomial.legendre.leggauss(16)
    interfaces = laminate.interfaces
    matrices = {name: np.zeros((3, 3), dtype=float) for name in ("A", "B", "D")}
    surface_density = 0.0
    rotary_density = 0.0
    for index, ply in enumerate(laminate.plies):
        lower, upper = float(interfaces[index]), float(interfaces[index + 1])
        midpoint = 0.5 * (lower + upper)
        half_width = 0.5 * (upper - lower)
        for point, weight in zip(points, weights, strict=True):
            z = midpoint + half_width * float(point)
            differential = half_width * float(weight)
            matrices["A"] += ply.transformed_stiffness * differential
            matrices["B"] += ply.transformed_stiffness * z * differential
            matrices["D"] += ply.transformed_stiffness * z * z * differential
            surface_density += ply.material.density * differential
            rotary_density += ply.material.density * z * z * differential
    return {**matrices, "surface_density": surface_density, "rotary_density": rotary_density}


def _compare_laminate(
    laminate: ClassicalLaminate, reference: dict[str, np.ndarray | float]
) -> dict[str, float]:
    def relative(actual: np.ndarray, expected: np.ndarray) -> float:
        return float(np.linalg.norm(actual - expected) / max(float(np.linalg.norm(expected)), 1.0))

    material = LaminateShellMaterial(laminate)
    return {
        "A_relative_difference": relative(laminate.extensional_matrix, np.asarray(reference["A"])),
        "B_relative_difference": relative(laminate.coupling_matrix, np.asarray(reference["B"])),
        "D_relative_difference": relative(laminate.bending_matrix, np.asarray(reference["D"])),
        "surface_density_relative_difference": abs(material.surface_density - float(reference["surface_density"]))
        / max(abs(float(reference["surface_density"])), 1.0),
        "rotary_density_relative_difference": abs(material.rotary_density - float(reference["rotary_density"]))
        / max(abs(float(reference["rotary_density"])), 1.0),
    }


def _orientation_check(lamina: OrthotropicLamina) -> dict[str, float]:
    angle = 30.0
    reference_direction = np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle)), 0.0])
    material = LaminateShellMaterial(_laminate(lamina, (0.0, 90.0)), reference_direction=reference_direction)
    frame = np.array(
        [[np.cos(np.deg2rad(15.0)), np.sin(np.deg2rad(15.0)), 0.0],
         [-np.sin(np.deg2rad(15.0)), np.cos(np.deg2rad(15.0)), 0.0],
         [0.0, 0.0, 1.0]]
    )
    oriented = material.oriented_for_frame(frame)
    expected_offset = angle - 15.0
    actual_offset = material.orientation_angle_deg(frame)
    expected_matrix = _laminate(lamina, (expected_offset, 90.0 + expected_offset)).extensional_matrix
    return {
        "expected_angle_deg": expected_offset,
        "actual_angle_deg": actual_offset,
        "angle_error_deg": abs(actual_offset - expected_offset),
        "matrix_relative_error": float(
            np.linalg.norm(oriented.membrane_matrix - expected_matrix)
            / max(float(np.linalg.norm(expected_matrix)), 1.0)
        ),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {STUDY_ID}",
        "",
        f"Statut : **{report['status']}**.",
        "",
        "La chaîne matériau est comparée à une intégration indépendante de Gauss-Legendre dans l'épaisseur.",
        "",
        "| Layup | A | B | D | rho*t | rho*I | Couplage B |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, key in (("symétrique [0/90/90/0]", "symmetric_layup"), ("non symétrique [0/90]", "unsymmetric_layup")):
        metrics = report[key]["metrics"]
        lines.append(
            f"| {label} | {metrics['A_relative_difference']:.3e} | {metrics['B_relative_difference']:.3e} | "
            f"{metrics['D_relative_difference']:.3e} | {metrics['surface_density_relative_difference']:.3e} | "
            f"{metrics['rotary_density_relative_difference']:.3e} | {report[key]['coupling_norm']:.3e} |"
        )
    lines.extend(["", "## Orientation projetée", "", json.dumps(report["orientation"], indent=2), "", "## Checks", ""])
    lines.extend(f"- `{name}` : **{'PASS' if value else 'FAIL'}**" for name, value in report["checks"].items())
    lines.extend(["", "## Limites", "", *[f"- {item}" for item in report["limitations"]], ""])
    return "\n".join(lines)
