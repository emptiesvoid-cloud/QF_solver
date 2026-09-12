"""WP04-C1 diagnostic evidence for the preserved failed TET4 campaign.

This is intentionally not a replacement qualification campaign.  It retains
the frozen C mesh and load definitions, adds only finer diagnostic meshes, and
keeps G04-10 failed while establishing whether the observed response is a
discretization trend or a defect in load application, mesh construction, or
the local Total-Lagrangian mechanics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq
from scipy.sparse.linalg import spsolve

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.nonlinear.state import NonlinearState
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
ORIGINAL_SUMMARY = QUALIFICATION / "wp04_c_tet4_structural_summary.json"
DIAGNOSIS_JSON = QUALIFICATION / "wp04_c1_tet4_mesh_diagnosis.json"
DIAGNOSIS_NPZ = QUALIFICATION / "wp04_c1_tet4_mesh_diagnosis_raw.npz"
WP04_C_HOLD_SHA = "a5c3031f6b28b00476e328daff4845a741a5c161"
WP04_C_START_SHA = "48bfa83bc517e031cdab4876970a4f511f744e35"

LENGTH = 4.0
HEIGHT = 0.5
DEPTH = 0.5
YOUNG = 1.0e6
POISSON = 0.30
TOTAL_LOAD = np.asarray([0.0, -50.0, 0.0], dtype=float)
MATERIAL = SolidMaterial(E=YOUNG, nu=POISSON)
NEWTON_TOLERANCE = 1.0e-10
NEWTON_MAX_ITERATIONS = 40
MESH_LEVELS: dict[str, tuple[int, int, int]] = {
    "M1": (8, 4, 4),
    "M2": (16, 8, 8),
    "M3": (24, 12, 12),
    "M4": (32, 16, 16),
    "M5": (48, 24, 24),
}
NONLINEAR_LEVELS = ("M1", "M2", "M3", "M4")


_CACHE: tuple[dict[str, Any], dict[str, np.ndarray]] | None = None


def _structured_tet4_mesh(nx: int, ny: int, nz: int, *, alternate_diagonal: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Return exactly the frozen WP04-C six-TET body-diagonal subdivision."""

    x = np.linspace(0.0, LENGTH, nx + 1)
    y = np.linspace(0.0, HEIGHT, ny + 1)
    z = np.linspace(0.0, DEPTH, nz + 1)
    nodes = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)

    def node_id(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    pattern: tuple[tuple[int, int, int, int], ...] = (
        (0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7),
        (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7),
    )
    if alternate_diagonal:
        # Reflect local x (0<->1, 2<->3, 4<->5, 6<->7), then swap two
        # vertices to restore positive orientation. This is the other body
        # diagonal, not a change to geometry, material, load, or element.
        pattern = tuple((tet[1] ^ 1, tet[0] ^ 1, tet[2] ^ 1, tet[3] ^ 1) for tet in pattern)
    elements: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = [
                    node_id(a, b, c)
                    for a, b, c in (
                        (i, j, k), (i + 1, j, k), (i, j + 1, k), (i + 1, j + 1, k),
                        (i, j, k + 1), (i + 1, j, k + 1), (i, j + 1, k + 1), (i + 1, j + 1, k + 1),
                    )
                ]
                elements.extend([[cube[index] for index in local] for local in pattern])
    return nodes, np.asarray(elements, dtype=int)


def _case(level: str, *, alternate_diagonal: bool = False) -> dict[str, Any]:
    nodes, elements = _structured_tet4_mesh(*MESH_LEVELS[level], alternate_diagonal=alternate_diagonal)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, MATERIAL)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    external = np.zeros(assembly.ndof, dtype=float)
    external.reshape(-1, 3)[loaded_nodes] = TOTAL_LOAD / loaded_nodes.size
    centroids = np.mean(nodes[elements], axis=1)
    stress_mask = (
        (centroids[:, 0] / LENGTH >= 0.40) & (centroids[:, 0] / LENGTH <= 0.60)
        & (centroids[:, 1] / HEIGHT >= 0.75) & (centroids[:, 1] / HEIGHT <= 0.90)
        & (centroids[:, 2] / DEPTH >= 0.25) & (centroids[:, 2] / DEPTH <= 0.75)
    )
    if not np.any(stress_mask):
        raise AssertionError(f"Frozen stress region has no samples for {level}.")
    return {
        "level": level, "alternate_diagonal": alternate_diagonal, "nodes": nodes, "elements": elements, "assembly": assembly,
        "fixed": fixed, "loaded_nodes": loaded_nodes, "external": external,
        "centroids": centroids, "stress_mask": stress_mask,
    }


