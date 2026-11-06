from __future__ import annotations

import math

import numpy as np
import pytest

from solveur.core.analyses.excitation_channels import (
    CHANNEL_SCHEMA,
    ComplexPhasor,
    ExcitationChannel,
    ExcitationChannelSet,
    HarmonicAmplitude,
    SpatialDofWeight,
    TimeSample,
)
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import model_to_dict


_SOURCE_SHA = "a" * 40


def _model(family: str = "TET4", *, loads=None, distributed_loads=None, parameters=None) -> FiniteElementModel:
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
            edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
            nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2 for a, b in edges]]).tolist()
            connectivity = list(range(20))
            fixed_nodes = [0, 3, 4, 7, 9, 10, 15, 17]
    elif family == "BEAM2":
        nodes = [[0, 0, 0], [1, 0, 0]]
        connectivity = [0, 1]
        fixed_nodes = [0]
    else:
        raise AssertionError(family)

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
        if family == "BEAM2"
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    fixed_dofs = [
        {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"] if family == "BEAM2" else ["UX", "UY", "UZ"]}
        for node in fixed_nodes
    ]
    analysis_parameters = {"time_step": 0.01, "steps": 1}
    analysis_parameters.update(parameters or {})
    return FiniteElementModel.from_raw(
        analysis={"type": "transient_dynamic", "method": "newmark", "parameters": analysis_parameters},
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "mat"}],
        materials={"mat": material},
        fixed_dofs=fixed_dofs,
        loads=loads or [],
        distributed_loads=distributed_loads or [],
    )


def _prepared(model: FiniteElementModel) -> PreparedDynamicSystem:
    return PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)


class _CountingAssembler(GlobalAssembler):
    def __init__(self) -> None:
        super().__init__()
        self.operator_assemblies = 0

    def assemble_stiffness_and_mass(self, *args, **kwargs):
        self.operator_assemblies += 1
        return super().assemble_stiffness_and_mass(*args, **kwargs)


def _channel(
    channel_id: str,
    node: int,
    dof: str,
    value: float,
    *,
    amplitude: float | None = 1.0,
    history: tuple[TimeSample, ...] = (),
    harmonic: HarmonicAmplitude | None = None,
    result_units: str = "N",
) -> ExcitationChannel:
    return ExcitationChannel(
        channel_id=channel_id,
        spatial_distribution=(SpatialDofWeight(node, dof, value),),
        spatial_units="N",
        amplitude_units="1",
        result_units=result_units,
        frame_convention="global",
        sign_convention="positive_global_dof",
        constant_amplitude=amplitude,
        time_history=history,
        harmonic=harmonic,
    )


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_explicit_channels_bind_to_each_wp00_element_family(family: str) -> None:
    model = _model(family)
    prepared = _prepared(model)
    channels = ExcitationChannelSet([_channel("force", 1, "UX", 2.5)])
    bound = channels.bind(prepared)
    rhs = bound.full_real_rhs(prepared, time_s=0.0)
    assert rhs.shape == (prepared.mass_full.shape[0],)
    assert np.isclose(rhs[model.dof_manager().index(1, "UX")], 2.5)


def test_nodal_real_amplitude_and_multiple_channel_superposition() -> None:
    model = _model()
    prepared = _prepared(model)
    channels = ExcitationChannelSet(
        [
            _channel("left", 1, "UX", 2.0, amplitude=3.0),
            _channel("right", 1, "UY", -4.0, amplitude=0.5),
        ]
    )
    rhs = channels.bind(prepared).full_real_rhs(prepared, time_s=0.0)
    dofs = model.dof_manager()
    assert rhs[dofs.index(1, "UX")] == pytest.approx(6.0)
    assert rhs[dofs.index(1, "UY")] == pytest.approx(-2.0)


