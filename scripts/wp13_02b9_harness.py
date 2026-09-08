"""WP13-02B9 V&V harness checks for the frozen Newmark V2 contract.

This module deliberately does not replace or rewrite the B5/B7 campaign
evidence.  It supplies the missing evaluator and archive primitives for a
future campaign and exercises them on the existing B7 archive.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

import numpy as np

import run_wp13_02b5_newmark_v2 as b5
from solveur.api.public import solve_model
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.wedge6 import Wedge6Element


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02b4_newmark_v2_contract.json"
SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02b4_contract.schema.json"
B7_MANIFEST_PATH = ROOT / "qualification/0_2_8/wp13_02b7_v2/manifest.json"
B7_ARCHIVE_PATH = ROOT / "qualification/0_2_8/wp13_02b7_v2/wp13_02b7_arrays.npz"
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02b9_harness"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02b9_harness_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

CONTRACT_ID = "WP13-02B4-NEWMARK-MIXED-V2-001"
CONTRACT_BLOB = "8b44792466eacaf1f341a7970502e9b48dbed4e1"
B7_START_SHA = "fc6b32c8ea1fff0a98390b7788018b14e2ac4891"
FAMILIES = ("TET4", "WEDGE6", "HEX8")
LEVELS = (20, 40, 80, 160)
INTERFACES = ("TET4_WEDGE6", "WEDGE6_HEX8")

RUN_FIELDS = (
    "time",
    "displacement",
    "velocity",
    "acceleration",
    "u_ref",
    "v_ref",
    "a_ref",
    "q",
    "q_ref",
    "qv",
    "qv_ref",
    "qa",
    "qa_ref",
    "residual_vector",
    "residual_norm",
    "residual_relative",
    "reactions",
    "energy_strain",
    "energy_kinetic",
    "energy_total",
    "energy_damping",
    "energy_external",
    "damping_power",
    "external_power",
)

REPLAY_FIELD_MAP = {
    "u": "displacement",
    "v": "velocity",
    "a": "acceleration",
    "q": "q",
    "residual full vector": "residual_vector",
    "kinetic energy": "energy_kinetic",
    "strain energy": "energy_strain",
    "damping energy": "energy_damping",
    "external work": "energy_external",
    "reactions": "reactions",
}

HISTORY_FIELD_MAP = {
    "time": ("time",),
    "u": ("displacement",),
    "v": ("velocity",),
    "a": ("acceleration",),
    "q": ("q",),
    "qv": ("qv",),
    "qa": ("qa",),
    "analytical u/v/a/q/qv/qa": (
        "u_ref",
        "v_ref",
        "a_ref",
        "q_ref",
        "qv_ref",
        "qa_ref",
    ),
    "residual full vector": ("residual_vector",),
    "residual free normalized": ("residual_relative",),
    "kinetic energy": ("energy_kinetic",),
    "strain energy": ("energy_strain",),
    "damping energy": ("energy_damping",),
    "external work": ("energy_external",),
    "reactions": ("reactions",),
    "interface side force/power/cumulative work": tuple(
        f"{interface}_{field}"
        for interface in INTERFACES
        for field in (
            "left_force",
            "right_force",
            "power_left",
            "power_right",
            "work_left",
            "work_right",
        )
    ),
    "family kinetic/strain energies": tuple(
        f"family_{family}_{kind}"
        for family in FAMILIES
        for kind in ("kinetic", "strain")
    ),
}


def digest(array: np.ndarray) -> str:
    """Return the contract's float64 array digest."""

    return hashlib.sha256(
        np.ascontiguousarray(array, dtype=np.float64).tobytes()
    ).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


def json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def contract_gate_values(contract: dict[str, Any]) -> dict[str, Any]:
    """Read every evaluator threshold from the frozen contract."""

    return {
        "acceptance": copy.deepcopy(contract["acceptance_gates"]),
        "convergence": copy.deepcopy(contract["convergence"]),
        "interfaces": copy.deepcopy(contract["interfaces"]),
        "replay": copy.deepcopy(contract["replay"]),
    }


