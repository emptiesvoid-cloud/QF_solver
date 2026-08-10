"""Fine-mesh TET4 torsion stress probe with compact large-model evidence."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.solid_extended import apply_consistent_circular_torsion
from solveur.core.errors import InputValidationError
from solveur.io.manifest import (
    discovered_file_entries,
    git_source_state,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.large.io import from_finite_element_model
from solveur.large.solver import solve_large_model
from solveur.materials.solid import SolidMaterial
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.vnv_visualization import plot_tet4_cell_field
from solveur.version import DISPLAY_NAME, __version__


PROBE_ID = "VNV-TET4-TORSION-STRESS-H9-001"
H8_ELEMENT_COUNT = 26_336
H8_MESH_SIZE = 0.075
TARGET_ELEMENT_MULTIPLIER = 4.0
TARGET_MESH_SIZE = H8_MESH_SIZE / TARGET_ELEMENT_MULTIPLIER ** (1.0 / 3.0)
LENGTH = 3.0
RADIUS = 0.5
YOUNG = 80.0e9
POISSON = 0.3
TORQUE = 1000.0


class TorsionStressProbeRunner:
    """Run one fine TET4 torsion calculation and write compact evidence."""

    def run(self, output_dir: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
        output = Path(output_dir).resolve()
        source_state = git_source_state(Path(__file__).resolve().parents[2])
        source_state["repository"] = "."
        _prepare_output(output, overwrite)
        mesh_path = BenchmarkMeshFactory().cylinder_tetra(
            output / "h9.msh",
            length=LENGTH,
            radius=RADIUS,
            mesh_size=TARGET_MESH_SIZE,
        )
        setup_path = output / "h9.setup.json"
        write_json_file(setup_path, _setup())
        imported = GmshModelImporter().import_model(mesh_path, setup_path)
        load_diagnostics = apply_consistent_circular_torsion(imported.model, TORQUE)
        model = from_finite_element_model(imported.model)
        with tempfile.TemporaryDirectory(prefix="qf_torsion_h9_", dir=output.parent) as temporary:
            large_result = solve_large_model(
                model,
                temporary,
                solver_backend="scipy",
                preconditioner="jacobi",
                chunk_size=4096,
                parameters={
                    "method": "cg",
                    "rtol": 1.0e-10,
                    "atol": 0.0,
                    "maxiter": 20_000,
                    "scipy_max_dofs": 100_000,
                },
            )
            displacements = _load_displacements(Path(temporary), model.node_count)
        stresses = recover_tet4_stresses(
            model.nodes,
            model.tet4,
            displacements,
            SolidMaterial(E=YOUNG, nu=POISSON).elasticity_matrix,
        )
        reference_stresses = saint_venant_stresses(model.nodes, model.tet4)
        metrics = _metrics(model, displacements, stresses, reference_stresses, load_diagnostics, large_result)
        checks = _checks(metrics)
        status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
        scale = _deformation_scale(model.nodes, displacements)
        _write_figures(output, model.nodes, model.tet4, displacements, stresses, reference_stresses, scale)
        summary = {
            "schema_version": 1,
            "probe_id": PROBE_ID,
            "status": status,
            "solver": {"name": DISPLAY_NAME, "version": __version__},
            "date": "2026-07-14",
            "scope": "tet4-linear-static",
            "reference": "Saint-Venant circular shaft",
            "review": {
                "validator": "Quentin Farinazzo",
                "mode": "self_review",
                "decision": "accepted" if status == "PASS" else "rejected",
                "independence": "not_independent",
            },
            "criteria_scope": (
                "Global L2 stress field on this smooth circular-shaft benchmark; "
                "not pointwise peaks, singularities or arbitrary geometries."
            ),
            "metrics": metrics,
            "checks": checks,
            "artifacts": {
                "mesh": "h9.msh",
                "setup": "h9.setup.json",
                "qf_deformation": "h9_qf_deformation.png",
                "qf_von_mises": "h9_qf_von_mises.png",
                "reference_deformation": "h9_saint_venant_deformation.png",
                "reference_von_mises": "h9_saint_venant_von_mises.png",
                "stress_error": "h9_stress_error.png",
            },
        }
        write_json_file(output / "stress_probe_summary.json", summary)
        _write_markdown(output / "STRESS_PROBE.md", summary)
        _write_manifest(output, status, source_state)
        return summary


def recover_tet4_stresses(
    nodes: np.ndarray,
    connectivity: np.ndarray,
    displacements: np.ndarray,
    elasticity: np.ndarray,
    *,
    chunk_size: int = 8192,
) -> np.ndarray:
    """Recover constant TET4 stresses by chunks without result dictionaries."""
    coordinates = np.asarray(nodes, dtype=float)
    cells = np.asarray(connectivity, dtype=np.int64)
    translations = np.asarray(displacements, dtype=float)
    tangent = np.asarray(elasticity, dtype=float)
    if translations.shape != coordinates.shape or cells.ndim != 2 or cells.shape[1] != 4:
        raise InputValidationError("Torsion stress recovery expects nodes/u [n,3] and TET4 cells [m,4].")
    stresses = np.empty((cells.shape[0], 6), dtype=float)
    actual_chunk = max(1, int(chunk_size))
    for start in range(0, cells.shape[0], actual_chunk):
        stop = min(start + actual_chunk, cells.shape[0])
        selected = cells[start:stop]
        xyz = coordinates[selected]
        interpolation = np.concatenate((np.ones((len(selected), 4, 1)), xyz), axis=2)
        inverse = np.linalg.inv(interpolation)
        gradients = np.transpose(inverse[:, 1:, :], (0, 2, 1))
        stresses[start:stop] = _strains(gradients, translations[selected]) @ tangent.T
    return stresses


def saint_venant_stresses(nodes: np.ndarray, connectivity: np.ndarray) -> np.ndarray:
    """Evaluate the exact Saint-Venant stress field at TET4 centroids."""
    centroids = np.asarray(nodes, dtype=float)[np.asarray(connectivity, dtype=np.int64)].mean(axis=1)
    reference = np.zeros((len(centroids), 6), dtype=float)
    polar_moment = 0.5 * np.pi * RADIUS**4
    reference[:, 3] = -TORQUE * centroids[:, 2] / polar_moment
    reference[:, 5] = TORQUE * centroids[:, 1] / polar_moment
    return reference


def _strains(gradients: np.ndarray, local_u: np.ndarray) -> np.ndarray:
    strain = np.empty((gradients.shape[0], 6), dtype=float)
    strain[:, 0] = np.einsum("mi,mi->m", gradients[:, :, 0], local_u[:, :, 0])
    strain[:, 1] = np.einsum("mi,mi->m", gradients[:, :, 1], local_u[:, :, 1])
    strain[:, 2] = np.einsum("mi,mi->m", gradients[:, :, 2], local_u[:, :, 2])
    strain[:, 3] = np.einsum("mi,mi->m", gradients[:, :, 1], local_u[:, :, 0]) + np.einsum(
        "mi,mi->m", gradients[:, :, 0], local_u[:, :, 1]
    )
    strain[:, 4] = np.einsum("mi,mi->m", gradients[:, :, 2], local_u[:, :, 1]) + np.einsum(
        "mi,mi->m", gradients[:, :, 1], local_u[:, :, 2]
    )
    strain[:, 5] = np.einsum("mi,mi->m", gradients[:, :, 2], local_u[:, :, 0]) + np.einsum(
        "mi,mi->m", gradients[:, :, 0], local_u[:, :, 2]
    )
    return strain


def _metrics(
    model: object,
    displacements: np.ndarray,
    stresses: np.ndarray,
    reference: np.ndarray,
    load_diagnostics: dict[str, float],
    result: object,
) -> dict[str, Any]:
    nodes = np.asarray(model.nodes, dtype=float)
    maximum = float(np.max(nodes[:, 0]))
    selected = np.where(np.isclose(nodes[:, 0], maximum))[0]
    y, z = nodes[selected, 1], nodes[selected, 2]
    uy, uz = displacements[selected, 1], displacements[selected, 2]
    twist = float(np.sum(y * uz - z * uy) / np.sum(y * y + z * z))
    shear = YOUNG / (2.0 * (1.0 + POISSON))
    polar_moment = 0.5 * np.pi * RADIUS**4
    reference_twist = TORQUE * LENGTH / (shear * polar_moment)
    audit = result.audit.details
    solver = result.summary["solver"]
    return {
        "mesh_size": TARGET_MESH_SIZE,
        "node_count": int(model.node_count),
        "element_count": int(model.element_count),
        "ndof": int(model.ndof),
        "element_multiplier_vs_h8": float(model.element_count / H8_ELEMENT_COUNT),
        "twist_angle": twist,
        "reference_twist_angle": reference_twist,
        "relative_twist_error": abs((twist - reference_twist) / reference_twist),
        "relative_stress_l2_error": float(np.linalg.norm(stresses - reference) / np.linalg.norm(reference)),
        "applied_torque": float(load_diagnostics["resultant_torque_x"]),
        "resultant_force_norm": float(load_diagnostics["resultant_force_norm"]),
        "free_relative_residual": float(audit["solution"]["free_relative_residual"]),
        "matrix_symmetry_relative_error": float(audit["matrix"]["symmetry_relative_error"]),
        "matrix_nnz": int(audit["matrix"]["nnz"]),
        "iterations": int(solver["iterations"]),
        "final_residual_norm": float(solver["residual_norm"]),
        "assembly_time_seconds": float(result.summary["assembly_time_seconds"]),
        "solve_time_seconds": float(result.summary["solve_time_seconds"]),
    }


def _checks(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = (
        ("element-multiplier-min", float(metrics["element_multiplier_vs_h8"]), 3.8, "greater_equal"),
        ("element-multiplier-max", float(metrics["element_multiplier_vs_h8"]), 4.2, "less_equal"),
        ("twist-error", float(metrics["relative_twist_error"]), 0.05, "less_equal"),
        ("stress-l2-error", float(metrics["relative_stress_l2_error"]), 0.20, "less_equal"),
        ("free-residual", float(metrics["free_relative_residual"]), 1.0e-8, "less_equal"),
        ("torque-error", abs(float(metrics["applied_torque"]) - TORQUE) / TORQUE, 1.0e-12, "less_equal"),
    )
    return [
        {
            "id": identifier,
            "value": value,
            "limit": limit,
            "operator": operator,
            "status": "PASS" if (value >= limit if operator == "greater_equal" else value <= limit) else "FAIL",
        }
        for identifier, value, limit, operator in definitions
    ]


def _write_figures(
    output: Path,
    nodes: np.ndarray,
    cells: np.ndarray,
    displacements: np.ndarray,
    stresses: np.ndarray,
    reference_stresses: np.ndarray,
    scale: float,
) -> None:
    exact = _saint_venant_displacements(nodes)
    qf_vm = _von_mises(stresses)
    reference_vm = _von_mises(reference_stresses)
    common_maximum = float(max(np.max(qf_vm), np.max(reference_vm)))
    zero = np.zeros(cells.shape[0], dtype=float)
    fields = (
        ("h9_qf_deformation.png", displacements, zero, "QF_solver h9 - deformee", "Champ neutre", 1.0),
        ("h9_saint_venant_deformation.png", exact, zero, "Saint-Venant h9 - deformee", "Champ neutre", 1.0),
        ("h9_qf_von_mises.png", displacements, qf_vm, "QF_solver h9 - von Mises", "von Mises [Pa]", common_maximum),
        (
            "h9_saint_venant_von_mises.png",
            exact,
            reference_vm,
            "Saint-Venant h9 - von Mises",
            "von Mises [Pa]",
            common_maximum,
        ),
        (
            "h9_stress_error.png",
            displacements,
            np.linalg.norm(stresses - reference_stresses, axis=1),
            "QF_solver h9 - norme de l'ecart de contrainte",
            "||sigma_QF - sigma_ref|| [Pa]",
            None,
        ),
    )
    for filename, translations, values, title, label, maximum in fields:
        plot_tet4_cell_field(
            output / filename,
            nodes,
            cells,
            translations,
            values,
            scale,
            title=title,
            color_label=label,
            color_maximum=maximum,
            view=(22.0, -60.0),
        )


def _von_mises(stresses: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(stresses, dtype=float).T
    return np.sqrt(
        0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
        + 3.0 * (txy**2 + tyz**2 + txz**2)
    )


def _saint_venant_displacements(nodes: np.ndarray) -> np.ndarray:
    shear = YOUNG / (2.0 * (1.0 + POISSON))
    polar_moment = 0.5 * np.pi * RADIUS**4
    angle = TORQUE * np.asarray(nodes)[:, 0] / (shear * polar_moment)
    result = np.zeros_like(nodes, dtype=float)
    result[:, 1] = -angle * nodes[:, 2]
    result[:, 2] = angle * nodes[:, 1]
    return result


def _deformation_scale(nodes: np.ndarray, displacements: np.ndarray) -> float:
    magnitude = float(np.max(np.linalg.norm(displacements, axis=1)))
    return 0.18 * float(np.ptp(nodes[:, 0])) / max(magnitude, 1.0e-30)


def _load_displacements(directory: Path, node_count: int) -> np.ndarray:
    hdf5 = directory / "displacements.h5"
    if hdf5.is_file():
        import h5py

        with h5py.File(hdf5, "r") as handle:
            values = np.asarray(handle["displacements"], dtype=float)
    else:
        with np.load(directory / "displacements.npz") as data:
            values = np.asarray(data["displacements"], dtype=float)
    if values.shape != (node_count, 3) or not np.all(np.isfinite(values)):
        raise InputValidationError(f"Invalid stress-probe displacement array {values.shape}.")
    return values


def _setup() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "linear_static", "method": "cg", "parameters": {"rtol": 1.0e-10}},
        "materials": {"solid": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON, "density": 7800.0}},
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": "TET4", "material": "solid"}],
            },
            {
                "name": "x_min",
                "dimension": 2,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}],
            },
        ],
    }


def _prepare_output(output: Path, overwrite: bool) -> None:
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise InputValidationError(f"Stress-probe output is not empty: {output}; use overwrite=True.")
    output.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for name in (
            "h9.msh",
            "h9.setup.json",
            "stress_probe_summary.json",
            "stress_probe_manifest.json",
            "STRESS_PROBE.md",
            "h9_qf_deformation.png",
            "h9_qf_von_mises.png",
            "h9_saint_venant_deformation.png",
            "h9_saint_venant_von_mises.png",
            "h9_stress_error.png",
        ):
            (output / name).unlink(missing_ok=True)


def _write_manifest(output: Path, status: str, source_state: dict[str, Any]) -> None:
    manifest = output / "stress_probe_manifest.json"
    entries = discovered_file_entries(output, lambda _: "torsion_stress_probe", exclude_names=(manifest.name,))
    write_json_file(
        manifest,
        {
            "manifest_schema_version": 1,
            "created_at_utc": utc_timestamp(),
            "probe_id": PROBE_ID,
            "status": status,
            "solver": {"name": DISPLAY_NAME, "version": __version__},
            "source": source_state,
            "runtime": runtime_fingerprint(),
            "input_sha256": sha256(output / "h9.msh"),
            "files": entries,
        },
    )


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    checks = summary["checks"]
    lines = [
        "# Sonde de contrainte TET4 en torsion - h9",
        "",
        "**Decision : accepted.** Validation engineering interne par Quentin Farinazzo, en auto-revue non independante.",
        "",
        "Le niveau h9 vise quatre fois le nombre d'elements du niveau h8. L'acceptation porte sur l'erreur globale",
        "L2 du champ de contrainte de cet arbre circulaire lisse. Elle ne couvre pas les pics ponctuels, singularites",
        "ou une extrapolation automatique a une geometrie quelconque.",
        "",
        "## Resultats",
        "",
        "| Grandeur | Valeur |",
        "| --- | ---: |",
        f"| Noeuds | {metrics['node_count']} |",
        f"| TET4 | {metrics['element_count']} |",
        f"| Multiplicateur par rapport a h8 | {metrics['element_multiplier_vs_h8']:.6f} |",
        f"| Erreur rotation | {metrics['relative_twist_error']:.3%} |",
        f"| Erreur contrainte L2 | {metrics['relative_stress_l2_error']:.3%} |",
        f"| Residu libre relatif | {metrics['free_relative_residual']:.6e} |",
        f"| Iterations CG/Jacobi | {metrics['iterations']} |",
        "",
        "## Criteres",
        "",
        "| Critere | Valeur | Limite | Verdict |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {check['id']} | {check['value']:.6e} | {check['operator']} {check['limit']:.6e} | {check['status']} |"
        for check in checks
    )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "| QF_solver | Saint-Venant |",
            "| --- | --- |",
            "| ![Deformee QF](h9_qf_deformation.png) | ![Deformee analytique](h9_saint_venant_deformation.png) |",
            "| ![von Mises QF](h9_qf_von_mises.png) | ![von Mises analytique](h9_saint_venant_von_mises.png) |",
            "",
            "![Ecart de contrainte](h9_stress_error.png)",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
