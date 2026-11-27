"""Public-route checkpoint continuation with element assembly replaced by a toy operator.

This is not a FEM test: a tiny TET10-shaped input exercises routing and
checkpoint identity, while its force/tangent operator is a one-matrix double.
"""

from copy import deepcopy

import numpy as np
import pytest
from scipy.sparse import eye

from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore


class PauseAfterAcceptedCheckpoint(RuntimeError):
    """Simulate process interruption just after a chosen accepted state is saved."""


def test_planned_pause_option_refused_on_linear_static_before_assembly(tmp_path):
    model = _model(tmp_path / "unused.npz")
    model.analysis = AnalysisSettings.from_raw(
        {"type": "linear_static", "parameters": {"experimental_pause_after_accepted_increments": 1}}
    )
    with pytest.raises(InputValidationError, match="experimental_pause_after_accepted_increments requires"):
        AnalysisRouter().solve(model)


class SyntheticAssembly:
    def __init__(self, ndof: int) -> None:
        self.ndof = ndof
        self.nodes = np.zeros((10, 3))
        self.matrix = eye(ndof, format="csr")

    def assemble(self, displacement, *, tangent_required=True):
        force = self.matrix @ np.asarray(displacement)
        return force, self.matrix if tangent_required else None

    def deformation_determinants(self, displacement):
        del displacement
        return np.ones(1)

    def element_states(self, displacement):
        del displacement
        return {
            "det_f": np.ones(1),
            "green_lagrange_strain": np.zeros((1, 6)),
            "second_piola_stress": np.zeros((1, 6)),
            "cauchy_stress": np.zeros((1, 6)),
            "strain_energy_density": np.zeros(1),
        }

    def strain_energy(self, displacement):
        del displacement
        return 0.0


def _model(
    checkpoint_path,
    *,
    restart_from=None,
    load_increments=12,
    pause_after=None,
    exact_checks=24,
):
    coordinates = [
        [0.0, 0.0, 0.0],  # corner nodes
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.5, 0.0, 0.0],  # midside nodes
        [0.5, 0.5, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 0.5],
        [0.5, 0.0, 0.5],
        [0.0, 0.5, 0.5],
    ]
    fixed = [
        {"node": node, "dofs": ["UX", "UY", "UZ"]}
        for node in range(9)
    ] + [{"node": 9, "dofs": ["UX", "UY"]}]
    parameters = {
        "load_increments": load_increments,
        "max_iterations": 5,
        "tolerance": 1.0e-8,
        "adaptive_load_steps": False,
        "experimental_newton_exact_residual": True,
        "experimental_newton_exact_residual_max_checks": exact_checks,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
    }
    if restart_from is not None:
        parameters["restart_from"] = str(restart_from)
    if pause_after is not None:
        parameters["experimental_pause_after_accepted_increments"] = pause_after
    return FiniteElementModel.from_raw(
        nodes=coordinates,
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 2.1e9, "nu": 0.0}},
        fixed_dofs=fixed,
        loads=[{"node": 9, "dof": "UZ", "value": 1.0}],
        analysis={"type": "geometric_nonlinear_static", "method": "newton_raphson", "parameters": parameters},
    )


def _patch_operator(monkeypatch, *, stop_after_step=None):
    from solveur.core.analyses import geometric_nonlinear
    import solveur.io.nonlinear_checkpoint as checkpoint_io

    builds = []

    def build(model):
        builds.append(model)
        return SyntheticAssembly(model.dof_manager().ndof)

    monkeypatch.setattr(geometric_nonlinear, "build_total_lagrangian_assembly", build)
    if stop_after_step is None:
        return builds

    class PausingStore(NpzNonlinearCheckpointStore):
        def save(self, path, checkpoint, *, keep_step=False):
            written = super().save(path, checkpoint, keep_step=keep_step)
            if checkpoint.completed_step == stop_after_step:
                raise PauseAfterAcceptedCheckpoint(f"paused after accepted step {stop_after_step}")
            return written

    monkeypatch.setattr(checkpoint_io, "NpzNonlinearCheckpointStore", PausingStore)
    return builds


