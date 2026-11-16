"""Copy J9 development evidence into a path-sanitized, reproducible bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = ROOT / ".codex/development-runs/worktrees/j9"
RESULT_ROOT = ROOT / "research/j9/results/diagnostic-2026-11-16"
HEX_SERIES = "dev-j9-hex8-distortion-20261116-01"
MODAL_SERIES = "dev-j9-tet10-newmark-20261116-01"
DIRECT_SERIES = "dev-j9-tet10-direct-only-20261116-01"
HEX_PREFLIGHT = "pf-f4b9d0310d27"
MODAL_PREFLIGHT = "pf-7c21a48ef3d0"
DIRECT_PREFLIGHT = "pf-b8257c4b620e"
OWNER_MANDATE = "QF_SOLVER_0.3.0_J9_OWNER_2026-11-16"
HEX_NODEID = "tests/verification/test_j9_hex8_controlled_distortion.py::test_j9_hex8_constant_domain_distortion_sweep"
MODAL_NODEID = "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_and_modal_newmark_time_mesh_study"
DIRECT_NODEID = "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_newmark_time_mesh_study"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _copy_outputs(series: str, output_name: str, destination: Path, expected: list[str]) -> dict[str, Any]:
    source = RUN_ROOT / series / "attempt-0001/output" / output_name
    destination.mkdir(parents=True, exist_ok=True)
    for name in expected:
        source_file = source / name
        if not source_file.is_file():
            raise FileNotFoundError(f"Expected J9 output is missing: {source_file.name}")
        shutil.copy2(source_file, destination / name)
    return _read_json(destination / "result.json")


def _sanitize_threadpools(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ("user_api", "internal_api", "num_threads", "version", "prefix")
    return [{key: row[key] for key in keys if key in row} for row in rows]


def _preflight_receipt(preflight_id: str, nodeid: str, destination: Path) -> dict[str, Any]:
    folder = RUN_ROOT / "preflight" / preflight_id
    source = _read_json(folder / "preflight.json")
    sidecar = _read_json(folder / "preflight.sha256.json")
    if sidecar.get("sha256") != _sha256(folder / "preflight.json"):
        raise ValueError(f"Preflight checksum mismatch for {preflight_id}")
    if source.get("state") != "PREFLIGHT_PASS" or source.get("target") != nodeid:
        raise ValueError(f"Preflight does not authorize the expected exact node: {preflight_id}")
    sanitized = {
        "schema": "qf-j9-sanitized-preflight-v1",
        "preflight_id": preflight_id,
        "state": source["state"],
        "nodeid": nodeid,
        "source_head": source["identity"]["head"],
        "source_fingerprint": source["source_fingerprint"],
        "receipt_sha256": sidecar["sha256"],
        "started_at_utc": source["started_at_utc"],
        "finished_at_utc": source["finished_at_utc"],
        "elapsed_seconds": source["elapsed_seconds"],
        "thread_environment": source["thread_environment"],
        "threadpools": _sanitize_threadpools(source["threadpool_info"]),
        "peak_rss_bytes": source["peak_rss_bytes"],
        "peak_process_count": source["peak_process_count"],
        "stdout_bytes": source["stdout_bytes"],
        "stdout_sha256": source["stdout_sha256"],
        "stderr_bytes": source["stderr_bytes"],
        "stderr_sha256": source["stderr_sha256"],
        "archive_bytes": source["archive_bytes"],
        "temporary_bytes": source["temporary_bytes"],
        "free_disk_before_bytes": source["free_disk_before_bytes"],
        "free_disk_after_bytes": source["free_disk_after_bytes"],
        "command_root_relative": [
            "python",
            "scripts/development_autonomous.py",
            "preflight",
            "--worktree",
            "j9",
            "--target",
            nodeid,
            "--preflight-id",
            preflight_id,
        ],
    }
    _write_json(destination / "preflight_receipt.json", sanitized)
    return sanitized


def _run_receipt(
    series: str,
    preflight_id: str,
    nodeid: str,
    destination: Path,
    *,
    contract_sha256: str,
) -> dict[str, Any]:
    attempt_dir = RUN_ROOT / series / "attempt-0001"
    run = _read_json(attempt_dir / "run.json")
    preflight = _preflight_receipt(preflight_id, nodeid, destination)
    output_entries = []
    for item in run.get("output_inventory", []):
        relative = Path(item["path"])
        if relative.parts[0] in {"stdout.log", "stderr.log"}:
            continue
        if relative.parts[0] not in {"j9_hex8_constant_domain", "j9_tet10_newmark"}:
            continue
        output_entries.append({
            "path": Path(*relative.parts[1:]).as_posix(),
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        })
    controller_sha = run["controller_provenance"]["sha256"]
    runtime = run["controller_provenance"]["runtime"]
    sanitized = {
        "schema": "qf-j9-sanitized-run-receipt-v1",
        "series_id": series,
        "attempt": run["attempt"],
        "mandate_id": run["mandate_id"],
        "owner_mandate_id": OWNER_MANDATE,
        "branch": run["identity"]["branch"],
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "nodeid": nodeid,
        "execution_state": run["state"],
        "return_code": run["return_code"],
        "reason": run["reason"],
        "command_root_relative": [
            "python",
            "scripts/development_autonomous.py",
            "test",
            "--scope",
            "fem_exploratory",
            "--worktree",
            "j9",
            "--target",
            nodeid,
            "--preflight-id",
            preflight_id,
            "--series",
            series,
            "--reason",
            run["reason"],
        ],
        "contract_sha256": contract_sha256,
        "preflight": {
            "preflight_id": preflight_id,
            "state": preflight["state"],
            "receipt_sha256": preflight["receipt_sha256"],
        },
        "started_at_utc": run["started_at_utc"],
        "finished_at_utc": run["finished_at_utc"],
        "elapsed_seconds": run["elapsed_seconds"],
        "budgets": run["budgets"],
        "resources_observed": {
            "peak_rss_bytes": run["peak_rss_bytes"],
            "peak_rss_mib": run["peak_rss_bytes"] / (1024.0 * 1024.0),
            "peak_process_count": run["peak_process_count"],
            "archive_bytes": run["archive_bytes"],
            "temporary_bytes": run["temporary_bytes"],
            "stdout_bytes": run["stdout_bytes"],
            "stdout_sha256": run["stdout_sha256"],
            "stderr_bytes": run["stderr_bytes"],
            "stderr_sha256": run["stderr_sha256"],
        },
        "runtime": {
            "python_version": runtime["python_version"],
            "pytest_version": runtime["pytest_version"],
            "psutil_version": runtime["psutil_version"],
            "runner_sha256": controller_sha["runner"],
            "pytest_plugin_sha256": controller_sha["pytest_plugin"],
            "local_policy_sha256": controller_sha["policy"],
            "threadpools": preflight["threadpools"],
        },
        "outputs": output_entries,
        "raw_runner_record": "retained only in the ignored local development-run store; it contains local paths",
    }
    _write_json(destination / "run_receipt.json", sanitized)
    return sanitized


def _write_modal_failure(destination: Path) -> dict[str, Any]:
    series = MODAL_SERIES
    attempt_dir = RUN_ROOT / series / "attempt-0001"
    run = _read_json(attempt_dir / "run.json")
    preflight = _preflight_receipt(MODAL_PREFLIGHT, MODAL_NODEID, destination)
    stdout_path = attempt_dir / "output/stdout.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    raw_failure_line = next(
        (line.strip() for line in stdout.splitlines() if "ModalResidualValidationError:" in line),
        None,
    )
    failure_line = (
        raw_failure_line[raw_failure_line.index("ModalResidualValidationError:"):]
        if raw_failure_line is not None
        else None
    )
    expected_reason = "reason=aggregate_work_budget"
    if failure_line is None or expected_reason not in failure_line:
        raise ValueError("The historical modal-route failure no longer matches the registered diagnosis")
    contract = ROOT / "research/j9_transient/contracts/tet10_newmark_transient_contract.json"
    sanitized = {
        "schema": "qf-j9-modal-route-failure-v1",
        "classification": "DEVELOPMENT_ROUTE_FAILURE_NOT_SCIENTIFIC_FAIL",
        "series_id": series,
        "attempt": run["attempt"],
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "nodeid": MODAL_NODEID,
        "execution_state": run["state"],
        "return_code": run["return_code"],
        "owner_mandate_id": OWNER_MANDATE,
        "reason": run["reason"],
        "command_root_relative": [
            "python",
            "scripts/development_autonomous.py",
            "test",
            "--scope",
            "fem_exploratory",
            "--worktree",
            "j9",
            "--target",
            MODAL_NODEID,
            "--preflight-id",
            MODAL_PREFLIGHT,
            "--series",
            MODAL_SERIES,
            "--reason",
            run["reason"],
        ],
        "contract_path": "research/j9_transient/contracts/tet10_newmark_transient_contract.json",
        "contract_sha256": _sha256(contract),
        "preflight": {
            "preflight_id": MODAL_PREFLIGHT,
            "state": preflight["state"],
            "receipt_sha256": preflight["receipt_sha256"],
        },
        "started_at_utc": run["started_at_utc"],
        "finished_at_utc": run["finished_at_utc"],
        "elapsed_seconds": run["elapsed_seconds"],
        "budgets": run["budgets"],
        "resources_observed": {
            "peak_rss_bytes": run["peak_rss_bytes"],
            "peak_rss_mib": run["peak_rss_bytes"] / (1024.0 * 1024.0),
            "peak_process_count": run["peak_process_count"],
            "archive_bytes": run["archive_bytes"],
            "temporary_bytes": run["temporary_bytes"],
            "stdout_bytes": run["stdout_bytes"],
            "stdout_sha256": run["stdout_sha256"],
            "stderr_bytes": run["stderr_bytes"],
            "stderr_sha256": run["stderr_sha256"],
        },
        "failure": {
            "exception": "ModalResidualValidationError",
            "message": failure_line.removeprefix("ModalResidualValidationError: ").strip(),
            "stage": "full-order modal basis validation after the coarse-mesh direct time steps and before fine-mesh processing or final serialization",
            "free_dofs_at_refusal": 108,
            "prior_work_completed": "three coarse-mesh direct Newmark histories were computed in memory; no response artifact was written",
            "fine_mesh_attempted": False,
            "solves_or_acceptance": "not a numerical PASS or FAIL for TET10 mechanics; the modal route was outside its declared bounded validation-work domain",
        },
        "raw_stdout_log": {
            "path": "retained only in the ignored local development-run store",
            "bytes": run["stdout_bytes"],
            "sha256": run["stdout_sha256"],
        },
    }
    _write_json(destination / "modal_route_failure.json", sanitized)
    return sanitized


def _hex_plan_grid(axis: Any, coordinates: np.ndarray, ijk: np.ndarray, *, title: str, xlim: tuple[float, float]) -> None:
    node_id = {tuple(map(int, index)): i for i, index in enumerate(ijk)}
    k = 1
    for j in range(3):
        points = np.asarray([coordinates[node_id[(i, j, k)]] for i in range(5)])
        axis.plot(points[:, 0], points[:, 1], color="#235c78", linewidth=1.5)
    for i in range(5):
        points = np.asarray([coordinates[node_id[(i, j, k)]] for j in range(3)])
        axis.plot(points[:, 0], points[:, 1], color="#78838b", linewidth=0.8)
    axis.set(xlim=xlim, ylim=(-0.05, 1.05), xlabel="x [m]", ylabel="y [m]", title=title)
    axis.grid(True, alpha=0.2)
    axis.set_aspect(4.0, adjustable="box")


def _plot_hex8(folder: Path) -> None:
    result = _read_json(folder / "result.json")
    with np.load(folder / "hex8_distortion_states.npz") as states:
        coordinates = states["coordinates_m"]
        ijk = states["ijk"]
    alpha = [float(row["distortion_amplitude_fraction_of_height"]) for row in result["levels"]]
    conditions = np.asarray([float(row["condition_2_free_stiffness_estimate"]) for row in result["levels"]])
    errors = [float(row["free_displacement_error_relative_to_exact_l2"]) for row in result["levels"]]
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 7.0))
    _hex_plan_grid(axes[0, 0], coordinates[0], ijk, title="α = 0 · plan z = 0.5 m · y ×4 visuellement", xlim=(0.0, 20.0))
    _hex_plan_grid(axes[0, 1], coordinates[-1], ijk, title="α = 0.15 · zone médiane agrandie", xlim=(8.0, 12.0))
    # Overlay the regular interior row in the zoom panel to show the physical shift.
    regular = np.asarray([coordinates[0][i] for i, index in enumerate(ijk) if tuple(index) in {(i, 1, 1) for i in range(5)}])
    distorted = np.asarray([coordinates[-1][i] for i, index in enumerate(ijk) if tuple(index) in {(i, 1, 1) for i in range(5)}])
    axes[0, 1].plot(regular[:, 0], regular[:, 1], "o--", color="#9a6a24", linewidth=1.0, label="rangée intérieure α=0")
    axes[0, 1].plot(distorted[:, 0], distorted[:, 1], "o-", color="#235c78", linewidth=1.5, label="rangée intérieure α=0.15")
    axes[0, 1].legend(fontsize=8, loc="upper left")
    condition_change_percent = 100.0 * (conditions / conditions[0] - 1.0)
    axes[1, 0].plot(alpha, condition_change_percent, "s-", color="#b24e22")
    axes[1, 0].axhline(0.0, color="#555555", linewidth=0.8, linestyle=":")
    axes[1, 0].set(
        xlabel="Amplitude α [hauteur]",
        ylabel="Variation κ₂(Kff) vs α=0 [%]",
        title="Variation relative du conditionnement",
        ylim=(-0.01, 0.04),
    )
    axes[1, 0].grid(True, alpha=0.25)
    axes[1, 1].semilogy(alpha, errors, "o-", color="#486b58")
    axes[1, 1].set(xlabel="Amplitude α [hauteur]", ylabel="Erreur L2 relative [–]", title="Déplacement intérieur vs champ affine")
    axes[1, 1].grid(True, which="both", alpha=0.25)
    figure.suptitle("HEX8-SRI · domaine extérieur constant · contrôle affine exploratoire", fontsize=14)
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    figure.savefig(folder / "site_hex8_distortion.png", dpi=180)
    plt.close(figure)


def _plot_tet_mesh(folder: Path) -> None:
    with np.load(folder / "tet10_newmark_states.npz") as states:
        meshes = [
            (states["coarse_coordinates_m"], states["coarse_connectivity_tet10"]),
            (states["fine_coordinates_m"], states["fine_connectivity_tet10"]),
        ]
    figure = plt.figure(figsize=(10.4, 5.0))
    for index, (coordinates, connectivity) in enumerate(meshes):
        axis = figure.add_subplot(1, 2, index + 1, projection="3d")
        edges: set[tuple[int, int]] = set()
        for tet in connectivity:
            for left in range(4):
                for right in range(left + 1, 4):
                    edges.add(tuple(sorted((int(tet[left]), int(tet[right])))))
        for left, right in edges:
            axis.plot(*coordinates[[left, right]].T, color="#668078", linewidth=0.55, alpha=0.50)
        corners = np.asarray([[0.0, 0.0, 0.0], [0.0, 0.4, 0.0], [0.0, 0.4, 0.4], [0.0, 0.0, 0.4]])
        axis.plot(*np.vstack((corners, corners[0])).T, color="#236b8e", linewidth=2.2, label="encastrement x=0")
        axis.scatter([2.0], [0.2], [0.2], color="#c44834", s=30, label="force nodale −Z")
        axis.set(xlim=(0.0, 2.0), ylim=(0.0, 0.4), zlim=(0.0, 0.4))
        axis.set_xticks([0.0, 1.0, 2.0])
        axis.set_yticks([])
        axis.set_zticks([])
        axis.set_xlabel("x [m]", labelpad=2)
        axis.set_ylabel("")
        axis.set_zlabel("")
        axis.set_box_aspect((2.0, 0.4, 0.4))
        axis.set_proj_type("ortho")
        axis.view_init(elev=22, azim=-55)
        axis.set_title(f"TET10 · {2 if index == 0 else 4}×1×1 boîtes · section 0.4×0.4 m")
        if index == 0:
            axis.legend(loc="upper left", fontsize=7)
    figure.suptitle("Console 3D · TET10 · encastrement et force nodale impulsionnelle", fontsize=13)
    figure.subplots_adjust(left=0.01, right=0.96, bottom=0.08, top=0.86, wspace=0.16)
    figure.savefig(folder / "site_tet10_mesh.png", dpi=180)
    plt.close(figure)


def _plot_tet_history(folder: Path) -> None:
    result = _read_json(folder / "result.json")
    rows = list(csv.DictReader((folder / "tet10_newmark_history.csv").open(encoding="utf-8", newline="")))
    periods = {tuple(level["cells"]): float(level["period_s"]) for level in result["mesh_levels"]}
    figure, axes = plt.subplots(1, 2, figsize=(11.8, 4.8))
    for cells in ("2x1x1", "4x1x1"):
        direct = [row for row in rows if row["route"] == "direct_newmark" and row["cells"] == cells and int(row["steps_per_period"]) == 64]
        oracle = [row for row in rows if row["route"] == "direct_newmark" and row["cells"] == cells and int(row["steps_per_period"]) == 64]
        if not direct or not oracle:
            raise ValueError(f"Missing 64-step histories for mesh {cells}")
        # The CSV stores one QF and oracle value in each row; split the common time column into the two histories.
        period = periods[tuple(map(int, cells.split("x")))]
        time = np.asarray([float(row["time_s"]) / period for row in direct])
        actual = np.asarray([float(row["tip_uz_qf_m"]) * 1.0e6 for row in direct])
        reference = np.asarray([float(row["tip_uz_oracle_m"]) * 1.0e6 for row in oracle])
        axes[0].plot(time, actual, label=f"QF {cells}")
        axes[0].plot(time, reference, linestyle="--", label=f"oracle {cells}")
    axes[0].set(xlabel="Temps / période propre du maillage [–]", ylabel="UZ au bout [µm]", title="Historique à 64 pas par période")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    steps = [16, 32, 64]
    for level in result["mesh_levels"]:
        error = [float(row["rms_normalized_to_reference_peak"]) for row in level["time_levels"]]
        axes[1].loglog(steps, error, "o-", label=f"{level['cells'][0]} boîtes axiales")
        for row, value in zip(level["time_levels"], error, strict=True):
            axes[1].annotate(f"{100*value:.2g}%", (row["steps_per_period"], value), xytext=(4, 4), textcoords="offset points", fontsize=7)
    axes[1].set(xlabel="Pas par première période discrète [–]", ylabel="Erreur RMS / pic oracle [–]", title="Sensibilité temporelle · oracle par maillage")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(fontsize=8)
    figure.suptitle("TET10 · Newmark direct · comparaison semi-discrète exacte", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.93))
    figure.savefig(folder / "site_tet10_newmark.png", dpi=180)
    plt.close(figure)


def _build_manifest() -> None:
    rows = []
    for path in sorted(RESULT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "sha256_manifest.json":
            continue
        rows.append({
            "path": path.relative_to(RESULT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    _write_json(RESULT_ROOT / "sha256_manifest.json", {
        "schema": "qf-j9-artifact-manifest-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "files": rows,
    })


def _build_site_data() -> None:
    hex_folder = RESULT_ROOT / "hex8_constant_domain"
    tet_folder = RESULT_ROOT / "tet10_newmark_direct"
    hex_result = _read_json(hex_folder / "result.json")
    tet_result = _read_json(tet_folder / "result.json")
    hex_contract = ROOT / "research/j9_hex8/contracts/hex8_constant_domain_distortion_contract.json"
    tet_contract = ROOT / "research/j9_transient/contracts/tet10_newmark_direct_contract.json"
    payload = {
        "schema": "qf-j9-gallery-data-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "publication_status": "PREPARED_NOT_PUBLISHED",
        "models": [
            {
                "id": "J9-HEX8-SRI-AFFINE-DISTORTION",
                "title": "HEX8-SRI · distorsion intérieure à domaine constant",
                "execution_status": hex_result["execution_status"],
                "validation_status": "EXPLORATORY_PATCH_ONLY",
                "source_head": hex_result["source_head"],
                "contract_path": "research/j9_hex8/contracts/hex8_constant_domain_distortion_contract.json",
                "contract_sha256": hex_result["contract_sha256"],
                "geometry_m": hex_result["model"]["geometry_m"],
                "mesh_divisions": hex_result["model"]["mesh_divisions"],
                "material": hex_result["model"]["material"],
                "reference": {
                    "kind": "analytical homogeneous 3D affine elasticity field",
                    "stress_pa": [100.0, 0.0, 0.0],
                    "axial_reaction_n": 100.0,
                    "strain_energy_j": 0.1,
                    "limits": "does not exercise a non-affine field or validate the general HEX8-SRI formulation",
                },
                "measurements": hex_result["levels"],
                "figures": [
                    "hex8_constant_domain/site_hex8_distortion.png",
                    "hex8_constant_domain/hex8_distortion_study.png",
                ],
                "state_data": "hex8_constant_domain/hex8_distortion_states.npz",
                "external_solver_correlation": None,
            },
            {
                "id": "J9-TET10-NEWMARK-CANTILEVER",
                "title": "TET10 · cantilever 3D soumis à une impulsion nodale",
                "execution_status": tet_result["execution_status"],
                "validation_status": "TEMPORAL_INTEGRATION_VS_SEMIDISCRETE_ORACLE_ONLY",
                "source_head": tet_result["source_head"],
                "contract_path": "research/j9_transient/contracts/tet10_newmark_direct_contract.json",
                "contract_sha256": tet_result["contract_sha256"],
                "geometry_m": tet_result["model"]["geometry_m"],
                "material": tet_result["model"]["material"],
                "boundary_condition": tet_result["model"]["boundary_condition"],
                "load": tet_result["model"]["load"],
                "newmark": tet_result["model"]["newmark"],
                "reference": tet_result["reference"],
                "mesh_levels": tet_result["mesh_levels"],
                "modal_route_attempt": {
                    "status": "PYTEST_FAILED",
                    "record": "tet10_modal_route_failure/modal_route_failure.json",
                    "meaning": "full-basis modal validation exceeded its aggregate work budget; not a scientific mechanics verdict",
                },
                "figures": [
                    "tet10_newmark_direct/site_tet10_mesh.png",
                    "tet10_newmark_direct/site_tet10_newmark.png",
                ],
                "history_data": "tet10_newmark_direct/tet10_newmark_history.csv",
                "state_data": "tet10_newmark_direct/tet10_newmark_states.npz",
                "external_solver_correlation": None,
            },
        ],
        "contracts": [
            {"path": str(hex_contract.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha256(hex_contract)},
            {"path": str(tet_contract.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha256(tet_contract)},
        ],
        "historical_status": "J7 HEX8-SRI FAIL verdicts are unchanged",
    }
    _write_json(RESULT_ROOT / "site_data.json", payload)


def prepare() -> None:
    hex_folder = RESULT_ROOT / "hex8_constant_domain"
    tet_folder = RESULT_ROOT / "tet10_newmark_direct"
    modal_folder = RESULT_ROOT / "tet10_modal_route_failure"
    hex_result = _copy_outputs(
        HEX_SERIES,
        "j9_hex8_constant_domain",
        hex_folder,
        ["result.json", "result.sha256.json", "hex8_distortion_states.npz", "hex8_distortion_study.png"],
    )
    tet_result = _copy_outputs(
        DIRECT_SERIES,
        "j9_tet10_newmark",
        tet_folder,
        ["result.json", "result.sha256.json", "tet10_newmark_states.npz", "tet10_newmark_history.csv", "tet10_newmark_mesh.png", "tet10_newmark_history.png"],
    )
    for folder, result, series, preflight, nodeid in (
        (hex_folder, hex_result, HEX_SERIES, HEX_PREFLIGHT, HEX_NODEID),
        (tet_folder, tet_result, DIRECT_SERIES, DIRECT_PREFLIGHT, DIRECT_NODEID),
    ):
        expected = _read_json(folder / "result.sha256.json")["sha256"]
        if expected != _sha256(folder / "result.json"):
            raise ValueError(f"Result checksum mismatch in {folder.name}")
        if result["source_head"] != _read_json(RUN_ROOT / series / "attempt-0001/run.json")["identity"]["head"]:
            raise ValueError(f"Result source commit mismatch in {folder.name}")
        contract_sha = result["contract_sha256"]
        _run_receipt(series, preflight, nodeid, folder, contract_sha256=contract_sha)
    _write_modal_failure(modal_folder)
    _plot_hex8(hex_folder)
    _plot_tet_mesh(tet_folder)
    _plot_tet_history(tet_folder)
    _build_site_data()
    _build_manifest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plots-only",
        action="store_true",
        help="regenerate site figures from the versioned result bundle without reading local runner records",
    )
    arguments = parser.parse_args()
    if arguments.plots_only:
        _plot_hex8(RESULT_ROOT / "hex8_constant_domain")
        _plot_tet_mesh(RESULT_ROOT / "tet10_newmark_direct")
        _plot_tet_history(RESULT_ROOT / "tet10_newmark_direct")
        _build_site_data()
        _build_manifest()
    else:
        prepare()
