"""Generate authoritative 0.2.6 planning data and synchronized Markdown.

The generator creates controlled definitions, not solver results.  The ten
foundation smoke cases and the bounded G05 execution batch are READY; the
remaining catalog entries stay explicit future work and are not evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "qualification" / "0_2_6"
DOCS = ROOT / "docs" / "verification" / "0_2_6"
BASE_HEAD = "1e6c3e96d1e1366c4cc790546e82769cd9227902"
QUALIFIED_SOURCE = "8047fb63c420609b510beaa1e30aa3ab31d9ad87"


CAMPAIGNS = (
    ("LIN", "Linear solids", "linear_solids", 24, "QUALIFIED_BOUNDED"),
    ("SHL", "Shell / beam / discrete", "shell_beam_discrete", 18, "QUALIFIED_BOUNDED"),
    ("MOD", "Modal", "modal", 14, "QUALIFIED_BOUNDED"),
    ("DYN", "Transient dynamics", "transient_dynamics", 16, "QUALIFIED_BOUNDED"),
    ("HAR", "Harmonic", "harmonic", 12, "QUALIFIED_BOUNDED"),
    ("J2", "Small-strain J2", "small_strain_j2", 24, "QUALIFIED_BOUNDED"),
    ("GNL", "Geometric nonlinear", "geometric_nonlinear", 18, "EXPERIMENTAL"),
    ("BUC", "Buckling", "linear_buckling", 12, "QUALIFIED_BOUNDED"),
    ("CON", "Frictionless contact", "frictionless_contact", 16, "QUALIFIED_BOUNDED"),
    ("CPL", "Existing coupled workflows", "coupled_nonlinear", 10, "EXPERIMENTAL"),
    ("ADV", "Failure / adversarial / metamorphic", "adversarial", 10, "QUALIFIED_BOUNDED"),
    ("SCL", "Scaling profiles", "scaling", 6, "EXPERIMENTAL"),
)


def _ready(
    case_id: str,
    title: str,
    prefix: str,
    capability: str,
    input_model: str,
    analysis_type: str,
    *,
    expected_failure: str | None = None,
    maturity: str = "QUALIFIED_BOUNDED",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "title": title,
        "family": prefix,
        "capability": capability,
        "maturity_target": maturity,
        "description": "A deterministic foundation smoke case reusing a maintained public model.",
        "geometry": {"source": input_model},
        "element_family": "mixed_or_declared_by_model",
        "element_order": None,
        "mesh_strategy": "maintained_example",
        "mesh_levels": ["smoke"],
        "material": {"source": "model"},
        "kinematics": "declared_by_model",
        "analysis_type": analysis_type,
        "load_definition": {"source": "model"},
        "boundary_conditions": {"source": "model"},
        "solver_configuration": {"source": "model"},
        "oracle_types": ["internal_regression"],
        "oracle_ids": [],
        "metrics": ["solver_status", "max_displacement", "residual_norm", "numerical_fingerprint"],
        "tolerance_ids": ["TOL-026-FLOAT-001"],
        "expected_behaviour": "Complete deterministically with finite reported metrics.",
        "expected_failure": expected_failure,
        "random_seed": None,
        "cost_profile": "SMOKE",
        "ci_profiles": ["SMOKE", "STANDARD", "FULL", "RELEASE"],
        "source_reference": "0.2.5 maintained public example",
        "tags": ["foundation", prefix.lower()],
        "known_limitations": ["Foundation smoke evidence is not a new qualification claim."],
        "execution_state": "READY",
        "input_model": input_model,
        "factory_id": None,
    }


SMOKE_CASES = (
    _ready("VNV026-LIN-TET4-STATIC-001", "Linear TET4 static equilibrium", "LIN", "linear_solids", "examples/tet4_static.json", "linear_static"),
    _ready("VNV026-SHL-MITC3-STATIC-001", "MITC3 shell static route", "SHL", "shell_beam_discrete", "examples/mitc3_shell_static.json", "linear_static"),
    _ready("VNV026-MOD-TET4-UNIT-001", "TET4 modal route", "MOD", "modal", "examples/tet4_modal_unit.json", "modal"),
    _ready("VNV026-DYN-TET4-TRANSIENT-001", "TET4 transient dynamic route", "DYN", "transient_dynamics", "examples/tet4_transient_dynamic.json", "transient_dynamic"),
    _ready("VNV026-HAR-TET4-RESPONSE-001", "TET4 harmonic response route", "HAR", "harmonic", "examples/tet4_harmonic_response.json", "harmonic"),
    _ready("VNV026-J2-TET4-PLASTIC-001", "Small-strain J2 TET4 route", "J2", "small_strain_j2", "examples/tet4_elastoplastic_static.json", "nonlinear_static"),
    _ready("VNV026-GNL-TET4-TL-001", "Bounded TET4 geometric nonlinear route", "GNL", "geometric_nonlinear", "examples/tet4_geometric_nonlinear_static.json", "geometric_nonlinear_static", maturity="EXPERIMENTAL"),
    _ready("VNV026-BUC-TET4-SPARSE-001", "Sparse TET4 linear buckling route", "BUC", "linear_buckling", "examples/tet4_linear_buckling.json", "linear_buckling"),
    _ready("VNV026-CON-TET4-PLANE-001", "Bounded frictionless plane contact route", "CON", "frictionless_contact", "examples/frictionless_contact_plane.json", "linear_static"),
    _ready("VNV026-ADV-INVERTED-TET4-001", "Inverted TET4 rejects safely", "ADV", "adversarial", "examples/invalid_inverted_tet4.json", "linear_static", expected_failure="INVALID_ELEMENT", maturity="QUALIFIED_BOUNDED"),
)


def _g05_case(case_id: str, title: str, prefix: str, capability: str, model: str, analysis_type: str, *, load_scale: float = 1.0, analysis: dict[str, Any] | None = None, material_updates: dict[str, dict[str, Any]] | None = None, expected_failure: str | None = None, maturity: str = "QUALIFIED_BOUNDED") -> dict[str, Any]:
    case = _ready(case_id, title, prefix, capability, f"examples/{model}", analysis_type, expected_failure=expected_failure, maturity=maturity)
    case.update({
        "description": "A bounded G05 executable case using a maintained example with declared deterministic variation.",
        "mesh_strategy": "maintained_example_or_declared_variant",
        "mesh_levels": ["controlled"],
        "oracle_types": ["internal_regression", "invariant"],
        "metrics": ["solver_status", "displacement", "reaction", "residual", "numerical_fingerprint"],
        "ci_profiles": ["G05", "FULL", "RELEASE"],
        "tags": ["g05", prefix.lower(), capability],
        "source_reference": "0.2.6 maintained example and controlled G05 variation",
        "known_limitations": ["Executable robustness evidence; does not independently promote capability maturity."],
        "model_overrides": {
            **({"load_scale": load_scale} if load_scale != 1.0 else {}),
            **({"analysis": analysis} if analysis else {}),
            **({"material_updates": material_updates} if material_updates else {}),
        },
    })
    return case


G05_CASES = (
    _g05_case("VNV026-LIN-G05-001", "TET4 static half load", "LIN", "linear_solids", "tet4_static.json", "linear_static", load_scale=0.5),
    _g05_case("VNV026-LIN-G05-002", "TET4 static amplified load", "LIN", "linear_solids", "tet4_static.json", "linear_static", load_scale=1.5),
    _g05_case("VNV026-LIN-G05-003", "TET4 body force", "LIN", "linear_solids", "tet4_body_force.json", "linear_static"),
    _g05_case("VNV026-LIN-G05-004", "TET4 compression", "LIN", "linear_solids", "tet4_compression.json", "linear_static"),
    _g05_case("VNV026-LIN-G05-005", "TET4 pressure", "LIN", "linear_solids", "tet4_pressure.json", "linear_static"),
    _g05_case("VNV026-LIN-G05-006", "TET10 static", "LIN", "linear_solids", "tet10_static.json", "linear_static"),
    _g05_case("VNV026-LIN-G05-007", "TET10 orthotropic static", "LIN", "linear_solids", "tet10_orthotropic_static.json", "linear_static"),
    _g05_case("VNV026-LIN-G05-008", "TET4 orthotropic static", "LIN", "linear_solids", "tet4_orthotropic_static.json", "linear_static"),
    _g05_case("VNV026-SHL-G05-001", "BEAM2 cantilever", "SHL", "shell_beam_discrete", "beam2_cantilever.json", "linear_static"),
    _g05_case("VNV026-SHL-G05-002", "MITC3 shell static", "SHL", "shell_beam_discrete", "mitc3_shell_static.json", "linear_static"),
    _g05_case("VNV026-SHL-G05-003", "MITC4 shell static", "SHL", "shell_beam_discrete", "mitc4_shell_static.json", "linear_static"),
    _g05_case("VNV026-SHL-G05-004", "MITC4 laminate static", "SHL", "shell_beam_discrete", "mitc4_laminate_static.json", "linear_static"),
    _g05_case("VNV026-SHL-G05-005", "RBE2 rigid arm", "SHL", "shell_beam_discrete", "rbe2_rigid_arm.json", "linear_static"),
    _g05_case("VNV026-MOD-G05-001", "TET4 modal unit", "MOD", "modal", "tet4_modal_unit.json", "modal"),
    _g05_case("VNV026-MOD-G05-002", "TET4 modal orthotropic", "MOD", "modal", "tet4_orthotropic_modal.json", "modal"),
    _g05_case("VNV026-MOD-G05-003", "MITC3 modal", "MOD", "modal", "mitc3_modal_cantilever.json", "modal"),
    _g05_case("VNV026-MOD-G05-004", "MITC4 modal", "MOD", "modal", "mitc4_modal_cantilever.json", "modal"),
    _g05_case("VNV026-MOD-G05-005", "TET4 modal repeated mass", "MOD", "modal", "tet4_modal_unit.json", "modal", material_updates={"steel": {"density": 8000.0}}),
    _g05_case("VNV026-DYN-G05-001", "TET4 free vibration", "DYN", "transient_dynamics", "tet4_dynamic_free_vibration.json", "transient_dynamic"),
    _g05_case("VNV026-DYN-G05-002", "TET4 SDOF free vibration", "DYN", "transient_dynamics", "tet4_dynamic_sdof_free_vibration.json", "transient_dynamic"),
    _g05_case("VNV026-DYN-G05-003", "TET4 tabulated transient", "DYN", "transient_dynamics", "tet4_dynamic_tabulated_load.json", "transient_dynamic"),
    _g05_case("VNV026-DYN-G05-004", "TET4 transient", "DYN", "transient_dynamics", "tet4_transient_dynamic.json", "transient_dynamic"),
    _g05_case("VNV026-DYN-G05-005", "MITC3 Newmark", "DYN", "transient_dynamics", "mitc3_newmark_cantilever.json", "transient_dynamic"),
    _g05_case("VNV026-DYN-G05-006", "MITC4 Newmark", "DYN", "transient_dynamics", "mitc4_newmark_cantilever.json", "transient_dynamic"),
    _g05_case("VNV026-HAR-G05-001", "TET4 harmonic response", "HAR", "harmonic", "tet4_harmonic_response.json", "harmonic"),
    _g05_case("VNV026-HAR-G05-002", "TET4 SDOF harmonic", "HAR", "harmonic", "tet4_harmonic_sdof_response.json", "harmonic"),
    _g05_case("VNV026-HAR-G05-003", "MITC3 laminate harmonic", "HAR", "harmonic", "mitc3_laminate_harmonic.json", "harmonic"),
    _g05_case("VNV026-HAR-G05-004", "MITC4 harmonic", "HAR", "harmonic", "mitc4_harmonic_cantilever.json", "harmonic"),
    _g05_case("VNV026-HAR-G05-005", "TET4 harmonic stiffness variant", "HAR", "harmonic", "tet4_harmonic_response.json", "harmonic", material_updates={"steel": {"E": 1100.0}}),
    _g05_case("VNV026-J2-G05-001", "J2 TET4 elastoplastic nominal", "J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static"),
    _g05_case("VNV026-J2-G05-002", "J2 TET4 elastoplastic half load", "J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", load_scale=0.5),
    _g05_case("VNV026-J2-G05-003", "J2 TET4 elastoplastic hardening", "J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", material_updates={"plastic_steel": {"hardening_modulus": 120.0}}),
    _g05_case("VNV026-J2-G05-004", "Nonlinear TET4 route", "J2", "small_strain_j2", "tet4_nonlinear_static.json", "nonlinear_static"),
    _g05_case("VNV026-J2-G05-005", "J2 load-step variant", "J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", analysis={"load_steps": 8}),
    _g05_case("VNV026-J2-G05-006", "J2 stricter iteration budget", "J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", analysis={"max_iterations": 100}),
    _g05_case("VNV026-GNL-G05-001", "TET4 geometric nonlinear nominal", "GNL", "geometric_nonlinear", "tet4_geometric_nonlinear_static.json", "geometric_nonlinear_static", maturity="EXPERIMENTAL"),
    _g05_case("VNV026-GNL-G05-002", "TET4 geometric nonlinear half load", "GNL", "geometric_nonlinear", "tet4_geometric_nonlinear_static.json", "geometric_nonlinear_static", load_scale=0.5, maturity="EXPERIMENTAL"),
    _g05_case("VNV026-GNL-G05-003", "TET4 geometric nonlinear steps", "GNL", "geometric_nonlinear", "tet4_geometric_nonlinear_static.json", "geometric_nonlinear_static", analysis={"load_steps": 8}, maturity="EXPERIMENTAL"),
    _g05_case("VNV026-BUC-G05-001", "TET4 sparse buckling", "BUC", "linear_buckling", "tet4_linear_buckling.json", "linear_buckling"),
    _g05_case("VNV026-BUC-G05-002", "TET4 buckling load variant", "BUC", "linear_buckling", "tet4_linear_buckling.json", "linear_buckling", load_scale=0.75),
    _g05_case("VNV026-BUC-G05-003", "TET4 buckling modes variant", "BUC", "linear_buckling", "tet4_linear_buckling.json", "linear_buckling", analysis={"modes": 2}),
    _g05_case("VNV026-CON-G05-001", "Frictionless plane contact", "CON", "frictionless_contact", "frictionless_contact_plane.json", "linear_static"),
    _g05_case("VNV026-CON-G05-002", "Frictionless surface contact", "CON", "frictionless_contact", "frictionless_contact_surface.json", "linear_static"),
    _g05_case("VNV026-CON-G05-003", "Frictionless plane contact load variant", "CON", "frictionless_contact", "frictionless_contact_plane.json", "linear_static", load_scale=0.75),
    _g05_case("VNV026-CON-G05-004", "Frictionless surface contact load variant", "CON", "frictionless_contact", "frictionless_contact_surface.json", "linear_static", load_scale=0.75),
    _g05_case("VNV026-ADV-G05-001", "Invalid inverted TET4 contract", "ADV", "adversarial", "invalid_inverted_tet4.json", "linear_static", expected_failure="INVALID_ELEMENT", maturity="QUALIFIED_BOUNDED"),
    _g05_case("VNV026-ADV-G05-002", "Repeated invalid geometry contract", "ADV", "adversarial", "invalid_inverted_tet4.json", "linear_static", expected_failure="INVALID_ELEMENT", maturity="QUALIFIED_BOUNDED"),
    _g05_case("VNV026-ADV-G05-003", "Invalid geometry deterministic repeat", "ADV", "adversarial", "invalid_inverted_tet4.json", "linear_static", expected_failure="INVALID_ELEMENT", maturity="QUALIFIED_BOUNDED"),
    _g05_case("VNV026-SCL-G05-001", "Spring mass scaling baseline", "SCL", "scaling", "spring_mass_oscillator.json", "linear_static", maturity="EXPERIMENTAL"),
    _g05_case("VNV026-SCL-G05-002", "TET4 scaling route baseline", "SCL", "scaling", "tet4_static.json", "linear_static", maturity="EXPERIMENTAL"),
)


def planned_cases() -> list[dict[str, Any]]:
    ready_cases = (*SMOKE_CASES, *G05_CASES)
    ready_counts = {prefix: sum(case["family"] == prefix for case in ready_cases) for prefix, *_ in CAMPAIGNS}
    cases = list(ready_cases)
    for prefix, title, capability, target, maturity in CAMPAIGNS:
        count = target - ready_counts[prefix]
        for index in range(1, count + 1):
            cases.append(
                {
                    "case_id": f"VNV026-{prefix}-PLN-{index:03d}",
                    "title": f"{title} planned variation {index:03d}",
                    "family": prefix,
                    "capability": capability,
                    "maturity_target": maturity,
                    "description": "A deterministic planned case generated from the 0.2.6 campaign matrix; execution is intentionally deferred until its gate batch.",
                    "geometry": {"factory": f"{capability}_factory", "variation_index": index},
                    "element_family": _element_for(prefix, index),
                    "element_order": _order_for(prefix, index),
                    "mesh_strategy": _mesh_for(prefix, index),
                    "mesh_levels": ["coarse", "medium", "fine"] if prefix not in {"ADV", "SCL"} else ["targeted"],
                    "material": {"sampling": "controlled_boundary_nominal_pairwise", "variation_index": index},
                    "kinematics": _kinematics_for(prefix),
                    "analysis_type": _analysis_for(prefix),
                    "load_definition": {"sampling": "documented_factory", "variation_index": index},
                    "boundary_conditions": {"sampling": "documented_factory"},
                    "solver_configuration": {"profile": _cost_for(prefix), "deterministic": True},
                    "oracle_types": _oracles_for(prefix),
                    "oracle_ids": [],
                    "metrics": _metrics_for(prefix),
                    "tolerance_ids": _tolerances_for(prefix),
                    "expected_behaviour": "Defined by the factory and acceptance policy before execution.",
                    "expected_failure": _expected_failure_for(prefix, index),
                    "random_seed": 260000 + index if prefix == "ADV" else None,
                    "cost_profile": _cost_for(prefix),
                    "ci_profiles": ["FULL"] + (["EXTERNAL"] if "external" in _oracles_for(prefix) else []),
                    "source_reference": "0.2.6 campaign matrix",
                    "tags": ["planned", prefix.lower(), capability],
                    "known_limitations": ["Not executed in the 0.2.6 foundation run."],
                    "execution_state": "PLANNED",
                    "input_model": None,
                    "factory_id": f"FACTORY-026-{prefix}",
                }
            )
    return sorted(cases, key=lambda item: item["case_id"])


def _element_for(prefix: str, index: int) -> str:
    families = ("TET4", "TET10", "HEX8", "HEX20")
    if prefix == "SHL":
        return ("MITC3", "MITC4", "BEAM2", "DISCRETE")[index % 4]
    return families[index % len(families)] if prefix in {"LIN", "J2", "GNL", "BUC", "CON", "CPL", "SCL"} else "mixed"


def _order_for(prefix: str, index: int) -> int | None:
    return 2 if _element_for(prefix, index) in {"TET10", "HEX20"} else 1


def _mesh_for(prefix: str, index: int) -> str:
    return "structured_refinement" if prefix in {"LIN", "J2", "GNL", "BUC", "CON"} else "targeted_reference"


def _kinematics_for(prefix: str) -> str:
    return "total_lagrangian" if prefix in {"GNL", "CPL"} else "small_strain"


def _analysis_for(prefix: str) -> str:
    return {
        "LIN": "linear_static", "SHL": "mixed", "MOD": "modal", "DYN": "transient_dynamic", "HAR": "harmonic",
        "J2": "nonlinear_static", "GNL": "geometric_nonlinear_static", "BUC": "linear_buckling",
        "CON": "linear_static_contact", "CPL": "coupled_nonlinear", "ADV": "failure_contract", "SCL": "scaling",
    }[prefix]


def _oracles_for(prefix: str) -> list[str]:
    if prefix in {"J2", "GNL", "BUC", "CON"}:
        return ["analytical", "external"]
    if prefix == "ADV":
        return ["invariant"]
    return ["analytical", "internal_regression"]


def _metrics_for(prefix: str) -> list[str]:
    base = ["status", "displacement", "reaction", "residual"]
    if prefix == "MOD":
        return ["eigenfrequency", "modal_residual", "mac", "orthogonality"]
    if prefix in {"DYN", "HAR"}:
        return ["history", "energy", "phase", "residual"]
    if prefix == "J2":
        return base + ["von_mises", "equivalent_plastic_strain", "dissipation"]
    if prefix in {"BUC", "GNL"}:
        return base + ["tangent", "determinant"]
    if prefix == "SCL":
        return ["n_dof", "nnz", "wall_time", "peak_memory"]
    return base


def _tolerances_for(prefix: str) -> list[str]:
    if prefix == "ADV":
        return ["TOL-026-EXACT-001"]
    if prefix == "SCL":
        return ["TOL-026-PERF-001"]
    if prefix in {"MOD", "DYN", "HAR"}:
        return ["TOL-026-DYNAMIC-001"]
    if prefix in {"J2", "GNL", "CPL"}:
        return ["TOL-026-NONLINEAR-001"]
    return ["TOL-026-ANALYTICAL-001"]


def _expected_failure_for(prefix: str, index: int) -> str | None:
    return "EXPECTED_FAILURE_CONTRACT" if prefix == "ADV" and index % 2 else None


def _cost_for(prefix: str) -> str:
    if prefix == "SCL":
        return "EXTENDED"
    if prefix in {"CPL", "GNL", "CON"}:
        return "STANDARD"
    return "SMOKE"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_data() -> None:
    cases = planned_cases()
    if len(cases) != 180:
        raise RuntimeError(f"0.2.6 target catalog must contain 180 cases, found {len(cases)}.")
    _write_json(QUALIFICATION / "scope.json", {
        "schema_version": 1,
        "release": "0.2.6a0",
        "baseline_release": "v0.2.5a0",
        "baseline_release_head": BASE_HEAD,
        "historical_qualified_numerical_source": QUALIFIED_SOURCE,
        "purpose": "maturity_vnv_architecture_foundation",
        "non_goals": ["new_fem_elements", "new_constitutive_models", "friction_implementation", "new_physics", "release_publication"],
        "maturity_vocabulary": ["RESEARCH", "EXPERIMENTAL", "QUALIFIED_BOUNDED", "STABLE_BOUNDED", "DEFERRED", "NOT_IN_SCOPE", "BLOCKED", "FAILED"],
    })
    _write_json(QUALIFICATION / "campaign_registry.json", {
        "schema_version": 1,
        "target_case_count": 180,
        "foundation_smoke_case_count": len(SMOKE_CASES),
        "g05_executable_case_count": len(G05_CASES),
        "campaigns": [{"prefix": prefix, "title": title, "capability": capability, "target_case_count": target, "maturity_target": maturity} for prefix, title, capability, target, maturity in CAMPAIGNS],
        "profiles": {"SMOKE": "10 maintained foundation executable cases", "G05": "50 bounded robustness executable cases", "STANDARD": "future routine selection", "FULL": "all ready cases after gate implementation", "EXTERNAL": "explicit external adapters only", "ADVERSARIAL": "expected failure and metamorphic cases", "SCALING": "machine-characterized profiles", "RELEASE": "controlled aggregation"},
    })
    ready_case_count = len(SMOKE_CASES) + len(G05_CASES)
    _write_json(QUALIFICATION / "case_registry.json", {"schema_version": 1, "metadata": {"release": "0.2.6a0", "target_case_count": 180, "ready_case_count": ready_case_count, "foundation_smoke_case_count": len(SMOKE_CASES), "g05_executable_case_count": len(G05_CASES), "planned_case_count": 180 - ready_case_count, "generator": "scripts/generate_vnv_026_foundation.py"}, "cases": cases})
    _write_json(QUALIFICATION / "gates.json", {"schema_version": 1, "gates": [{"id": f"026-G{index:02d}", "title": title, "status": status, "evidence_ids": evidence} for index, title, status, evidence in _gates()]})
    _write_json(QUALIFICATION / "capability_targets.json", {"schema_version": 1, "capabilities": [{"id": capability, "current_maturity": maturity, "target": target, "claim_boundary": limit} for capability, maturity, target, limit in _capabilities()]})
    _write_json(QUALIFICATION / "requirements.json", {"schema_version": 1, "requirements": _requirements()})
    _write_json(QUALIFICATION / "work_packages.json", {"schema_version": 1, "completed_work_packages": _completed_work_packages(), "work_packages": _work_packages()})
    _write_json(QUALIFICATION / "risk_register.json", {"schema_version": 1, "risks": _risks()})
    _write_json(QUALIFICATION / "debt_register.json", {"schema_version": 1, "debts": _debts()})
    _write_json(QUALIFICATION / "oracle_registry.json", {"schema_version": 1, "oracles": [{"id": "ANALYTICAL", "kind": "analytical", "availability": "local", "claim": "verification_reference"}, {"id": "CODE_ASTER", "kind": "external", "availability": "optional_local_or_container", "claim": "external_numerical_correlation"}, {"id": "CALCULIX", "kind": "external", "availability": "should_when_comparable", "claim": "external_numerical_correlation"}], "rule": "External unavailability is SKIPPED_EXTERNAL_UNAVAILABLE, never PASS."})
    _write_json(QUALIFICATION / "tolerance_policy.json", {"schema_version": 1, "policy": "Tolerance changes require an anomaly record; coverage is distinct from V&V.", "tolerances": _tolerances()})
    _write_json(QUALIFICATION / "anomaly_registry.json", {"schema_version": 1, "next_id": "ANOM-026-0001", "categories": ["QF_DEFECT", "TEST_DEFECT", "REFERENCE_DEFECT", "FORMULATION_MISMATCH", "NUMERICAL_SENSITIVITY", "UNSUPPORTED_DOMAIN", "INFRASTRUCTURE_DEFECT", "UNRESOLVED_ANOMALY"], "anomalies": []})
    _write_json(QUALIFICATION / "performance_profiles.json", {"schema_version": 1, "profiles": [{"id": "SMOKE", "dof_range": "1e3-1e4", "ci": True}, {"id": "STANDARD", "dof_range": "1e4-1e5", "ci": False}, {"id": "EXTENDED", "dof_range": "1e5-5e5", "ci": False}, {"id": "LARGE", "dof_range": "5e5-1e6+", "ci": False, "constraint": "hardware_and_backend_permit"}], "metrics": ["model_generation", "assembly", "constraint_application", "factorization", "solve", "post", "wall_time", "peak_rss", "nnz", "iterations"]})
    _write_json(QUALIFICATION / "artifact_policy.json", {"schema_version": 1, "commit_policy": [{"max_bytes": 1000000, "rule": "normally_acceptable_if_useful"}, {"max_bytes": 10000000, "rule": "requires_justification"}, {"max_bytes": 50000000, "rule": "must_not_enter_normal_source_history"}], "commit": ["definitions", "small_references", "summary_json", "compact_csv", "digests", "manifests"], "exclude": ["raw_external_workdirs", "temporary_meshes", "large_histories", "ephemeral_logs", "duplicate_pdfs"]})
    _write_json(QUALIFICATION / "owner_decisions.json", {"schema_version": 1, "release": "0.2.6a0", "decisions": [], "rule": "Automation can request Owner review but cannot promote maturity autonomously."})
    _write_json(QUALIFICATION / "migration_map.json", {"schema_version": 1, "execution": "PLAN_ONLY", "current_to_target": [{"current": "src/solveur/verification/calculix_*.py", "target": "src/solveur/verification/oracles/calculix/", "risk": "medium", "precondition": "baseline_fingerprint_and_smoke_pass"}, {"current": "src/solveur/verification/code_aster_*.py", "target": "src/solveur/verification/oracles/code_aster/", "risk": "medium", "precondition": "baseline_fingerprint_and_smoke_pass"}, {"current": "src/solveur/verification/*_campaign.py", "target": "src/solveur/verification/campaigns/<domain>/", "risk": "medium", "precondition": "one_domain_per_mechanical_commit"}, {"current": "scripts/run_*_vnv.py", "target": "scripts/run_vnv_026.py plus explicit adapters", "risk": "low", "precondition": "runner_registry_available"}]})


def _gates() -> list[tuple[int, str, str, list[str]]]:
    titles = ["Baseline / provenance", "Architecture audit", "V&V infrastructure", "Corpus design", "Linear / element robustness", "Modal / dynamic / harmonic", "J2 maturity extension", "Geometric nonlinear and arc-length review", "Buckling maturity extension", "Contact maturity extension", "Existing coupled nonlinear review", "Adversarial / failure / metamorphic", "Performance / scalability", "External correlation aggregation", "Full regression / architecture freeze", "Owner release review"]
    foundation = {
        0: ("PASS", ["baseline_snapshot.json", "0_2_5_release_readiness.md"], "Clean baseline snapshot captured on the committed foundation; the 0.2.5 qualified source remains immutable."),
        1: ("PASS", ["architecture_audit.json", "0_2_6_architecture_audit.md"], "Static audit captured before any high-risk verification-package migration."),
        2: ("PASS", ["test_vnv_026_framework.py", "VNV026-SMOKE"], "Validated registry, safe runner, manifest and expected-failure contract."),
        3: ("PASS", ["case_registry.json", "0_2_6_campaign_matrix.md"], "Exactly 180 deterministic definitions exist; only 10 are READY and no planned case is evidence."),
    }
    return [
        (index, title, foundation[index][0], foundation[index][1]) if index in foundation else (index, title, "NOT_STARTED", [])
        for index, title in enumerate(titles)
    ]


def _capabilities() -> list[tuple[str, str, str, str]]:
    return [
        ("small_strain_j2", "QUALIFIED_BOUNDED", "maturity_extension", "No finite-strain J2 claim."),
        ("total_lagrangian_elasticity", "QUALIFIED_BOUNDED", "bounded_refinement", "TET4/HEX8 bounded domain."),
        ("linear_buckling", "QUALIFIED_BOUNDED", "maturity_extension", "No nonlinear collapse claim."),
        ("frictionless_contact", "QUALIFIED_BOUNDED", "maturity_extension", "No general mortar or arbitrary large sliding claim."),
        ("arc_length", "EXPERIMENTAL", "review_only", "Promotion requires independent reproducible reference."),
        ("coupled_nonlinear", "EXPERIMENTAL", "review_only", "Finite-kinematic J2 remains deferred."),
        ("friction", "NOT_IN_SCOPE", "not_in_scope", "No implementation in 0.2.6 foundation."),
    ]


def _debts() -> list[dict[str, str]]:
    return [
        {"id": "DEBT-026-001", "area": "arc_length", "status": "OPEN", "reason": "Independent compatible published/reproducible reference remains incomplete after 0.2.5."},
        {"id": "DEBT-026-002", "area": "coupled_nonlinear", "status": "DEFERRED", "reason": "Finite-kinematic J2 and equivalent external correlations are not qualified."},
        {"id": "DEBT-026-003", "area": "verification_architecture", "status": "OPEN", "reason": "Flat campaign/oracle layout duplicates runner and evidence logic."},
        {"id": "DEBT-026-004", "area": "repository_artifacts", "status": "OPEN", "reason": "Historical multi-million displacement blobs exceed the proposed normal Git size policy; preserve history and prevent recurrence."},
    ]


def _requirements() -> list[dict[str, Any]]:
    return [
        {"id": "REQ-026-001", "requirement": "Preserve the immutable 0.2.5 numerical source and claims.", "verification": "baseline snapshot plus provenance review", "gate": "026-G00", "priority": "MUST"},
        {"id": "REQ-026-002", "requirement": "Provide a versioned machine-readable registry for controlled V&V cases.", "verification": "registry schema and unit tests", "gate": "026-G02", "priority": "MUST"},
        {"id": "REQ-026-003", "requirement": "Separate planned definitions from executable evidence.", "verification": "execution-state and smoke-selection tests", "gate": "026-G03", "priority": "MUST"},
        {"id": "REQ-026-004", "requirement": "Produce digest-first evidence with source, environment and threshold provenance.", "verification": "runner manifest contract tests", "gate": "026-G02", "priority": "MUST"},
        {"id": "REQ-026-005", "requirement": "Keep external tools optional and record unavailable tools as skipped, never passed.", "verification": "oracle registry and future adapter tests", "gate": "026-G13", "priority": "MUST"},
        {"id": "REQ-026-006", "requirement": "Keep public claims bounded by recorded evidence and Owner decisions.", "verification": "gate and claim audit before release decision", "gate": "026-G15", "priority": "MUST"},
        {"id": "REQ-026-007", "requirement": "Characterize performance with repeatable measurements and hardware metadata.", "verification": "scaling profiles and benchmark manifests", "gate": "026-G12", "priority": "SHOULD"},
    ]


def _work_packages() -> list[dict[str, Any]]:
    return [
        {"id": "WP-026-00", "title": "Baseline and provenance", "depends_on": [], "gate": "026-G00", "stop_go": "STOP if historical source or baseline route is not reproducible."},
        {"id": "WP-026-01", "title": "Verification architecture inventory", "depends_on": ["WP-026-00"], "gate": "026-G01", "stop_go": "GO only after import and responsibility boundaries are mapped."},
        {"id": "WP-026-02", "title": "Registry and safe runner", "depends_on": ["WP-026-01"], "gate": "026-G02", "stop_go": "STOP if a planned case can execute or a path can escape controlled examples."},
        {"id": "WP-026-03", "title": "Corpus factory design", "depends_on": ["WP-026-02"], "gate": "026-G03", "stop_go": "GO only when every case has a capability, oracle and tolerance source."},
        {"id": "WP-026-04", "title": "Linear, element, modal and dynamic maturity", "depends_on": ["WP-026-03"], "gate": "026-G04 to 026-G05", "stop_go": "STOP on unexplained baseline drift."},
        {"id": "WP-026-05", "title": "J2, geometric, buckling and contact evidence", "depends_on": ["WP-026-04"], "gate": "026-G06 to 026-G10", "stop_go": "STOP before maturity promotion when external equivalence is unresolved."},
        {"id": "WP-026-06", "title": "Adversarial, performance and external aggregation", "depends_on": ["WP-026-05"], "gate": "026-G11 to 026-G13", "stop_go": "STOP on a fail-open contract or undocumented machine variance."},
        {"id": "WP-026-07", "title": "Regression, architecture freeze and Owner review", "depends_on": ["WP-026-06"], "gate": "026-G14 to 026-G15", "stop_go": "STOP if a claim lacks a manifest or Owner decision."},
    ]


def _completed_work_packages() -> list[dict[str, Any]]:
    return [{
        "id": "026-WP04-ARCH",
        "title": "Numerical core architecture refactor",
        "status": "PASS",
        "depends_on": ["WP-026-03"],
        "official_gate_collision": "026-G04",
        "evidence": ["g04_architecture_evidence.json", "0_2_6_g04_architecture_evidence.md"],
        "note": "Distinct work-package identifier. Official gate 026-G04 remains Linear / element robustness.",
    }]


def _risks() -> list[dict[str, str]]:
    return [
        {"id": "RISK-026-001", "risk": "Planned cases are mistaken for completed evidence.", "severity": "high", "mitigation": "READY/PLANNED state and runner exclusion", "gate": "026-G03"},
        {"id": "RISK-026-002", "risk": "A V&V refactor changes numerical behavior or public API.", "severity": "high", "mitigation": "baseline fingerprints and focused API smoke", "gate": "026-G00/026-G14"},
        {"id": "RISK-026-003", "risk": "External tool absence is represented as a pass.", "severity": "high", "mitigation": "explicit SKIPPED_EXTERNAL_UNAVAILABLE outcome", "gate": "026-G13"},
        {"id": "RISK-026-004", "risk": "Large artifacts obscure source history and inflate clones.", "severity": "medium", "mitigation": "artifact policy and digest-first summaries", "gate": "026-G01"},
        {"id": "RISK-026-005", "risk": "Performance comparisons use incompatible hardware or one noisy sample.", "severity": "medium", "mitigation": "hardware metadata, repeated medians and profile bands", "gate": "026-G12"},
        {"id": "RISK-026-006", "risk": "Research paths are promoted by test count alone.", "severity": "high", "mitigation": "claim matrix and Owner-only maturity decision", "gate": "026-G15"},
    ]


def _tolerances() -> list[dict[str, Any]]:
    return [
        {"id": "TOL-026-EXACT-001", "category": "exact_invariant", "metric": "boolean or identity", "value": 0.0, "reason": "Invariants and expected failures are exact contracts.", "applicability": "adversarial/metamorphic"},
        {"id": "TOL-026-FLOAT-001", "category": "floating_point", "metric": "relative numerical fingerprint comparison", "value": 1e-12, "reason": "Baseline guard for deterministic small examples.", "applicability": "foundation_smoke"},
        {"id": "TOL-026-ANALYTICAL-001", "category": "analytical_discretization", "metric": "case-defined normalized error", "value": None, "reason": "Case-specific and justified before execution.", "applicability": "linear/modal"},
        {"id": "TOL-026-NONLINEAR-001", "category": "iterative_nonlinear", "metric": "residual, path and tangent", "value": None, "reason": "Reuse existing qualified limits until a documented anomaly changes them.", "applicability": "J2/geometric/coupled"},
        {"id": "TOL-026-DYNAMIC-001", "category": "dynamic", "metric": "amplitude, phase, energy", "value": None, "reason": "Defined per oracle and time/frequency refinement study.", "applicability": "modal/dynamic/harmonic"},
        {"id": "TOL-026-PERF-001", "category": "performance", "metric": "median repeated measurement", "value": None, "reason": "No noisy two-percent CI gate; characterize machine metadata.", "applicability": "scaling"},
    ]


def write_docs() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    campaign_rows = "\n".join(f"| `{prefix}` | {title} | {target} | {maturity} |" for prefix, title, _, target, maturity in CAMPAIGNS)
    gate_rows = "\n".join(f"| `026-G{index:02d}` | {title} | {status} |" for index, title, status, _ in _gates())
    docs = {
        "README.md": "# QF Solver 0.2.6a0 V&V Foundation\n\nThis directory is the generated, reader-facing view of authoritative data in `qualification/0_2_6/`. It defines infrastructure and planned work; it does not certify a new release.\n\nRun `python scripts/generate_vnv_026_foundation.py` after an intentional policy change.\n",
        "0_2_6_master_plan.md": """# 0.2.6a0 Master Plan

