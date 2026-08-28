"""Controlled executable case definitions for the 0.2.6 G06 batch."""

from __future__ import annotations

from typing import Any


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
        "description": "A deterministic G06 case reusing a maintained public model.",
        "geometry": {"source": input_model},
        "element_family": "mixed_or_declared_by_model",
        "element_order": None,
        "mesh_strategy": "maintained_example",
        "mesh_levels": ["g06"],
        "material": {"source": "model"},
        "kinematics": "declared_by_model",
        "analysis_type": analysis_type,
        "load_definition": {"source": "model"},
        "boundary_conditions": {"source": "model"},
        "solver_configuration": {"source": "model"},
        "oracle_types": ["internal_regression"],
        "oracle_ids": [],
        "metrics": ["solver_status", "displacement", "residual", "numerical_fingerprint"],
        "tolerance_ids": ["TOL-026-FLOAT-001"],
        "expected_behaviour": "Complete deterministically with finite reported metrics.",
        "expected_failure": expected_failure,
        "random_seed": None,
        "cost_profile": "SMOKE",
        "ci_profiles": ["G06", "FULL", "RELEASE"],
        "source_reference": "0.2.6 G06 V&V campaign definition",
        "tags": ["g06", prefix.lower()],
        "known_limitations": [],
        "execution_state": "READY",
        "input_model": input_model,
        "factory_id": None,
    }


def _g06_case(
    case_id: str,
    title: str,
    prefix: str,
    capability: str,
    model: str,
    analysis_type: str,
    *,
    element_family: str,
    oracle_types: tuple[str, ...] = ("analytical", "internal_regression"),
    oracle_ids: tuple[str, ...] = ("ANALYTICAL",),
    mesh_strategy: str = "controlled_variant",
    mesh_levels: tuple[str, ...] = ("controlled",),
    load_scale: float = 1.0,
    analysis: dict[str, Any] | None = None,
    material_updates: dict[str, dict[str, Any]] | None = None,
    expected_failure: str | None = None,
    maturity: str = "QUALIFIED_BOUNDED",
    oracle_configuration: dict[str, Any] | None = None,
    extra_tags: tuple[str, ...] = (),
) -> dict[str, Any]:
    case = _ready(case_id, title, prefix, capability, f"examples/{model}", analysis_type, expected_failure=expected_failure, maturity=maturity)
    case.update({
        "description": "A G06 quantitative V&V case with an explicit oracle, metric set and deterministic configuration.",
        "element_family": element_family,
        "element_order": 2 if element_family in {"TET10", "HEX20"} else 1,
        "mesh_strategy": mesh_strategy,
        "mesh_levels": list(mesh_levels),
        "oracle_types": list(oracle_types),
        "oracle_ids": list(oracle_ids),
        "metrics": ["solver_status", "displacement", "reaction", "residual", "reference_error", "energy", "numerical_fingerprint"],
        "ci_profiles": ["G06", "FULL", "RELEASE"],
        "tags": ["g06", prefix.lower(), capability, element_family.lower(), *extra_tags],
        "source_reference": "0.2.6 G06 V&V campaign definition",
        "known_limitations": ["Executable quantitative evidence; promotion requires the applicable gate and independent review."],
        "model_overrides": {
            **({"load_scale": load_scale} if load_scale != 1.0 else {}),
            **({"analysis": analysis} if analysis else {}),
            **({"material_updates": material_updates} if material_updates else {}),
        },
        "oracle_configuration": dict(oracle_configuration or {}),
    })
    return case


