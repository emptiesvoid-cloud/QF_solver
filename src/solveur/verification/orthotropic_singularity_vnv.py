"""Mesh-refined stress acceptance near orthotropic stress concentrations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from solveur.api.public import save_model, save_result, solve_model
from solveur.io.manifest import write_json_file
from solveur.large.io import from_finite_element_model, save_large_model
from solveur.large.postprocess import postprocess_large_tet4
from solveur.large.solver import solve_large_model as solve_large_tet4
from solveur.verification.code_aster_tl_structural import code_aster_mesh, run_code_aster
from solveur.verification.orthotropic_complex_mesh import (
    OrthotropicComplexCase,
    OrthotropicComplexMeshFactory,
)
from solveur.verification.orthotropic_external import (
    _run_calculix,
    code_aster_orthotropic_commands,
    write_calculix_orthotropic_input,
)
from solveur.verification.singularity_stress import SingularityStressAssessor, StressPathSample
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class _CaseDefinition:
    identifier: str
    true_singularity: bool
    mesh_sizes: tuple[float, ...]
    distances: tuple[float, ...]
    band: tuple[float, float]
    point: tuple[float, float]
    direction: tuple[float, float]
    path_radius: float


class OrthotropicSingularityStressCampaign:
    """Run the controlled path-and-band stress protocol on two solid geometries."""

    study_id = "VNV-ORTHOTROPIC-SINGULAR-STRESS-005"
    detailed_result_element_limit = 10_000

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        definitions = (
            _CaseDefinition(
                "finite_radius_hole",
                False,
                (0.35, 0.27, 0.21, 0.16, 0.12, 0.09, 0.07, 0.055),
                (0.70, 1.00, 1.30),
                (0.75, 1.25),
                (2.0, 0.0),
                (1.0, 0.0),
                0.25,
            ),
            _CaseDefinition(
                "reentrant_corner",
                True,
                (0.16, 0.12, 0.09, 0.07, 0.055, 0.045, 0.037, 0.031),
                (0.40, 0.60, 0.80),
                (0.45, 0.75),
                (0.75, 0.75),
                (-1.0, -1.0),
                0.18,
            ),
        )
        rows = [self._run_case(definition) for definition in definitions]
        passed = all(str(row["assessment"]["status"]) == "PASS" for row in rows)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_STRESS_ACCEPTANCE" if passed else "FAIL",
            "maturity": "engineering_internal",
            "acceptance_basis": "fixed_distance_material_S11_paths_and_band_averages",
            "stress_recovery": "compact_quadratic_kernel_with_volume_weights",
            "cases": rows,
            "limitations": [
                "The reported scalar is material-axis S11, not an anisotropic failure criterion.",
                "The re-entrant-corner nodal/element peak remains informative only.",
                "This campaign does not qualify ply-level composite stresses, damage, or delamination.",
            ],
        }
        summary = apply_external_oracle_policy(summary)
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def reassess_existing(self) -> dict[str, object]:
        """Reapply the documented oracle policy without changing numerical data."""
        summary_path = self.output_dir / "summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"Missing existing campaign summary: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary = apply_external_oracle_policy(summary)
        write_json_file(summary_path, summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, definition: _CaseDefinition) -> dict[str, object]:
        root = self.output_dir / definition.identifier
        root.mkdir(exist_ok=True)
        factory = OrthotropicComplexMeshFactory()
        samples: list[StressPathSample] = []
        aster_samples: list[dict[str, object]] = []
        levels: list[dict[str, object]] = []
        for index, mesh_size in enumerate(definition.mesh_sizes, start=1):
            work = root / f"h{index}"
            work.mkdir(exist_ok=True)
            case = self._build_case(factory, definition, work / "mesh.msh", mesh_size)
            qf_stress, aster_stress, qf_nodal, calculix_nodal = self._solve_same_mesh(case, work)
            centroids = np.mean(case.nodes[case.elements], axis=1)
            volumes = _tetra_volumes(case.nodes, case.elements)
            qf_values, qf_band = _sample_stress(
                centroids,
                qf_stress,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=definition.path_radius,
                weights=volumes,
            )
            aster_values, aster_band = _sample_stress(
                centroids,
                aster_stress,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=definition.path_radius,
                weights=volumes,
            )
            qf_nodal_values, qf_nodal_band = _sample_stress(
                case.nodes,
                qf_nodal,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=definition.path_radius,
            )
            calculix_values, calculix_band = _sample_stress(
                case.nodes,
                calculix_nodal,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=definition.path_radius,
            )
            samples.append(StressPathSample(mesh_size, definition.distances, tuple(qf_values), qf_band))
            aster_samples.append({"values": aster_values, "band_average": aster_band})
            levels.append(
                {
                    "level": index,
                    "mesh_size": mesh_size,
                    "nodes": int(case.nodes.shape[0]),
                    "elements": int(case.elements.shape[0]),
                    "qf_path_S11_pa": qf_values,
                    "code_aster_path_S11_pa": aster_values,
                    "qf_band_S11_pa": qf_band,
                    "code_aster_band_S11_pa": aster_band,
                    "same_mesh_relative_path_error": _relative_vector(qf_values, aster_values),
                    "same_mesh_relative_band_error": _relative_scalar(qf_band, aster_band),
                    "qf_nodal_path_S11_pa": qf_nodal_values,
                    "calculix_nodal_path_S11_pa": calculix_values,
                    "qf_nodal_band_S11_pa": qf_nodal_band,
                    "calculix_nodal_band_S11_pa": calculix_band,
                    "calculix_nodal_path_error": _relative_vector(qf_nodal_values, calculix_values),
                    "calculix_nodal_band_error": _relative_scalar(qf_nodal_band, calculix_band),
                }
            )
        fine = aster_samples[-1]
        assessment = SingularityStressAssessor().assess(
            samples,
            true_singularity=definition.true_singularity,
            reference_values=fine["values"],
            reference_band_average=float(fine["band_average"]),
            reference_kind="code_aster",
        )
        comparison_limit = 0.05
        primary_comparisons = [
            {
                "id": f"same_mesh_code_aster_{level['level']}",
                "path_error": level["same_mesh_relative_path_error"],
                "band_error": level["same_mesh_relative_band_error"],
                "limit": comparison_limit,
                "status": "PASS"
                if max(float(level["same_mesh_relative_path_error"]), float(level["same_mesh_relative_band_error"]))
                <= comparison_limit
                else "FAIL",
            }
            for level in levels
        ]
        secondary_comparisons = [
            {
                "id": f"same_mesh_calculix_nodal_{level['level']}",
                "path_error": level["calculix_nodal_path_error"],
                "band_error": level["calculix_nodal_band_error"],
                "limit": comparison_limit,
                "stress_recovery": "nodal_extrapolation",
                "status": "PASS"
                if max(float(level["calculix_nodal_path_error"]), float(level["calculix_nodal_band_error"]))
                <= comparison_limit
                else "WARNING",
            }
            for level in levels
        ]
        if not all(item["status"] == "PASS" for item in primary_comparisons):
            assessment = {**assessment, "status": "FAIL"}
        return {
            "id": definition.identifier,
            "classification": "true_mathematical_singularity" if definition.true_singularity else "finite_stress_concentration",
            "observable": "material-axis S11 [Pa]",
            "sampling_distances_m": list(definition.distances),
            "band_distances_m": list(definition.band),
            "levels": levels,
            "assessment": assessment,
            "same_mesh_code_aster_checks": primary_comparisons,
            "secondary_calculix_nodal_checks": secondary_comparisons,
            "secondary_comparison_policy": (
                "CalculiX nodal extrapolation is diagnostic because it is not the same "
                "stress-recovery operator as QF_solver volume averaging."
            ),
        }

    @staticmethod
    def _build_case(
        factory: OrthotropicComplexMeshFactory,
        definition: _CaseDefinition,
        mesh_path: Path,
        mesh_size: float,
    ) -> OrthotropicComplexCase:
        if definition.identifier == "finite_radius_hole":
            return factory.perforated_coupon(mesh_path, mesh_size)
        return factory.l_bracket(mesh_path, mesh_size)

    @staticmethod
    def _solve_same_mesh(
        case: OrthotropicComplexCase, work: Path
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        model = case.qf_model()
        save_model(model, work / "model.json")
        if case.elements.shape[0] <= OrthotropicSingularityStressCampaign.detailed_result_element_limit:
            result = solve_model(model)
            if result.status != "PASS":
                raise RuntimeError(f"QF_solver failed for {case.identifier}: {result.status}")
            save_result(result, work / "qf_result.json")
            qf_stress = np.asarray(
                [row["material_stress"][0] for row in result.element_results],
                dtype=float,
            )
            qf_nodal = np.asarray(
                [row["material_stress"][0] for row in result.nodal_results],
                dtype=float,
            )
        else:
            qf_stress, qf_nodal, large_summary = _solve_qf_large(case, model, work)
            write_json_file(
                work / "qf_summary.json",
                {
                    "status": "PASS",
                    "nodes": int(case.nodes.shape[0]),
                    "elements": int(case.elements.shape[0]),
                    "solver_path": "large_scipy_chunked_postprocess",
                    "postprocessing": "file_backed_element_fields_and_volume_weighted_nodal_recovery",
                    "large_summary": large_summary,
                },
            )
        groups = {
            "FIXED": (case.fixed_nodes + 1).tolist(),
            "LOADED": (case.loaded_nodes + 1).tolist(),
        }
        (work / "code_aster.mail").write_text(
            code_aster_mesh(case.nodes, case.elements, groups["FIXED"], groups=groups), encoding="ascii"
        )
        (work / "code_aster.comm").write_text(code_aster_orthotropic_commands(case), encoding="utf-8")
        run_code_aster(work, "code_aster")
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        stress = np.asarray(raw.get("stress_global"), dtype=float)
        if stress.shape != (case.elements.shape[0], 6):
            raise RuntimeError(
                "Code_Aster did not return one SIEF_ELGA stress vector per TETRA4 element; "
                f"got {stress.shape}, expected {(case.elements.shape[0], 6)}."
            )
        deck = write_calculix_orthotropic_input(work / "calculix.inp", case)
        _run_calculix(work, deck.stem)
        calculix_global = parse_calculix_nodal_stress(work / "calculix.frd", case.nodes.shape[0])
        return qf_stress, _material_s11(stress, case.angle_deg), qf_nodal, _material_s11(
            calculix_global, case.angle_deg
        )

    def _plot(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, len(rows), figsize=(12.0, 4.4), squeeze=False)
        for axis, row in zip(axes[0], rows, strict=True):
            distances = np.asarray(row["sampling_distances_m"], dtype=float)
            for level in row["levels"]:
                label = f"QF h={level['mesh_size']:.2f}"
                axis.plot(distances, level["qf_path_S11_pa"], "o-", label=label)
            fine = row["levels"][-1]
            axis.plot(distances, fine["code_aster_path_S11_pa"], "ks--", label="Code_Aster h fin")
            axis.set(title=str(row["id"]), xlabel="Distance physique [m]", ylabel="S11 materiau [Pa]")
            axis.grid(True, alpha=0.25)
            axis.legend(fontsize=7)
        figure.tight_layout()
        figure.savefig(self.output_dir / "stress_paths.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Les grandeurs d'acceptation sont `S11` dans les axes materiau, echantillonnees a des distances physiques fixes.",
            "Les pics locaux ne sont pas utilises comme critere de decision au coin rentrant.",
            "",
            "![Chemins de contrainte](stress_paths.png)",
            "",
        ]
        for row in summary["cases"]:
            assessment = row["assessment"]
            lines.extend(
                [
                    f"## {row['id']}",
                    "",
                    f"Classification : `{row['classification']}`. Verdict : **{assessment['status']}**.",
                    "",
                    "| Niveau | TET4 | h | Chemin QF/Aster | Bande QF/Aster | Chemin QF/CalculiX | Bande QF/CalculiX |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                ]
            )
            for level in row["levels"]:
                secondary = row["secondary_calculix_nodal_checks"][int(level["level"]) - 1]
                lines.append(
                    f"| h{level['level']} | {level['elements']} | {level['mesh_size']:.3f} | "
                    f"{100 * level['same_mesh_relative_path_error']:.4f} % | "
                    f"{100 * level['same_mesh_relative_band_error']:.4f} % | "
                    f"{100 * level['calculix_nodal_path_error']:.4f} % | "
                    f"{100 * level['calculix_nodal_band_error']:.4f} % "
                    f"({secondary['status']}) |"
                )
            lines.extend(
                [
                    "",
                    f"Regle de pic : `{assessment['point_peak_rule']}`.",
                    "",
                    "La correlation Code_Aster aux points d'integration est bloquante. "
                    "La comparaison nodale CalculiX est diagnostique car les operateurs "
                    "de recuperation ne sont pas identiques.",
                    "",
                ]
            )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def apply_external_oracle_policy(summary: dict[str, object]) -> dict[str, object]:
    """Apply the v2 blocking/diagnostic policy to stored numerical evidence."""
    comparison_limit = 0.05
    all_cases_pass = True
    for case in summary["cases"]:
        levels = case["levels"]
        primary = [
            {
                "id": f"same_mesh_code_aster_{level['level']}",
                "path_error": level["same_mesh_relative_path_error"],
                "band_error": level["same_mesh_relative_band_error"],
                "limit": comparison_limit,
                "status": "PASS"
                if max(float(level["same_mesh_relative_path_error"]), float(level["same_mesh_relative_band_error"]))
                <= comparison_limit
                else "FAIL",
            }
            for level in levels
        ]
        secondary = [
            {
                "id": f"same_mesh_calculix_nodal_{level['level']}",
                "path_error": level["calculix_nodal_path_error"],
                "band_error": level["calculix_nodal_band_error"],
                "limit": comparison_limit,
                "stress_recovery": "nodal_extrapolation",
                "status": "PASS"
                if max(float(level["calculix_nodal_path_error"]), float(level["calculix_nodal_band_error"]))
                <= comparison_limit
                else "WARNING",
            }
            for level in levels
        ]
        intrinsic_checks_pass = all(check["status"] == "PASS" for check in case["assessment"]["checks"])
        case_pass = intrinsic_checks_pass and all(item["status"] == "PASS" for item in primary)
        case["assessment"]["status"] = "PASS" if case_pass else "FAIL"
        case["same_mesh_code_aster_checks"] = primary
        case["secondary_calculix_nodal_checks"] = secondary
        case["secondary_comparison_policy"] = (
            "CalculiX nodal extrapolation is diagnostic because it is not the same "
            "stress-recovery operator as QF_solver volume averaging."
        )
        all_cases_pass = all_cases_pass and case_pass
    summary["status"] = "PASS_STRESS_ACCEPTANCE" if all_cases_pass else "FAIL"
    summary["acceptance_policy_revision"] = 2
    summary["blocking_external_oracle"] = "Code_Aster integration-point stress on the same mesh"
    summary["diagnostic_external_oracle"] = "CalculiX nodal extrapolated stress on the same mesh"
    return summary


def _sample_stress(
    centroids: np.ndarray,
    values: np.ndarray,
    point: tuple[float, float],
    direction: tuple[float, float],
    distances: tuple[float, ...],
    band: tuple[float, float],
    *,
    path_radius: float = 0.0,
    weights: np.ndarray | None = None,
) -> tuple[list[float], float]:
    """Sample one material stress component on fixed physical paths and bands."""
    xy = np.asarray(centroids[:, :2], dtype=float)
    origin = np.asarray(point, dtype=float)
    vector = np.asarray(direction, dtype=float)
    vector /= np.linalg.norm(vector)
    targets = np.asarray([origin + distance * vector for distance in distances], dtype=float)
    if weights is None:
        weights = np.ones(values.shape[0], dtype=float)
    if path_radius <= 0.0:
        path = [float(values[np.argmin(np.linalg.norm(xy - target, axis=1))]) for target in targets]
    else:
        path = []
        for target in targets:
            distances_to_target = np.linalg.norm(xy - target, axis=1)
            mask = distances_to_target <= path_radius
            if not np.any(mask):
                raise RuntimeError("No element centroid falls within a controlled stress path disk.")
            normalized = distances_to_target[mask] / path_radius
            kernel = np.square(1.0 - np.square(normalized))
            recovered_weights = weights[mask] * kernel
            if not np.any(recovered_weights > 0.0):
                raise RuntimeError("Controlled stress recovery produced zero compact-kernel weights.")
            path.append(float(np.average(values[mask], weights=recovered_weights)))
    radial = np.linalg.norm(xy - origin, axis=1)
    mask = (radial >= band[0]) & (radial <= band[1])
    if not np.any(mask):
        raise RuntimeError("No element centroid falls within the controlled stress averaging band.")
    return path, float(np.average(values[mask], weights=weights[mask]))


def _tetra_volumes(nodes: np.ndarray, elements: np.ndarray) -> np.ndarray:
    coords = nodes[elements]
    determinants = np.linalg.det(coords[:, 1:] - coords[:, :1])
    return np.abs(determinants) / 6.0


def _solve_qf_large(
    case: OrthotropicComplexCase,
    model: object,
    work: Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Solve and recover one refined case without Python result dictionaries."""
    from solveur.core.model import FiniteElementModel

    if not isinstance(model, FiniteElementModel):
        raise TypeError("Orthotropic large V&V requires a FiniteElementModel.")
    large = from_finite_element_model(model)
    model_path = save_large_model(large, work / "large_model.h5")
    solution_dir = work / "large_solution"
    solved = solve_large_tet4(
        large,
        output_dir=solution_dir,
        solver_backend="scipy",
        preconditioner="jacobi",
        chunk_size=8_192,
    )
    if solved.status != "PASS":
        raise RuntimeError(f"Large QF_solver failed for {case.identifier}: {solved.status}")
    post_dir = work / "large_postprocess"
    postprocess_large_tet4(
        model_path,
        solution_dir / solved.output_files["displacements"],
        post_dir,
        chunk_size=65_536,
        overwrite=True,
    )
    h5py = _h5py()
    with h5py.File(post_dir / "element_results.h5", "r") as results:
        global_stress = np.asarray(results["stress"], dtype=float)
        volumes = np.asarray(results["volume"], dtype=float)
    element_s11 = _material_s11(global_stress, case.angle_deg)
    nodal_s11 = _volume_weighted_nodal_recovery(
        case.nodes.shape[0],
        case.elements,
        element_s11,
        volumes,
    )
    return element_s11, nodal_s11, {
        "backend": solved.backend,
        "ndof": large.ndof,
        "solver": solved.summary["solver"],
        "assembly_time_seconds": solved.summary["assembly_time_seconds"],
        "solve_time_seconds": solved.summary["solve_time_seconds"],
    }


