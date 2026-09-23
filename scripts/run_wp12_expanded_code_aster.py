"""Run the frozen WP12 R3 expanded same-mesh Code_Aster correlation matrix.

The campaign consists of one-at-a-time, single-CPU QF Solver and Code_Aster
linear-static solves. It does not alter production mechanics or R2 evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import save_npz

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from scripts.wp12_expanded_models import (  # noqa: E402
    ASTER_TYPES,
    FAMILIES,
    MATERIAL,
    ExpandedCase,
    case_catalog,
    model_fingerprint,
)
from solveur.large.multifamily import solve_linear_system  # noqa: E402


IMAGE = "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
ASTER_PROFILE = "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-owafurl325k3dbxls3s645zyfmvakxsg"
ASTER_RUNNER = f"{ASTER_PROFILE}/bin/run_aster"
SPACK_ROOT = "/opt/spack/opt/spack/linux-zen"
RUNTIME_PROBE = (
    f"export RUNASTER_ROOT={ASTER_PROFILE}; "
    f"source {ASTER_PROFILE}/share/aster/profile.sh; "
    f"export PYTHONPATH=$(find {SPACK_ROOT} -type d -path '*/lib/python3.11/site-packages' | paste -sd: -):${{PYTHONPATH:-}}; "
    f"export LD_LIBRARY_PATH=$(find {SPACK_ROOT} -type d \\( -name lib -o -name lib64 \\) | paste -sd: -):${{LD_LIBRARY_PATH:-}}; "
    f"python3 -c 'import mpi4py, numpy; import code_aster.Commands' && {ASTER_RUNNER} --version"
)
COMPONENTS = (("FX", "DX"), ("FY", "DY"), ("FZ", "DZ"))


class CampaignError(RuntimeError):
    """Raised when a frozen R3 precondition is not satisfied."""


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


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _runtime_command(command: str) -> str:
    return RUNTIME_PROBE.rsplit(" && ", 1)[0] + " && " + command


def validate_external_configuration(contract: dict[str, Any]) -> tuple[int, int]:
    """Validate duplicated frozen resource fields before constructing cases."""

    external = contract.get("external_solver")
    if not isinstance(external, dict):
        raise CampaignError("Frozen external_solver block is missing")
    timeout = contract.get("timeout_seconds")
    memory = contract.get("memory_limit_mb")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or timeout <= 0
        or isinstance(memory, bool)
        or not isinstance(memory, int)
        or memory <= 0
        or external.get("timeout_seconds") != timeout
        or external.get("memory_limit_mb") != memory
    ):
        raise CampaignError("Root and external_solver timeout/memory fields are missing or inconsistent")
    if (
        external.get("name") != "Code_Aster"
        or external.get("version") != contract.get("code_aster_version")
        or external.get("image") != IMAGE
        or external.get("image_id") != contract.get("code_aster_image_id")
        or external.get("modelisation") != "3D"
        or external.get("fresh_container_per_case") is not True
        or external.get("cpu_limit") != 1
        or external.get("mpi") is not False
        or external.get("action") != "make_etude"
    ):
        raise CampaignError("Frozen Code_Aster image/action/resource configuration is inconsistent")
    if contract.get("code_aster_image") != IMAGE:
        raise CampaignError("Code_Aster image digest differs from the runner pin")
    return timeout, memory


def _aster_node_order(family: str) -> tuple[int, ...]:
    if family == "HEX20":
        return (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17)
    return tuple(range({"TET4": 4, "HEX8": 8, "TET10": 10}[family]))


def _aster_node_name(index: int) -> str:
    """Encode a compact alphabetic identifier valid in the native Aster mesh format."""
    value = index + 1
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def _aster_element_name(index: int) -> str:
    return _aster_node_name(index)


def _mesh_text(case: ExpandedCase) -> str:
    coordinates = np.asarray(case.model.nodes, dtype=np.float64)
    lines = ["TITRE", f"WP12 R3 {case.case_id}", "FINSF", "COOR_3D"]
    lines.extend(f"{_aster_node_name(i)} {x:.17g} {y:.17g} {z:.17g}" for i, (x, y, z) in enumerate(coordinates))
    lines.extend(["FINSF", ASTER_TYPES[case.family]])
    order = _aster_node_order(case.family)
    for element_index, element in enumerate(case.connectivity):
        ordered = [int(element[index]) for index in order]
        lines.append(f"{_aster_element_name(element_index)} " + " ".join(_aster_node_name(node) for node in ordered))
    lines.extend(["FINSF", "GROUP_MA", "SOLID"])
    lines.extend(_aster_element_name(index) for index in range(len(case.connectivity)))
    lines.append("FINSF")
    root_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-12))
    if root_nodes.size == 0:
        raise CampaignError(f"{case.case_id}: root group is empty")
    lines.extend(["GROUP_NO", "ROOT", *(_aster_node_name(int(node)) for node in root_nodes), "FINSF"])
    for index in range(len(coordinates)):
        lines.extend(["GROUP_NO", f"QF{index:05d}", _aster_node_name(index), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _comm_text(case: ExpandedCase) -> str:
    nodal = case.system.loads.reshape(-1, 3)
    terms: list[str] = []
    for node, values in enumerate(nodal):
        for axis, (force_name, _) in enumerate(COMPONENTS):
            value = float(values[axis])
            if value != 0.0:
                terms.append(f'_F(NOEUD="{_aster_node_name(node)}", {force_name}={value:.17g})')
    if not terms:
        raise CampaignError(f"{case.case_id}: generated load vector is empty")
    force_text = ",\n    ".join(terms)
    node_count = len(case.model.nodes)
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={float(MATERIAL['E']):.17g}, NU={float(MATERIAL['nu']):.17g}))
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
    group = "QF%05d" % node
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
        "status": "PASS", "case_id": "{case.case_id}", "family": "{case.family}",
        "element_type": "{ASTER_TYPES[case.family]}", "modelisation": "3D",
        "displacement": displacement.tolist(), "reaction": reaction.tolist()
    }}, stream, indent=2, allow_nan=False)
FIN()
'''


def _export_text(case: ExpandedCase, timeout_seconds: int, memory_limit_mb: int) -> str:
    return "\n".join(
        (
            "P actions make_etude",
            f"P time_limit {timeout_seconds}",
            f"P memory_limit {memory_limit_mb}",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P mpi_nbnoeud 1",
            f"F comm /work/{case.case_id}.comm D 1",
            f"F mail /work/{case.case_id}.mail D 20",
            f"F mess /work/{case.case_id}.mess R 6",
            f"F resu /work/{case.case_id}.resu R 8",
            "",
        )
    )


def _manifest(output_root: Path, manifest_path: Path) -> None:
    files = {}
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[path.relative_to(output_root).as_posix()] = {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
    write_json(manifest_path, {"files": files})


def preflight(contract_path: Path, repo_root: Path) -> tuple[dict[str, Any], list[ExpandedCase]]:
    contract_path, repo_root = contract_path.resolve(), repo_root.resolve()
    contract = load_json(contract_path)
    validate_external_configuration(contract)
    expected_branch = contract.get("branch")
    if contract.get("status") != "FROZEN" or contract.get("execution_authorized") is not True:
        raise CampaignError("R3 contract is not frozen and execution-authorized")
    if contract.get("abort_on_execution_failure") is not True:
        raise CampaignError("Frozen R3 contract must require fail-fast behavior for execution errors")
    if _git(repo_root, "branch", "--show-current") != expected_branch:
        raise CampaignError("Current branch differs from the frozen R3 branch")
    if _git(repo_root, "status", "--porcelain"):
        raise CampaignError("Working tree must be clean before R3 execution")
    base = str(contract.get("branch_base_sha", ""))
    if _git(repo_root, "rev-parse", "--verify", f"{base}^{{commit}}") != base:
        raise CampaignError("Frozen R3 base SHA is not resolvable")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=repo_root, check=False).returncode:
        raise CampaignError("R3 branch does not descend from frozen base")
    if _git(repo_root, "rev-parse", "HEAD^") != contract.get("freeze_commit_sha"):
        raise CampaignError("Frozen contract does not immediately follow its recorded preparation commit")
    if subprocess.run(["git", "diff", "--quiet", base, "HEAD", "--", "src/"], cwd=repo_root, check=False).returncode:
        raise CampaignError("R3 preparation changed production source")
    required_paths = {
        "runner_sha": "scripts/run_wp12_expanded_code_aster.py",
        "model_builder_sha": "scripts/wp12_expanded_models.py",
        "auditor_sha": "scripts/audit_wp12_expanded_code_aster.py",
        "contract_builder_sha": "scripts/freeze_wp12_expanded_contract.py",
    }
    for field, relative in required_paths.items():
        latest = _git(repo_root, "log", "-1", "--format=%H", "--", relative)
        if latest != contract.get(field):
            raise CampaignError(f"Frozen {field} does not match the tracked source commit")
    catalog = case_catalog()
    expected = contract.get("cases")
    if not isinstance(expected, list) or len(expected) != len(catalog):
        raise CampaignError("Frozen R3 case matrix has missing or extra cases")
    for case, frozen in zip(catalog, expected, strict=True):
        if (
            frozen.get("case_id") != case.case_id
            or frozen.get("family") != case.family
            or frozen.get("geometry") != case.geometry
            or frozen.get("dimensions_m") != list(case.dimensions)
            or frozen.get("mesh") != case.mesh
            or frozen.get("divisions") != list(case.divisions)
            or frozen.get("load_case") != case.load_case
            or frozen.get("resultant_N") != list(case.resultant)
            or frozen.get("model_fingerprint") != case.fingerprint
            or frozen.get("nodes") != len(case.model.nodes)
            or frozen.get("elements") != len(case.connectivity)
            or frozen.get("dofs") != case.system.stiffness.shape[0]
        ):
            raise CampaignError(f"Generated input differs from frozen R3 case: {case.case_id}")
    if contract.get("case_count") != len(catalog) or set(contract.get("families", [])) != set(FAMILIES):
        raise CampaignError("Frozen case count/family coverage differs from generated matrix")
    output_root = (repo_root / contract["output_root"]).resolve()
    manifest_path = (repo_root / contract["manifest_path"]).resolve()
    if repo_root not in manifest_path.parents:
        raise CampaignError("Frozen manifest path must stay inside the repository")
    if output_root.exists():
        raise CampaignError(f"R3 output root already exists; refusing overwrite: {output_root}")
    if manifest_path.exists():
        raise CampaignError(f"R3 manifest path already exists; refusing overwrite: {manifest_path}")
    docker = shutil.which("docker")
    if docker is None:
        raise CampaignError("Docker CLI unavailable")
    image = subprocess.run([docker, "image", "inspect", IMAGE, "--format", "{{.Id}}"], capture_output=True, text=True)
    if image.returncode != 0 or image.stdout.strip() != contract.get("code_aster_image_id"):
        raise CampaignError("Pinned Code_Aster image ID is unavailable or mismatched")
    probe = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", "/bin/bash", IMAGE, "-lc", _runtime_command(f"{ASTER_RUNNER} --version")],
        capture_output=True,
        text=True,
    )
    version = probe.stdout.strip()
    if probe.returncode != 0 or not version.startswith(f"code_aster {contract['code_aster_version']} "):
        raise CampaignError("Pinned Code_Aster runtime/import preflight failed")
    return (
        {
            "status": "PREFLIGHT_PASS",
            "branch": expected_branch,
            "execution_sha": _git(repo_root, "rev-parse", "HEAD"),
            "contract_sha256": sha256_file(contract_path),
            "code_aster_image_id": image.stdout.strip(),
            "code_aster_runtime_version": version,
            "case_count": len(catalog),
            "output_path_absent": True,
        },
        catalog,
    )


def _metric_comparison(case: ExpandedCase, qf_displacement: np.ndarray, aster: dict[str, Any]) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    qf_u = np.asarray(qf_displacement, dtype=np.float64).reshape(-1, 3)
    aster_u = np.asarray(aster["displacement"], dtype=np.float64)
    aster_r = np.asarray(aster["reaction"], dtype=np.float64)
    qf_f = np.asarray(case.system.loads, dtype=np.float64).reshape(-1, 3)
    qf_r = np.asarray(case.system.stiffness @ qf_displacement - case.system.loads, dtype=np.float64).reshape(-1, 3)
    free_mask = np.ones(case.system.stiffness.shape[0], dtype=bool)
    free_mask[case.system.fixed] = False
    qf_free_residual = np.asarray(case.system.stiffness @ qf_displacement - case.system.loads)[free_mask]
    qf_energy = float(0.5 * qf_displacement @ (case.system.stiffness @ qf_displacement))
    aster_energy = float(0.5 * np.sum(qf_f * aster_u))
    qf_balance_force = np.sum(qf_r + qf_f, axis=0)
    aster_balance_force = np.sum(aster_r + qf_f, axis=0)
    coordinates = np.asarray(case.model.nodes, dtype=np.float64)
    qf_balance_moment = np.sum(np.cross(coordinates, qf_r + qf_f), axis=0)
    aster_balance_moment = np.sum(np.cross(coordinates, aster_r + qf_f), axis=0)
    force_scale = max(float(np.sum(np.linalg.norm(qf_f, axis=1))), 1.0)
    length_scale = max(float(np.max(np.ptp(coordinates, axis=0))), 1.0)
    moment_scale = force_scale * length_scale
    fixed_nodes = np.unique(case.system.fixed // 3)
    tiny = float(np.finfo(np.float64).tiny)

    def relative_l2(actual: np.ndarray, expected: np.ndarray) -> float:
        return float(np.linalg.norm(actual - expected) / max(float(np.linalg.norm(expected)), tiny))

    def relative_linf(actual: np.ndarray, expected: np.ndarray) -> float:
        return float(np.max(np.abs(actual - expected), initial=0.0) / max(float(np.max(np.abs(expected), initial=0.0)), tiny))

    metrics = {
        "displacement_relative_l2": relative_l2(aster_u, qf_u),
        "displacement_relative_linf": relative_linf(aster_u, qf_u),
        "reaction_relative_l2": relative_l2(aster_r, qf_r),
        "reaction_relative_linf": relative_linf(aster_r, qf_r),
        "strain_energy_from_external_work_relative": abs(aster_energy - qf_energy) / max(abs(qf_energy), tiny),
        "qf_free_residual_relative_l2": float(np.linalg.norm(qf_free_residual) / force_scale),
        "qf_force_equilibrium_relative": float(np.linalg.norm(qf_balance_force) / force_scale),
        "aster_force_equilibrium_relative": float(np.linalg.norm(aster_balance_force) / force_scale),
        "qf_moment_equilibrium_relative": float(np.linalg.norm(qf_balance_moment) / moment_scale),
        "aster_moment_equilibrium_relative": float(np.linalg.norm(aster_balance_moment) / moment_scale),
        "fixed_displacement_abs_max": float(np.max(np.abs(aster_u[fixed_nodes]), initial=0.0)),
        "qf_energy_j": qf_energy,
        "aster_external_work_energy_j": aster_energy,
        "load_area_m2": case.load_area,
    }
    arrays = {
        "qf_displacement": qf_u,
        "qf_reaction": qf_r,
        "aster_displacement": aster_u,
        "aster_reaction": aster_r,
        "loads": qf_f,
    }
    if any(array.shape != qf_u.shape for array in (aster_u, aster_r, qf_r, qf_f)):
        raise CampaignError(f"{case.case_id}: raw vector shape mismatch")
    if any(not np.all(np.isfinite(array)) for array in arrays.values()):
        raise CampaignError(f"{case.case_id}: non-finite raw vector")
    return metrics, arrays


def _run_case(case: ExpandedCase, work: Path, contract: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=False)
    material = dict(MATERIAL)
    qf_u, qf_metrics = solve_linear_system(case.system)
    if not np.all(np.isfinite(qf_u)):
        raise CampaignError(f"{case.case_id}: QF linear solve produced non-finite displacement")
    np.savez_compressed(
        work / "model_inputs.npz",
        coordinates=np.asarray(case.model.nodes, dtype=np.float64),
        connectivity=np.asarray(case.connectivity, dtype=np.int64),
        fixed=np.asarray(case.system.fixed, dtype=np.int64),
        loads=np.asarray(case.system.loads, dtype=np.float64),
    )
    np.savez_compressed(work / "qf_result.npz", displacement=qf_u)
    save_npz(work / "qf_stiffness.npz", case.system.stiffness)
    write_json(
        work / "case.json",
        {
            "case_id": case.case_id,
            "family": case.family,
            "geometry": case.geometry,
            "dimensions_m": list(case.dimensions),
            "mesh": case.mesh,
            "divisions": list(case.divisions),
            "load_case": case.load_case,
            "resultant_N": list(case.resultant),
            "load_area_m2": case.load_area,
            "load_moment_origin_Nm": list(case.load_moment),
            "nodes": len(case.model.nodes),
            "elements": len(case.connectivity),
            "dofs": int(case.system.stiffness.shape[0]),
            "material": material,
            "model_fingerprint": model_fingerprint(
                case.family,
                case.model.nodes,
                case.connectivity,
                case.system.fixed,
                case.system.loads,
                material,
            ),
            "qf_metrics": qf_metrics,
            "source_sha": readiness["execution_sha"],
            "runner_sha": contract["runner_sha"],
            "contract_sha256": readiness["contract_sha256"],
        },
    )
    (work / f"{case.case_id}.mail").write_text(_mesh_text(case), encoding="ascii", newline="\n")
    (work / f"{case.case_id}.comm").write_text(_comm_text(case), encoding="utf-8", newline="\n")
    (work / f"{case.case_id}.export").write_text(
        _export_text(case, int(contract["timeout_seconds"]), int(contract["memory_limit_mb"])),
        encoding="ascii",
        newline="\n",
    )
    write_json(
        work / "result.json",
        {
            "status": "RUNNING",
            "case_id": case.case_id,
            "source_sha": readiness["execution_sha"],
            "runner_sha": contract["runner_sha"],
            "contract_sha256": readiness["contract_sha256"],
        },
    )

    docker = shutil.which("docker")
    if docker is None:
        raise CampaignError("Docker CLI disappeared after preflight")
    runtime_shell = _runtime_command(f"{ASTER_RUNNER} {case.case_id}.export --no-mpi")
    command = [
        docker,
        "run",
        "--rm",
        "--cpus=1",
        "--cidfile",
        str(work.resolve() / "container.cid"),
        "-v",
        f"{work.resolve()}:/work",
        "--workdir",
        "/work",
        "--entrypoint",
        "/bin/bash",
        IMAGE,
        "-lc",
        runtime_shell,
    ]
    telemetry_path = work / "telemetry.jsonl"
    progress_path = work / "progress.json"
    start = time.perf_counter()
    event_count = 0

    def emit(event: str, **fields: Any) -> None:
        nonlocal event_count
        event_count += 1
        row = {
            "event": event,
            "case_id": case.case_id,
            "family": case.family,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.perf_counter() - start,
            **fields,
        }
        with telemetry_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        write_json(progress_path, row)

    emit("RUN_START", status="STARTING", command=command)
    with (work / "stdout.log").open("w", encoding="utf-8", newline="\n") as stdout, (work / "stderr.log").open(
        "w", encoding="utf-8", newline="\n"
    ) as stderr:
        process = subprocess.Popen(command, cwd=work, stdout=stdout, stderr=stderr, text=True)
        started = datetime.now(timezone.utc).isoformat()
        emit("PROCESS_START", status="RUNNING", host_process_id=process.pid)
        while process.poll() is None:
            time.sleep(5.0)
            if process.poll() is None:
                emit("HEARTBEAT", status="RUNNING", host_process_id=process.pid)
        exit_code = int(process.returncode)
    container_id = (work / "container.cid").read_text(encoding="ascii").strip() if (work / "container.cid").exists() else None
    process_record = {
        "case_id": case.case_id,
        "family": case.family,
        "image": IMAGE,
        "image_id": readiness["code_aster_image_id"],
        "runtime_version": readiness["code_aster_runtime_version"],
        "command": command,
        "runtime_shell_command": runtime_shell,
        "host_process_id": process.pid,
        "container_id": container_id,
        "exit_code": exit_code,
        "elapsed_seconds": time.perf_counter() - start,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "fresh_container_process": True,
        "container_cpu_limit": 1,
        "solver_mpi_disabled": True,
        "telemetry_events": event_count + 1,
    }
    write_json(work / "process.json", process_record)
    emit("RUN_END", status="COMPLETED" if exit_code == 0 else "FAILED", exit_code=exit_code)
    if exit_code != 0:
        raise CampaignError(f"Code_Aster process exited with {exit_code}; see {work / 'stderr.log'}")
    raw = load_json(work / "aster_raw.json")
    if raw.get("status") != "PASS" or raw.get("case_id") != case.case_id or raw.get("family") != case.family:
        raise CampaignError("Code_Aster result identity/status mismatch")
    metrics, _ = _metric_comparison(case, qf_u, raw)
    gates = contract["gates"]
    comparisons = {
        key: {
            "value": metrics[key],
            "limit": float(limit),
            "status": "PASS" if np.isfinite(metrics[key]) and metrics[key] <= float(limit) else "FAIL",
        }
        for key, limit in gates.items()
    }
    status = "PASS_CANDIDATE" if all(row["status"] == "PASS" for row in comparisons.values()) else "FAIL_CLOSED"
    result = {
        "status": status,
        "case_id": case.case_id,
        "family": case.family,
        "source_sha": readiness["execution_sha"],
        "runner_sha": contract["runner_sha"],
        "contract_sha256": readiness["contract_sha256"],
        "model_fingerprint": case.fingerprint,
        "process": process_record,
        "metrics": metrics,
        "comparisons": comparisons,
        "raw_sha256": sha256_file(work / "aster_raw.json"),
    }
    write_json(work / "result.json", result)
    return result


def execute(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    contract_path, repo_root = contract_path.resolve(), repo_root.resolve()
    readiness, cases = preflight(contract_path, repo_root)
    contract = load_json(contract_path)
    output_root = (repo_root / contract["output_root"]).resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    write_json(output_root / "preflight.json", readiness)
    results: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(cases, start=1):
        case_path = output_root / case.case_id
        try:
            result = _run_case(case, case_path, contract, readiness)
        except Exception as exc:  # Each frozen model is an independent evidence unit.
            result = {
                "status": "FAIL_CLOSED_EXECUTION",
                "case_id": case.case_id,
                "family": case.family,
                "source_sha": readiness["execution_sha"],
                "runner_sha": contract["runner_sha"],
                "contract_sha256": readiness["contract_sha256"],
                "error": f"{type(exc).__name__}: {exc}",
            }
            if case_path.exists():
                write_json(case_path / "result.json", result)
        results[case.case_id] = result
        write_json(
            output_root / "progress.json",
            {
                "completed_cases": index,
                "total_cases": len(cases),
                "current_case": case.case_id,
                "current_status": result["status"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        _manifest(output_root, repo_root / contract["manifest_path"])
        if result.get("status") == "FAIL_CLOSED_EXECUTION":
            break
    passed = sum(result.get("status") == "PASS_CANDIDATE" for result in results.values())
    execution_aborted = len(results) < len(cases)
    family_summary = {
        family: {
            "cases": sum(result.get("family") == family for result in results.values()),
            "passed": sum(result.get("family") == family and result.get("status") == "PASS_CANDIDATE" for result in results.values()),
            "failed": sum(result.get("family") == family and result.get("status") != "PASS_CANDIDATE" for result in results.values()),
        }
        for family in FAMILIES
    }
    summary = {
        "work_package": "WP12",
        "campaign": "R3 expanded same-mesh linear-static Code_Aster correlation",
        "status": "PASS_CANDIDATE_WITH_LIMITATIONS" if passed == len(cases) else "FAIL_CLOSED",
        "case_count": len(cases),
        "attempted_case_count": len(results),
        "not_started_case_count": len(cases) - len(results),
        "execution_aborted_on_error": execution_aborted,
        "candidate_cases_passed": passed,
        "official_points_changed": False,
        "branch": readiness["branch"],
        "execution_sha": readiness["execution_sha"],
        "runner_sha": contract["runner_sha"],
        "model_builder_sha": contract["model_builder_sha"],
        "auditor_sha": contract["auditor_sha"],
        "contract_builder_sha": contract["contract_builder_sha"],
        "contract_sha256": readiness["contract_sha256"],
        "code_aster_image": IMAGE,
        "code_aster_image_id": readiness["code_aster_image_id"],
        "code_aster_runtime_version": readiness["code_aster_runtime_version"],
        "families": family_summary,
        "cases": results,
        "limitations": contract["limitations"],
    }
    write_json(output_root / "wp12_expanded_summary.json", summary)
    (output_root / "wp12_expanded_summary.md").write_text(render_summary(summary), encoding="utf-8", newline="\n")
    _manifest(output_root, repo_root / contract["manifest_path"])
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# WP12 R3 — Expanded Code_Aster Correlation",
        "",
        f"Status: **{summary['status']}**",
        "",
        f"Cases: {summary['candidate_cases_passed']}/{summary['case_count']} PASS_CANDIDATE",
        f"Attempted: {summary['attempted_case_count']}; not started: {summary['not_started_case_count']}; aborted on execution error: {summary['execution_aborted_on_error']}",
        "",
        "| Family | Cases | PASS | FAIL/HOLD |",
        "|---|---:|---:|---:|",
    ]
    for family, record in summary["families"].items():
        lines.append(f"| {family} | {record['cases']} | {record['passed']} | {record['failed']} |")
    lines.extend(["", "Official WP12 points are unchanged; this supplemental campaign does not award points.", "", "## Scope limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=_ROOT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    contract = args.contract if args.contract.is_absolute() else root / args.contract
    try:
        if args.execute:
            result = execute(contract, root)
        else:
            readiness, cases = preflight(contract, root)
            result = {**readiness, "case_ids": [case.case_id for case in cases]}
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result.get("status") in {"PREFLIGHT_PASS", "PASS_CANDIDATE_WITH_LIMITATIONS"} else 2
    except (CampaignError, OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"WP12_R3_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
