"""WP13-02C5 evidence-pipeline guards for the future harmonic campaign.

This module is deliberately limited to evidence construction and validation.
It does not run the WP13-02C harmonic campaign.  The future C6 campaign must
use these helpers before its first solve and must not mutate the pipeline
after that freeze.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_wp13_02c_harmonic_mixed as legacy  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
CONTRACT_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c5_pipeline.schema.json"
C4_RECORD_PATH = ROOT / "qualification/0_2_8/wp13_02c4_owner_gate.json"

CONTRACT_RELATIVE = "qualification/0_2_8/wp13_02c_harmonic_contract.json"
SCHEMA_RELATIVE = "qualification/0_2_8/wp13_02c5_pipeline.schema.json"
PIPELINE_RELATIVE = "scripts/run_wp13_02c5_harmonic_pipeline.py"
LEGACY_MODEL_RELATIVE = "scripts/run_wp13_02c_harmonic_mixed.py"
RUNTIME_RELATIVE = "src/solveur/api/public.py"

_ENERGY_CONTRACT_PATH = "metric_definitions.interface_energy"
_ENERGY_LITERAL_PATTERN = re.compile(
    r"^W_side=conj\(x_interface\)dotg_side;"
    r"mismatch=abs\(W_left\+W_right\)/"
    r"max\(abs\(W_left\)\+abs\(W_right\),max\(norm\(F_free\)\*norm\(x\),1e-30\)"
)


class ContractComplianceError(ValueError):
    """Raised when an evidence producer does not implement the frozen contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_blob_sha(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if math.isnan(number):
            return {"__qf_float__": "NaN"}
        if math.isinf(number):
            return {"__qf_float__": "+Inf" if number > 0.0 else "-Inf"}
        return number
    if isinstance(value, (np.complexfloating, complex)):
        number = complex(value)
        return {
            "__qf_complex__": {
                "real": _json_safe(number.real),
                "imag": _json_safe(number.imag),
            }
        }
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def environment_snapshot() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "executable": sys.executable,
        "pipeline": "WP13-02C5 evidence-only; no harmonic campaign",
    }


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(contract))
    if errors:
        raise ContractComplianceError(f"Frozen contract schema errors: {[error.message for error in errors]}")
    if contract["contract_id"] != "WP13-02C-HARMONIC-MIXED-001":
        raise ContractComplianceError("Unexpected harmonic contract id.")
    return contract


def contract_value(contract: dict[str, Any], path: str) -> Any:
    value: Any = contract
    for component in path.split("."):
        value = value[component]
    return value


