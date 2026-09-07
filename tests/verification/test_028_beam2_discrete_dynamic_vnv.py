"""WP03B analytical V&V for the bounded BEAM2 and DISCRETE dynamic routes."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pytest

from qf_solver import FiniteElementModel, check_mesh, solve_model


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification/0_2_8/wp03b_dynamic_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp03b_maturity_matrix.json"

BEAM_LENGTH = 10.0
BEAM_E = 210.0e9
BEAM_NU = 0.3
BEAM_AREA = 0.01
BEAM_IY = 2.0e-6
BEAM_IZ = 3.0e-6
BEAM_J = 5.0e-6
BEAM_RHO = 7800.0
BEAM_U0 = 1.0e-3

DISCRETE_K = 1000.0
DISCRETE_M = 10.0
DISCRETE_U0 = 2.0e-2
DISCRETE_ZETA = 2.0e-2


def _load_evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _beam_frequency() -> float:
    """Return the independent axial one-element consistent-mass frequency."""
    return math.sqrt((BEAM_E * BEAM_AREA / BEAM_LENGTH) / (BEAM_RHO * BEAM_AREA * BEAM_LENGTH / 3.0))


def _beam_model(analysis: dict[str, object], *, load: float = 0.0) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=[[0.0, 0.0, 0.0], [BEAM_LENGTH, 0.0, 0.0]],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": BEAM_E,
                "nu": BEAM_NU,
                "A": BEAM_AREA,
                "Iy": BEAM_IY,
                "Iz": BEAM_IZ,
                "J": BEAM_J,
                "density": BEAM_RHO,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": load}] if load else [],
    )


def _discrete_model(analysis: dict[str, object], *, load: float = 0.0) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
        springs=[{"node_a": 0, "dofs": ["UX", "UY", "UZ"], "stiffness": [DISCRETE_K] * 3}],
        concentrated_masses=[{"node": 0, "mass": DISCRETE_M}],
        fixed_dofs=[{"node": 0, "dofs": ["UY", "UZ"]}],
        loads=[{"node": 0, "dof": "UX", "value": load}] if load else [],
    )


def _history_arrays(result: object, label: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    history = result.solver["time_history"]
    time = np.asarray([row["time"] for row in history], dtype=float)
    displacement = np.asarray([row["probes"][label]["displacement"] for row in history], dtype=float)
    velocity = np.asarray([row["probes"][label]["velocity"] for row in history], dtype=float)
    energy = np.asarray([row["total_energy"] for row in history], dtype=float)
    damping_power = np.asarray([row["damping_power"] for row in history], dtype=float)
    drift = np.asarray([row["relative_energy_drift"] for row in history], dtype=float)
    return time, displacement, velocity, energy, damping_power, drift


def _first_two_down_crossings(time: np.ndarray, displacement: np.ndarray) -> np.ndarray:
    crossings: list[float] = []
    for index in range(displacement.size - 1):
        left, right = displacement[index], displacement[index + 1]
        if left > 0.0 and right <= 0.0:
            fraction = left / (left - right)
            crossings.append(float(time[index] + fraction * (time[index + 1] - time[index])))
            if len(crossings) == 2:
                return np.asarray(crossings)
    raise AssertionError("The analytical V&V history did not contain two positive-to-negative crossings.")


def _wrapped_error(observed: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(np.angle(np.exp(1j * (observed - expected))))))


def _assert_observed(actual: Any, expected: Any, path: str = "") -> None:
    """Compare the recorded replay observation without pinning platform noise."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        assert set(actual) == set(expected), path
        for key, value in expected.items():
            _assert_observed(actual[key], value, f"{path}.{key}" if path else key)
    elif isinstance(expected, bool):
        assert actual is expected, path
    elif isinstance(expected, int):
        assert actual == expected, path
    else:
        assert actual == pytest.approx(expected, rel=1.0e-11, abs=1.0e-13), path


