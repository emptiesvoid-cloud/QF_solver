"""Prepare the archived J13 TET10 flexure case for an Abaqus comparison.

This script validates an archived mesh and its equivalent nodal tip load,
then writes an Abaqus/Standard C3D10 direct-dynamic input deck and descriptive
QF/Euler--Bernoulli artifacts. It does not invoke a finite-element solver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"
MODEL_INPUTS = DATA_DIR / "j13_tet10_8x4x4_model_inputs.npz"
QF_HISTORY = DATA_DIR / "j13_tet10_8x4x4_qf_history.npz"
QF_RESULT = DATA_DIR / "j13_tet10_8x4x4_qf_result.json"
EXPECTED_INPUT_SHA256 = "c2bc590c8bbadaf1497b8c7f005c062f416ab9844d85fc130bb19523f02476ae"
EXPECTED_HISTORY_SHA256 = "7bb5da33a9e1625a76a54194087ee960868eede297a8aba1d66dcabf56090b33"
EXPECTED_RESULT_SHA256 = "86b77096fb2e3cd49de3b4ffad9bedef88772f7b8aceaee6fa702aee7d8f5263"

ELEMENT_EDGE_LOCAL_PAIRS = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
TIP_X_M = 2.0
TIP_FORCE_N = 100.0
SECTION_AREA_M2 = 0.01
PULSE_KNOTS_S_FACTOR = ((0.0, 0.0), (0.01, 1.0), (0.02, 0.0), (0.08, 0.0))
DT_S = 1.0e-4
END_TIME_S = 0.08


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_model_inputs(path: Path = MODEL_INPUTS) -> dict[str, np.ndarray]:
    """Load the frozen mesh after checking its known archive identity."""
    actual_hash = sha256_file(path)
    if actual_hash != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"model input archive SHA-256 mismatch: expected {EXPECTED_INPUT_SHA256}, got {actual_hash}"
        )
    with np.load(path, allow_pickle=False) as archive:
        arrays = {
            "coordinates": np.asarray(archive["coordinates_nx8_ny4_nz4_m"], dtype=np.float64),
            "connectivity": np.asarray(archive["connectivity_nx8_ny4_nz4_tet10"], dtype=np.int64),
            "corner_volumes": np.asarray(archive["corner_volumes_nx8_ny4_nz4_m3"], dtype=np.float64),
            "archived_nodal_force": np.asarray(archive["nodal_force_nx8_ny4_nz4_n"], dtype=np.float64),
        }
    validate_mesh(arrays)
    return arrays


def validate_mesh(arrays: dict[str, np.ndarray]) -> None:
    coordinates = arrays["coordinates"]
    connectivity = arrays["connectivity"]
    volumes = arrays["corner_volumes"]
    archived_force = arrays["archived_nodal_force"]
    if coordinates.shape != (1377, 3) or connectivity.shape != (768, 10):
        raise ValueError(f"unexpected mesh dimensions: coordinates={coordinates.shape}, connectivity={connectivity.shape}")
    if volumes.shape != (768,) or archived_force.shape != coordinates.shape:
        raise ValueError("unexpected volume or archived load dimensions")
    if not all(np.all(np.isfinite(array)) for array in arrays.values()):
        raise ValueError("mesh archive contains non-finite values")
    if int(connectivity.min()) < 0 or int(connectivity.max()) >= len(coordinates):
        raise ValueError("connectivity contains an out-of-range zero-based node index")
    expected_bounds = np.asarray(((0.0, 0.0, 0.0), (2.0, 0.1, 0.1)))
    if not np.allclose(np.vstack((coordinates.min(axis=0), coordinates.max(axis=0))), expected_bounds, rtol=0.0, atol=1e-12):
        raise ValueError("mesh bounds do not match the J13 2.0 x 0.1 x 0.1 m model")

    calculated_volumes = []
    for element in connectivity:
        a, b, c, d = coordinates[element[:4]]
        determinant = float(np.linalg.det(np.column_stack((b - a, c - a, d - a))))
        if determinant <= 0.0:
            raise ValueError("TET10 corner node order is not positively oriented")
        calculated_volumes.append(determinant / 6.0)
        for edge_index, (local_a, local_b) in enumerate(ELEMENT_EDGE_LOCAL_PAIRS, start=4):
            expected_midpoint = 0.5 * (coordinates[element[local_a]] + coordinates[element[local_b]])
            if not np.allclose(coordinates[element[edge_index]], expected_midpoint, rtol=0.0, atol=1e-12):
                raise ValueError("TET10 midside-node ordering does not match C3D10 edges 1-2, 2-3, 3-1, 1-4, 2-4, 3-4")
    if not np.allclose(calculated_volumes, volumes, rtol=1e-12, atol=1e-16):
        raise ValueError("stored corner volumes do not match the archived tetrahedral geometry")


def _midpoint_node(element: np.ndarray, node_a: int, node_b: int) -> int:
    for edge_index, (local_a, local_b) in enumerate(ELEMENT_EDGE_LOCAL_PAIRS, start=4):
        pair = {int(element[local_a]), int(element[local_b])}
        if pair == {node_a, node_b}:
            return int(element[edge_index])
    raise ValueError(f"edge ({node_a}, {node_b}) is absent from a boundary TET10")


def integrate_uniform_tip_load(
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    resultant_n: float = TIP_FORCE_N,
    target_area_m2: float = SECTION_AREA_M2,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Integrate constant +Z traction over quadratic end-face triangles.

    For a quadratic triangular face, exact integration of each shape function
    gives zero resultant weight at corner nodes and A/3 at each midside node.
    """
    face_elements: dict[tuple[int, int, int], np.ndarray] = {}
    for element in connectivity:
        tip_vertices = [int(node) for node in element[:4] if math.isclose(float(coordinates[node, 0]), TIP_X_M, rel_tol=0.0, abs_tol=1e-12)]
        if len(tip_vertices) == 3:
            face_elements[tuple(sorted(tip_vertices))] = element
    if len(face_elements) != 32:
        raise ValueError(f"expected 32 end-face triangles, found {len(face_elements)}")

    face_area = 0.0
    nodal_force = np.zeros_like(coordinates)
    triangle_areas = []
    for vertices in sorted(face_elements):
        element = face_elements[vertices]
        p0, p1, p2 = coordinates[list(vertices)]
        area = 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
        if area <= 0.0:
            raise ValueError("degenerate triangle on the loaded end face")
        face_area += area
        triangle_areas.append(area)
        for node_a, node_b in ((vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], vertices[0])):
            midside = _midpoint_node(element, node_a, node_b)
            nodal_force[midside, 2] += (resultant_n / target_area_m2) * area / 3.0

    if not math.isclose(face_area, target_area_m2, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"integrated end-face area {face_area:.17g} m^2 does not match {target_area_m2:.17g} m^2")
    resultant = np.sum(nodal_force, axis=0)
    centroid = np.asarray((TIP_X_M, 0.05, 0.05))
    moment = np.sum(np.cross(coordinates - centroid, nodal_force), axis=0)
    audit = {
        "face_triangle_count": len(face_elements),
        "face_area_m2": face_area,
        "traction_pa": resultant_n / target_area_m2,
        "recomputed_resultant_n": resultant.tolist(),
        "moment_about_loaded_face_centroid_nm": moment.tolist(),
        "quadratic_face_integration": "constant traction, exact shape-function integrals: corner weights 0, each midside weight A/3",
        "triangle_area_min_max_m2": [min(triangle_areas), max(triangle_areas)],
    }
    return nodal_force, audit


