"""Guarded WP-C02-AR M4/M5 production-FEM campaign.

The always-enabled test is a geometry/model preflight only.  Scientific solves
require the Owner's token and the exact frozen execution-manifest digest, and
write the complete result record before applying any acceptance assertion.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import LinearStaticSolver
from solveur.mesh.validation import MeshValidator
from scripts.wpc02_ar_native_collection import (
    contact_force_vectors,
    decode_contact_rows,
    decode_audit_vectors,
    elastic_strain_energy_from_total_internal,
    production_free_stationarity_inf,
    production_support_reactions,
    resultant_and_moment,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "qualification/0_2_12/wp_c02_ar_mesh_plan.json"
AJ_PATH = ROOT / "tests/unit/test_wpc02_aj_partial_active_contact.py"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
AJ_SHA256 = PLAN["provenance"]["aj_test_sha256"]
FRONT_X_M = 0.5
GAP_M = 1.0e-3
MASTER_TRIANGLE = ((-2.0, -1.0, 0.0), (3.0, -1.0, 0.0), (0.5, 4.0, 0.0))
MASTER_NODE_IDS = ("UX", "UY", "UZ")
OWNER_GO_TOKEN = "GO-RUN-FEM-NATIF"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frozen_aj() -> Any:
    actual = _sha256(AJ_PATH)
    if actual != AJ_SHA256:
        raise RuntimeError(f"Frozen AJ fixture hash mismatch: expected {AJ_SHA256}, got {actual}.")
    spec = importlib.util.spec_from_file_location("wpc02_ar_frozen_aj_fixture", AJ_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the frozen AJ fixture helpers.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _level_contract(level: str) -> dict[str, Any]:
    return next(row for row in PLAN["mesh_family"]["levels"] if row["level"] == level)


def _build_model(level: str) -> tuple[FiniteElementModel, tuple[Any, ...], np.ndarray]:
    """Build the AR benchmark from the frozen AJ mesh/load helpers."""
    spec = _level_contract(level)
    aj = _frozen_aj()
    mesh = aj._mesh((spec["nx"], spec["ny"], spec["nz"]))
    xyz, tets, bottom, top, _areas, _boundary, _bottom_triangles = mesh
    master_ids = tuple(range(len(xyz), len(xyz) + 3))
    nodes = np.vstack((xyz, np.asarray(MASTER_TRIANGLE, dtype=float)))
    external = np.asarray(aj._load(mesh, FRONT_X_M), dtype=float)

    elements = [
        {"type": "TET4", "nodes": [int(node) for node in tet], "material": "solid"}
        for tet in np.asarray(tets, dtype=int)
    ]
    fixed = [
        {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
        for node in (*top, *master_ids)
    ]
    loads = [
        {"node": int(node), "dof": dof, "value": float(external[node, axis])}
        for node in range(len(xyz))
        for axis, dof in enumerate(("UX", "UY", "UZ"))
        if external[node, axis] != 0.0
    ]
    contacts = [
        {
            "slave_node": int(node),
            "master_nodes": list(master_ids),
            "name": f"WP-C02-AR-{level}-bottom-{int(node)}",
            "gap_tolerance": PLAN["frozen_aj_acceptance_gates"]["gap_tolerance_m"],
            "friction_coefficient": 0.0,
        }
        for node in bottom
    ]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=elements,
        materials={"solid": {"type": "isotropic_3d", "E": 3.0e6, "nu": 0.0}},
        fixed_dofs=fixed,
        loads=loads,
        contacts=contacts,
        analysis={
            "type": "linear_static",
            "method": "direct",
            "parameters": {
                "contact_projection_policy": "accepted_rigid_plane_v1",
                "contact_search_mode": "initial",
                "contact_tolerance_policy": "dimensional_v1",
                "contact_force_reference": 1000.0,
                "contact_force_tolerance": 0.0,
                "contact_force_relative_tolerance": 1.0e-10,
                "contact_max_iterations": 128,
            },
        },
    )
    return model, mesh, external


def _assert_model_contract(level: str, model: FiniteElementModel, mesh: tuple[Any, ...]) -> dict[str, Any]:
    spec = _level_contract(level)
    xyz, tets, bottom, top, _areas, _boundary, _bottom_triangles = mesh
    assert len(xyz) == spec["nodes"]
    assert len(tets) == spec["tet4"]
    assert 3 * len(xyz) == spec["mechanical_dofs"]
    assert 3 * len(xyz) - 3 * len(top) == spec["free_dofs"]
    assert len(bottom) == spec["contact_rows"]
    assert np.array_equal(np.min(xyz, axis=0), np.asarray((0.0, 0.0, 1.0e-3)))
    assert np.array_equal(np.max(xyz, axis=0), np.asarray((1.0, 1.0, 1.001)))
    assert model.node_count == len(xyz) + 3
    assert len(model.elements) == spec["tet4"]
    assert len(model.contacts) == spec["contact_rows"]
    assert model.materials["solid"]["type"] == "isotropic_3d"
    assert model.materials["solid"]["E"] == 3.0e6
    assert model.materials["solid"]["nu"] == 0.0
    assert all(contact.slave_node == int(node) for contact, node in zip(model.contacts, bottom))
    assert all(contact.master_nodes == (len(xyz), len(xyz) + 1, len(xyz) + 2) for contact in model.contacts)
    assert all(contact.friction_coefficient == 0.0 for contact in model.contacts)
    assert all(contact.gap_tolerance == 1.0e-10 for contact in model.contacts)
    assert model.analysis.type == "linear_static" and model.analysis.method == "direct"
    assert model.analysis.parameters["contact_projection_policy"] == "accepted_rigid_plane_v1"
    assert model.analysis.parameters["contact_search_mode"] == "initial"
    assert model.analysis.parameters["contact_tolerance_policy"] == "dimensional_v1"
    assert model.analysis.parameters["contact_force_reference"] == 1000.0
    assert model.analysis.parameters["contact_force_tolerance"] == 0.0
    assert model.analysis.parameters["contact_force_relative_tolerance"] == 1.0e-10
    assert model.analysis.parameters["contact_max_iterations"] == 128
    fixed_by_node = {condition.node: set(condition.dofs) for condition in model.fixed_dofs}
    expected_fixed_nodes = set(map(int, top)) | {len(xyz), len(xyz) + 1, len(xyz) + 2}
    assert set(fixed_by_node) == expected_fixed_nodes
    assert all(fixed_by_node[node] == {"UX", "UY", "UZ"} for node in expected_fixed_nodes)

    report = MeshValidator().validate(model)
    assert report.status != "FAIL", "; ".join(report.errors)
    for contact in model.contacts:
        normal, _barycentric, gap = contact.geometry(model.nodes)
        assert np.allclose(normal, (0.0, 0.0, 1.0), rtol=0.0, atol=1.0e-10)
        assert abs(gap - GAP_M) <= 1.0e-10
    return {
        "mesh_validation_status": report.status,
        "mesh_validation_warnings": list(report.warnings),
        "model_nodes_including_master_geometry": model.node_count,
        "solver_dofs_including_fixed_master_geometry": model.dof_manager().ndof,
        "body_nodes": len(xyz),
        "body_mechanical_dofs": spec["mechanical_dofs"],
        "body_free_dofs": spec["free_dofs"],
        "tet4": len(tets),
        "contact_rows": len(model.contacts),
        "master_triangle_coordinates_m": [list(point) for point in MASTER_TRIANGLE],
        "non_fem_preflight_only": True,
    }


def test_wpc02_ar_native_model_preflight_m4_m5() -> None:
    """Check prepared mesh/model sizes and contact geometry without assembly or solve."""
    assert _sha256(PLAN_PATH) == "fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc"
    assert _sha256(AJ_PATH) == AJ_SHA256
    for level in ("M4", "M5"):
        model, mesh, _external = _build_model(level)
        diagnostic = _assert_model_contract(level, model, mesh)
        print(json.dumps({"wpc02_ar_native_preflight": {"level": level, **diagnostic}}, sort_keys=True))


def _require_owner_go(level: str) -> Path:
    token = os.environ.get("WPC02_AR_NATIVE_OWNER_GO_TOKEN", "")
    digest = os.environ.get("WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256", "")
    manifest_path = Path(os.environ.get(
        "WPC02_AR_NATIVE_MANIFEST_PATH",
        ROOT / "qualification/0_2_12/wp_c02_ar_native_execution_manifest.json",
    ))
    if token != OWNER_GO_TOKEN:
        pytest.skip("FEM scenario is gated on explicit GO-RUN-FEM-NATIF from the Owner.")
    if not digest or _sha256(manifest_path) != digest:
        pytest.skip("FEM scenario is gated on Owner approval of this exact execution-manifest SHA-256.")
    output_dir = os.environ.get("WPC02_AR_NATIVE_OUTPUT_DIR")
    if not output_dir:
        pytest.fail("The one-shot runner did not provide an archive output directory.")
    archive = Path(output_dir).resolve()
    ledger_path = archive / "run_ledger.json"
    if not ledger_path.is_file():
        pytest.fail("The one-shot runner ledger is missing; direct scenario invocation is refused.")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger.get("authorization", {}).get("manifest_sha256") != digest:
        pytest.fail("The run ledger does not bind this test to the approved manifest.")
    entries = [item for item in ledger.get("scenarios", []) if item.get("level") == level]
    if len(entries) != 1 or entries[0].get("attempt_count") != 1 or entries[0].get("state") != "RUNNING":
        pytest.fail(f"The run ledger does not authorize exactly one active attempt for {level}.")
    record = archive / f"{level.lower()}_diagnostics.json"
    if record.exists():
        pytest.fail(f"Refusing a repeated {level} scenario; diagnostic record already exists: {record}.")
    return record


def _scenario_diagnostic(level: str) -> dict[str, Any]:
    record_path = _require_owner_go(level)
    aj = _frozen_aj()
    model, mesh, external = _build_model(level)
    model_preflight = _assert_model_contract(level, model, mesh)
    xyz, tets, bottom, top, areas, _boundary, bottom_triangles = mesh
    spec = _level_contract(level)
    n_body = len(xyz)
    bottom = np.asarray(bottom, dtype=int)
    top = np.asarray(top, dtype=int)

    partial_record: dict[str, Any] = {
        "schema": "wpc02-ar-native-scenario-v1",
        "campaign": "WP-C02-AR native Python/pytest, non-Docker execution",
        "level": level,
        "scenario_state": "STARTED",
        "git_head": os.environ.get("WPC02_AR_NATIVE_GIT_HEAD", "UNBOUND"),
        "git_tree_oid": os.environ.get("WPC02_AR_NATIVE_GIT_TREE_OID", "UNBOUND"),
        "aj_fixture_sha256": AJ_SHA256,
        "mesh_contract": spec,
        "production_route": "LinearStaticSolver -> GlobalAssembler -> FrictionlessActiveSetSolver",
        "model_preflight": model_preflight,
    }
    record_path.write_text(json.dumps(partial_record, indent=2, sort_keys=True), encoding="utf-8")

    try:
        with threadpool_limits(limits=1):
            # Full detail is required by the documented SolverAudit contract:
            # summary mode omits sparse vector values needed for reactions.
            result = LinearStaticSolver().solve(model, detail_level="full")
        if result.status != "PASS" or result.solver.get("contact", {}).get("method") != "lagrange_active_set":
            raise RuntimeError("The public production FEM/contact route did not return a converged active-set result.")

        dofs = result.dofs
        body_indices = np.asarray(
            [dofs.index(node, dof) for node in range(n_body) for dof in ("UX", "UY", "UZ")], dtype=int
        )
        prescribed = np.asarray(
            [3 * int(node) + axis for node in top for axis in range(3)], dtype=int
        )
        u = np.asarray(result.displacements[body_indices], dtype=float)
        audit_vectors = decode_audit_vectors(result.audit.vectors, expected_size=dofs.ndof)
        production_internal_raw = audit_vectors["internal_force"][body_indices]
        production_residual_raw = audit_vectors["residual"][body_indices]
        production_load = audit_vectors["loads"][body_indices]
        load_max_abs_difference = float(np.max(np.abs(production_load - external.reshape(-1)), initial=0.0))
        if load_max_abs_difference != 0.0:
            raise RuntimeError(f"Production-assembled load vector differs from the frozen AJ load by {load_max_abs_difference} N.")
        K_independent = aj._independent_stiffness(xyz, tets)
        contact_rows = result.solver["contact"].get("contacts")
        if not isinstance(contact_rows, list) or len(contact_rows) != len(bottom):
            raise RuntimeError("Production solver did not return one result row per frozen AR contact constraint.")

        contact = decode_contact_rows(
            contact_rows,
            contact_nodes=bottom,
            area_weights_m2=np.asarray([areas[int(node)] for node in bottom], dtype=float),
            # WP-C02-AR freezes a +Z normal; production row pressure already
            # uses positive compression and is the force on the slave node.
            expected_normals=np.asarray([0.0, 0.0, 1.0]),
            active_force_tolerance_n=PLAN["frozen_aj_acceptance_gates"]["force_tolerance_n"],
        )
        gaps = contact["gaps_m"]
        multipliers = contact["multipliers_n"]
        solver_active = contact["active_flags"]
        u_nodes = u.reshape((n_body, 3))
        reconstructed_gaps = GAP_M + u_nodes[bottom, 2]
        gap_reconstruction_error = float(np.max(np.abs(gaps - reconstructed_gaps), initial=0.0))
        active = multipliers > PLAN["frozen_aj_acceptance_gates"]["force_tolerance_n"]
        opened = gaps > PLAN["frozen_aj_acceptance_gates"]["gap_tolerance_m"]
        pressure = contact["pressure_pa"]
        support = production_support_reactions(audit_vectors, top_nodes=top)[:n_body]

        partial_record.update(
            {
                "scenario_state": "SOLVER_COMPLETED_RAW_FIELDS",
                "solver": {
                    "result_status": result.status,
                    "result_method": result.method,
                    "contact_method": result.solver["contact"].get("method"),
                    "contact_converged": result.solver["contact"].get("converged"),
                    "contact_iteration_count": result.solver["contact"].get("iteration_count"),
                    "linear_static_solver_class": "solveur.core.solvers.static.LinearStaticSolver",
                    "synthetic_result_substitution": False,
                    "experimental_frozen_adapter_used_for_solve": False,
                    "solver_dofs_including_master_geometry": int(dofs.ndof),
                },
                "field_values": {
                    "body_displacements_m_node_major_xyz": u_nodes.tolist(),
                    "contact_node_ids": bottom.tolist(),
                    "contact_gaps_m": gaps.tolist(),
                    "contact_multipliers_n": multipliers.tolist(),
                    "production_contact_active_set_flags": solver_active.tolist(),
                    "contact_pressures_pa": pressure.tolist(),
                    "contact_area_weights_m2": [float(areas[int(node)]) for node in bottom],
                    "support_reactions_n_node_major_xyz": support.tolist(),
                    "external_nodal_loads_n_node_major_xyz": external.tolist(),
                    "production_total_internal_force_n_body_node_major_xyz": production_internal_raw.reshape((n_body, 3)).tolist(),
                    "production_residual_force_n_body_node_major_xyz": production_residual_raw.reshape((n_body, 3)).tolist(),
                },
            }
        )
        record_path.write_text(json.dumps(partial_record, indent=2, sort_keys=True), encoding="utf-8")

        independent = aj._independent_discrete_kkt(
            K_independent,
            external.reshape(-1),
            bottom,
            prescribed,
        )
        free = independent["free_dofs"]
        u_ref = np.asarray(independent["displacement"], dtype=float)
        lambda_ref = np.asarray(independent["multipliers"], dtype=float)
        gap_ref = np.asarray(independent["gaps"], dtype=float)
        production_internal = production_internal_raw
        production_residual = production_residual_raw
        contact_force = contact_force_vectors(
            node_ids=bottom,
            normals=contact["normals"],
            force_magnitudes_n=multipliers,
            node_count=n_body,
        ).reshape(-1)
        production_stationarity = production_free_stationarity_inf(
            production_internal,
            external.reshape(-1),
            free,
        )
        residual_identity_error = float(
            np.linalg.norm(
                (production_internal - external.reshape(-1) - production_residual)[free], ord=np.inf
            )
        )

        _ = np.asarray([aj._lambda_exact(float(xyz[node, 0]), FRONT_X_M) for node in bottom])
        pressure_error_sq = 0.0
        exact_pressure_sq = 0.0
        for triangle in bottom_triangles:
            tri_nodes = np.asarray(triangle, dtype=int)
            tri_xyz = xyz[tri_nodes]
            tri_pressure = pressure[[int(np.flatnonzero(bottom == node)[0]) for node in tri_nodes]]
            for shape, point, area_weight in aj._tri_rule(tri_xyz):
                exact = aj._lambda_exact(float(point[0]), FRONT_X_M)
                pressure_error_sq += float((shape @ tri_pressure - exact) ** 2) * area_weight
                exact_pressure_sq += exact**2 * area_weight
        pressure_error = float(np.sqrt(pressure_error_sq / exact_pressure_sq))

        contact_force = contact_force.reshape((n_body, 3))
        external_resultant, external_moment = resultant_and_moment(xyz, external)
        support_resultant, support_moment = resultant_and_moment(xyz, support)
        contact_resultant, contact_moment = resultant_and_moment(xyz, contact_force)
        force_balance = external_resultant + support_resultant + contact_resultant
        moment_balance = external_moment + support_moment + contact_moment
        support_exact, support_moment_exact = aj._exact_top(FRONT_X_M)
        exact_contact_force, exact_contact_moment = aj._exact_contact(FRONT_X_M)
        force_scale = max(abs(float(exact_contact_force)), 1.0)
        moment_scale = force_scale

        contact_work = float(multipliers @ u_nodes[bottom, 2])
        contact_work_identity_error = abs(contact_work + GAP_M * float(multipliers.sum()))
        independent_contact_work = float(lambda_ref @ u_ref.reshape((-1, 3))[bottom, 2])
        independent_contact_work_identity_error = abs(
            independent_contact_work + GAP_M * float(lambda_ref.sum())
        )
        independent_contact_force = np.zeros((n_body, 3), dtype=float)
        independent_contact_force[bottom, 2] = lambda_ref
        reference_support = np.zeros((n_body, 3), dtype=float)
        support_mask = np.zeros(3 * n_body, dtype=bool)
        support_mask[prescribed] = True
        reference_residual = K_independent @ u_ref - external.reshape(-1) - independent_contact_force.reshape(-1)
        reference_support.reshape(-1)[support_mask] = reference_residual[support_mask]
        reference_support_resultant, reference_support_moment = resultant_and_moment(xyz, reference_support)
        reference_contact_resultant, reference_contact_moment = resultant_and_moment(xyz, independent_contact_force)
        ref_force_balance = external_resultant + reference_support_resultant + reference_contact_resultant
        ref_moment_balance = external_moment + reference_support_moment + reference_contact_moment

        field = aj._field_metrics(mesh, u, FRONT_X_M, K_independent)
        production_energy = elastic_strain_energy_from_total_internal(
            np.asarray(u, dtype=float), production_internal, contact_force.reshape(-1)
        )
        field["strain_energy_j"] = production_energy
        field["fe_energy_matrix_vs_quadrature_error_j"] = abs(
            production_energy - field["fe_integrated_strain_energy_j"]
        )
        front = aj._front_diagnostics(bottom, xyz, areas, FRONT_X_M, spec["hx_m"], gaps, multipliers)
        front = _enrich_front_trace(front, bottom, xyz, gaps, multipliers, areas)
        front["rows_with_more_than_one_active_open_transition"] = _multiple_front_rows(front["front_trace_by_y"])
        hmax = max(
            float(np.linalg.norm(xyz[a] - xyz[b]))
            for tet in tets
            for i, a in enumerate(tet)
            for b in tet[i + 1 :]
        )
        production_force_balance = float(np.linalg.norm(force_balance) / force_scale)
        production_moment_balance = float(np.linalg.norm(moment_balance) / moment_scale)
        qp_force_balance = float(np.linalg.norm(ref_force_balance) / force_scale)
        qp_moment_balance = float(np.linalg.norm(ref_moment_balance) / moment_scale)
        production_complementarity = float(np.max(np.abs(gaps * multipliers), initial=0.0))
        partial_record = {
            **partial_record,
            "scenario_state": "COMPLETED_DIAGNOSTICS",
            "solver": {
                "result_status": result.status,
                "result_method": result.method,
                "contact_method": result.solver["contact"].get("method"),
                "contact_converged": result.solver["contact"].get("converged"),
                "contact_iteration_count": result.solver["contact"].get("iteration_count"),
                "linear_static_solver_class": "solveur.core.solvers.static.LinearStaticSolver",
                "synthetic_result_substitution": False,
                "experimental_frozen_adapter_used_for_solve": False,
                "solver_dofs_including_master_geometry": int(dofs.ndof),
            },
            "field_values": {
                "body_displacements_m_node_major_xyz": u_nodes.tolist(),
                "contact_node_ids": bottom.tolist(),
                "contact_gaps_m": gaps.tolist(),
                "contact_multipliers_n": multipliers.tolist(),
                "production_contact_active_set_flags": solver_active.tolist(),
                "contact_pressures_pa": pressure.tolist(),
                "contact_area_weights_m2": [float(areas[int(node)]) for node in bottom],
                "support_reactions_n_node_major_xyz": support.tolist(),
                "external_nodal_loads_n_node_major_xyz": external.tolist(),
                "production_total_internal_force_n_body_node_major_xyz": production_internal.reshape((n_body, 3)).tolist(),
                "production_residual_force_n_body_node_major_xyz": audit_vectors["residual"][body_indices].reshape((n_body, 3)).tolist(),
                "independent_qp_displacements_m_node_major_xyz": u_ref.reshape((n_body, 3)).tolist(),
                "independent_qp_multipliers_n": lambda_ref.tolist(),
            },
            "diagnostics": {
                "mesh": {
                    "nx_ny_nz": [spec["nx"], spec["ny"], spec["nz"]],
                    "nodes": n_body,
                    "tet4": len(tets),
                    "body_mechanical_dofs": spec["mechanical_dofs"],
                    "body_free_dofs": len(free),
                    "contact_rows": len(bottom),
                    "h_x_m": float(spec["hx_m"]),
                    "h_max_m": hmax,
                },
                "active_count": int(np.count_nonzero(active)),
                "open_count": int(np.count_nonzero(opened)),
                "solver_active_count": int(np.count_nonzero(solver_active)),
                "production_load_max_abs_difference_from_frozen_aj_n": load_max_abs_difference,
                "ordered_front_bracket_row_count": int(front["front_bracket_ordered_row_count"]),
                "maximum_penetration_m": max(0.0, -float(np.min(gaps))),
                "production_gap_reconstruction_error_m": gap_reconstruction_error,
                "production_complementarity_inf_nm": production_complementarity,
                "production_stationarity_inf_n": production_stationarity,
                "production_residual_stationarity_inf_n": float(np.linalg.norm(production_residual[free], ord=np.inf)),
                "production_residual_identity_error_inf_n": residual_identity_error,
                "independent_qp_primal_gap_min_m": float(np.min(gap_ref)),
                "independent_qp_dual_multiplier_min_n": float(np.min(lambda_ref)),
                "independent_qp_complementarity_inf_nm": float(independent["complementarity_inf_nm"]),
                "independent_qp_stationarity_inf_n": float(np.linalg.norm(independent["stationarity"], ord=np.inf)),
                "independent_qp_displacement_max_error_m": float(np.max(np.abs(u - u_ref))),
                "independent_qp_multiplier_max_error_n": float(np.max(np.abs(multipliers - lambda_ref))),
                "independent_qp_nnls_residual_sqrt_j": float(independent["nnls_residual_sqrt_j"]),
                "independent_qp_dual_condition": float(independent["dual_hessian_condition"]),
                "production_elastic_internal_force_max_abs_difference_from_independent_stiffness_n": float(
                    np.max(np.abs(production_internal + contact_force.reshape(-1) - K_independent @ u), initial=0.0)
                ),
                "strict_active_max_gap_m": float(np.max(gaps[active])) if np.any(active) else None,
                "strict_active_min_multiplier_n": float(np.min(multipliers[active])) if np.any(active) else None,
                "strict_open_min_gap_m": float(np.min(gaps[opened], initial=np.inf)),
                "strict_open_max_multiplier_n": float(np.max(multipliers[opened], initial=0.0)),
                "contact_resultant_n": float(multipliers.sum()),
                "contact_resultant_exact_n": float(exact_contact_force),
                "contact_resultant_error_n": abs(float(multipliers.sum()) - float(exact_contact_force)),
                "contact_resultant_relative_error": abs(float(multipliers.sum()) - float(exact_contact_force)) / force_scale,
                "contact_moment_nm": contact_moment.tolist(),
                "contact_moment_exact_nm": np.asarray(exact_contact_moment).tolist(),
                "contact_moment_error_nm": float(np.linalg.norm(contact_moment - exact_contact_moment)),
                "contact_moment_relative_error": float(np.linalg.norm(contact_moment - exact_contact_moment) / moment_scale),
                "production_force_balance_vector_n": force_balance.tolist(),
                "production_moment_balance_vector_nm": moment_balance.tolist(),
                "production_force_balance_relative": production_force_balance,
                "production_moment_balance_relative": production_moment_balance,
                "support_resultant_n": support_resultant.tolist(),
                "support_resultant_exact_n": np.asarray(support_exact).tolist(),
                "support_resultant_error_n": float(np.linalg.norm(support_resultant - support_exact)),
                "support_moment_nm": support_moment.tolist(),
                "support_moment_exact_nm": np.asarray(support_moment_exact).tolist(),
                "support_moment_error_nm": float(np.linalg.norm(support_moment - support_moment_exact)),
                "production_contact_work_j": contact_work,
                "production_contact_work_identity_error_j": contact_work_identity_error,
                "independent_qp_contact_work_j": independent_contact_work,
                "independent_qp_contact_work_identity_error_j": independent_contact_work_identity_error,
                "independent_qp_force_balance_vector_n": ref_force_balance.tolist(),
                "independent_qp_moment_balance_vector_nm": ref_moment_balance.tolist(),
                "independent_qp_force_balance_relative": qp_force_balance,
                "independent_qp_moment_balance_relative": qp_moment_balance,
                "pressure_relative_l2_error": pressure_error,
                "force_scale_n": force_scale,
                "moment_scale_nm": moment_scale,
                "units": {"length": "m", "force": "N", "pressure": "Pa", "moment": "N*m", "energy": "J"},
                **front,
                **field,
            },
            "criteria_source": {
                "historical_gates": "wp_c02_ar_mesh_plan.json:frozen_aj_acceptance_gates",
                "prospective_endpoint_gates": "wp_c02_ar_mesh_plan.json:proposed_ar_endpoint_gates_require_owner_approval",
                "prospective_front_gates": "wp_c02_ar_mesh_plan.json:proposed_ar_front_gate_requires_owner_approval",
                "no_adjacent_level_monotonicity_gate": True,
            },
        }
        record_path.write_text(json.dumps(partial_record, indent=2, sort_keys=True), encoding="utf-8")
        return partial_record
    except BaseException as exc:
        partial_record["scenario_state"] = "SOLVER_OR_DIAGNOSTIC_EXCEPTION"
        partial_record["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        record_path.write_text(json.dumps(partial_record, indent=2, sort_keys=True), encoding="utf-8")
        raise


def _multiple_front_rows(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report rows with more than one A/O transition after ignoring biactive nodes."""
    multiple = []
    for row in trace:
        labels = []
        for x in row["active_x_m"]:
            labels.append((float(x), "A"))
        for x in row["open_x_m"]:
            labels.append((float(x), "O"))
        labels.sort()
        collapsed = []
        for x, label in labels:
            if collapsed and collapsed[-1][1] == label:
                continue
            collapsed.append((x, label))
        transitions = sum(left[1] != right[1] for left, right in zip(collapsed, collapsed[1:]))
        if transitions > 1:
            multiple.append({"y_m": row["y_m"], "transition_count": transitions, "labels": collapsed})
    return multiple