_ANALYTICAL_MODELS = (
    ("TET4", "tet4_g06_analytic.json"),
    ("TET10", "tet10_g06_analytic.json"),
    ("HEX8", "hex8_g06_analytic.json"),
    ("HEX20", "hex20_g06_analytic.json"),
)
G06_ANALYTICAL_CASES = tuple(
    _g06_case(
        f"VNV026-LIN-G06-A{i:03d}",
        f"Analytical equilibrium {_ANALYTICAL_MODELS[(i - 1) % 4][0]} variant {i:02d}",
        "LIN", "linear_solids", _ANALYTICAL_MODELS[(i - 1) % 4][1], "linear_static",
        element_family=_ANALYTICAL_MODELS[(i - 1) % 4][0], load_scale=0.5 + 0.1 * ((i - 1) % 6),
        oracle_configuration={
            "type": "constrained_free_dof",
            "element_family": _ANALYTICAL_MODELS[(i - 1) % 4][0],
            "free_node": 1,
            "free_dof": "UX",
            "relative_tolerance": 1.0e-10,
        },
        extra_tags=("analytical",),
    ) for i in range(1, 21)
)

G06_MESH_CASES = tuple(
    _g06_case(
        f"VNV026-LIN-G06-M{i:03d}", f"HEX8 structured mesh level {nx} repeat {repeat}", "LIN", "linear_solids",
        f"vnv_026_g06/hex8_mesh_{nx:02d}.json", "linear_static", element_family="HEX8",
        mesh_strategy="structured_hex8_refinement", mesh_levels=(f"nx={nx}",), load_scale=1.0 + 0.05 * repeat,
    ) for i, (nx, repeat) in enumerate(((nx, repeat) for repeat in range(1, 5) for nx in (1, 2, 4, 8)), start=1)
)

