"""Independently audit WP12 raw Code_Aster correlations.

This checker deliberately does not import the QF solver or the WP12 runner. It
verifies immutable input/output hashes and recomputes all numerical comparisons
from the archived NumPy and JSON arrays.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


FAMILIES = ("TET4", "HEX8", "TET10", "HEX20")
EXPECTED_NODES = {"TET4": 4, "HEX8": 8, "TET10": 10, "HEX20": 20}
EXPECTED_DOFS = {"TET4": 12, "HEX8": 24, "TET10": 30, "HEX20": 60}
ASTER_TYPES = {"TET4": "TETRA4", "HEX8": "HEXA8", "TET10": "TETRA10", "HEX20": "HEXA20"}
ASTER_NODE_ORDER = {
    "TET4": tuple(range(4)),
    "HEX8": tuple(range(8)),
    "TET10": tuple(range(10)),
    "HEX20": (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17),
}
CODE_ASTER_PROFILE = (
    "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
    "owafurl325k3dbxls3s645zyfmvakxsg"
)
CODE_ASTER_RUNNER = f"{CODE_ASTER_PROFILE}/bin/run_aster"
SPACK_ROOT = "/opt/spack/opt/spack/linux-zen"
CODE_ASTER_IMAGE = (
    "simvia/code_aster@sha256:"
    "4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
)
INPUT_NAMES = ("result.json", "displacement.npy", "fixed.npy", "loads.npy", "stiffness.npy")
DEFAULT_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_contract.json")
DEFAULT_OUTPUT = Path("qualification/0_2_9/wp12_external_vv")
DEFAULT_AUDIT = Path("qualification/0_2_9/wp12_external_vv_audit.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return payload


def safe_path(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Path escapes repository root: {relative}")
    return resolved


def _expected_runtime_shell(runtime: dict[str, Any], solver_command: str) -> str:
    if (
        runtime.get("shell") != "/bin/bash"
        or runtime.get("profile_script") != f"{CODE_ASTER_PROFILE}/share/aster/profile.sh"
        or runtime.get("spack_root") != SPACK_ROOT
        or runtime.get("python_site_packages_pattern") != "*/lib/python3.11/site-packages"
        or runtime.get("shared_library_directory_names") != ["lib", "lib64"]
        or runtime.get("login_shell") is not True
    ):
        raise ValueError("WP12 runtime bootstrap differs from the verified Code_Aster image setup")
    return (
        f"export RUNASTER_ROOT={CODE_ASTER_PROFILE}; "
        f"source {runtime['profile_script']}; "
        f"export PYTHONPATH=$(find {runtime['spack_root']} -type d -path "
        f"'{runtime['python_site_packages_pattern']}' | paste -sd: -):${{PYTHONPATH:-}}; "
        f"export LD_LIBRARY_PATH=$(find {runtime['spack_root']} -type d "
        r"\( -name lib -o -name lib64 \) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        f"{solver_command}"
    )


def relative_l2(actual: np.ndarray, expected: np.ndarray) -> float:
    magnitude = float(np.linalg.norm(expected))
    denominator = magnitude if magnitude > 0.0 else float(np.finfo(np.float64).tiny)
    return float(np.linalg.norm(actual - expected)) / denominator


def relative_linf(actual: np.ndarray, expected: np.ndarray) -> float:
    magnitude = float(np.max(np.abs(expected), initial=0.0))
    denominator = magnitude if magnitude > 0.0 else float(np.finfo(np.float64).tiny)
    return float(np.max(np.abs(actual - expected), initial=0.0) / denominator)


def recompute_metrics(
    *,
    qf_displacement: np.ndarray,
    qf_fixed: np.ndarray,
    qf_loads: np.ndarray,
    qf_stiffness: np.ndarray,
    aster_displacement: np.ndarray,
    aster_reaction: np.ndarray,
    coordinates: np.ndarray,
) -> dict[str, float]:
    """Recompute external-correlation observables without solver imports."""

    qf_u = np.asarray(qf_displacement, dtype=np.float64).reshape(-1, 3)
    aster_u = np.asarray(aster_displacement, dtype=np.float64)
    aster_r = np.asarray(aster_reaction, dtype=np.float64)
    qf_f = np.asarray(qf_loads, dtype=np.float64).reshape(-1, 3)
    qf_k = np.asarray(qf_stiffness, dtype=np.float64)
    xyz = np.asarray(coordinates, dtype=np.float64)
    fixed_dofs = np.asarray(qf_fixed, dtype=np.int64)
    if qf_k.shape != (qf_u.size, qf_u.size):
        raise ValueError("QF stiffness shape does not match the displacement vector.")
    if aster_u.shape != qf_u.shape or aster_r.shape != qf_u.shape or xyz.shape != qf_u.shape:
        raise ValueError("External vector/coordinate shapes do not match the frozen family model.")
    if qf_f.shape != qf_u.shape or np.any(fixed_dofs < 0) or np.any(fixed_dofs >= qf_u.size):
        raise ValueError("QF load/fixed data has an invalid shape or index.")
    if not all(np.all(np.isfinite(item)) for item in (qf_u, aster_u, aster_r, qf_f, qf_k, xyz)):
        raise ValueError("Non-finite value in WP12 raw evidence.")

    qf_r = (qf_k @ qf_u.reshape(-1) - np.asarray(qf_loads, dtype=np.float64)).reshape(-1, 3)
    qf_balance = qf_r + qf_f
    aster_balance = aster_r + qf_f
    load_scale = max(float(np.sum(np.linalg.norm(qf_f, axis=1))), 1.0)
    length_scale = max(float(np.max(np.ptp(xyz, axis=0))), 1.0)
    fixed_nodes = np.unique(fixed_dofs // 3)
    qf_energy = float(0.5 * qf_displacement @ (qf_k @ qf_displacement))
    aster_work_energy = float(0.5 * np.sum(qf_f * aster_u))

    energy_scale = abs(qf_energy) if abs(qf_energy) > 0.0 else float(np.finfo(np.float64).tiny)
    return {
        "displacement_relative_l2": relative_l2(aster_u, qf_u),
        "displacement_relative_linf": relative_linf(aster_u, qf_u),
        "reaction_relative_l2": relative_l2(aster_r, qf_r),
        "reaction_relative_linf": relative_linf(aster_r, qf_r),
        "strain_energy_from_external_work_relative": abs(aster_work_energy - qf_energy)
        / energy_scale,
        "qf_force_equilibrium_relative": float(np.linalg.norm(np.sum(qf_balance, axis=0)) / load_scale),
        "aster_force_equilibrium_relative": float(np.linalg.norm(np.sum(aster_balance, axis=0)) / load_scale),
        "qf_moment_equilibrium_relative": float(
            np.linalg.norm(np.sum(np.cross(xyz, qf_balance), axis=0)) / (load_scale * length_scale)
        ),
        "aster_moment_equilibrium_relative": float(
            np.linalg.norm(np.sum(np.cross(xyz, aster_balance), axis=0)) / (load_scale * length_scale)
        ),
        "fixed_displacement_abs_max": float(np.max(np.abs(aster_u[fixed_nodes]), initial=0.0)),
        "qf_strain_energy": qf_energy,
        "aster_external_work_energy": aster_work_energy,
    }


def _expected_mail(family: str, spec: dict[str, Any]) -> str:
    coordinates = np.asarray(spec["coordinates"], dtype=np.float64)
    connectivity = np.asarray(spec["connectivity"], dtype=np.int64)
    lines = ["TITRE", f"WP12 external correlation {family}", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(coordinates)
    )
    lines.extend(["FINSF", ASTER_TYPES[family]])
    ordered = [int(connectivity[index]) for index in ASTER_NODE_ORDER[family]]
    lines.append("M1 " + " ".join(f"N{node + 1}" for node in ordered))
    lines.extend(["FINSF", "GROUP_MA", "SOLID", "M1", "FINSF"])
    for name, predicate in (
        ("ROOT", lambda point: abs(float(point[0])) <= 1.0e-14),
        ("LOAD", lambda point: abs(float(point[0]) - 1.0) <= 1.0e-14),
    ):
        names = [f"N{i + 1}" for i, point in enumerate(coordinates) if predicate(point)]
        lines.extend(["GROUP_NO", name, *names, "FINSF"])
    lines.extend(["GROUP_NO", "NALL", *(f"N{i + 1}" for i in range(len(coordinates))), "FINSF"])
    for index in range(len(coordinates)):
        lines.extend(["GROUP_NO", f"QF{index:03d}", f"N{index + 1}", "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _expected_comm(family: str, spec: dict[str, Any], material: dict[str, float], loads_vector: np.ndarray) -> str:
    loads = np.asarray(loads_vector, dtype=np.float64).reshape(-1, 3)
    terms = []
    for node, force in enumerate(loads):
        for component, value in zip(("FX", "FY", "FZ"), force, strict=True):
            if value != 0.0:
                terms.append(f'_F(NOEUD="N{node + 1}", {component}={float(value):.17g})')
    force_text = ",\n    ".join(terms)
    node_count = len(spec["coordinates"])
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={float(material['E']):.17g}, NU={float(material['nu']):.17g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    {force_text}
))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force)))
result = CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",))
depl = result.getField("DEPL", 1)
reac = result.getField("REAC_NODA", 1)
displacement = np.zeros(({node_count}, 3), dtype=float)
reaction = np.zeros(({node_count}, 3), dtype=float)
for node in range({node_count}):
    group = "QF%03d" % node
    for component, name in enumerate(("DX", "DY", "DZ")):
        values, _ = depl.getValuesWithDescription(name, [group])
        if len(values) != 1:
            raise RuntimeError("Expected one displacement value for " + group)
        displacement[node, component] = float(values[0])
        values, _ = reac.getValuesWithDescription(name, [group])
        if len(values) != 1:
            raise RuntimeError("Expected one reaction value for " + group)
        reaction[node, component] = float(values[0])
with open("/work/aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "status": "PASS",
        "family": "{family}",
        "element_type": "{ASTER_TYPES[family]}",
        "modelisation": "3D",
        "displacement": displacement.tolist(),
        "reaction": reaction.tolist(),
    }}, stream, indent=2, allow_nan=False)
FIN()
'''


def _expected_export(family: str, contract: dict[str, Any]) -> str:
    return "\n".join(
        (
            "P actions make_etude",
            f"P time_limit {int(contract['timeout_seconds'])}",
            f"P memory_limit {int(contract['memory_limit_mb'])}",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P mpi_nbnoeud 1",
            f"F comm /work/{family}.comm D 1",
            f"F mail /work/{family}.mail D 20",
            f"F mess /work/{family}.mess R 6",
            f"F resu /work/{family}.resu R 8",
            "",
        )
    )


def _validate_manifest(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return ["output manifest is missing"]
    manifest = load_json(manifest_path).get("files")
    if not isinstance(manifest, dict):
        return ["output manifest has no file map"]
    for relative, record in manifest.items():
        try:
            path = safe_path(root, str(relative))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"manifest file missing: {relative}")
        elif sha256_file(path) != record.get("sha256") or path.stat().st_size != record.get("size_bytes"):
            errors.append(f"manifest hash/size mismatch: {relative}")
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_files != set(manifest):
        missing = sorted(actual_files - set(manifest))
        stale = sorted(set(manifest) - actual_files)
        errors.append(f"manifest file coverage mismatch: unlisted={missing}, missing={stale}")
    return errors


def _load_family_input(repo_root: Path, output_root: Path, contract: dict[str, Any], family: str) -> tuple[dict[str, Any], dict[str, np.ndarray], list[str]]:
    errors: list[str] = []
    spec = contract["families"][family]
    snapshot = output_root / family / "qf_m1"
    arrays: dict[str, np.ndarray] = {}
    for name in INPUT_NAMES:
        path = snapshot / name
        if not path.is_file():
            errors.append(f"{family}: missing snapshotted WP11 M1 input {name}")
            continue
        actual = sha256_file(path)
        expected = spec["m1_file_hashes"].get(name)
        if actual != expected:
            errors.append(f"{family}: WP11 M1 snapshot hash mismatch for {name}")
        if name.endswith(".npy"):
            try:
                arrays[name] = np.load(path, allow_pickle=False)
            except (OSError, ValueError) as exc:
                errors.append(f"{family}: invalid NumPy input {name}: {exc}")
    result_path = snapshot / "result.json"
    result: dict[str, Any] = {}
    if result_path.is_file():
        try:
            result = load_json(result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{family}: invalid M1 result JSON: {exc}")
    if result.get("status") != "PASS" or result.get("element_family") != family:
        errors.append(f"{family}: WP11 M1 result is not accepted PASS evidence")
    if result.get("source_sha") != contract["wp11_source_sha"]:
        errors.append(f"{family}: WP11 source SHA mismatch")
    if result.get("model_fingerprint") != spec["model_fingerprint"]:
        errors.append(f"{family}: WP11 model fingerprint mismatch")
    coordinates = np.asarray(spec["coordinates"], dtype=np.float64)
    dof_count = 3 * len(coordinates)
    if (
        spec.get("element_type") != family
        or spec.get("aster_element_type") != ASTER_TYPES[family]
        or spec.get("nodes") != EXPECTED_NODES[family]
        or spec.get("elements") != 1
        or spec.get("dofs") != EXPECTED_DOFS[family]
        or dof_count != EXPECTED_DOFS[family]
    ):
        errors.append(f"{family}: frozen element family/dimensions mismatch")
    if tuple(spec.get("aster_local_node_order", ())) != ASTER_NODE_ORDER[family]:
        errors.append(f"{family}: frozen QF-to-Code_Aster local node permutation mismatch")
    if result.get("actual_nodes") != len(coordinates) or result.get("actual_dofs") != dof_count:
        errors.append(f"{family}: WP11 result dimensions differ from frozen WP12 geometry")
    connectivity = np.asarray(spec.get("connectivity", ()), dtype=np.int64)
    if connectivity.shape != (EXPECTED_NODES[family],) or not np.array_equal(
        np.sort(connectivity), np.arange(EXPECTED_NODES[family], dtype=np.int64)
    ):
        errors.append(f"{family}: frozen connectivity is not a one-element node permutation")
    if coordinates.shape != (EXPECTED_NODES[family], 3) or not np.all(np.isfinite(coordinates)):
        errors.append(f"{family}: frozen coordinate array has invalid shape or non-finite entries")
    if "fixed.npy" in arrays and not np.array_equal(
        np.asarray(arrays["fixed.npy"], dtype=np.int64), np.asarray(spec["fixed_dofs"], dtype=np.int64)
    ):
        errors.append(f"{family}: fixed DOFs differ from frozen WP12 contract")
    if "loads.npy" in arrays:
        expected_load: np.ndarray = np.zeros(dof_count, dtype=np.float64)
        dof_component = {"UX": 0, "UY": 1, "UZ": 2}
        for item in spec["nodal_loads"]:
            expected_load[3 * int(item["node"]) + dof_component[item["dof"]]] = float(item["value"])
        if not np.array_equal(np.asarray(arrays["loads.npy"], dtype=np.float64), expected_load):
            errors.append(f"{family}: applied nodal load differs from frozen WP12 contract")
    loaded_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 1.0, rtol=0.0, atol=1.0e-14))
    if not np.array_equal(loaded_nodes, np.asarray(spec["loaded_nodes"], dtype=np.int64)):
        errors.append(f"{family}: loaded node set differs from frozen WP12 contract")
    return result, arrays, errors


def audit(contract_path: Path, output_root: Path, repo_root: Path) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    output_root = output_root.resolve()
    repo_root = repo_root.resolve()
    contract = load_json(contract_path)
    errors = _validate_manifest(output_root)
    families: dict[str, Any] = {}
    external = contract.get("external_solver", {})
    if not isinstance(external, dict):
        external = {}
        errors.append("WP12 contract external_solver must be an object")
    runtime_bootstrap = external.get("runtime_bootstrap", {})
    if not isinstance(runtime_bootstrap, dict):
        runtime_bootstrap = {}
        errors.append("WP12 contract runtime_bootstrap must be an object")
    if (
        external.get("name") != "Code_Aster"
        or external.get("version") != contract.get("code_aster_version")
        or external.get("image") != contract.get("code_aster_image")
        or external.get("image_id") != contract.get("code_aster_image_id")
        or external.get("timeout_seconds") != contract.get("timeout_seconds")
        or external.get("memory_limit_mb") != contract.get("memory_limit_mb")
        or external.get("action") != contract.get("code_aster_action")
        or not isinstance(external.get("entrypoint"), str)
        or external.get("entrypoint", "").split("/")[-1] != "run_aster"
        or external.get("mpi") is not False
        or external.get("cpu_limit") != 1
        or external.get("fresh_container_per_family") is not True
        or contract.get("code_aster_action") != "make_etude"
    ):
        errors.append("WP12 contract Code_Aster action/runtime/resource fields are inconsistent")
    try:
        _expected_runtime_shell(runtime_bootstrap, f"{CODE_ASTER_RUNNER} --version")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"WP12 contract Code_Aster runtime bootstrap is invalid: {exc}")
    qf_reference = contract.get("qf_reference", {})
    if not isinstance(qf_reference, dict):
        qf_reference = {}
        errors.append("WP12 contract qf_reference must be an object")
    if (
        qf_reference.get("source_sha") != contract.get("wp11_source_sha")
        or qf_reference.get("owner_acceptance_path") != contract.get("wp11_owner_acceptance_path")
        or qf_reference.get("owner_acceptance_sha256") != contract.get("wp11_owner_acceptance_sha256")
        or qf_reference.get("owner_manifest_path") != contract.get("wp11_owner_manifest_path")
        or qf_reference.get("owner_manifest_sha256") != contract.get("wp11_owner_manifest_sha256")
        or qf_reference.get("contract_path") != contract.get("wp11_contract_path")
        or qf_reference.get("contract_sha256") != contract.get("wp11_contract_sha256")
    ):
        errors.append("WP11 input provenance fields disagree within frozen WP12 contract")

    owner_path = safe_path(repo_root, contract["wp11_owner_acceptance_path"])
    wp11_manifest_path = safe_path(repo_root, contract["wp11_owner_manifest_path"])
    wp11_contract_path = safe_path(repo_root, contract["wp11_contract_path"])
    for label, path, key in (
        ("WP11 Owner acceptance", owner_path, "wp11_owner_acceptance_sha256"),
        ("WP11 owner manifest", wp11_manifest_path, "wp11_owner_manifest_sha256"),
        ("WP11 frozen contract", wp11_contract_path, "wp11_contract_sha256"),
    ):
        if not path.is_file() or sha256_file(path) != contract[key]:
            errors.append(f"{label} hash mismatch or file missing")
    if owner_path.is_file():
        owner = load_json(owner_path)
        if (
            owner.get("status") != "CLOSED_OWNER_ACCEPTED_WITH_LIMITATIONS"
            or owner.get("owner_accepts_wp11_scope") is not True
            or owner.get("approved_points") != 6
        ):
            errors.append("WP11 Owner acceptance record does not confirm the accepted bounded scope")
    if wp11_manifest_path.is_file():
        wp11_manifest = load_json(wp11_manifest_path).get("manifest", {})
        for family in FAMILIES:
            for name, digest in contract["families"][family]["m1_file_hashes"].items():
                key = f"{family}\\M1\\{name}"
                if wp11_manifest.get(key) != digest:
                    errors.append(f"{family}: frozen WP11 owner manifest entry mismatch: {name}")

    summary_path = output_root / "wp12_summary.json"
    if not summary_path.is_file():
        errors.append("WP12 runner summary is missing")
        summary: dict[str, Any] = {}
    else:
        summary = load_json(summary_path)
        if summary.get("contract_sha256") != sha256_file(contract_path):
            errors.append("WP12 summary contract digest mismatch")
        if summary.get("runner_sha") != contract.get("runner_sha"):
            errors.append("WP12 summary runner SHA mismatch")
        if summary.get("branch") != contract.get("branch") or summary.get("branch_base_sha") != contract.get(
            "branch_base_sha"
        ):
            errors.append("WP12 summary branch/base provenance mismatch")
        try:
            subprocess.check_output(
                ["git", "cat-file", "-e", f"{summary.get('execution_sha')}^{{commit}}"],
                cwd=repo_root,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            errors.append("WP12 execution SHA is not a resolvable Git commit")

    for family in FAMILIES:
        family_errors: list[str] = []
        family_root = output_root / family
        result, qf, input_errors = _load_family_input(repo_root, output_root, contract, family)
        family_errors.extend(input_errors)
        spec = contract["families"][family]
        required = (
            f"{family}.mail",
            f"{family}.comm",
            f"{family}.export",
            "aster_raw.json",
            "stdout.log",
            "stderr.log",
            "process.json",
            "telemetry.jsonl",
            "progress.json",
            "comparison.json",
            "container.cid",
        )
        for filename in required:
            if not (family_root / filename).is_file():
                family_errors.append(f"missing family evidence: {filename}")
        for filename, expected_text in (
            (f"{family}.mail", _expected_mail(family, spec)),
            (f"{family}.comm", _expected_comm(family, spec, contract["material"], qf["loads.npy"])),
            (f"{family}.export", _expected_export(family, contract)),
        ):
            path = family_root / filename
            if path.is_file() and path.read_text(encoding="utf-8") != expected_text:
                family_errors.append(f"generated Code_Aster input differs from frozen contract: {filename}")

        raw: dict[str, Any] = {}
        raw_path = family_root / "aster_raw.json"
        if raw_path.is_file():
            try:
                raw = load_json(raw_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                family_errors.append(f"invalid raw Code_Aster JSON: {exc}")
        if (
            raw.get("status") != "PASS"
            or raw.get("family") != family
            or raw.get("element_type") != spec["aster_element_type"]
            or raw.get("modelisation") != "3D"
        ):
            family_errors.append("Code_Aster raw result family/type/modelisation mismatch")

        process_path = family_root / "process.json"
        process: dict[str, Any] = {}
        if process_path.is_file():
            try:
                process = load_json(process_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                family_errors.append(f"invalid process metadata: {exc}")
        if process:
            command = process.get("command", [])
            expected_runtime_shell = _expected_runtime_shell(
                runtime_bootstrap, f"{CODE_ASTER_RUNNER} {family}.export --no-mpi"
            )
            if (
                process.get("family") != family
                or process.get("image") != contract.get("code_aster_image")
                or process.get("image_id") != contract.get("code_aster_image_id")
                or not str(process.get("runtime_version", "")).startswith(f"code_aster {contract['code_aster_version']} ")
                or process.get("exit_code") != 0
                or process.get("fresh_container_process") is not True
                or process.get("container_cpu_limit") != 1
                or process.get("solver_mpi_disabled") is not True
                or not isinstance(process.get("host_process_id"), int)
                or process.get("solver_entrypoint") != external.get("entrypoint")
                or process.get("python_runtime_import_smoke") != "PASS"
                or process.get("runtime_shell_command") != expected_runtime_shell
                or not command
                or command[command.index("--entrypoint") + 1] != runtime_bootstrap.get("shell")
                or command[command.index(CODE_ASTER_IMAGE) + 1] != "-lc"
                or command[-1] != expected_runtime_shell
                or f"{family}.export" not in expected_runtime_shell
                or "--no-mpi" not in expected_runtime_shell
                or "--cpus=1" not in command
            ):
                family_errors.append("Code_Aster process provenance/resource constraints mismatch")
            cid_path = family_root / "container.cid"
            cid = cid_path.read_text(encoding="ascii").strip() if cid_path.is_file() else ""
            if not re.fullmatch(r"[0-9a-f]{64}", cid) or cid != process.get("container_id"):
                family_errors.append("Docker container ID is invalid or disagrees with process metadata")
            telemetry_path = family_root / "telemetry.jsonl"
            telemetry_rows: list[dict[str, Any]] = []
            if telemetry_path.is_file():
                try:
                    parsed_rows = [json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines()]
                    if any(not isinstance(row, dict) for row in parsed_rows):
                        raise ValueError("telemetry row is not a JSON object")
                    telemetry_rows = parsed_rows
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    family_errors.append(f"invalid telemetry JSONL: {exc}")
            if telemetry_rows:
                elapsed_values = [row.get("elapsed_seconds") for row in telemetry_rows]
                elapsed_is_numeric = all(isinstance(value, (int, float)) for value in elapsed_values)
                numeric_elapsed = [float(value) for value in elapsed_values if isinstance(value, (int, float))]
                elapsed_is_finite_monotone = elapsed_is_numeric and all(
                    np.isfinite(value) for value in numeric_elapsed
                ) and all(right >= left for left, right in zip(numeric_elapsed, numeric_elapsed[1:], strict=False))
                if (
                    telemetry_rows[0].get("event") != "RUN_START"
                    or telemetry_rows[-1].get("event") != "RUN_END"
                    or any(row.get("family") != family for row in telemetry_rows)
                    or process.get("telemetry_events") != len(telemetry_rows)
                    or not elapsed_is_finite_monotone
                    or telemetry_rows[-1].get("exit_code") != process.get("exit_code")
                ):
                    family_errors.append("telemetry lifecycle/count/timing does not match process metadata")
            else:
                family_errors.append("telemetry has no parseable lifecycle events")

        metrics: dict[str, float] = {}
        comparisons: dict[str, Any] = {}
        try:
            metrics = recompute_metrics(
                qf_displacement=np.asarray(qf["displacement.npy"], dtype=np.float64),
                qf_fixed=np.asarray(qf["fixed.npy"], dtype=np.int64),
                qf_loads=np.asarray(qf["loads.npy"], dtype=np.float64),
                qf_stiffness=np.asarray(qf["stiffness.npy"], dtype=np.float64),
                aster_displacement=np.asarray(raw["displacement"], dtype=np.float64),
                aster_reaction=np.asarray(raw["reaction"], dtype=np.float64),
                coordinates=np.asarray(spec["coordinates"], dtype=np.float64),
            )
            for name, limit in contract["gates"].items():
                if name not in metrics:
                    family_errors.append(f"checker cannot evaluate frozen gate: {name}")
                    continue
                value = metrics[name]
                comparisons[name] = {
                    "value": value,
                    "limit": float(limit),
                    "status": "PASS" if np.isfinite(value) and value <= float(limit) else "FAIL",
                }
        except (KeyError, TypeError, ValueError) as exc:
            family_errors.append(f"metric recomputation failed: {exc}")

        comparison_path = family_root / "comparison.json"
        recorded: dict[str, Any] = {}
        if comparison_path.is_file():
            try:
                recorded = load_json(comparison_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                family_errors.append(f"invalid comparison record: {exc}")
        if recorded:
            if (
                recorded.get("family") != family
                or recorded.get("execution_sha") != summary.get("execution_sha")
                or recorded.get("contract_sha256") != sha256_file(contract_path)
                or recorded.get("runner_sha") != contract.get("runner_sha")
                or recorded.get("raw") != raw
                or recorded.get("process") != process
            ):
                family_errors.append("comparison record provenance/raw/process does not match primary artifacts")
            recorded_metrics = recorded.get("metrics", {})
            if not isinstance(recorded_metrics, dict):
                family_errors.append("recorded comparison metrics must be an object")
                recorded_metrics = {}
            for name, expected_value in metrics.items():
                actual_value = recorded_metrics.get(name)
                if (
                    not isinstance(actual_value, (int, float))
                    or not np.isfinite(actual_value)
                    or not np.isclose(float(actual_value), expected_value, rtol=1.0e-14, atol=0.0)
                ):
                    family_errors.append(f"recorded comparison metric differs from independent recomputation: {name}")
            recorded_gates = recorded.get("comparisons", {})
            if not isinstance(recorded_gates, dict):
                family_errors.append("recorded comparison gates must be an object")
                recorded_gates = {}
            if set(recorded_gates) != set(comparisons):
                family_errors.append("recorded comparison gate coverage differs from the frozen gate set")
            else:
                for name, gate in comparisons.items():
                    previous = recorded_gates[name]
                    if (
                        not isinstance(previous, dict)
                        or previous.get("limit") != gate["limit"]
                        or previous.get("status") != gate["status"]
                        or not isinstance(previous.get("value"), (int, float))
                        or not np.isclose(float(previous["value"]), gate["value"], rtol=1.0e-14, atol=0.0)
                    ):
                        family_errors.append(f"recorded gate differs from independent recomputation: {name}")

        record_status = "PASS_CANDIDATE" if not family_errors and comparisons and all(
            item["status"] == "PASS" for item in comparisons.values()
        ) else "FAIL_CLOSED"
        runner_family = summary.get("families", {}).get(family, {})
        runner_status = runner_family.get("status")
        if (record_status == "PASS_CANDIDATE" and runner_status != "PASS") or (
            record_status == "FAIL_CLOSED" and runner_status == "PASS"
        ):
            family_errors.append("runner family verdict disagrees with independent raw-evidence audit")
            record_status = "FAIL_CLOSED"
        families[family] = {
            "status": record_status,
            "runner_status": runner_status,
            "model_fingerprint": result.get("model_fingerprint"),
            "metrics_recomputed_from_raw": metrics,
            "gates": comparisons,
            "errors": family_errors,
        }
        errors.extend(family_errors)

    passed_families = sum(record["status"] == "PASS_CANDIDATE" for record in families.values())
    overall_pass = not errors and passed_families == len(FAMILIES)
    return {
        "work_package": "WP12",
        "audit_status": "PASS_CANDIDATE" if overall_pass else "FAIL_CLOSED",
        "official_points": "0/4",
        "candidate_points": f"{passed_families}/4",
        "contract_sha256": sha256_file(contract_path),
        "execution_sha": summary.get("execution_sha"),
        "runner_sha": contract.get("runner_sha"),
        "manifest_sha256": sha256_file(output_root / "manifest.json") if (output_root / "manifest.json").is_file() else None,
        "families": families,
        "errors": errors,
        "limitations": contract.get("limitations", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else repo_root / args.contract
    output_root = args.output_root if args.output_root.is_absolute() else repo_root / args.output_root
    audit_output = args.audit_output if args.audit_output.is_absolute() else repo_root / args.audit_output
    try:
        report = audit(contract_path, output_root, repo_root)
        audit_output.parent.mkdir(parents=True, exist_ok=True)
        audit_output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"audit_status": report["audit_status"], "candidate_points": report["candidate_points"], "errors": report["errors"]}, indent=2))
        return 0 if report["audit_status"] == "PASS_CANDIDATE" else 2
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"WP12_AUDIT_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
