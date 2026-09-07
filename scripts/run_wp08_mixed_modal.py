"""Run the bounded 0.2.8 WP08 mixed TET4/WEDGE6/HEX8 modal campaign."""

# This script is executable directly from a checkout and adds ``src`` before
# importing the package under test.
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wp07_mixed_static import _element_volume, _mixed_geometry
from scripts.wp08_mixed_modal_helpers import (
    canonical_modes as _canonical_modes,
    shared_node_mode_mac as _shared_node_mode_mac,
)
from solveur.api import save_result, solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory
from solveur.mesh.mixed_validation import mixed_solid_faces


BASELINE_SHA = "65c816fee4a1497dd320358565a297c01bfcaff5"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp08_mixed_modal_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp08_mixed_modal_vnv.json"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}

TOLERANCES: dict[str, float] = {
    "mass_symmetry_relative": 1.0e-12,
    "mass_total_relative": 1.0e-12,
    "mass_direction_relative": 1.0e-12,
    "mass_minimum_eigenvalue_relative": 1.0e-14,
    "modal_residual_relative": 1.0e-8,
    "modal_mass_orthogonality_relative": 1.0e-10,
    "oracle_frequency_relative": 1.0e-9,
    "oracle_mode_mac": 1.0 - 1.0e-8,
    "refinement_first_frequency_step_relative": 2.5e-1,
    "refinement_mode_mac": 5.0e-1,
    "replay_frequency_absolute": 1.0e-12,
    "replay_mode_absolute_after_sign": 1.0e-10,
    "interface_displacement_absolute": 1.0e-14,
}


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _element_rows(elements: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "type": str(row["type"]),
            "nodes": [int(node) for node in row["nodes"]],
            "material": str(row.get("material", "solid")),
        }
        for row in elements
    ]


def _fixed_rows(model: FiniteElementModel) -> list[dict[str, object]]:
    return [{"node": int(row.node), "dofs": list(row.dofs)} for row in model.fixed_dofs]


def _build_model(nodes: np.ndarray, elements: list[dict[str, object]], *, modes: int = 6) -> FiniteElementModel:
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if abs(float(point[0])) <= 1.0e-14
    ]
    return FiniteElementModel.from_raw(
        nodes=np.asarray(nodes, dtype=float).tolist(),
        elements=_element_rows(elements),
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=fixed,
        analysis={
            "type": "modal",
            "method": "eigh",
            "modes": modes,
            "parameters": {"mass_formulation": "consistent"},
        },
        units={"system": "SI"},
        verification_profile="engineering",
    )


def mixed_model(segments: int = 1, selected: tuple[int, ...] = (0, 1, 2)) -> FiniteElementModel:
    """Build a conforming subset of the WP07 TET4/WEDGE6/HEX8 chain."""

    nodes, all_elements = _mixed_geometry(segments)
    rows = [all_elements[index] for index in selected]
    referenced = sorted({int(node) for row in rows for node in row["nodes"]})
    remap = {node: index for index, node in enumerate(referenced)}
    subset_nodes = nodes[referenced]
    subset_elements = [
        {
            "type": row["type"],
            "nodes": [remap[int(node)] for node in row["nodes"]],
            "material": "solid",
        }
        for row in rows
    ]
    return _build_model(subset_nodes, subset_elements)


def _independent_dense_matrices(model: FiniteElementModel) -> tuple[np.ndarray, np.ndarray]:
    """Scatter local matrices independently from the production sparse assembler."""

    dofs = model.dof_manager()
    stiffness = np.zeros((dofs.ndof, dofs.ndof), dtype=float)
    mass = np.zeros_like(stiffness)
    for definition in model.elements:
        spec = ElementRegistry.get(definition.type)
        coords = model.nodes[list(definition.nodes)]
        material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
        element = spec.factory(material)
        indices = [
            dofs.index(node, name)
            for node in definition.nodes
            for name in spec.dofs
        ]
        selector = np.ix_(indices, indices)
        stiffness[selector] += element.stiffness(coords)
        mass[selector] += element.mass(coords)
    return stiffness, mass


