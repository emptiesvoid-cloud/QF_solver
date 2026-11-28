"""Public-route checkpoint continuation with element assembly replaced by a toy operator.

This is not a FEM test: a tiny TET10-shaped input exercises routing and
checkpoint identity, while its force/tangent operator is a one-matrix double.
"""

from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch

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


def test_c24_terminal_extension_keeps_absolute_force_and_accepted_state(tmp_path, monkeypatch):
    key = "experimental_fixed_path_extension"
    original = tmp_path / "old"
    original.mkdir()
    new = tmp_path / "new"
    new.mkdir()
    _patch_operator(monkeypatch)
    first = AnalysisRouter().solve(_model(original / "state.npz", load_increments=12, pause_after=12))
    seed = original / "state.step00000012.npz"
    raw = seed.read_bytes()
    extension = _model(new / "state.npz", restart_from=seed, load_increments=12, pause_after=12)
    extension.analysis.parameters[key] = {
        "start_factor": 1.0, "target_factor": 1.5, "steps": 6,
        "checkpoint_sha256": sha256(raw).hexdigest(),
    }
    assert first.displacements[29] == 1.0
    result = AnalysisRouter().solve(extension)
    assert result.solver["restart_step"] == 12
    assert result.solver["target_load_factor"] == 1.5
    assert result.solver["continuation_status"] == "CONVERGED"
    assert [i["load_factor"] for i in result.solver["increments"]] == [n / 12 for n in range(13, 19)]
    assert result.displacements[29] == 1.5
    assert (new / "state.step00000018.npz").is_file()
    assert seed.read_bytes() == raw

    for field, value in (("start_factor", 0), ("target_factor", 1.6), ("checkpoint_sha256", "0" * 64)):
        bad = deepcopy(extension)
        bad.analysis.parameters[key][field] = value
        with pytest.raises(InputValidationError):
            AnalysisRouter().solve(bad)
    other = deepcopy(extension)
    other.loads[0] = type(other.loads[0])(node=9, dof="UZ", value=1.01)
    with pytest.raises(InputValidationError, match="does not match"):
        AnalysisRouter().solve(other)
    damaged = original / "incomplete.npz"
    damaged.write_bytes(raw[:100])
    bad = deepcopy(extension)
    bad.analysis.parameters["restart_from"] = str(damaged)
    bad.analysis.parameters[key]["checkpoint_sha256"] = sha256(damaged.read_bytes()).hexdigest()
    with pytest.raises(InputValidationError, match="corrupted"):
        AnalysisRouter().solve(bad)

    from solveur.core.nonlinear import iteration
    from solveur.core.errors import NumericalConvergenceError

    solve_increment = iteration.UnifiedNewtonEngine._solve_increment
    def reject(self, **options):
        transaction = options["transaction"]
        assert options["load_factor"] == 13 / 12
        assert options["external"][29] == 1.0
        before = transaction.accepted_state.digest
        with patch.object(iteration.NonlinearLinearSolverAdapter, "solve",
                          side_effect=NumericalConvergenceError("synthetic rejected correction")):
            with pytest.raises(NumericalConvergenceError):
                solve_increment(self, **options)
        assert transaction.accepted_state.digest == before
        raise NumericalConvergenceError("synthetic rejected correction")

    monkeypatch.setattr(iteration.UnifiedNewtonEngine, "_solve_increment", reject)
    failed = deepcopy(extension)
    failed.analysis.parameters["checkpoint_path"] = str(new / "failed.npz")
    with pytest.raises(NumericalConvergenceError, match="synthetic rejected correction"):
        AnalysisRouter().solve(failed)
    assert not (new / "failed.npz").exists()
    assert seed.read_bytes() == raw


