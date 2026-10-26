"""Prospective HEX8-SRI study matrix; declarations only, with no FEM calls."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


FORMULATIONS = ("hex8_standard", "sri_historical", "sri_corrected")
POISSON_RATIOS = (0.3, 0.45, 0.49, 0.499, 0.4999)
MESH_BUDGETS = (
    ((4, 2, 2), 180, 512),
    ((8, 4, 4), 300, 1024),
    ((16, 8, 8), 900, 4096),
    ((32, 16, 16), 3600, 16384),
)
PROPOSED_THRESHOLDS = (
    "free_residual_relative<=1e-7; force_and_moment_closure_relative<=1e-6; "
    "energy_identity_relative<=1e-8; at finest two-level change in mean UZ and energy<=2%; "
    "finest displacement error versus independently verified 3D mixed reference<=5%"
)


def _case_id(formulation: str, poisson_ratio: float, mesh: tuple[int, int, int]) -> str:
    nu_id = f"{poisson_ratio:.4f}".rstrip("0").rstrip(".").replace(".", "p")
    mesh_id = "x".join(str(value) for value in mesh)
    return f"{formulation}-nu_{nu_id}-{mesh_id}"


def iter_mesh_convergence_rows() -> list[dict[str, Any]]:
    """Return 60 frozen proposal rows; no test or manifest is registered here."""

    rows: list[dict[str, Any]] = []
    for mesh, wall_seconds, rss_mib in MESH_BUDGETS:
        nx, ny, nz = mesh
        elements = nx * ny * nz
        nodes = (nx + 1) * (ny + 1) * (nz + 1)
        dofs = 3 * nodes
        fixed_dofs = 3 * (ny + 1) * (nz + 1)
        dense_global_k_mib = dofs * dofs * 8 / (1024.0**2)
        for poisson_ratio in POISSON_RATIOS:
            bulk_to_shear = 2.0 * (1.0 + poisson_ratio) / (3.0 * (1.0 - 2.0 * poisson_ratio))
            for formulation in FORMULATIONS:
                identifier = _case_id(formulation, poisson_ratio, mesh)
                rows.append(
                    {
                        "campaign_status": "PREPARED_NOT_AUTHORIZED",
                        "entry_status": "PLANNED_NOT_IMPLEMENTED_OR_REGISTERED",
                        "test_nodeid_proposal": (
                            f"tests/verification/test_hex8_sri_convergence.py::test_convergence_case[{identifier}]"
                        ),
                        "formulation": formulation,
                        "poisson_ratio": poisson_ratio,
                        "E_Pa": 1.0e6,
                        "dimensions_m": "20x1x1",
                        "mesh_elements_xyz": f"{nx}x{ny}x{nz}",
                        "element_count": elements,
                        "node_count": nodes,
                        "dof_count": dofs,
                        "fixed_dof_count": fixed_dofs,
                        "free_dof_count": dofs - fixed_dofs,
                        "bulk_to_shear_kappa_over_mu": bulk_to_shear,
                        "oracle": "Timoshenko trend only; independent 3D mixed reference required for accuracy gate",
                        "primary_observables": "signed mean loaded-face UZ; strain energy; independent-reference error",
                        "proposed_acceptance_thresholds": PROPOSED_THRESHOLDS,
                        "threshold_status": "PROPOSAL_REQUIRES_OWNER_FREEZE_BEFORE_EXECUTION",
                        "memory_budget_mib": rss_mib,
                        "dense_single_global_K_lower_bound_mib": dense_global_k_mib,
                        "required_assembly_mode": "sparse_global_operator_before_finest_level",
                        "wall_budget_seconds": wall_seconds,
                        "stop_criteria": "first integrity/provenance failure; non-finite state; non-positive sampled J; budget exceeded; frozen criterion failure",
                        "max_attempts": 1,
                        "priority": "MUST",
                    }
                )
    return rows


def write_mesh_convergence_matrix(path: Path) -> int:
    """Write the proposal matrix without creating an authorization manifest."""

    rows = iter_mesh_convergence_rows()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def iter_supplemental_validation_rows() -> list[dict[str, Any]]:
    """Plan patch, geometry-screen, distortion and spectral cases without executing them."""

    rows: list[dict[str, Any]] = []

    def add_row(
        *,
        study: str,
        nodeid: str,
        formulation: str,
        poisson_ratio: float | str,
        geometry: str,
        mesh: tuple[int, int, int],
        oracle: str,
        observable: str,
        threshold: str,
        memory_mib: int,
        wall_seconds: int,
        stop: str,
        priority: str,
    ) -> None:
        nx, ny, nz = mesh
        elements = nx * ny * nz
        nodes = (nx + 1) * (ny + 1) * (nz + 1)
        dofs = 3 * nodes
        rows.append(
            {
                "campaign_status": "PREPARED_NOT_AUTHORIZED",
                "entry_status": "PLANNED_NOT_IMPLEMENTED_OR_REGISTERED",
                "study_family": study,
                "test_nodeid_proposal": nodeid,
                "formulation": formulation,
                "poisson_ratio": poisson_ratio,
                "E_Pa": 1.0e6,
                "dimensions_or_geometry": geometry,
                "mesh_elements_xyz": "x".join(str(value) for value in mesh),
                "element_count": elements,
                "node_count": nodes,
                "dof_count": dofs,
                "fixed_dof_count": 0,
                "free_dof_count": dofs,
                "oracle": oracle,
                "primary_observables": observable,
                "proposed_acceptance_thresholds": threshold,
                "threshold_status": "PROPOSAL_REQUIRES_OWNER_FREEZE_BEFORE_EXECUTION",
                "memory_budget_mib": memory_mib,
                "wall_budget_seconds": wall_seconds,
                "stop_criteria": stop,
                "max_attempts": 1,
                "priority": priority,
            }
        )

    nu_values = (0.3, 0.4999)
    patch_modes = (
        "uniform_dilatation",
        "hydrostatic_compression",
        "pure_shear",
        "uniaxial_tension",
        "general_affine",
        "infinitesimal_rotation",
    )
    for formulation in FORMULATIONS:
        for poisson_ratio in nu_values:
            nu_id = f"{poisson_ratio:.4f}".rstrip("0").rstrip(".").replace(".", "p")
            for mode in patch_modes:
                add_row(
                    study="analytic_patch_energy",
                    nodeid=(
                        "tests/verification/test_hex8_sri_patch_energy.py::test_patch_case["
                        f"{formulation}-{mode}-nu_{nu_id}-regular]"
                    ),
                    formulation=formulation,
                    poisson_ratio=poisson_ratio,
                    geometry="affine unit cube; 1 element; 8 nodes/24 local DDL",
                    mesh=(1, 1, 1),
                    oracle="closed-form stress, energy and resultant for prescribed affine field",
                    observable="strain, stress, internal energy, nodal force and rigid-force norm",
                    threshold="scaled analytical relative force/energy error<=1e-10; freeze before execution",
                    memory_mib=128,
                    wall_seconds=30,
                    stop="first nonfinite value, analytic mismatch or provenance error; preserve failure",
                    priority="MUST",
                )

    geometry_families = (
        "regular",
        "moderate_skew",
        "severe_shear",
        "warped",
        "stretched_z0p1",
        "near_degenerate_z0p05",
        "seeded_20261026",
    )
    for family in geometry_families:
        add_row(
            study="geometry_quality_screen",
            nodeid=(f"tests/unit/test_hex8_sri_mesh_quality_families.py::test_quality_family[{family}]"),
            formulation="n/a_geometry_only",
            poisson_ratio="n/a",
            geometry=family,
            mesh=(4, 2, 2),
            oracle="independent coordinate map and sampled/certified Jacobian geometry checks",
            observable="detJ samples, scaled Jacobian, aspect ratio, nonorthogonality, geometry SHA",
            threshold="finite positive sampled detJ; certify positivity for any severe case retained",
            memory_mib=128,
            wall_seconds=30,
            stop="any nonfinite metric, nonpositive Jacobian or missing geometry provenance",
            priority="MUST",
        )

    spectral_families = (
        "regular",
        "moderate_skew",
        "severe_shear",
        "warped",
        "stretched_z0p1",
        "near_degenerate_z0p05",
        "seeded_20261026",
    )
    for formulation in FORMULATIONS:
        for poisson_ratio in nu_values:
            nu_id = f"{poisson_ratio:.4f}".rstrip("0").rstrip(".").replace(".", "p")
            for family in spectral_families:
                add_row(
                    study="local_element_stability_spectrum",
                    nodeid=(
                        "tests/verification/test_hex8_sri_spectrum.py::test_element_spectrum["
                        f"{formulation}-nu_{nu_id}-{family}]"
                    ),
                    formulation=formulation,
                    poisson_ratio=poisson_ratio,
                    geometry=family,
                    mesh=(1, 1, 1),
                    oracle="six analytic rigid vectors plus scaled numerical rank and mode fields",
                    observable="nullity, positive singular scale, mode shapes, symmetry, tolerance sensitivity",
                    threshold="exactly six rigid modes and no extra zero-energy mode at predeclared scaled cutoff",
                    memory_mib=256,
                    wall_seconds=60,
                    stop="invalid Jacobian, nonfinite spectrum, unexpected null mode or budget overrun",
                    priority="DEFERRED_OWNER_EIGENSOLVE_REQUIRED",
                )

    global_distortions = ("moderate_skew", "severe_shear", "warped", "stretched_z0p1", "seeded_20261026")
    for formulation in FORMULATIONS:
        for poisson_ratio in nu_values:
            nu_id = f"{poisson_ratio:.4f}".rstrip("0").rstrip(".").replace(".", "p")
            for family in global_distortions:
                add_row(
                    study="global_distortion_response",
                    nodeid=(
                        "tests/verification/test_hex8_sri_distortion.py::test_distorted_cantilever["
                        f"{formulation}-nu_{nu_id}-{family}]"
                    ),
                    formulation=formulation,
                    poisson_ratio=poisson_ratio,
                    geometry=family,
                    mesh=(4, 2, 2),
                    oracle="independent 3D mixed reference for identical geometry, supports and load",
                    observable="signed UZ, projected strain/energy, residual, reactions and global balance",
                    threshold="residual<=1e-7; force/moment<=1e-6 proposed; reference error<=5% proposed",
                    memory_mib=1024,
                    wall_seconds=180,
                    stop="uncertified/nonpositive Jacobian, frozen threshold failure or resource limit",
                    priority="SHOULD",
                )

    return rows


def write_supplemental_validation_matrix(path: Path) -> int:
    """Write the supplementary proposed cases; no authorization fields are granted."""

    rows = iter_supplemental_validation_rows()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