def test_distributed_legacy_load_adapter_matches_existing_assembler_independently() -> None:
    model = _model(distributed_loads=[{"type": "body_force", "value": [1.0, -2.0, 0.5], "elements": [0]}])
    prepared = _prepared(model)
    adapter = ExcitationChannelSet.from_legacy_model(model, prepared)
    actual = adapter.bind(prepared).full_real_rhs(prepared, time_s=0.0)
    expected = GlobalAssembler().assemble_load_vectors(model, model.dof_manager())[0]
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-14)


@pytest.mark.parametrize(
    ("phase", "expected"),
    [(0.0, 1.0 + 0.0j), (90.0, 0.0 + 1.0j), (180.0, -1.0 + 0.0j)],
)
def test_harmonic_phasor_phase_convention_and_complex_preservation(phase: float, expected: complex) -> None:
    model = _model()
    prepared = _prepared(model)
    channel = _channel(
        "phasor",
        1,
        "UX",
        1.0,
        amplitude=None,
        harmonic=HarmonicAmplitude(5.0, ComplexPhasor.from_amplitude_phase(1.0, phase)),
    )
    rhs = ExcitationChannelSet([channel]).bind(prepared).full_harmonic_rhs(prepared)
    assert rhs[model.dof_manager().index(1, "UX")] == pytest.approx(expected)
    assert channel.harmonic is not None
    assert channel.harmonic.angular_frequency_rad_s == pytest.approx(10.0 * math.pi)


def test_complex_superposition_exact_and_near_cancellation_use_absolute_metric() -> None:
    model = _model()
    prepared = _prepared(model)
    channels = ExcitationChannelSet(
        [
            _channel("a", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(2.0, ComplexPhasor(3.0, -1.0))),
            _channel("b", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(2.0, ComplexPhasor(-3.0, 1.0))),
        ]
    )
    rhs = channels.bind(prepared).full_harmonic_rhs(prepared)
    assert np.linalg.norm(rhs) == 0.0

    almost = (
        ExcitationChannelSet(
            [
                _channel("a", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(2.0, ComplexPhasor(1.0, 0.0))),
                _channel(
                    "b",
                    1,
                    "UX",
                    1.0,
                    amplitude=None,
                    harmonic=HarmonicAmplitude(2.0, ComplexPhasor(-1.0 + 1.0e-13, 0.0)),
                ),
            ]
        )
        .bind(prepared)
        .full_harmonic_rhs(prepared)
    )
    assert np.linalg.norm(almost) <= 2.0e-13


def test_complex_rhs_matches_independent_analytic_reference_and_reduces_without_loss() -> None:
    model = _model()
    prepared = _prepared(model)
    channels = ExcitationChannelSet(
        [
            _channel("a", 1, "UX", 2.0, amplitude=None, harmonic=HarmonicAmplitude(7.0, ComplexPhasor(1.0, 2.0))),
            _channel("b", 1, "UY", -3.0, amplitude=None, harmonic=HarmonicAmplitude(7.0, ComplexPhasor(-0.5, 0.25))),
        ]
    )
    bound = channels.bind(prepared)
    actual = bound.full_harmonic_rhs(prepared)
    expected = np.zeros(prepared.mass_full.shape[0], dtype=np.complex128)
    dofs = model.dof_manager()
    expected[dofs.index(1, "UX")] = 2.0 * (1.0 + 2.0j)
    expected[dofs.index(1, "UY")] = -3.0 * (-0.5 + 0.25j)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-14)
    reduced = bound.reduced_harmonic_rhs(prepared)
    assert np.iscomplexobj(reduced)
    assert np.any(np.abs(reduced.imag) > 0.0)