def _enrich_front_trace(
    front: dict[str, Any],
    contact_nodes: np.ndarray,
    xyz: np.ndarray,
    gaps: np.ndarray,
    multipliers: np.ndarray,
    areas: dict[int, float],
) -> dict[str, Any]:
    """Add every node state and the bracketing values required by AR."""
    gap_tol = PLAN["frozen_aj_acceptance_gates"]["gap_tolerance_m"]
    force_tol = PLAN["frozen_aj_acceptance_gates"]["force_tolerance_n"]
    points = xyz[np.asarray(contact_nodes, dtype=int)]
    pressure = multipliers / np.asarray([areas[int(node)] for node in contact_nodes], dtype=float)
    row_details = []
    biactive = []
    ordered_count = 0
    for row in front["front_trace_by_y"]:
        indices = np.flatnonzero(np.isclose(points[:, 1], row["y_m"], rtol=0.0, atol=1.0e-14))
        states = []
        for index in indices:
            node = int(contact_nodes[index])
            active = multipliers[index] > force_tol
            opened = gaps[index] > gap_tol
            is_biactive = abs(gaps[index]) <= gap_tol and abs(multipliers[index]) <= force_tol
            state = "ACTIVE_AND_OPEN" if active and opened else "ACTIVE" if active else "OPEN" if opened else "BI-ACTIVE" if is_biactive else "UNCLASSIFIED"
            item = {
                "node": node,
                "x_m": float(points[index, 0]),
                "gap_m": float(gaps[index]),
                "lambda_n": float(multipliers[index]),
                "pressure_pa": float(pressure[index]),
                "classification": state,
            }
            states.append(item)
            if is_biactive:
                biactive.append(item)
        last_active = next((item for item in reversed(states) if item["classification"] in {"ACTIVE", "ACTIVE_AND_OPEN"}), None)
        first_open = next((item for item in states if item["classification"] in {"OPEN", "ACTIVE_AND_OPEN"}), None)
        ordered = (
            last_active is not None
            and first_open is not None
            and last_active["x_m"] < first_open["x_m"]
        )
        ordered_count += int(ordered)
        row_details.append(
            {
                **row,
                "ordered_active_open_bracket": ordered,
                "bracket_width_m": (
                    first_open["x_m"] - last_active["x_m"]
                    if last_active is not None and first_open is not None
                    else None
                ),
                "last_active_values": last_active,
                "first_open_values": first_open,
                "contact_states_by_x": states,
            }
        )
    front["front_trace_by_y"] = row_details
    front["front_bracket_ordered_row_count"] = ordered_count
    front["front_biactive_nodes"] = biactive
    return front