## Objective

0.2.6a0 is a maturity, reproducibility and architecture cycle. It makes the
qualification system executable as controlled work packages before any claim is
expanded. This foundation run adds no FEM physics and does not certify a new
release.

## Ordered Execution

1. G00 baseline and provenance.
2. G01 architecture audit.
3. G02 registry, runner and manifest contracts.
4. G03 corpus design.
5. G04-G13 controlled capability batches, each followed by evidence and gate
   review.
6. G14 full regression and architecture freeze.
7. G15 Owner review.

Every batch follows: audit, implement only the approved narrow change, verify,
benchmark where applicable, correlate, gate, then move to the next package.
An OPEN gate is recorded as OPEN; it is never converted to PASS by a new label.
""",
        "0_2_6_scope.md": """# Scope

## Allowed Foundation Work

- V&V tooling, registries, safe runners, provenance manifests and artifact
  policy.
- Documentation, architecture inventory, planned factories and focused
  non-numerical instrumentation.
- Baseline and smoke checks that guard existing numerical behavior.

## Excluded Work

- New FEM element families, constitutive models, friction development or new
  physical domains.
- New public numerical claims, tolerance relaxation, automatic release,
  publication or maturity promotion.

Qualified 0.2.5 claims remain historical. Arc-length and coupled nonlinear
paths remain experimental unless later gates establish stronger evidence.
""",
        "0_2_6_capability_inventory.md": "# Capability Inventory\n\n| Capability | 0.2.5 maturity | 0.2.6 intent | Claim boundary |\n| --- | --- | --- | --- |\n" + "\n".join(f"| `{cid}` | {current} | {target} | {boundary} |" for cid, current, target, boundary in _capabilities()) + "\n",
        "0_2_6_debt_register.md": "# Debt Register\n\n| ID | Area | Status | Reason |\n| --- | --- | --- | --- |\n" + "\n".join(f"| `{row['id']}` | {row['area']} | {row['status']} | {row['reason']} |" for row in _debts()) + "\n",
        "0_2_6_architecture_refactor_plan.md": """# Architecture Refactor Plan