def test_public_geometric_route_resumes_from_last_accepted_checkpoint(tmp_path, monkeypatch):
    partial_path = tmp_path / "partial.npz"
    partial_model = _model(partial_path)
    _patch_operator(monkeypatch, stop_after_step=2)

    with pytest.raises(PauseAfterAcceptedCheckpoint):
        AnalysisRouter().solve(partial_model)

    step_checkpoint = tmp_path / "partial.step00000002.npz"
    assert step_checkpoint.is_file()
    stored = NpzNonlinearCheckpointStore().load(step_checkpoint, model=partial_model, expected_dofs=30)
    assert stored.completed_step == 2
    assert stored.accepted_state.load_factor == pytest.approx(2 / 12)
    assert stored.accepted_state.displacement[29] == pytest.approx(2 / 12)

    # Run a single uninterrupted synthetic route for comparison.
    monkeypatch.undo()
    _patch_operator(monkeypatch)
    continuous = AnalysisRouter().solve(_model(tmp_path / "continuous.npz"))

    # Restart from the last saved accepted state, preserving the physical model,
    # total load path and global increment count.
    restarted_model = _model(tmp_path / "resumed.npz", restart_from=step_checkpoint)
    resumed = AnalysisRouter().solve(restarted_model)
    np.testing.assert_array_equal(resumed.displacements, continuous.displacements)
    assert resumed.solver["restart_step"] == 2
    assert resumed.solver["history_is_partial"] is True
    assert len(resumed.solver["increments"]) == 10
    assert resumed.solver["increments"][-1]["load_factor"] == pytest.approx(1.0)

    # A changed force vector cannot reuse the checkpoint's accepted state.
    incompatible = deepcopy(restarted_model)
    incompatible.loads[0] = type(incompatible.loads[0])(
        node=incompatible.loads[0].node,
        dof=incompatible.loads[0].dof,
        value=1.01,
    )
    with pytest.raises(InputValidationError, match="does not match"):
        AnalysisRouter().solve(incompatible)

    # A truncated checkpoint fails closed before the toy assembly is evaluated.
    corrupt_path = tmp_path / "corrupt.npz"
    corrupt_path.write_bytes(b"not a checkpoint")
    corrupt = _model(tmp_path / "corrupt-resumed.npz", restart_from=corrupt_path)
    with pytest.raises(InputValidationError, match="corrupted"):
        AnalysisRouter().solve(corrupt)

    absent = _model(
        tmp_path / "absent-resumed.npz",
        restart_from=tmp_path / "absent-checkpoint.npz",
    )
    with pytest.raises(InputValidationError, match="invalid or corrupted NPZ"):
        AnalysisRouter().solve(absent)