def _newmark_metrics(
    result: object,
    *,
    label: str,
    reference_displacement: Callable[[np.ndarray], np.ndarray],
    reference_velocity: Callable[[np.ndarray], np.ndarray],
    frequency_rad_s: float,
    displacement_scale: float,
    damped: bool,
) -> dict[str, float]:
    time, displacement, velocity, energy, damping_power, drift = _history_arrays(result, label)
    expected_displacement = reference_displacement(time)
    expected_velocity = reference_velocity(time)
    observed_phase = np.unwrap(np.arctan2(-velocity / frequency_rad_s, displacement))
    expected_phase = np.unwrap(np.arctan2(-expected_velocity / frequency_rad_s, expected_displacement))
    values: dict[str, float] = {
        "max_relative_displacement_error": float(np.max(np.abs(displacement - expected_displacement)) / displacement_scale),
        "max_relative_velocity_error": float(
            np.max(np.abs(velocity - expected_velocity)) / (displacement_scale * frequency_rad_s)
        ),
        "max_phase_error_rad": _wrapped_error(observed_phase, expected_phase),
        "measured_frequency_relative_error": abs(
            1.0 / float(np.diff(_first_two_down_crossings(time, displacement))[0]) / (frequency_rad_s / (2.0 * math.pi)) - 1.0
        ),
    }
    if not damped:
        amplitude = np.sqrt(displacement**2 + (velocity / frequency_rad_s) ** 2)
        values["max_relative_amplitude_error"] = float(np.max(np.abs(amplitude - displacement_scale)) / displacement_scale)
        values["max_relative_energy_drift"] = float(np.max(np.abs(drift)))
    else:
        dissipated = np.concatenate(
            [[0.0], np.cumsum(0.5 * (damping_power[1:] + damping_power[:-1]) * np.diff(time))]
        )
        values["max_relative_energy_balance_error"] = float(
            np.max(np.abs(energy + dissipated - energy[0])) / energy[0]
        )
        values["max_mechanical_energy_increase"] = float(np.max(np.diff(energy)))
        values["final_mechanical_energy_ratio"] = float(energy[-1] / energy[0])
    return values


def _beam_newmark_run() -> dict[str, Any]:
    omega = _beam_frequency()
    period = 2.0 * math.pi / omega

    def run(samples_per_period: int) -> dict[str, float]:
        model = _beam_model(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": period / samples_per_period,
                "steps": 4 * samples_per_period,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "initial_displacements": [{"node": 1, "dof": "UX", "value": BEAM_U0}],
                "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
                "history_probes": [{"node": 1, "dof": "UX", "label": "tip_ux"}],
                "postprocess_mode": "summary",
            }
        )
        assert check_mesh(model).status == "PASS"
        result = solve_model(model, enforce_policy=False)
        return _newmark_metrics(
            result,
            label="tip_ux",
            reference_displacement=lambda time: BEAM_U0 * np.cos(omega * time),
            reference_velocity=lambda time: -BEAM_U0 * omega * np.sin(omega * time),
            frequency_rad_s=omega,
            displacement_scale=BEAM_U0,
            damped=False,
        )

    coarse = run(40)
    fine = run(80)
    return {
        "natural_frequency_hz": omega / (2.0 * math.pi),
        "coarse": coarse,
        "fine": fine,
        "dt_displacement_error_ratio": coarse["max_relative_displacement_error"] and fine["max_relative_displacement_error"] / coarse["max_relative_displacement_error"],
        "dt_velocity_error_ratio": coarse["max_relative_velocity_error"] and fine["max_relative_velocity_error"] / coarse["max_relative_velocity_error"],
    }