def _free_dofs(ndof: int, fixed: np.ndarray) -> np.ndarray:
    return np.setdiff1d(np.arange(ndof, dtype=int), fixed)


def _rel(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-12)


def _stress(assembly: TotalLagrangianTet4Assembly, displacement: np.ndarray, mask: np.ndarray) -> tuple[float, float, int]:
    states = assembly.element_states(displacement)
    volumes = np.asarray(assembly.volumes)[mask]
    sigma_xx = np.asarray(states["cauchy_stress"])[mask, 0, 0]
    return float(np.dot(volumes, sigma_xx) / np.sum(volumes)), float(np.sum(volumes)), int(np.count_nonzero(mask))


def _quality(nodes: np.ndarray, elements: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    points = nodes[elements]
    edges = np.stack([points[:, b] - points[:, a] for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))], axis=1)
    squared_sum = np.sum(np.einsum("mei,mei->me", edges, edges), axis=1)
    return 12.0 * (3.0 * np.abs(volumes)) ** (2.0 / 3.0) / squared_sum


def _mesh_audit(case: dict[str, Any]) -> dict[str, Any]:
    nodes = np.asarray(case["nodes"])
    elements = np.asarray(case["elements"])
    volumes = np.asarray(case["assembly"].volumes)
    quality = _quality(nodes, elements, volumes)
    loaded_nodes = np.asarray(case["loaded_nodes"])
    applied = np.asarray(case["external"]).reshape(-1, 3)[loaded_nodes]
    weights = -applied[:, 1]
    centroid = np.average(nodes[loaded_nodes], axis=0, weights=weights)
    return {
        "nodes": int(nodes.shape[0]), "elements": int(elements.shape[0]), "dofs": int(case["assembly"].ndof),
        "total_mesh_volume": float(np.sum(volumes)), "domain_volume": LENGTH * HEIGHT * DEPTH,
        "total_volume_error": float(abs(np.sum(volumes) - LENGTH * HEIGHT * DEPTH) / (LENGTH * HEIGHT * DEPTH)),
        "minimum_volume": float(np.min(volumes)), "maximum_volume": float(np.max(volumes)),
        "orientation_failures": int(np.count_nonzero(volumes <= 0.0)),
        "quality_minimum": float(np.min(quality)), "quality_median": float(np.median(quality)), "quality_maximum": float(np.max(quality)),
        "loaded_face_area": HEIGHT * DEPTH, "loaded_nodes": int(loaded_nodes.size),
        "total_load": np.sum(applied, axis=0).tolist(), "load_centroid": centroid.tolist(),
        "per_node_y_weight": float(TOTAL_LOAD[1] / loaded_nodes.size),
        "load_moment_about_origin": np.sum(np.cross(nodes[loaded_nodes], applied), axis=0).tolist(),
        "stress_region_elements": int(np.count_nonzero(case["stress_mask"])),
        "stress_region_volume": float(np.sum(volumes[case["stress_mask"]])),
        "stress_region_centroid": np.average(case["centroids"][case["stress_mask"]], axis=0, weights=volumes[case["stress_mask"]]).tolist(),
    }


def _linear(level: str, *, alternate_diagonal: bool = False) -> dict[str, Any]:
    case = _case(level, alternate_diagonal=alternate_diagonal)
    assembly = case["assembly"]
    zero = np.zeros(assembly.ndof, dtype=float)
    _, tangent = assembly.assemble(zero, tangent_required=True)
    if tangent is None:
        raise AssertionError("Linear diagnostic requires the zero-state tangent.")
    free = _free_dofs(assembly.ndof, case["fixed"])
    displacement = np.zeros(assembly.ndof, dtype=float)
    displacement[free] = np.asarray(spsolve(tangent[free, :][:, free], case["external"][free]), dtype=float)
    stress, volume, count = _stress(assembly, displacement, case["stress_mask"])
    return {
        "case": case, "displacement": displacement,
        "tip_displacement": float(np.mean(displacement.reshape(-1, 3)[case["loaded_nodes"], 1])),
        "strain_energy": float(0.5 * np.dot(case["external"], displacement)),
        "representative_stress": stress, "stress_region_volume": volume, "stress_region_elements": count,
    }