def _volume_weighted_nodal_recovery(
    node_count: int,
    elements: np.ndarray,
    values: np.ndarray,
    volumes: np.ndarray,
) -> np.ndarray:
    """Recover one scalar element field to nodes with bounded array storage."""
    connectivity = np.asarray(elements, dtype=np.int64)
    weighted = np.asarray(values, dtype=float) * np.asarray(volumes, dtype=float)
    sums = np.zeros(node_count, dtype=float)
    weights = np.zeros(node_count, dtype=float)
    np.add.at(sums, connectivity.reshape(-1), np.repeat(weighted, 4))
    np.add.at(weights, connectivity.reshape(-1), np.repeat(volumes, 4))
    if np.any(weights <= 0.0):
        raise RuntimeError("Refined stress recovery encountered an unconnected node.")
    return sums / weights


def _h5py() -> object:
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("Refined orthotropic V&V requires h5py.") from exc
    return h5py


def _material_s11(global_stress: np.ndarray, angle_deg: float) -> np.ndarray:
    angle = np.deg2rad(angle_deg)
    cosine, sine = np.cos(angle), np.sin(angle)
    rotation = np.array([[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])
    output = np.empty(global_stress.shape[0], dtype=float)
    for index, value in enumerate(global_stress):
        sx, sy, sz, txy, tyz, txz = value
        tensor = np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)
        output[index] = float((rotation.T @ tensor @ rotation)[0, 0])
    return output


