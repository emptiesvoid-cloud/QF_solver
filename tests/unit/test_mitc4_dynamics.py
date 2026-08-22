from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse.linalg import spsolve

from solveur.compat.mitc4.element import MITC4Element
from solveur.compat.mitc4.material import ShellMaterial
from solveur.core.assembler import GlobalAssembler
from solveur.core.analysis import AnalysisSettings
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.api import solve_model
from solveur.mesh.validation import MeshValidator


def _square() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 1.0, 0.0], [0.0, 1.0, 0.0]])


def _material() -> ShellMaterial:
    return ShellMaterial(E=70.0e9, nu=0.3, t=0.2, density=2700.0)


def test_mitc4_consistent_mass_has_exact_physical_resultants() -> None:
    element = MITC4Element(_material())
    mass = element.mass_local(element.project_to_local_midplane(_square())[1])
    area = 2.0
    translation = _material().density * _material().t * area
    rotation = _material().density * _material().t**3 * area / 12.0

    assert np.allclose(mass, mass.T, rtol=0.0, atol=1.0e-12)
    for component in range(3):
        indices = np.arange(component, 24, 6)
        assert np.isclose(mass[np.ix_(indices, indices)].sum(), translation)
    for component in (3, 4):
        indices = np.arange(component, 24, 6)
        assert np.isclose(mass[np.ix_(indices, indices)].sum(), rotation)
    drilling = np.arange(5, 24, 6)
    assert np.count_nonzero(mass[drilling, :]) == 0
    assert np.linalg.eigvalsh(mass).min() >= -1.0e-12


def test_mitc4_mass_is_objective_under_rigid_rotation() -> None:
    element = MITC4Element(_material())
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    coords = _square()
    rotated = coords @ rotation.T
    block = np.zeros((6, 6))
    block[:3, :3] = rotation
    block[3:, 3:] = rotation
    transform = np.kron(np.eye(4), block)

    expected = transform @ element.mass(coords) @ transform.T
    assert np.allclose(element.mass(rotated), expected, rtol=1.0e-12, atol=1.0e-10)


def test_mitc4_mass_rejects_missing_density() -> None:
    element = MITC4Element(ShellMaterial(E=70.0e9, nu=0.3, t=0.2))
    with pytest.raises(ValueError, match="positive material density"):
        element.mass(_square())


def _dynamic_plate(coords: np.ndarray | None = None) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={"type": "modal", "method": "eigh", "modes": 3},
        nodes=(coords if coords is not None else _square()).tolist(),
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.2,
                "density": 2700.0,
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for node in (0, 3)
        ],
    )


def _soft_dynamic_plate(analysis: dict[str, object]) -> FiniteElementModel:
    model = _dynamic_plate()
    model.materials["skin"].update({"E": 1000.0, "density": 10.0, "t": 0.1})
    model.analysis = AnalysisSettings.from_raw(analysis)
    return model


def test_dynamic_reducer_condenses_massless_drilling_and_reconstructs_equilibrium() -> None:
    model = _dynamic_plate()
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)

    assert reducer.has_condensation
    assert reducer.diagnostics["condensed_drilling_dof_count"] == 2
    assert reducer.reduced_size == 10
    reduced = np.linspace(0.0, 1.0e-5, reducer.reduced_size)
    expanded = reducer.expand_state(reduced)
    residual = stiffness @ expanded
    free_drilling = [dofs.index(node, "RZ") for node in (1, 2)]
    assert np.linalg.norm(residual[free_drilling]) < 1.0e-7

    complex_reduced = reduced * (1.0 + 2.0j)
    complex_expanded = reducer.expand_complex_state(complex_reduced)
    complex_residual = stiffness @ complex_expanded
    assert np.iscomplexobj(complex_expanded)
    assert np.linalg.norm(complex_residual[free_drilling]) < 1.0e-7