def _nonlinear(level: str) -> dict[str, Any]:
    case = _case(level)
    assembly = case["assembly"]
    snapshots: list[NonlinearState] = []

    def observe(_step: int, state: NonlinearState) -> None:
        snapshots.append(state.detached_copy())

    displacement, diagnostics = _newton_dead_load(
        assembly, case["external"], case["fixed"], increments=12,
        tolerance=NEWTON_TOLERANCE, max_iterations=NEWTON_MAX_ITERATIONS,
        initial_state=NonlinearState(np.zeros(assembly.ndof, dtype=float), continuation_state={"accepted_step": 0}),
        target_load_factors=[step / 12 for step in range(1, 13)], accepted_state_callback=observe,
    )
    if len(snapshots) != 12:
        raise AssertionError("A diagnostic nonlinear run must expose twelve accepted states.")
    stress, volume, count = _stress(assembly, displacement, case["stress_mask"])
    states = assembly.element_states(displacement)
    return {
        "case": case, "displacement": displacement,
        "tip_displacement": float(np.mean(displacement.reshape(-1, 3)[case["loaded_nodes"], 1])),
        "strain_energy": float(assembly.strain_energy(displacement)), "representative_stress": stress,
        "stress_region_volume": volume, "stress_region_elements": count,
        "minimum_det_f": float(np.min(states["det_f"])),
        "accepted_digest": snapshots[-1].digest,
        "accepted_factors": np.asarray([state.load_factor for state in snapshots]),
        "newton_iterations": int(sum(int(row["iterations"]) for row in diagnostics["increments"])),
    }


