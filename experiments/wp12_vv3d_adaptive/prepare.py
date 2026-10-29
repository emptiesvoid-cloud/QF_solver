"""Generate create-only, non-executable case descriptions and mesh hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from experiments.wp12_vv3d_adaptive.mesh import FORMULATIONS, LEVELS, generate
from experiments.wp12_vv3d_adaptive.oracle import E_PA, NU, AMPLITUDE_M, LENGTHS_M


def encode(data: object) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def write_new(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(contents)


def prepare(root: Path) -> list[dict]:
    if root.exists():
        raise FileExistsError("refusing to overwrite an existing campaign directory")
    root.mkdir(parents=True)
    cases = []
    for family in FORMULATIONS:
        for level,n in enumerate(LEVELS, 1):
            mesh = generate(family,n)
            summary = mesh["summary"]
            if summary["dofs"] > 30000 or summary["free_dofs"] < 1:
                raise ValueError("invalid DOF cap or no interior degrees of freedom")
            contents = encode(mesh)
            name = f"mesh_{family.lower()}_l{level}.json"
            write_new(root / name, contents)
            cases.append({"case_id": f"VV3D-{family}-L{level}", "formulation": family,
                "level": level, "mesh_file": name, "mesh_sha256": hashlib.sha256(contents).hexdigest(),
                "divisions": [n,n,n], **summary, "timeout_max_seconds": 1200, "rss_soft_limit_mib": 4096,
                "attempts_max": 1, "nodeid": None, "nodeid_status": "NOT_IMPLEMENTED_NOT_REGISTERED",
                "execution_authorized": False, "do_not_execute": True})
    metadata = {"schema": "qf-wp12-vv3d-prepared-matrix-v1", "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "state": "PREPARATION_AUTHORIZED_EXECUTION_NOT_AUTHORIZED", "model_status": "PROPOSED_OWNER_REVIEW",
        "physical_problem": {"domain_m": LENGTHS_M, "E_pa": E_PA, "nu": NU, "amplitude_m": AMPLITUDE_M,
            "boundary": "all boundary displacement components fixed to zero", "body_force": "oracle.field exact -div(sigma)",
            "notes": "smooth 3D manufactured solution; not a cantilever; consistent load discretization NOT IMPLEMENTED"},
        "global_proposed_budget": {"attempts_max": 24, "cumulative_machine_seconds_max": 28800,
            "timeout_max_seconds": 1200, "rss_soft_limit_mib": 4096, "dofs_max": 30000, "concurrency": 1,
            "automatic_retry": False}, "cases": cases}
    write_new(root / "MATRIX_NOT_AUTHORIZED.json", encode(metadata))
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new dedicated directory; never overwrites")
    args = parser.parse_args()
    print(f"Prepared {len(prepare(args.output))} mesh records; no FEM assembly or solve.")