def test_hz_conversion_is_single_explicit_boundary_and_mixed_frequencies_reject() -> None:
    signal = HarmonicAmplitude(12.5, ComplexPhasor(1.0, 0.0))
    assert signal.angular_frequency_rad_s == pytest.approx(25.0 * math.pi)
    model = _model()
    prepared = _prepared(model)
    two_frequencies = ExcitationChannelSet(
        [
            _channel("a", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(2.0, ComplexPhasor(1.0, 0.0))),
            _channel("b", 1, "UY", 1.0, amplitude=None, harmonic=HarmonicAmplitude(3.0, ComplexPhasor(1.0, 0.0))),
        ]
    )
    with pytest.raises(InputValidationError, match="different frequencies"):
        two_frequencies.bind(prepared).full_harmonic_rhs(prepared)


def test_units_dimensions_and_frame_mismatch_reject_superposition() -> None:
    first = _channel("a", 1, "UX", 1.0)
    incompatible = _channel("b", 1, "UY", 1.0, result_units="m")
    with pytest.raises(InputValidationError, match="incompatible units"):
        ExcitationChannelSet([first, incompatible])


def test_explicit_channel_set_rejects_ignored_legacy_identity_payload() -> None:
    with pytest.raises(InputValidationError, match="cannot carry ignored legacy controls"):
        ExcitationChannelSet([], legacy_controls={"load_function": "sine"})


@pytest.mark.parametrize("bad", [complex(1.0, 0.0), np.nan, np.inf, -np.inf])
def test_nonreal_or_nonfinite_spatial_values_reject(bad: object) -> None:
    with pytest.raises(InputValidationError):
        SpatialDofWeight(1, "UX", bad)  # type: ignore[arg-type]


def test_invalid_frequency_phasor_and_history_reject() -> None:
    with pytest.raises(InputValidationError, match="non-negative"):
        HarmonicAmplitude(-1.0, ComplexPhasor(1.0, 0.0))
    with pytest.raises(InputValidationError, match="finite"):
        ComplexPhasor(float("nan"), 0.0)
    with pytest.raises(InputValidationError, match="strictly increasing"):
        _channel(
            "history",
            1,
            "UX",
            1.0,
            amplitude=None,
            history=(TimeSample(0.0, 0.0), TimeSample(0.0, 1.0)),
        )


def test_real_time_history_interpolates_explicitly_and_zero_channel_is_retained() -> None:
    model = _model()
    prepared = _prepared(model)
    zero = _channel("zero", 1, "UX", 0.0, amplitude=4.0)
    history = _channel(
        "history",
        1,
        "UY",
        2.0,
        amplitude=None,
        history=(TimeSample(0.0, 0.0), TimeSample(1.0, 3.0)),
    )
    channel_set = ExcitationChannelSet([zero, history])
    bound = channel_set.bind(prepared)
    rhs = bound.full_real_rhs(prepared, time_s=0.5)
    assert rhs[model.dof_manager().index(1, "UY")] == pytest.approx(3.0)
    assert channel_set.zero_channel_ids == ("zero",)


def test_empty_channel_set_is_an_explicit_zero_rhs() -> None:
    model = _model()
    prepared = _prepared(model)
    bound = ExcitationChannelSet().bind(prepared)
    assert np.linalg.norm(bound.full_real_rhs(prepared, time_s=0.0)) == 0.0
    assert np.linalg.norm(bound.full_harmonic_rhs(prepared, frequency_hz=3.0)) == 0.0


def test_new_legacy_syntax_mix_is_rejected_and_legacy_per_load_factors_apply_once() -> None:
    model = _model(
        loads=[{"node": 1, "dof": "UX", "value": 3.0}, {"node": 1, "dof": "UY", "value": 8.0}],
        parameters={"load_factors_by_load": {"0": [2.0], "1": [0.5]}},
    )
    prepared = _prepared(model)
    with pytest.raises(InputValidationError, match="cannot coexist"):
        ExcitationChannelSet.from_model_inputs(model, prepared, explicit_channels=[])
    legacy = ExcitationChannelSet.from_model_inputs(model, prepared)
    rhs = legacy.bind(prepared).full_real_rhs(prepared, time_s=0.0, step=0, steps=1, dt=0.01)
    dofs = model.dof_manager()
    assert rhs[dofs.index(1, "UX")] == pytest.approx(6.0)
    assert rhs[dofs.index(1, "UY")] == pytest.approx(4.0)