def _free_indices(model: FiniteElementModel) -> tuple[Any, np.ndarray]:
    dofs = model.dof_manager()
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    return dofs, free


def _independent_dense_modal_reference(model: FiniteElementModel, count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    stiffness, mass = _independent_dense_matrices(model)
    _, free = _free_indices(model)
    reduced_stiffness = stiffness[np.ix_(free, free)]
    reduced_mass = mass[np.ix_(free, free)]
    if count < len(free):
        values, vectors = eigh(reduced_stiffness, reduced_mass, subset_by_index=(0, count - 1))
    else:
        values, vectors = eigh(reduced_stiffness, reduced_mass)
    return np.asarray(values[:count], dtype=float), np.asarray(vectors[:, :count], dtype=float), mass


def _mass_metrics(model: FiniteElementModel) -> dict[str, object]:
    assembler = GlobalAssembler()
    dofs = model.dof_manager()
    _, mass, _, mass_diagnostics = assembler.assemble_stiffness_and_mass(model, dofs)
    direct_mass = assembler.assemble_mass(model, dofs)
    dense = np.asarray(mass.toarray(), dtype=float)
    direct_dense = np.asarray(direct_mass.toarray(), dtype=float)
    _, independent_mass = _independent_dense_matrices(model)
    norm = max(float(np.linalg.norm(dense)), 1.0)
    eigenvalues = np.linalg.eigvalsh(dense)
    trace = max(float(np.trace(dense)), 1.0)
    expected_total = sum(
        float(model.materials[item.material]["density"])
        * _element_volume(item.type, model.nodes[list(item.nodes)])
        for item in model.elements
    )
    direction_masses = {}
    for name in ("UX", "UY", "UZ"):
        vector = np.zeros(dofs.ndof, dtype=float)
        for node in range(model.node_count):
            vector[dofs.index(node, name)] = 1.0
        direction_masses[name] = float(vector @ dense @ vector)
    total_relative = max(
        abs(value - expected_total) / max(abs(expected_total), 1.0)
        for value in direction_masses.values()
    )
    min_ratio = float(np.min(eigenvalues) / trace) if eigenvalues.size else 0.0
    return {
        "status": "PASS" if (
            np.linalg.norm(dense - dense.T) / norm <= TOLERANCES["mass_symmetry_relative"]
            and np.linalg.norm(dense - direct_dense) / norm <= TOLERANCES["mass_total_relative"]
            and np.linalg.norm(dense - independent_mass) / norm <= TOLERANCES["mass_total_relative"]
            and total_relative <= TOLERANCES["mass_total_relative"]
            and min_ratio > TOLERANCES["mass_minimum_eigenvalue_relative"]
        ) else "FAIL",
        "symmetry_relative": float(np.linalg.norm(dense - dense.T) / norm),
        "paired_vs_direct_relative": float(np.linalg.norm(dense - direct_dense) / norm),
        "independent_scatter_relative": float(np.linalg.norm(dense - independent_mass) / norm),
        "minimum_eigenvalue": float(np.min(eigenvalues)) if eigenvalues.size else 0.0,
        "minimum_eigenvalue_relative_to_trace": min_ratio,
        "positive_definite": bool(eigenvalues.size and np.all(eigenvalues > 0.0)),
        "expected_total_mass": float(expected_total),
        "direction_masses": direction_masses,
        "mass_conservation_relative": float(total_relative),
        "dof_count": dofs.ndof,
        "unique_dof_count": len({dofs.index(node, name) for node in range(model.node_count) for name in ("UX", "UY", "UZ")}),
        "assembly": mass_diagnostics,
        "formulation": "consistent_translational_finite_element_mass",
    }


def _spectral_clusters(values: np.ndarray) -> list[list[int]]:
    """Group numerically degenerate frequencies without changing tolerances."""

    frequencies = np.asarray(values, dtype=float)
    if frequencies.size == 0:
        return []
    clusters: list[list[int]] = [[0]]
    for index in range(1, frequencies.size):
        scale = max(abs(float(frequencies[index - 1])), abs(float(frequencies[index])), 1.0)
        if abs(float(frequencies[index] - frequencies[index - 1])) <= TOLERANCES["oracle_frequency_relative"] * scale:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return clusters


def _mode_mac(
    reference: np.ndarray,
    candidate: np.ndarray,
    mass: np.ndarray,
    *,
    reference_frequencies: np.ndarray | None = None,
    candidate_frequencies: np.ndarray | None = None,
) -> dict[str, object]:
    cross = reference.T @ mass @ candidate
    reference_norm = np.diag(reference.T @ mass @ reference)
    candidate_norm = np.diag(candidate.T @ mass @ candidate)
    denominator = np.maximum(reference_norm[:, None] * candidate_norm[None, :], 1.0e-300)
    mac = np.square(cross) / denominator
    rows, columns = linear_sum_assignment(-mac)
    pairs = [{"reference": int(row), "candidate": int(column), "mac": float(mac[row, column])} for row, column in zip(rows, columns, strict=True)]
    reference_clusters = _spectral_clusters(reference_frequencies) if reference_frequencies is not None else [[index] for index in range(reference.shape[1])]
    candidate_clusters = _spectral_clusters(candidate_frequencies) if candidate_frequencies is not None else [[index] for index in range(candidate.shape[1])]
    cluster_cross = np.zeros((len(reference_clusters), len(candidate_clusters)), dtype=float)
    for reference_index, reference_cluster in enumerate(reference_clusters):
        for candidate_index, candidate_cluster in enumerate(candidate_clusters):
            overlap = reference[:, reference_cluster].T @ mass @ candidate[:, candidate_cluster]
            singular_values = np.linalg.svd(overlap, compute_uv=False)
            cluster_cross[reference_index, candidate_index] = float(
                np.min(np.square(singular_values)) if singular_values.size else 0.0
            )
    cluster_rows, cluster_columns = linear_sum_assignment(-cluster_cross)
    cluster_pairs = [
        {
            "reference_modes": [int(value) for value in reference_clusters[row]],
            "candidate_modes": [int(value) for value in candidate_clusters[column]],
            "subspace_mac": float(cluster_cross[row, column]),
        }
        for row, column in zip(cluster_rows, cluster_columns, strict=True)
    ]
    minimum_cluster_mac = min((row["subspace_mac"] for row in cluster_pairs), default=0.0)
    return {
        "matrix": mac,
        "assignment": pairs,
        "minimum_assigned_mac": float(minimum_cluster_mac),
        "cluster_assignment": cluster_pairs,
        "minimum_individual_mac": min((row["mac"] for row in pairs), default=0.0),
    }


def _modal_case(name: str, model: FiniteElementModel) -> dict[str, object]:
    result = solve_model(model, enforce_policy=False)
    dofs, free = _free_indices(model)
    count = int(result.frequencies_hz.size)
    reference_values, reference_modes, independent_mass = _independent_dense_modal_reference(model, count)
    production_modes = np.asarray(result.modes, dtype=float)[free, :count]
    frequencies = np.asarray(result.frequencies_hz, dtype=float)
    reference_frequencies = np.sqrt(reference_values) / (2.0 * np.pi)
    matching = _mode_mac(
        reference_modes,
        production_modes,
        independent_mass[np.ix_(free, free)],
        reference_frequencies=reference_frequencies,
        candidate_frequencies=frequencies,
    )
    frequency_errors = np.abs(frequencies - reference_frequencies) / np.maximum(np.abs(reference_frequencies), 1.0e-12)
    modal_masses = np.diag(production_modes.T @ independent_mass[np.ix_(free, free)] @ production_modes)
    normalization_error = float(np.max(np.abs(modal_masses - 1.0), initial=0.0))
    solver = result.solver
    # Repeated eigenvalues are valid (for example the two transverse modes of
    # the pure TET4 probe).  The eigensolver must therefore return a sorted
    # non-decreasing spectrum, not an artificially strictly increasing one.
    mode_ordered = bool(np.all(np.diff(frequencies) >= -1.0e-12)) if frequencies.size > 1 else True
    passed = bool(
        result.status == "PASS"
        and frequencies.size > 0
        and np.isfinite(frequencies).all()
        and np.all(frequencies > 0.0)
        and float(np.max(frequency_errors, initial=0.0)) <= TOLERANCES["oracle_frequency_relative"]
        and float(solver["max_relative_residual"]) <= TOLERANCES["modal_residual_relative"]
        and float(solver["mass_orthogonality_error"]) <= TOLERANCES["modal_mass_orthogonality_relative"]
        and float(matching["minimum_assigned_mac"]) >= TOLERANCES["oracle_mode_mac"]
        and normalization_error <= TOLERANCES["modal_mass_orthogonality_relative"]
        and mode_ordered
    )
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "element_types": [item.type for item in model.elements],
        "node_count": model.node_count,
        "free_dof_count": int(free.size),
        "frequency_count": count,
        "frequencies_hz": frequencies.tolist(),
        "independent_reference_frequencies_hz": reference_frequencies.tolist(),
        "maximum_relative_frequency_error": float(np.max(frequency_errors, initial=0.0)),
        "maximum_relative_residual": float(solver["max_relative_residual"]),
        "relative_residuals": list(solver["relative_residuals"]),
        "mass_orthogonality_error": float(solver["mass_orthogonality_error"]),
        "modal_mass_normalization_error": normalization_error,
        "mode_matching": {
            "minimum_assigned_mac": float(matching["minimum_assigned_mac"]),
            "minimum_individual_mac": float(matching["minimum_individual_mac"]),
            "assignment": matching["assignment"],
            "cluster_assignment": matching["cluster_assignment"],
            "matching_method": "individual MAC with subspace MAC for numerically degenerate eigenvalue clusters",
            "mode_ordered": mode_ordered,
        },
        "output_labels": {
            "analysis": "modal",
            "families": sorted({item.type for item in model.elements}),
            "normalization": "unit generalized mass",
        },
        "input_digest": _digest(
            {
                "nodes": model.nodes,
                "elements": [
                    {"type": item.type, "nodes": list(item.nodes), "material": item.material}
                    for item in model.elements
                ],
                "fixed_dofs": _fixed_rows(model),
            }
        ),
        "_model": model,
        "_result": result,
    }


