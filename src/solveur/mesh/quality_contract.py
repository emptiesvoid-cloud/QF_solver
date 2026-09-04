"""Common geometric quality contract for solid elements.

This module deliberately does not alter element integration or solver checks.  It
provides a stable summary for preflight, V&V evidence, and future element work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.mesh.quality import MeshQuality, MeshQualityThresholds

QUALITY_CONTRACT_VERSION = "1.0"
VALID = "VALID"
VALID_WITH_WARNING = "VALID_WITH_WARNING"
INVALID = "INVALID"
SUPPORTED_FAMILIES = ("TET4", "TET10", "HEX8", "HEX20", "WEDGE6")
WEDGE6_QUALITY_CONTRACT = {
    "element_family": "WEDGE6",
    "implemented": True,
    "dimension": 3,
    "node_count": 6,
    "signed_volume": "prism-oriented signed volume",
    "jacobian_sampling": {
        "validity_controls": "analytic minimum of det(J)(t) at each triangular reference vertex",
        "diagnostic_samples": "all selected volume quadrature points, face centroids and prism interior centroid",
        "integration_points_only": False,
        "certificate": "det(J) is affine in (r,s) at fixed t and quadratic in t; endpoints and interior stationary points are checked",
        "tolerance": "machine-epsilon-scaled to the determinant coefficient magnitude",
        "contract": "T1-R-WEDGE6-FORMULATION-001",
    },
    "faces": {"triangles": 2, "quadrilaterals": 3},
    "orientation": "six-node orientation and outward face normals",
    "degeneracy": "non-positive or non-finite certified minimum determinant",
    "distortion": "prism-compatible dimensionless diagnostics, no universal cutoff",
    "status": "CONTROLLED_TECHNICAL_KERNEL_CONTRACT",
    "source_contract": "qualification/0_2_7/wedge6_formulation_contract.json",
}

_WEDGE6_REFERENCE_TRIANGLE_VERTICES = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
_WEDGE6_MACHINE_EPSILON = float(np.finfo(float).eps)
_WEDGE6_WARNING_RATIO = float(np.sqrt(_WEDGE6_MACHINE_EPSILON))

_TET4_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
_HEX8_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
_TET10_EDGES = _TET4_EDGES
_HEX20_EDGES = _HEX8_EDGES
_WEDGE6_EDGES = (
    (0, 1), (1, 2), (2, 0),
    (3, 4), (4, 5), (5, 3),
    (0, 3), (1, 4), (2, 5),
)
_WEDGE6_PRODUCTION_POINTS = tuple(
    (r, s, t)
    for r, s in ((1.0 / 6.0, 1.0 / 6.0), (2.0 / 3.0, 1.0 / 6.0), (1.0 / 6.0, 2.0 / 3.0))
    for t in (-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0))
)


@dataclass(frozen=True)
class ElementQualityAssessment:
    """Deterministic geometric assessment for one finite element."""

    element_id: int
    element_family: str
    classification: str
    metrics: dict[str, float | int | bool | str | None]
    warnings: tuple[str, ...]
    fatal_findings: tuple[str, ...]
    provenance: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_family": self.element_family,
            "classification": self.classification,
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
            "fatal_findings": list(self.fatal_findings),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class MeshQualityAssessment:
    """Aggregated deterministic assessment for a model mesh."""

    classification: str
    elements: tuple[ElementQualityAssessment, ...]
    contract_version: str = QUALITY_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "classification": self.classification,
            "elements": [element.to_dict() for element in self.elements],
        }


def wedge6_quality_contract() -> dict[str, Any]:
    """Return the active technical quality contract for WEDGE6."""

    return dict(WEDGE6_QUALITY_CONTRACT)


def _wedge6_shape_gradients(r: float, s: float, t: float) -> np.ndarray:
    """Return reference derivatives for the linear WEDGE6 mapping."""

    return np.asarray(
        [
            [-0.5 * (1.0 - t), -0.5 * (1.0 - t), -0.5 * (1.0 - r - s)],
            [0.5 * (1.0 - t), 0.0, -0.5 * r],
            [0.0, 0.5 * (1.0 - t), -0.5 * s],
            [-0.5 * (1.0 + t), -0.5 * (1.0 + t), 0.5 * (1.0 - r - s)],
            [0.5 * (1.0 + t), 0.0, 0.5 * r],
            [0.0, 0.5 * (1.0 + t), 0.5 * s],
        ],
        dtype=float,
    )


def _wedge6_detj(coords: np.ndarray, r: float, s: float, t: float) -> float:
    return float(np.linalg.det(coords.T @ _wedge6_shape_gradients(r, s, t)))


def _wedge6_coordinates(coords: Any) -> np.ndarray:
    values = np.asarray(coords, dtype=float)
    if values.shape != (6, 3):
        raise ValueError("Expected WEDGE6 coordinates with shape (6, 3).")
    if not np.isfinite(values).all():
        raise ValueError("WEDGE6 coordinates must be finite.")
    return values


def wedge6_detj_quadratic_coefficients(coords: Any) -> tuple[tuple[float, float, float], ...]:
    """Return ``a, b, c`` for certified ``det(J)(t) = a*t² + b*t + c``.

    For the linear prism mapping, ``det(J)`` is affine over each triangular
    section at fixed ``t``.  The global minimum therefore occurs at one of the
    three section vertices, where its remaining dependence on ``t`` is
    quadratic.
    """

    values = _wedge6_coordinates(coords)
    coefficients: list[tuple[float, float, float]] = []
    for r, s in _WEDGE6_REFERENCE_TRIANGLE_VERTICES:
        at_minus = _wedge6_detj(values, r, s, -1.0)
        at_zero = _wedge6_detj(values, r, s, 0.0)
        at_plus = _wedge6_detj(values, r, s, 1.0)
        a = 0.5 * (at_plus + at_minus) - at_zero
        b = 0.5 * (at_plus - at_minus)
        coefficients.append((float(a), float(b), float(at_zero)))
    return tuple(coefficients)


def wedge6_jacobian_certificate(coords: Any) -> dict[str, Any]:
    """Certify the minimum WEDGE6 Jacobian determinant.

    The certificate checks the exact polynomial reduction implied by the
    linear shape functions.  The additional quadrature, face and interior
    samples remain diagnostics and are deliberately not the validity proof.
    """

    coefficients = wedge6_detj_quadratic_coefficients(coords)
    candidates: list[dict[str, float | str]] = []
    for vertex_index, (a, b, c) in enumerate(coefficients):
        scale = max(abs(a), abs(b), abs(c))
        points = [-1.0, 1.0]
        if scale > 0.0 and abs(a) > _WEDGE6_MACHINE_EPSILON * scale:
            stationary = -b / (2.0 * a)
            if -1.0 < stationary < 1.0:
                points.append(float(stationary))
        for t in points:
            candidates.append(
                {
                    "triangle_vertex": float(vertex_index + 1),
                    "t": float(t),
                    "determinant": float(a * t * t + b * t + c),
                }
            )
    determinant_scale = max((abs(float(item["determinant"])) for item in candidates), default=0.0)
    tolerance = _WEDGE6_MACHINE_EPSILON * determinant_scale
    minimum = min((float(item["determinant"]) for item in candidates), default=float("nan"))
    ratio = minimum / determinant_scale if determinant_scale > 0.0 else 0.0
    if not np.isfinite(minimum) or minimum <= tolerance:
        classification = INVALID
    elif ratio <= _WEDGE6_WARNING_RATIO:
        classification = VALID_WITH_WARNING
    else:
        classification = VALID
    return {
        "method": "triangular-vertex reduction plus quadratic t minimization",
        "coefficients": [list(item) for item in coefficients],
        "candidates": candidates,
        "minimum_detJ": minimum,
        "detJ_scale": determinant_scale,
        "geometry_tolerance": tolerance,
        "minimum_to_scale_ratio": ratio,
        "classification": classification,
        "valid": classification != INVALID,
        "diagnostic_samples_are_certificate": False,
    }


def _as_coords(coords: Any, expected_nodes: int) -> np.ndarray:
    values = np.asarray(coords, dtype=float)
    if values.shape != (expected_nodes, 3):
        raise ValueError(f"Expected coordinates with shape ({expected_nodes}, 3).")
    return values


def _edge_lengths(coords: np.ndarray, edges: tuple[tuple[int, int], ...]) -> np.ndarray:
    return np.asarray([np.linalg.norm(coords[end] - coords[start]) for start, end in edges], dtype=float)


def _orientation_state(determinants: np.ndarray) -> tuple[str, bool]:
    positive = bool(np.all(determinants > 0.0))
    negative = bool(np.all(determinants < 0.0))
    if positive:
        return "POSITIVE", True
    if negative:
        return "NEGATIVE", False
    return "INCONSISTENT", False


def _base_metrics(
    signed_volume: float,
    determinants: np.ndarray,
    edge_lengths: np.ndarray,
    *,
    distortion_metric: float | None,
) -> dict[str, float | int | bool | str | None]:
    finite_determinants = determinants[np.isfinite(determinants)]
    minimum = float(np.min(finite_determinants)) if finite_determinants.size else None
    maximum = float(np.max(finite_determinants)) if finite_determinants.size else None
    ratio = None
    degeneracy = None
    if finite_determinants.size and maximum is not None and maximum != 0.0:
        ratio = float(minimum / maximum)
        degeneracy = float(np.min(np.abs(finite_determinants)) / np.max(np.abs(finite_determinants)))
    positive_edges = edge_lengths[edge_lengths > 0.0]
    aspect = float(np.max(positive_edges) / np.min(positive_edges)) if positive_edges.size else None
    orientation, _ = _orientation_state(determinants) if finite_determinants.size else ("UNAVAILABLE", False)
    return {
        "signed_volume": float(signed_volume),
        "volume": float(abs(signed_volume)),
        "min_jacobian_determinant": minimum,
        "max_jacobian_determinant": maximum,
        "jacobian_determinant_ratio": ratio,
        "jacobian_sign_consistent": orientation in {"POSITIVE", "NEGATIVE"},
        "orientation_state": orientation,
        "degeneracy_indicator": degeneracy,
        "aspect_ratio": aspect,
        "distortion_metric": distortion_metric,
        "geometric_conditioning_indicator": None,
        "edge_length_min": float(np.min(edge_lengths)) if edge_lengths.size else None,
        "edge_length_max": float(np.max(edge_lengths)) if edge_lengths.size else None,
    }


def _invalid_assessment(
    element_id: int,
    family: str,
    reason: str,
    *,
    metrics: dict[str, float | int | bool | str | None] | None = None,
) -> ElementQualityAssessment:
    return ElementQualityAssessment(
        element_id,
        family,
        INVALID,
        metrics or {},
        (),
        (reason,),
        {
            "contract": QUALITY_CONTRACT_VERSION,
            "metric_source": "solveur.mesh.quality_contract",
            "conditioning": "not estimated; no universal conditioning cutoff",
        },
    )


def _family_data(
    family: str,
    coords: np.ndarray,
) -> tuple[float, np.ndarray, np.ndarray, float | None, tuple[str, ...]]:
    if family == "TET4":
        signed_volume = MeshQuality.tet4_volume(coords)
        determinants = np.asarray([6.0 * signed_volume], dtype=float)
        edges = _edge_lengths(coords, _TET4_EDGES)
        distortion = float(1.0 - MeshQuality.tet4_quality(coords))
        warnings: tuple[str, ...] = ()
        return signed_volume, determinants, edges, distortion, warnings
    if family == "TET10":
        determinants = np.asarray(Tet10Element.jacobian_determinants(coords), dtype=float)
        integration_determinants = np.asarray(
            Tet10Element.jacobian_determinants(coords, Tet10Element.integration_points), dtype=float
        )
        signed_volume = float(np.sum(integration_determinants) * Tet10Element.integration_weight)
        edges = _edge_lengths(coords, _TET10_EDGES)
        ratio = float(np.min(determinants) / np.max(determinants)) if np.max(determinants) > 0.0 else None
        diagnostics = Tet10Element.geometry_diagnostics(coords)
        warnings = []
        if diagnostics["mid_edge_deviation_ratio_max"] > MeshQualityThresholds().tet10_max_mid_edge_deviation_ratio:
            warnings.append("MID_EDGE_DEVIATION_ABOVE_LEGACY_WARNING")
        if ratio is not None and ratio < MeshQualityThresholds().tet10_min_jacobian_ratio:
            warnings.append("JACOBIAN_RATIO_BELOW_LEGACY_WARNING")
        return signed_volume, determinants, edges, float(1.0 - ratio) if ratio is not None else None, tuple(warnings)
    if family == "HEX8":
        points = Hex8Element.integration_points
        determinants = np.asarray([Hex8Element.jacobian_determinant(coords, point) for point in points], dtype=float)
        signed_volume = float(np.sum(determinants))
        edges = _edge_lengths(coords, _HEX8_EDGES)
        ratio = float(np.min(determinants) / np.max(determinants)) if np.max(determinants) > 0.0 else None
        return signed_volume, determinants, edges, float(1.0 - ratio) if ratio is not None else None, ()
    if family == "HEX20":
        points = Hex20Element.integration_points
        determinants = np.asarray([Hex20Element.jacobian_determinant(coords, point) for point in points], dtype=float)
        signed_volume = float(np.dot(np.asarray(Hex20Element.integration_weights), determinants))
        edges = _edge_lengths(coords, _HEX20_EDGES)
        ratio = float(np.min(determinants) / np.max(determinants)) if np.max(determinants) > 0.0 else None
        return signed_volume, determinants, edges, float(1.0 - ratio) if ratio is not None else None, ()
    if family == "WEDGE6":
        determinants = np.asarray(
            [_wedge6_detj(coords, r, s, t) for r, s, t in _WEDGE6_PRODUCTION_POINTS],
            dtype=float,
        )
        signed_volume = float(np.dot(np.full(determinants.size, 1.0 / 6.0), determinants))
        edges = _edge_lengths(coords, _WEDGE6_EDGES)
        certificate = wedge6_jacobian_certificate(coords)
        distortion = float(1.0 - certificate["minimum_to_scale_ratio"])
        warnings = (
            ("JACOBIAN_CERTIFICATE_NEAR_DEGENERATE",)
            if certificate["classification"] == VALID_WITH_WARNING
            else ()
        )
        return signed_volume, determinants, edges, distortion, warnings
    raise ValueError(f"Quality assessment is not implemented for element family {family!r}.")


def assess_element(
    element_id: int,
    element_family: str,
    coords: Any,
    *,
    thresholds: MeshQualityThresholds | None = None,
) -> ElementQualityAssessment:
    """Assess geometry without imposing a new universal quality threshold."""

    family = str(element_family).strip().upper()
    expected_nodes = {"TET4": 4, "TET10": 10, "HEX8": 8, "HEX20": 20, "WEDGE6": 6}.get(family)
    if expected_nodes is None:
        return _invalid_assessment(element_id, family, "UNSUPPORTED_ELEMENT_FAMILY")
    try:
        values = _as_coords(coords, expected_nodes)
    except (TypeError, ValueError):
        return _invalid_assessment(element_id, family, "INVALID_COORDINATE_SHAPE")
    if not np.isfinite(values).all():
        return _invalid_assessment(element_id, family, "NONFINITE_COORDINATES")
    if np.unique(values, axis=0).shape[0] != values.shape[0]:
        return _invalid_assessment(element_id, family, "COINCIDENT_ELEMENT_NODES")
    try:
        signed_volume, determinants, edges, distortion, family_warnings = _family_data(family, values)
    except (TypeError, ValueError, np.linalg.LinAlgError):
        return _invalid_assessment(element_id, family, "GEOMETRY_EVALUATION_FAILED")
    metrics = _base_metrics(signed_volume, determinants, edges, distortion_metric=distortion)
    warnings = list(family_warnings)
    certificate = wedge6_jacobian_certificate(values) if family == "WEDGE6" else None
    if certificate is not None:
        metrics.update(
            {
                "certified_min_jacobian_determinant": float(certificate["minimum_detJ"]),
                "certified_detj_scale": float(certificate["detJ_scale"]),
                "certified_detj_ratio": float(certificate["minimum_to_scale_ratio"]),
                "certified_geometry_tolerance": float(certificate["geometry_tolerance"]),
            }
        )
    if family in {"TET4", "TET10"}:
        selected_thresholds = thresholds or MeshQualityThresholds()
        if family == "TET4":
            if float(metrics["aspect_ratio"]) > selected_thresholds.tet_max_aspect_ratio:
                warnings.append("ASPECT_ABOVE_LEGACY_WARNING")
            if MeshQuality.tet4_quality(values) < selected_thresholds.tet_min_quality:
                warnings.append("QUALITY_BELOW_LEGACY_WARNING")
    finite = np.isfinite(determinants).all()
    orientation, positive = _orientation_state(determinants) if finite else ("UNAVAILABLE", False)
    fatal: list[str] = []
    if not finite:
        fatal.append("NONFINITE_JACOBIAN")
    if not positive:
        fatal.append("JACOBIAN_ORIENTATION_INVALID")
    if certificate is not None and not certificate["valid"]:
        fatal.append("WEDGE6_JACOBIAN_CERTIFICATE_INVALID")
    if signed_volume <= 0.0:
        fatal.append("NONPOSITIVE_SIGNED_VOLUME")
    if not edges.size or np.any(edges <= 0.0):
        fatal.append("ZERO_LENGTH_EDGE")
    metrics["orientation_state"] = orientation
    metrics["jacobian_sign_consistent"] = bool(finite and np.all(determinants > 0.0))
    provenance = {
        "contract": QUALITY_CONTRACT_VERSION,
        "metric_source": "solveur.mesh.quality_contract",
        "jacobian_sampling": {
            "TET4": "corner mapping determinant",
            "TET10": "Tet10Element.jacobian_determinants",
            "HEX8": "Hex8Element.integration_points",
            "HEX20": "Hex20Element.integration_points",
            "WEDGE6": "analytic triangular-vertex quadratic certificate plus TRI3_X_GAUSS2 diagnostics",
        }[family],
        "thresholds": "legacy MeshQualityThresholds; diagnostic warnings only" if warnings else "none; no universal threshold applied",
        "conditioning": "not estimated; no universal conditioning cutoff",
    }
    classification = INVALID if fatal else VALID_WITH_WARNING if warnings else VALID
    return ElementQualityAssessment(element_id, family, classification, metrics, tuple(sorted(set(warnings))), tuple(fatal), provenance)


def assess_model(model: Any) -> MeshQualityAssessment:
    """Assess all model elements and aggregate with fail-closed invalidity."""

    assessments: list[ElementQualityAssessment] = []
    nodes = np.asarray(getattr(model, "nodes", []), dtype=float)
    for element_id, element in enumerate(getattr(model, "elements", [])):
        family = str(getattr(element, "type", "")).upper()
        connectivity = tuple(getattr(element, "nodes", ()))
        expected = {"TET4": 4, "TET10": 10, "HEX8": 8, "HEX20": 20, "WEDGE6": 6}.get(family)
        if expected is None:
            continue
        if len(connectivity) != expected or any(index < 0 or index >= len(nodes) for index in connectivity):
            assessments.append(_invalid_assessment(element_id, family, "INVALID_ELEMENT_CONNECTIVITY"))
            continue
        assessments.append(assess_element(element_id, family, nodes[list(connectivity)]))
    if any(item.classification == INVALID for item in assessments):
        classification = INVALID
    elif any(item.classification == VALID_WITH_WARNING for item in assessments):
        classification = VALID_WITH_WARNING
    else:
        classification = VALID
    return MeshQualityAssessment(classification, tuple(assessments))


__all__ = [
    "QUALITY_CONTRACT_VERSION",
    "VALID",
    "VALID_WITH_WARNING",
    "INVALID",
    "SUPPORTED_FAMILIES",
    "ElementQualityAssessment",
    "MeshQualityAssessment",
    "assess_element",
    "assess_model",
    "wedge6_detj_quadratic_coefficients",
    "wedge6_jacobian_certificate",
    "wedge6_quality_contract",
]
