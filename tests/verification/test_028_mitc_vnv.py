"""Executable WP04 gates for the bounded MITC3/MITC4 V&V campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.shell.mitc4 import ShellMaterial
from solveur.verification.mitc3_campaign import Mitc3ValidationCampaign
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.mitc4_convergence import Mitc4StructuralConvergence
from solveur.verification.mitc4_harmonic import Mitc4HarmonicModalStudy
from solveur.verification.mitc4_mechanical import MechanicalVerifier
from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy
from solveur.verification.mitc4_newmark import Mitc4NewmarkFreeVibrationStudy
from solveur.elements.shell.mitc4.constants import DOF_PER_NODE, UZ
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.elements.shell.mitc4.model import ShellModel


ROOT = Path(__file__).parents[2]
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp04_mitc_vnv.json"


def _plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _digest(value: object) -> str:
    payload = json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mitc3_static_replay(tmp_path: Path) -> dict[str, object]:
    campaign = Mitc3ValidationCampaign(tmp_path / "mitc3", quick=True)
    studies = {
        "patch": campaign._patch(),
        "locking": campaign._locking(),
        "distortion": campaign._distortion(),
        "cook": campaign._cook(),
        "scordelis": campaign._scordelis(),
        "pinched": campaign._pinched(),
        "mixed_mesh": campaign._mixed_mesh(),
        "loads": campaign._loads(),
    }

    model = cantilever_model(4, 1, transverse_force=-12.0)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs).toarray()
    loads = assembler.assemble_loads(model, dofs)
    result = solve_model(model, enforce_policy=False)
    displacement = np.asarray(result.displacements, dtype=float)
    residual = stiffness @ displacement - loads
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    free_residual_ratio = float(np.linalg.norm(residual[free]) / max(np.linalg.norm(loads[free]), 1.0e-30))
    work = float(displacement @ loads)
    energy_identity_error = float(abs(displacement @ stiffness @ displacement - work) / max(abs(work), 1.0e-30))
    reaction_z = sum(float(residual[dofs.index(node, "UZ")]) for node in (0, 1))
    reaction_error = abs(reaction_z - 12.0) / 12.0

    coords = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.2, 1.0, 0.0]])
    element = Mitc3ShellElement(ShellMaterial(E=70.0e9, nu=0.3, t=0.02))
    element_stiffness = element.stiffness(coords)
    rigid = np.zeros(18)
    translation = np.array([0.2, -0.1, 0.4])
    omega = np.array([0.03, -0.02, 0.04])
    for node, position in enumerate(coords):
        rigid[6 * node : 6 * node + 3] = translation + np.cross(omega, position)
        rigid[6 * node + 3 : 6 * node + 6] = omega
    rigid_ratio = float(
        np.linalg.norm(element_stiffness @ rigid)
        / max(np.linalg.norm(element_stiffness) * np.linalg.norm(rigid), 1.0e-30)
    )

    angle = np.deg2rad(37.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated_coords = coords @ rotation.T
    transform = np.zeros((18, 18))
    for node in range(3):
        transform[6 * node : 6 * node + 3, 6 * node : 6 * node + 3] = rotation
        transform[6 * node + 3 : 6 * node + 6, 6 * node + 3 : 6 * node + 6] = rotation
    values = np.linspace(-1.0e-4, 2.0e-4, 18)
    orientation_energy_error = float(
        abs(values @ element_stiffness @ values - (transform @ values) @ element.stiffness(rotated_coords) @ (transform @ values))
        / max(abs(values @ element_stiffness @ values), 1.0e-30)
    )
    cyclic_coords = coords[[1, 2, 0]]
    cyclic_values = values.reshape(3, 6)[[1, 2, 0]].reshape(-1)
    permutation_energy_error = float(
        abs(values @ element_stiffness @ values - cyclic_values @ element.stiffness(cyclic_coords) @ cyclic_values)
        / max(abs(values @ element_stiffness @ values), 1.0e-30)
    )
    permutation_finite = bool(np.all(np.isfinite(element.stiffness(coords[[0, 2, 1]]))))

    thickness_displacements = []
    for thickness in (0.005, 0.01, 0.02):
        thickness_model = cantilever_model(4, 1, thickness=thickness, transverse_force=-12.0)
        thickness_result = solve_model(thickness_model, enforce_policy=False)
        tip_nodes = np.where(np.isclose(thickness_model.nodes[:, 0], 1.0))[0]
        thickness_displacements.append(
            abs(
                float(
                    np.mean(
                        [thickness_result.displacements[thickness_result.dofs.index(int(node), "UZ")] for node in tip_nodes]
                    )
                )
            )
        )

    studies["static_checks"] = {
        "free_residual_ratio": free_residual_ratio,
        "energy_identity_error": energy_identity_error,
        "reaction_relative_error": reaction_error,
        "load_resultant_relative_error": float(assembler.last_load_diagnostics["resultant"][2] + 12.0) / 12.0,
        "rigid_body_residual_ratio": rigid_ratio,
        "orientation_energy_relative_error": orientation_energy_error,
        "permutation_energy_relative_error": permutation_energy_error,
        "permutation_finite": permutation_finite,
        "thickness_displacements": thickness_displacements,
        "thickness_monotonic": thickness_displacements[0] > thickness_displacements[1] > thickness_displacements[2],
    }
    return _plain(studies)


def _mitc4_static_replay() -> dict[str, object]:
    mechanical = [result.__dict__ for result in MechanicalVerifier().run(include_benchmark=True)]
    convergence = {
        name: item.to_dict()
        for name, item in Mitc4StructuralConvergence().run(quick=False).items()
    }
    drilling = Mitc4StructuralConvergence.drilling_sensitivity()
    mesh = MeshFactory.rectangular_plate(4, 1, 1.0, 0.2)
    model = ShellModel(mesh.nodes, mesh.quads, ShellMaterial(E=210.0e9, nu=0.3, t=0.01))
    tip_nodes = np.where(np.isclose(mesh.nodes[:, 0], 1.0))[0]
    for node in tip_nodes:
        model.add_nodal_load(int(node), UZ, -1000.0 / len(tip_nodes))
    root_nodes = np.where(np.isclose(mesh.nodes[:, 0], 0.0))[0]
    for node in root_nodes:
        model.fix_node(int(node))
    stiffness = model.assemble_stiffness().toarray()
    displacement = model.solve()
    fixed = np.array(sorted(model.fixed_dofs), dtype=int)
    free = np.setdiff1d(np.arange(model.ndof), fixed)
    residual = stiffness @ displacement - model.loads
    work = float(displacement @ model.loads)
    reaction_z = sum(float(residual[int(node) * DOF_PER_NODE + UZ]) for node in root_nodes)
    equilibrium = {
        "free_residual_ratio": float(np.linalg.norm(residual[free]) / max(np.linalg.norm(model.loads[free]), 1.0e-30)),
        "energy_identity_error": float(abs(displacement @ stiffness @ displacement - work) / max(abs(work), 1.0e-30)),
        "reaction_relative_error": abs(reaction_z - 1000.0) / 1000.0,
    }
    return _plain({"mechanical": mechanical, "convergence": convergence, "drilling": drilling, "equilibrium": equilibrium})


def _mitc4_modal_replay() -> dict[str, object]:
    return _plain(Mitc4ModalCantileverStudy(meshes=((4, 1), (8, 2), (16, 4))).run())


def _mitc4_newmark_replay() -> dict[str, object]:
    return _plain(Mitc4NewmarkFreeVibrationStudy(steps_per_period=(20, 40, 80), periods=2).run())


def _mitc4_harmonic_replay() -> dict[str, object]:
    return _plain(
        Mitc4HarmonicModalStudy(
            frequency_ratios=(0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0),
        ).run()
    )


def test_wp04_contract_classifies_unclosed_mitc3_dynamic_routes() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    for key in ("MITC3_MODAL", "MITC3_NEWMARK", "MITC3_HARMONIC"):
        case = contract["cases"][key]
        assert case["decision"] == "EXPERIMENTAL"
        assert case["external_correlation"] == "MISSING_EXECUTABLE_ARTIFACT"


def test_wp04_mitc3_static_replays_and_frozen_gates(tmp_path: Path) -> None:
    first = _mitc3_static_replay(tmp_path / "first")
    second = _mitc3_static_replay(tmp_path / "second")
    assert _digest(first) == _digest(second)
    assert first["patch"]["status"] == "PASS"
    assert first["locking"]["status"] == "PASS"
    assert first["mixed_mesh"]["status"] == "PASS"
    assert first["loads"]["status"] == "PASS"
    checks = first["static_checks"]
    assert checks["free_residual_ratio"] <= 1.0e-10
    assert checks["energy_identity_error"] <= 1.0e-10
    assert np.isfinite(checks["reaction_relative_error"])
    assert abs(checks["load_resultant_relative_error"]) <= 1.0e-14
    assert checks["rigid_body_residual_ratio"] <= 2.0e-12
    assert checks["orientation_energy_relative_error"] <= 2.0e-12
    assert checks["permutation_finite"]
    assert checks["thickness_monotonic"]


def test_wp04_mitc4_static_replays_and_frozen_gates() -> None:
    first = _mitc4_static_replay()
    second = _mitc4_static_replay()
    assert _digest(first) == _digest(second)
    assert all(item["passed"] for item in first["mechanical"])
    assert all(item["status"] == "PASS" for item in first["convergence"].values())
    assert first["drilling"]["status"] == "PASS"
    assert first["drilling"]["plateau_relative_change"] <= 0.01
    assert first["equilibrium"]["free_residual_ratio"] <= 1.0e-10
    assert first["equilibrium"]["energy_identity_error"] <= 1.0e-10
    assert first["equilibrium"]["reaction_relative_error"] <= 1.0e-10


def test_wp04_mitc4_modal_replays_and_preserves_failed_frozen_gate() -> None:
    first = _mitc4_modal_replay()
    second = _mitc4_modal_replay()
    assert _digest(first) == _digest(second)
    assert first["status"] == "PASS"
    assert all(first["checks"].values())
    assert first["points"][-1]["relative_frequency_error"] <= 0.02
    assert first["points"][-1]["mode_assurance_criterion"] >= 0.999
    assert first["points"][-1]["relative_residual"] > 1.0e-8


def test_wp04_mitc4_newmark_replays_and_frozen_gates() -> None:
    first = _mitc4_newmark_replay()
    second = _mitc4_newmark_replay()
    assert _digest(first) == _digest(second)
    assert first["status"] == "PASS"
    assert first["points"][-1]["normalized_rms_error"] <= 0.003
    assert first["points"][-1]["period_return_error"] <= 0.02
    assert first["points"][-1]["maximum_relative_energy_drift"] <= 1.0e-8
    assert min(first["observed_orders"]) >= 1.9
    assert max(point["maximum_dynamic_residual_norm"] for point in first["points"]) <= 1.0e-7


def test_wp04_mitc4_harmonic_replays_and_frozen_gates() -> None:
    first = _mitc4_harmonic_replay()
    second = _mitc4_harmonic_replay()
    assert _digest(first) == _digest(second)
    assert first["status"] == "PASS"
    assert first["maximum_relative_error"] <= 1.0e-6
    assert first["zero_hz_static_relative_error"] <= 1.0e-9
    assert first["maximum_residual_norm"] <= 1.0e-7
    assert 0.95 <= first["peak"]["frequency_ratio"] <= 1.05
    assert first["checks"]["phase_before_resonance"]
    assert first["checks"]["phase_after_resonance"]