_HEX_COMMON_ANALYSES = (
    ("linear_static", None, "LIN"),
    ("modal", {"type": "modal", "method": "eigh", "modes": 2}, "MOD"),
    ("transient_dynamic", {"type": "transient_dynamic", "method": "newmark", "time_step": 0.01, "steps": 4, "newmark_beta": 0.25, "newmark_gamma": 0.5}, "DYN"),
    ("harmonic", {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": [1.0]}, "HAR"),
    ("nonlinear_static", {"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0]}, "J2"),
    ("linear_static", None, "LIN"),
    ("modal", {"type": "modal", "method": "eigh", "modes": 3}, "MOD"),
    ("linear_static", None, "LIN"),
    ("transient_dynamic", {"type": "transient_dynamic", "method": "newmark", "time_step": 0.005, "steps": 2, "newmark_beta": 0.25, "newmark_gamma": 0.5}, "DYN"),
    ("harmonic", {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": [2.0]}, "HAR"),
)


def _hex_cases(family: str, static_model: str, j2_model: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        _g06_case(
            f"VNV026-HEX-G06-{family}-{index:03d}", f"{family} common analysis {index:02d}", prefix,
            "small_strain_j2" if prefix == "J2" else family.lower(), j2_model if prefix == "J2" else static_model,
            kind, element_family=family, analysis=updates, maturity="QUALIFIED_BOUNDED",
        ) for index, (kind, updates, prefix) in enumerate(_HEX_COMMON_ANALYSES, start=1)
    )


G06_HEX_CASES = (*_hex_cases("HEX8", "hex8_g06_static.json", "hex8_g06_j2.json"), *_hex_cases("HEX20", "hex20_g06_static.json", "hex20_g06_j2.json"))

_ROBUSTNESS_ROWS = (
    ("LIN", "linear_solids", "tet4_compression.json", "linear_static", "TET4", 0.75, None, "QUALIFIED_BOUNDED"),
    ("LIN", "linear_solids", "tet4_pressure.json", "linear_static", "TET4", 1.25, None, "QUALIFIED_BOUNDED"),
    ("LIN", "linear_solids", "tet10_orthotropic_static.json", "linear_static", "TET10", 0.8, None, "QUALIFIED_BOUNDED"),
    ("SHL", "shell_beam_discrete", "beam2_cantilever.json", "linear_static", "BEAM2", 1.2, None, "QUALIFIED_BOUNDED"),
    ("SHL", "shell_beam_discrete", "mitc3_shell_static.json", "linear_static", "MITC3", 0.9, None, "QUALIFIED_BOUNDED"),
    ("SHL", "shell_beam_discrete", "mitc4_laminate_static.json", "linear_static", "MITC4", 1.1, None, "QUALIFIED_BOUNDED"),
    ("MOD", "modal", "tet4_modal_unit.json", "modal", "TET4", 1.0, {"steel": {"density": 7900.0}}, "QUALIFIED_BOUNDED"),
    ("MOD", "modal", "tet4_orthotropic_modal.json", "modal", "TET4", 1.0, None, "QUALIFIED_BOUNDED"),
    ("DYN", "transient_dynamics", "tet4_dynamic_free_vibration.json", "transient_dynamic", "TET4", 1.0, {"steel": {"density": 12.0}}, "QUALIFIED_BOUNDED"),
    ("DYN", "transient_dynamics", "mitc3_newmark_cantilever.json", "transient_dynamic", "MITC3", 1.0, None, "QUALIFIED_BOUNDED"),
    ("HAR", "harmonic", "tet4_harmonic_response.json", "harmonic", "TET4", 1.0, {"steel": {"E": 1100.0}}, "QUALIFIED_BOUNDED"),
    ("HAR", "harmonic", "mitc4_harmonic_cantilever.json", "harmonic", "MITC4", 1.0, None, "QUALIFIED_BOUNDED"),
    ("J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", "TET4", 0.6, None, "QUALIFIED_BOUNDED"),
    ("J2", "small_strain_j2", "tet4_elastoplastic_static.json", "nonlinear_static", "TET4", 1.0, {"plastic_steel": {"yield_stress": 6.0}}, "QUALIFIED_BOUNDED"),
    ("J2", "small_strain_j2", "tet4_nonlinear_static.json", "nonlinear_static", "TET4", 1.0, None, "QUALIFIED_BOUNDED"),
    ("GNL", "geometric_nonlinear", "tet4_geometric_nonlinear_static.json", "geometric_nonlinear_static", "TET4", 0.75, None, "EXPERIMENTAL"),
    ("BUC", "linear_buckling", "tet4_linear_buckling.json", "linear_buckling", "TET4", 1.0, None, "QUALIFIED_BOUNDED"),
    ("CON", "frictionless_contact", "frictionless_contact_plane.json", "linear_static", "TET4", 0.8, None, "QUALIFIED_BOUNDED"),
    ("CON", "frictionless_contact", "frictionless_contact_surface.json", "linear_static", "TET4", 1.0, None, "QUALIFIED_BOUNDED"),
    ("LIN", "hex8", "hex8_g06_static.json", "linear_static", "HEX8", 1.0, {"solid": {"nu": 0.49}}, "QUALIFIED_BOUNDED"),
    ("LIN", "hex20", "hex20_g06_static.json", "linear_static", "HEX20", 1.0, {"solid": {"nu": 0.49}}, "QUALIFIED_BOUNDED"),
    ("J2", "hex8", "hex8_g06_j2.json", "nonlinear_static", "HEX8", 1.0, None, "QUALIFIED_BOUNDED"),
    ("J2", "hex20", "hex20_g06_j2.json", "nonlinear_static", "HEX20", 1.0, None, "QUALIFIED_BOUNDED"),
    ("ADV", "adversarial", "invalid_inverted_tet4.json", "linear_static", "TET4", 1.0, None, "QUALIFIED_BOUNDED"),
)
G06_ROBUSTNESS_CASES = tuple(
    _g06_case(
        f"VNV026-RBT-G06-{index:03d}", f"Robustness route {index:02d}", prefix, capability, model, analysis_type,
        element_family=element, load_scale=scale, material_updates=updates,
        expected_failure="INVALID_ELEMENT" if prefix == "ADV" else None, maturity=maturity,
    ) for index, (prefix, capability, model, analysis_type, element, scale, updates, maturity) in enumerate(_ROBUSTNESS_ROWS, start=1)
)

G06_CASES = (*G06_ANALYTICAL_CASES, *G06_MESH_CASES, *G06_HEX_CASES, *G06_ROBUSTNESS_CASES)
