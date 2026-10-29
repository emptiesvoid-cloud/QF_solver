"""Generate the four closed-catalog adaptive meshes; never runs or assembles FEM."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from experiments.wp12_vv3d_adaptive import mesh, prepare, quality


def generate_adaptive(root: Path) -> list[dict]:
    if root.exists():
        raise FileExistsError("refusing to overwrite existing adaptive artifacts")
    root.mkdir(parents=True)
    entries=[]
    for family in mesh.FORMULATIONS:
        n=mesh.ADAPTIVE_LEVELS[family]
        generated=mesh.generate(family,n)
        if generated["summary"]["dofs"] > 30000:
            raise ValueError("adaptive mesh exceeds the 30000 DOF budget")
        checked=quality.assess(generated)
        raw=prepare.encode(generated)
        name=f"mesh_{family.lower()}_h1.json"
        prepare.write_new(root/name,raw)
        entries.append({"case_id":f"VV3D-ADAPT-{family}-H1","family":family,"n":n,"mesh_file":name,
                        "mesh_sha256":hashlib.sha256(raw).hexdigest(),"summary":generated["summary"],
                        "quality":checked,"nested_with_n8":n == 16,"nodeid":None,
                        "nodeid_status":"NOT_IMPLEMENTED_NOT_REGISTERED","execution_authorized":False})
    prepare.write_new(root/"ADAPTIVE_MESH_INDEX_NOT_AUTHORIZED.json",prepare.encode({
        "schema":"qf-wp12-vv3d-adaptive-meshes-v1","state":"PREPARED_NOT_AUTHORIZED","cases":entries}))
    return entries


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    print(f"Prepared {len(generate_adaptive(args.output))} adaptive meshes without assembly or solve.")