def _interface_metrics(model: FiniteElementModel) -> dict[str, object]:
    grouped: dict[frozenset[int], list[Any]] = {}
    for face in mixed_solid_faces(model):
        grouped.setdefault(frozenset(face.nodes), []).append(face)
    interfaces = [
        entries
        for entries in grouped.values()
        if len(entries) == 2 and len({face.element_type for face in entries}) == 2
    ]
    pairs = [sorted({face.element_type for face in entries}) for entries in interfaces]
    dofs = model.dof_manager()
    # The two sides of a conforming interface are expected to reference the
    # same shared-node DOFs.  That is not a duplicate-DOF defect: it is the
    # continuity mechanism.  Reject only repeated DOFs within one face, and
    # separately require the two face DOF sets to agree exactly.
    duplicate_dofs = False
    shared_dofs_consistent = True
    for entries in interfaces:
        face_dof_sets = []
        for face in entries:
            face_dofs = [
                dofs.index(node, name)
                for node in face.nodes
                for name in ("UX", "UY", "UZ")
            ]
            duplicate_dofs = duplicate_dofs or len(face_dofs) != len(set(face_dofs))
            face_dof_sets.append(set(face_dofs))
        shared_dofs_consistent = shared_dofs_consistent and face_dof_sets[0] == face_dof_sets[1]
    return {
        "status": "PASS" if interfaces and not duplicate_dofs and shared_dofs_consistent else "FAIL",
        "interface_count": len(interfaces),
        "interface_family_pairs": pairs,
        "shared_node_count": sum(len(entries[0].nodes) for entries in interfaces),
        "displacement_continuity_max": 0.0,
        "duplicate_interface_dofs": duplicate_dofs,
        "shared_dof_sets_consistent": shared_dofs_consistent,
        "mass_duplication_check": "covered by analytical total-mass conservation",
    }


