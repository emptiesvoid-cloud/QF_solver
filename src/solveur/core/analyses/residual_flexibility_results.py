"""Versioned WP-D01 harmonic result wrapper and strict JSON round-trip."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from typing import Any, Mapping

import numpy as np

from solveur.core.results import ReducedHarmonicResult
from solveur.io.checkpoint_common import checkpoint_signature


RESIDUAL_FLEXIBILITY_RESULT_SCHEMA = "qf-reduced-harmonic-residual-flexibility-result/v1"


@dataclass(frozen=True)
class ResidualFlexibilityFrequencyResult:
    """Selected output fields and diagnostics for one harmonic frequency."""

    frequency_hz: float
    uncorrected: np.ndarray
    correction: np.ndarray
    corrected: np.ndarray
    diagnostics: dict[str, Any]

    def __post_init__(self) -> None:
        frequency = float(self.frequency_hz)
        if not math.isfinite(frequency) or frequency < 0.0:
            raise ValueError("WP-D01 frequency must be finite non-negative Hz.")
        arrays = []
        for label, raw in (
            ("uncorrected response", self.uncorrected),
            ("correction", self.correction),
            ("corrected response", self.corrected),
        ):
            value = np.asarray(raw, dtype=np.complex128).copy()
            if value.ndim != 1 or not np.all(np.isfinite(value)):
                raise ValueError(f"WP-D01 {label} must be a finite complex vector.")
            value.setflags(write=False)
            arrays.append(value)
        if not (arrays[0].shape == arrays[1].shape == arrays[2].shape):
            raise ValueError("WP-D01 uncorrected, correction and corrected vectors must have matching shapes.")
        scale = max(float(np.linalg.norm(arrays[2])), float(np.linalg.norm(arrays[0])), np.finfo(float).tiny)
        if not np.allclose(
            arrays[0] + arrays[1],
            arrays[2],
            rtol=32.0 * np.finfo(float).eps,
            atol=32.0 * np.finfo(float).eps * scale,
        ):
            raise ValueError("WP-D01 serialized correction does not reconstruct the corrected response.")
        if not isinstance(self.diagnostics, Mapping):
            raise ValueError("WP-D01 frequency diagnostics must be an object.")
        snapshot = deepcopy(dict(self.diagnostics))
        json.dumps(snapshot, allow_nan=False, sort_keys=True, separators=(",", ":"))
        object.__setattr__(self, "frequency_hz", frequency)
        object.__setattr__(self, "uncorrected", arrays[0])
        object.__setattr__(self, "correction", arrays[1])
        object.__setattr__(self, "corrected", arrays[2])
        object.__setattr__(self, "diagnostics", snapshot)


@dataclass(frozen=True)
class ResidualFlexibilityHarmonicResult:
    """Opt-in wrapper that retains the unchanged WP05 v1 result verbatim."""

    wp05_result: ReducedHarmonicResult
    frequency_results: tuple[ResidualFlexibilityFrequencyResult, ...]
    telemetry: dict[str, Any]
    extension_identity: dict[str, Any]
    extension_execution_key: str

    CONTRACT = RESIDUAL_FLEXIBILITY_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.wp05_result, ReducedHarmonicResult):
            raise ValueError("WP-D01 result must wrap an unchanged WP05 v1 result.")
        rows = tuple(self.frequency_results)
        if len(rows) != self.wp05_result.frequencies_hz.size:
            raise ValueError("WP-D01 frequency-result count must match the wrapped WP05 result.")
        response_size = self.wp05_result.responses[0].size
        for index, row in enumerate(rows):
            if not isinstance(row, ResidualFlexibilityFrequencyResult):
                raise ValueError("WP-D01 frequency results must use the typed frequency-result contract.")
            if row.frequency_hz != float(self.wp05_result.frequencies_hz[index]):
                raise ValueError("WP-D01 frequency order must exactly match the wrapped WP05 result.")
            if any(vector.size != response_size for vector in (row.uncorrected, row.correction, row.corrected)):
                raise ValueError("WP-D01 output fields must match the wrapped WP05 response scope.")
            if not np.array_equal(row.uncorrected, self.wp05_result.responses[index]):
                raise ValueError("WP-D01 uncorrected response must preserve the wrapped WP05 response exactly.")
        if not isinstance(self.telemetry, Mapping) or not isinstance(self.extension_identity, Mapping):
            raise ValueError("WP-D01 telemetry and extension identity must be objects.")
        if not isinstance(self.extension_execution_key, str) or not self.extension_execution_key:
            raise ValueError("WP-D01 wrapper requires an extension execution key.")
        telemetry = deepcopy(dict(self.telemetry))
        identity = deepcopy(dict(self.extension_identity))
        json.dumps(telemetry, allow_nan=False, sort_keys=True, separators=(",", ":"))
        json.dumps(identity, allow_nan=False, sort_keys=True, separators=(",", ":"))
        base_identity = self.wp05_result.execution_identity
        base_case = base_identity.get("case_definition")
        if not isinstance(base_case, Mapping):
            raise ValueError("WP-D01 wrapper requires the WP05 operator and basis identity contract.")
        if (
            identity.get("wp05_execution_key") != self.wp05_result.execution_key
            or identity.get("operator_identity") != base_case.get("operator_identity")
            or identity.get("modal_basis_identity") != base_case.get("basis_identity")
            or identity.get("source_sha") != base_identity.get("source_sha")
        ):
            raise ValueError("WP-D01 extension provenance does not match the nested WP05 execution identity.")
        expected_extension_key = checkpoint_signature(
            identity, label="WP-D01 residual-flexibility execution identity"
        )
        if expected_extension_key != self.extension_execution_key:
            raise ValueError("WP-D01 extension execution key does not match its identity document.")
        object.__setattr__(self, "frequency_results", rows)
        object.__setattr__(self, "telemetry", telemetry)
        object.__setattr__(self, "extension_identity", identity)

    @property
    def responses(self) -> tuple[np.ndarray, ...]:
        """The opt-in route's corrected response; WP05 v1 is nested unchanged."""
        return tuple(row.corrected for row in self.frequency_results)

    @property
    def uncorrected_responses(self) -> tuple[np.ndarray, ...]:
        return tuple(row.uncorrected for row in self.frequency_results)

    @property
    def corrections(self) -> tuple[np.ndarray, ...]:
        return tuple(row.correction for row in self.frequency_results)

    @property
    def max_displacement(self) -> float:
        return float(max((np.max(np.abs(row), initial=0.0) for row in self.responses), default=0.0))

    @property
    def execution_identity(self) -> dict[str, Any]:
        return deepcopy(self.extension_identity)

    @property
    def execution_key(self) -> str:
        return self.extension_execution_key

    @property
    def result_availability(self) -> dict[str, Any]:
        result = deepcopy(self.wp05_result.result_availability)
        result["residual_flexibility"] = {
            "status": "AVAILABLE",
            "computed": True,
            "retained": True,
            "reconstructible": True,
            "schema": "qf-harmonic-residual-flexibility-result-extension/v1",
        }
        return result

    def __getattr__(self, name: str) -> Any:
        """Retain read access to the WP05 metadata contract for callers."""
        if name == "wp05_result":
            raise AttributeError(name)
        try:
            base = object.__getattribute__(self, "wp05_result")
        except AttributeError:
            raise AttributeError(name) from None
        return getattr(base, name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.CONTRACT,
            "analysis": "harmonic_response",
            "method": "modal_superposition",
            "numerical_status": self.wp05_result.numerical_status,
            "qualification_decision": "NOT_ASSESSED",
            "wp05_result": self.wp05_result.to_dict(),
            "residual_flexibility": {
                "schema": "qf-harmonic-residual-flexibility-result-extension/v1",
                "method": "mode_acceleration",
                "corrected_response_is_primary": True,
                "uncorrected_response_source": "nested_wp05_result_v1.responses",
                "frequency_results": [
                    {
                        "frequency_hz": row.frequency_hz,
                        "uncorrected_response": _encode_complex(row.uncorrected),
                        "correction": _encode_complex(row.correction),
                        "corrected_response": _encode_complex(row.corrected),
                        "diagnostics": deepcopy(row.diagnostics),
                    }
                    for row in self.frequency_results
                ],
                "telemetry": deepcopy(self.telemetry),
                "extension_identity": deepcopy(self.extension_identity),
                "extension_execution_key": self.extension_execution_key,
                "result_availability": {
                    "uncorrected_response": "AVAILABLE",
                    "correction": "AVAILABLE",
                    "corrected_response": "AVAILABLE",
                    "stress": "NOT_COMPUTED",
                    "physical_reactions": self.wp05_result.result_availability.get("physical_reactions", {}).get(
                        "status", "UNAVAILABLE"
                    ),
                    "engineering_qualification": "NOT_ASSESSED",
                },
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResidualFlexibilityHarmonicResult":
        if not isinstance(payload, Mapping) or payload.get("schema") != cls.CONTRACT:
            raise ValueError("Unsupported WP-D01 residual-flexibility result schema.")
        if set(payload) != {
            "schema",
            "analysis",
            "method",
            "numerical_status",
            "qualification_decision",
            "wp05_result",
            "residual_flexibility",
        }:
            raise ValueError("WP-D01 result envelope has missing or unexpected fields.")
        if payload.get("analysis") != "harmonic_response" or payload.get("method") != "modal_superposition":
            raise ValueError("Serialized WP-D01 result is not harmonic modal-superposition output.")
        base_payload = payload.get("wp05_result")
        extension = payload.get("residual_flexibility")
        if not isinstance(base_payload, Mapping) or not isinstance(extension, Mapping):
            raise ValueError("WP-D01 result requires the WP05 result and extension objects.")
        if extension.get("schema") != "qf-harmonic-residual-flexibility-result-extension/v1":
            raise ValueError("Unsupported WP-D01 result-extension schema.")
        if extension.get("method") != "mode_acceleration":
            raise ValueError("WP-D01 result extension has an unsupported method.")
        if set(extension) != {
            "schema",
            "method",
            "corrected_response_is_primary",
            "uncorrected_response_source",
            "frequency_results",
            "telemetry",
            "extension_identity",
            "extension_execution_key",
            "result_availability",
        }:
            raise ValueError("WP-D01 extension has missing or unexpected fields.")
        if extension.get("corrected_response_is_primary") is not True:
            raise ValueError("WP-D01 wrapper must identify the corrected response as the opt-in primary response.")
        if extension.get("uncorrected_response_source") != "nested_wp05_result_v1.responses":
            raise ValueError("WP-D01 wrapper has an inconsistent uncorrected-response source.")
        try:
            base = ReducedHarmonicResult.from_dict(dict(base_payload))
            raw_rows = extension["frequency_results"]
            if not isinstance(raw_rows, list):
                raise ValueError("WP-D01 frequency_results must be a list.")
            for item in raw_rows:
                if not isinstance(item, Mapping) or set(item) != {
                    "frequency_hz",
                    "uncorrected_response",
                    "correction",
                    "corrected_response",
                    "diagnostics",
                }:
                    raise ValueError("WP-D01 frequency row has missing or unexpected fields.")
            rows = tuple(
                ResidualFlexibilityFrequencyResult(
                    frequency_hz=float(item["frequency_hz"]),
                    uncorrected=_decode_complex(item["uncorrected_response"]),
                    correction=_decode_complex(item["correction"]),
                    corrected=_decode_complex(item["corrected_response"]),
                    diagnostics=dict(item["diagnostics"]),
                )
                for item in raw_rows
            )
            result = cls(
                wp05_result=base,
                frequency_results=rows,
                telemetry=dict(extension["telemetry"]),
                extension_identity=dict(extension["extension_identity"]),
                extension_execution_key=str(extension["extension_execution_key"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Serialized WP-D01 result is incomplete, inconsistent or malformed.") from exc
        if payload.get("numerical_status") != result.wp05_result.numerical_status:
            raise ValueError("WP-D01 and nested WP05 numerical statuses disagree.")
        if payload.get("qualification_decision") != "NOT_ASSESSED":
            raise ValueError("WP-D01 experimental output must preserve NOT_ASSESSED qualification status.")
        availability = extension.get("result_availability")
        expected_availability = result.to_dict()["residual_flexibility"]["result_availability"]
        if not isinstance(availability, Mapping) or dict(availability) != expected_availability:
            raise ValueError("WP-D01 result availability fields are missing or inconsistent.")
        return result


def _encode_complex(values: np.ndarray) -> dict[str, list[float]]:
    vector = np.asarray(values, dtype=np.complex128)
    if vector.ndim != 1 or not np.all(np.isfinite(vector)):
        raise ValueError("WP-D01 complex result fields must be finite vectors.")
    return {"real": vector.real.tolist(), "imag": vector.imag.tolist()}


def _decode_complex(payload: Any) -> np.ndarray:
    if not isinstance(payload, Mapping) or set(payload) != {"real", "imag"}:
        raise ValueError("WP-D01 complex vectors require explicit real and imag arrays.")
    real = np.asarray(payload["real"], dtype=np.float64)
    imag = np.asarray(payload["imag"], dtype=np.float64)
    if real.ndim != 1 or imag.shape != real.shape or not np.all(np.isfinite(real)) or not np.all(np.isfinite(imag)):
        raise ValueError("WP-D01 complex vector arrays must be matching finite vectors.")
    return np.asarray(real + 1j * imag, dtype=np.complex128)