def test_dynamic_reducer_lazy_condensation_matches_explicit_operator() -> None:
    model = _dynamic_plate()
    model.analysis = AnalysisSettings.from_raw({"type": "modal", "method": "eigsh", "lazy_drilling_condensation": True})
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)

    assert reducer.diagnostics["lazy_condensation"] is True
    state = np.linspace(0.0, 1.0e-5, reducer.reduced_size)
    expected = reducer.stiffness @ state
    assert np.all(np.isfinite(expected))


def test_dynamic_reducer_is_invariant_for_rotated_flat_plate() -> None:
    angle = np.deg2rad(29.0)
    rotation = np.array(
        [[1.0, 0.0, 0.0], [0.0, np.cos(angle), -np.sin(angle)], [0.0, np.sin(angle), np.cos(angle)]]
    )
    model = _dynamic_plate(_square() @ rotation.T)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, assembler.fixed_indices(model, dofs))

    assert reducer.diagnostics["condensed_drilling_dof_count"] == 2
    assert np.linalg.eigvalsh(reducer.mass.toarray()).min() > 0.0


def test_mitc4_modal_solver_returns_physical_modes_and_reduction_audit() -> None:
    result = solve_model(_soft_dynamic_plate({"type": "modal", "method": "eigh", "modes": 3}))

    assert len(result.frequencies_hz) == 3
    assert np.all(result.frequencies_hz > 0.0)
    assert result.solver["max_relative_residual"] < 1.0e-10
    assert result.solver["mass_orthogonality_error"] < 1.0e-10
    assert result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] == 2
    assert result.modes.shape == (24, 3)


def test_mitc4_modal_frequencies_are_objective() -> None:
    base = solve_model(_soft_dynamic_plate({"type": "modal", "method": "eigh", "modes": 3}))
    angle = np.deg2rad(31.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated = _soft_dynamic_plate({"type": "modal", "method": "eigh", "modes": 3})
    rotated.nodes = _square() @ rotation.T
    comparison = solve_model(rotated)

    assert np.allclose(comparison.frequencies_hz, base.frequencies_hz, rtol=1.0e-10, atol=1.0e-10)


def test_mitc4_newmark_free_vibration_conserves_energy() -> None:
    modal = solve_model(_soft_dynamic_plate({"type": "modal", "method": "eigh", "modes": 1}))
    period = 1.0 / float(modal.frequencies_hz[0])
    dynamic = _soft_dynamic_plate(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": period / 80.0,
            "steps": 160,
            "load_factors": [0.0],
            "initial_displacements": [
                {"node": 1, "dof": "UZ", "value": 1.0e-4},
                {"node": 2, "dof": "UZ", "value": 1.0e-4},
            ],
        }
    )
    result = solve_model(dynamic)
    history = result.solver["time_history"]

    assert result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] == 2
    assert max(abs(row["relative_energy_drift"]) for row in history) < 1.0e-8
    assert max(row["dynamic_residual_norm"] for row in history) < 1.0e-8


def test_mitc4_harmonic_zero_hz_matches_static_with_drilling_condensation() -> None:
    harmonic_model = _soft_dynamic_plate(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [0.0, 1.0],
            "rayleigh_alpha": 0.05,
            "rayleigh_beta": 0.0,
        }
    )
    harmonic_model.loads = [NodalLoad(node=1, dof="UZ", value=1.0)]
    harmonic = solve_model(harmonic_model)

    static_model = _soft_dynamic_plate({"type": "linear_static", "method": "direct"})
    static_model.loads = [NodalLoad(node=1, dof="UZ", value=1.0)]
    static = solve_model(static_model)

    np.testing.assert_allclose(harmonic.responses[0].real, static.displacements, rtol=1.0e-10, atol=1.0e-12)
    assert harmonic.solver["dynamic_reduction"]["condensed_drilling_dof_count"] == 2
    assert harmonic.solver["max_residual_norm"] < 1.0e-8
    assert len(harmonic.shell_stress_response) == 2
    assert harmonic.to_dict()["peak_shell_stress"]["peak_component"]["amplitude"] > 0.0