def contract_trace(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the literal contract source for every implemented metric/gate."""

    paths = {
        "amplitude_error": "metric_definitions.amplitude_error",
        "phase_error": "metric_definitions.phase_error",
        "frequency_error": "metric_definitions.frequency_error",
        "static_limit_error": "metric_definitions.static_limit_error",
        "residual_relative": "metric_definitions.residual_relative",
        "interface_continuity": "metric_definitions.interface_continuity",
        "interface_force_transfer": "metric_definitions.interface_force_transfer",
        "interface_energy": "metric_definitions.interface_energy",
        "replay_scales": "metric_definitions.replay_scales",
        "oracle_amplitude_gate": "predeclared_gates.oracle_amplitude_relative",
        "oracle_phase_gate": "predeclared_gates.oracle_phase_absolute_rad",
        "residual_gate": "predeclared_gates.harmonic_residual_relative",
        "static_limit_gate": "predeclared_gates.static_limit_relative",
        "resonance_gate": "predeclared_gates.resonance_frequency_relative",
        "interface_continuity_gate": "predeclared_gates.interface_displacement_continuity",
        "interface_force_gate": "predeclared_gates.interface_force_transfer_relative",
        "interface_energy_gate": "predeclared_gates.interface_energy_error_relative",
        "replay_response_gate": "predeclared_gates.replay_response_relative",
        "replay_reaction_gate": "predeclared_gates.replay_reaction_relative",
        "replay_residual_gate": "predeclared_gates.replay_residual_relative_difference",
        "replay_amplitude_gate": "predeclared_gates.replay_amplitude_relative",
        "replay_phase_gate": "predeclared_gates.replay_phase_absolute_rad",
    }
    return {
        name: {
            "contract_path": path,
            "literal_definition": contract_value(contract, path),
            "implementation_source": f"{PIPELINE_RELATIVE}:{name}",
        }
        for name, path in paths.items()
    }


def _energy_literal(contract: dict[str, Any]) -> str:
    literal = str(contract_value(contract, _ENERGY_CONTRACT_PATH))
    compact = re.sub(r"\s+", "", literal)
    if not _ENERGY_LITERAL_PATTERN.fullmatch(compact):
        raise ContractComplianceError(
            f"Unsupported frozen interface-energy definition at {_ENERGY_CONTRACT_PATH}: {literal}"
        )
    return literal


def energy_metric_from_contract(
    contract: dict[str, Any],
    work_left: complex,
    work_right: complex,
    ffree_l2: float,
    x_l2: float,
) -> dict[str, Any]:
    """Evaluate the literal frozen interface-energy definition."""

    literal = _energy_literal(contract)
    wleft_abs = abs(complex(work_left))
    wright_abs = abs(complex(work_right))
    work_sum = wleft_abs + wright_abs
    force_displacement_product = float(ffree_l2) * float(x_l2)
    denominator = max(work_sum, max(force_displacement_product, 1.0e-30))
    numerator = abs(complex(work_left) + complex(work_right))
    return {
        "contract_path": _ENERGY_CONTRACT_PATH,
        "literal_definition": literal,
        "wleft_abs": float(wleft_abs),
        "wright_abs": float(wright_abs),
        "work_sum": float(work_sum),
        "ffree_l2": float(ffree_l2),
        "x_l2": float(x_l2),
        "force_displacement_product": float(force_displacement_product),
        "energy_denominator": float(denominator),
        "energy_numerator": float(numerator),
        "energy_relative": float(numerator / denominator),
        "formula_literal_match": True,
    }


def modal_coordinate(
    phi: np.ndarray,
    mass: np.ndarray,
    response: np.ndarray,
    *,
    phi_source: str,
    mass_source: str,
) -> tuple[complex, dict[str, Any]]:
    """Compute and describe q = phi^H M x inside the frozen pipeline."""

    phi = np.asarray(phi, dtype=float)
    mass = np.asarray(mass, dtype=float)
    response = np.asarray(response, dtype=np.complex128)
    if phi.ndim != 1 or mass.shape != (phi.size, phi.size) or response.shape != phi.shape:
        raise ValueError("Modal projection shapes are incompatible.")
    q = complex(np.vdot(phi, mass @ response))
    return q, {
        "projection_formula": "q = phi^H M x",
        "phi_source": phi_source,
        "phi_digest": canonical_digest(phi),
        "mass_source": mass_source,
        "mass_digest": canonical_digest(mass),
        "normalization": "mass-normalized eigenvector",
        "complex_observed_in_main_pipeline": True,
        "amplitude": float(abs(q)),
        "phase": float(np.angle(q)),
    }


def _raw_model_input(
    base: Any,
    frequencies: list[float],
    alpha: float,
    *,
    material_override: dict[str, Any] | None = None,
    elements_override: list[dict[str, Any]] | None = None,
    loads_override: list[dict[str, Any]] | None = None,
    analysis_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    top_nodes = [
        node
        for node, point in enumerate(base.nodes)
        if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)
    ]
    loads = loads_override if loads_override is not None else [
        {"node": node, "dof": "UZ", "value": 1.0 / len(top_nodes)}
        for node in top_nodes
    ]
    elements = elements_override if elements_override is not None else [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        for element in base.elements
    ]
    materials = {
        key: copy.deepcopy(value) for key, value in base.materials.items()
    }
    if material_override is not None:
        materials = material_override
    analysis: dict[str, Any] = {
        "type": "harmonic_response",
        "method": "direct_frequency",
        "frequencies_hz": frequencies,
        "damping_model": "rayleigh",
        "rayleigh_alpha": alpha,
        "rayleigh_beta": 0.0,
        "mass_formulation": "consistent",
        "harmonic_residual_failure_tolerance": 1.0e-7,
    }
    if analysis_override:
        analysis.update(analysis_override)
    return {
        "nodes": base.nodes.tolist(),
        "elements": elements,
        "materials": materials,
        "fixed_dofs": [
            {"node": condition.node, "dofs": list(condition.dofs)}
            for condition in base.fixed_dofs
        ],
        "loads": loads,
        "analysis": analysis,
        "units": copy.deepcopy(base.units),
    }


def _failure_specs(base: Any, frequency_hz: float, alpha: float) -> dict[str, dict[str, Any]]:
    frequency = [frequency_hz]

    def material_with(**updates: Any) -> dict[str, Any]:
        material = {key: copy.deepcopy(value) for key, value in base.materials.items()}
        material["solid"].update(updates)
        return material

    top_node = next(
        node
        for node, point in enumerate(base.nodes)
        if np.isclose(float(point[2]), 3.0, rtol=0.0, atol=1.0e-14)
    )
    valid_elements = [
        {"type": element.type, "nodes": list(element.nodes), "material": element.material}
        for element in base.elements
    ]
    no_wedge = [item for item in valid_elements if item["type"] != "WEDGE6"]
    pyramid = [
        {
            "type": "PYRAMID5" if index == 0 else element["type"],
            "nodes": list(element["nodes"][:5]) if index == 0 else element["nodes"],
            "material": element["material"],
        }
        for index, element in enumerate(valid_elements)
    ]

    def spec(
        case_id: str,
        payload: dict[str, Any],
        factory: Callable[[], Any],
        expected_type: str,
        message_pattern: str,
        path_pattern: str,
    ) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "actual_input": payload,
            "factory": factory,
            "expected_exception_type": expected_type,
            "expected_message_pattern": message_pattern,
            "expected_execution_path": path_pattern,
        }

    def solve(*, frequencies_hz: list[float] | None = None, **overrides: Any) -> Any:
        return legacy.solve_model(
            legacy.build_harmonic_model(base, frequencies_hz or frequency, alpha, **overrides),
            enforce_policy=False,
        )

    cases: dict[str, dict[str, Any]] = {}
    payload = _raw_model_input(base, [-1.0], alpha)
    cases["invalid_frequency_negative"] = spec(
        "invalid_frequency_negative", payload, lambda: solve(frequencies_hz=[-1.0]),
        "InputValidationError", r"finite and non-negative", r"solve_model.*frequency_grid",
    )
    for case_id, value, label in (
        ("invalid_frequency_nan", float("nan"), "NaN"),
        ("invalid_frequency_inf", float("inf"), "+Inf"),
    ):
        payload = _raw_model_input(base, [value], alpha)
        cases[case_id] = spec(
            case_id, payload, lambda value=value: solve(frequencies_hz=[value]),
            "InputValidationError", r"finite and non-negative", r"solve_model.*frequency_grid",
        )
        cases[case_id]["nonfinite_label"] = label

    payload = _raw_model_input(base, frequency, alpha, material_override=material_with(density=0.0))
    cases["missing_mass"] = spec(
        "missing_mass", payload, lambda: solve(material_override=material_with(density=0.0)),
        "MeshValidationError", r"positive density", r"solve_model.*solve",
    )
    payload = _raw_model_input(base, frequency, alpha, analysis_override={"damping_model": "unknown_model"})
    cases["unsupported_damping"] = spec(
        "unsupported_damping", payload, lambda: solve(analysis_override={"damping_model": "unknown_model"}),
        "InputValidationError", r"Unsupported damping model", r"solve_model.*rayleigh_damping_definition",
    )
    payload = _raw_model_input(
        base, frequency, alpha,
        loads_override=[{"node": top_node, "dof": "BAD", "value": 1.0}],
    )
    cases["malformed_harmonic_load"] = spec(
        "malformed_harmonic_load", payload,
        lambda: solve(loads_override=[{"node": top_node, "dof": "BAD", "value": 1.0}]),
        "ValueError", r"Unknown dof name 'BAD'", r"build_harmonic_model.*normalize_dof_name",
    )
    payload = _raw_model_input(
        base, frequency, alpha,
        loads_override=[{"node": top_node, "dof": "UZ", "value": 1.0 + 1.0j}],
    )
    cases["invalid_complex_real_input"] = spec(
        "invalid_complex_real_input", payload,
        lambda: solve(loads_override=[{"node": top_node, "dof": "UZ", "value": 1.0 + 1.0j}]),
        "TypeError", r"not 'complex'", r"build_harmonic_model.*from_raw",
    )
    payload = _raw_model_input(base, frequency, alpha, elements_override=no_wedge)
    cases["invalid_mixed_interface"] = spec(
        "invalid_mixed_interface", payload,
        lambda: legacy.validate_connected_scope(
            legacy.build_harmonic_model(base, frequency, alpha, elements_override=no_wedge)
        ),
        "InputValidationError", r"requires exactly", r"validate_connected_scope",
    )
    payload = _raw_model_input(base, frequency, alpha, elements_override=pyramid)
    cases["unsupported_family"] = spec(
        "unsupported_family", payload, lambda: solve(elements_override=pyramid),
        "CompatibilityError", r"UNKNOWN_ELEMENT", r"solve_model.*raise_for_error",
    )
    return cases


def execute_failure_contract(
    base: Any,
    frequency_hz: float,
    alpha: float,
    contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    specs = _failure_specs(base, frequency_hz, alpha)
    required = set(contract["failure_contract"]["cases"])
    if set(specs) != required:
        raise ContractComplianceError(f"Failure case set mismatch: {sorted(specs)} != {sorted(required)}")
    executions: dict[str, dict[str, Any]] = {}
    for case_id, item in specs.items():
        payload = item["actual_input"]
        serialized = canonical_json(payload).decode("utf-8")
        observed_type: str | None = None
        observed_message = "No exception was raised."
        path_signature = ""
        try:
            item["factory"]()
        except Exception as exc:  # noqa: BLE001 - evidence observes the public rejection
            observed_type = type(exc).__name__
            observed_message = str(exc)[:1000]
            path_signature = " -> ".join(
                frame.name for frame in traceback.extract_tb(exc.__traceback__)
            )
        type_match = observed_type == item["expected_exception_type"]
        message_match = bool(re.search(item["expected_message_pattern"], observed_message))
        path_match = bool(re.search(item["expected_execution_path"], path_signature))
        executions[case_id] = {
            "case_id": case_id,
            "executed": True,
            "actual_input": _json_safe(payload),
            "actual_input_serialized": serialized,
            "actual_input_digest": sha256_bytes(serialized.encode("utf-8")),
            "descriptive_payload_only_allowed": False,
            "execution_path": path_signature,
            "expected_execution_path": item["expected_execution_path"],
            "expected_exception_type": item["expected_exception_type"],
            "expected_message_pattern": item["expected_message_pattern"],
            "observed_exception_type": observed_type,
            "observed_message": observed_message,
            "type_match": type_match,
            "message_match": message_match,
            "path_match": path_match,
            "failure_any_exception_accepted": False,
            "pass": bool(type_match and message_match and path_match),
        }
    return executions


def validate_failure_record(case_id: str, record: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "case_id", "actual_input", "actual_input_serialized", "actual_input_digest",
        "execution_path", "expected_exception_type", "expected_message_pattern",
        "observed_exception_type", "observed_message", "type_match", "message_match",
        "path_match", "pass",
    }
    errors.extend(f"{case_id}: missing {field}" for field in sorted(required - set(record)))
    if errors:
        return errors
    if record["case_id"] != case_id or record["descriptive_payload_only_allowed"] is not False:
        errors.append(f"{case_id}: descriptive payloads are forbidden")
    if not isinstance(record["actual_input"], dict):
        errors.append(f"{case_id}: actual_input must be a full object")
    else:
        for field in ("nodes", "elements", "materials", "analysis"):
            if field not in record["actual_input"]:
                errors.append(f"{case_id}: actual_input missing {field}")
        if isinstance(record["actual_input"].get("elements"), str):
            errors.append(f"{case_id}: descriptive elements string is not actual input")
    serialized = canonical_json(record["actual_input"]).decode("utf-8")
    if record["actual_input_serialized"] != serialized:
        errors.append(f"{case_id}: serialized input mismatch")
    if record["actual_input_digest"] != sha256_bytes(serialized.encode("utf-8")):
        errors.append(f"{case_id}: input digest mismatch")
    elements = record["actual_input"].get("elements", [])
    families = {element.get("type") for element in elements if isinstance(element, dict)}
    if case_id == "invalid_mixed_interface" and families == set(legacy.FAMILIES):
        errors.append(f"{case_id}: missing-family mutation is absent")
    if case_id == "unsupported_family":
        if not any(element.get("type") == "PYRAMID5" for element in elements if isinstance(element, dict)):
            errors.append(f"{case_id}: injected unsupported family is absent")
        if not any(
            element.get("type") == "PYRAMID5" and len(element.get("nodes", [])) == 5
            for element in elements if isinstance(element, dict)
        ):
            errors.append(f"{case_id}: unsupported-family connectivity is absent")
    if case_id == "malformed_harmonic_load":
        if not any(load.get("dof") == "BAD" for load in record["actual_input"].get("loads", [])):
            errors.append(f"{case_id}: malformed load was not archived")
    if case_id == "invalid_complex_real_input":
        if "__qf_complex__" not in json.dumps(record["actual_input"], sort_keys=True):
            errors.append(f"{case_id}: complex input encoding is absent")
    if not all(record[field] is True for field in ("type_match", "message_match", "path_match", "pass")):
        errors.append(f"{case_id}: strict failure matching did not pass")
    return errors


PIPELINE_COMPONENTS = [
    {"name": "contract", "path": CONTRACT_RELATIVE, "role": "contract source"},
    {"name": "schema", "path": SCHEMA_RELATIVE, "role": "evidence schema"},
    {"name": "main_pipeline", "path": PIPELINE_RELATIVE, "role": "main runner/manifest builder"},
    {"name": "modal_coordinate", "path": PIPELINE_RELATIVE, "role": "frozen modal projection"},
    {"name": "replay_comparator", "path": PIPELINE_RELATIVE, "role": "replay comparator"},
    {"name": "failure_evaluator", "path": PIPELINE_RELATIVE, "role": "failure evaluator"},
    {"name": "post_run_guard", "path": PIPELINE_RELATIVE, "role": "post-run mutation guard"},
    {"name": "model_and_oracle_builder", "path": LEGACY_MODEL_RELATIVE, "role": "frozen model/oracle builder"},
    {"name": "runtime_entrypoint", "path": RUNTIME_RELATIVE, "role": "public runtime entrypoint"},
]


def pipeline_component_digests() -> dict[str, str]:
    digests: dict[str, str] = {}
    for component in PIPELINE_COMPONENTS:
        path = ROOT / component["path"]
        if not path.is_file():
            raise ContractComplianceError(f"Missing pipeline component: {component['path']}")
        digests[component["name"]] = sha256_file(path)
    return digests


def pipeline_combined_digest(digests: dict[str, str]) -> str:
    return canonical_digest({key: digests[key] for key in sorted(digests)})


def build_pipeline_freeze() -> dict[str, Any]:
    digests = pipeline_component_digests()
    return {
        "pipeline_components": copy.deepcopy(PIPELINE_COMPONENTS),
        "pipeline_component_digests": digests,
        "pipeline_combined_digest": pipeline_combined_digest(digests),
        "post_run_pipeline_mutation_allowed": False,
        "post_run_manifest_rewrite_allowed": False,
        "numerical_campaign_started": False,
        "pre_run_freeze_valid": True,
        "repo_sha": git_revision(),
        "environment": environment_snapshot(),
    }


def assert_pipeline_unchanged(freeze: dict[str, Any]) -> None:
    current = pipeline_component_digests()
    if current != freeze["pipeline_component_digests"]:
        raise ContractComplianceError("Pipeline component digest changed after freeze.")
    if pipeline_combined_digest(current) != freeze["pipeline_combined_digest"]:
        raise ContractComplianceError("Combined pipeline digest changed after freeze.")
    if freeze["post_run_pipeline_mutation_allowed"] is not False:
        raise ContractComplianceError("Post-run pipeline mutation must remain disabled.")
    if freeze["post_run_manifest_rewrite_allowed"] is not False:
        raise ContractComplianceError("Post-run manifest rewrite must remain disabled.")


def replay_fields_from_contract(contract: dict[str, Any]) -> list[str]:
    return list(contract["replay"]["fields"])


def validate_pipeline_evidence(manifest: dict[str, Any], contract: dict[str, Any] | None = None) -> list[str]:
    """Validate structural and semantic C5/C6 evidence without running a solve."""

    contract = contract or load_contract()
    schema = json.loads(EVIDENCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(manifest)]
    if manifest.get("contract_id") != contract["contract_id"]:
        errors.append("contract_id does not match frozen contract")
    if manifest.get("contract_values_single_source_of_truth") is not True:
        errors.append("contract values are not declared single-source")
    energy = manifest.get("energy_contract", {})
    if energy.get("contract_path") != _ENERGY_CONTRACT_PATH:
        errors.append("energy contract path is not literal contract path")
    if energy.get("literal_definition") != contract_value(contract, _ENERGY_CONTRACT_PATH):
        errors.append("energy literal definition differs from frozen contract")
    if energy.get("formula_literal_match") is not True:
        errors.append("energy formula literal guard did not pass")
    pipeline = manifest.get("pipeline_freeze", {})
    try:
        assert_pipeline_unchanged(pipeline)
    except (KeyError, ContractComplianceError) as exc:
        errors.append(f"pipeline freeze invalid: {exc}")
    if manifest.get("post_run_manifest_rewrite_allowed") is not False:
        errors.append("post-run manifest rewrite is allowed or unspecified")
    if manifest.get("post_run_pipeline_mutation_allowed") is not False:
        errors.append("post-run pipeline mutation is allowed or unspecified")
    failure_cases = manifest.get("failure_executions", {}).get("cases", {})
    for case_id in contract["failure_contract"]["cases"]:
        if case_id not in failure_cases:
            errors.append(f"missing failure case {case_id}")
        else:
            errors.extend(validate_failure_record(case_id, failure_cases[case_id], contract))
    modal = manifest.get("modal_coordinate_pipeline", {})
    for field in ("phi_source", "phi_digest", "mass_source", "mass_digest", "normalization", "projection_formula"):
        if not modal.get(field):
            errors.append(f"modal pipeline metadata missing {field}")
    if modal.get("projection_formula") != "q = phi^H M x":
        errors.append("modal projection formula is not contractual")
    if modal.get("frozen_pipeline") is not True:
        errors.append("modal coordinate is not produced in frozen pipeline")
    required_replay = set(replay_fields_from_contract(contract))
    replay = manifest.get("replay_pipeline", {})
    if set(replay.get("fields", [])) != required_replay:
        errors.append("replay fields differ from contract")
    if replay.get("runtime_iteration_semantics") == "synthetic":
        errors.append("synthetic iteration metadata is forbidden")
    if "iterations" in replay.get("fields", []) and replay.get("runtime_iteration_semantics") != "observed_runtime_metadata":
        errors.append("synthetic iteration field is present")
    records = manifest.get("historical_owner_records", {})
    if records.get("WP13-02C4") != "qualification/0_2_8/wp13_02c4_owner_gate.json":
        errors.append("WP13-02C4 Owner reject record is missing")
    elif not C4_RECORD_PATH.is_file():
        errors.append("WP13-02C4 Owner reject record file is missing")
    else:
        c4_record = json.loads(C4_RECORD_PATH.read_text(encoding="utf-8"))
        if c4_record.get("verdict") != "REJECT_CONTRACT_VIOLATION":
            errors.append("WP13-02C4 Owner reject record verdict is not preserved")
    return errors


def make_c5_microcheck_manifest(
    contract: dict[str, Any],
    pipeline_freeze: dict[str, Any],
    failure_executions: dict[str, dict[str, Any]],
    energy_check: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 5,
        "record_id": "QF-028-WP13-02C5-PIPELINE-COMPLIANCE",
        "work_package": "WP13-02C5",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "repo_sha": git_revision(),
        "numerical_runs": "NONE",
        "contract_values_single_source_of_truth": True,
        "contract_trace": contract_trace(contract),
        "energy_contract": energy_check,
        "pipeline_freeze": pipeline_freeze,
        "post_run_pipeline_mutation_allowed": False,
        "post_run_manifest_rewrite_allowed": False,
        "failure_executions": {
            "required": len(contract["failure_contract"]["cases"]),
            "executed": len(failure_executions),
            "pass": sum(bool(item["pass"]) for item in failure_executions.values()),
            "silent_fallback_allowed": False,
            "cases": failure_executions,
        },
        "modal_coordinate_pipeline": {
            "frozen_pipeline": True,
            "phi_source": "independent dense K/M eigen-oracle first fixed-base mode",
            "phi_digest": "microcheck-only-not-run",
            "mass_source": "independent dense K/M mass matrix",
            "mass_digest": "microcheck-only-not-run",
            "normalization": "mass-normalized eigenvector",
            "projection_formula": "q = phi^H M x",
        },
        "replay_pipeline": {
            "fields": replay_fields_from_contract(contract),
            "runtime_iteration_semantics": "not_declared_by_harmonic_contract",
            "synthetic_fields": [],
        },
        "historical_owner_records": {
            "WP13-02C4": "qualification/0_2_8/wp13_02c4_owner_gate.json",
        },
        "semantic_checks": {
            "actual_input_serialization": True,
            "failure_semantic_guards": True,
            "pipeline_freeze": True,
            "post_run_mutation_guard": True,
            "modal_coordinate_integrated": True,
            "c4_owner_record": True,
        },
        "evidence_schema_valid": True,
        "integrity": {
            "numerical_source_changed": False,
            "vnv_harness_changed": True,
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "historical_0_2_7_evidence_changed": False,
        },
    }