def test_c24_secant_extension_resumes_step_198_on_same_absolute_path(tmp_path, monkeypatch):
    """Synthetic public-route test; the TET10 assembly is replaced by an identity double."""
    key = "experimental_fixed_path_extension"
    base_dir, first_dir, source_dir = (tmp_path / name for name in ("base", "first", "source"))
    base_dir.mkdir()
    first_dir.mkdir()
    source_dir.mkdir()

    _patch_operator(monkeypatch)
    base_model = _model(base_dir / "base.npz", load_increments=12, pause_after=12, exact_checks=48)
    AnalysisRouter().solve(base_model)
    checkpoint_192 = base_dir / "base.step00000012.npz"

    first_model = _model(
        first_dir / "first.npz", restart_from=checkpoint_192, load_increments=12, pause_after=12, exact_checks=48
    )
    first_extension = {
        "start_factor": 1.0,
        "target_factor": 1.5,
        "steps": 6,
        "checkpoint_sha256": sha256(checkpoint_192.read_bytes()).hexdigest(),
    }
    first_model.analysis.parameters[key] = first_extension
    first_result = AnalysisRouter().solve(first_model)
    assert first_result.solver["segment_end_step"] == 18
    checkpoint_197 = first_dir / "first.step00000017.npz"
    checkpoint_198 = first_dir / "first.step00000018.npz"
    checkpoint_197_bytes = checkpoint_197.read_bytes()
    checkpoint_198_bytes = checkpoint_198.read_bytes()
    checkpoint_store = NpzNonlinearCheckpointStore()
    accepted_197 = checkpoint_store.load(checkpoint_197, model=first_model, expected_dofs=30)
    accepted_198 = checkpoint_store.load(checkpoint_198, model=first_model, expected_dofs=30)
    assert accepted_197.completed_step == 17
    assert accepted_198.completed_step == 18
    assert accepted_197.load_factor == pytest.approx(17 / 12)
    assert accepted_198.load_factor == pytest.approx(18 / 12)

    def second_model(output_name, *, predictor=False):
        model = _model(
            source_dir / output_name,
            restart_from=checkpoint_198,
            load_increments=12,
            pause_after=12,
            exact_checks=48,
        )
        model.analysis.parameters[key] = {
            "start_step": 18,
            "start_factor": 1.5,
            "target_factor": 2.5,
            "steps": 6,
            "step_stride": 2,
            "checkpoint_sha256": sha256(checkpoint_198_bytes).hexdigest(),
            "predecessor_checkpoint_path": str(checkpoint_197),
            "predecessor_checkpoint_sha256": sha256(checkpoint_197_bytes).hexdigest(),
            "previous_model_signature": accepted_198.model_signature,
            "previous_extension": dict(first_extension),
        }
        if predictor:
            model.analysis.parameters["experimental_secant_predictor"] = True
        return model

    reference_model = second_model("reference.npz")
    reference = AnalysisRouter().solve(reference_model)
    assert reference.status == "success"
    assert reference.solver["restart_step"] == 18
    assert reference.solver["segment_end_step"] == 30
    assert reference.solver["segment_start_load_factor"] == pytest.approx(18 / 12)
    assert reference.solver["segment_end_load_factor"] == pytest.approx(30 / 12)
    assert [item["load_factor"] for item in reference.solver["increments"]] == [n / 12 for n in (20, 22, 24, 26, 28, 30)]
    assert "experimental_secant_predictor" not in reference.solver

    predicted_model = second_model("predicted.npz", predictor=True)
    predicted = AnalysisRouter().solve(predicted_model)
    assert predicted.status == "success"
    assert predicted.solver["restart_step"] == 18
    assert predicted.solver["segment_end_step"] == 30
    predictor = predicted.solver["experimental_secant_predictor"]
    assert [item["ratio"] for item in predictor["predictions"]] == pytest.approx([2, 1, 1, 1, 1, 1])
    assert predictor["total_prediction_seconds"] >= 0
    np.testing.assert_array_equal(predicted.displacements, reference.displacements)
    np.testing.assert_array_equal(predicted.displacements[:29], np.zeros(29))
    assert predicted.displacements[29] == pytest.approx(2.5)
    assert checkpoint_197.read_bytes() == checkpoint_197_bytes
    assert checkpoint_198.read_bytes() == checkpoint_198_bytes

    bad_model = second_model("bad-source.npz")
    bad_model.analysis.parameters[key]["predecessor_checkpoint_sha256"] = "0" * 64
    with pytest.raises(InputValidationError, match="predecessor checkpoint digest"):
        AnalysisRouter().solve(bad_model)
    bad_schema = second_model("bad-schema.npz")
    bad_schema.analysis.parameters[key]["previous_extension"]["start_factor"] = True
    with pytest.raises(InputValidationError, match="Continued extension"):
        AnalysisRouter().solve(bad_schema)
    wrong_model = second_model("wrong-model.npz")
    wrong_model.loads[0] = type(wrong_model.loads[0])(node=9, dof="UZ", value=1.01)
    with pytest.raises(InputValidationError):
        AnalysisRouter().solve(wrong_model)

    from solveur.core.nonlinear import iteration
    from solveur.core.errors import NumericalConvergenceError

    accepted_digest = accepted_198.accepted_state.digest

    def reject_predicted_trial(self, **options):
        transaction = options["transaction"]
        assert transaction.accepted_state.load_factor == pytest.approx(18 / 12)
        assert transaction.accepted_state.digest == accepted_digest
        assert transaction.trial_state.displacement[29] == pytest.approx(20 / 12)
        raise NumericalConvergenceError("synthetic predictor rejection")

    monkeypatch.setattr(iteration.UnifiedNewtonEngine, "_solve_increment", reject_predicted_trial)
    failed_model = second_model("failed-predictor.npz", predictor=True)
    with pytest.raises(NumericalConvergenceError, match="synthetic predictor rejection"):
        AnalysisRouter().solve(failed_model)
    assert checkpoint_197.read_bytes() == checkpoint_197_bytes
    assert checkpoint_198.read_bytes() == checkpoint_198_bytes
    assert not (source_dir / "failed-predictor.npz").exists()