## G04 implementation result

The first completed architectural batch groups the existing core
implementations by responsibility without changing numerical bodies, public
API, file formats or solver options:

| Domain | Implementation package |
| --- | --- |
| Assembly | `solveur.core.assembly` |
| Linear solvers and backend policy | `solveur.core.solvers` |
| Modal, dynamic, harmonic and stability analyses | `solveur.core.analyses` |
| Nonlinear state, contracts and strategies | `solveur.core.nonlinear` |

Legacy flat imports such as `solveur.core.assembler` and
`solveur.core.nonlinear_iteration` remain compatibility facades. They resolve
to the new implementation modules so existing 0.2.x callers and tests retain
their import paths while new code has explicit ownership boundaries.

The verification package remains intentionally flat in this batch. Its future
oracle/campaign migration is separate work and is not required to reorganize
the numerical core.

Modules near the repository 700-line limit are inventory candidates, not
automatic refactor targets. This batch did not split numerical functions or
change algorithmic thresholds merely to satisfy a line count.

### Migration Guard

Before every migration: capture fingerprints, run focused tests and keep the
compatibility facade. After it: rerun the same checks, compare results and
record the evidence. Stop on numerical drift, changed output schema or import
breakage.

## G04 acceptance boundary

- New implementation modules must be importable directly.
- Legacy flat module paths must resolve to the same module objects.
- Public `qf_solver` imports, CLI routes and serialized outputs must remain
  unchanged.