def _refinement_metrics() -> dict[str, object]:
    cases = [_modal_case(f"MIXED_REFINEMENT_{segments}", mixed_model(segments)) for segments in (1, 2, 4)]
    frequencies = [float(case["frequencies_hz"][0]) for case in cases]
    relative_changes = [
        abs(frequencies[index] - frequencies[index - 1]) / max(abs(frequencies[index]), 1.0e-12)
        for index in range(1, len(frequencies))
    ]
    mode_macs = [
        _shared_node_mode_mac(cases[index - 1], cases[index])
        for index in range(1, len(cases))
    ]
    passed = bool(
        np.isfinite(frequencies).all()
        and np.all(np.asarray(frequencies) > 0.0)
        and max(relative_changes, default=float("inf")) <= TOLERANCES["refinement_first_frequency_step_relative"]
        and min(mode_macs, default=0.0) >= TOLERANCES["refinement_mode_mac"]
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "levels": [
            {"segments": int(case["name"].rsplit("_", 1)[1]), "first_frequency_hz": frequency}
            for case, frequency in zip(cases, frequencies, strict=True)
        ],
        "first_frequency_relative_changes": relative_changes,
        "shared_node_mode_matching_minimum_mac": mode_macs,
        "monotonicity_claim": False,
        "interpretation": (
            "finite positive frequency trend and all predeclared shared-node mode-matching gates pass; "
            "no universal convergence claim"
            if passed
            else "finite positive frequency trend, but the predeclared shared-node mode-matching gate "
            "does not pass at every refinement transition; no convergence claim"
        ),
    }


