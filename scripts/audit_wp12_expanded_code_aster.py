"""Independent raw-evidence audit for WP12 R3 expanded correlations.

Only Python's standard library, NumPy, and SciPy sparse file readers are used.
This auditor does not import QF Solver, the R3 model builder, or its runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

import numpy as np
from scipy.sparse import load_npz


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _canonical_model_hash(
    family: str, coordinates: np.ndarray, connectivity: np.ndarray, fixed: np.ndarray, loads: np.ndarray, material: dict[str, Any]
) -> str:
    digest = hashlib.sha256()
    digest.update(family.encode("ascii"))
    for values, dtype in (
        (coordinates, np.float64),
        (connectivity, np.int64),
        (fixed, np.int64),
        (loads, np.float64),
    ):
        array = np.asarray(values, dtype=dtype)
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes(order="C"))
    digest.update(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def _relative_l2(actual: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(actual - reference) / max(float(np.linalg.norm(reference)), float(np.finfo(float).tiny)))


def _relative_linf(actual: np.ndarray, reference: np.ndarray) -> float:
    return float(
        np.max(np.abs(actual - reference), initial=0.0)
        / max(float(np.max(np.abs(reference), initial=0.0)), float(np.finfo(float).tiny))
    )


def _expected_aster_type(family: str) -> str:
    return {"TET4": "TETRA4", "TET10": "TETRA10", "HEX8": "HEXA8", "HEX20": "HEXA20"}[family]


def _aster_to_canonical_order(family: str) -> tuple[int, ...]:
    if family == "HEX20":
        aster_order: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17)
    else:
        aster_order = tuple(range({"TET4": 4, "TET10": 10, "HEX8": 8}[family]))
    return tuple(aster_order.index(index) for index in range(len(aster_order)))


def _decode_aster_identifier(identifier: str) -> int:
    if not re.fullmatch(r"[A-Z]+", identifier):
        raise ValueError(f"invalid alphabetic Code_Aster identifier: {identifier!r}")
    value = 0
    for character in identifier:
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def _audit_mesh_text(path: Path, family: str, coordinates: np.ndarray, connectivity: np.ndarray) -> list[str]:
    errors: list[str] = []
    lines = path.read_text(encoding="ascii").splitlines()
    try:
        coord_start = lines.index("COOR_3D") + 1
        coord_end = lines.index("FINSF", coord_start)
        parsed_coordinates = []
        for line in lines[coord_start:coord_end]:
            parts = line.split()
            parsed_coordinates.append((parts[0], tuple(float(value) for value in parts[1:4])))
        if len(parsed_coordinates) != len(coordinates):
            errors.append("Code_Aster mesh node count differs from raw input arrays")
        else:
            try:
                node_ids = [_decode_aster_identifier(name) for name, _ in parsed_coordinates]
            except ValueError:
                node_ids = []
            if node_ids != list(range(len(coordinates))):
                errors.append("Code_Aster mesh node names/order differ from raw input arrays")
            if not np.array_equal(np.asarray([row for _, row in parsed_coordinates]), coordinates):
                errors.append("Code_Aster mesh coordinates differ from raw input arrays")
        element_type_index = coord_end + 1
        if lines[element_type_index] != _expected_aster_type(family):
            errors.append("Code_Aster mesh element type differs from raw model family")
        element_end = lines.index("FINSF", element_type_index + 1)
        parsed_elements = []
        parsed_element_ids = []
        for line in lines[element_type_index + 1 : element_end]:
            parts = line.split()
            if not parts:
                continue
            try:
                parsed_element_ids.append(_decode_aster_identifier(parts[0]))
                parsed_elements.append([_decode_aster_identifier(name) for name in parts[1:]])
            except ValueError:
                errors.append("Code_Aster mesh contains an invalid alphabetic node/element identifier")
        if parsed_element_ids != list(range(len(connectivity))):
            errors.append("Code_Aster element names/order differ from raw input connectivity")
        permutation = _aster_to_canonical_order(family)
        canonical = np.asarray([[row[permutation[index]] for index in range(len(permutation))] for row in parsed_elements], dtype=np.int64)
        if canonical.shape != connectivity.shape or not np.array_equal(canonical, connectivity):
            errors.append("Code_Aster mesh connectivity differs from raw input arrays")
        root_start = lines.index("ROOT", element_end + 1) + 1
        root_end = lines.index("FINSF", root_start)
        root_names = lines[root_start:root_end]
        try:
            root_nodes = np.asarray([_decode_aster_identifier(name) for name in root_names], dtype=np.int64)
        except ValueError:
            errors.append("Code_Aster root group contains an invalid alphabetic node identifier")
            root_nodes = np.asarray([], dtype=np.int64)
        expected_root = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1e-12))
        if not np.array_equal(root_nodes, expected_root):
            errors.append("Code_Aster root boundary group differs from raw coordinates")
    except (ValueError, IndexError, TypeError) as exc:
        errors.append(f"Code_Aster mesh cannot be parsed: {type(exc).__name__}: {exc}")
    return errors


def _audit_comm_text(path: Path, loads: np.ndarray, material: dict[str, Any], case_id: str) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    expected_e = f"E={float(material['E']):.17g}"
    expected_nu = f"NU={float(material['nu']):.17g}"
    if expected_e not in text or expected_nu not in text:
        errors.append("Code_Aster material fields differ from frozen material")
    if 'GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0' not in text:
        errors.append("Code_Aster fixed-boundary condition is absent or different")
    if f'"case_id": "{case_id}"' not in text or "MECA_STATIQUE" not in text:
        errors.append("Code_Aster command does not identify this case or perform MECA_STATIQUE")
    observed: dict[tuple[int, int], float] = {}
    force_dof = {"FX": 0, "FY": 1, "FZ": 2}
    for node_text, component, value_text in re.findall(r'NOEUD="([A-Z]+)"\s*,\s*(FX|FY|FZ)=([-+0-9.eE]+)', text):
        observed[(_decode_aster_identifier(node_text), force_dof[component])] = float(value_text)
    expected = {
        (node, axis): float(value)
        for node, vector in enumerate(loads)
        for axis, value in enumerate(vector)
        if float(value) != 0.0
    }
    if set(observed) != set(expected) or any(observed[key] != expected[key] for key in expected):
        errors.append("Code_Aster nodal force terms differ from the frozen QF nodal load vector")
    return errors


def _audit_case(
    case_root: Path,
    case_contract: dict[str, Any],
    contract: dict[str, Any],
    contract_sha: str,
    execution_sha: str | None,
) -> dict[str, Any]:
    case_id = str(case_contract["case_id"])
    errors: list[str] = []
    try:
        case = load_json(case_root / "case.json")
        result = load_json(case_root / "result.json")
        process = load_json(case_root / "process.json")
        raw = load_json(case_root / "aster_raw.json")
        with np.load(case_root / "model_inputs.npz", allow_pickle=False) as payload:
            coordinates = np.asarray(payload["coordinates"], dtype=np.float64)
            connectivity = np.asarray(payload["connectivity"], dtype=np.int64)
            fixed = np.asarray(payload["fixed"], dtype=np.int64)
            loads = np.asarray(payload["loads"], dtype=np.float64)
        with np.load(case_root / "qf_result.npz", allow_pickle=False) as payload:
            qf_displacement = np.asarray(payload["displacement"], dtype=np.float64)
        stiffness = load_npz(case_root / "qf_stiffness.npz").tocsr()
        aster_displacement = np.asarray(raw.get("displacement"), dtype=np.float64)
        aster_reaction = np.asarray(raw.get("reaction"), dtype=np.float64)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL_CLOSED", "errors": [f"missing/invalid raw case evidence: {type(exc).__name__}: {exc}"]}

    family = str(case_contract["family"])
    node_count = int(case_contract["nodes"])
    dof_count = int(case_contract["dofs"])
    element_nodes = {"TET4": 4, "HEX8": 8, "TET10": 10, "HEX20": 20}.get(family)
    expected_dimensions = tuple(float(value) for value in case_contract["dimensions_m"])
    if case.get("case_id") != case_id or result.get("case_id") != case_id or raw.get("case_id") != case_id:
        errors.append("case identity mismatch across raw files")
    if any(payload.get("family") != family for payload in (case, result, raw, process)):
        errors.append("element family mismatch across raw files")
    if case.get("dimensions_m") != list(expected_dimensions) or case.get("mesh") != case_contract.get("mesh"):
        errors.append("model geometry or mesh label differs from frozen case contract")
    if case.get("divisions") != case_contract.get("divisions") or case.get("load_case") != case_contract.get("load_case"):
        errors.append("raw case discretization/load label differs from frozen contract")
    if case.get("resultant_N") != case_contract.get("resultant_N"):
        errors.append("raw case resultant differs from frozen contract")
    if coordinates.shape != (node_count, 3) or loads.shape != (node_count * 3,) or qf_displacement.shape != (dof_count,):
        errors.append("raw QF array dimensions differ from frozen case dimensions")
    if connectivity.shape != (int(case_contract["elements"]), element_nodes or -1):
        errors.append("raw connectivity dimensions differ from frozen element family")
    if stiffness.shape != (dof_count, dof_count):
        errors.append("raw stiffness dimensions differ from frozen DOF count")
    if fixed.ndim != 1 or np.any(fixed < 0) or np.any(fixed >= dof_count) or np.unique(fixed).size != fixed.size:
        errors.append("fixed DOF vector is invalid")
    if np.any(connectivity < 0) or np.any(connectivity >= node_count):
        errors.append("connectivity references invalid node IDs")
    if not all(np.all(np.isfinite(value)) for value in (coordinates, loads, qf_displacement, aster_displacement, aster_reaction)):
        errors.append("non-finite value in raw evidence")
    if aster_displacement.shape != (node_count, 3) or aster_reaction.shape != (node_count, 3):
        errors.append("Code_Aster displacement/reaction shape mismatch")

    material = case.get("material", {})
    if material != contract.get("material"):
        errors.append("raw case material differs from frozen contract")
    actual_fingerprint = _canonical_model_hash(family, coordinates, connectivity, fixed, loads, material)
    if actual_fingerprint != case_contract.get("model_fingerprint") or case.get("model_fingerprint") != actual_fingerprint:
        errors.append("model fingerprint differs from frozen contract")
    if int(case.get("nodes", -1)) != node_count or int(case.get("elements", -1)) != int(case_contract["elements"]):
        errors.append("raw case node/element counts differ from frozen contract")
    if case.get("source_sha") != result.get("source_sha") or case.get("source_sha") != execution_sha:
        errors.append("source SHA differs from the execution SHA bound in the campaign summary")
    if result.get("runner_sha") != contract.get("runner_sha") or case.get("runner_sha") != contract.get("runner_sha"):
        errors.append("runner SHA mismatch")
    if result.get("contract_sha256") != contract_sha or case.get("contract_sha256") != contract_sha:
        errors.append("contract SHA-256 mismatch")
    if result.get("model_fingerprint") != actual_fingerprint:
        errors.append("result model fingerprint mismatch")
    if coordinates.shape == (node_count, 3) and loads.shape == (dof_count,):
        nodal_loads = loads.reshape(-1, 3)
        applied_resultant = np.sum(nodal_loads, axis=0)
        applied_moment = np.sum(np.cross(coordinates, nodal_loads), axis=0)
        declared_resultant = np.asarray(case_contract["resultant_N"], dtype=np.float64)
        declared_moment = np.asarray(case_contract["load_moment_origin_Nm"], dtype=np.float64)
        if not np.allclose(applied_resultant, declared_resultant, rtol=1e-12, atol=1e-10):
            errors.append("raw nodal loads do not preserve the frozen traction resultant")
        if not np.allclose(applied_moment, declared_moment, rtol=1e-12, atol=1e-10):
            errors.append("raw nodal loads do not preserve the frozen traction moment")
        loaded_nodes = np.flatnonzero(np.any(nodal_loads != 0.0, axis=1))
        distal_x = float(case_contract["dimensions_m"][0])
        if not loaded_nodes.size or not np.allclose(coordinates[loaded_nodes, 0], distal_x, rtol=0.0, atol=1e-12):
            errors.append("equivalent nodal traction is not confined to the frozen distal face")
        if not np.isclose(float(case.get("load_area_m2", np.nan)), float(case_contract["load_area_m2"]), rtol=1e-12, atol=1e-12):
            errors.append("raw load area differs from the frozen case contract")
    if result.get("status") != "PASS_CANDIDATE":
        errors.append(f"runner case status is {result.get('status')}, not PASS_CANDIDATE")

    if process.get("case_id") != case_id or process.get("exit_code") != 0 or process.get("fresh_container_process") is not True:
        errors.append("Code_Aster process completion/fresh-container evidence mismatch")
    if process.get("image") != contract.get("code_aster_image") or process.get("image_id") != contract.get("code_aster_image_id"):
        errors.append("Code_Aster image digest/ID mismatch")
    if not str(process.get("runtime_version", "")).startswith(f"code_aster {contract.get('code_aster_version')} "):
        errors.append("Code_Aster runtime version mismatch")
    if process.get("container_cpu_limit") != 1 or process.get("solver_mpi_disabled") is not True:
        errors.append("Code_Aster CPU/MPI constraints mismatch")
    if not isinstance(process.get("host_process_id"), int) or not isinstance(process.get("container_id"), str):
        errors.append("Code_Aster process/container identity is missing")
    cid_path = case_root / "container.cid"
    if not cid_path.is_file() or cid_path.read_text(encoding="ascii").strip() != process.get("container_id"):
        errors.append("Docker container ID file differs from process record")
    if result.get("process") != process:
        errors.append("result/process.json process metadata differ")
    command = process.get("command", [])
    if not isinstance(command, list) or contract.get("code_aster_image") not in command or "--cpus=1" not in command:
        errors.append("Docker execution command does not prove pinned image and one-CPU limit")
    telemetry_path = case_root / "telemetry.jsonl"
    try:
        telemetry = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
        elapsed = [float(row["elapsed_seconds"]) for row in telemetry]
        if (
            not telemetry
            or telemetry[0].get("event") != "RUN_START"
            or telemetry[-1].get("event") != "RUN_END"
            or any(row.get("case_id") != case_id for row in telemetry)
            or telemetry[-1].get("exit_code") != process.get("exit_code")
            or process.get("telemetry_events") != len(telemetry)
            or any(not np.isfinite(value) for value in elapsed)
            or any(right < left for left, right in zip(elapsed, elapsed[1:], strict=False))
        ):
            errors.append("process telemetry lifecycle/count/timing mismatch")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"process telemetry missing/invalid: {type(exc).__name__}: {exc}")
    if raw.get("status") != "PASS" or raw.get("family") != family or raw.get("element_type") != _expected_aster_type(family) or raw.get("modelisation") != "3D":
        errors.append("Code_Aster raw result type/status mismatch")

    for filename in (f"{case_id}.mail", f"{case_id}.comm", f"{case_id}.export"):
        if not (case_root / filename).is_file():
            errors.append(f"missing Code_Aster input file {filename}")
    if (case_root / f"{case_id}.mail").is_file():
        errors.extend(_audit_mesh_text(case_root / f"{case_id}.mail", family, coordinates, connectivity))
    if (case_root / f"{case_id}.comm").is_file():
        errors.extend(_audit_comm_text(case_root / f"{case_id}.comm", loads.reshape(-1, 3), material, case_id))

    metrics: dict[str, float] = {}
    if not errors:
        qf_residual = np.asarray(stiffness @ qf_displacement - loads, dtype=np.float64)
        qf_reaction = qf_residual.reshape(-1, 3)
        free_mask: np.ndarray = np.ones(dof_count, dtype=bool)
        free_mask[fixed] = False
        free_residual = qf_residual[free_mask]
        qf_u = qf_displacement.reshape(-1, 3)
        qf_f = loads.reshape(-1, 3)
        qf_energy = float(0.5 * qf_displacement @ (stiffness @ qf_displacement))
        aster_energy = float(0.5 * np.sum(qf_f * aster_displacement))
        qf_force = np.sum(qf_reaction + qf_f, axis=0)
        aster_force = np.sum(aster_reaction + qf_f, axis=0)
        qf_moment = np.sum(np.cross(coordinates, qf_reaction + qf_f), axis=0)
        aster_moment = np.sum(np.cross(coordinates, aster_reaction + qf_f), axis=0)
        load_scale = max(float(np.sum(np.linalg.norm(qf_f, axis=1))), 1.0)
        length_scale = max(float(np.max(np.ptp(coordinates, axis=0))), 1.0)
        fixed_nodes = np.unique(fixed // 3)
        tiny = float(np.finfo(float).tiny)
        metrics = {
            "displacement_relative_l2": _relative_l2(aster_displacement, qf_u),
            "displacement_relative_linf": _relative_linf(aster_displacement, qf_u),
            "reaction_relative_l2": _relative_l2(aster_reaction, qf_reaction),
            "reaction_relative_linf": _relative_linf(aster_reaction, qf_reaction),
            "strain_energy_from_external_work_relative": abs(aster_energy - qf_energy) / max(abs(qf_energy), tiny),
            "qf_free_residual_relative_l2": float(np.linalg.norm(free_residual) / load_scale),
            "qf_force_equilibrium_relative": float(np.linalg.norm(qf_force) / load_scale),
            "aster_force_equilibrium_relative": float(np.linalg.norm(aster_force) / load_scale),
            "qf_moment_equilibrium_relative": float(np.linalg.norm(qf_moment) / (load_scale * length_scale)),
            "aster_moment_equilibrium_relative": float(np.linalg.norm(aster_moment) / (load_scale * length_scale)),
            "fixed_displacement_abs_max": float(np.max(np.abs(aster_displacement[fixed_nodes]), initial=0.0)),
            "qf_energy_j": qf_energy,
            "aster_external_work_energy_j": aster_energy,
            "load_area_m2": float(case["load_area_m2"]),
        }
        for name, threshold in contract["gates"].items():
            value = metrics.get(name)
            if value is None or not np.isfinite(value) or value > float(threshold):
                errors.append(f"gate {name} failed: {value} > {threshold}")
        recorded = result.get("metrics", {})
        for name, value in metrics.items():
            previous = recorded.get(name)
            if not isinstance(previous, (int, float)) or not np.isclose(float(previous), value, rtol=1e-12, atol=1e-18):
                errors.append(f"recorded metric differs from independent recomputation: {name}")
        recorded_gates = result.get("comparisons", {})
        if set(recorded_gates) != set(contract["gates"]):
            errors.append("recorded gate set differs from frozen contract")
        else:
            for name, threshold in contract["gates"].items():
                gate = recorded_gates[name]
                expected_status = "PASS" if metrics[name] <= float(threshold) else "FAIL"
                if gate.get("limit") != threshold or gate.get("status") != expected_status or not np.isclose(
                    float(gate.get("value", np.nan)), metrics[name], rtol=1e-12, atol=1e-18
                ):
                    errors.append(f"recorded gate differs from independent recomputation: {name}")
        raw_hash = sha256_file(case_root / "aster_raw.json")
        if result.get("raw_sha256") != raw_hash:
            errors.append("Code_Aster raw result SHA-256 mismatch")

    return {
        "status": "PASS_CANDIDATE" if not errors else "FAIL_CLOSED",
        "metrics_recomputed_from_raw": metrics,
        "errors": errors,
    }


def audit(contract_path: Path, output_root: Path, repo_root: Path) -> dict[str, Any]:
    contract_path, output_root, repo_root = contract_path.resolve(), output_root.resolve(), repo_root.resolve()
    contract = load_json(contract_path)
    errors: list[str] = []
    contract_sha = sha256_file(contract_path)
    manifest_path = (repo_root / contract.get("manifest_path", "")).resolve()
    if repo_root not in manifest_path.parents:
        errors.append("frozen manifest path escapes repository")
    manifest: dict[str, Any] = {}
    if not manifest_path.is_file():
        errors.append("campaign manifest is missing")
    else:
        manifest = load_json(manifest_path).get("files", {})
        actual_files = {
            path.relative_to(output_root).as_posix()
            for path in output_root.rglob("*")
            if path.is_file() and path.name != "manifest.json"
        }
        if actual_files != set(manifest):
            errors.append("manifest file set does not match actual campaign files")
        for relative, entry in manifest.items():
            path = output_root / relative
            if not path.is_file() or sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("size_bytes"):
                errors.append(f"manifest hash/size mismatch: {relative}")
    try:
        summary = load_json(output_root / "wp12_expanded_summary.json")
        if summary.get("contract_sha256") != contract_sha:
            errors.append("summary contract digest mismatch")
        if summary.get("execution_sha") is None or summary.get("runner_sha") != contract.get("runner_sha"):
            errors.append("summary execution/runner provenance mismatch")
        if summary.get("branch") != contract.get("branch") or summary.get("contract_builder_sha") != contract.get("contract_builder_sha"):
            errors.append("summary branch/contract-builder provenance mismatch")
        try:
            subprocess.check_output(["git", "cat-file", "-e", f"{summary['execution_sha']}^{{commit}}"], cwd=repo_root)
            if subprocess.check_output(
                ["git", "rev-parse", f"{summary['execution_sha']}^"], cwd=repo_root, text=True
            ).strip() != contract.get("freeze_commit_sha"):
                errors.append("execution commit does not immediately follow the recorded preparation commit")
            for field in ("runner_sha", "model_builder_sha", "auditor_sha", "contract_builder_sha"):
                subprocess.check_output(["git", "cat-file", "-e", f"{contract[field]}^{{commit}}"], cwd=repo_root)
            if subprocess.run(
                ["git", "diff", "--quiet", contract["branch_base_sha"], summary["execution_sha"], "--", "src/"],
                cwd=repo_root,
                check=False,
            ).returncode != 0:
                errors.append("production source differs from frozen WP12 R3 branch base")
        except (subprocess.SubprocessError, KeyError):
            errors.append("summary execution/source SHA is not resolvable as a Git commit")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"summary missing/invalid: {type(exc).__name__}: {exc}")
        summary = {}

    expected_cases = contract.get("cases", [])
    if len(expected_cases) != contract.get("case_count"):
        errors.append("frozen contract case count is inconsistent")
    cases: dict[str, Any] = {}
    summary_cases = summary.get("cases", {})
    if set(summary_cases) != {item.get("case_id") for item in expected_cases}:
        errors.append("summary case coverage differs from frozen contract")
    for frozen in expected_cases:
        case_id = str(frozen.get("case_id"))
        case_root = output_root / case_id
        audit_result = _audit_case(case_root, frozen, contract, contract_sha, summary.get("execution_sha"))
        cases[case_id] = audit_result
        if audit_result["status"] != "PASS_CANDIDATE":
            errors.extend(f"{case_id}: {error}" for error in audit_result["errors"])
        recorded_summary = summary_cases.get(case_id, {})
        if recorded_summary.get("status") != audit_result["status"]:
            errors.append(f"{case_id}: summary status differs from independent audit")
    passed = sum(case["status"] == "PASS_CANDIDATE" for case in cases.values())
    if summary and summary.get("candidate_cases_passed") != passed:
        errors.append("summary candidate case count differs from independent audit")
    return {
        "work_package": "WP12",
        "campaign": "R3 expanded Code_Aster same-mesh correlation",
        "audit_status": "PASS_WITH_LIMITATIONS" if not errors and passed == len(expected_cases) else "FAIL_CLOSED",
        "case_count": len(expected_cases),
        "case_pass_count": passed,
        "official_points_changed": False,
        "contract_sha256": contract_sha,
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "cases": cases,
        "errors": errors,
        "limitations": contract.get("limitations", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--audit-output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else root / args.contract
    output_root = args.output_root if args.output_root.is_absolute() else root / args.output_root
    audit_path = args.audit_output if args.audit_output.is_absolute() else root / args.audit_output
    try:
        report = audit(contract_path, output_root, root)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"audit_status": report["audit_status"], "case_pass_count": report["case_pass_count"], "case_count": report["case_count"], "errors": report["errors"]}, indent=2))
        return 0 if report["audit_status"] == "PASS_WITH_LIMITATIONS" else 2
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"WP12_R3_AUDIT_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