- The foundation smoke and representative route fingerprints must match the
  baseline exactly within the existing comparison policy.
- No verification maturity status is promoted by this structural refactor.
""",
        "0_2_6_vnv_architecture.md": """# V&V Architecture

Authoritative definitions live in `qualification/0_2_6/case_registry.json`.
The registry validates identifiers and selection. `VnvRunner` executes only
READY cases whose JSON model is under `examples/`; it intentionally has no
arbitrary command field. PLANNED cases are visible but cannot run.

Each case result and manifest records source SHA, dirty state, UTC timestamp,
solver version, configuration, threshold policy, environment and digests.
Results stay runtime artifacts, while small definitions and manifests remain
versionable. External adapters are explicit, optional and must report an
unavailable tool as `SKIPPED_EXTERNAL_UNAVAILABLE`.
""",
        "0_2_6_campaign_matrix.md": "# Campaign Matrix\n\nThe catalog contains exactly 180 meaningful case definitions. Ten maintained models are READY as foundation smoke cases and 50 bounded G05 variants are READY for execution; the remaining 120 definitions are PLANNED and are not evidence.\n\n`READY` means the controlled runner can execute the case. It does not by itself mean `QUALIFIED`; qualification still requires the applicable oracle, acceptance criteria and gate decision.\n\n| Prefix | Campaign | Target | Maturity target |\n| --- | --- | ---: | --- |\n" + campaign_rows + "\n",
        "0_2_6_external_correlation_plan.md": """# External Correlation Plan