def _assert_scenario_criteria(row: dict[str, Any]) -> None:
    gate = PLAN["frozen_aj_acceptance_gates"]
    diag = row["diagnostics"]
    assert 0 < diag["active_count"] < diag["mesh"]["contact_rows"]
    assert diag["open_count"] > 0
    assert diag["maximum_penetration_m"] <= gate["production_maximum_penetration_m"]
    assert diag["production_gap_reconstruction_error_m"] <= gate["production_gap_reconstruction_error_m"]
    assert diag["production_complementarity_inf_nm"] <= gate["complementarity_tolerance_nm"]
    assert diag["strict_active_max_gap_m"] <= gate["production_strict_active_max_gap_m"]
    assert diag["strict_open_max_multiplier_n"] <= gate["production_strict_open_max_multiplier_n"]
    assert diag["production_stationarity_inf_n"] <= gate["production_stationarity_inf_residual_n"]
    assert diag["independent_qp_primal_gap_min_m"] >= gate["independent_qp_primal_min_gap_m"]
    assert diag["independent_qp_dual_multiplier_min_n"] >= gate["independent_qp_dual_min_multiplier_n"]
    assert diag["independent_qp_complementarity_inf_nm"] <= gate["independent_qp_complementarity_inf_nm"]
    assert diag["independent_qp_stationarity_inf_n"] <= gate["independent_qp_stationarity_inf_residual_n"]
    assert diag["independent_qp_displacement_max_error_m"] <= gate["production_vs_independent_qp_displacement_max_error_m"]
    assert diag["independent_qp_multiplier_max_error_n"] <= gate["production_vs_independent_qp_multiplier_max_error_n"]
    assert diag["production_force_balance_relative"] <= gate["production_normalized_force_balance"]
    assert diag["production_moment_balance_relative"] <= gate["production_normalized_moment_balance"]
    assert diag["independent_qp_force_balance_relative"] <= gate["independent_qp_normalized_force_balance"]
    assert diag["independent_qp_moment_balance_relative"] <= gate["independent_qp_normalized_moment_balance"]
    assert diag["production_contact_work_identity_error_j"] <= gate["production_contact_work_identity_error_j"]
    assert diag["independent_qp_contact_work_identity_error_j"] <= gate["independent_qp_contact_work_identity_error_j"]
    assert diag["fe_energy_matrix_vs_quadrature_error_j"] <= gate["fe_matrix_energy_vs_quadrature_error_j"]
    assert np.isfinite(diag["contact_resultant_relative_error"])
    assert np.isfinite(diag["contact_moment_relative_error"])
    assert np.isfinite(diag["front_error_max_abs_m"])
    assert np.isfinite(diag["front_error_rms_over_hx"])

    level = row["level"]
    if level in PLAN["proposed_ar_front_gate_requires_owner_approval"]["eligible_levels"]:
        assert diag["front_bracketed_row_count"] == diag["front_row_count"]
        assert diag["front_bracket_ordered_row_count"] == diag["front_row_count"]
        assert diag["front_error_max_over_hx"] <= 1.0
        assert not diag["rows_with_more_than_one_active_open_transition"]
        for point in (*diag["false_positives"], *diag["false_negatives"]):
            assert point["distance_to_front_over_hx"] <= 1.0


def test_wpc02_ar_native_m4() -> None:
    diagnostic = _scenario_diagnostic("M4")
    _assert_scenario_criteria(diagnostic)


def test_wpc02_ar_native_m5() -> None:
    diagnostic = _scenario_diagnostic("M5")
    _assert_scenario_criteria(diagnostic)
