"""WP03 analytic V&V for bounded BEAM2 and DISCRETE routes."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from qf_solver import FiniteElementModel, check_mesh, solve_model
from solveur.core.assembler import GlobalAssembler
from solveur.elements.beam.beam2 import Beam2Element
from solveur.materials.beam import BeamSectionMaterial


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification/0_2_8/wp03_beam2_discrete_vnv.json"

E = 210.0e9
NU = 0.3
G = E / (2.0 * (1.0 + NU))
A = 0.01
IY = 2.0e-6
IZ = 3.0e-6
J = 5.0e-6
RHO = 7800.0
LENGTH = 2.0
KAPPA = 5.0 / 6.0


def _load_evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _beam_model(
    elements: int,
    *,
    analysis: str | dict[str, object] = "linear_static",
    load_dof: str | None = None,
    load_value: float = 0.0,
) -> FiniteElementModel:
    nodes = [[LENGTH * index / elements, 0.0, 0.0] for index in range(elements + 1)]
    element_data = [{"type": "BEAM2", "nodes": [index, index + 1], "material": "beam"} for index in range(elements)]
    loads = [] if load_dof is None else [{"node": elements, "dof": load_dof, "value": load_value}]
    return FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=nodes,
        elements=element_data,
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": E,
                "nu": NU,
                "A": A,
                "Iy": IY,
                "Iz": IZ,
                "J": J,
                "density": RHO,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        loads=loads,
    )


def _beam_static_run() -> dict[str, Any]:
    cases = {
        "axial": ("UX", 2000.0, lambda force: force * LENGTH / (E * A)),
        "flexion_y": (
            "UY",
            1000.0,
            lambda force: force * LENGTH**3 / (3.0 * E * IZ) + force * LENGTH / (KAPPA * G * A),
        ),
        "flexion_z": (
            "UZ",
            1000.0,
            lambda force: force * LENGTH**3 / (3.0 * E * IY) + force * LENGTH / (KAPPA * G * A),
        ),
        "torsion": ("RX", 500.0, lambda torque: torque * LENGTH / (G * J)),
    }
    displacement_errors: list[float] = []
    reaction_errors: list[float] = []
    energy_errors: list[float] = []
    residuals: list[float] = []
    refinements: list[dict[str, float]] = []
    for name, (dof, load, exact) in cases.items():
        for elements in (1, 2, 4):
            model = _beam_model(elements, load_dof=dof, load_value=load)
            assert check_mesh(model).status == "PASS"
            result = solve_model(model, enforce_policy=False)
            index = result.dofs.index(elements, dof)
            observed = float(result.displacements[index])
            expected = float(exact(load))
            relative_error = abs(observed - expected) / abs(expected)
            displacement_errors.append(relative_error)
            assembler = GlobalAssembler()
            stiffness = assembler.assemble_stiffness(model, result.dofs).toarray()
            loads_vector = assembler.assemble_loads(model, result.dofs)
            equilibrium = stiffness @ result.displacements - loads_vector
            scale = max(float(np.linalg.norm(loads_vector, ord=np.inf)), 1.0)
            expected_reactions = np.zeros(result.dofs.ndof)
            expected_reactions[result.dofs.index(0, dof)] = -load
            if dof == "UY":
                expected_reactions[result.dofs.index(0, "RZ")] = -load * LENGTH
            elif dof == "UZ":
                expected_reactions[result.dofs.index(0, "RY")] = load * LENGTH
            fixed = set(GlobalAssembler().fixed_indices(model, result.dofs))
            free_error = max(
                (abs(float(equilibrium[index])) / scale for index in range(result.dofs.ndof) if index not in fixed),
                default=0.0,
            )
            reaction_error = max(
                (abs(float(equilibrium[index] - expected_reactions[index])) / scale for index in fixed),
                default=0.0,
            )
            reaction_errors.append(max(free_error, reaction_error))
            internal_energy = 0.5 * float(result.displacements @ stiffness @ result.displacements)
            external_work = float(result.displacements @ loads_vector)
            energy_errors.append(abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0))
            residuals.append(float(result.solver["relative_residual_norm"]))
            refinements.append(
                {
                    "case": name,
                    "elements": elements,
                    "relative_displacement_error": relative_error,
                }
            )

    material = BeamSectionMaterial(E=E, G=G, A=A, Iy=IY, Iz=IZ, J=J, density=RHO)
    element_stiffness = Beam2Element(material).stiffness(np.array([[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0]]))
    eigenvalues = np.linalg.eigvalsh(element_stiffness)
    nullity_tolerance = np.max(np.abs(eigenvalues)) * 1.0e-10
    rigid_body_nullity = int(np.count_nonzero(np.abs(eigenvalues) <= nullity_tolerance))

    return {
        "max_relative_displacement_error": max(displacement_errors),
        "max_reaction_equilibrium_error": max(reaction_errors),
        "max_energy_identity_error": max(energy_errors),
        "max_relative_solver_residual": max(residuals),
        "rigid_body_stiffness_nullity": rigid_body_nullity,
        "refinement": refinements,
    }


def _beam_modal_run() -> dict[str, Any]:
    reference = sorted(
        [
            (1.875104068711961**2) / (2.0 * math.pi * LENGTH**2) * math.sqrt(E * IZ / (RHO * A)),
            (1.875104068711961**2) / (2.0 * math.pi * LENGTH**2) * math.sqrt(E * IY / (RHO * A)),
        ]
    )
    frequency_errors: list[float] = []
    residuals: list[float] = []
    orthogonality_errors: list[float] = []
    refinements: list[dict[str, Any]] = []
    for elements in (1, 2, 4):
        model = _beam_model(elements, analysis={"type": "modal", "method": "eigh", "modes": 2})
        result = solve_model(model, enforce_policy=False)
        observed = [float(value) for value in result.frequencies_hz[:2]]
        errors = [abs(value - ref) / ref for value, ref in zip(observed, reference, strict=True)]
        frequency_errors.extend(errors)
        residuals.append(float(result.solver["max_relative_residual"]))
        orthogonality_errors.append(float(result.solver["mass_orthogonality_error"]))
        refinements.append(
            {
                "elements": elements,
                "frequencies_hz": observed,
                "relative_errors": errors,
            }
        )
    return {
        "analytic_reference_frequencies_hz": reference,
        "max_relative_frequency_error": max(frequency_errors),
        "max_relative_eigen_residual": max(residuals),
        "max_mass_orthogonality_error": max(orthogonality_errors),
        "refinement": refinements,
        "positive_frequency_count_final_mesh": len(refinements[-1]["frequencies_hz"]),
    }


def _discrete_static_model(dof: str, force: float) -> FiniteElementModel:
    stiffness = {"UX": 1000.0, "UY": 4000.0, "UZ": 9000.0}
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
        springs=[{"node_a": 0, "dofs": ["UX", "UY", "UZ"], "stiffness": [stiffness["UX"], stiffness["UY"], stiffness["UZ"]]}],
        concentrated_masses=[{"node": 0, "mass": 10.0}],
        loads=[{"node": 0, "dof": dof, "value": force}],
    )


def _discrete_static_run() -> dict[str, Any]:
    cases = {"UX": 25.0, "UY": -20.0, "UZ": 45.0}
    stiffness = {"UX": 1000.0, "UY": 4000.0, "UZ": 9000.0}
    displacement_errors: list[float] = []
    equilibrium_errors: list[float] = []
    energy_errors: list[float] = []
    residuals: list[float] = []
    observations: dict[str, float] = {}
    for dof, force in cases.items():
        model = _discrete_static_model(dof, force)
        assert check_mesh(model).status in {"PASS", "WARNING"}
        result = solve_model(model, enforce_policy=False)
        index = result.dofs.index(0, dof)
        observed = float(result.displacements[index])
        expected = force / stiffness[dof]
        observations[dof] = observed
        displacement_errors.append(abs(observed - expected) / abs(expected))
        assembler = GlobalAssembler()
        matrix = assembler.assemble_stiffness(model, result.dofs).toarray()
        loads = assembler.assemble_loads(model, result.dofs)
        equilibrium_errors.append(float(np.max(np.abs(matrix @ result.displacements - loads)) / max(abs(force), 1.0)))
        internal_energy = 0.5 * float(result.displacements @ matrix @ result.displacements)
        external_work = float(result.displacements @ loads)
        energy_errors.append(abs(2.0 * internal_energy - external_work) / max(abs(external_work), 1.0))
        residuals.append(float(result.solver["relative_residual_norm"]))

    pair_model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[{"node_a": 0, "node_b": 1, "dofs": ["UX"], "stiffness": 1200.0}],
    )
    pair_dofs = pair_model.dof_manager()
    pair_matrix = GlobalAssembler().assemble_stiffness(pair_model, pair_dofs).toarray()
    rigid = pair_matrix @ np.ones(pair_dofs.ndof)
    extension = pair_matrix @ np.array([0.0, 0.01])
    return {
        "displacements_m": observations,
        "max_relative_displacement_error": max(displacement_errors),
        "max_equilibrium_error": max(equilibrium_errors),
        "max_energy_identity_error": max(energy_errors),
        "max_relative_solver_residual": max(residuals),
        "two_node_rigid_mode_error": float(np.max(np.abs(rigid))),
        "two_node_action_reaction_error": float(abs(extension[0] + extension[1])),
    }


def _discrete_modal_run() -> dict[str, Any]:
    stiffness = np.array([1000.0, 4000.0, 9000.0])
    mass = 10.0
    model = FiniteElementModel.from_raw(
        analysis={"type": "modal", "method": "eigh", "parameters": {"modes": 3}},
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
        springs=[{"node_a": 0, "dofs": ["UX", "UY", "UZ"], "stiffness": stiffness.tolist()}],
        concentrated_masses=[{"node": 0, "mass": mass}],
    )
    assert check_mesh(model).status in {"PASS", "WARNING"}
    result = solve_model(model, enforce_policy=False)
    reference = [float(math.sqrt(value / mass) / (2.0 * math.pi)) for value in stiffness]
    observed = [float(value) for value in result.frequencies_hz[:3]]
    errors = [abs(value - expected) / expected for value, expected in zip(observed, reference, strict=True)]
    return {
        "analytic_reference_frequencies_hz": reference,
        "frequencies_hz": observed,
        "max_relative_frequency_error": max(errors),
        "max_relative_eigen_residual": float(result.solver["max_relative_residual"]),
        "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
        "positive_frequency_count": len(observed),
    }


def test_wp03_machine_evidence_declares_bounded_scope_and_decisions() -> None:
    evidence = _load_evidence()
    matrix = json.loads(
        (ROOT / "qualification/0_2_8/wp03_maturity_matrix.json").read_text(encoding="utf-8")
    )
    assert evidence["baseline_sha"] == "598704c834b4642f7c2a9a1fdc7595895f9e4130"
    assert evidence["status"] == "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING"
    assert set(evidence["cases"]) == {"BEAM2_STATIC", "BEAM2_MODAL", "DISCRETE_STATIC", "DISCRETE_MODAL"}
    assert set(evidence["routes"]) == {"BEAM2_NEWMARK", "BEAM2_HARMONIC", "DISCRETE_NEWMARK", "DISCRETE_HARMONIC"}
    assert all(case["decision"] == "QUALIFIED_BOUNDED" for case in evidence["cases"].values())
    assert all(route["decision"] == "EXPERIMENTAL" for route in evidence["routes"].values())
    assert all(case["owner_gate"] == "PENDING" for case in evidence["cases"].values())
    assert all(case["replay_count"] >= 2 for case in evidence["cases"].values())
    assert matrix["parent_baseline"] == "qualification/0_2_8/wp01_maturity_matrix.json"
    assert matrix["summary"] == {
        "QUALIFIED_BOUNDED": 4,
        "EXPERIMENTAL": 4,
        "NOT_QUALIFIED": 0,
        "public_maturity_relabels_applied": 0,
    }
    assert len(matrix["decisions"]) == 8


@pytest.mark.parametrize(
    ("case_name", "runner"),
    [
        ("BEAM2_STATIC", _beam_static_run),
        ("BEAM2_MODAL", _beam_modal_run),
        ("DISCRETE_STATIC", _discrete_static_run),
        ("DISCRETE_MODAL", _discrete_modal_run),
    ],
)
def test_wp03_analytic_cases_pass_frozen_tolerances_and_replay(case_name: str, runner) -> None:
    evidence = _load_evidence()
    case = evidence["cases"][case_name]
    first = runner()
    second = runner()
    tolerances = case["tolerances"]
    assert _digest(first) == _digest(second)
    assert first[case["primary_metric"]] <= tolerances[case["primary_metric"]]
    assert first[case["invariant_metric"]] <= tolerances[case["invariant_metric"]]
    assert first[case["residual_metric"]] <= tolerances[case["residual_metric"]]
    expected = case["observed"]
    for key, value in expected.items():
        assert first[key] == pytest.approx(value, rel=1.0e-12, abs=1.0e-14), (case_name, key)
    assert case["replay_digests"][0] == case["replay_digests"][1]
    assert _digest(first) == _digest(second)
    for metric in case.get("additional_metrics", {}):
        assert first[metric] <= tolerances[metric]
    if case_name == "BEAM2_STATIC":
        assert first["rigid_body_stiffness_nullity"] == 6
    if case_name == "BEAM2_MODAL":
        assert first["positive_frequency_count_final_mesh"] == 2
    if case_name == "DISCRETE_STATIC":
        assert first["two_node_rigid_mode_error"] <= tolerances["two_node_rigid_mode_error"]
        assert first["two_node_action_reaction_error"] <= tolerances["two_node_action_reaction_error"]
    if case_name == "DISCRETE_MODAL":
        assert first["positive_frequency_count"] == 3


def test_wp03_external_oracle_is_not_claimed() -> None:
    evidence = _load_evidence()
    assert all(case["oracle_type"] == "ANALYTICAL" for case in evidence["cases"].values())
    assert all(route["decision"] == "EXPERIMENTAL" for route in evidence["routes"].values())