def test_public_route_pauses_and_resumes_the_same_fixed_path(tmp_path, monkeypatch):
    first_path = tmp_path / "first.npz"
    first_model = _model(
        first_path,
        load_increments=24,
        pause_after=12,
        exact_checks=48,
    )
    _patch_operator(monkeypatch)
    first = AnalysisRouter().solve(first_model)

    checkpoint_path = tmp_path / "first.step00000012.npz"
    assert checkpoint_path.is_file()
    saved = NpzNonlinearCheckpointStore().load(checkpoint_path, model=first_model, expected_dofs=30)
    assert saved.completed_step == 12
    assert saved.accepted_state.load_factor == pytest.approx(0.5)
    assert first.status == "PAUSED"
    assert first.solver["continuation_status"] == "PAUSED"
    assert first.solver["converged"] is False
    assert first.solver["segment_converged"] is True
    assert first.solver["segment_end_step"] == 12
    assert first.solver["segment_end_load_factor"] == pytest.approx(0.5)
    assert first.solver["history_is_partial"] is True
    assert len(first.solver["increments"]) == 12
    assert first.solver["increments"][0]["load_factor"] == pytest.approx(1 / 24)
    assert first.solver["increments"][-1]["load_factor"] == pytest.approx(0.5)

    missing_store = _model(
        tmp_path / "missing-store.npz",
        load_increments=24,
        pause_after=12,
        exact_checks=48,
    )
    missing_store.analysis.parameters.pop("checkpoint_path")
    with pytest.raises(InputValidationError, match="checkpoint_path"):
        AnalysisRouter().solve(missing_store)

    missing_exact_option = _model(
        tmp_path / "missing-exact.npz",
        load_increments=24,
        pause_after=12,
        exact_checks=48,
    )
    missing_exact_option.analysis.parameters.pop("experimental_newton_exact_residual")
    with pytest.raises(InputValidationError, match="experimental fixed-step TET10 exact-residual route"):
        AnalysisRouter().solve(missing_exact_option)

    # The continuous run uses the same full absolute load and 24-factor path.
    monkeypatch.undo()
    _patch_operator(monkeypatch)
    continuous = AnalysisRouter().solve(_model(tmp_path / "continuous.npz", load_increments=24))
    assert continuous.status == "success"
    assert continuous.solver["converged"] is True

    # Resume from global factor 12/24. The next targets are 13/24 through 24/24.
    resumed_model = _model(
        tmp_path / "second.npz",
        restart_from=checkpoint_path,
        load_increments=24,
        pause_after=12,
        exact_checks=48,
    )
    resumed = AnalysisRouter().solve(resumed_model)
    np.testing.assert_array_equal(resumed.displacements, continuous.displacements)
    assert resumed.status == "success"
    assert resumed.solver["continuation_status"] == "CONVERGED"
    assert resumed.solver["converged"] is True
    assert resumed.solver["restart_step"] == 12
    assert resumed.solver["segment_start_step"] == 12
    assert resumed.solver["segment_end_step"] == 24
    assert resumed.solver["segment_start_load_factor"] == pytest.approx(0.5)
    assert resumed.solver["segment_end_load_factor"] == pytest.approx(1.0)
    assert len(resumed.solver["increments"]) == 12
    assert resumed.solver["increments"][0]["load_factor"] == pytest.approx(13 / 24)
    assert resumed.solver["increments"][-1]["load_factor"] == pytest.approx(1.0)

    # Budget changes are part of checkpoint identity; they cannot be used to reset a call.
    changed_budget = _model(
        tmp_path / "changed-budget.npz",
        restart_from=checkpoint_path,
        load_increments=24,
        pause_after=12,
        exact_checks=24,
    )
    with pytest.raises(InputValidationError, match="does not match"):
        AnalysisRouter().solve(changed_budget)

    changed_path = _model(
        tmp_path / "wrong-path.npz",
        restart_from=checkpoint_path,
        load_increments=48,
        pause_after=12,
        exact_checks=48,
    )
    with pytest.raises(InputValidationError, match="does not match"):
        AnalysisRouter().solve(changed_path)

@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"pause_after": True}, "requires a positive integer"),
        ({"pause_after": 0}, "requires a positive integer"),
        ({"pause_after": 12, "checkpoint_interval": 12}, "checkpoint_interval=1"),
    ],
)
def test_planned_pause_rejects_invalid_or_unsaved_boundaries(tmp_path, overrides, message):
    parameters = {
        "load_increments": 24,
        "max_iterations": 5,
        "tolerance": 1.0e-8,
        "adaptive_load_steps": False,
        "experimental_newton_exact_residual": True,
        "experimental_newton_exact_residual_max_checks": 48,
        "checkpoint_path": str(tmp_path / "pause.npz"),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
        "experimental_pause_after_accepted_increments": 12,
    }
    parameters.update(
        {"experimental_pause_after_accepted_increments": overrides.get("pause_after", 12)}
    )
    if "checkpoint_interval" in overrides:
        parameters["checkpoint_interval"] = overrides["checkpoint_interval"]
    model = _model(tmp_path / "validated-pause.npz", load_increments=24, pause_after=12, exact_checks=48)
    model.analysis.parameters.update(parameters)
    with pytest.raises(InputValidationError, match=message):
        AnalysisRouter().solve(model)
