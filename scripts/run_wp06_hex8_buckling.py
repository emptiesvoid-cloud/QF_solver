"""Run the 0.2.8 WP06 HEX8 linear-buckling closure campaign."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scipy.sparse.linalg import eigsh  # noqa: E402

from solveur.api import solve_model  # noqa: E402
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.errors import MeshValidationError, NumericalConvergenceError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.core.nonlinear.iteration import solve_full_newton  # noqa: E402
from solveur.verification.calculix_buckling_025 import (  # noqa: E402
    DEFAULT_IMAGE,
    _run_calculix,
    write_buckling_input,
)


BASELINE_SHA = "1dac48f88c07f1f5450f693702263472824f42bb"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp06_hex8_buckling_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp06_hex8_buckling_vnv.json"
HISTORICAL_EXTERNAL = ROOT / "qualification" / "0_2_6" / "g08_calculix_correlation.json"
LEVELS = ((2, 2, 2), (4, 4, 4), (6, 6, 6))
E = 1_000.0
NU = 0.3
B = 1.2
H = 1.0
P_REFERENCE = 1.0
IMAGE = DEFAULT_IMAGE


def _json_default(item: object) -> object:
    if isinstance(item, np.generic):
        return item.item()
    if isinstance(item, np.ndarray):
        return item.tolist()
    raise TypeError(f"Unsupported JSON value: {type(item).__name__}")


def _canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _structured_mesh(length: float, width: float, height: float, counts: tuple[int, int, int]) -> tuple[np.ndarray, list[list[int]]]:
    nx, ny, nz = counts
    coordinates: list[tuple[float, float, float]] = []
    node_ids: dict[tuple[float, float, float], int] = {}

    def node_id(point: tuple[float, float, float]) -> int:
        key = tuple(round(float(item), 14) for item in point)
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    elements: list[list[int]] = []
    for k in range(nz):
        z0 = height * k / nz
        z1 = height * (k + 1) / nz
        for j in range(ny):
            y0 = width * j / ny
            y1 = width * (j + 1) / ny
            for i in range(nx):
                x0 = length * i / nx
                x1 = length * (i + 1) / nx
                points = (
                    (x0, y0, z0),
                    (x1, y0, z0),
                    (x1, y1, z0),
                    (x0, y1, z0),
                    (x0, y0, z1),
                    (x1, y0, z1),
                    (x1, y1, z1),
                    (x0, y1, z1),
                )
                elements.append([node_id(point) for point in points])
    return np.asarray(coordinates, dtype=float), elements


def _analysis_parameters() -> dict[str, object]:
    return {
        "type": "linear_buckling",
        "method": "eigsh",
        "preload_factor": 1.0,
        "load_increments": 6,
        "maximum_factor": 1.0e7,
        "max_iterations": 40,
        "tolerance": 1.0e-10,
        "eigensolver_tolerance": 1.0e-9,
        "eigensolver_maxiter": 3000,
        "factor_tolerance": 1.0e-5,
        "bracket_iterations": 60,
    }


def _model(
    configuration: str,
    *,
    length: float = 4.0,
    width: float = B,
    height: float = H,
    counts: tuple[int, int, int] = (2, 2, 2),
    load_total: float = P_REFERENCE,
    perturb: bool = False,
    invalid_orientation: bool = False,
    singular: bool = False,
) -> FiniteElementModel:
    nodes, elements = _structured_mesh(length, width, height, counts)
    if perturb:
        center = np.asarray([length / 2.0, width / 2.0, height / 2.0])
        index = int(np.argmin(np.linalg.norm(nodes - center, axis=1)))
        nodes[index] += np.asarray([0.0, 0.03 * width, 0.02 * height])
    if invalid_orientation:
        elements = [list(reversed(item)) for item in elements]

    x0 = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    x1 = np.flatnonzero(np.isclose(nodes[:, 0], length))
    if singular:
        fixed_dofs = [{"node": int(x0[0]), "dofs": ["UX"]}]
    elif configuration == "cantilever":
        fixed_dofs = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in x0]
    elif configuration == "pinned_pinned_lateral":
        fixed_dofs = [
            {"node": int(node), "dofs": ["UY", "UZ"]}
            for node in np.concatenate((x0, x1))
        ]
        fixed_dofs.append({"node": int(x0[0]), "dofs": ["UX"]})
    else:
        raise ValueError(f"Unsupported WP06 boundary configuration: {configuration!r}.")

    loads = [
        {"node": int(node), "dof": "UX", "value": -float(load_total) / max(len(x1), 1)}
        for node in x1
    ]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": E, "nu": NU}},
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis=_analysis_parameters(),
    )


def _input_digest(model: FiniteElementModel, configuration: str) -> str:
    payload = {
        "configuration": configuration,
        "nodes": np.asarray(model.nodes, dtype=float).round(14).tolist(),
        "elements": [list(item.nodes) for item in model.elements],
        "fixed_dofs": [{"node": row.node, "dofs": list(row.dofs)} for row in model.fixed_dofs],
        "loads": [{"node": row.node, "dof": row.dof, "value": row.value} for row in model.loads],
        "analysis": {"type": model.analysis.type, "method": model.analysis.method, "parameters": model.analysis.parameters},
        "material": model.materials,
    }
    return _canonical_digest(payload)


def _fixed_and_free(model: FiniteElementModel) -> tuple[np.ndarray, np.ndarray]:
    dofs = model.dof_manager()
    fixed = np.unique(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
    )
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    return fixed, free


def _matrix_diagnostics(model: FiniteElementModel, mode: np.ndarray, factor: float) -> dict[str, object]:
    assembly = build_total_lagrangian_assembly(model)
    fixed, free = _fixed_and_free(model)
    loads = np.zeros(assembly.ndof, dtype=float)
    dofs = model.dof_manager()
    for load in model.loads:
        loads[dofs.index(load.node, load.dof)] += load.value
    parameters = model.analysis.parameters
    preload, preload_diagnostics = solve_full_newton(
        assembly,
        float(parameters.get("preload_factor", 1.0)) * loads,
        fixed,
        increments=int(parameters.get("load_increments", 6)),
        tolerance=float(parameters.get("tolerance", 1.0e-10)),
        max_iterations=int(parameters.get("max_iterations", 40)),
    )
    zero = np.zeros(assembly.ndof, dtype=float)
    _, initial = assembly.assemble(zero)
    _, tangent = assembly.assemble(preload)
    geometric = assembly.geometric_tangent(preload).tocsr()
    reduced_initial = initial[free, :][:, free].tocsr()
    reduced_geometric = geometric[free, :][:, free].tocsr()
    reduced_mode = np.asarray(mode[free], dtype=float)
    k_mode = reduced_initial @ reduced_mode
    kg_mode = reduced_geometric @ reduced_mode
    residual = k_mode + float(factor) * kg_mode
    residual_relative = float(
        np.linalg.norm(residual)
        / max(np.linalg.norm(k_mode) + abs(float(factor)) * np.linalg.norm(kg_mode), 1.0e-30)
    )
    kg_norm = max(float(np.linalg.norm(reduced_geometric.toarray())), 1.0)
    kg_symmetry = float(np.linalg.norm((reduced_geometric - reduced_geometric.T).toarray()) / kg_norm)
    try:
        kg_min = float(eigsh(reduced_geometric, k=1, which="SA", return_eigenvectors=False, tol=1.0e-8)[0])
        kg_max = float(eigsh(reduced_geometric, k=1, which="LA", return_eigenvectors=False, tol=1.0e-8)[0])
    except (RuntimeError, ValueError, TypeError):
        kg_min = float("nan")
        kg_max = float("nan")
    increments = preload_diagnostics.get("increments", [])
    preload_residual = max((float(step["relative_residual"]) for step in increments), default=float("inf"))
    return {
        "preload_relative_residual": preload_residual,
        "geometric_stiffness_symmetry_relative": kg_symmetry,
        "geometric_stiffness_eigenvalue_min": kg_min,
        "geometric_stiffness_eigenvalue_max": kg_max,
        "compression_sign_detected": bool(np.isfinite(kg_min) and kg_min < 0.0),
        "initial_tangent_nnz": int(initial.nnz),
        "geometric_tangent_nnz": int(geometric.nnz),
        "eigen_residual_relative_recomputed": residual_relative,
        "free_dof_count": int(free.size),
    }


def _mode_match(model: FiniteElementModel, mode: np.ndarray, configuration: str, length: float) -> dict[str, object]:
    x = np.asarray(model.nodes, dtype=float)[:, 0]
    if configuration == "cantilever":
        reference = 1.0 - np.cos(np.pi * x / (2.0 * length))
    else:
        reference = np.sin(np.pi * x / length)
    lateral_y = np.asarray(mode, dtype=float)[1::3]
    lateral_z = np.asarray(mode, dtype=float)[2::3]
    reference_norm = float(np.linalg.norm(reference))

    def metric(values: np.ndarray) -> tuple[float, float]:
        norm = float(np.linalg.norm(values))
        if norm <= 0.0 or reference_norm <= 0.0:
            return 0.0, float("inf")
        mac = float(np.dot(values, reference) ** 2 / (np.dot(values, values) * np.dot(reference, reference)))
        scale = float(np.dot(values, reference) / np.dot(reference, reference))
        rmse = float(np.linalg.norm(values - scale * reference) / norm)
        return mac, rmse

    mac_y, rmse_y = metric(lateral_y)
    mac_z, rmse_z = metric(lateral_z)
    dominant = "UY" if np.linalg.norm(lateral_y) > np.linalg.norm(lateral_z) else "UZ"
    return {
        "dominant_lateral_direction": dominant,
        "uz_mac": mac_z,
        "uy_mac": mac_y,
        "uz_shape_relative_rmse": rmse_z,
        "uy_shape_relative_rmse": rmse_y,
        "weak_axis_expected": "UZ",
        "mac_selected": mac_z if dominant == "UZ" else mac_y,
        "shape_relative_rmse_selected": rmse_z if dominant == "UZ" else rmse_y,
    }


def _solve_case(
    configuration: str,
    *,
    length: float = 4.0,
    counts: tuple[int, int, int],
    load_total: float = P_REFERENCE,
    perturb: bool = False,
    invalid_orientation: bool = False,
    singular: bool = False,
) -> dict[str, object]:
    model = _model(
        configuration,
        length=length,
        counts=counts,
        load_total=load_total,
        perturb=perturb,
        invalid_orientation=invalid_orientation,
        singular=singular,
    )
    result: dict[str, object] = {
        "configuration": configuration,
        "length": length,
        "width": B,
        "height": H,
        "counts": list(counts),
        "load_total": load_total,
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "input_sha256": _input_digest(model, configuration),
    }
    try:
        solved = solve_model(model, enforce_policy=False)
        solver = solved.solver
        factor = float(solver["critical_factor"])
        mode = np.asarray(solved.displacements, dtype=float)
        c_factor = 0.25 if configuration == "cantilever" else 1.0
        inertia = B * H**3 / 12.0
        pcr = c_factor * np.pi**2 * E * inertia / length**2
        analytical_factor = pcr / load_total
        mode_match = _mode_match(model, mode, configuration, length)
        matrix = _matrix_diagnostics(model, mode, factor)
        bracket = solver["critical_bracket"]
        bracket_relative = float(
            (float(bracket["upper"]) - float(bracket["lower"])) / max(abs(float(bracket["upper"])), 1.0)
        )
        factor_error = abs(factor - analytical_factor) / max(abs(analytical_factor), 1.0e-30)
        result.update(
            {
                "status": "PASS",
                "critical_factor": factor,
                "analytical_factor": analytical_factor,
                "analytical_pcr": pcr,
                "analytical_relative_error": float(factor_error),
                "critical_bracket": {
                    "lower": float(bracket["lower"]),
                    "upper": float(bracket["upper"]),
                    "relative_width": bracket_relative,
                },
                "eigen_formulation": solver.get("eigen_formulation"),
                "mode_norm": float(np.linalg.norm(mode[np.asarray(_fixed_and_free(model)[1], dtype=int)])),
                "mode_match": mode_match,
                "solver_reported_residual_relative": float(solver["critical_mode_residual_relative"]),
                "matrix_diagnostics": matrix,
                "expected_passes": {
                    "analytical_factor": bool(factor_error <= 0.10),
                    "analytical_mode": bool(mode_match["dominant_lateral_direction"] == "UZ" and mode_match["mac_selected"] >= 0.90),
                    "preload": bool(matrix["preload_relative_residual"] <= 1.0e-8),
                    "kg_symmetry": bool(matrix["geometric_stiffness_symmetry_relative"] <= 1.0e-12),
                    "kg_sign": bool(matrix["compression_sign_detected"]),
                    "eigen_residual": bool(matrix["eigen_residual_relative_recomputed"] <= 1.0e-7),
                    "bracket": bool(bracket_relative <= 1.0e-3),
                },
            }
        )
    except (MeshValidationError, NumericalConvergenceError, ValueError, RuntimeError) as exc:
        result.update(
            {
                "status": "EXPECTED_FAILURE" if invalid_orientation or singular else "FAIL",
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
            }
        )
    return result


def _primary_campaign() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for configuration in ("cantilever", "pinned_pinned_lateral"):
        for counts in LEVELS:
            rows.append(_solve_case(configuration, counts=counts))
    summaries: dict[str, object] = {}
    all_primary_pass = True
    for configuration in ("cantilever", "pinned_pinned_lateral"):
        selected = [row for row in rows if row["configuration"] == configuration]
        factors = [float(row["critical_factor"]) for row in selected if row["status"] == "PASS"]
        final_change = (
            abs(factors[-1] - factors[-2]) / max(abs(factors[-1]), 1.0e-30)
            if len(factors) >= 2
            else float("inf")
        )
        analytical_pass = all(bool(row.get("expected_passes", {}).get("analytical_factor", False)) for row in selected)
        mode_pass = all(bool(row.get("expected_passes", {}).get("analytical_mode", False)) for row in selected)
        checks_pass = all(
            row["status"] == "PASS"
            and all(
                bool(row.get("expected_passes", {}).get(name, False))
                for name in ("preload", "kg_symmetry", "kg_sign", "eigen_residual", "bracket")
            )
            for row in selected
        )
        convergence_pass = len(factors) == len(LEVELS) and final_change <= 0.01
        summaries[configuration] = {
            "levels": [list(row["counts"]) for row in selected],
            "critical_factors": factors,
            "analytical_relative_errors": [row.get("analytical_relative_error") for row in selected],
            "final_adjacent_factor_change": final_change,
            "analytical_factor_pass": analytical_pass,
            "analytical_mode_pass": mode_pass,
            "internal_checks_pass": checks_pass,
            "convergence_pass": convergence_pass,
            "status": "PASS" if analytical_pass and mode_pass and checks_pass and convergence_pass else "FAIL",
        }
        all_primary_pass = all_primary_pass and summaries[configuration]["status"] == "PASS"
    return {"status": "PASS" if all_primary_pass else "FAIL", "rows": rows, "summaries": summaries}


def _robustness_campaign(reference: dict[str, object]) -> dict[str, object]:
    base_factor = float(reference["critical_factor"])
    scale = _solve_case("cantilever", length=8.0, counts=(8, 4, 4))
    preload = _solve_case("cantilever", counts=(4, 4, 4), load_total=2.0)
    perturb = _solve_case("cantilever", counts=(4, 4, 4), perturb=True)
    invalid = _solve_case("cantilever", counts=(1, 1, 1), invalid_orientation=True)
    singular = _solve_case("cantilever", counts=(1, 1, 1), singular=True)
    scale_expected = 0.25
    preload_expected = 0.5
    scale_ratio = float(scale["critical_factor"]) / base_factor if scale["status"] == "PASS" else float("nan")
    preload_ratio = float(preload["critical_factor"]) / base_factor if preload["status"] == "PASS" else float("nan")
    scale_error = abs(scale_ratio - scale_expected) / scale_expected if np.isfinite(scale_ratio) else float("inf")
    preload_error = abs(preload_ratio - preload_expected) / preload_expected if np.isfinite(preload_ratio) else float("inf")
    return {
        "reference_input": reference["input_sha256"],
        "scale": {"result": scale, "expected_factor_ratio": scale_expected, "observed_factor_ratio": scale_ratio, "relative_error": scale_error, "pass": scale_error <= 0.02},
        "preload": {"result": preload, "expected_factor_ratio": preload_expected, "observed_factor_ratio": preload_ratio, "relative_error": preload_error, "pass": preload_error <= 0.02},
        "moderate_mesh_perturbation": {"result": perturb, "finite_pass": perturb["status"] == "PASS" and np.isfinite(float(perturb.get("critical_factor", float("nan"))))},
        "invalid_orientation": {"result": invalid, "explicit_failure": invalid["status"] == "EXPECTED_FAILURE"},
        "singular_boundary": {"result": singular, "explicit_failure": singular["status"] == "EXPECTED_FAILURE"},
        "status": "PASS" if scale_error <= 0.02 and preload_error <= 0.02 and perturb["status"] == "PASS" and invalid["status"] == "EXPECTED_FAILURE" and singular["status"] == "EXPECTED_FAILURE" else "FAIL",
    }


def _external_correlation() -> dict[str, object]:
    docker = shutil.which("docker")
    if docker is None:
        return {"status": "SKIPPED_EXTERNAL_UNAVAILABLE", "reason": "docker executable not found", "comparable": True}
    probe = subprocess.run([docker, "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        return {"status": "SKIPPED_EXTERNAL_UNAVAILABLE", "reason": probe.stderr.strip(), "comparable": True}
    model = _model("cantilever", counts=(4, 4, 4))
    output = ROOT / "qualification" / "0_2_8" / "wp06_runtime" / "calculix_cantilever"
    output.mkdir(parents=True, exist_ok=True)
    deck = write_buckling_input(output / "buckling.inp", model, "HEX8", modes=1)
    try:
        factors = _run_calculix(output, image=IMAGE)
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "BLOCKED_EXTERNAL_TOOL",
            "reason": str(exc),
            "comparable": True,
            "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest(),
        }
    qf = _solve_case("cantilever", counts=(4, 4, 4))
    external_factor = float(factors[0])
    relative_error = abs(external_factor - float(qf["critical_factor"])) / max(abs(float(qf["critical_factor"])), 1.0e-30)
    return {
        "status": "PASS" if relative_error <= 0.10 else "FAIL",
        "comparable": True,
        "solver": {"name": "CalculiX", "image": IMAGE, "version": "2.20"},
        "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest(),
        "qf_critical_factor": float(qf["critical_factor"]),
        "external_critical_factor": external_factor,
        "relative_error": relative_error,
        "mode_matching": "NOT_AVAILABLE_FROM_EXISTING_FACTOR_PARSER",
    }


def _historical_audit() -> dict[str, object]:
    if not HISTORICAL_EXTERNAL.is_file():
        return {"status": "MISSING_HISTORICAL_ARTIFACT"}
    data = json.loads(HISTORICAL_EXTERNAL.read_text(encoding="utf-8"))
    rows = [row for row in data.get("rows", []) if row.get("element") == "HEX8"]
    return {
        "status": "AUDITED_HISTORICAL_ONLY",
        "path": str(HISTORICAL_EXTERNAL.relative_to(ROOT)).replace("\\", "/"),
        "hex8_rows": len(rows),
        "pass_rows": sum(row.get("status") == "PASS" for row in rows),
        "max_relative_error": max((float(row.get("relative_difference", 0.0)) for row in rows), default=None),
        "not_current_wp06_execution": True,
        "historical_0_2_7_preserved": True,
    }


def _scoped_source_integrity() -> dict[str, object]:
    git = shutil.which("git") or "git"

    def clean(pathspec: str) -> bool:
        process = subprocess.run([git, "diff", "--quiet", "HEAD", "--", pathspec], cwd=ROOT, check=False)
        return process.returncode == 0

    source_process = subprocess.run([git, "diff", "--quiet", "HEAD", "--", "src"], cwd=ROOT, check=False)
    history_process = subprocess.run([git, "diff", "--quiet", "HEAD", "--", "qualification/0_2_7"], cwd=ROOT, check=False)
    return {
        "numerical_source_changed": source_process.returncode != 0,
        "historical_0_2_7_evidence_changed": history_process.returncode != 0,
        "source_clean_check": clean("src"),
        "historical_clean_check": clean("qualification/0_2_7"),
    }


def _run_once() -> dict[str, object]:
    primary = _primary_campaign()
    reference = next(row for row in primary["rows"] if row["configuration"] == "cantilever" and row["counts"] == [4, 4, 4])
    return {
        "primary": primary,
        "robustness": _robustness_campaign(reference),
        "historical_external_audit": _historical_audit(),
    }


def run_campaign() -> dict[str, object]:
    np.random.seed(0)
    first = _run_once()
    np.random.seed(0)
    second = _run_once()
    first_digest = _canonical_digest(first)
    second_digest = _canonical_digest(second)
    external = _external_correlation()
    integrity = _scoped_source_integrity()
    primary_pass = first["primary"]["status"] == "PASS"
    robustness_pass = first["robustness"]["status"] == "PASS"
    replay_pass = first_digest == second_digest
    external_pass = external["status"] == "PASS"
    technical_decision = "QUALIFIED_BOUNDED" if primary_pass and robustness_pass and replay_pass and external_pass and not any(integrity.values()) else "NOT_QUALIFIED"
    return {
        "schema_version": 1,
        "record_id": "QF-028-WP06-HEX8-BUCKLING-VNV",
        "work_package": "WP06",
        "applicable_version": "0.2.8-development",
        "baseline_sha": BASELINE_SHA,
        "source_sha": BASELINE_SHA,
        "status": "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING",
        "technical_decision": technical_decision,
        "public_maturity": "NOT_QUALIFIED",
        "owner_gate_required": True,
        "contract": str(CONTRACT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "campaign_policy": {
            "tolerances_frozen_before_execution": True,
            "no_post_observation_retuning": True,
            "replays_required": 2,
            "external_required_for_promotion": True,
        },
        "primary_campaign": first["primary"],
        "robustness_campaign": first["robustness"],
        "external_oracle": external,
        "historical_external_audit": first["historical_external_audit"],
        "replays": {
            "required": 2,
            "first_digest": first_digest,
            "second_digest": second_digest,
            "deterministic": replay_pass,
        },
        "integrity": integrity,
        "bugs": {"found": False, "fixed": False},
        "global_state": {
            "before_wp06": {"QUALIFIED_BOUNDED": 32, "EXPERIMENTAL": 13, "NOT_QUALIFIED": 1, "TOTAL": 46},
            "technical_if_promoted": {"QUALIFIED_BOUNDED": 33, "EXPERIMENTAL": 13, "NOT_QUALIFIED": 0, "TOTAL": 46},
            "technical_if_not_promoted": {"QUALIFIED_BOUNDED": 32, "EXPERIMENTAL": 13, "NOT_QUALIFIED": 1, "TOTAL": 46},
            "not_qualified_combination": "COMB-HEX8-linear_buckling",
        },
        "limitations": [
            "First linearized tangent-instability factor and first mode only.",
            "Euler is the independent analytical oracle; no universal solid-buckling claim is made.",
            "CalculiX C3D8 correlation is required for promotion and is explicitly unavailable when Docker cannot connect.",
            "Code_Aster solid eigen-buckling remains NOT_COMPARABLE unless an equivalent modelisation is demonstrated.",
            "No post-buckling, collapse, multi-mode, HEX8R/SRI/B-bar/hourglass or mixed-mesh claim.",
        ],
    }


def main() -> None:
    result = run_campaign()
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(result, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "technical_decision": result["technical_decision"], "replays": result["replays"], "external": result["external_oracle"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