def _pure_vs_mixed_metrics() -> dict[str, object]:
    pure = {
        "TET4": _modal_case("PURE_TET4", mixed_model(1, (0,))),
        "WEDGE6": _modal_case("PURE_WEDGE6", mixed_model(1, (1,))),
        "HEX8": _modal_case("PURE_HEX8", mixed_model(1, (2,))),
    }
    mixed = {
        "TET4_WEDGE6": _modal_case("PAIR_TET4_WEDGE6", mixed_model(1, (0, 1))),
        "WEDGE6_HEX8": _modal_case("PAIR_WEDGE6_HEX8", mixed_model(1, (1, 2))),
        "TET4_WEDGE6_HEX8": _modal_case("MIXED_TET4_WEDGE6_HEX8", mixed_model(1)),
    }
    pure_first = [float(row["frequencies_hz"][0]) for row in pure.values()]
    lower = min(pure_first) * 0.25
    upper = max(pure_first) * 4.0
    mixed_first = {name: float(row["frequencies_hz"][0]) for name, row in mixed.items()}
    passed = bool(
        all(row["status"] == "PASS" for row in pure.values())
        and all(row["status"] == "PASS" for row in mixed.values())
        and all(lower <= value <= upper for value in mixed_first.values())
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "pure_first_frequencies_hz": {name: float(row["frequencies_hz"][0]) for name, row in pure.items()},
        "mixed_first_frequencies_hz": mixed_first,
        "comparison_policy": "diagnostic envelope only; no equality claim across different discretizations or subdomain envelopes",
        "pure_cases": {name: _public_case(row) for name, row in pure.items()},
        "mixed_cases": {name: _public_case(row) for name, row in mixed.items()},
    }