def test_legacy_real_load_is_a_zero_phase_harmonic_coefficient_at_explicit_frequency() -> None:
    model = _model(loads=[{"node": 1, "dof": "UX", "value": 2.5}])
    prepared = _prepared(model)
    bound = ExcitationChannelSet.from_legacy_model(model, prepared).bind(prepared)
    rhs = bound.full_harmonic_rhs(prepared, frequency_hz=6.0)
    assert rhs[model.dof_manager().index(1, "UX")] == pytest.approx(2.5 + 0.0j)


def test_legacy_invalid_temporal_controls_fail_closed_before_factor_evaluation() -> None:
    model = _model(
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        parameters={"load_function": "linear_chirp", "chirp_start_hz": 0.0, "chirp_end_hz": 4.0, "chirp_duration": 0.0},
    )
    prepared = _prepared(model)
    bound = ExcitationChannelSet.from_legacy_model(model, prepared).bind(prepared)
    with pytest.raises(InputValidationError, match="chirp_duration"):
        bound.full_real_rhs(prepared, time_s=0.0)


def test_excitation_mutation_changes_identity_but_preserves_prepared_operator_identity() -> None:
    model = _model(loads=[{"node": 1, "dof": "UX", "value": 2.0}])
    prepared = _prepared(model)
    before = ExcitationChannelSet.from_legacy_model(model, prepared)
    operator_identity = prepared.operator_identity
    model.loads[0] = type(model.loads[0])(node=1, dof="UX", value=5.0)
    prepared.require_compatible(model)
    after = ExcitationChannelSet.from_legacy_model(model, prepared)
    assert before.identity != after.identity
    assert prepared.operator_identity == operator_identity


def test_legacy_channel_adaptation_does_not_reassemble_prepared_operators() -> None:
    model = _model(loads=[{"node": 1, "dof": "UX", "value": 2.0}])
    assembler = _CountingAssembler()
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA, assembler=assembler)
    assert assembler.operator_assemblies == 1
    adapted = ExcitationChannelSet.from_legacy_model(model, prepared, assembler=assembler)
    adapted.bind(prepared).full_real_rhs(prepared, time_s=0.0)
    assert assembler.operator_assemblies == 1


def test_explicit_identity_is_order_independent_and_sensitive_to_all_signal_inputs() -> None:
    base = _channel("stable", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(4.0, ComplexPhasor(1.0, 0.0)))
    other = _channel("other", 1, "UY", 1.0, amplitude=2.0)
    canonical = ExcitationChannelSet([base, other])
    reordered = ExcitationChannelSet([other, base])
    assert canonical.identity == reordered.identity

    changed_distribution = _channel(
        "stable", 1, "UX", 2.0, amplitude=None, harmonic=HarmonicAmplitude(4.0, ComplexPhasor(1.0, 0.0))
    )
    changed_amplitude = _channel(
        "stable", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(4.0, ComplexPhasor(2.0, 0.0))
    )
    changed_phase = _channel(
        "stable", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(4.0, ComplexPhasor(0.0, 1.0))
    )
    changed_frequency = _channel(
        "stable", 1, "UX", 1.0, amplitude=None, harmonic=HarmonicAmplitude(5.0, ComplexPhasor(1.0, 0.0))
    )
    assert ExcitationChannelSet([changed_distribution]).identity != ExcitationChannelSet([base]).identity
    assert ExcitationChannelSet([changed_amplitude]).identity != ExcitationChannelSet([base]).identity
    assert ExcitationChannelSet([changed_phase]).identity != ExcitationChannelSet([base]).identity
    assert ExcitationChannelSet([changed_frequency]).identity != ExcitationChannelSet([base]).identity
    history_a = _channel("h", 1, "UX", 1.0, amplitude=None, history=(TimeSample(0.0, 0.0), TimeSample(1.0, 1.0)))
    history_b = _channel("h", 1, "UX", 1.0, amplitude=None, history=(TimeSample(0.0, 0.0), TimeSample(1.0, 2.0)))
    assert ExcitationChannelSet([history_a]).identity != ExcitationChannelSet([history_b]).identity