def _sequence(rows: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    labels = list(rows)
    values = np.asarray([float(rows[label][key]) for label in labels])
    h = np.asarray([(LENGTH * HEIGHT * DEPTH / rows[label]["case"]["elements"].shape[0]) ** (1.0 / 3.0) for label in labels])
    deltas = [float(_rel(float(values[index + 1]), float(values[index]))) for index in range(len(labels) - 1)]
    return {"levels": labels, "values": values.tolist(), "h": h.tolist(), "successive_relative_deltas": deltas,
            "monotonic_absolute": bool(np.all(np.diff(np.abs(values)) >= 0.0) or np.all(np.diff(np.abs(values)) <= 0.0))}


def _apparent_order(sequence: dict[str, Any]) -> dict[str, Any]:
    h = np.asarray(sequence["h"], dtype=float)
    values = np.asarray(sequence["values"], dtype=float)
    if values.size < 5 or np.any(np.diff(values) == 0.0):
        return {
            "order": None,
            "extrapolated_value": None,
            "asymptotic": False,
            "reason": "At least five levels are required before a nonuniform-ratio order fit is reported.",
        }
    ratio = abs((values[-2] - values[-3]) / (values[-1] - values[-2]))
    def residual(order: float) -> float:
        return (h[-3] ** order - h[-2] ** order) / (h[-2] ** order - h[-1] ** order) - ratio
    try:
        order = float(brentq(residual, 0.05, 8.0))
    except ValueError:
        return {
            "order": None,
            "extrapolated_value": None,
            "asymptotic": False,
            "reason": "The final three nonuniform refinements do not support a stable order fit.",
        }
    coefficient = (values[-2] - values[-1]) / (h[-2] ** order - h[-1] ** order)
    extrapolated = float(values[-1] - coefficient * h[-1] ** order)
    return {
        "order": order,
        "extrapolated_value": extrapolated,
        "asymptotic": False,
        "reason": "Diagnostic fit only: the final observed change remains above the frozen qualification threshold.",
    }


def _summary_row(row: dict[str, Any], *, nonlinear: bool) -> dict[str, Any]:
    output = {
        "tip_displacement": row["tip_displacement"], "strain_energy": row["strain_energy"],
        "representative_stress_sigma_xx": row["representative_stress"],
        "stress_region_volume": row["stress_region_volume"], "stress_region_elements": row["stress_region_elements"],
    }
    if nonlinear:
        output.update({"minimum_det_f": row["minimum_det_f"], "accepted_digest": row["accepted_digest"], "newton_iterations": row["newton_iterations"]})
    return output


def _campaign() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    original = json.loads(ORIGINAL_SUMMARY.read_text(encoding="utf-8"))
    nonlinear = {level: _nonlinear(level) for level in NONLINEAR_LEVELS}
    linear = {level: _linear(level) for level in MESH_LEVELS}
    mesh = {level: _mesh_audit(_case(level)) for level in MESH_LEVELS}
    nonlinear_reproduction = {
        level: {key: _rel(float(nonlinear[level][key]), float(original["mesh_campaign"][level][{"tip_displacement": "tip_displacement", "strain_energy": "strain_energy", "representative_stress": "representative_stress_sigma_xx"}[key]])) for key in ("tip_displacement", "strain_energy", "representative_stress")}
        for level in ("M1", "M2", "M3")
    }
    nonlinear_sequences = {key: _sequence(nonlinear, key) for key in ("tip_displacement", "strain_energy", "representative_stress")}
    linear_sequences = {key: _sequence(linear, key) for key in ("tip_displacement", "strain_energy", "representative_stress")}
    nonlinear_orders = {key: _apparent_order(value) for key, value in nonlinear_sequences.items()}
    linear_orders = {key: _apparent_order(value) for key, value in linear_sequences.items()}
    alternate_diagonal = {}
    for level in ("M2", "M3"):
        alternate = _linear(level, alternate_diagonal=True)
        alternate_diagonal[level] = {
            "alternate_body_diagonal_relative_tip_displacement": _rel(
                alternate["tip_displacement"], linear[level]["tip_displacement"]
            ),
            "alternate_body_diagonal_relative_energy": _rel(
                alternate["strain_energy"], linear[level]["strain_energy"]
            ),
        }
    original_nonlinear_deltas = {key: nonlinear_sequences[key]["successive_relative_deltas"][1] for key in nonlinear_sequences}
    linear_m2_m3 = {key: linear_sequences[key]["successive_relative_deltas"][1] for key in linear_sequences}
    correlation = {key: float(linear_m2_m3[key] / original_nonlinear_deltas[key]) for key in linear_m2_m3}
    # M5 sums 625 equal binary floating-point nodal weights.  The physical
    # resultant is invariant; permit only the resulting round-off summation.
    load_invariant = all(np.allclose(np.asarray(row["total_load"]), TOTAL_LOAD, rtol=0.0, atol=1.0e-11) for row in mesh.values())
    centroid_target = np.asarray([LENGTH, HEIGHT / 2.0, DEPTH / 2.0])
    centroid_invariant = all(np.allclose(np.asarray(row["load_centroid"]), centroid_target, rtol=0.0, atol=1.0e-12) for row in mesh.values())
    stress_target = np.asarray([LENGTH / 2.0, 0.825 * HEIGHT, DEPTH / 2.0])
    stress_invariant = all(np.linalg.norm(np.asarray(row["stress_region_centroid"]) - stress_target) <= 0.05 for row in mesh.values())
    summary = {
        "schema_version": 1, "record_id": "QF-SOLVER-0.2.9-WP04-C1-TET4-MESH-DIAGNOSIS-001",
        "work_package": "WP04-C1", "status": "EXECUTED_TARGETED_DIAGNOSIS",
        "original_failed_campaign": {"hold_sha": WP04_C_HOLD_SHA, "start_sha": WP04_C_START_SHA, "summary": str(ORIGINAL_SUMMARY.relative_to(ROOT)).replace("\\", "/"), "G04-10": "FAIL"},
        "scope": {"production_source_changed": False, "numerical_formulation_changed": False, "maturity_changed": False, "full_test_suite_run": False},
        "original_failure_reproduction_relative": nonlinear_reproduction,
        "linear_campaign": {level: _summary_row(row, nonlinear=False) for level, row in linear.items()},
        "nonlinear_campaign": {level: _summary_row(row, nonlinear=True) for level, row in nonlinear.items()},
        "mesh_audit": mesh,
        "linear_sequences": linear_sequences, "nonlinear_sequences": nonlinear_sequences,
        "linear_apparent_orders": linear_orders, "nonlinear_apparent_orders": nonlinear_orders,
        "linear_nonlinear_m2_m3_correlation": correlation,
        "total_load_invariant": load_invariant, "load_centroid_invariant": centroid_invariant,
        "stress_region_physically_invariant": stress_invariant,
        "tetra_subdivision_bias_audit": {
            **alternate_diagonal,
            "status": "NOT_DETECTED_IN_LINEAR_M2_M3_AUDIT",
        },
        "diagnosis": {"primary": "SLOW_TET4_DISCRETIZATION_CONVERGENCE", "confidence": "MEDIUM", "classification_basis": "Original and extended nonlinear tip/energy/stress sequences are monotone; the linear route exhibits the same compliant-with-refinement direction; mesh volume, orientation, and resultant/centroid audits are invariant. M5 nonlinear was not run because M4 establishes the trend and M5 requires a substantially larger direct sparse factorization."},
        "gate_status": {"G04-10": "FAIL_UNDER_REMEDIATION"},
        "recommendation": "C2_REQUALIFY_WITH_FINER_PREDECLARED_MESHES only after Owner review; retain this failed campaign and establish a separately frozen asymptotic mesh set.",
    }
    arrays: dict[str, np.ndarray] = {}
    for label, row in linear.items():
        arrays[f"linear_{label}_displacement"] = row["displacement"]
    for label, row in nonlinear.items():
        arrays[f"nonlinear_{label}_displacement"] = row["displacement"]
        arrays[f"nonlinear_{label}_accepted_factors"] = row["accepted_factors"]
    _CACHE = (summary, arrays)
    return _CACHE


def test_c1_original_failure_reproduces_exactly() -> None:
    summary, _ = _campaign()
    for row in summary["original_failure_reproduction_relative"].values():
        assert max(row.values()) <= 1.0e-12


def test_c1_linear_and_nonlinear_share_refinement_direction() -> None:
    summary, _ = _campaign()
    for key in ("tip_displacement", "strain_energy", "representative_stress"):
        assert summary["linear_sequences"][key]["monotonic_absolute"]
        assert summary["nonlinear_sequences"][key]["monotonic_absolute"]
        assert summary["linear_nonlinear_m2_m3_correlation"][key] > 0.0


def test_c1_load_and_mesh_audits_are_invariant() -> None:
    summary, _ = _campaign()
    assert summary["total_load_invariant"]
    assert summary["load_centroid_invariant"]
    assert summary["stress_region_physically_invariant"]
    for row in summary["mesh_audit"].values():
        assert row["total_volume_error"] <= 1.0e-13
        assert row["orientation_failures"] == 0


def test_c1_preserves_the_failed_gate() -> None:
    summary, _ = _campaign()
    assert summary["gate_status"]["G04-10"] == "FAIL_UNDER_REMEDIATION"


def test_c1_nonuniform_order_requires_five_levels() -> None:
    result = _apparent_order({"h": [0.4, 0.3, 0.2, 0.1], "values": [1.0, 1.2, 1.3, 1.35]})
    assert result["order"] is None
    assert not result["asymptotic"]


def test_c1_alternate_body_diagonal_is_a_bounded_bias_audit() -> None:
    """Compare the other self-similar body diagonal on the frozen linear case."""

    for level in ("M2", "M3"):
        original = _linear(level)
        alternate = _linear(level, alternate_diagonal=True)
        assert _rel(alternate["tip_displacement"], original["tip_displacement"]) <= 1.0e-8


def test_c1_write_controlled_diagnostic_evidence() -> None:
    json_path, npz_path = write_evidence()
    assert json_path == DIAGNOSIS_JSON
    assert npz_path == DIAGNOSIS_NPZ
    assert json_path.is_file()
    assert npz_path.is_file()


def write_evidence(output_dir: Path | None = None) -> tuple[Path, Path]:
    """Write controlled diagnosis evidence; never overwrite WP04-C evidence."""

    destination = QUALIFICATION if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary, arrays = _campaign()
    json_path = destination / DIAGNOSIS_JSON.name
    npz_path = destination / DIAGNOSIS_NPZ.name
    np.savez_compressed(npz_path, **arrays)  # type: ignore[arg-type]
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return json_path, npz_path


if __name__ == "__main__":
    write_evidence()
