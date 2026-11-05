from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.linalg import eigh
from scipy.sparse import csr_matrix, diags, eye, lil_matrix

from solveur.core.analyses import modal as modal_module
from solveur.core.analyses.excitation_channels import (
    ComplexPhasor,
    ExcitationChannel,
    ExcitationChannelSet,
    HarmonicAmplitude,
    SpatialDofWeight,
)
from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.analyses.modal_basis import (
    ModalBasis,
    _mass_metric_subspace_equivalent,
    _mass_normalize_and_handle_degenerate_subspaces,
    _positive_definite_screen,
    _relative_sparse_symmetry_error,
)
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.errors import InputValidationError, ModalResidualValidationError
from solveur.core.model import FiniteElementModel
from solveur.elements.discrete import ConcentratedMass


# Declared source revision for these local modal fixtures; the runner separately
# verifies the exact corrective worktree HEAD and raw source fingerprints.
_SOURCE_SHA = "3cc36fe49d4f4943038b083297bf660f897e7b3e"


def _model(family: str = "TET4", *, analysis_type: str = "transient_dynamic") -> FiniteElementModel:
    if family == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        connectivity = list(range(4))
        fixed_nodes = [0, 2, 3]
    elif family == "TET10":
        nodes = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ]
        connectivity = list(range(10))
        fixed_nodes = [0, 2, 3, 6, 7, 9]
    elif family in {"HEX8", "HEX20"}:
        corners = np.asarray(
            [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
            dtype=float,
        )
        if family == "HEX8":
            nodes = corners.tolist()
            connectivity = list(range(8))
            fixed_nodes = [0, 3, 4, 7]
        else:
            edges = (
                (0, 1),
                (0, 3),
                (0, 4),
                (1, 2),
                (1, 5),
                (2, 3),
                (2, 6),
                (3, 7),
                (4, 5),
                (4, 7),
                (5, 6),
                (6, 7),
            )
            nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2 for a, b in edges]]).tolist()
            connectivity = list(range(20))
            fixed_nodes = [0, 3, 4, 7, 9, 10, 15, 17]
    elif family == "BEAM2":
        nodes = [[0, 0, 0], [1, 0, 0]]
        connectivity = [0, 1]
        fixed_nodes = [0]
    else:
        raise AssertionError(family)

    beam = family == "BEAM2"
    material = (
        {
            "type": "beam_isotropic",
            "E": 210.0e9,
            "nu": 0.3,
            "A": 0.01,
            "Iy": 1.0e-5,
            "Iz": 1.0e-5,
            "J": 2.0e-5,
            "density": 7800.0,
        }
        if beam
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    fixed_dofs = [
        {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"] if beam else ["UX", "UY", "UZ"]}
        for node in fixed_nodes
    ]
    return FiniteElementModel.from_raw(
        analysis={
            "type": analysis_type,
            "method": "newmark" if analysis_type == "transient_dynamic" else "eigsh",
            "time_step": 0.01,
            "steps": 2,
            "modes": 1,
        },
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "mat"}],
        materials={"mat": material},
        fixed_dofs=fixed_dofs,
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
    )


def _prepared(family: str = "TET4", *, analysis_type: str = "transient_dynamic") -> PreparedDynamicSystem:
    return PreparedDynamicSystem.prepare(_model(family, analysis_type=analysis_type), source_sha=_SOURCE_SHA)


def _matrix_basis(k: np.ndarray, m: np.ndarray, modes: int, *, method: str = "dense") -> ModalBasis:
    return ModalBasis._from_operators(
        csr_matrix(k),
        csr_matrix(m),
        operator_identity="analytical-operator-v1",
        dof_signature=(),
        requested_modes=modes,
        method=method,
        dense_limit=max(k.shape[0], 256),
    )


