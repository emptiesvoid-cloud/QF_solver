"""Prepare the deterministic 5M TET4 workload and its preflight evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from solveur.large.generator import generate_tet4_block
from solveur.large.readiness import estimate_structured_tet4_size
from solveur.verification.observatory import canonical_digest, canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp04_execution_contract.json"
FREEZE_ID = "LU2-WP02-FREEZE-bfd1975b012453a3"
FREEZE_DIGEST = "bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1"
RUNTIME_IMAGE = "qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e"
NX, NY, NZ = 117, 117, 119
MODEL_ID = "LU2-WP04-5M-WORKLOAD-001"


def main() -> int:
    args = _parse_args()
    contract = _read_json(CONTRACT_PATH)
    _validate_contract(contract)
    if args.preflight:
        record = build_preflight(contract, args.output)
        _write(args.output, record)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0 if record["status"] == "PASS" else 1
    if args.build:
        record = build_workload(args.output, args.metadata, args.source_sha, contract)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    raise ValueError("Select exactly one of --preflight or --build.")


def build_preflight(contract: dict[str, Any], output: Path | None = None) -> dict[str, Any]:
    sizing = estimate_structured_tet4_size(NX, NY, NZ)
    disk_root = output or ROOT / "tmp" / "lu2_wp04"
    probe = disk_root
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    disk = shutil.disk_usage(probe)
    docker = _docker_probe()
    expected_disk = int(sizing["recommended_free_disk_bytes"]) * 2
    image_ok = docker["image_id"] is not None and docker["image_ref"] == RUNTIME_IMAGE
    docker_memory = docker["memory_bytes"]
    memory_ok = docker_memory is not None and docker_memory >= int(sizing["petsc_rule_of_thumb_bytes"])
    disk_ok = disk.free >= expected_disk
    status = "PASS" if image_ok and memory_ok and disk_ok else "RESOURCE_RISK"
    if docker_memory is None or docker["image_id"] is None:
        status = "RESOURCE_RISK"
    if docker_memory is not None and docker_memory < int(sizing["petsc_rule_of_thumb_bytes"]):
        status = "FAIL"
    if not disk_ok:
        status = "FAIL"
    return {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_bronze_preflight",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "status": status,
        "source_sha": contract["source_snapshot"],
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST},
        "workload": {
            "model_id": MODEL_ID,
            "dimensions": {"nx": NX, "ny": NY, "nz": NZ},
            "nodes": sizing["node_count"],
            "elements": sizing["element_count"],
            "true_dof": sizing["ndof"],
            "sizing": sizing,
        },
        "resources": {
            "docker_memory_bytes": docker_memory,
            "estimated_ram_bytes": sizing["petsc_rule_of_thumb_bytes"],
            "estimated_ram_margin_bytes": (
                int(docker_memory) - int(sizing["petsc_rule_of_thumb_bytes"])
                if docker_memory is not None
                else None
            ),
            "estimated_disk_bytes_for_two_recreations": expected_disk,
            "host_free_disk_bytes": int(disk.free),
            "host_total_disk_bytes": int(disk.total),
            "reference_3m_peak_rss_bytes": contract["preflight"]["reference_3m_peak_rss_bytes"],
            "extrapolation": "DIAGNOSTIC_ONLY; not an acceptance claim",
        },
        "docker": docker,
        "checks": {
            "true_dof_at_least_5m": sizing["ndof"] >= 5_000_000,
            "pinned_image_available": image_ok,
            "indicative_memory_within_budget": memory_ok,
            "two_run_disk_envelope_available": disk_ok,
            "no_oom_injection": True,
            "solve_not_required": True,
        },
        "configuration": {
            "backend": "petsc",
            "matrix_format": "aij",
            "ksp": "cg",
            "preconditioner": "gamg",
            "mpi_ranks": 8,
            "partition_strategy": "contiguous",
            "chunk_size": 4096,
            "freeze_digest_sha256": FREEZE_DIGEST,
        },
        "artifact_classification": "CONTROLLED_PROOF",
    }


def build_workload(
    output: Path,
    metadata_path: Path,
    source_sha: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    output = output.resolve()
    metadata_path = metadata_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    model = generate_tet4_block(
        output,
        nx=NX,
        ny=NY,
        nz=NZ,
        length=2.0,
        height=0.75,
        depth=1.25,
        young=210.0e9,
        poisson=0.3,
        density=7800.0,
        total_load=1_000_000.0,
        load_component=0,
        load_distribution="uniform",
        decomposition="six",
    )
    digest = _sha256_file(output)
    record = {
        "schema_version": 1,
        "record_type": "lu2_wp04_5m_workload_build",
        "work_package": "LU2-WP04",
        "gate": "LU2-027-G04",
        "status": "PASS",
        "source_sha": source_sha,
        "freeze": {"freeze_id": FREEZE_ID, "freeze_digest_sha256": FREEZE_DIGEST},
        "workload": {
            "model_id": MODEL_ID,
            "element_family": "TET4",
            "analysis": "linear_static",
            "nodes": model.node_count,
            "elements": model.element_count,
            "true_dof": model.ndof,
            "input_digest_sha256": digest,
            "input_file_bytes": output.stat().st_size,
            "geometry": {"nx": NX, "ny": NY, "nz": NZ, "length_m": 2.0, "height_m": 0.75, "depth_m": 1.25},
            "material": {"type": "isotropic_linear_elastic", "young_modulus_pa": 210.0e9, "poisson_ratio": 0.3, "density_kg_m3": 7800.0},
            "boundary_condition": "all translations fixed at x=0",
            "load": {"type": "uniform nodal x load", "face": "x=length", "total_force_n": 1_000_000.0},
        },
        "generation": {
            "seconds": time.perf_counter() - started,
            "command": [
                "python",
                "scripts/prepare_lu2_wp04_workload.py",
                "--build",
                "--output",
                _repo_relative(output),
                "--metadata",
                _repo_relative(metadata_path),
                "--source-sha",
                source_sha,
            ],
            "generator": "solveur.large.generator.generate_tet4_block",
            "deterministic_parameters_digest": canonical_digest(contract["workload"]),
        },
        "provenance": {
            "contract_path": "qualification/0_2_7/wp04_execution_contract.json",
            "contract_digest_sha256": _sha256_file(CONTRACT_PATH),
            "source_sha": source_sha,
            "artifact_classification": "CONTROLLED_PROOF",
        },
    }
    _write(metadata_path, record)
    return record


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--build", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--source-sha", default="2581e4750eb024628c5592d6c49cef503020c3aa")
    return parser.parse_args()


def _validate_contract(contract: dict[str, Any]) -> None:
    if contract["freeze"]["freeze_id"] != FREEZE_ID or contract["freeze"]["freeze_digest_sha256"] != FREEZE_DIGEST:
        raise ValueError("WP02 freeze does not match the WP04 contract.")
    expected = contract["workload"]["expected_size"]
    actual = estimate_structured_tet4_size(NX, NY, NZ)
    if {"nodes": actual["node_count"], "elements": actual["element_count"], "true_dof": actual["ndof"]} != expected:
        raise ValueError("WP04 expected size does not match deterministic dimensions.")
    if contract["freeze"]["runtime_image"] != RUNTIME_IMAGE:
        raise ValueError("WP04 runtime image is not pinned to the WP02 image.")


def _docker_probe() -> dict[str, Any]:
    image_id = None
    memory = None
    try:
        image = subprocess.run(
            ["docker", "image", "inspect", RUNTIME_IMAGE, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if image.returncode == 0:
            image_id = image.stdout.strip() or None
    except OSError:
        pass
    try:
        info = subprocess.run(
            ["docker", "info", "--format", "{{.MemTotal}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if info.returncode == 0 and info.stdout.strip().isdigit():
            memory = int(info.stdout.strip())
    except OSError:
        pass
    return {"image_ref": RUNTIME_IMAGE, "image_id": image_id, "memory_bytes": memory}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value) + b"\n")


if __name__ == "__main__":
    raise SystemExit(main())
