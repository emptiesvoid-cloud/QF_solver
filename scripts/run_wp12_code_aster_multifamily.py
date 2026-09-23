"""Prospective WP12 same-mesh external correlation against Code_Aster.

This runner reuses accepted WP11 M1 inputs and performs only the external
Code_Aster solves. It never invokes the QF production solver. Execution is
disabled unless the frozen contract explicitly authorizes it and --execute
is supplied.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
_multifamily = import_module("solveur.large.multifamily")
SUPPORTED_WP11_FAMILIES = _multifamily.SUPPORTED_WP11_FAMILIES
assemble_linear_system = _multifamily.assemble_linear_system
build_wp11_family_model = _multifamily.build_wp11_family_model
model_fingerprint = _multifamily.model_fingerprint


FAMILIES = tuple(SUPPORTED_WP11_FAMILIES)
EXPECTED_DOFS = {"TET4": 12, "HEX8": 24, "TET10": 30, "HEX20": 60}
EXPECTED_NODES = {"TET4": 4, "HEX8": 8, "TET10": 10, "HEX20": 20}
ASTER_TYPES = {"TET4": "TETRA4", "HEX8": "HEXA8", "TET10": "TETRA10", "HEX20": "HEXA20"}
ASTER_NODE_ORDER = {
    "TET4": tuple(range(4)),
    "HEX8": tuple(range(8)),
    # The WP11 TET10 edge ordering matches Code_Aster's TETRA10 ordering.
    "TET10": tuple(range(10)),
    # Convert the QF/Gmsh HEX20 edge order to Code_Aster's ASTER-mail order.
    "HEX20": (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17),
}
WP11_EVIDENCE_ROOT = Path("qualification/0_2_9/wp11_multifamily_extension_provenance_r1")
WP11_MANIFEST = Path("qualification/0_2_9/wp11_multifamily_provenance_owner_review.json")
WP11_CONTRACT = Path("qualification/0_2_9/wp11_multifamily_extension_contract.json")
CODE_ASTER_IMAGE = (
    "simvia/code_aster@sha256:"
    "4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
)
CODE_ASTER_PROFILE = (
    "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
    "owafurl325k3dbxls3s645zyfmvakxsg"
)
CODE_ASTER_RUNNER = f"{CODE_ASTER_PROFILE}/bin/run_aster"
SPACK_ROOT = "/opt/spack/opt/spack/linux-zen"
INPUT_NAMES = ("result.json", "displacement.npy", "fixed.npy", "loads.npy", "stiffness.npy")
RUNTIME_IMPORT_SMOKE = ["mpi4py", "numpy", "code_aster.Commands"]
RUNTIME_IMPORT_SMOKE_COMMAND = "python3 -c 'import mpi4py, numpy; import code_aster.Commands'"
R2_REVISION = "R2_PROSPECTIVE_RUNTIME_BOOTSTRAP_REMEDIATION"
R2_AUTHORIZATION_SCOPE = (
    "Four serial Code_Aster linear-static correlations only; no QF M1/M2/M3 rerun, no merge, no push, no ledger "
    "award; R2 changes runtime bootstrap and prior-attempt provenance checks only"
)


class WP12PreflightError(RuntimeError):
    """Raised when frozen WP12 inputs or provenance do not match."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a complete JSON file, replacing it atomically after serialization."""

    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _manifest_key(family: str, filename: str) -> str:
    return f"{family}\\M1\\{filename}"