def validate_archived_load(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, Any]]:
    recomputed, audit = integrate_uniform_tip_load(arrays["coordinates"], arrays["connectivity"])
    difference = recomputed - arrays["archived_nodal_force"]
    max_difference = float(np.max(np.abs(difference)))
    sum_difference = float(np.sum(np.abs(difference)))
    archive_resultant = np.sum(arrays["archived_nodal_force"], axis=0)
    audit.update(
        {
            "archived_resultant_n": archive_resultant.tolist(),
            "archive_load_max_abs_difference_n": max_difference,
            "archive_load_l1_difference_n": sum_difference,
        }
    )
    if max_difference > 1e-13:
        raise ValueError(f"independent end-face load integration differs from archived load by {max_difference:.6g} N")
    if not np.allclose(archive_resultant, (0.0, 0.0, TIP_FORCE_N), rtol=0.0, atol=1e-12):
        raise ValueError(f"archived load resultant is not 100 N in +Z: {archive_resultant}")
    if float(np.linalg.norm(audit["moment_about_loaded_face_centroid_nm"])) > 1e-12:
        raise ValueError("recomputed end-face load has nonzero moment about its centroid")
    return recomputed, audit


def _format_node_ids(ids: list[int], prefix: str = "") -> list[str]:
    lines = []
    for start in range(0, len(ids), 12):
        lines.append(prefix + ", ".join(str(node_id) for node_id in ids[start : start + 12]))
    return lines


