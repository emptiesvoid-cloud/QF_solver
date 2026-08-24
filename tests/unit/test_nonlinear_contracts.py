import numpy as np

from solveur.core.material_state import MaterialStateSession
from solveur.core.nonlinear_contracts import ConstitutiveResponse, evaluate_constitutive
from solveur.core.nonlinear_controls import NonlinearSolverOptions, NonlinearStep
from solveur.materials.solid import SolidMaterial, VonMisesElastoplasticMaterial


def test_linear_material_uses_common_constitutive_response() -> None:
    material = SolidMaterial(E=1000.0, nu=0.25)
    response = evaluate_constitutive(material, np.array([1.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0]))

    assert isinstance(response, ConstitutiveResponse)
    assert response.diagnostics["stateful"] is False
    assert response.diagnostics["elastic"] is True
    assert response.trial_state == {}


def test_j2_evaluation_does_not_mutate_committed_state() -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    committed = material.initial_state()
    response = material.evaluate(np.array([8.0e-2, 0.005, -0.002, 0.01, -0.004, 0.006]), committed)

    assert response.diagnostics["stateful"] is True
    assert response.trial_state["equivalent_plastic_strain"] > 0.0
    assert committed == material.initial_state()


def test_j2_algorithmic_tangent_matches_central_finite_difference() -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    strain = np.array([8.0e-2, 0.005, -0.002, 0.01, -0.004, 0.006])
    committed = material.initial_state()
    response = material.evaluate(strain, committed)
    step = 1.0e-7
    numerical = np.column_stack(
        [
            (
                material.evaluate(strain + step * np.eye(6)[column], committed).stress
                - material.evaluate(strain - step * np.eye(6)[column], committed).stress
            )
            / (2.0 * step)
            for column in range(6)
        ]
    )

    relative_error = np.linalg.norm(response.tangent - numerical) / np.linalg.norm(numerical)
    assert relative_error < 1.0e-7


def test_material_state_session_commit_and_rollback_are_transactional() -> None:
    committed = {0: [{"equivalent_plastic_strain": 0.0}]}
    session = MaterialStateSession(committed)
    trial = session.begin_trial()
    trial[0][0]["equivalent_plastic_strain"] = 0.25
    session.rollback()
    assert committed[0][0]["equivalent_plastic_strain"] == 0.0

    trial = session.begin_trial()
    trial[0][0]["equivalent_plastic_strain"] = 0.5
    session.commit()
    assert committed[0][0]["equivalent_plastic_strain"] == 0.5


def test_nonlinear_solver_options_preserve_legacy_defaults_and_normalize_method() -> None:
    options = NonlinearSolverOptions.from_parameters({"linear_method": "CG", "max_iterations": 0})

    assert options.max_iterations == 1
    assert options.linear_method == "cg"
    assert options.tolerance == 1.0e-8


def test_nonlinear_step_serializes_initial_residual_and_failure_reason() -> None:
    record = NonlinearStep(
        step=2,
        load_factor=0.5,
        iterations=3,
        residual_norm=1.0e-9,
        relative_residual=1.0e-10,
        residual_initial=2.0,
        failure_reason="MAX_ITERATIONS",
    ).to_dict()

    assert record["residual_initial"] == 2.0
    assert record["failure_reason"] == "MAX_ITERATIONS"