def _discrete_newmark_run() -> dict[str, Any]:
    omega = math.sqrt(DISCRETE_K / DISCRETE_M)
    omega_d = omega * math.sqrt(1.0 - DISCRETE_ZETA**2)
    alpha = 2.0 * DISCRETE_ZETA * omega
    period = 2.0 * math.pi / omega

    def exact_displacement(time: np.ndarray) -> np.ndarray:
        return DISCRETE_U0 * np.exp(-DISCRETE_ZETA * omega * time) * (
            np.cos(omega_d * time) + DISCRETE_ZETA / math.sqrt(1.0 - DISCRETE_ZETA**2) * np.sin(omega_d * time)
        )

    def exact_velocity(time: np.ndarray) -> np.ndarray:
        return -DISCRETE_U0 * omega**2 / omega_d * np.exp(-DISCRETE_ZETA * omega * time) * np.sin(omega_d * time)

    def run(samples_per_period: int) -> dict[str, float]:
        model = _discrete_model(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": period / samples_per_period,
                "steps": 4 * samples_per_period,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
                "initial_displacements": [{"node": 0, "dof": "UX", "value": DISCRETE_U0}],
                "initial_velocities": [{"node": 0, "dof": "UX", "value": 0.0}],
                "history_probes": [{"node": 0, "dof": "UX", "label": "ux"}],
                "postprocess_mode": "summary",
            }
        )
        assert check_mesh(model).status in {"PASS", "WARNING"}
        result = solve_model(model, enforce_policy=False)
        return _newmark_metrics(
            result,
            label="ux",
            reference_displacement=exact_displacement,
            reference_velocity=exact_velocity,
            frequency_rad_s=omega_d,
            displacement_scale=DISCRETE_U0,
            damped=True,
        )

    coarse = run(80)
    fine = run(160)
    return {
        "natural_frequency_hz": omega / (2.0 * math.pi),
        "damped_frequency_hz": omega_d / (2.0 * math.pi),
        "rayleigh_alpha": alpha,
        "coarse": coarse,
        "fine": fine,
        "dt_displacement_error_ratio": fine["max_relative_displacement_error"] / coarse["max_relative_displacement_error"],
        "dt_velocity_error_ratio": fine["max_relative_velocity_error"] / coarse["max_relative_velocity_error"],
    }


def _harmonic_metrics(result: object, *, dof_index: int, stiffness: float, mass: float, alpha: float, frequencies_hz: list[float]) -> dict[str, Any]:
    observed = np.asarray(result.responses, dtype=complex)[:, dof_index]
    omega = 2.0 * math.pi * np.asarray(frequencies_hz)
    expected = 1.0 / (stiffness - mass * omega**2 + 1j * omega * alpha * mass)
    amplitude_error = np.abs(np.abs(observed) - np.abs(expected)) / np.abs(expected)
    phase_error = np.abs(np.angle(np.exp(1j * (np.angle(observed) - np.angle(expected)))))
    peak_index = int(np.argmax(np.abs(observed)))
    return {
        "max_relative_amplitude_error": float(np.max(amplitude_error)),
        "max_phase_error_rad": float(np.max(phase_error)),
        "max_relative_complex_response_error": float(np.max(np.abs(observed - expected) / np.abs(expected))),
        "max_relative_residual": float(result.solver["max_relative_residual_norm"]),
        "sampled_peak_frequency_hz": float(frequencies_hz[peak_index]),
        "sampled_peak_is_natural_frequency": peak_index == 3,
        "off_resonance_amplitude_ratio_low": float(abs(observed[3]) / abs(observed[1])),
        "off_resonance_amplitude_ratio_high": float(abs(observed[3]) / abs(observed[5])),
        "frequency_count": len(frequencies_hz),
    }


def _beam_harmonic_run() -> dict[str, Any]:
    omega_n = _beam_frequency()
    alpha = 2.0 * 2.0e-2 * omega_n
    frequencies_hz = [omega_n / (2.0 * math.pi) * ratio for ratio in (0.25, 0.5, 0.9, 1.0, 1.1, 1.5, 2.0)]
    model = _beam_model(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": frequencies_hz,
            "rayleigh_alpha": alpha,
            "rayleigh_beta": 0.0,
            "postprocess_mode": "summary",
        },
        load=1.0,
    )
    assert check_mesh(model).status == "PASS"
    result = solve_model(model, enforce_policy=False)
    return _harmonic_metrics(
        result,
        dof_index=result.dofs.index(1, "UX"),
        stiffness=BEAM_E * BEAM_AREA / BEAM_LENGTH,
        mass=BEAM_RHO * BEAM_AREA * BEAM_LENGTH / 3.0,
        alpha=alpha,
        frequencies_hz=frequencies_hz,
    )


