"""Reusable shell and laminate result-recovery helpers."""

from __future__ import annotations

import numpy as np

from solveur.elements.shell.mitc4 import ShellMaterial

from solveur.materials.failure import CompositeFailureEvaluator
from solveur.materials.laminate import LaminateShellMaterial


def shell_nodal_results(
    nodes: tuple[int, ...],
    coords: np.ndarray,
    membrane_strain: np.ndarray,
    curvature: np.ndarray,
    shear_strain: np.ndarray,
    shell_faces: list[dict[str, object]],
) -> list[dict[str, object]]:
    top = next((face for face in shell_faces if face["face"] == "top"), {})
    bottom = next((face for face in shell_faces if face["face"] == "bottom"), {})
    rows: list[dict[str, object]] = []
    for local_index, node in enumerate(nodes):
        rows.append(
            {
                "node": int(node),
                "local_node": int(local_index),
                "method": "center_result",
                "coordinates": np.asarray(coords[local_index], dtype=float).tolist(),
                "membrane_strain": membrane_strain.tolist(),
                "curvature": curvature.tolist(),
                "shear_strain": shear_strain.tolist(),
                "shell_top_von_mises": float(top.get("von_mises", 0.0)),
                "shell_bottom_von_mises": float(bottom.get("von_mises", 0.0)),
            }
        )
    return rows


def average_contributions(
    node: int,
    contributions: list[dict[str, object]],
) -> dict[str, object]:
    row: dict[str, object] = {
        "node": int(node),
        "contributing_element_count": len(contributions),
        "source": "element_nodal_average",
    }
    keys = sorted(
        {
            key
            for item in contributions
            for key in item
            if key not in {"node", "local_node", "method", "coordinates"}
        }
    )
    for key in keys:
        values = [item[key] for item in contributions if key in item]
        averaged = _average_numeric_values(values)
        if averaged is not None:
            row[key] = averaged
    return row


def shell_face_results(
    material: ShellMaterial,
    membrane_strain: np.ndarray,
    curvature: np.ndarray,
) -> list[dict[str, object]]:
    cmat = material.E / (1.0 - material.nu**2) * material._plane_stress_matrix()
    faces: list[dict[str, object]] = []
    for name, z in (("bottom", -0.5 * material.t), ("top", 0.5 * material.t)):
        strain = membrane_strain + z * curvature
        stress = cmat @ strain
        tensor = np.array(
            [[stress[0], stress[2]], [stress[2], stress[1]]],
            dtype=float,
        )
        faces.append(
            {
                "face": name,
                "z": float(z),
                "strain": strain.tolist(),
                "stress": stress.tolist(),
                "principal_stress": np.linalg.eigvalsh(tensor).tolist(),
                "von_mises": plane_stress_von_mises(stress),
            }
        )
    return faces


def laminate_ply_results(
    material: LaminateShellMaterial,
    membrane_strain: np.ndarray,
    curvature: np.ndarray,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for point in material.laminate.ply_results(membrane_strain, curvature):
        ply = material.laminate.plies[point.ply_index]
        stress = np.asarray(point.stress_element, dtype=float)
        stress_tensor = np.array(
            [[stress[0], stress[2]], [stress[2], stress[1]]],
            dtype=float,
        )
        row: dict[str, object] = {
            "ply_index": int(point.ply_index),
            "ply_name": point.ply_name,
            "location": point.location,
            "z": float(point.z),
            "strain": point.strain_element.tolist(),
            "stress": point.stress_element.tolist(),
            "material_strain": point.strain_material.tolist(),
            "material_stress": point.stress_material.tolist(),
            "principal_stress": np.linalg.eigvalsh(stress_tensor).tolist(),
            "von_mises": plane_stress_von_mises(point.stress_element),
        }
        if ply.strengths is not None:
            evaluated = CompositeFailureEvaluator.evaluate(
                point.stress_material,
                point.strain_material,
                ply.strengths,
                ply.strain_allowables,
            )
            row["failure_indices"] = {
                item.criterion: item.to_dict() for item in evaluated
            }
        results.append(row)
    return results


def laminate_failure_summary(
    ply_results: list[dict[str, object]],
) -> dict[str, object] | None:
    critical: dict[str, dict[str, object]] = {}
    for point in ply_results:
        indices = point.get("failure_indices")
        if not isinstance(indices, dict):
            continue
        for criterion, raw in indices.items():
            if not isinstance(raw, dict):
                continue
            index = float(raw["index"])
            if criterion not in critical or index > float(critical[criterion]["index"]):
                critical[criterion] = {
                    "index": index,
                    "reserve_factor": raw.get("reserve_factor"),
                    "passed": bool(raw["passed"]),
                    "ply_index": int(point["ply_index"]),
                    "ply_name": str(point["ply_name"]),
                    "location": str(point["location"]),
                    "z": float(point["z"]),
                }
    if not critical:
        return None
    return {
        "all_passed": all(bool(item["passed"]) for item in critical.values()),
        "critical_by_criterion": critical,
        "interpretation": "non_degrading_first_ply_indicator",
    }


def laminate_outer_faces(
    ply_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    bottom = next(
        item
        for item in ply_results
        if item["ply_index"] == 0 and item["location"] == "lower"
    )
    top_index = max(int(item["ply_index"]) for item in ply_results)
    top = next(
        item
        for item in ply_results
        if item["ply_index"] == top_index and item["location"] == "upper"
    )
    return [
        {"face": "bottom", "section_position": "shell_down", **bottom},
        {"face": "top", "section_position": "shell_up", **top},
    ]


def laminate_section_results(
    ply_results: list[dict[str, object]],
) -> dict[str, object]:
    """Expose unambiguous through-thickness shell extraction positions.

    At a laminate interface, stress is generally discontinuous.  The
    ``shell_middle`` value is therefore a list containing both material-side
    limits when the geometric mid-plane lies on an interface.
    """
    faces = laminate_outer_faces(ply_results)
    minimum = min(abs(float(item["z"])) for item in ply_results)
    tolerance = max(1.0e-14, 1.0e-12 * max(abs(float(item["z"])) for item in ply_results))
    middle = [
        {"section_position": "shell_middle", **item}
        for item in ply_results
        if abs(abs(float(item["z"])) - minimum) <= tolerance
    ]
    return {
        "axis": "local_e3",
        "shell_down": faces[0],
        "shell_middle": middle,
        "shell_up": faces[1],
        "middle_is_interface": len(middle) > 1 and minimum <= tolerance,
    }


def plane_stress_von_mises(stress: np.ndarray) -> float:
    sx, sy, txy = np.asarray(stress, dtype=float)
    return float(
        np.sqrt(max(sx * sx - sx * sy + sy * sy + 3.0 * txy * txy, 0.0))
    )


def _average_numeric_values(values: list[object]) -> object | None:
    first = values[0]
    if isinstance(first, (int, float)):
        return float(np.mean([float(value) for value in values]))
    if isinstance(first, list):
        arrays = [np.asarray(value, dtype=float) for value in values]
        if not all(array.shape == arrays[0].shape for array in arrays):
            return None
        flattened = np.vstack([array.ravel() for array in arrays])
        return np.mean(flattened, axis=0).reshape(arrays[0].shape).tolist()
    return None
