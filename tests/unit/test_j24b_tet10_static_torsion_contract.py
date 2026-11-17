from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tests.verification.test_j24b_tet10_static_torsion import (
    _campaign_summary,
    CORRECTED_H1_CONTRACT_PATH,
    CORRECTED_H1_NODEID,
    _load_contract,
    _end_twist,
    _reintegrate_loads,
    _validate_model_input,
)
from solveur.mesh.gmsh_importer import GmshModelImporter


ROOT = Path(__file__).resolve().parents[2]


def test_j24b_frozen_contract_matches_independent_saint_venant_calculation() -> None:
    contract = json.loads((ROOT / "research/j24b/tet10_torsion/contract.json").read_text(encoding="utf-8"))
    model = contract["model"]
    geometry = model["geometry"]
    material = model["material"]
    torque = model["load"]["torque_Nm"]
    reference = contract["reference"]
    shear = material["young_modulus_Pa"] / (2.0 * (1.0 + material["poisson_ratio"]))
    polar_moment = math.pi * geometry["radius_m"] ** 4 / 2.0
    twist = torque * geometry["length_m"] / (shear * polar_moment)
    assert math.isclose(reference["shear_modulus_Pa"], shear, rel_tol=1e-15)
    assert math.isclose(reference["polar_moment_m4"], polar_moment, rel_tol=1e-15)
    assert math.isclose(reference["tip_twist_rad"], twist, rel_tol=1e-15)


def test_j24b_corrected_h1_contract_matches_preflight_003_artifact_manifest() -> None:
    contract = _load_contract(CORRECTED_H1_CONTRACT_PATH, expected_nodeid=CORRECTED_H1_NODEID)
    mesh = ROOT / contract["inputs"]["mesh_directory"] / contract["inputs"]["levels"]["h1"]["mesh"]
    manifest_path = ROOT / contract["corrected_h1_input_identity"]["preflight_003_artifact_manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(row for row in manifest["artifacts"] if row["path"] == mesh.name)
    actual = hashlib.sha256(mesh.read_bytes()).hexdigest()
    assert record["sha256"] == actual
    assert contract["inputs"]["levels"]["h1"]["mesh_sha256"] == actual


def test_j24b_all_imported_meshes_match_frozen_geometry_material_and_supports() -> None:
    contract = _load_contract()
    levels = contract["inputs"]["levels"]
    for level, entry in levels.items():
        mesh = ROOT / contract["inputs"]["mesh_directory"] / entry["mesh"]
        setup = ROOT / contract["inputs"]["mesh_directory"] / entry["setup"]
        model = GmshModelImporter().import_model(mesh, setup).model
        summary = _validate_model_input(model, contract)
        assert summary["element_families"] == ["TET10"]
        assert summary["analysis"] == {"type": "linear_static", "method": "direct"}


def test_j24b_tip_twist_fit_recovers_rigid_small_rotation_on_exact_xL_plane() -> None:
    theta = 2.5e-4
    coordinates = np.asarray(
        [[3.0, 0.5, 0.0], [3.0, -0.5, 0.0], [3.0, 0.0, 0.5], [3.0, 0.0, -0.5]],
        dtype=float,
    )
    displacement = np.column_stack(
        (np.zeros(4), -theta * coordinates[:, 2], theta * coordinates[:, 1])
    )
    assert math.isclose(_end_twist(coordinates, displacement), theta, rel_tol=1e-14)


def test_j24b_load_reintegration_recovers_zero_force_and_positive_x_torque() -> None:
    model = SimpleNamespace(
        nodes=np.asarray(
            [[0.0, 1.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]
        ),
        loads=[
            SimpleNamespace(node=0, dof="UZ", value=250.0),
            SimpleNamespace(node=1, dof="UZ", value=-250.0),
            SimpleNamespace(node=2, dof="UY", value=-250.0),
            SimpleNamespace(node=3, dof="UY", value=250.0),
        ],
    )
    force, moment = _reintegrate_loads(model)
    np.testing.assert_allclose(force, np.zeros(3), atol=0.0, rtol=0.0)
    np.testing.assert_allclose(moment, [1000.0, 0.0, 0.0], atol=0.0, rtol=0.0)


def test_j24b_campaign_summary_keeps_missing_mesh_data_inconclusive() -> None:
    contract = {"contract_id": "J24B-TEST"}
    summary = _campaign_summary(
        [{"level": "h1", "state": "LEVEL_FAILED_OR_INCOMPLETE", "exception": "controlled test"}],
        contract,
    )
    assert summary["status"] == "INCONCLUSIVE"
    assert summary["reasons"]