def _discrete_harmonic_run() -> dict[str, Any]:
    omega_n = math.sqrt(DISCRETE_K / DISCRETE_M)
    alpha = 2.0 * DISCRETE_ZETA * omega_n
    frequencies_hz = [omega_n / (2.0 * math.pi) * ratio for ratio in (0.25, 0.5, 0.9, 1.0, 1.1, 1.5, 2.0)]
    model = _discrete_model(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": frequencies_hz,
            "rayleigh_alpha": alpha,
            "rayleigh_beta": 0.0,
            "postprocess_mode": "summary",
        },
        load=1.0,
    )
    assert check_mesh(model).status in {"PASS", "WARNING"}
    result = solve_model(model, enforce_policy=False)
    return _harmonic_metrics(
        result,
        dof_index=result.dofs.index(0, "UX"),
        stiffness=DISCRETE_K,
        mass=DISCRETE_M,
        alpha=alpha,
        frequencies_hz=frequencies_hz,
    )


def test_wp03b_machine_evidence_preserves_wp03a_and_declares_dynamic_scope() -> None:
    evidence = _load_evidence()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert evidence["baseline_sha"] == "6b9c08f91c876bf5136a9da39555149b89dc2b98"
    assert evidence["historical_0_2_7_evidence_modified"] is False
    assert evidence["supersedes"] == []
    assert set(evidence["cases"]) == {
        "BEAM2_NEWMARK",
        "BEAM2_HARMONIC",
        "DISCRETE_NEWMARK",
        "DISCRETE_HARMONIC",
    }
    assert {case["decision"] for case in evidence["cases"].values()} == {"QUALIFIED_BOUNDED", "EXPERIMENTAL"}
    assert evidence["cases"]["DISCRETE_NEWMARK"]["owner_gate"] == "NOT_APPLICABLE"
    assert all(case["replay_count"] >= 2 for case in evidence["cases"].values())
    assert matrix["preserved_wp03a_decisions"] == [
        "BEAM2_STATIC",
        "BEAM2_MODAL",
        "DISCRETE_STATIC",
        "DISCRETE_MODAL",
    ]
    assert matrix["summary"]["new_qualified_bounded"] == 3
    assert matrix["summary"]["remain_experimental"] == 1
    assert matrix["summary"]["public_maturity_relabels_applied"] == 0
    matrix_by_source = {entry["source_record"]: entry for entry in matrix["decisions"]}
    for case in evidence["cases"].values():
        delta = matrix_by_source[case["source_record"]]
        assert delta["decision"] == case["decision"]
        assert delta["owner_gate"] == case["owner_gate"]


@pytest.mark.parametrize(
    ("case_name", "runner"),
    [
        ("BEAM2_NEWMARK", _beam_newmark_run),
        ("BEAM2_HARMONIC", _beam_harmonic_run),
        ("DISCRETE_NEWMARK", _discrete_newmark_run),
        ("DISCRETE_HARMONIC", _discrete_harmonic_run),
    ],
)
def test_wp03b_dynamic_cases_pass_frozen_tolerances_and_replay(case_name: str, runner: Callable[[], dict[str, Any]]) -> None:
    case = _load_evidence()["cases"][case_name]
    first = runner()
    second = runner()
    assert _digest(first) == _digest(second)
    assert case["replay_digests"][0] == case["replay_digests"][1]
    _assert_observed(first, case["observed"], case_name)
    for metric, limit in case["tolerances"].items():
        path = metric.split(".")
        value: Any = first
        for key in path:
            value = value[key]
        if case["decision"] == "QUALIFIED_BOUNDED" or metric != case.get("failed_gate", {}).get("metric"):
            assert value <= limit, (case_name, metric, value, limit)
        else:
            assert value > limit, (case_name, metric, value, limit)