def _safe_repo_path(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    if not isinstance(relative, str) or not relative:
        raise WP12PreflightError("WP12 evidence path must be a non-empty repository-relative string.")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise WP12PreflightError(f"WP12 evidence path must be repository-relative: {relative}")
    resolved = (root / candidate).resolve()
    if resolved == root or root not in resolved.parents:
        raise WP12PreflightError(f"WP12 evidence path escapes repository root: {relative}")
    return resolved


def _validate_prior_attempt(repo_root: Path, contract: dict[str, Any]) -> dict[str, Any] | None:
    prior = contract.get("prior_attempt")
    if prior is None:
        if contract.get("revision") == R2_REVISION:
            raise WP12PreflightError("WP12 R2 must bind the immutable R1 launch-failure evidence.")
        return None
    if not isinstance(prior, dict) or prior.get("attempt") != "R1":
        raise WP12PreflightError("WP12 prior-attempt binding must identify R1.")
    if prior.get("classification") != "FAIL_CLOSED_LAUNCHER_RUNTIME_IMPORT_FAILURE":
        raise WP12PreflightError("WP12 R1 failure classification has drifted.")

    record_path = _safe_repo_path(repo_root, prior.get("record_path", ""))
    contract_path = _safe_repo_path(repo_root, prior.get("contract_path", ""))
    output_root = _safe_repo_path(repo_root, prior.get("output_root", ""))
    if not record_path.is_file() or sha256_file(record_path) != prior.get("record_sha256"):
        raise WP12PreflightError("WP12 R1 launch-failure record is missing or has changed.")
    if not contract_path.is_file() or sha256_file(contract_path) != prior.get("contract_sha256"):
        raise WP12PreflightError("WP12 frozen R1 contract is missing or has changed.")
    if not output_root.is_dir():
        raise WP12PreflightError("WP12 R1 output archive is missing.")
    r2_output = _safe_repo_path(repo_root, str(contract.get("output_root", "")))
    if r2_output == output_root or output_root in r2_output.parents or r2_output in output_root.parents:
        raise WP12PreflightError("WP12 R1 and R2 output roots must be disjoint.")

    summary_path = output_root / "wp12_summary.json"
    manifest_path = output_root / "manifest.json"
    if not summary_path.is_file() or sha256_file(summary_path) != prior.get("summary_sha256"):
        raise WP12PreflightError("WP12 R1 summary is missing or has changed.")
    if not manifest_path.is_file() or sha256_file(manifest_path) != prior.get("manifest_sha256"):
        raise WP12PreflightError("WP12 R1 output manifest is missing or has changed.")

    manifest = load_json(manifest_path).get("files")
    if not isinstance(manifest, dict):
        raise WP12PreflightError("WP12 R1 manifest has no file map.")
    actual_files = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_files != set(manifest):
        raise WP12PreflightError("WP12 R1 manifest does not cover the exact archived file set.")
    for relative, entry in manifest.items():
        path = _safe_repo_path(output_root, str(relative))
        if (
            not isinstance(entry, dict)
            or not path.is_file()
            or sha256_file(path) != entry.get("sha256")
            or path.stat().st_size != entry.get("size_bytes")
        ):
            raise WP12PreflightError(f"WP12 R1 archived file failed hash/size verification: {relative}")
    if any(path.name == "aster_raw.json" for path in output_root.rglob("*")):
        raise WP12PreflightError("WP12 R1 unexpectedly contains a Code_Aster raw result; its failure record drifted.")

    r1_record = load_json(record_path)
    r1_summary = load_json(summary_path)
    r1_contract = load_json(contract_path)
    if contract.get("revision") == R2_REVISION:
        expected_r2_output = "qualification/0_2_9/wp12_external_vv_r2"
        authorization = contract.get("execution_authorization", {})
        if (
            contract.get("output_root") != expected_r2_output
            or not isinstance(authorization, dict)
            or authorization.get("scope") != R2_AUTHORIZATION_SCOPE
        ):
            raise WP12PreflightError("WP12 R2 revision/output/authorization scope is not the frozen prospective scope.")
        r1_comparable = json.loads(json.dumps(r1_contract))
        r2_comparable = json.loads(json.dumps(contract))
        for document in (r1_comparable, r2_comparable):
            for key in ("revision", "runner_sha", "auditor_sha", "output_root", "prior_attempt"):
                document.pop(key, None)
            document.get("external_solver", {}).pop("runtime_bootstrap", None)
            document.get("execution_authorization", {}).pop("scope", None)
        if r1_comparable != r2_comparable:
            raise WP12PreflightError("WP12 R2 changed a frozen R1 model, load, gate, solver, or limitation field.")
    if (
        r1_record.get("classification") != prior["classification"]
        or r1_record.get("numerical_failure") is not False
        or r1_record.get("correlation_claim") is not False
        or r1_record.get("contract_sha256") != prior["contract_sha256"]
        or r1_record.get("summary_sha256") != prior["summary_sha256"]
        or r1_record.get("raw_manifest_sha256") != prior["manifest_sha256"]
        or r1_summary.get("status") != "FAIL_CLOSED"
        or r1_summary.get("candidate_points") != "0/4"
        or r1_summary.get("official_points") != "0/4"
        or r1_summary.get("execution_sha") != r1_record.get("execution_sha")
        or r1_summary.get("contract_sha256") != prior["contract_sha256"]
        or r1_contract.get("status") != "FROZEN"
        or r1_contract.get("revision") != "R1_PROSPECTIVE_CODE_ASTER_STATIC_FAMILY_MATRIX"
        or r1_summary.get("runner_sha") != r1_contract.get("runner_sha")
        or set(r1_record.get("families", {})) != set(FAMILIES)
        or set(r1_summary.get("families", {})) != set(FAMILIES)
    ):
        raise WP12PreflightError("WP12 R1 failure record and summary are inconsistent.")
    for family in FAMILIES:
        failure = r1_record["families"][family]
        result = r1_summary["families"][family]
        process = result.get("process", {})
        if (
            failure.get("exit_code") != 1
            or failure.get("aster_raw_json_present") is not False
            or result.get("status") != "FAIL_CLOSED_EXECUTION"
            or process.get("exit_code") != 1
            or process.get("host_process_id") != failure.get("host_process_id")
        ):
            raise WP12PreflightError(f"WP12 R1 {family} failure classification/process evidence drifted.")
        if (output_root / family / "aster_raw.json").exists():
            raise WP12PreflightError(f"WP12 R1 {family} unexpectedly has a raw solve result.")
    try:
        subprocess.check_output(
            ["git", "cat-file", "-e", f"{r1_record.get('execution_sha')}^{{commit}}"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_output(
            ["git", "cat-file", "-e", f"{r1_contract.get('runner_sha')}^{{commit}}"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        if subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                str(r1_contract.get("runner_sha")),
                str(r1_record.get("execution_sha")),
            ],
            cwd=repo_root,
            check=False,
        ).returncode != 0:
            raise WP12PreflightError("WP12 R1 runner SHA is not an ancestor of its recorded execution SHA.")
    except subprocess.CalledProcessError as exc:
        raise WP12PreflightError("WP12 R1 execution/runner SHA is not a resolvable Git commit.") from exc
    return {
        "status": "PASS_IMMUTABLE_FAILURE_PRESERVED",
        "record_sha256": sha256_file(record_path),
        "contract_sha256": sha256_file(contract_path),
        "summary_sha256": sha256_file(summary_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_entries": len(manifest),
        "family_failures": list(FAMILIES),
    }


def _runtime_shell_command(runtime: dict[str, Any], command: str) -> str:
    """Build the pinned image's profiled Spack environment without invoking a solver."""

    if (
        runtime.get("shell") != "/bin/bash"
        or runtime.get("profile_script") != f"{CODE_ASTER_PROFILE}/share/aster/profile.sh"
        or runtime.get("spack_root") != SPACK_ROOT
        or runtime.get("python_site_packages_pattern") != "*/lib/python3.11/site-packages"
        or runtime.get("shared_library_directory_names") != ["lib", "lib64"]
        or runtime.get("required_import_smoke") != RUNTIME_IMPORT_SMOKE
        or runtime.get("login_shell") is not True
    ):
        raise WP12PreflightError("WP12 Code_Aster runtime bootstrap differs from the validated image setup.")
    return (
        f"export RUNASTER_ROOT={CODE_ASTER_PROFILE}; "
        f"source {runtime['profile_script']}; "
        f"export PYTHONPATH=$(find {runtime['spack_root']} -type d -path "
        f"'{runtime['python_site_packages_pattern']}' | paste -sd: -):${{PYTHONPATH:-}}; "
        f"export LD_LIBRARY_PATH=$(find {runtime['spack_root']} -type d "
        r"\( -name lib -o -name lib64 \) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        f"{command}"
    )


def _load_frozen_inputs(repo_root: Path, contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest_path = repo_root / WP11_MANIFEST
    if sha256_file(manifest_path) != contract["wp11_owner_manifest_sha256"]:
        raise WP12PreflightError("WP11 accepted-evidence manifest SHA-256 mismatch.")
    wp11_contract_path = repo_root / WP11_CONTRACT
    if sha256_file(wp11_contract_path) != contract["wp11_contract_sha256"]:
        raise WP12PreflightError("WP11 frozen contract SHA-256 mismatch.")
    manifest = load_json(manifest_path).get("manifest")
    if not isinstance(manifest, dict):
        raise WP12PreflightError("WP11 owner manifest has no file-hash map.")

    result: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        family_root = repo_root / WP11_EVIDENCE_ROOT / family / "M1"
        entries: dict[str, Any] = {}
        for name in INPUT_NAMES:
            relative = (WP11_EVIDENCE_ROOT / family / "M1" / name).as_posix()
            expected = manifest.get(_manifest_key(family, name))
            if expected != contract["families"][family]["m1_file_hashes"].get(name):
                raise WP12PreflightError(f"{family}: contract does not bind the accepted M1 hash for {name}.")
            path = repo_root / relative
            if not isinstance(expected, str) or not path.is_file():
                raise WP12PreflightError(f"{family}: missing or unmanifested WP11 M1 input {relative}.")
            actual = sha256_file(path)
            if actual != expected:
                raise WP12PreflightError(f"{family}: WP11 M1 input hash mismatch for {relative}.")
            entries[name] = {"path": relative, "sha256": actual}

        result_payload = load_json(family_root / "result.json")
        if result_payload.get("status") != "PASS" or result_payload.get("element_family") != family:
            raise WP12PreflightError(f"{family}: accepted WP11 M1 result status/family mismatch.")
        if result_payload.get("source_sha") != contract["wp11_source_sha"]:
            raise WP12PreflightError(f"{family}: WP11 source SHA differs from frozen contract.")
        if result_payload.get("actual_dofs") != EXPECTED_DOFS[family]:
            raise WP12PreflightError(f"{family}: WP11 M1 DOF count mismatch.")

        model = build_wp11_family_model(family)
        if model_fingerprint(model) != result_payload.get("model_fingerprint"):
            raise WP12PreflightError(f"{family}: reconstructed input does not match WP11 model fingerprint.")
        frozen_family = contract["families"][family]
        if (
            frozen_family.get("element_type") != family
            or frozen_family.get("aster_element_type") != ASTER_TYPES[family]
            or frozen_family.get("nodes") != EXPECTED_NODES[family]
            or frozen_family.get("elements") != 1
            or frozen_family.get("dofs") != EXPECTED_DOFS[family]
            or tuple(frozen_family.get("aster_local_node_order", ())) != ASTER_NODE_ORDER[family]
        ):
            raise WP12PreflightError(f"{family}: frozen element type/dimensions/Code_Aster node order mismatch.")
        if frozen_family.get("model_fingerprint") != result_payload.get("model_fingerprint"):
            raise WP12PreflightError(f"{family}: WP12 contract model fingerprint differs from accepted WP11 M1.")
        system = assemble_linear_system(model)
        displacement = np.load(family_root / "displacement.npy", allow_pickle=False)
        fixed = np.load(family_root / "fixed.npy", allow_pickle=False)
        loads = np.load(family_root / "loads.npy", allow_pickle=False)
        stiffness = np.load(family_root / "stiffness.npy", allow_pickle=False)
        if displacement.shape != (EXPECTED_DOFS[family],) or not np.all(np.isfinite(displacement)):
            raise WP12PreflightError(f"{family}: invalid WP11 M1 displacement vector.")
        if not np.array_equal(fixed, system.fixed) or not np.array_equal(loads, system.loads):
            raise WP12PreflightError(f"{family}: reconstructed boundary/load vectors differ from WP11 M1.")
        if stiffness.shape != system.stiffness.shape or not np.array_equal(stiffness, system.stiffness.toarray()):
            raise WP12PreflightError(f"{family}: reconstructed stiffness differs from WP11 M1.")
        coordinates = np.asarray(model.nodes, dtype=float)
        connectivity = np.asarray(model.elements[0].nodes, dtype=np.int64)
        if not np.array_equal(coordinates, np.asarray(frozen_family["coordinates"], dtype=float)):
            raise WP12PreflightError(f"{family}: coordinates differ from frozen WP12 contract.")
        if not np.array_equal(connectivity, np.asarray(frozen_family["connectivity"], dtype=np.int64)):
            raise WP12PreflightError(f"{family}: connectivity differs from frozen WP12 contract.")
        if not np.array_equal(system.fixed, np.asarray(frozen_family["fixed_dofs"], dtype=np.int64)):
            raise WP12PreflightError(f"{family}: fixed DOFs differ from frozen WP12 contract.")
        expected_loads: np.ndarray = np.zeros(EXPECTED_DOFS[family], dtype=float)
        component_indices = {"UX": 0, "UY": 1, "UZ": 2}
        for nodal_load in frozen_family["nodal_loads"]:
            expected_loads[3 * int(nodal_load["node"]) + component_indices[nodal_load["dof"]]] = float(
                nodal_load["value"]
            )
        if not np.array_equal(loads, expected_loads):
            raise WP12PreflightError(f"{family}: load vector differs from frozen WP12 contract.")
        if model.materials["solid"].get("E") != contract["material"]["E"] or model.materials["solid"].get(
            "nu"
        ) != contract["material"]["nu"]:
            raise WP12PreflightError(f"{family}: material differs from frozen WP12 contract.")
        loaded_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 1.0, rtol=0.0, atol=1.0e-14))
        fixed_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-14))
        if not loaded_nodes.size or not fixed_nodes.size:
            raise WP12PreflightError(f"{family}: frozen geometry has no load/fixed node set.")
        if not np.array_equal(loaded_nodes, np.asarray(frozen_family["loaded_nodes"], dtype=np.int64)):
            raise WP12PreflightError(f"{family}: load node set differs from frozen WP12 contract.")
        if system.fixed.size != int(frozen_family["fixed_dof_count"]):
            raise WP12PreflightError(f"{family}: fixed DOF count differs from frozen WP12 contract.")
        result[family] = {
            "model": model,
            "system": system,
            "coordinates": coordinates,
            "connectivity": connectivity,
            "displacement": displacement,
            "fixed": fixed,
            "loads": loads,
            "stiffness": stiffness,
            "fixed_nodes": fixed_nodes,
            "loaded_nodes": loaded_nodes,
            "files": entries,
            "model_fingerprint": result_payload["model_fingerprint"],
        }
    return result


def preflight(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    contract = load_json(contract_path)
    prior_attempt_audit = _validate_prior_attempt(repo_root, contract)
    if contract.get("status") != "FROZEN" or contract.get("execution_authorized") is not True:
        raise WP12PreflightError("WP12 contract is not frozen and execution-authorized.")
    if tuple(contract.get("families", {}).keys()) != FAMILIES:
        raise WP12PreflightError("WP12 contract family coverage/order mismatch.")
    if contract.get("code_aster_image") != CODE_ASTER_IMAGE:
        raise WP12PreflightError("WP12 Code_Aster image digest differs from the runner pin.")
    external = contract.get("external_solver", {})
    if not isinstance(external, dict):
        raise WP12PreflightError("WP12 external_solver configuration must be an object.")
    if (
        external.get("name") != "Code_Aster"
        or external.get("version") != contract.get("code_aster_version")
        or external.get("image") != contract.get("code_aster_image")
        or external.get("image_id") != contract.get("code_aster_image_id")
        or external.get("entrypoint") != CODE_ASTER_RUNNER
        or external.get("timeout_seconds") != contract.get("timeout_seconds")
        or external.get("memory_limit_mb") != contract.get("memory_limit_mb")
        or external.get("action") != contract.get("code_aster_action")
        or external.get("mpi") is not False
        or external.get("cpu_limit") != 1
        or external.get("fresh_container_per_family") is not True
        or contract.get("code_aster_action") != "make_etude"
    ):
        raise WP12PreflightError("WP12 Code_Aster runtime/action/resource configuration is inconsistent.")
    runtime_bootstrap = external.get("runtime_bootstrap")
    if not isinstance(runtime_bootstrap, dict):
        raise WP12PreflightError("WP12 Code_Aster runtime bootstrap is missing.")
    runtime_probe_shell = _runtime_shell_command(
        runtime_bootstrap,
        f"{RUNTIME_IMPORT_SMOKE_COMMAND} && {CODE_ASTER_RUNNER} --version",
    )
    qf_reference = contract.get("qf_reference", {})
    if not isinstance(qf_reference, dict):
        raise WP12PreflightError("WP12 qf_reference provenance must be an object.")
    if (
        qf_reference.get("source_sha") != contract.get("wp11_source_sha")
        or qf_reference.get("owner_acceptance_path") != contract.get("wp11_owner_acceptance_path")
        or qf_reference.get("owner_acceptance_sha256") != contract.get("wp11_owner_acceptance_sha256")
        or qf_reference.get("owner_manifest_path") != contract.get("wp11_owner_manifest_path")
        or qf_reference.get("owner_manifest_sha256") != contract.get("wp11_owner_manifest_sha256")
        or qf_reference.get("contract_path") != contract.get("wp11_contract_path")
        or qf_reference.get("contract_sha256") != contract.get("wp11_contract_sha256")
    ):
        raise WP12PreflightError("WP11 input provenance fields disagree within the frozen WP12 contract.")
    if _git(repo_root, "branch", "--show-current") != contract.get("branch"):
        raise WP12PreflightError("Current branch differs from frozen WP12 branch.")
    if _git(repo_root, "status", "--porcelain"):
        raise WP12PreflightError("Working tree must be clean before WP12 execution.")
    branch_base = contract.get("branch_base_sha")
    if _git(repo_root, "rev-parse", "--verify", f"{branch_base}^{{commit}}") != branch_base:
        raise WP12PreflightError("Frozen WP12 branch base is not resolvable.")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", branch_base, "HEAD"], cwd=repo_root, check=False
    ).returncode != 0:
        raise WP12PreflightError("WP12 branch is not descended from its frozen base.")
    if subprocess.run(
        ["git", "diff", "--quiet", branch_base, "HEAD", "--", "src/"], cwd=repo_root, check=False
    ).returncode != 0:
        raise WP12PreflightError("WP12 preparation changed production source after the frozen branch base.")
    runner_commit = _git(repo_root, "log", "-1", "--format=%H", "--", "scripts/run_wp12_code_aster_multifamily.py")
    if runner_commit != contract.get("runner_sha"):
        raise WP12PreflightError("Runner SHA differs from frozen WP12 contract.")
    auditor_commit = _git(repo_root, "log", "-1", "--format=%H", "--", "scripts/audit_wp12_code_aster_multifamily.py")
    if auditor_commit != contract.get("auditor_sha"):
        raise WP12PreflightError("Independent auditor SHA differs from frozen WP12 contract.")
    if _git(repo_root, "rev-parse", "--verify", f"{contract['wp11_source_sha']}^{{commit}}") != contract[
        "wp11_source_sha"
    ]:
        raise WP12PreflightError("WP11 source commit is not resolvable in this repository.")
    owner_acceptance_path = repo_root / contract["wp11_owner_acceptance_path"]
    if not owner_acceptance_path.is_file() or sha256_file(owner_acceptance_path) != contract[
        "wp11_owner_acceptance_sha256"
    ]:
        raise WP12PreflightError("WP11 Owner acceptance record is missing or has changed.")
    owner_acceptance = load_json(owner_acceptance_path)
    if (
        owner_acceptance.get("status") != "CLOSED_OWNER_ACCEPTED_WITH_LIMITATIONS"
        or owner_acceptance.get("owner_accepts_wp11_scope") is not True
        or owner_acceptance.get("approved_points") != 6
    ):
        raise WP12PreflightError("WP11 Owner acceptance does not authorize the frozen M1 baseline scope.")
    if subprocess.run(
        ["git", "diff", "--quiet", contract["wp11_source_sha"], "HEAD", "--", "src/solveur/large/multifamily.py"],
        cwd=repo_root,
        check=False,
    ).returncode != 0:
        raise WP12PreflightError("WP11 model source differs from the accepted WP11 execution source.")

    frozen = _load_frozen_inputs(repo_root, contract)
    docker = shutil.which("docker")
    if docker is None:
        raise WP12PreflightError("Docker CLI is unavailable; no external solve may start.")
    image = subprocess.run(
        [docker, "image", "inspect", CODE_ASTER_IMAGE, "--format", "{{.Id}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    expected_image_id = contract.get("code_aster_image_id")
    if image.returncode != 0 or image.stdout.strip() != expected_image_id:
        raise WP12PreflightError("Local Code_Aster image is absent or has an unexpected immutable image ID.")
    version = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", runtime_bootstrap["shell"], CODE_ASTER_IMAGE, "-lc", runtime_probe_shell],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if version.returncode != 0 or not version.stdout.strip().startswith(f"code_aster {contract['code_aster_version']} "):
        raise WP12PreflightError("Pinned Code_Aster runtime version does not match the frozen contract.")
    output_root = repo_root / contract["output_root"]
    if output_root.exists():
        raise WP12PreflightError(f"WP12 output path already exists; refusing overwrite: {output_root}.")
    return {
        "status": "PREFLIGHT_PASS",
        "branch": contract["branch"],
        "branch_base_sha": branch_base,
        "head": _git(repo_root, "rev-parse", "HEAD"),
        "runner_sha": runner_commit,
        "contract_sha256": sha256_file(contract_path),
        "wp11_m1_families": {family: frozen[family]["model_fingerprint"] for family in FAMILIES},
        "code_aster_image": CODE_ASTER_IMAGE,
        "code_aster_image_id": image.stdout.strip(),
        "code_aster_runtime_version": version.stdout.strip(),
        "output_path_absent": True,
        "prior_attempt_audit": prior_attempt_audit,
    }


def aster_mesh_text(family: str, coordinates: np.ndarray, connectivity: np.ndarray) -> str:
    family = str(family).upper()
    if family not in ASTER_TYPES:
        raise ValueError(f"Unsupported WP12 element family {family!r}.")
    if len(connectivity) != len(ASTER_NODE_ORDER[family]):
        raise ValueError(f"{family}: connectivity node count mismatch.")
    lines = ["TITRE", f"WP12 external correlation {family}", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(np.asarray(coordinates, dtype=float))
    )
    lines.extend(["FINSF", ASTER_TYPES[family]])
    ordered = [int(connectivity[index]) for index in ASTER_NODE_ORDER[family]]
    lines.append("M1 " + " ".join(f"N{node + 1}" for node in ordered))
    lines.extend(["FINSF", "GROUP_MA", "SOLID", "M1", "FINSF"])
    for name, predicate in (
        ("ROOT", lambda point: abs(float(point[0])) <= 1.0e-14),
        ("LOAD", lambda point: abs(float(point[0]) - 1.0) <= 1.0e-14),
    ):
        node_names = [f"N{index + 1}" for index, point in enumerate(coordinates) if predicate(point)]
        if not node_names:
            raise ValueError(f"{family}: {name} node group is empty.")
        lines.extend(["GROUP_NO", name, *node_names, "FINSF"])
    lines.extend(["GROUP_NO", "NALL", *(f"N{i + 1}" for i in range(len(coordinates))), "FINSF"])
    for index in range(len(coordinates)):
        lines.extend(["GROUP_NO", f"QF{index:03d}", f"N{index + 1}", "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def aster_comm_text(family: str, node_count: int, material: dict[str, float], loads: np.ndarray) -> str:
    force_terms = []
    for node, force in enumerate(np.asarray(loads, dtype=float).reshape(node_count, 3)):
        components = [(name, float(value)) for name, value in zip(("FX", "FY", "FZ"), force, strict=True) if value != 0.0]
        for name, value in components:
            force_terms.append(f'_F(NOEUD="N{node + 1}", {name}={value:.17g})')
    if not force_terms:
        raise ValueError(f"{family}: frozen WP11 load vector is empty.")
    force_text = ",\n    ".join(force_terms)
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


def aster_export_text(family: str, timeout_seconds: int, memory_limit_mb: int) -> str:
    """Create a run_aster export descriptor for the fixed mesh/command units."""

    return "\n".join(
        (
            "P actions make_etude",
            f"P time_limit {int(timeout_seconds)}",
            f"P memory_limit {int(memory_limit_mb)}",
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


def _write_manifest(output_root: Path) -> None:
    manifest = {}
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest[path.relative_to(output_root).as_posix()] = {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
    write_json(output_root / "manifest.json", {"files": manifest})


def relative_l2(actual: np.ndarray, expected: np.ndarray) -> float:
    magnitude = float(np.linalg.norm(expected))
    denominator = magnitude if magnitude > 0.0 else float(np.finfo(np.float64).tiny)
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(expected))) / denominator


def relative_linf(actual: np.ndarray, expected: np.ndarray) -> float:
    magnitude = float(np.max(np.abs(expected), initial=0.0))
    denominator = magnitude if magnitude > 0.0 else float(np.finfo(np.float64).tiny)
    return float(np.max(np.abs(np.asarray(actual) - np.asarray(expected)), initial=0.0) / denominator)


def _run_aster(
    work: Path, family: str, timeout_s: int, image_id: str, runtime_bootstrap: dict[str, Any]
) -> dict[str, Any]:
    docker = shutil.which("docker")
    if docker is None:
        raise WP12PreflightError("Docker CLI disappeared after preflight.")
    runtime_shell = _runtime_shell_command(runtime_bootstrap, f"{CODE_ASTER_RUNNER} {family}.export --no-mpi")
    command = [
        docker,
        "run",
        "--rm",
        "--cpus=1",
        "--cidfile",
        f"{work.resolve() / 'container.cid'}",
        "-v",
        f"{work.resolve()}:/work",
        "--workdir",
        "/work",
        "--entrypoint",
        runtime_bootstrap["shell"],
        CODE_ASTER_IMAGE,
        "-lc",
        runtime_shell,
    ]
    start = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()
    telemetry_path = work / "telemetry.jsonl"
    progress_path = work / "progress.json"
    event_count = 0

    def emit(event: str, **values: Any) -> None:
        nonlocal event_count
        event_count += 1
        row = {
            "event": event,
            "family": family,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.perf_counter() - start,
            **values,
        }
        with telemetry_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        write_json(progress_path, row)
        _write_manifest(work.parent)

    emit("RUN_START", status="STARTING", command=command)
    with (work / "stdout.log").open("w", encoding="utf-8", newline="\n") as stdout, (work / "stderr.log").open(
        "w", encoding="utf-8", newline="\n"
    ) as stderr:
        process = subprocess.Popen(command, cwd=work, stdout=stdout, stderr=stderr, text=True)
        emit("CONTAINER_PROCESS_START", status="RUNNING", host_process_id=process.pid)
        while process.poll() is None:
            time.sleep(5.0)
            if process.poll() is None:
                emit("HEARTBEAT", status="RUNNING", host_process_id=process.pid)
        exit_code = process.returncode
    elapsed = time.perf_counter() - start
    container_id_path = work / "container.cid"
    container_id = container_id_path.read_text(encoding="ascii").strip() if container_id_path.is_file() else None
    runtime_probe_shell = _runtime_shell_command(
        runtime_bootstrap,
        f"{RUNTIME_IMPORT_SMOKE_COMMAND} && {CODE_ASTER_RUNNER} --version",
    )
    runtime_probe = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", runtime_bootstrap["shell"], CODE_ASTER_IMAGE, "-lc", runtime_probe_shell],
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
    )
    metadata = {
        "family": family,
        "image": CODE_ASTER_IMAGE,
        "image_id": image_id,
        "runtime_version": runtime_probe.stdout.strip() if runtime_probe.returncode == 0 else None,
        "command": command,
        "runtime_shell_command": runtime_shell,
        "runtime_probe_shell_command": runtime_probe_shell,
        "solver_entrypoint": CODE_ASTER_RUNNER,
        "python_runtime_import_smoke": "PASS" if runtime_probe.returncode == 0 else "FAIL",
        "host_process_id": process.pid,
        "container_id": container_id,
        "exit_code": exit_code,
        "elapsed_seconds": elapsed,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "fresh_container_process": True,
        "container_cpu_limit": 1,
        "solver_mpi_disabled": True,
        "telemetry_events": event_count + 1,
    }
    write_json(work / "process.json", metadata)
    emit("RUN_END", status="COMPLETED" if exit_code == 0 else "FAILED", exit_code=exit_code)
    if runtime_probe.returncode != 0:
        raise RuntimeError(f"Could not verify post-run Code_Aster version for {family}.")
    if exit_code != 0:
        tail = "\n".join((work / "stdout.log").read_text(encoding="utf-8").splitlines()[-40:])
        tail += "\n" + "\n".join((work / "stderr.log").read_text(encoding="utf-8").splitlines()[-40:])
        raise RuntimeError(f"Code_Aster {family} failed with exit {exit_code}:\n{tail}")
    return metadata


def execute(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    contract = load_json(contract_path)
    readiness = preflight(contract_path, repo_root)
    output_root = repo_root / contract["output_root"]
    output_root.mkdir(parents=True, exist_ok=False)
    run_sha = _git(repo_root, "rev-parse", "HEAD")
    evidence = _load_frozen_inputs(repo_root, contract)
    family_results: dict[str, Any] = {}

    for family in FAMILIES:
        source = evidence[family]
        work = output_root / family
        work.mkdir()
        qf_snapshot = work / "qf_m1"
        qf_snapshot.mkdir()
        for name in INPUT_NAMES:
            shutil.copyfile(repo_root / source["files"][name]["path"], qf_snapshot / name)
        (work / f"{family}.mail").write_text(
            aster_mesh_text(family, source["coordinates"], source["connectivity"]), encoding="ascii"
        )
        material = dict(source["model"].materials["solid"])
        (work / f"{family}.comm").write_text(
            aster_comm_text(family, len(source["coordinates"]), material, source["loads"]), encoding="utf-8"
        )
        (work / f"{family}.export").write_text(
            aster_export_text(family, int(contract["timeout_seconds"]), int(contract["memory_limit_mb"])),
            encoding="ascii",
            newline="\n",
        )
        _write_manifest(output_root)
        record: dict[str, Any] = {
            "family": family,
            "status": "RUNNING",
            "execution_sha": run_sha,
            "contract_sha256": readiness["contract_sha256"],
            "wp11_source_sha": contract["wp11_source_sha"],
            "runner_sha": contract["runner_sha"],
            "model_fingerprint": source["model_fingerprint"],
            "input_hashes": source["files"],
        }
        try:
            process = _run_aster(
                work,
                family,
                int(contract["timeout_seconds"]),
                str(readiness["code_aster_image_id"]),
                contract["external_solver"]["runtime_bootstrap"],
            )
            raw = load_json(work / "aster_raw.json")
            if raw.get("status") != "PASS" or raw.get("family") != family:
                raise RuntimeError("Code_Aster raw result status/family mismatch.")
            aster_u = np.asarray(raw.get("displacement"), dtype=float)
            aster_r = np.asarray(raw.get("reaction"), dtype=float)
            qf_u = np.asarray(source["displacement"], dtype=float).reshape(-1, 3)
            qf_r = (source["stiffness"] @ source["displacement"] - source["loads"]).reshape(-1, 3)
            qf_f = np.asarray(source["loads"], dtype=float).reshape(-1, 3)
            xyz = source["coordinates"]
            if aster_u.shape != qf_u.shape or aster_r.shape != qf_r.shape:
                raise RuntimeError("Code_Aster output vector shape mismatch.")
            if not np.all(np.isfinite(aster_u)) or not np.all(np.isfinite(aster_r)):
                raise RuntimeError("Code_Aster produced a non-finite displacement or reaction.")
            qf_energy = float(0.5 * source["displacement"] @ (source["stiffness"] @ source["displacement"]))
            aster_external_work = float(0.5 * np.sum(qf_f * aster_u))
            qf_force_balance = np.sum(qf_r + qf_f, axis=0)
            aster_force_balance = np.sum(aster_r + qf_f, axis=0)
            qf_moment_balance = np.sum(np.cross(xyz, qf_r + qf_f), axis=0)
            aster_moment_balance = np.sum(np.cross(xyz, aster_r + qf_f), axis=0)
            load_scale = max(float(np.sum(np.linalg.norm(qf_f, axis=1))), 1.0)
            length_scale = max(float(np.max(np.ptp(xyz, axis=0))), 1.0)
            gates = contract["gates"]
            metrics = {
                "displacement_relative_l2": relative_l2(aster_u, qf_u),
                "displacement_relative_linf": relative_linf(aster_u, qf_u),
                "reaction_relative_l2": relative_l2(aster_r, qf_r),
                "reaction_relative_linf": relative_linf(aster_r, qf_r),
                "strain_energy_from_external_work_relative": abs(aster_external_work - qf_energy)
                / (abs(qf_energy) if abs(qf_energy) > 0.0 else float(np.finfo(np.float64).tiny)),
                "qf_force_equilibrium_relative": float(np.linalg.norm(qf_force_balance) / load_scale),
                "aster_force_equilibrium_relative": float(np.linalg.norm(aster_force_balance) / load_scale),
                "qf_moment_equilibrium_relative": float(np.linalg.norm(qf_moment_balance) / (load_scale * length_scale)),
                "aster_moment_equilibrium_relative": float(np.linalg.norm(aster_moment_balance) / (load_scale * length_scale)),
                "fixed_displacement_abs_max": float(np.max(np.abs(aster_u[np.unique(source["fixed"] // 3)]), initial=0.0)),
                "qf_strain_energy": qf_energy,
                "aster_external_work_energy": aster_external_work,
            }
            comparisons = {
                name: {"value": value, "limit": float(gates[name]), "status": "PASS" if value <= float(gates[name]) else "FAIL"}
                for name, value in metrics.items()
                if name in gates
            }
            missing = set(gates) - set(comparisons)
            if missing:
                raise RuntimeError(f"Runner does not evaluate frozen gates: {sorted(missing)}")
            family_status = "PASS" if all(item["status"] == "PASS" for item in comparisons.values()) else "FAIL_CLOSED"
            record.update(
                {
                    "status": family_status,
                    "process": process,
                    "external_solver": {
                        "name": "Code_Aster",
                        "version": contract["code_aster_version"],
                        "image": CODE_ASTER_IMAGE,
                        "image_id": readiness["code_aster_image_id"],
                    },
                    "raw": raw,
                    "metrics": metrics,
                    "comparisons": comparisons,
                }
            )
            (work / "comparison.json").write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        except Exception as exc:  # Preserve each family failure and continue independent cases.
            record.update({"status": "FAIL_CLOSED_EXECUTION", "error": f"{type(exc).__name__}: {exc}"})
            process_path = work / "process.json"
            if process_path.is_file():
                record["process"] = load_json(process_path)
            (work / "comparison.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        family_results[family] = record
        _write_manifest(output_root)

    passed_count = sum(family_results[family]["status"] == "PASS" for family in FAMILIES)
    passed = passed_count == len(FAMILIES)
    summary = {
        "work_package": "WP12",
        "campaign": "WP11 accepted linear-static one-element family correlation against Code_Aster",
        "status": "PASS_CANDIDATE" if passed else "FAIL_CLOSED",
        "candidate_points": f"{passed_count}/4",
        "official_points": "0/4",
        "branch": readiness["branch"],
        "branch_base_sha": readiness["branch_base_sha"],
        "execution_sha": run_sha,
        "contract_sha256": readiness["contract_sha256"],
        "runner_sha": contract["runner_sha"],
        "wp11_source_sha": contract["wp11_source_sha"],
        "code_aster_image": CODE_ASTER_IMAGE,
        "code_aster_image_id": readiness["code_aster_image_id"],
        "code_aster_runtime_version": readiness["code_aster_runtime_version"],
        "families": family_results,
        "limitations": contract["limitations"],
    }
    (output_root / "wp12_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (output_root / "wp12_summary.md").write_text(render_summary(summary), encoding="utf-8")
    _write_manifest(output_root)
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    rows = ["# WP12 — Code_Aster multi-family external correlation", "", f"Status: **{summary['status']}**", "", "| Famille | Statut | Δu L2 | Δu L∞ | Δréaction L2 | énergie externe |", "|---|---|---:|---:|---:|---:|"]
    for family in FAMILIES:
        item = summary["families"][family]
        metrics = item.get("metrics", {})
        rows.append(
            f"| {family} | {item['status']} | {metrics.get('displacement_relative_l2', 'n/a')} | "
            f"{metrics.get('displacement_relative_linf', 'n/a')} | {metrics.get('reaction_relative_l2', 'n/a')} | "
            f"{metrics.get('strain_energy_from_external_work_relative', 'n/a')} |"
        )
    rows.extend(["", "Official points remain `0/4` pending explicit Owner review.", "", "## Limitations", ""])
    rows.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--execute", action="store_true", help="Run the four serial Code_Aster external solves.")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else repo_root / args.contract
    try:
        if args.execute:
            result = execute(contract_path, repo_root)
        else:
            result = preflight(contract_path, repo_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        WP12PreflightError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"WP12_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