def test_analytical_coupled_two_dof_eigenproblem_and_projected_operators() -> None:
    mass = np.asarray([[2.0, 0.25], [0.25, 1.5]])
    stiffness = np.asarray([[20.0, -2.0], [-2.0, 8.0]])
    expected_values = eigh(stiffness, mass, eigvals_only=True)
    basis = _matrix_basis(stiffness, mass, 2)

    np.testing.assert_allclose(basis.eigenvalues, expected_values, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(basis.projected_mass, np.eye(2), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(basis.projected_stiffness, np.diag(expected_values), rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(basis.modes.T @ mass @ basis.modes, np.eye(2), atol=1e-12)
    reconstructed = mass @ basis.modes @ basis.projected_stiffness @ basis.modes.T @ mass
    np.testing.assert_allclose(reconstructed, stiffness, rtol=1e-11, atol=1e-11)
    assert basis.is_full_basis
    assert basis.maturity == "EXPERIMENTAL"
    assert basis.numerical_status == "PASS"
    assert basis.result_availability["eigenvalues"]["status"] == "AVAILABLE"
    assert basis.result_availability["full_mode_shapes"]["status"] == "NOT_COMPUTED"
    assert basis.result_availability["physical_reactions"]["status"] == "NOT_COMPUTED"


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_prepared_modal_basis_supports_each_wp00_family(family: str) -> None:
    prepared = _prepared(family)
    basis = ModalBasis.from_prepared(
        prepared,
        mode_count=prepared.reduced_size,
        method="dense",
        dense_limit=128,
    )

    assert basis.system_size == prepared.reduced_size
    assert basis.mode_count == prepared.reduced_size
    assert basis.is_full_basis
    assert basis.operator_identity == prepared.operator_identity
    assert basis.diagnostics["spectral_domain"] == "NUMERICALLY_SCREENED_SYMMETRIC_POSITIVE_DEFINITE"
    assert basis.diagnostics["maximum_relative_modal_residual"] <= 1e-8
    validation = basis.diagnostics["modal_residual_validation"]
    assert validation["status"] == "PASS_CERTIFIED"
    assert len(validation["checks"]) == basis.mode_count
    assert all(check["status"] == "PASS_CERTIFIED" for check in validation["checks"])
    assert basis.diagnostics["mass_orthogonality_frobenius_error"] <= 1e-8


def test_sparse_spd_screen_and_sparse_extraction_do_not_materialize_full_spectrum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    size = 270
    mass = eye(size, format="csr")
    stiffness = diags(np.linspace(1.0, 20.0, size), format="csr")
    screen = _positive_definite_screen(stiffness, "stiffness")

    requested_eigenpairs: list[int] = []
    scipy_eigsh = modal_module.eigsh

    def record_sparse_request(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        requested_eigenpairs.append(int(kwargs["k"]))
        return scipy_eigsh(*args, **kwargs)

    monkeypatch.setattr(modal_module, "eigsh", record_sparse_request)
    values, vectors, backend = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        3,
        "eigsh",
        dense_limit=64,
        which="SA",
    )

    assert backend == "eigsh"
    assert "SPARSE_SMALLEST_ALGEBRAIC" in str(screen["method"])
    np.testing.assert_allclose(values, [1.0, 1.0 + 19.0 / 269.0, 1.0 + 38.0 / 269.0], rtol=1e-8)
    assert vectors.shape == (size, 3)
    assert requested_eigenpairs == [3]
    assert requested_eigenpairs[0] < size


def test_sparse_modal_basis_refuses_270_dof_certificate_and_preserves_candidate() -> None:
    size = 270
    mass = eye(size, format="csr")
    stiffness = diags(np.linspace(1.0, 20.0, size), format="csr")
    screen = _positive_definite_screen(stiffness, "stiffness")

    with pytest.raises(ModalResidualValidationError) as caught:
        ModalBasis._from_operators(
            stiffness,
            mass,
            operator_identity="sparse-diagonal-270-v1",
            dof_signature=(),
            requested_modes=2,
            method="eigsh",
            dense_limit=64,
            spectral_screens={"stiffness": screen},
        )

    error = caught.value
    assert error.validation_status == "INCONCLUSIVE"
    assert error.diagnostics["reason"] == "dimension_budget"
    assert not isinstance(error.computed_result, ModalBasis)
    assert isinstance(error.computed_result, dict)
    candidate = error.computed_result
    assert candidate["validation"]["status"] == "INCONCLUSIVE"
    assert candidate["validation"]["reason"] == "dimension_budget"
    assert candidate["eigenvalues_rad2_s2"].shape == (3,)
    assert candidate["modes"].shape == (size, 3)


def test_132_dof_six_modes_are_computed_only_under_explicit_inconclusive_policy() -> None:
    size = 132
    mass = eye(size, format="csr")
    stiffness = diags(np.linspace(1.0, 40.0, size), format="csr")

    with pytest.raises(ModalResidualValidationError) as strict_error:
        ModalBasis._from_operators(
            stiffness,
            mass,
            operator_identity="diagonal-132-strict-v1",
            dof_signature=(),
            requested_modes=6,
            method="eigsh",
            dense_limit=64,
        )
    assert strict_error.value.validation_status == "INCONCLUSIVE"
    assert strict_error.value.diagnostics["reason"] == "dimension_budget"
    assert strict_error.value.computed_result["modes"].shape == (size, 7)

    basis = ModalBasis._from_operators(
        stiffness,
        mass,
        operator_identity="diagonal-132-compat-v1",
        dof_signature=(),
        requested_modes=6,
        method="eigsh",
        dense_limit=64,
        validation_policy="allow_inconclusive",
    )
    assert basis.mode_count == 6
    assert basis.calculation_status == "COMPUTED"
    assert basis.validation_status == "INCONCLUSIVE"
    assert basis.numerical_status == "INCONCLUSIVE"
    assert basis.use_policy == "ALLOW_INCONCLUSIVE_COMPUTED_MODES"
    assert basis.diagnostics["modal_validation_status"] == "INCONCLUSIVE"
    assert basis.result_availability["eigenvalues"]["status"] == "AVAILABLE_UNCERTIFIED"
    assert basis.result_availability["eigenvalues"]["usable_as_certified_evidence"] is False
    with pytest.raises(ModalResidualValidationError) as denied:
        basis.assert_compatible(None, allow_inconclusive=False)  # type: ignore[arg-type]
    assert denied.value.diagnostics["reason"] == "inconclusive_basis_use_not_authorized"
    with pytest.raises(InputValidationError, match="requires a PreparedDynamicSystem"):
        basis.assert_compatible(None, allow_inconclusive=True)  # type: ignore[arg-type]


def test_120_dof_1188_stored_terms_can_be_accessed_but_not_certified() -> None:
    size = 120
    stiffness_lil = lil_matrix((size, size))
    stiffness_lil.setdiag(np.full(size, 20.0))
    for offset in range(1, 5):
        values = np.full(size - offset, 0.01)
        stiffness_lil.setdiag(values, k=offset)
        stiffness_lil.setdiag(values, k=-offset)
    for row, column in ((0, 10), (1, 20), (2, 30), (3, 40)):
        stiffness_lil[row, column] = 0.002
        stiffness_lil[column, row] = 0.002
    stiffness = stiffness_lil.tocsr()
    mass = eye(size, format="csr")
    assert stiffness.nnz + mass.nnz == 1_188

    with pytest.raises(ModalResidualValidationError) as strict_error:
        ModalBasis._from_operators(
            stiffness,
            mass,
            operator_identity="banded-120-1188-strict-v1",
            dof_signature=(),
            requested_modes=2,
            method="eigsh",
            dense_limit=64,
        )
    assert strict_error.value.validation_status == "INCONCLUSIVE"
    assert strict_error.value.diagnostics["reason"] == "aggregate_work_budget"

    basis = ModalBasis._from_operators(
        stiffness,
        mass,
        operator_identity="banded-120-1188-compat-v1",
        dof_signature=(),
        requested_modes=2,
        method="eigsh",
        dense_limit=64,
        validation_policy="allow_inconclusive",
    )
    assert basis.mode_count == 2
    assert basis.validation_status == "INCONCLUSIVE"
    assert basis.diagnostics["modal_residual_validation"]["reason"] == "aggregate_work_budget"


def test_explicit_compatibility_policy_never_promotes_a_failed_eigenpair(monkeypatch: pytest.MonkeyPatch) -> None:
    def wrong_eigensolver(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray, str]:
        return np.asarray([1.0, 4.0]), np.eye(2)[:, ::-1], "synthetic_wrong_pair"

    monkeypatch.setattr(ModalAnalysisSolver, "_solve_eigenproblem", wrong_eigensolver)
    with pytest.raises(ModalResidualValidationError) as caught:
        ModalBasis._from_operators(
            csr_matrix(np.diag([1.0, 4.0])),
            eye(2, format="csr"),
            operator_identity="failed-pair-compat-v1",
            dof_signature=(),
            requested_modes=1,
            method="eigsh",
            dense_limit=8,
            validation_policy="allow_inconclusive",
        )
    assert caught.value.validation_status == "FAIL"


def test_cluster_boundary_is_rejected_without_automatic_mode_count_increase() -> None:
    stiffness = np.diag([1.0, 1.0, 4.0])
    with pytest.raises(InputValidationError, match="cuts an identified modal cluster"):
        _matrix_basis(stiffness, np.eye(3), 1)

    basis = _matrix_basis(stiffness, np.eye(3), 2)
    assert basis.clusters == ((1, 2),)
    assert basis.mode_count == 2
    assert basis.diagnostics["truncation"]["unrepresented_dof_modes"] == 1


def test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe() -> None:
    stiffness = csr_matrix(np.diag([1.0, 1.0, 4.0]))
    mass = csr_matrix(np.eye(3))
    angle = 0.37
    rotation = np.asarray([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    original = np.eye(3)[:, :2]
    rotated = np.column_stack((original @ rotation, np.eye(3)[:, 2]))
    normalized = _mass_normalize_and_handle_degenerate_subspaces(
        rotated,
        np.asarray([1.0, 1.0, 4.0]),
        mass,
        ((0, 1),),
    )
    np.testing.assert_allclose(normalized.T @ (mass @ normalized), np.eye(3), atol=1e-12)
    for index, eigenvalue in enumerate([1.0, 1.0, 4.0]):
        np.testing.assert_allclose(
            stiffness @ normalized[:, index], eigenvalue * (mass @ normalized[:, index]), atol=1e-12
        )

    signed = normalized.copy()
    signed[:, 0] *= -1.0
    assert _mass_metric_subspace_equivalent(
        normalized, signed, np.asarray([1.0, 1.0, 4.0]), np.asarray([1.0, 1.0, 4.0]), mass, tolerance=1e-12
    )
    assert not np.array_equal(normalized, signed)
    assert _mass_metric_subspace_equivalent(
        normalized,
        np.column_stack((original, np.eye(3)[:, 2])),
        np.asarray([1.0, 1.0, 4.0]),
        np.asarray([1.0, 1.0, 4.0]),
        mass,
        tolerance=1e-12,
    )


def test_near_degenerate_cluster_uses_invariant_damping_block() -> None:
    basis = _matrix_basis(np.diag([1.0, 1.0 + 1.0e-9, 9.0]), np.eye(3), 3)
    assert basis.clusters[0] == (1, 2)
    damping = basis.prescribed_modal_damping([0.02, 0.02, 0.03])
    block = damping.matrix[:2, :2]
    assert block[0, 0] == pytest.approx(block[1, 1], rel=0.0, abs=1e-12)
    assert block[0, 1] == pytest.approx(0.0, abs=1e-14)


def test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard() -> None:
    prepared = _prepared("TET4")
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    alpha, beta = 0.02, 0.001
    rayleigh = basis.rayleigh_damping(prepared, alpha=alpha, beta=beta)
    expected = alpha * basis.projected_mass + beta * basis.projected_stiffness
    np.testing.assert_allclose(rayleigh.matrix, expected, rtol=1e-10, atol=1e-10)
    assert rayleigh.source == "RAYLEIGH_PHYSICAL_PROJECTED"
    assert rayleigh.reaction_availability == "NOT_COMPUTED"
    assert "full-space equilibrium" in rayleigh.reaction_reason

    clustered = _matrix_basis(np.diag([1.0, 1.0, 9.0]), np.eye(3), 3)
    prescribed = clustered.prescribed_modal_damping([0.02, 0.02, 0.03])
    np.testing.assert_allclose(prescribed.matrix[:2, :2], np.eye(2) * 0.04, atol=1e-12)
    assert prescribed.reaction_availability == "UNAVAILABLE"
    assert prescribed.parameters["cluster_records"]
    with pytest.raises(InputValidationError, match="must be equal within every identified modal cluster"):
        clustered.prescribed_modal_damping([0.02, 0.04, 0.03])
    zero = clustered.prescribed_modal_damping(0.0)
    np.testing.assert_array_equal(zero.matrix, np.zeros((3, 3)))


def test_invalid_spectral_domain_singular_mass_indefinite_stiffness_and_rigid_mode() -> None:
    with pytest.raises(InputValidationError, match="non-positive diagonal"):
        _positive_definite_screen(csr_matrix([[1.0, 0.0], [0.0, 0.0]]), "mass")
    with pytest.raises(InputValidationError, match="Cholesky SPD screen"):
        _positive_definite_screen(csr_matrix([[1.0, 1.0], [1.0, 1.0]]), "mass")
    with pytest.raises(InputValidationError, match="Cholesky SPD screen"):
        _positive_definite_screen(csr_matrix([[1.0, 2.0], [2.0, 1.0]]), "stiffness")
    with pytest.raises(InputValidationError, match="non-positive eigenvalues"):
        _matrix_basis(np.diag([0.0, 2.0]), np.eye(2), 2)
    asymmetric = csr_matrix([[2.0, 0.25], [0.0, 1.0]])
    assert _relative_sparse_symmetry_error(asymmetric) > 1e-12


def test_wp03_complex_excitation_projection_preserves_phasor_and_reuses_operators() -> None:
    model = _model("TET4")
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    channel = ExcitationChannel(
        channel_id="harmonic:vertical",
        spatial_distribution=(SpatialDofWeight(1, "UY", 2.5),),
        spatial_units="N",
        amplitude_units="1",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=None,
        harmonic=HarmonicAmplitude(3.0, ComplexPhasor(0.0, 4.0)),
    )
    channels = ExcitationChannelSet([channel]).bind(prepared)
    projected = basis.project_harmonic_excitation(channels, prepared, frequency_hz=3.0)
    full = channels.full_harmonic_rhs(prepared, frequency_hz=3.0)
    expected = basis.modes.T @ prepared.reduce_load(full)
    np.testing.assert_allclose(projected, expected, rtol=1e-12, atol=1e-12)
    assert np.iscomplexobj(projected)
    assert np.any(np.abs(projected.imag) > 0.0)
    basis.assert_compatible(prepared)

    real_channel = ExcitationChannel(
        channel_id="static:vertical",
        spatial_distribution=(SpatialDofWeight(1, "UY", 3.0),),
        spatial_units="N",
        amplitude_units="1",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=2.0,
    )
    real_bound = ExcitationChannelSet([real_channel]).bind(prepared)
    real_projection = basis.project_real_excitation(real_bound, prepared, time_s=0.0)
    expected_real = basis.modes.T @ real_bound.reduced_real_rhs(prepared, time_s=0.0)
    np.testing.assert_allclose(real_projection, expected_real, rtol=1e-12, atol=1e-12)
    assert not np.iscomplexobj(real_projection)

    changed_excitation = ExcitationChannelSet(
        [
            ExcitationChannel(
                channel_id="harmonic:vertical",
                spatial_distribution=(SpatialDofWeight(1, "UY", 5.0),),
                spatial_units="N",
                amplitude_units="1",
                result_units="N",
                frame_convention="global_model_frame",
                sign_convention="positive_along_named_global_dof",
                constant_amplitude=None,
                harmonic=HarmonicAmplitude(3.0, ComplexPhasor(1.0, 0.0)),
            )
        ]
    ).bind(prepared)
    basis.assert_compatible(prepared)
    assert not np.allclose(
        projected,
        basis.project_harmonic_excitation(changed_excitation, prepared, frequency_hz=3.0),
    )


def test_physical_mutation_invalidates_basis_and_full_rhs_projection_is_mapped() -> None:
    model = _model("TET4")
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    full_vector = np.zeros(sum(len(names) for _, names in prepared.dof_signature))
    full_vector[-1] = 1.0
    projected = basis.project_full_rhs(full_vector, prepared)
    np.testing.assert_allclose(projected, basis.modes.T @ prepared.reduce_load(full_vector))

    mutated = _model("TET4")
    mutated.concentrated_masses.append(ConcentratedMass(node=1, mass=0.5))
    other = PreparedDynamicSystem.prepare(mutated, source_sha=_SOURCE_SHA)
    with pytest.raises(InputValidationError, match="stale or belongs to different"):
        basis.assert_compatible(other)


def test_modal_basis_snapshot_is_defensive_and_historical_modal_route_still_runs() -> None:
    model = _model("TET4", analysis_type="modal")
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    alternate = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="eigsh")
    assert basis.basis_identity != alternate.basis_identity
    assert basis.subspace_equivalent(alternate, prepared)
    exposed = basis.modes
    with pytest.raises(ValueError):
        exposed[0, 0] = 10.0
    matrix = basis.projected_mass
    with pytest.raises(ValueError):
        matrix[0, 0] = 10.0

    legacy = ModalAnalysisSolver().solve(model)
    assert legacy.eigenvalues.size > 0
    assert legacy.frequencies_hz.size == legacy.eigenvalues.size
    assert legacy.solver["max_relative_residual"] <= 1e-7