def test_complex_phasor_serialization_roundtrip_and_schema_fail_closed() -> None:
    channel = _channel(
        "phasor", 1, "UX", 3.0, amplitude=None, harmonic=HarmonicAmplitude(9.0, ComplexPhasor(1.25, -4.5))
    )
    original = ExcitationChannelSet([channel])
    encoded = original.to_dict()
    assert encoded["schema"] == CHANNEL_SCHEMA
    restored = ExcitationChannelSet.from_dict(encoded)
    assert restored.identity == original.identity
    assert restored.channels[0].harmonic is not None
    assert restored.channels[0].harmonic.phasor.to_dict() == {"real": 1.25, "imag": -4.5}

    broken = dict(encoded)
    broken["schema"] = "unknown/v99"
    with pytest.raises(InputValidationError, match="Unsupported excitation channel schema"):
        ExcitationChannelSet.from_dict(broken)


def test_provenance_rejects_absolute_paths_and_operational_timestamps() -> None:
    with pytest.raises(InputValidationError, match="local or temporary path"):
        ExcitationChannel(
            "bad-path",
            (SpatialDofWeight(1, "UX", 1.0),),
            "1",
            "1",
            "N",
            "global",
            "positive_global_dof",
            provenance=(("source", r"C:\Users\private\input.csv"),),
        )
    with pytest.raises(InputValidationError, match="Operational timestamps"):
        ExcitationChannel(
            "bad-time",
            (SpatialDofWeight(1, "UX", 1.0),),
            "1",
            "1",
            "N",
            "global",
            "positive_global_dof",
            provenance=(("created_at", "2026-10-08T10:00:00Z"),),
        )


def test_unmapped_dof_rejects_and_bound_channels_reject_other_operator() -> None:
    model = _model()
    prepared = _prepared(model)
    with pytest.raises(InputValidationError, match="inactive DOF"):
        ExcitationChannelSet([_channel("bad", 1, "RX", 1.0)]).bind(prepared)

    channels = ExcitationChannelSet([_channel("ok", 1, "UX", 1.0)])
    bound = channels.bind(prepared)
    other_model = _model("BEAM2")
    other_prepared = _prepared(other_model)
    with pytest.raises(InputValidationError, match="do not match"):
        bound.full_real_rhs(other_prepared, time_s=0.0)


def test_sparse_mapping_avoids_dense_dof_by_channel_storage() -> None:
    model = _model()
    prepared = _prepared(model)
    channels = ExcitationChannelSet([_channel(f"c{i:03}", 1, "UX", float(i + 1)) for i in range(64)])
    bound = channels.bind(prepared)
    dense_bytes = bound.dof_count * bound.channel_count * np.dtype(float).itemsize
    assert bound.distribution_nnz == 64
    assert bound.distribution_storage_bytes < dense_bytes


def test_legacy_model_json_surface_remains_unchanged_and_adapter_preserves_load_vectors() -> None:
    model = _model(loads=[{"node": 1, "dof": "UX", "value": 2.0}])
    original = model_to_dict(model)
    assert "excitation_channels" not in original
    parsed = JsonModelReader().from_dict(original)
    assert model_to_dict(parsed) == original
    prepared = _prepared(parsed)
    adapted = ExcitationChannelSet.from_legacy_model(parsed, prepared).bind(prepared)
    expected = GlobalAssembler().assemble_load_vectors(parsed, parsed.dof_manager())[0]
    np.testing.assert_allclose(adapted.full_real_rhs(prepared, time_s=0.0), expected, rtol=0.0, atol=0.0)
