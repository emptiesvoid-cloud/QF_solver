"""Contract and prepared load for bounded uniform base acceleration (WP07).

The input is deliberately separate from force channels: it is a prescribed
kinematic excitation whose equivalent inertia is formed from the complete
assembled mass before the fixed-coordinate reduction.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np
from scipy.sparse import csr_matrix, eye

from solveur.core.analyses.excitation_channels import TimeSample
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.checkpoint_common import checkpoint_signature


UNIFORM_BASE_ACCELERATION_SCHEMA = "qf-uniform-base-acceleration/v1"
_SUPPORT_POLICY = "all_homogeneous_fixed_supports_comoving"
_GROUND_SPRING_POLICY = "COMOVING_WITH_BASE"
_INTERPOLATION = "linear_endpoint_hold"
_PHASE_CONVENTION = "a_g(t) = Re[A_g exp(+i*omega*t)]"


@dataclass(frozen=True, slots=True)
class UniformBaseAcceleration:
    """Immutable unit-resolved translational base-acceleration input."""

    direction: tuple[float, float, float]
    route: str
    harmonic_phasors: tuple[tuple[float, complex], ...] = ()
    time_history: tuple[TimeSample, ...] = ()
    grounded_spring_policy: str | None = None

    @classmethod
    def from_mapping(
        cls,
        value: object,
        *,
        route: str,
        model: FiniteElementModel,
    ) -> "UniformBaseAcceleration":
        if route not in {"harmonic", "transient"}:
            raise InputValidationError("Uniform base acceleration is only defined for WP07 harmonic/transient routes.")
        if not isinstance(value, Mapping):
            raise InputValidationError("uniform_base_acceleration must be an explicit object.")

        common = {
            "schema",
            "direction",
            "direction_frame",
            "acceleration_unit",
            "support_policy",
        }
        route_field = "harmonic_phasors" if route == "harmonic" else "time_history"
        allowed = common | {route_field, "grounded_spring_policy"}
        unknown = sorted(str(key) for key in set(value).difference(allowed))
        missing = sorted((common | {route_field}) - set(value))
        if unknown or missing:
            detail = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if unknown:
                detail.append("unsupported " + ", ".join(unknown))
            raise InputValidationError("Invalid uniform_base_acceleration fields: " + "; ".join(detail) + ".")
        if value.get("schema") != UNIFORM_BASE_ACCELERATION_SCHEMA:
            raise InputValidationError("Unsupported uniform base-acceleration schema.")
        if value.get("direction_frame") != "global_model_axes":
            raise InputValidationError("Base-acceleration direction_frame must be 'global_model_axes'.")
        if value.get("acceleration_unit") != "m/s^2":
            raise InputValidationError("Base acceleration must use the explicit SI unit 'm/s^2'.")
        if value.get("support_policy") != _SUPPORT_POLICY:
            raise InputValidationError("WP07 requires support_policy='all_homogeneous_fixed_supports_comoving'.")
        if not model.fixed_dofs:
            raise InputValidationError("WP07 requires explicit homogeneous fixed supports to define the moving base.")

        raw_direction = value.get("direction")
        if not isinstance(raw_direction, (list, tuple)) or len(raw_direction) != 3:
            raise InputValidationError("Base-acceleration direction must be a unit 3-vector in global axes.")
        direction = (
            _finite_real(raw_direction[0], "direction component"),
            _finite_real(raw_direction[1], "direction component"),
            _finite_real(raw_direction[2], "direction component"),
        )
        norm = float(np.linalg.norm(direction))
        if not math.isfinite(norm) or abs(norm - 1.0) > 1.0e-12:
            raise InputValidationError("Base-acceleration direction must already be normalized to unit length.")

        grounded_springs = [spring for spring in model.springs if spring.node_b is None]
        spring_policy_raw = value.get("grounded_spring_policy")
        spring_policy: str | None
        if grounded_springs:
            if spring_policy_raw != _GROUND_SPRING_POLICY:
                raise InputValidationError(
                    "Ground-referenced springs require explicit grounded_spring_policy='COMOVING_WITH_BASE'; "
                    "fixed-in-absolute-frame references are outside WP07."
                )
            spring_policy = _GROUND_SPRING_POLICY
        else:
            if spring_policy_raw not in (None, _GROUND_SPRING_POLICY):
                raise InputValidationError("Unsupported grounded_spring_policy.")
            spring_policy = _GROUND_SPRING_POLICY if spring_policy_raw is not None else None

        if route == "harmonic":
            if "time_history" in value:
                raise InputValidationError("Harmonic base excitation cannot also contain a time history.")
            phasors = _parse_harmonic_phasors(value["harmonic_phasors"])
            history: tuple[TimeSample, ...] = ()
        else:
            if "harmonic_phasors" in value:
                raise InputValidationError("Transient base excitation cannot also contain harmonic phasors.")
            phasors = ()
            history = _parse_time_history(value["time_history"])

        return cls(
            direction=direction,
            route=route,
            harmonic_phasors=phasors,
            time_history=history,
            grounded_spring_policy=spring_policy,
        )

    @property
    def identity(self) -> str:
        return checkpoint_signature(self.identity_payload(), label="WP07 uniform base excitation identity")

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema": UNIFORM_BASE_ACCELERATION_SCHEMA,
            "route": self.route,
            "direction_global_unit_vector": list(self.direction),
            "direction_frame": "global_model_axes",
            "acceleration_unit": "m/s^2",
            "support_policy": _SUPPORT_POLICY,
            "grounded_spring_policy": self.grounded_spring_policy or "NOT_APPLICABLE",
            "phase_convention": _PHASE_CONVENTION if self.route == "harmonic" else "real_time_history",
            "harmonic_phasors": [
                {"frequency_hz": frequency, "real": value.real, "imag": value.imag}
                for frequency, value in self.harmonic_phasors
            ],
            "time_history": [sample.to_dict() for sample in self.time_history],
            "interpolation": _INTERPOLATION if self.route == "transient" else "NOT_APPLICABLE",
        }

    def phasor_at(self, frequency_hz: float) -> complex:
        if self.route != "harmonic":
            raise InputValidationError("A transient base-acceleration history has no harmonic phasor.")
        matches = [value for frequency, value in self.harmonic_phasors if frequency == frequency_hz]
        if len(matches) != 1:
            raise InputValidationError(
                f"Base-acceleration phasors must define requested frequency {frequency_hz:.17g} Hz exactly."
            )
        return matches[0]

    def acceleration_at(self, time_s: float) -> float:
        if self.route != "transient":
            raise InputValidationError("Harmonic base excitation cannot be sampled as a real time history.")
        time = _finite_real(time_s, "base-acceleration sample time")
        if time < 0.0:
            raise InputValidationError("Base-acceleration sample time must be non-negative.")
        if time <= self.time_history[0].time_s:
            return self.time_history[0].value
        if time >= self.time_history[-1].time_s:
            return self.time_history[-1].value
        for left, right in zip(self.time_history, self.time_history[1:]):
            if left.time_s <= time <= right.time_s:
                fraction = (time - left.time_s) / (right.time_s - left.time_s)
                return left.value + fraction * (right.value - left.value)
        raise AssertionError("Validated base acceleration history did not contain the requested interval.")


@dataclass(frozen=True, slots=True)
class PreparedBaseAcceleration:
    """Full and reduced inertial load directions prepared once for a solve."""

    specification: UniformBaseAcceleration
    influence_full: np.ndarray
    inertial_load_full_per_m_s2: np.ndarray
    inertial_load_reduced_per_m_s2: np.ndarray
    modal_load_per_m_s2: np.ndarray


def prepare_base_acceleration(
    specification: UniformBaseAcceleration,
    model: FiniteElementModel,
    prepared: PreparedDynamicSystem,
    modes: np.ndarray,
) -> PreparedBaseAcceleration:
    """Form ``-P.T M_full r`` before constraints, then project through Phi."""
    if not isinstance(specification, UniformBaseAcceleration):
        raise InputValidationError("WP07 requires a validated UniformBaseAcceleration specification.")
    prepared.require_compatible(model)
    dofs = model.dof_manager()
    signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
    if signature != prepared.dof_signature or dofs.ndof != prepared.mass_full.shape[0]:
        raise InputValidationError("WP07 physical DOF mapping does not match the prepared full mass operator.")

    reduction = prepared.reduction_transform.tocsr()
    free = np.asarray(prepared.free_dof_indices, dtype=int)
    if (
        prepared.reduced_size != free.size
        or reduction.shape != (free.size, free.size)
        or (reduction - eye(free.size, format="csr")).nnz
        and float(np.max(np.abs((reduction - eye(free.size, format="csr")).data), initial=0.0)) > 1.0e-13
        or int(prepared.assembly_diagnostics["reduction"].get("condensed_drilling_dof_count", 0)) != 0
    ):
        raise InputValidationError(
            "WP07 cannot construct its contracted physical-to-relative map for condensed/algebraic DOFs."
        )

    influence = np.zeros(dofs.ndof, dtype=np.float64)
    translation_component = {"UX": 0, "UY": 1, "UZ": 2}
    for node, names in dofs.node_dofs.items():
        for dof in names:
            component = translation_component.get(dof)
            if component is not None:
                influence[dofs.index(node, dof)] = specification.direction[component]
    if not np.all(np.isfinite(influence)):
        raise InputValidationError("WP07 influence vector contains non-finite values.")

    # With WP00's bounded non-condensed domain, P is the full-to-free selector.
    # Keep it explicit so constrained/free mass coupling is retained in P.T M r.
    projection = csr_matrix(
        (np.ones(free.size, dtype=np.float64), (free, np.arange(free.size, dtype=int))),
        shape=(dofs.ndof, free.size),
    )
    mass_full = prepared.mass_full
    inertial_mass_column = np.asarray(mass_full @ influence, dtype=np.float64).reshape(-1)
    full_load = -inertial_mass_column
    reduced_load = np.asarray(projection.T @ full_load, dtype=np.float64).reshape(-1)
    reducer_load = prepared.reduce_load(full_load)
    if reducer_load.shape != reduced_load.shape or not np.allclose(
        reducer_load, reduced_load, rtol=0.0, atol=1.0e-12 * max(1.0, float(np.linalg.norm(reduced_load)))
    ):
        raise InputValidationError("WP07 physical-to-relative projection disagrees with PreparedDynamicSystem.")

    mode_array = np.asarray(modes, dtype=np.float64)
    if mode_array.ndim != 2 or mode_array.shape[0] != prepared.reduced_size:
        raise InputValidationError("WP07 modal basis does not match the prepared reduced coordinate map.")
    modal_load = np.asarray(mode_array.T @ reduced_load, dtype=np.float64).reshape(-1)
    for array in (influence, full_load, reduced_load, modal_load):
        if not np.all(np.isfinite(array)):
            raise InputValidationError("WP07 prepared inertial load contains non-finite values.")
        array.setflags(write=False)
    return PreparedBaseAcceleration(specification, influence, full_load, reduced_load, modal_load)


def combined_excitation_identity(force_channel_identity: str, base: PreparedBaseAcceleration | None) -> str:
    """Bind WP03 force channels and WP07 base motion without conflating operators."""
    if base is None:
        return force_channel_identity
    return checkpoint_signature(
        {
            "schema": "qf-combined-excitation-identity/v1",
            "force_channel_identity": force_channel_identity,
            "uniform_base_acceleration_identity": base.specification.identity,
        },
        label="WP03 force channels plus WP07 base excitation",
    )


def _parse_harmonic_phasors(value: object) -> tuple[tuple[float, complex], ...]:
    if not isinstance(value, list) or not value:
        raise InputValidationError("harmonic_phasors must be a non-empty list.")
    parsed: list[tuple[float, complex]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"frequency_hz", "real", "imag"}:
            raise InputValidationError(f"harmonic_phasors[{index}] must contain exactly frequency_hz, real and imag.")
        frequency = _finite_real(item["frequency_hz"], f"harmonic_phasors[{index}].frequency_hz")
        real = _finite_real(item["real"], f"harmonic_phasors[{index}].real")
        imag = _finite_real(item["imag"], f"harmonic_phasors[{index}].imag")
        if frequency < 0.0:
            raise InputValidationError("Base-acceleration frequencies must be non-negative Hz values.")
        amplitude = complex(real, imag)
        if frequency == 0.0 and amplitude != 0.0j:
            raise InputValidationError("A nonzero harmonic base acceleration at 0 Hz is not admissible in WP07.")
        parsed.append((frequency, amplitude))
    if len({frequency for frequency, _ in parsed}) != len(parsed):
        raise InputValidationError("Base-acceleration harmonic frequencies must be unique.")
    return tuple(sorted(parsed, key=lambda item: item[0]))


def _parse_time_history(value: object) -> tuple[TimeSample, ...]:
    if not isinstance(value, Mapping) or set(value) != {"time_unit", "interpolation", "samples"}:
        raise InputValidationError("time_history must contain exactly time_unit, interpolation and samples.")
    if value["time_unit"] != "s" or value["interpolation"] != _INTERPOLATION:
        raise InputValidationError("WP07 time history requires seconds and linear_endpoint_hold interpolation.")
    raw_samples = value["samples"]
    if not isinstance(raw_samples, list) or not raw_samples:
        raise InputValidationError("Base-acceleration samples must be a non-empty list.")
    samples: list[TimeSample] = []
    for index, item in enumerate(raw_samples):
        if not isinstance(item, Mapping) or set(item) != {"time_s", "value"}:
            raise InputValidationError(f"time_history.samples[{index}] must contain exactly time_s and value.")
        samples.append(TimeSample(item["time_s"], item["value"]))
    if samples[0].time_s != 0.0:
        raise InputValidationError("WP07 base-acceleration history must explicitly start at t=0 s.")
    if any(right.time_s <= left.time_s for left, right in zip(samples, samples[1:])):
        raise InputValidationError("Base-acceleration history times must be strictly increasing.")
    return tuple(samples)


def _finite_real(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise InputValidationError(f"{name} must be a finite real number, not boolean.")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"{name} must be a finite real number.") from exc
    if not math.isfinite(result):
        raise InputValidationError(f"{name} must be finite.")
    return result