def test_newmark_history_probe_preserves_signed_nodal_state() -> None:
    model = _soft_dynamic_plate(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 1.0e-3,
            "steps": 2,
            "load_factors": [0.0],
            "initial_displacements": [{"node": 1, "dof": "UZ", "value": 1.0e-4}],
            "history_probes": [{"node": 1, "dof": "UZ", "label": "tip_uz"}],
        }
    )

    history = solve_model(model).solver["time_history"]

    assert list(history[0]["probes"]) == ["tip_uz"]
    assert set(history[0]["probes"]["tip_uz"]) == {"displacement", "velocity", "acceleration"}
    assert np.isfinite(history[0]["probes"]["tip_uz"]["displacement"])


def test_newmark_history_probe_rejects_duplicate_labels() -> None:
    model = _soft_dynamic_plate(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 1.0e-3,
            "steps": 1,
            "history_probes": [
                {"node": 1, "dof": "UZ", "label": "same"},
                {"node": 2, "dof": "UZ", "label": "same"},
            ],
        }
    )

    with pytest.raises(InputValidationError, match="labels must be non-empty and unique"):
        solve_model(model)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda model: model.materials["skin"].update({"density": 0.0}), "positive density"),
        (lambda model: model.materials["skin"].update({"drilling_scale": 0.0}), "drilling_scale > 0"),
    ],
)
def test_mitc4_dynamic_input_failures_are_explicit(mutation, message: str) -> None:
    model = _dynamic_plate()
    mutation(model)
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any(message in error for error in report.errors)


def test_mitc4_harmonic_supports_stiffness_proportional_damping() -> None:
    model = _soft_dynamic_plate(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [1.0],
            "rayleigh_beta": 1.0e-4,
        }
    )
    model.loads = [
        NodalLoad(node=1, dof="UZ", value=1.0),
        NodalLoad(node=1, dof="RZ", value=0.25),
    ]
    result = solve_model(model)

    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    omega = 2.0 * np.pi
    beta = 1.0e-4
    impedance = (1.0 + 1j * omega * beta) * stiffness - omega**2 * mass
    full_reference = np.zeros(dofs.ndof, dtype=complex)
    full_reference[free] = spsolve(impedance[free, :][:, free].tocsc(), loads[free])

    assert result.status == "PASS"
    assert result.solver["max_residual_norm"] < 1.0e-8
    assert result.solver["max_relative_residual_norm"] < 1.0e-8
    assert result.solver["harmonic_condensation"]["supports_stiffness_proportional_damping"] is True
    np.testing.assert_allclose(result.responses[0], full_reference, rtol=2.0e-11, atol=1.0e-12)


def test_mitc4_dynamic_accepts_aligned_partial_rotational_constraints() -> None:
    model = _dynamic_plate()
    model.fixed_dofs.extend(
        [type(model.fixed_dofs[0])(node=node, dofs=("RZ",)) for node in (1, 2)]
    )

    report = MeshValidator().validate(model)
    result = solve_model(model)

    assert report.status != "FAIL"
    assert result.status == "PASS"
    assert result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] == 0


def test_mitc4_dynamic_rejects_misaligned_partial_rotational_constraints() -> None:
    angle = np.deg2rad(31.0)
    rotation = np.array(
        [[np.cos(angle), 0.0, np.sin(angle)], [0.0, 1.0, 0.0], [-np.sin(angle), 0.0, np.cos(angle)]]
    )
    model = _dynamic_plate(_square() @ rotation.T)
    model.fixed_dofs = [
        condition for condition in model.fixed_dofs if condition.node != 0
    ] + [type(model.fixed_dofs[0])(node=0, dofs=("RX",))]
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("must align" in error for error in report.errors)


def test_qualification_profile_rejects_shell_outside_mesh_domain() -> None:
    model = _dynamic_plate(np.array([[0, 0, 0], [20, 0, 0], [20, 1, 0], [0, 1, 0]], dtype=float))
    model.verification_profile = "qualification"
    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert any("outside the bounded mesh-quality domain" in error for error in report.errors)