def test_secant_predictor_is_rejected_on_other_routes_and_false_is_a_noop(monkeypatch, tmp_path):
    model = _model(tmp_path / "unused.npz")
    model.analysis = AnalysisSettings.from_raw({"type": "linear_static", "parameters": {"experimental_secant_predictor": True}})
    monkeypatch.setattr(
        "solveur.core.router.preflight_model",
        lambda _model: type("Compatible", (), {"raise_for_error": lambda self: None})(),
    )
    with pytest.raises(InputValidationError, match="experimental_secant_predictor requires geometric_nonlinear_static"):
        AnalysisRouter().solve(model)

    for parameters in ({}, {"experimental_secant_predictor": False}):
        model = _model(tmp_path / "unused.npz")
        model.analysis = AnalysisSettings.from_raw({"type": "linear_static", "parameters": parameters})
        marker = object()
        monkeypatch.setattr("solveur.core.router.LinearStaticSolver.solve", lambda *args, **kwargs: marker)
        assert AnalysisRouter().solve(model) is marker


def test_secant_predictor_requires_an_identified_continuation_before_assembly(monkeypatch, tmp_path):
    model = _model(tmp_path / "unused.npz")
    model.analysis.parameters["experimental_secant_predictor"] = True
    monkeypatch.setattr(
        "solveur.core.analyses.geometric_nonlinear.build_total_lagrangian_assembly",
        lambda _model: pytest.fail("predictor eligibility must be checked before assembly"),
    )
    with pytest.raises(InputValidationError, match="requires the identified stateless, fixed-step TET10 extension"):
        AnalysisRouter().solve(model)


@pytest.mark.parametrize("value", [1, "true", None])
def test_secant_predictor_option_requires_boolean(value, tmp_path):
    model = _model(tmp_path / "unused.npz")
    model.analysis.parameters["experimental_secant_predictor"] = value
    with pytest.raises(InputValidationError, match="experimental_secant_predictor must be an explicit boolean"):
        AnalysisRouter().solve(model)