Analytical references come first for clean cases. Code_Aster is the primary
optional external numerical oracle; CalculiX is SHOULD only when the element,
kinematics, integration and output measures are comparable. Abaqus is COULD
when a licensed, reproducible environment exists.

For every external cell, preserve geometry, mesh, material, boundary
conditions, load history, solver deck, observable mapping and source digest.
Compare histories where the method is path dependent. Numerical correlation is
not physical validation. Missing external software produces
`SKIPPED_EXTERNAL_UNAVAILABLE`, never PASS.
""",
        "0_2_6_adversarial_plan.md": """# Adversarial Plan

Expected safe failures are distinct from numerical failures. Planned families
cover invalid connectivity, inverted elements, singular systems, NaN/Inf,
invalid material data, invalid time steps, solver failures and impossible
contact states. Every expected failure must fail closed with a structured
category and without state corruption.

Metamorphic checks cover numbering and element ordering invariance, rigid
translation where appropriate, load scaling, sign-invariant modes and
trial/commit/rollback reproducibility. Failures become anomaly records rather
than tolerance changes.
""",
        "0_2_6_performance_scaling_plan.md": """# Performance and Scaling Plan

Record model generation, assembly, constraints, factorization, solve,
post-processing, wall time, peak RSS, DOF, NNZ and iterations. Every profile
records Python, dependency, backend and hardware metadata.