def render_abaqus_input(arrays: dict[str, np.ndarray], nodal_force: np.ndarray) -> str:
    coordinates = arrays["coordinates"]
    connectivity = arrays["connectivity"]
    fixed_nodes = [int(index + 1) for index in np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1e-12))]
    midspan = np.flatnonzero(np.all(np.isclose(coordinates, (1.0, 0.05, 0.05), rtol=0.0, atol=1e-12), axis=1))
    tip = np.flatnonzero(np.all(np.isclose(coordinates, (2.0, 0.05, 0.05), rtol=0.0, atol=1e-12), axis=1))
    if len(midspan) != 1 or len(tip) != 1:
        raise ValueError("the two J13 physical probe positions must each map to exactly one mesh node")
    loaded = [(int(index + 1), float(nodal_force[index, 2])) for index in range(len(nodal_force)) if abs(float(nodal_force[index, 2])) > 0.0]

    lines = [
        "*HEADING",
        "J23 prepared independent-comparison deck: J13 TET10 8x4x4 flexure, no local solver run",
        "** Source mesh SHA-256: " + EXPECTED_INPUT_SHA256,
        "** QF history SHA-256: " + EXPECTED_HISTORY_SHA256,
        "** Load vector is independently re-integrated from the quadratic end-face triangles.",
        "** CLOAD reproduces the archived equivalent nodal vector; it does not test Abaqus distributed-load integration.",
        "*MATERIAL, NAME=ELASTIC_SOLID",
        "*DENSITY",
        "7800.",
        "*ELASTIC",
        "210000000000., 0.3",
        "*PART, NAME=BEAM",
        "*NODE",
    ]
    for label, (x, y, z) in enumerate(coordinates, start=1):
        lines.append(f"{label}, {x:.17g}, {y:.17g}, {z:.17g}")
    lines.extend(("*ELEMENT, TYPE=C3D10, ELSET=ALL_ELEMENTS",))
    for label, element in enumerate(connectivity, start=1):
        abaqus_nodes = ", ".join(str(int(node) + 1) for node in element)
        lines.append(f"{label}, {abaqus_nodes}")
    lines.extend(
        (
            "*SOLID SECTION, ELSET=ALL_ELEMENTS, MATERIAL=ELASTIC_SOLID",
            ",",
            "*END PART",
            "*ASSEMBLY, NAME=ASSEMBLY",
            "*INSTANCE, NAME=BEAM-1, PART=BEAM",
            "*END INSTANCE",
            "*NSET, NSET=FIXED_NODES, INSTANCE=BEAM-1",
            *_format_node_ids(fixed_nodes),
            "*NSET, NSET=MIDSPAN_PROBE, INSTANCE=BEAM-1",
            str(int(midspan[0]) + 1),
            "*NSET, NSET=TIP_PROBE, INSTANCE=BEAM-1",
            str(int(tip[0]) + 1),
            "*NSET, NSET=PROBE_NODES, INSTANCE=BEAM-1",
            f"{int(midspan[0]) + 1}, {int(tip[0]) + 1}",
            "*END ASSEMBLY",
            "*AMPLITUDE, NAME=TIP_PULSE, DEFINITION=TABULAR, TIME=STEP TIME",
        )
    )
    for time_s, factor in PULSE_KNOTS_S_FACTOR:
        lines.append(f"{time_s:.17g}, {factor:.17g}")
    lines.extend(
        (
            "*STEP, NAME=TRANSIENT, NLGEOM=NO",
            "*DYNAMIC, DIRECT, ALPHA=0.0, BETA=0.25, GAMMA=0.5",
            f"{DT_S:.17g}, {END_TIME_S:.17g}, {DT_S:.17g}, {DT_S:.17g}",
            "*BOUNDARY",
            "FIXED_NODES, 1, 3, 0.0",
            "*CLOAD, AMPLITUDE=TIP_PULSE",
        )
    )
    for node_label, force_z in loaded:
        lines.append(f"BEAM-1.{node_label}, 3, {force_z:.17g}")
    lines.extend(
        (
            "*OUTPUT, FIELD, NUMBER INTERVAL=800, TIME MARKS=YES",
            "*NODE OUTPUT",
            "U, V, A",
            "*NODE OUTPUT, NSET=FIXED_NODES",
            "RF",
            "*END STEP",
            "",
        )
    )
    deck = "\n".join(lines)
    if any(len(line) > 256 for line in lines):
        raise ValueError("generated Abaqus input contains a line exceeding 256 characters")
    return deck


