"""Identified real-space excitation channels and complex harmonic phasors.

This WP03 layer creates load right-hand sides only.  It does not assemble or
solve a dynamic equation, and it never changes PreparedDynamicSystem K/M.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import json
import math
import re
from typing import Any, Iterable, Mapping, cast

import numpy as np
from scipy.sparse import csc_matrix

from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.analyses.dynamic_controls import validate_per_load_factors
from solveur.core.dofs import DOF_ORDER, DofManager, normalize_dof_name
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.checkpoint_common import checkpoint_signature


CHANNEL_SCHEMA = "qf-excitation-channel/v1"
_IDENTITY_DOMAIN = "qf-excitation-identity/v1"
_LEGACY_CONTROL_KEYS = (
    "load_function",
    "load_frequency_hz",
    "chirp_start_hz",
    "chirp_end_hz",
    "load_table",
    "load_factors",
    "load_factors_by_load",
    "pulse_duration",
    "frequencies_hz",
    "frequency_start_hz",
    "frequency_stop_hz",
    "frequency_count",
    "start_hz",
    "stop_hz",
    "count",
)
_PHASE_CONVENTION = "response(t) = Re(U * exp(+i*omega*t))"


@dataclass(frozen=True, slots=True)
class ComplexPhasor:
    """Finite complex scalar serialized explicitly as real and imaginary parts."""

    real: float
    imag: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "real", _finite_real(self.real, "phasor.real"))
        object.__setattr__(self, "imag", _finite_real(self.imag, "phasor.imag"))

    @property
    def value(self) -> complex:
        return complex(self.real, self.imag)

    @classmethod
    def from_amplitude_phase(cls, amplitude: float, phase_degrees: float) -> "ComplexPhasor":
        magnitude = _finite_real(amplitude, "phasor amplitude")
        phase = _finite_real(phase_degrees, "phase_degrees")
        angle = math.radians(phase)
        return cls(magnitude * math.cos(angle), magnitude * math.sin(angle))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ComplexPhasor":
        if set(payload) != {"real", "imag"}:
            raise InputValidationError("A phasor must contain exactly finite 'real' and 'imag' fields.")
        return cls(payload["real"], payload["imag"])  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, float]:
        return {"real": self.real, "imag": self.imag}


@dataclass(frozen=True, slots=True)
class SpatialDofWeight:
    """One real spatial-distribution coefficient at a physical node/DOF."""

    node: int
    dof: str
    value: float

    def __post_init__(self) -> None:
        try:
            node = int(self.node)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InputValidationError("Excitation spatial node must be a non-negative integer.") from exc
        if isinstance(self.node, bool) or node != self.node or node < 0:
            raise InputValidationError("Excitation spatial node must be a non-negative integer.")
        try:
            dof = normalize_dof_name(self.dof)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Invalid excitation DOF {self.dof!r}.") from exc
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "dof", dof)
        object.__setattr__(self, "value", _finite_real(self.value, "spatial distribution value"))

    def to_dict(self) -> dict[str, object]:
        return {"node": self.node, "dof": self.dof, "value": self.value}


@dataclass(frozen=True, slots=True)
class TimeSample:
    """A real amplitude sample; histories use linear interpolation and endpoint hold."""

    time_s: float
    value: float

    def __post_init__(self) -> None:
        time = _finite_real(self.time_s, "history time")
        if time < 0.0:
            raise InputValidationError("Excitation history times must be non-negative seconds.")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "value", _finite_real(self.value, "history amplitude"))

    def to_dict(self) -> dict[str, float]:
        return {"time_s": self.time_s, "value": self.value}


@dataclass(frozen=True, slots=True)
class HarmonicAmplitude:
    """A frequency-domain coefficient, with Hz converted once at construction."""

    frequency_hz: float
    phasor: ComplexPhasor
    angular_frequency_rad_s: float = field(init=False)

    def __post_init__(self) -> None:
        frequency = _finite_real(self.frequency_hz, "frequency_hz")
        if frequency < 0.0:
            raise InputValidationError("Excitation frequency_hz must be non-negative.")
        if not isinstance(self.phasor, ComplexPhasor):
            raise InputValidationError("Harmonic amplitude requires a ComplexPhasor.")
        angular_frequency = 2.0 * math.pi * frequency
        if not math.isfinite(angular_frequency):
            raise InputValidationError("Resolved angular frequency must be finite.")
        object.__setattr__(self, "frequency_hz", frequency)
        object.__setattr__(self, "angular_frequency_rad_s", angular_frequency)

    def to_dict(self) -> dict[str, object]:
        return {
            "frequency_hz": self.frequency_hz,
            "frequency_unit": "Hz",
            "angular_frequency_rad_s": self.angular_frequency_rad_s,
            "phasor": self.phasor.to_dict(),
            "phase_convention": _PHASE_CONVENTION,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "HarmonicAmplitude":
        if set(payload) != {"frequency_hz", "frequency_unit", "angular_frequency_rad_s", "phasor", "phase_convention"}:
            raise InputValidationError("Harmonic amplitude has an unsupported or incomplete serialized contract.")
        if payload["frequency_unit"] != "Hz" or payload["phase_convention"] != _PHASE_CONVENTION:
            raise InputValidationError("Harmonic amplitude has an unsupported frequency or phase convention.")
        phasor_data = payload["phasor"]
        if not isinstance(phasor_data, Mapping):
            raise InputValidationError("Harmonic phasor must be an object with real/imag fields.")
        result = cls(payload["frequency_hz"], ComplexPhasor.from_dict(phasor_data))  # type: ignore[arg-type]
        declared_omega = _finite_real(payload["angular_frequency_rad_s"], "angular_frequency_rad_s")
        if declared_omega != result.angular_frequency_rad_s:
            raise InputValidationError("Serialized angular frequency does not match 2*pi*frequency_hz.")
        return result


@dataclass(frozen=True, slots=True)
class ExcitationChannel:
    """One uniquely named real spatial distribution and one temporal signal."""

    channel_id: str
    spatial_distribution: tuple[SpatialDofWeight, ...]
    spatial_units: str
    amplitude_units: str
    result_units: str
    frame_convention: str
    sign_convention: str
    constant_amplitude: float | None = 1.0
    time_history: tuple[TimeSample, ...] = ()
    harmonic: HarmonicAmplitude | None = None
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.channel_id, str) or not self.channel_id.strip():
            raise InputValidationError("Excitation channel_id must be a non-empty stable string.")
        object.__setattr__(self, "channel_id", self.channel_id.strip())
        for name in ("spatial_units", "amplitude_units", "result_units", "frame_convention", "sign_convention"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InputValidationError(f"Excitation channel {name} must be explicit and non-empty.")
            object.__setattr__(self, name, value.strip())

        weights = tuple(_coerce_weight(item) for item in self.spatial_distribution)
        if not weights:
            raise InputValidationError("Excitation channel spatial_distribution must not be empty.")
        canonical = _canonical_weights(weights)
        object.__setattr__(self, "spatial_distribution", canonical)

        history = tuple(item if isinstance(item, TimeSample) else TimeSample(*item) for item in self.time_history)
        if any(right.time_s <= left.time_s for left, right in zip(history, history[1:])):
            raise InputValidationError("Excitation history times must be strictly increasing.")
        object.__setattr__(self, "time_history", history)

        signal_count = int(self.constant_amplitude is not None) + int(bool(history)) + int(self.harmonic is not None)
        if signal_count != 1:
            raise InputValidationError(
                "A channel must define exactly one constant, time-history, or harmonic amplitude."
            )
        if self.constant_amplitude is not None:
            object.__setattr__(self, "constant_amplitude", _finite_real(self.constant_amplitude, "constant_amplitude"))
        if self.harmonic is not None and not isinstance(self.harmonic, HarmonicAmplitude):
            raise InputValidationError("harmonic must be a HarmonicAmplitude.")

        provenance = _canonical_provenance(self.provenance)
        object.__setattr__(self, "provenance", provenance)

    @property
    def signal_kind(self) -> str:
        if self.harmonic is not None:
            return "harmonic_phasor"
        if self.time_history:
            return "real_time_history"
        return "real_constant"

    @property
    def is_zero(self) -> bool:
        if all(weight.value == 0.0 for weight in self.spatial_distribution):
            return True
        if self.constant_amplitude == 0.0:
            return True
        if self.time_history and all(sample.value == 0.0 for sample in self.time_history):
            return True
        return self.harmonic is not None and self.harmonic.phasor.real == 0.0 and self.harmonic.phasor.imag == 0.0

    def amplitude_at(self, time_s: float) -> float:
        time = _finite_real(time_s, "time_s")
        if time < 0.0:
            raise InputValidationError("time_s must be non-negative.")
        if self.harmonic is not None:
            raise InputValidationError("A harmonic phasor is not a real time-history amplitude.")
        if self.constant_amplitude is not None:
            return self.constant_amplitude
        if time <= self.time_history[0].time_s:
            return self.time_history[0].value
        if time >= self.time_history[-1].time_s:
            return self.time_history[-1].value
        for left, right in zip(self.time_history, self.time_history[1:]):
            if left.time_s <= time <= right.time_s:
                fraction = (time - left.time_s) / (right.time_s - left.time_s)
                return left.value + fraction * (right.value - left.value)
        raise AssertionError("validated time history did not contain the requested interval")

    def to_dict(self) -> dict[str, object]:
        signal: dict[str, object]
        if self.harmonic is not None:
            signal = {"kind": "harmonic_phasor", "value": self.harmonic.to_dict()}
        elif self.time_history:
            signal = {
                "kind": "real_time_history",
                "time_unit": "s",
                "interpolation": "piecewise_linear_endpoint_hold",
                "samples": [sample.to_dict() for sample in self.time_history],
            }
        else:
            signal = {"kind": "real_constant", "value": self.constant_amplitude}
        return {
            "channel_id": self.channel_id,
            "spatial_distribution": [weight.to_dict() for weight in self.spatial_distribution],
            "spatial_units": self.spatial_units,
            "amplitude_units": self.amplitude_units,
            "result_units": self.result_units,
            "frame_convention": self.frame_convention,
            "sign_convention": self.sign_convention,
            "temporal_signal": signal,
            "provenance": {key: value for key, value in self.provenance},
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ExcitationChannel":
        expected = {
            "channel_id",
            "spatial_distribution",
            "spatial_units",
            "amplitude_units",
            "result_units",
            "frame_convention",
            "sign_convention",
            "temporal_signal",
            "provenance",
        }
        if set(payload) != expected:
            raise InputValidationError("Excitation channel has an unsupported or incomplete serialized contract.")
        raw_weights = payload["spatial_distribution"]
        raw_signal = payload["temporal_signal"]
        raw_provenance = payload["provenance"]
        if (
            not isinstance(raw_weights, list)
            or not isinstance(raw_signal, Mapping)
            or not isinstance(raw_provenance, Mapping)
        ):
            raise InputValidationError("Excitation channel distribution, signal and provenance must be objects/lists.")
        weights = tuple(_weight_from_dict(item) for item in raw_weights)
        channel_id = _required_string(payload["channel_id"], "channel_id")
        spatial_units = _required_string(payload["spatial_units"], "spatial_units")
        amplitude_units = _required_string(payload["amplitude_units"], "amplitude_units")
        result_units = _required_string(payload["result_units"], "result_units")
        frame_convention = _required_string(payload["frame_convention"], "frame_convention")
        sign_convention = _required_string(payload["sign_convention"], "sign_convention")
        provenance = _canonical_provenance(raw_provenance)
        kind = raw_signal.get("kind")
        if kind == "real_constant" and set(raw_signal) == {"kind", "value"}:
            return cls(
                channel_id,
                weights,
                spatial_units,
                amplitude_units,
                result_units,
                frame_convention,
                sign_convention,
                constant_amplitude=_finite_real(raw_signal["value"], "constant_amplitude"),
                provenance=provenance,
            )
        if kind == "real_time_history" and set(raw_signal) == {"kind", "time_unit", "interpolation", "samples"}:
            raw_samples = raw_signal["samples"]
            if raw_signal["time_unit"] != "s" or raw_signal["interpolation"] != "piecewise_linear_endpoint_hold":
                raise InputValidationError("Unsupported excitation history time or interpolation convention.")
            if not isinstance(raw_samples, list):
                raise InputValidationError("Excitation history samples must be a list.")
            samples = tuple(_sample_from_dict(item) for item in raw_samples)
            if not samples:
                raise InputValidationError("Excitation history must contain at least one sample.")
            return cls(
                channel_id,
                weights,
                spatial_units,
                amplitude_units,
                result_units,
                frame_convention,
                sign_convention,
                constant_amplitude=None,
                time_history=samples,
                provenance=provenance,
            )
        if kind == "harmonic_phasor" and set(raw_signal) == {"kind", "value"}:
            raw_harmonic = raw_signal["value"]
            if not isinstance(raw_harmonic, Mapping):
                raise InputValidationError("Harmonic temporal signal must be an object.")
            return cls(
                channel_id,
                weights,
                spatial_units,
                amplitude_units,
                result_units,
                frame_convention,
                sign_convention,
                constant_amplitude=None,
                harmonic=HarmonicAmplitude.from_dict(raw_harmonic),
                provenance=provenance,
            )
        raise InputValidationError(f"Unsupported excitation temporal signal kind {kind!r}.")


class ExcitationChannelSet:
    """Canonical immutable set of identified channels, independent of K/M."""

    def __init__(
        self,
        channels: Iterable[ExcitationChannel] = (),
        *,
        source_mode: str = "explicit",
        legacy_controls: Mapping[str, object] | None = None,
        legacy_operator_identity: str | None = None,
    ) -> None:
        parsed = tuple(channels)
        if any(not isinstance(channel, ExcitationChannel) for channel in parsed):
            raise InputValidationError("ExcitationChannelSet accepts only ExcitationChannel entries.")
        ids = [channel.channel_id for channel in parsed]
        if len(set(ids)) != len(ids):
            raise InputValidationError("Excitation channel IDs must be unique within a channel set.")
        self._channels = tuple(sorted(parsed, key=lambda channel: channel.channel_id))
        if self._channels:
            common_contract = (
                self._channels[0].spatial_units,
                self._channels[0].amplitude_units,
                self._channels[0].result_units,
                self._channels[0].frame_convention,
                self._channels[0].sign_convention,
            )
            for channel in self._channels[1:]:
                contract = (
                    channel.spatial_units,
                    channel.amplitude_units,
                    channel.result_units,
                    channel.frame_convention,
                    channel.sign_convention,
                )
                if contract != common_contract:
                    raise InputValidationError(
                        "Channels with incompatible units, frames, or sign conventions cannot be superposed."
                    )
        if source_mode not in {"explicit", "legacy_adapter"}:
            raise InputValidationError("Unsupported excitation source_mode.")
        if source_mode == "legacy_adapter" and not legacy_operator_identity:
            raise InputValidationError("A legacy adapter must be tied to its source operator identity.")
        self._source_mode = source_mode
        self._legacy_operator_identity = legacy_operator_identity
        self._legacy_controls = _json_snapshot(dict(legacy_controls or {}), "legacy excitation controls")
        if source_mode == "explicit" and (self._legacy_controls or legacy_operator_identity is not None):
            raise InputValidationError(
                "Explicit channel sets cannot carry ignored legacy controls or operator bindings."
            )
        self._identity = checkpoint_signature(self._identity_payload(), label="Excitation identity")

    @property
    def channels(self) -> tuple[ExcitationChannel, ...]:
        return self._channels

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def source_mode(self) -> str:
        return self._source_mode

    @property
    def zero_channel_ids(self) -> tuple[str, ...]:
        return tuple(channel.channel_id for channel in self._channels if channel.is_zero)

    @property
    def memory_estimate_bytes(self) -> int:
        """Approximate immutable Python payload size, excluding interpreter overhead."""
        return sum(24 * len(channel.spatial_distribution) for channel in self._channels)

    def _identity_payload(self) -> dict[str, object]:
        return {
            "identity_domain": _IDENTITY_DOMAIN,
            "identity_schema_version": 1,
            "source_mode": self._source_mode,
            "legacy_operator_identity": self._legacy_operator_identity,
            "legacy_controls": _json_snapshot(self._legacy_controls, "legacy excitation controls"),
            "channels": [channel.to_dict() for channel in self._channels],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ExcitationChannelSet":
        if set(payload) != {
            "schema",
            "source_mode",
            "channels",
            "legacy_controls",
            "legacy_operator_identity",
            "identity",
        }:
            raise InputValidationError("Excitation channel set has an unsupported or incomplete serialized contract.")
        if payload["schema"] != CHANNEL_SCHEMA:
            raise InputValidationError(f"Unsupported excitation channel schema {payload['schema']!r}.")
        raw_channels = payload["channels"]
        raw_controls = payload["legacy_controls"]
        if not isinstance(raw_channels, list) or not isinstance(raw_controls, Mapping):
            raise InputValidationError("Serialized excitation channels or legacy controls have invalid types.")
        channels = tuple(ExcitationChannel.from_dict(item) for item in raw_channels if isinstance(item, Mapping))
        if len(channels) != len(raw_channels):
            raise InputValidationError("Every serialized excitation channel must be an object.")
        result = cls(
            channels,
            source_mode=str(payload["source_mode"]),
            legacy_controls=raw_controls,
            legacy_operator_identity=(
                str(payload["legacy_operator_identity"]) if payload["legacy_operator_identity"] else None
            ),
        )
        if payload["identity"] != result.identity:
            raise InputValidationError("Serialized excitation identity does not match its channel content.")
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CHANNEL_SCHEMA,
            "source_mode": self._source_mode,
            "channels": [channel.to_dict() for channel in self._channels],
            "legacy_controls": self._legacy_controls,
            "legacy_operator_identity": self._legacy_operator_identity,
            "identity": self.identity,
        }

    @classmethod
    def from_legacy_model(
        cls,
        model: FiniteElementModel,
        prepared: PreparedDynamicSystem,
        *,
        assembler: GlobalAssembler | None = None,
    ) -> "ExcitationChannelSet":
        """Adapt legacy nodal/distributed loads without changing their semantics."""
        if not isinstance(model, FiniteElementModel) or not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("Legacy excitation adaptation requires a model and PreparedDynamicSystem.")
        if model.analysis.parameters.get("excitation_channels") is not None:
            raise InputValidationError("Embedded new channels are unsupported in legacy model parameters.")
        prepared.require_compatible(model)
        dofs = model.dof_manager()
        signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
        if signature != prepared.dof_signature:
            raise InputValidationError("Legacy load mapping does not match the prepared physical DOF map.")
        vectors = (assembler or GlobalAssembler()).assemble_load_vectors(model, dofs)
        params = model.analysis.parameters
        validate_per_load_factors(params.get("load_factors_by_load"), len(vectors))
        channels: list[ExcitationChannel] = []
        reverse_map: dict[int, tuple[int, str]] = {}
        position = 0
        for node, names in sorted(dofs.node_dofs.items()):
            for name in DOF_ORDER:
                if name in names:
                    reverse_map[position] = (node, name)
                    position += 1
        for index, vector in enumerate(vectors):
            source_kind = "nodal" if index < len(model.loads) else "distributed"
            raw_definition = (
                model.loads[index] if source_kind == "nodal" else model.distributed_loads[index - len(model.loads)]
            )
            if not is_dataclass(raw_definition):
                raise InputValidationError("Legacy load adapter requires typed, immutable load definitions.")
            source_digest = checkpoint_signature(
                {"source_kind": source_kind, "definition": asdict(cast(Any, raw_definition))},
                label="Legacy excitation source",
            )
            components = tuple(
                SpatialDofWeight(node, dof, float(vector[dof_index]))
                for dof_index, (node, dof) in reverse_map.items()
                if vector[dof_index] != 0.0
            )
            if not components:
                # A zero historical load remains an identified, explicit no-op.
                node, names = next(iter(sorted(dofs.node_dofs.items())))
                components = (SpatialDofWeight(node, names[0], 0.0),)
            channels.append(
                ExcitationChannel(
                    channel_id=f"legacy:{source_kind}:{index if source_kind == 'nodal' else index - len(model.loads)}",
                    spatial_distribution=components,
                    spatial_units="model_force",
                    amplitude_units="dimensionless",
                    result_units="model_force",
                    frame_convention="global_model_frame",
                    sign_convention="positive_along_named_global_dof",
                    constant_amplitude=1.0,
                    provenance=(
                        ("adapter", "legacy_loads/v1"),
                        ("legacy_index", str(index)),
                        ("source_definition_sha256", source_digest),
                    ),
                )
            )
        controls = {key: params[key] for key in _LEGACY_CONTROL_KEYS if key in params}
        return cls(
            channels,
            source_mode="legacy_adapter",
            legacy_controls=controls,
            legacy_operator_identity=prepared.operator_identity,
        )

    @classmethod
    def from_model_inputs(
        cls,
        model: FiniteElementModel,
        prepared: PreparedDynamicSystem,
        *,
        explicit_channels: Iterable[ExcitationChannel] | None = None,
        assembler: GlobalAssembler | None = None,
    ) -> "ExcitationChannelSet":
        """Resolve one input syntax; mixed legacy/new inputs fail closed."""
        if model.analysis.parameters.get("excitation_channels") is not None:
            raise InputValidationError("New channels must be passed explicitly, not embedded in legacy parameters.")
        legacy_present = bool(model.loads or model.distributed_loads)
        new_present = explicit_channels is not None
        if legacy_present and new_present:
            raise InputValidationError(
                "Legacy loads and explicit channels cannot coexist without a separately authorized disjoint-channel contract."
            )
        if new_present and any(key in model.analysis.parameters for key in _LEGACY_CONTROL_KEYS):
            raise InputValidationError(
                "Explicit channels cannot coexist with legacy temporal load controls in model parameters."
            )
        if legacy_present:
            return cls.from_legacy_model(model, prepared, assembler=assembler)
        prepared.require_compatible(model)
        return cls(explicit_channels if explicit_channels is not None else ())

    def bind(self, prepared: PreparedDynamicSystem) -> "BoundExcitationChannels":
        if not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("Excitation channels can bind only to a PreparedDynamicSystem.")
        if self._source_mode == "legacy_adapter" and prepared.operator_identity != self._legacy_operator_identity:
            raise InputValidationError("Legacy distributed-load channels are bound to a different prepared operator.")
        dofs = _dof_manager_from_signature(prepared.dof_signature)
        rows: list[int] = []
        cols: list[int] = []
        values: list[float] = []
        for column, channel in enumerate(self._channels):
            for weight in channel.spatial_distribution:
                try:
                    row = dofs.index(weight.node, weight.dof)
                except ValueError as exc:
                    raise InputValidationError(
                        f"Channel {channel.channel_id!r} maps to inactive DOF {weight.dof} at node {weight.node}."
                    ) from exc
                rows.append(row)
                cols.append(column)
                values.append(weight.value)
        distribution = csc_matrix((values, (rows, cols)), shape=(dofs.ndof, len(self._channels)), dtype=np.float64)
        distribution.sum_duplicates()
        distribution.eliminate_zeros()
        distribution.sort_indices()
        return BoundExcitationChannels(
            channels=self._channels,
            channel_identity=self.identity,
            source_mode=self._source_mode,
            legacy_controls=self._legacy_controls,
            legacy_operator_identity=self._legacy_operator_identity,
            operator_identity=prepared.operator_identity,
            dof_signature=prepared.dof_signature,
            distribution=distribution,
        )


class BoundExcitationChannels:
    """Sparse channel-to-DOF map bound to one exact prepared operator."""

    def __init__(
        self,
        *,
        channels: tuple[ExcitationChannel, ...],
        channel_identity: str,
        source_mode: str,
        legacy_controls: Mapping[str, object],
        legacy_operator_identity: str | None,
        operator_identity: str,
        dof_signature: tuple[tuple[int, tuple[str, ...]], ...],
        distribution: csc_matrix,
    ) -> None:
        self._channels = channels
        self.channel_identity = channel_identity
        self.source_mode = source_mode
        self._legacy_controls = _json_snapshot(dict(legacy_controls), "legacy excitation controls")
        self._legacy_operator_identity = legacy_operator_identity
        self.operator_identity = operator_identity
        self.dof_signature = dof_signature
        self._distribution = csc_matrix(distribution, dtype=np.float64, copy=True)
        self._distribution.data.setflags(write=False)
        self._distribution.indices.setflags(write=False)
        self._distribution.indptr.setflags(write=False)

    @property
    def channel_count(self) -> int:
        return len(self._channels)

    @property
    def dof_count(self) -> int:
        return int(self._distribution.shape[0])

    @property
    def distribution_storage_bytes(self) -> int:
        matrix = self._distribution
        return int(matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes)

    @property
    def distribution_nnz(self) -> int:
        return int(self._distribution.nnz)

    def full_real_rhs(
        self,
        prepared: PreparedDynamicSystem,
        *,
        time_s: float,
        step: int = 0,
        steps: int = 1,
        dt: float = 0.01,
    ) -> np.ndarray:
        self._require_prepared(prepared)
        time = _finite_real(time_s, "time_s")
        if time < 0.0:
            raise InputValidationError("time_s must be non-negative.")
        coefficients = self._real_coefficients(time, step=step, steps=steps, dt=dt)
        result = np.asarray(self._distribution @ coefficients, dtype=np.float64).ravel()
        if not np.all(np.isfinite(result)):
            raise InputValidationError("Composed real excitation RHS contains non-finite values.")
        return result

    def full_harmonic_rhs(
        self,
        prepared: PreparedDynamicSystem,
        *,
        frequency_hz: float | None = None,
    ) -> np.ndarray:
        self._require_prepared(prepared)
        harmonic = [channel.harmonic for channel in self._channels]
        legacy_real_loads = self.source_mode == "legacy_adapter" and all(
            item is None and channel.constant_amplitude == 1.0
            for item, channel in zip(harmonic, self._channels, strict=True)
        )
        if any(item is None for item in harmonic) and not legacy_real_loads:
            raise InputValidationError("Harmonic RHS requires every channel to carry a complex phasor.")
        _resolve_frequency(harmonic, frequency_hz)
        coefficients = (
            np.ones(len(self._channels), dtype=np.complex128)
            if legacy_real_loads
            else np.asarray(
                [channel.harmonic.phasor.value for channel in self._channels if channel.harmonic is not None],
                dtype=np.complex128,
            )
        )
        result = np.asarray(self._distribution @ coefficients, dtype=np.complex128).ravel()
        if result.shape != (self.dof_count,) or not np.all(np.isfinite(result)):
            raise InputValidationError("Composed complex excitation RHS has invalid dimensions or non-finite values.")
        return result

    def reduced_real_rhs(
        self,
        prepared: PreparedDynamicSystem,
        *,
        time_s: float,
        step: int = 0,
        steps: int = 1,
        dt: float = 0.01,
    ) -> np.ndarray:
        full = self.full_real_rhs(prepared, time_s=time_s, step=step, steps=steps, dt=dt)
        return np.asarray(prepared.reduce_load(full))

    def reduced_harmonic_rhs(
        self,
        prepared: PreparedDynamicSystem,
        *,
        frequency_hz: float | None = None,
    ) -> np.ndarray:
        return np.asarray(prepared.reduce_load(self.full_harmonic_rhs(prepared, frequency_hz=frequency_hz)))

    def _real_coefficients(self, time_s: float, *, step: int, steps: int, dt: float) -> np.ndarray:
        if any(channel.harmonic is not None for channel in self._channels):
            raise InputValidationError("Harmonic phasors cannot be silently converted into real time amplitudes.")
        if isinstance(step, bool) or int(step) != step or step < 0:
            raise InputValidationError("step must be a non-negative integer.")
        if isinstance(steps, bool) or int(steps) != steps or steps < 1:
            raise InputValidationError("steps must be a positive integer.")
        interval = _finite_real(dt, "dt")
        if interval <= 0.0:
            raise InputValidationError("dt must be positive.")
        coefficients = np.asarray([channel.amplitude_at(time_s) for channel in self._channels], dtype=np.float64)
        if self.source_mode == "legacy_adapter" and self._channels:
            # Reuse the exact historical Newmark factor semantics, including
            # per-load factors, without changing the solver route.
            from solveur.core.analyses.dynamic import (
                NewmarkDynamicSolver,
                _validate_load_function,
                _validate_load_table,
            )

            solver = NewmarkDynamicSolver()
            params = dict(self._legacy_controls)
            _validate_load_table(params.get("load_table"))
            _validate_load_function(params)
            factors = solver._component_load_factors(
                params, int(step), time_s, int(steps), interval, len(self._channels)
            )
            coefficients *= np.asarray(factors, dtype=np.float64)
        if not np.all(np.isfinite(coefficients)):
            raise InputValidationError("Real excitation amplitudes must be finite.")
        return coefficients

    def _require_prepared(self, prepared: PreparedDynamicSystem) -> None:
        if not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("Bound excitation channels require their PreparedDynamicSystem.")
        if prepared.operator_identity != self.operator_identity or prepared.dof_signature != self.dof_signature:
            raise InputValidationError("Bound excitation channels do not match these prepared operators/DOF mappings.")
        if self._legacy_operator_identity is not None and prepared.operator_identity != self._legacy_operator_identity:
            raise InputValidationError("Legacy distributed-load integration is stale for these prepared operators.")


def _resolve_frequency(harmonic: list[HarmonicAmplitude | None], requested: float | None) -> float | None:
    values = [item.frequency_hz for item in harmonic if item is not None]
    if requested is not None:
        requested_value = _finite_real(requested, "frequency_hz")
        if requested_value < 0.0:
            raise InputValidationError("frequency_hz must be non-negative.")
        if any(value != requested_value for value in values):
            raise InputValidationError("Requested frequency_hz conflicts with a channel phasor frequency.")
        return requested_value
    if not values:
        raise InputValidationError("An empty harmonic channel set requires an explicit frequency_hz.")
    if any(value != values[0] for value in values[1:]):
        raise InputValidationError("One harmonic RHS cannot combine channels with different frequencies.")
    return values[0]


def _dof_manager_from_signature(signature: tuple[tuple[int, tuple[str, ...]], ...]) -> DofManager:
    requirements = {int(node): set(names) for node, names in signature}
    result = DofManager.from_node_requirements(requirements)
    actual = tuple(sorted((int(node), tuple(names)) for node, names in result.node_dofs.items()))
    if actual != signature:
        raise InputValidationError("Prepared dynamic DOF signature is not canonical.")
    return result


def _coerce_weight(value: object) -> SpatialDofWeight:
    if isinstance(value, SpatialDofWeight):
        return value
    if isinstance(value, Mapping):
        return _weight_from_dict(value)
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return SpatialDofWeight(cast(int, value[0]), cast(str, value[1]), cast(float, value[2]))
    raise InputValidationError("Spatial distribution entries must be SpatialDofWeight or (node,dof,value).")


def _weight_from_dict(payload: object) -> SpatialDofWeight:
    if not isinstance(payload, Mapping) or set(payload) != {"node", "dof", "value"}:
        raise InputValidationError("Spatial DOF weight must contain exactly node, dof and value.")
    return SpatialDofWeight(
        cast(int, payload["node"]),
        cast(str, payload["dof"]),
        cast(float, payload["value"]),
    )


def _sample_from_dict(payload: object) -> TimeSample:
    if not isinstance(payload, Mapping) or set(payload) != {"time_s", "value"}:
        raise InputValidationError("Time sample must contain exactly time_s and value.")
    return TimeSample(cast(float, payload["time_s"]), cast(float, payload["value"]))


def _canonical_weights(weights: tuple[SpatialDofWeight, ...]) -> tuple[SpatialDofWeight, ...]:
    aggregated: dict[tuple[int, str], float] = {}
    for item in weights:
        key = (item.node, item.dof)
        aggregated[key] = aggregated.get(key, 0.0) + item.value
        if not math.isfinite(aggregated[key]):
            raise InputValidationError("Summed spatial distribution is non-finite.")
    return tuple(SpatialDofWeight(node, dof, value) for (node, dof), value in sorted(aggregated.items()))


def _canonical_provenance(value: object) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        raw_entries: list[object] = list(value.items())
    else:
        try:
            raw_entries = list(cast(Iterable[object], value))
        except TypeError as exc:
            raise InputValidationError("Channel provenance must be string key/value pairs.") from exc
    normalized: dict[str, str] = {}
    for entry in raw_entries:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise InputValidationError("Channel provenance must be string key/value pairs.")
        key, item = entry
        if not isinstance(key, str) or not key.strip() or not isinstance(item, str):
            raise InputValidationError("Channel provenance must use non-empty string keys and string values.")
        if key in normalized:
            raise InputValidationError(f"Duplicate channel provenance key {key!r}.")
        normalized_key = key.lower().replace("-", "_")
        if any(
            token in normalized_key for token in ("timestamp", "created_at", "output_path", "temp_path", "process_id")
        ):
            raise InputValidationError(
                "Operational timestamps, temporary paths and process IDs are not channel provenance identity."
            )
        if re.match(r"^(?:[a-zA-Z]:[\\/]|[/\\]{1,2})", item) or re.search(
            r"(?:^|[/\\])(?:temp|tmp)(?:[/\\]|$)", item, re.IGNORECASE
        ):
            raise InputValidationError(
                "Channel provenance must use a relative/public identifier, not a local or temporary path."
            )
        normalized[key] = item
    return tuple(sorted(normalized.items()))


def _json_snapshot(value: object, label: str) -> dict[str, object]:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        result = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be finite JSON data.") from exc
    if not isinstance(result, dict):
        raise InputValidationError(f"{label} must be an object.")
    return result


def _finite_real(value: object, label: str) -> float:
    if isinstance(value, (bool, complex, np.complexfloating)):
        raise InputValidationError(f"{label} must be a finite real scalar, not complex or boolean.")
    try:
        result = float(cast(Any, value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"{label} must be a finite real scalar.") from exc
    if not math.isfinite(result):
        raise InputValidationError(f"{label} must be finite.")
    return result


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{label} must be a non-empty string.")
    return value