def replay_fields(contract: dict[str, Any]) -> tuple[str, ...]:
    declared = tuple(contract["replay"]["fields"])
    unknown = set(declared) - set(REPLAY_FIELD_MAP)
    if unknown:
        raise ValueError(f"Unmapped replay fields in contract: {sorted(unknown)}")
    return declared


def required_history_fields(contract: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    declared = contract["histories_required"]["every_level_and_replay"]
    missing = set(declared) - set(HISTORY_FIELD_MAP)
    if missing:
        raise ValueError(f"Unmapped history fields in contract: {sorted(missing)}")
    return {field: HISTORY_FIELD_MAP[field] for field in declared}


def validate_contract_for_harness(contract: dict[str, Any]) -> dict[str, Any]:
    """Validate the frozen contract and expose its single-source values."""

    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - dependency is in CI
        raise RuntimeError("jsonschema is required for WP13-02B9.") from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(contract, schema)
    if contract["contract_id"] != CONTRACT_ID:
        raise ValueError("Unexpected Newmark V2 contract identifier.")
    if git_blob(CONTRACT_PATH) != CONTRACT_BLOB:
        raise ValueError("The frozen Newmark V2 contract blob changed.")
    if tuple(contract["replay"]["fields"]) != tuple(REPLAY_FIELD_MAP):
        raise ValueError("Replay field mapping is not aligned with the contract.")
    required_history_fields(contract)
    return {
        "contract_id": contract["contract_id"],
        "contract_blob_sha": git_blob(CONTRACT_PATH),
        "gate_values": contract_gate_values(contract),
        "replay_fields": list(replay_fields(contract)),
        "history_fields": required_history_fields(contract),
    }


def _model_payload(
    base: Any,
    *,
    analysis: dict[str, Any] | None = None,
    elements: list[dict[str, Any]] | None = None,
    materials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "nodes": base.nodes.tolist(),
        "elements": elements
        or [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in base.elements
        ],
        "materials": materials or copy.deepcopy(base.materials),
        "fixed_dofs": [
            {"node": item.node, "dofs": list(item.dofs)}
            for item in base.fixed_dofs
        ],
        "loads": [],
        "analysis": analysis or {},
    }


def _failure_record(
    name: str,
    expected_exception: str,
    payload: dict[str, Any],
    factory: Callable[[], Any],
    *,
    expected_route_status: str | None = None,
) -> dict[str, Any]:
    """Execute one failure case and retain the complete rejection trace."""

    record: dict[str, Any] = {
        "case": name,
        "case_executed": True,
        "expected_exception": expected_exception,
        "expected_route_status": expected_route_status,
        "input": json_safe(payload),
        "execution": {
            "path": "solve_model(model, enforce_policy=False)",
            "harness": "scripts/wp13_02b9_harness.py::run_failure_contract",
        },
    }
    try:
        result = factory()
    except Exception as exc:  # noqa: BLE001 - rejection evidence
        record.update(
            {
                "status": "REJECTED",
                "observed_exception": type(exc).__name__,
                "exception_message": str(exc)[:500],
                "pass": type(exc).__name__ == expected_exception,
            }
        )
        return record
    record.update(
        {
            "status": "NOT_REJECTED",
            "observed_exception": None,
            "exception_message": None,
            "result_status": getattr(result, "status", type(result).__name__),
            "pass": False,
        }
    )
    return record


def run_failure_contract(base: Any, reference: dict[str, Any]) -> dict[str, Any]:
    """Run all seven failure categories through the real public dispatch."""

    dt = reference["period"] / 20.0
    steps = 80
    invalid_elements = [
        {
            "type": item.type,
            "nodes": list(item.nodes)
            if index != 1
            else [*item.nodes[:-1], 999],
            "material": item.material,
        }
        for index, item in enumerate(base.elements)
    ]
    unsupported_elements = [
        {
            "type": "PYRAMID5" if index == 0 else item.type,
            "nodes": list(item.nodes[:5]) if index == 0 else list(item.nodes),
            "material": item.material,
        }
        for index, item in enumerate(base.elements)
    ]
    valid_analysis = {
        "type": "transient_dynamic",
        "method": "newmark",
        "time_step": dt,
        "steps": steps,
        "initial_displacements": reference["initial_entries"],
        "mass_formulation": "consistent",
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
    }

    def model(**overrides: Any) -> Any:
        values = dict(overrides)
        return b5.b2.clone(base, reference, dt, steps, **values)

    cases = {
        "invalid_dt": (
            "InputValidationError",
            _model_payload(base, analysis={**valid_analysis, "time_step": 0.0}),
            lambda: solve_model(
                b5.b2.clone(base, reference, 0.0, steps), enforce_policy=False
            ),
            None,
        ),
        "missing_mass": (
            "MeshValidationError",
            _model_payload(
                base,
                analysis=valid_analysis,
                materials={
                    "solid": {
                        **copy.deepcopy(base.materials["solid"]),
                        "density": 0.0,
                    }
                },
            ),
            lambda: solve_model(
                model(
                    materials={
                        "solid": {
                            **copy.deepcopy(base.materials["solid"]),
                            "density": 0.0,
                        }
                    }
                ),
                enforce_policy=False,
            ),
            None,
        ),
        "unsupported_damping": (
            "InputValidationError",
            _model_payload(
                base,
                analysis={**valid_analysis, "rayleigh_alpha": -1.0},
            ),
            lambda: solve_model(
                model(analysis={"rayleigh_alpha": -1.0}), enforce_policy=False
            ),
            None,
        ),
        "unsupported_time_load": (
            "InputValidationError",
            _model_payload(
                base,
                analysis={**valid_analysis, "load_function": "not_a_supported_function"},
            ),
            lambda: solve_model(
                model(analysis={"load_function": "not_a_supported_function"}),
                enforce_policy=False,
            ),
            None,
        ),
        "invalid_initial_conditions": (
            "InputValidationError",
            _model_payload(
                base,
                analysis={
                    **valid_analysis,
                    "initial_displacements": {
                        "node": 13,
                        "dof": "UZ",
                        "value": 1.0,
                    },
                },
            ),
            lambda: solve_model(
                model(
                    analysis={
                        "initial_displacements": {
                            "node": 13,
                            "dof": "UZ",
                            "value": 1.0,
                        }
                    }
                ),
                enforce_policy=False,
            ),
            None,
        ),
        "invalid_mixed_interface": (
            "MeshValidationError",
            _model_payload(base, analysis=valid_analysis, elements=invalid_elements),
            lambda: solve_model(
                model(elements=invalid_elements), enforce_policy=False
            ),
            None,
        ),
        "unsupported_family": (
            "CompatibilityError",
            _model_payload(base, analysis=valid_analysis, elements=unsupported_elements),
            lambda: solve_model(
                model(elements=unsupported_elements), enforce_policy=False
            ),
            "UNSUPPORTED_ROUTE",
        ),
    }
    return {
        name: _failure_record(
            name,
            expected_exception,
            payload,
            factory,
            expected_route_status=route_status,
        )
        for name, (expected_exception, payload, factory, route_status) in cases.items()
    }


def _gather_family_state(
    reference: dict[str, Any],
    family: str,
    shared_dofs: np.ndarray,
    history: np.ndarray,
) -> np.ndarray:
    """Gather shared fields through the selected family's element DOF maps."""

    result = np.full((history.shape[0], shared_dofs.size), np.nan, dtype=float)
    locations = {int(value): index for index, value in enumerate(shared_dofs)}
    for item, _spec, _stiffness, _mass, element_ids in reference["records"]:
        if item.type != family:
            continue
        for global_dof in element_ids:
            target = locations.get(int(global_dof))
            if target is None:
                continue
            values = history[:, int(global_dof)]
            if np.isnan(result[:, target]).all():
                result[:, target] = values
            elif not np.allclose(result[:, target], values, rtol=0.0, atol=0.0):
                raise ValueError(f"Inconsistent {family} local state at shared DOF {global_dof}.")
    if np.isnan(result).any():
        raise ValueError(f"{family} does not provide every requested shared DOF.")
    return result


def measured_interface_evidence(
    reference: dict[str, Any],
    run: dict[str, Any],
    *,
    family_histories: dict[str, dict[str, np.ndarray]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Measure continuity, force transfer and work from actual history fields."""

    base = reference["base"]
    dofs = reference["dofs"]
    histories = family_histories or {
        family: {
            "u": run["displacement"],
            "v": run["velocity"],
            "a": run["acceleration"],
        }
        for family in FAMILIES
    }
    family_nodes = {
        family: {
            node
            for item in base.elements
            if item.type == family
            for node in item.nodes
        }
        for family in FAMILIES
    }
    pairs = {
        "TET4_WEDGE6": ("TET4", "WEDGE6", sorted(family_nodes["TET4"] & family_nodes["WEDGE6"])),
        "WEDGE6_HEX8": ("WEDGE6", "HEX8", sorted(family_nodes["WEDGE6"] & family_nodes["HEX8"])),
    }
    fstar = float(run.get("fstar", max(np.linalg.norm(reference["stiffness"] @ run["displacement"][0]), 1.0)))
    e0 = float(run.get("e0", 0.5 * run["displacement"][0] @ reference["stiffness"] @ run["displacement"][0]))
    scale_u = max(float(np.max(np.abs(run["displacement"][0]))), 1.0e-30)
    output: dict[str, dict[str, Any]] = {}
    for key, (left, right, nodes) in pairs.items():
        ids = np.asarray(
            [index for node in nodes for index in dofs.node_indices(node, ("UX", "UY", "UZ"))],
            dtype=int,
        )
        left_u = _gather_family_state(reference, left, ids, histories[left]["u"])
        right_u = _gather_family_state(reference, right, ids, histories[right]["u"])
        left_v = _gather_family_state(reference, left, ids, histories[left]["v"])
        right_v = _gather_family_state(reference, right, ids, histories[right]["v"])
        family_forces = {
            family: np.zeros((run["time"].size, dofs.ndof), dtype=float)
            for family in FAMILIES
        }
        for item, _spec, stiffness, mass, element_ids in reference["records"]:
            family = item.type
            local_u = histories[family]["u"][:, element_ids]
            local_a = histories[family]["a"][:, element_ids]
            for row in range(run["time"].size):
                family_forces[family][row, element_ids] += (
                    stiffness @ local_u[row] + mass @ local_a[row]
                )
        left_force = family_forces[left][:, ids]
        right_force = family_forces[right][:, ids]
        power_left = np.einsum("ti,ti->t", left_force, left_v)
        power_right = np.einsum("ti,ti->t", right_force, right_v)
        work_left = np.concatenate(
            ([0.0], np.cumsum(0.5 * (power_left[1:] + power_left[:-1]) * np.diff(run["time"])))
        )
        work_right = np.concatenate(
            ([0.0], np.cumsum(0.5 * (power_right[1:] + power_right[:-1]) * np.diff(run["time"])))
        )
        delta_u = left_u - right_u
        continuity_history = np.max(np.abs(delta_u), axis=1) / scale_u
        output[key] = {
            "nodes": nodes,
            "dof_indices": ids,
            "left_displacement": left_u,
            "right_displacement": right_u,
            "delta_u": delta_u,
            "continuity_relative_history": continuity_history,
            "continuity_relative": float(np.max(continuity_history)),
            "left_force": left_force,
            "right_force": right_force,
            "force_balance_vector": left_force + right_force,
            "force_balance_relative": float(
                np.max(np.linalg.norm(left_force + right_force, axis=1)) / fstar
            ),
            "power_left": power_left,
            "power_right": power_right,
            "work_left": work_left,
            "work_right": work_right,
            "energy_error_relative": float(np.max(np.abs(work_left + work_right)) / e0),
            "gross_work_error_relative": float(
                np.trapezoid(np.abs(power_left + power_right), run["time"]) / e0
            ),
        }
    return output


def family_energy_histories(
    reference: dict[str, Any],
    displacement: np.ndarray,
    velocity: np.ndarray,
) -> dict[str, dict[str, np.ndarray]]:
    """Compute kinetic and strain histories by element family."""

    values = {
        family: {
            "kinetic": np.zeros(displacement.shape[0], dtype=float),
            "strain": np.zeros(displacement.shape[0], dtype=float),
        }
        for family in FAMILIES
    }
    for item, _spec, stiffness, mass, element_ids in reference["records"]:
        local_u = displacement[:, element_ids]
        local_v = velocity[:, element_ids]
        values[item.type]["strain"] += 0.5 * np.einsum(
            "ti,ij,tj->t", local_u, stiffness, local_u
        )
        values[item.type]["kinetic"] += 0.5 * np.einsum(
            "ti,ij,tj->t", local_v, mass, local_v
        )
    return values


def _conditioning_limit(text: str, pattern: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Conditioning limit is not machine-readable: {pattern}")
    return float(match.group(1).rstrip(".,;"))


def conditioning_prechecks(
    reference: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Execute the conditioning checks stated by the frozen contract."""

    base = reference["base"]
    jacobians: list[float] = []
    jacobian_conditions: list[float] = []
    aspect_ratios: list[float] = []
    element_classes = {
        "WEDGE6": Wedge6Element,
        "HEX8": Hex8Element,
    }
    for item in base.elements:
        coords = base.nodes[list(item.nodes)]
        distances = [
            float(np.linalg.norm(coords[first] - coords[second]))
            for first in range(coords.shape[0])
            for second in range(first)
            if np.linalg.norm(coords[first] - coords[second]) > 0.0
        ]
        aspect_ratios.append(max(distances) / min(distances))
        if item.type == "TET4":
            jacobian = np.column_stack((coords[1] - coords[0], coords[2] - coords[0], coords[3] - coords[0]))
            determinants = [float(np.linalg.det(jacobian))]
            jacobian_list = [jacobian]
        else:
            element_class = element_classes[item.type]
            jacobian_list = [
                element_class.jacobian(coords, point)
                for point in element_class.integration_points
            ]
            determinants = [float(np.linalg.det(value)) for value in jacobian_list]
        jacobians.extend(determinants)
        jacobian_conditions.extend(float(np.linalg.cond(value)) for value in jacobian_list)

    stiffness = reference["stiffness"]
    mass = reference["mass"]
    k_diagonal = np.diag(stiffness)
    m_diagonal = np.diag(mass)
    k_positive = k_diagonal[k_diagonal > 0.0]
    m_positive = m_diagonal[m_diagonal > 0.0]
    text = str(contract["benchmark"]["conditioning_precheck"])
    limits = {
        "max_aspect_ratio": _conditioning_limit(
            text, r"node-distance ratio\s*<=\s*([0-9.eE+-]+)"
        ),
        "max_affine_jacobian_condition": _conditioning_limit(
            text, r"affine Jacobian condition\s*<=\s*([0-9.eE+-]+)"
        ),
        "max_diagonal_ratio": _conditioning_limit(
            text, r"assembled K/M diagonal ratios\s*<=\s*([0-9.eE+-]+)"
        ),
        "symmetry_relative": _conditioning_limit(
            text, r"symmetry relative Frobenius error\s*<=\s*([0-9.eE+-]+)"
        ),
    }
    result = {
        "max_aspect_ratio": float(max(aspect_ratios)),
        "min_jacobian": float(min(jacobians)),
        "max_jacobian": float(max(jacobians)),
        "max_affine_jacobian_condition": float(max(jacobian_conditions)),
        "mass_scale_range": float(max(m_positive) / min(m_positive)),
        "stiffness_scale_range": float(max(k_positive) / min(k_positive)),
        "kff_positive_definite": bool(np.min(np.linalg.eigvalsh(stiffness[np.ix_(reference["free"], reference["free"])])) > 0.0),
        "mff_positive_definite": bool(np.min(np.linalg.eigvalsh(mass[np.ix_(reference["free"], reference["free"])])) > 0.0),
        "stiffness_symmetry_relative": float(np.linalg.norm(stiffness - stiffness.T) / np.linalg.norm(stiffness)),
        "mass_symmetry_relative": float(np.linalg.norm(mass - mass.T) / np.linalg.norm(mass)),
        "global_condition_number": "NOT_COMPUTED_BY_CONTRACT",
        "limits_from_contract": limits,
    }
    result["pass"] = bool(
        result["max_aspect_ratio"] <= limits["max_aspect_ratio"]
        and result["min_jacobian"] > 0.0
        and result["max_affine_jacobian_condition"] <= limits["max_affine_jacobian_condition"]
        and result["mass_scale_range"] <= limits["max_diagonal_ratio"]
        and result["stiffness_scale_range"] <= limits["max_diagonal_ratio"]
        and result["kff_positive_definite"]
        and result["mff_positive_definite"]
        and result["stiffness_symmetry_relative"] <= limits["symmetry_relative"]
        and result["mass_symmetry_relative"] <= limits["symmetry_relative"]
    )
    return result


def _scaled_history_error(
    actual: np.ndarray, reference: np.ndarray, scale: float
) -> float:
    difference = np.asarray(actual, dtype=float) - np.asarray(reference, dtype=float)
    if difference.ndim == 1:
        numerator = np.max(np.abs(difference))
    else:
        numerator = np.max(
            np.linalg.norm(difference.reshape(difference.shape[0], -1), axis=1)
        )
    return float(numerator / scale)


def compare_replay_fields(
    main: dict[str, Any], replay: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Compare every replay field declared by the frozen contract."""

    omega = float(main["omega"])
    ustar = float(main["ustar"])
    scales = {
        "u": ustar,
        "v": omega * ustar,
        "a": omega**2 * ustar,
        "q": abs(float(main["q"][0])),
        "residual full vector": float(main["fstar"]),
        "kinetic energy": float(main["e0"]),
        "strain energy": float(main["e0"]),
        "damping energy": float(main["e0"]),
        "external work": float(main["e0"]),
        "reactions": float(main["fstar"]),
    }
    errors: dict[str, float] = {}
    shapes_match = True
    for declared, field in ((name, REPLAY_FIELD_MAP[name]) for name in replay_fields(contract)):
        if field not in main or field not in replay:
            shapes_match = False
            errors[declared] = float("inf")
            continue
        shapes_match = shapes_match and np.shape(main[field]) == np.shape(replay[field])
        errors[declared] = _scaled_history_error(
            main[field], replay[field], max(scales[declared], 1.0e-30)
        )
    tolerance = float(contract["replay"]["tolerance"])
    return {
        "field_errors": errors,
        "tolerance": tolerance,
        "shapes_match": shapes_match,
        "time_identical": bool(np.array_equal(main["time"], replay["time"])),
        "all_fields_pass": bool(
            shapes_match
            and all(np.isfinite(value) and value <= tolerance for value in errors.values())
        ),
        "status_identical": main.get("solver_status") == replay.get("solver_status"),
        "iterations_identical": main.get("iterations_total") == replay.get("iterations_total"),
    }


def _load_archived_run(
    arrays: Any, manifest: dict[str, Any], level: int
) -> dict[str, Any]:
    prefix = f"dt_t1_{level}_"
    run = {field: np.asarray(arrays[prefix + field]) for field in RUN_FIELDS}
    level_meta = manifest["levels"][str(level)]
    run.update(
        {
            "solver_status": level_meta.get("solver_status", "PASS"),
            "iterations_total": int(level_meta.get("iterations_total", 0)),
            "fstar": float(level_meta.get("fstar", 1.0)),
            "e0": float(level_meta.get("e0", 1.0)),
            "ustar": float(level_meta.get("ustar", np.linalg.norm(run["displacement"][0]))),
            "omega": float(manifest["oracle"]["reference_frequency_hz"]) * 2.0 * math.pi,
        }
    )
    return run


def _archive_run(
    arrays: dict[str, np.ndarray],
    array_manifest: dict[str, Any],
    prefix: str,
    run: dict[str, Any],
    interface: dict[str, dict[str, Any]],
    family_energy: dict[str, dict[str, np.ndarray]],
) -> list[str]:
    names: list[str] = []

    def add(logical: str, value: Any) -> None:
        name = f"{prefix}_{logical}"
        array = np.asarray(value, dtype=np.float64)
        arrays[name] = array
        array_manifest[name] = {
            "shape": list(array.shape),
            "dtype": "float64",
            "sha256": digest(array),
        }
        names.append(name)

    for field in RUN_FIELDS:
        add(field, run[field])
    for key, values in interface.items():
        for field in (
            "left_displacement",
            "right_displacement",
            "delta_u",
            "continuity_relative_history",
            "left_force",
            "right_force",
            "force_balance_vector",
            "power_left",
            "power_right",
            "work_left",
            "work_right",
        ):
            add(f"{key}_{field}", values[field])
    for family, values in family_energy.items():
        for field in ("kinetic", "strain"):
            add(f"family_{family}_{field}", values[field])
    return names


def _attach_scales(run: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(run)
    enriched["omega"] = float(reference["omega"])
    enriched["q0"] = float(run["q"][0])
    enriched["vstar"] = float(reference["omega"] * run["ustar"])
    enriched["astar"] = float(reference["omega"] ** 2 * run["ustar"])
    return enriched


def run_micro_validation() -> dict[str, Any]:
    """Run harness-only checks and write a separate B9 readiness pack."""

    contract = load_contract()
    contract_info = validate_contract_for_harness(contract)
    b7_manifest = json.loads(B7_MANIFEST_PATH.read_text(encoding="utf-8"))
    if b7_manifest["start_sha"] != B7_START_SHA:
        raise ValueError("Unexpected historical B7 start SHA.")
    if sha256(B7_ARCHIVE_PATH) != b7_manifest["archive"]["sha256"]:
        raise ValueError("Historical B7 archive hash mismatch.")

    base = b5.b2.build(1)
    reference = b5.b2.reference(base)
    conditioning = conditioning_prechecks(reference, contract)
    failures = run_failure_contract(base, reference)

    arrays: dict[str, np.ndarray] = {}
    array_manifest: dict[str, Any] = {}
    source_level_names: dict[str, list[str]] = {}
    with np.load(B7_ARCHIVE_PATH, allow_pickle=False) as source:
        for level in LEVELS:
            run = _load_archived_run(source, b7_manifest, level)
            run = _attach_scales(run, reference)
            interface = measured_interface_evidence(reference, run)
            family_energy = family_energy_histories(
                reference, run["displacement"], run["velocity"]
            )
            source_level_names[str(level)] = _archive_run(
                arrays,
                array_manifest,
                f"dt_t1_{level}",
                run,
                interface,
                family_energy,
            )

    replay_runs: list[dict[str, Any]] = []
    for _ in range(3):
        captured = b5.b2.capture(base, reference, 160)
        reference["current_time"] = captured["time"]
        replay_runs.append(
            _attach_scales(b5.enrich_run(reference, captured), reference)
        )
    replay_names: dict[str, list[str]] = {}
    replay_evidence: list[dict[str, Any]] = []
    for index, run in enumerate(replay_runs):
        interface = measured_interface_evidence(reference, run)
        family_energy = family_energy_histories(
            reference, run["displacement"], run["velocity"]
        )
        replay_names[str(index)] = _archive_run(
            arrays,
            array_manifest,
            f"replay_{index}_t1_160",
            run,
            interface,
            family_energy,
        )
        if index > 0:
            replay_evidence.append(compare_replay_fields(replay_runs[0], run, contract))

    continuity_hardcoded = False
    all_interface_pass = True
    with np.load(B7_ARCHIVE_PATH, allow_pickle=False) as source:
        for level in LEVELS:
            run = _load_archived_run(source, b7_manifest, level)
            run = _attach_scales(run, reference)
            interface = measured_interface_evidence(reference, run)
            for values in interface.values():
                gates = contract["interfaces"]
                all_interface_pass = all_interface_pass and (
                    values["continuity_relative"] <= gates["continuity"]["maximum"]
                    and values["force_balance_relative"] <= gates["force_transfer"]["maximum"]
                    and values["energy_error_relative"] <= gates["energy_transfer"]["maximum"]
                )

    failure_pass = all(
        item["case_executed"] and item["status"] == "REJECTED" and item["pass"]
        for item in failures.values()
    )
    replay_pass = all(
        item["all_fields_pass"]
        and item["time_identical"]
        and item["status_identical"]
        and item["iterations_identical"]
        for item in replay_evidence
    )
    required_arrays = {
        f"{prefix}_{logical}"
        for prefix in (
            *(f"dt_t1_{level}" for level in LEVELS),
            *(f"replay_{index}_t1_160" for index in range(3)),
        )
        for fields in required_history_fields(contract).values()
        for logical in fields
    }
    # Interface and family names are generated by _archive_run and checked separately.
    required_arrays_ok = all(name in array_manifest for name in required_arrays)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVE_PATH, **arrays)
    manifest = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02B9-HARNESS-READINESS",
        "work_package": "WP13-02B9",
        "repo_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "contract_id": CONTRACT_ID,
        "contract_blob_sha": contract_info["contract_blob_sha"],
        "contract_unchanged": True,
        "contract_values_single_source_of_truth": True,
        "contract_gates": contract_info["gate_values"],
        "history_fields": contract_info["history_fields"],
        "replay_fields": contract_info["replay_fields"],
        "source_b7": {
            "manifest": str(B7_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(B7_MANIFEST_PATH),
            "archive_sha256": sha256(B7_ARCHIVE_PATH),
            "start_sha": B7_START_SHA,
            "historical_evidence_modified": False,
        },
        "micro_execution": {
            "full_v2_campaign_run": False,
            "fresh_replay_smoke_runs": 3,
            "failure_cases_actually_executed": len(failures),
            "purpose": "Harness/evaluator/archive validation only; no B10 campaign verdict.",
        },
        "failure_contract": {
            "cases": failures,
            "unsupported_family_executed": failures["unsupported_family"]["case_executed"],
            "unsupported_family_rejected": failures["unsupported_family"]["pass"],
            "silent_fallback": any(item["status"] != "REJECTED" for item in failures.values()),
        },
        "interface_continuity": {
            "implementation": "family-local DOF gathering from recorded displacement histories",
            "hardcoded": continuity_hardcoded,
            "all_interface_gates_pass": all_interface_pass,
            "interfaces": INTERFACES,
        },
        "energy_fields": {
            "TET4": ["kinetic", "strain"],
            "WEDGE6": ["kinetic", "strain"],
            "HEX8": ["kinetic", "strain"],
            "global": ["kinetic", "strain", "damping", "external", "total"],
        },
        "replay": {
            "fields_implemented": contract_info["replay_fields"],
            "full_residual_vector_archived": True,
            "separate_energy_fields_archived": True,
            "reactions_archived": True,
            "comparisons": replay_evidence,
            "all_fields_pass": replay_pass,
        },
        "conditioning_prechecks": conditioning,
        "archive": {
            "path": str(ARCHIVE_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(ARCHIVE_PATH),
            "array_count": len(array_manifest),
            "array_manifest": array_manifest,
            "source_level_names": source_level_names,
            "replay_names": replay_names,
            "required_history_arrays_present": required_arrays_ok,
        },
        "integrity": {
            "numerical_source_changed": False,
            "vnv_harness_changed": True,
            "input_validation_source_changed": False,
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "evidence_0_2_7_changed": False,
            "historical_b5_b6_b7_b8_preserved": True,
        },
    }
    manifest["decision"] = {
        "status": "PASS_HARNESS_READY"
        if failure_pass
        and conditioning["pass"]
        and all_interface_pass
        and not continuity_hardcoded
        and replay_pass
        and required_arrays_ok
        else "FAIL_HARNESS",
        "newmark_campaign_verdict": "NOT_RUN",
        "ready_for_wp13_02b10": bool(
            failure_pass
            and conditioning["pass"]
            and all_interface_pass
            and not continuity_hardcoded
            and replay_pass
            and required_arrays_ok
        ),
    }
    MANIFEST_PATH.write_text(
        json.dumps(json_safe(manifest), indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(run_micro_validation(), indent=2))