def export_qf_reference(history_path: Path, csv_path: Path, metrics_path: Path, plot_path: Path) -> dict[str, Any]:
    if sha256_file(history_path) != EXPECTED_HISTORY_SHA256:
        raise ValueError("QF history archive SHA-256 does not match the frozen J13 case")
    with np.load(history_path, allow_pickle=False) as archive:
        times = np.asarray(archive["times_s"], dtype=np.float64)
        values = {
            "midspan": (
                np.asarray(archive["qf_midspan_center_displacement"], dtype=np.float64),
                np.asarray(archive["eb_midspan_center_displacement_m"], dtype=np.float64),
            ),
            "tip": (
                np.asarray(archive["qf_tip_center_displacement"], dtype=np.float64),
                np.asarray(archive["eb_tip_center_displacement_m"], dtype=np.float64),
            ),
        }
    if times.shape != (800,) or not np.allclose(times, np.arange(1, 801) * DT_S, rtol=0.0, atol=1e-12):
        raise ValueError("archived QF time points do not match 800 Newmark increments of 0.1 ms")
    if any(qf.shape != times.shape or eb.shape != times.shape for qf, eb in values.values()):
        raise ValueError("probe histories do not match the archived time vector")

    output_times = np.concatenate(([0.0], times))
    columns = ["time_s"]
    for probe in ("midspan", "tip"):
        columns.extend((f"qf_{probe}_uz_m", f"eb_{probe}_uz_m"))
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for index, time_s in enumerate(output_times):
            row: list[float] = [float(time_s)]
            for probe in ("midspan", "tip"):
                qf, eb = values[probe]
                row.extend((0.0, 0.0) if index == 0 else (float(qf[index - 1]), float(eb[index - 1])))
            writer.writerow([format(value, ".17g") for value in row])

    metrics: dict[str, Any] = {
        "status": "DESCRIPTIVE_ARCHIVED_QF_VS_EULER_BERNOULLI",
        "sample_count_including_initial_zero": len(output_times),
        "dt_s": DT_S,
        "normalization": "RMS and maximum absolute QF-minus-Euler-Bernoulli history differences divided by the Euler-Bernoulli peak absolute displacement at the same physical probe over 0-80 ms; no pointwise division near zero.",
        "probes": {},
    }
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    for axis, probe in zip(axes, ("midspan", "tip")):
        qf, eb = values[probe]
        qf_full = np.concatenate(([0.0], qf))
        eb_full = np.concatenate(([0.0], eb))
        error = qf - eb
        denominator = float(np.max(np.abs(eb)))
        if denominator <= 0.0:
            raise ValueError(f"Euler-Bernoulli peak is zero at {probe}; normalized descriptive error is undefined")
        metrics["probes"][probe] = {
            "qf_peak_abs_m": float(np.max(np.abs(qf))),
            "qf_peak_time_s": float(times[int(np.argmax(np.abs(qf)))]),
            "euler_bernoulli_peak_abs_m": denominator,
            "euler_bernoulli_peak_time_s": float(times[int(np.argmax(np.abs(eb)))]),
            "rms_abs_difference_m": float(np.sqrt(np.mean(error**2))),
            "max_abs_difference_m": float(np.max(np.abs(error))),
            "rms_difference_normalized_to_eb_peak": float(np.sqrt(np.mean(error**2)) / denominator),
            "max_difference_normalized_to_eb_peak": float(np.max(np.abs(error)) / denominator),
        }
        axis.plot(output_times * 1e3, qf_full * 1e3, label="QF TET10, archived Newmark")
        axis.plot(output_times * 1e3, eb_full * 1e3, linestyle="--", label="Euler–Bernoulli continuous reference")
        axis.set_ylabel(f"{probe.capitalize()} $U_z$ (mm)")
        axis.grid(True, alpha=0.3)
        axis.legend(loc="best")
    axes[-1].set_xlabel("Physical time (ms)")
    figure.suptitle("J13 TET10 8×4×4 flexural pulse — archived QF result and Euler–Bernoulli reference")
    figure.savefig(plot_path, dpi=160)
    plt.close(figure)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def export_qf_reaction_checkpoints(result_path: Path, csv_path: Path, summary_path: Path) -> dict[str, Any]:
    """Export the actual stored J13 reaction/equilibrium checkpoints."""
    if sha256_file(result_path) != EXPECTED_RESULT_SHA256:
        raise ValueError("J13 QF result JSON SHA-256 does not match the frozen run")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    case = result["case_results"][0]
    equilibrium = case["equilibrium"]
    checkpoints = sorted(equilibrium["checkpoint_wrenches"], key=lambda item: float(item["time_s"]))
    if len(checkpoints) != 101 or not all(0.0 < float(point["time_s"]) <= END_TIME_S for point in checkpoints):
        raise ValueError("expected 101 archived positive-time equilibrium checkpoints in the 0-80 ms interval")
    duplicate_pairs = [
        (left, right)
        for left, right in zip(checkpoints, checkpoints[1:])
        if float(left["time_s"]) == float(right["time_s"])
    ]
    if len(duplicate_pairs) != 1 or duplicate_pairs[0][0] != duplicate_pairs[0][1]:
        raise ValueError("the only duplicate equilibrium time must be the exact repeated final checkpoint")
    columns = (
        "time_s",
        "qf_reaction_fx_n", "qf_reaction_fy_n", "qf_reaction_fz_n",
        "qf_reaction_mx_nm", "qf_reaction_my_nm", "qf_reaction_mz_nm",
        "qf_dynamic_balance_rx_n", "qf_dynamic_balance_ry_n", "qf_dynamic_balance_rz_n",
        "qf_dynamic_balance_mx_nm", "qf_dynamic_balance_my_nm", "qf_dynamic_balance_mz_nm",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for point in checkpoints:
            writer.writerow(
                [format(float(point["time_s"]), ".17g")]
                + [format(float(value), ".17g") for value in point["support_reaction_force_n"]]
                + [format(float(value), ".17g") for value in point["support_reaction_moment_nm"]]
                + [format(float(value), ".17g") for value in point["dynamic_balance_residual_force_n"]]
                + [format(float(value), ".17g") for value in point["dynamic_balance_residual_moment_nm"]]
            )
    summary = {
        "status": "ARCHIVED_QF_CHECKPOINTS",
        "source_result_sha256": EXPECTED_RESULT_SHA256,
        "source_commit": result["source_head"],
        "contract_id": result["contract_id"],
        "runner_series_id": result["runner_series_id"],
        "runner_execution_status": result["execution_status"],
        "checkpoint_count": len(checkpoints),
        "unique_checkpoint_count": len(checkpoints) - len(duplicate_pairs),
        "duplicate_time_s": [float(pair[0]["time_s"]) for pair in duplicate_pairs],
        "duplicate_terminal_checkpoint_identical": True,
        "checkpoint_stride_s": 0.0008,
        "maximum_force_balance_residual_norm_n": float(equilibrium["maximum_force_balance_residual_n"]),
        "maximum_moment_balance_residual_norm_nm": float(equilibrium["maximum_moment_balance_residual_nm"]),
        "interpretation": "These are stored J13 postprocessing observables at checkpoint times; they are not a new FEM run or a cross-solver result.",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def write_artifact_manifest(output_dir: Path) -> Path:
    """Hash the data, generated deck, preflight, and site-ready artifacts."""
    manifest_path = output_dir / "artifact_manifest.json"
    roots = (output_dir / "data", output_dir / "site_assets")
    files = [output_dir / "j23_tet10_transient_flexure.inp", output_dir / "load_preflight.json"]
    for root in roots:
        files.extend(path for path in root.rglob("*") if path.is_file())
    manifest = {
        "schema": "qf-j23-transient-flexure-artifacts-v1",
        "scope": "frozen input archives, generated Abaqus deck and load preflight, plus prepared site assets",
        "files": {
            path.relative_to(output_dir).as_posix(): {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(files)
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_package(data_dir: Path = DATA_DIR, output_dir: Path = PACKAGE_ROOT) -> dict[str, Any]:
    arrays = load_model_inputs(data_dir / MODEL_INPUTS.name)
    load, audit = validate_archived_load(arrays)
    deck = render_abaqus_input(arrays, load)
    output_dir.mkdir(parents=True, exist_ok=True)
    site_assets = output_dir / "site_assets"
    site_assets.mkdir(parents=True, exist_ok=True)
    (output_dir / "j23_tet10_transient_flexure.inp").write_text(deck, encoding="ascii", newline="\n")
    (output_dir / "load_preflight.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    metrics = export_qf_reference(
        data_dir / QF_HISTORY.name,
        site_assets / "qf_euler_bernoulli_probe_histories.csv",
        site_assets / "qf_euler_bernoulli_metrics.json",
        site_assets / "qf_euler_bernoulli_histories.png",
    )
    qf_equilibrium = export_qf_reaction_checkpoints(
        data_dir / QF_RESULT.name,
        site_assets / "qf_support_reaction_checkpoints.csv",
        site_assets / "qf_equilibrium_summary.json",
    )
    manifest_path = write_artifact_manifest(output_dir)
    return {
        "load_audit": audit,
        "qf_eb_metrics": metrics,
        "qf_equilibrium": qf_equilibrium,
        "deck_sha256": sha256_file(output_dir / "j23_tet10_transient_flexure.inp"),
        "artifact_manifest_sha256": sha256_file(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=PACKAGE_ROOT)
    arguments = parser.parse_args()
    result = build_package(arguments.data_dir, arguments.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