Use repeated medians, warm-up policy and profile bands rather than noisy
per-PR absolute runtime gates. CI is limited to SMOKE. STANDARD, EXTENDED and
LARGE runs are controlled evidence and do not become release claims without
their own gate review.
""",
        "0_2_6_artifact_policy.md": "# Artifact Policy\n\nMachine-readable policy: `qualification/0_2_6/artifact_policy.json`. Commit small inputs, summaries, compact CSV, digests and manifests. Do not commit large raw histories, external working directories or duplicate generated documents. Historical large blobs remain preserved and are a cleanup planning item, not a rewritten record.\n",
        "0_2_6_gate_matrix.md": "# Gate Matrix\n\n| Gate | Purpose | Current status |\n| --- | --- | --- |\n" + gate_rows + "\n\nG00 is a refactor guard with an explicit dirty-worktree limitation, not a replacement for immutable 0.2.5 evidence. G01-G03 close only audit, infrastructure and corpus design. Capability-gate outcomes are not implied by this foundation.\n",
        "0_2_6_requirements_matrix.md": "# Requirements Matrix\n\n| ID | Priority | Requirement | Verification | Gate |\n| --- | --- | --- | --- | --- |\n" + "\n".join(f"| `{row['id']}` | {row['priority']} | {row['requirement']} | {row['verification']} | `{row['gate']}` |" for row in _requirements()) + "\n",
        "0_2_6_work_packages.md": "# Work Packages\n\n## Completed work packages\n\n| Work package | Status | Evidence | Registry note |\n| --- | --- | --- | --- |\n" + "\n".join(f"| `{row['id']}` {row['title']} | {row['status']} | {', '.join(row['evidence'])} | {row['note']} |" for row in _completed_work_packages()) + "\n\n## Planned foundation work packages\n\n| Work package | Dependencies | Gate | STOP / GO |\n| --- | --- | --- | --- |\n" + "\n".join(f"| `{row['id']}` {row['title']} | {', '.join(row['depends_on']) or 'none'} | {row['gate']} | {row['stop_go']} |" for row in _work_packages()) + "\n",
        "0_2_6_risk_register.md": "# Risk Register\n\n| ID | Risk | Severity | Mitigation | Gate |\n| --- | --- | --- | --- | --- |\n" + "\n".join(f"| `{row['id']}` | {row['risk']} | {row['severity']} | {row['mitigation']} | `{row['gate']}` |" for row in _risks()) + "\n",
        "0_2_6_owner_review_template.md": "# Owner Review Template\n\n- Candidate source SHA and worktree state:\n- Gate evidence manifest and artifact digests:\n- Capability claims proposed for change:\n- Known limitations, anomalies and external-equivalence statement:\n- Regression, coverage and performance context:\n- Decision: `APPROVE`, `APPROVE_WITH_LIMITATIONS`, `DEFER`, or `REJECT`:\n\nNo automated process may fill the decision on behalf of the Owner.\n",
        "0_2_6_release_readiness_template.md": "# Release Readiness Template\n\n- Version and candidate SHA:\n- G00–G15 status with evidence IDs:\n- Full regression and coverage:\n- V&V corpus totals, expected failures and anomalies:\n- External correlation aggregation:\n- Performance profile and hardware:\n- Public claim matrix:\n- Owner decision:\n\nThis template is intentionally not a release approval.\n",
    }
    for name, content in docs.items():
        (DOCS / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    write_data()
    write_docs()
    print(f"Generated {QUALIFICATION.relative_to(ROOT)} and {DOCS.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