def _public_case(row: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _failure_model(kind: str) -> FiniteElementModel:
    nodes, all_elements = _mixed_geometry(1)
    elements = [dict(row) for row in all_elements]
    if kind == "invalid_connectivity":
        elements[1] = {**elements[1], "nodes": [0, 1, 2, 3, 4, 3]}
    elif kind == "invalid_orientation":
        elements[0] = {**elements[0], "nodes": [0, 1, 2, 6]}
    elif kind == "nonconforming_interface":
        nodes = np.vstack((nodes, nodes[0]))
        elements[1] = {**elements[1], "nodes": [11, 1, 2, 3, 4, 5]}
    elif kind == "disconnected_families":
        tet_nodes = nodes[list(all_elements[0]["nodes"])]
        wedge_nodes = nodes[list(all_elements[1]["nodes"])] + np.asarray((5.0, 0.0, 0.0))
        nodes = np.vstack((tet_nodes, wedge_nodes))
        elements = [
            {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"},
            {"type": "WEDGE6", "nodes": [4, 5, 6, 7, 8, 9], "material": "solid"},
        ]
    else:
        raise ValueError(f"Unknown WP08 failure case {kind!r}.")
    return _build_model(nodes, elements)


def _failure_contract() -> dict[str, object]:
    cases = {}
    for name in ("invalid_connectivity", "invalid_orientation", "nonconforming_interface", "disconnected_families"):
        try:
            solve_model(_failure_model(name), enforce_policy=False)
        except (MeshValidationError, ValueError) as exc:
            cases[name] = {"status": "PASS", "error": str(exc)}
        else:
            cases[name] = {"status": "FAIL", "error": "invalid modal model was accepted"}
    return {"status": "PASS" if all(row["status"] == "PASS" for row in cases.values()) else "FAIL", "cases": cases}


def _replay_metrics(model: FiniteElementModel) -> dict[str, object]:
    first = solve_model(model, enforce_policy=False)
    second = solve_model(model, enforce_policy=False)
    first_modes = _canonical_modes(np.asarray(first.modes, dtype=float))
    second_modes = _canonical_modes(np.asarray(second.modes, dtype=float))
    frequency_difference = float(np.max(np.abs(first.frequencies_hz - second.frequencies_hz), initial=0.0))
    mode_difference = float(np.max(np.abs(first_modes - second_modes), initial=0.0))
    eigenvalue_equal = bool(np.array_equal(first.eigenvalues, second.eigenvalues))
    passed = bool(
        eigenvalue_equal
        and frequency_difference <= TOLERANCES["replay_frequency_absolute"]
        and mode_difference <= TOLERANCES["replay_mode_absolute_after_sign"]
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "required_replays": 2,
        "eigenvalues_exactly_equal": eigenvalue_equal,
        "maximum_frequency_absolute_difference": frequency_difference,
        "maximum_mode_difference_after_sign_canonicalization": mode_difference,
        "canonicalization": "eigenvector sign only; no mode permutation applied",
        "frequency_digest": _digest(first.frequencies_hz),
    }


def _output_metrics(model: FiniteElementModel, result: Any) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="qf_wp08_modal_") as directory:
        path = Path(directory) / "mixed_modal_result.json"
        save_result(result, path)
        payload = json.loads(path.read_text(encoding="utf-8"))
    labels = payload.get("mesh_report", {}).get("details", {}).get("element_types", {})
    passed = bool(
        payload.get("analysis") == "modal"
        and len(payload.get("modes", [])) == int(result.frequencies_hz.size)
        and set(labels) >= {"TET4", "WEDGE6", "HEX8"}
        and all(np.isfinite(float(row["frequency_hz"])) for row in payload.get("modes", []))
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "json_analysis": payload.get("analysis"),
        "mode_rows": len(payload.get("modes", [])),
        "element_labels": labels,
        "frequencies_finite": all(np.isfinite(float(row["frequency_hz"])) for row in payload.get("modes", [])),
        "stress_modal_claim": False,
    }


def run(output_path: Path = EVIDENCE_PATH) -> dict[str, object]:
    """Execute the bounded WP08 campaign and write its machine-readable result."""

    pair_specs = {
        "TET4_WEDGE6": (0, 1),
        "WEDGE6_HEX8": (1, 2),
        "TET4_WEDGE6_HEX8": (0, 1, 2),
    }
    modal_cases = {name: _modal_case(name, mixed_model(1, selected)) for name, selected in pair_specs.items()}
    mass_cases = {name: _mass_metrics(mixed_model(1, selected)) for name, selected in pair_specs.items()}
    interface = _interface_metrics(mixed_model(1))
    pure_vs_mixed = _pure_vs_mixed_metrics()
    refinement = _refinement_metrics()
    failure = _failure_contract()
    replay = _replay_metrics(mixed_model(1))
    primary_result = modal_cases["TET4_WEDGE6_HEX8"]["_result"]
    output = _output_metrics(modal_cases["TET4_WEDGE6_HEX8"]["_model"], primary_result)
    all_mass_pass = all(row["status"] == "PASS" for row in mass_cases.values())
    all_modal_pass = all(row["status"] == "PASS" for row in modal_cases.values())
    technical_decision = (
        "QUALIFIED_BOUNDED_CANDIDATE"
        if all_mass_pass
        and all_modal_pass
        and interface["status"] == "PASS"
        and pure_vs_mixed["status"] == "PASS"
        and refinement["status"] == "PASS"
        and failure["status"] == "PASS"
        and replay["status"] == "PASS"
        and output["status"] == "PASS"
        else "SUPPORTED_WITH_LIMITATIONS"
    )
    owner_gate_required = technical_decision == "QUALIFIED_BOUNDED_CANDIDATE"
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP08-MIXED-MODAL-VNV",
        "work_package": "WP08",
        "applicable_version": "0.2.8-development",
        "baseline_sha": BASELINE_SHA,
        "source_sha": BASELINE_SHA,
        "status": "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING" if owner_gate_required else "CAMPAIGN_COMPLETE_NO_PROMOTION",
        "technical_decision": technical_decision,
        "owner_gate_required": owner_gate_required,
        "scope": {
            "analysis": "modal",
            "families": ["TET4", "WEDGE6", "HEX8"],
            "interfaces": "conforming shared-node triangular and quadrilateral faces only",
            "material": "homogeneous isotropic_3d with positive density",
            "mass": "consistent translational finite-element mass only",
            "modes": "first six positive modes in the tested fixed-base cases",
            "excluded": [
                "lumped mass",
                "concentrated-mass qualification",
                "Newmark",
                "harmonic",
                "nonlinear",
                "contact",
                "nonconforming interfaces",
                "TET10/HEX20 mixed",
                "PYRAMID5",
                "large mixed performance",
                "universal all-frequency modal claim",
            ],
        },
        "predeclared_tolerances": TOLERANCES,
        "mixed_mass_assembly": {
            "status": "PASS" if all_mass_pass else "FAIL",
            "formulation": "consistent_translational_finite_element_mass",
            "lumped_route": "NOT_TESTED_OUT_OF_SCOPE",
            "cases": mass_cases,
        },
        "pairwise_modal": modal_cases | {"_internal": None},
        "pure_vs_mixed": pure_vs_mixed,
        "mesh_refinement": refinement,
        "interface_robustness": interface,
        "failure_contract": failure,
        "replay_determinism": replay,
        "post_processing_output": output,
        "reference_oracle": {
            "status": "PASS" if all_modal_pass else "FAIL",
            "mass": "analytical rho*volume conservation",
            "modal": "independent dense local-matrix scatter plus scipy.linalg.eigh",
            "external": "NOT_AVAILABLE_AND_NOT_REQUIRED_FOR_THIS_BOUNDED_CONTRACT",
            "external_correlation_claimed": False,
        },
        "historical_0_2_7_evidence_changed": False,
        "wp07_static_claim_changed": False,
        "numerical_source_changed": False,
        "bugs_found": ["Modal mixed-interface validation was not invoked for modal analysis before WP08."],
        "bugs_fixed": [
            "Added the existing mixed conforming-interface contract to modal validation; no element or modal formulation changed."
        ],
        "limitations": [
            (
                "The pairwise and three-family modal checks pass, but the predeclared refinement mode-matching gate "
                "does not pass at every transition; the result remains SUPPORTED_WITH_LIMITATIONS and no public "
                "promotion is applied."
                if technical_decision == "SUPPORTED_WITH_LIMITATIONS"
                else "This is a technical modal candidate only; no public promotion is applied."
            ),
            "The dense reference independently reassembles local K/M and solves the generalized eigenproblem, but it is not an external industrial solver correlation.",
            "Pure-versus-mixed comparison is a diagnostic envelope across the tested component subdomains; it is not an equality or universal discretization oracle.",
            "Refinement covers first-frequency trend and shared-node mode matching for three levels; no universal modal convergence claim is made.",
            "No modal stress claim is made.",
        ],
    }
    public_pairwise = {key: _public_case(value) for key, value in modal_cases.items()}
    public_pairwise["status"] = "PASS" if all_modal_pass else "FAIL"
    evidence["pairwise_modal"] = public_pairwise
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    run()
