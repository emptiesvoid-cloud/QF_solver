"""Mesh quality metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.hex20 import Hex20Element


@dataclass(frozen=True)
class MeshQualityThresholds:
    """Warning and failure thresholds used by mesh validation."""

    tet_min_signed_volume: float = 1.0e-14
    tet_min_quality: float = 5.0e-2
    tet_min_radius_ratio: float = 5.0e-2
    tet_max_aspect_ratio: float = 20.0
    tet_min_relative_volume: float = 1.0e-4
    tet10_max_mid_edge_deviation_ratio: float = 5.0e-2
    tet10_min_sampled_jacobian: float = 1.0e-14
    tet10_min_jacobian_ratio: float = 5.0e-2
    mitc4_max_aspect_ratio: float = 10.0
    mitc4_max_planarity_ratio: float = 1.0e-3
    mitc4_min_angle_degrees: float = 30.0
    mitc4_max_angle_degrees: float = 150.0
    mitc4_max_warpage_degrees: float = 5.0
    mitc3_max_aspect_ratio: float = 10.0
    mitc3_min_angle_degrees: float = 20.0
    mitc3_max_angle_degrees: float = 140.0
    mitc3_min_relative_area: float = 1.0e-8

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


class MeshQuality:
    """Compute simple quality metrics for supported elements."""

    @staticmethod
    def tet4_volume(coords: np.ndarray) -> float:
        return Tet4Element.signed_volume(coords)

    @staticmethod
    def tet4_quality(coords: np.ndarray) -> float:
        volume = abs(Tet4Element.signed_volume(coords))
        edges = []
        for i in range(4):
            for j in range(i + 1, 4):
                edges.append(float(np.linalg.norm(coords[j] - coords[i])))
        rms = float(np.sqrt(np.mean(np.square(edges))))
        if rms <= 0.0:
            return 0.0
        return 6.0 * np.sqrt(2.0) * volume / (rms**3)

    @staticmethod
    def tet_metrics(coords: np.ndarray) -> dict[str, float]:
        corners = np.asarray(coords, dtype=float)[:4]
        edges = _edge_lengths(corners)
        edge_min = min(edges) if edges else 0.0
        edge_max = max(edges) if edges else 0.0
        volume = MeshQuality.tet4_volume(corners)
        radius_ratio = _tet_radius_ratio(corners, abs(volume))
        return {
            "signed_volume": float(volume),
            "quality": MeshQuality.tet4_quality(corners),
            "radius_ratio": radius_ratio,
            "edge_length_min": float(edge_min),
            "edge_length_max": float(edge_max),
            "aspect_ratio": float(edge_max / edge_min) if edge_min > 0.0 else float("inf"),
            "relative_volume": float(abs(volume) / (edge_max**3)) if edge_max > 0.0 else 0.0,
            "skew": float(max(0.0, 1.0 - MeshQuality.tet4_quality(corners))),
        }

    @staticmethod
    def tet10_metrics(coords: np.ndarray) -> dict[str, float]:
        """Extend corner metrics with midside placement and sampled Jacobians."""
        points = np.asarray(coords, dtype=float)
        metrics = MeshQuality.tet_metrics(points)
        metrics.update(Tet10Element.geometry_diagnostics(points))
        return metrics

    @staticmethod
    def hex20_metrics(coords: np.ndarray) -> dict[str, float]:
        """Return midside placement and sampled-Jacobian metrics for HEX20."""
        points = np.asarray(coords, dtype=float)
        edge_pairs = (
            (0, 1),
            (3, 0),
            (0, 4),
            (1, 2),
            (1, 5),
            (2, 3),
            (2, 6),
            (3, 7),
            (4, 5),
            (7, 4),
            (5, 6),
            (6, 7),
        )
        deviations = [
            float(np.linalg.norm(points[8 + index] - 0.5 * (points[first] + points[second])))
            for index, (first, second) in enumerate(edge_pairs)
        ]
        relative = [
            deviation / float(np.linalg.norm(points[second] - points[first]))
            if float(np.linalg.norm(points[second] - points[first])) > 0.0
            else float("inf")
            for deviation, (first, second) in zip(deviations, edge_pairs)
        ]
        determinants = np.asarray(
            [Hex20Element.jacobian_determinant(points, point) for point in Hex20Element.integration_points],
            dtype=float,
        )
        minimum = float(np.min(determinants))
        maximum = float(np.max(determinants))
        return {
            "mid_edge_deviation_max": float(max(deviations)),
            "mid_edge_deviation_mean": float(np.mean(deviations)),
            "mid_edge_deviation_ratio_max": float(max(relative)),
            "sampled_jacobian_min": minimum,
            "sampled_jacobian_max": maximum,
            "sampled_jacobian_ratio": minimum / maximum if maximum > 0.0 else float("-inf"),
            "sampled_jacobian_nonpositive_count": float(np.count_nonzero(determinants <= 0.0)),
            "sampled_jacobian_count": float(determinants.size),
        }

    @staticmethod
    def quad_metrics(coords: np.ndarray) -> dict[str, float]:
        points = np.asarray(coords, dtype=float)[:4]
        edges = [float(np.linalg.norm(points[(index + 1) % 4] - points[index])) for index in range(4)]
        edge_min = min(edges) if edges else 0.0
        edge_max = max(edges) if edges else 0.0
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        norm = float(np.linalg.norm(normal))
        if norm > 0.0:
            distances = np.abs((points - points[0]) @ (normal / norm))
            planarity = float(np.max(distances))
        else:
            planarity = float("inf")
        angles = _quad_angles(points)
        warpage_degrees = _quad_warpage_degrees(points)
        edge_scale = max(edge_max, 1.0)
        return {
            "area": _quad_area(points),
            "edge_length_min": float(edge_min),
            "edge_length_max": float(edge_max),
            "aspect_ratio": float(edge_max / edge_min) if edge_min > 0.0 else float("inf"),
            "planarity": planarity,
            "planarity_ratio": float(planarity / edge_scale),
            "angle_min_degrees": float(min(angles)) if angles else 0.0,
            "angle_max_degrees": float(max(angles)) if angles else 0.0,
            "warpage_degrees": warpage_degrees,
        }

    @staticmethod
    def triangle_metrics(coords: np.ndarray) -> dict[str, float]:
        points = np.asarray(coords, dtype=float)[:3]
        edges = [
            float(np.linalg.norm(points[1] - points[0])),
            float(np.linalg.norm(points[2] - points[1])),
            float(np.linalg.norm(points[0] - points[2])),
        ]
        edge_min = min(edges)
        edge_max = max(edges)
        area = _triangle_area(points[0], points[1], points[2])
        angles = _triangle_angles(points)
        inradius = 2.0 * area / sum(edges) if sum(edges) > 0.0 else 0.0
        circumradius = (
            edges[0] * edges[1] * edges[2] / (4.0 * area)
            if area > 0.0
            else float("inf")
        )
        return {
            "area": float(area),
            "edge_length_min": float(edge_min),
            "edge_length_max": float(edge_max),
            "aspect_ratio": float(edge_max / edge_min) if edge_min > 0.0 else float("inf"),
            "relative_area": float(area / edge_max**2) if edge_max > 0.0 else 0.0,
            "radius_ratio": float(2.0 * inradius / circumradius) if circumradius > 0.0 else 0.0,
            "angle_min_degrees": float(min(angles)) if angles else 0.0,
            "angle_max_degrees": float(max(angles)) if angles else 0.0,
            "planarity": 0.0,
            "planarity_ratio": 0.0,
            "warpage_degrees": 0.0,
        }


def _edge_lengths(coords: np.ndarray) -> list[float]:
    lengths: list[float] = []
    for i in range(coords.shape[0]):
        for j in range(i + 1, coords.shape[0]):
            lengths.append(float(np.linalg.norm(coords[j] - coords[i])))
    return lengths


def _quad_area(points: np.ndarray) -> float:
    first = 0.5 * np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0]))
    second = 0.5 * np.linalg.norm(np.cross(points[2] - points[0], points[3] - points[0]))
    return float(first + second)


def _quad_angles(points: np.ndarray) -> list[float]:
    angles: list[float] = []
    for index in range(4):
        previous_point = points[(index - 1) % 4]
        current = points[index]
        next_point = points[(index + 1) % 4]
        first = previous_point - current
        second = next_point - current
        norm = float(np.linalg.norm(first) * np.linalg.norm(second))
        if norm <= 0.0:
            continue
        cosine = float(np.clip((first @ second) / norm, -1.0, 1.0))
        angles.append(float(np.degrees(np.arccos(cosine))))
    return angles


def _triangle_angles(points: np.ndarray) -> list[float]:
    angles: list[float] = []
    for index in range(3):
        first = points[(index + 1) % 3] - points[index]
        second = points[(index + 2) % 3] - points[index]
        norm = float(np.linalg.norm(first) * np.linalg.norm(second))
        if norm <= 0.0:
            continue
        cosine = float(np.clip((first @ second) / norm, -1.0, 1.0))
        angles.append(float(np.degrees(np.arccos(cosine))))
    return angles


def _tet_radius_ratio(points: np.ndarray, volume: float) -> float:
    faces = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))
    surface = sum(_triangle_area(points[i], points[j], points[k]) for i, j, k in faces)
    if volume <= 0.0 or surface <= 0.0:
        return 0.0
    inradius = 3.0 * volume / surface
    try:
        matrix = 2.0 * np.vstack([points[1] - points[0], points[2] - points[0], points[3] - points[0]])
        rhs = np.array(
            [
                np.dot(points[1] - points[0], points[1] - points[0]),
                np.dot(points[2] - points[0], points[2] - points[0]),
                np.dot(points[3] - points[0], points[3] - points[0]),
            ],
            dtype=float,
        )
        center = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        return 0.0
    circumradius = float(np.linalg.norm(center))
    if circumradius <= 0.0:
        return 0.0
    return float(3.0 * inradius / circumradius)


def _triangle_area(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a)))


def _quad_warpage_degrees(points: np.ndarray) -> float:
    first = np.cross(points[1] - points[0], points[2] - points[0])
    second = np.cross(points[2] - points[0], points[3] - points[0])
    norm = float(np.linalg.norm(first) * np.linalg.norm(second))
    if norm <= 0.0:
        return 180.0
    cosine = float(np.clip((first @ second) / norm, -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))