def parse_calculix_nodal_stress(path: str | Path, node_count: int) -> np.ndarray:
    """Read the final nodal six-component stress block from a CalculiX FRD file."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    headers = [index for index, line in enumerate(lines) if line.startswith(" -4  STRESS")]
    if not headers:
        raise RuntimeError("CalculiX FRD contains no nodal STRESS block.")
    result = np.full((node_count, 6), np.nan, dtype=float)
    for line in lines[headers[-1] + 1 :]:
        if line.startswith(" -3"):
            break
        if not line.startswith(" -1"):
            continue
        numbers = _frd_numbers(line)
        if len(numbers) != 7:
            continue
        node = int(numbers[0]) - 1
        if 0 <= node < node_count:
            result[node] = numbers[1:]
    if not np.all(np.isfinite(result)):
        raise RuntimeError("CalculiX FRD stress block is incomplete for the requested nodes.")
    return result


def _frd_numbers(line: str) -> list[float]:
    return [float(value) for value in re.findall(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][+-]?\d+)?", line[3:])]


def _relative_vector(value: list[float], reference: list[float]) -> float:
    left, right = np.asarray(value, dtype=float), np.asarray(reference, dtype=float)
    return float(np.linalg.norm(left - right) / max(np.linalg.norm(right), np.finfo(float).tiny))


def _relative_scalar(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(value), abs(reference), np.finfo(float).tiny)
