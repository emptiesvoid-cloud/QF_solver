"""Frozen compact connected elbow runtime experiment; no production-kernel edits."""
from __future__ import annotations

# ruff: noqa: E402
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from run_wp13_01c_runtime import MATERIAL, _fixed_indices, _petsc_run, _serial_run
from run_wp13_01g_connected_mixed import _element_graph, _partition_metadata
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.large.generic_distributed import GenericDistributedModel, dispatch_element

CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_01k_contract.json"
OUT = ROOT / "qualification/0_2_8/wp13_01k_runtime"


def build(n):
    nodes, lookup, rows = [], {}, []

    def node(i, j, k):
        key = (i, j, k)
        if key not in lookup:
            lookup[key] = len(nodes)
            nodes.append(np.array(key, dtype=float) / n)
        return lookup[key]

    def add(family, ids, i, j, k, sub):
        if family == "TET4":
            x = np.array([nodes[a] for a in ids])
            if np.linalg.det((x[1:] - x[0]).T) < 0:
                ids[0], ids[1] = ids[1], ids[0]
        rows.append((((i+j+k) % 4, k, j, i, sub),
                     {"type": family, "nodes": ids, "material": "solid"}))

    for k in range(n):
        for j in range(-n, 0):
            for i in range(n):
                ids = [node(i+dx, j+dy, k+dz) for dx, dy, dz in
                       [(0,0,0),(1,0,0),(1,1,0),(0,1,0),
                        (0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
                add("HEX8", ids, i, j, k, 0)
    for k in range(3*n):
        for j in range(n):
            for i in range(n-j):
                triangles = [[(i,j),(i+1,j),(i,j+1)]]
                if i+j < n-1:
                    triangles.append([(i+1,j),(i+1,j+1),(i,j+1)])
                for t, triangle in enumerate(triangles):
                    lower = [node(x,y,k) for x,y in triangle]
                    upper = [node(x,y,k+1) for x,y in triangle]
                    if k < 2*n:
                        add("WEDGE6", lower+upper, i,j,k,t)
                    else:
                        pairs = sorted(zip(lower, upper))
                        (a,A),(b,B),(c,C) = pairs
                        for s, ids in enumerate([[a,b,c,C],[a,b,B,C],[a,A,B,C]]):
                            add("TET4", ids, i,j,k,3*t+s)
    points = np.asarray(nodes)
    fixed = [{"node": i, "dofs": ["UX","UY","UZ"]}
             for i,p in enumerate(points) if p[1] == -1]
    loaded = [i for i,p in enumerate(points) if p[2] == 3]
    return FiniteElementModel.from_raw(
        nodes=points.tolist(), elements=[r for _,r in sorted(rows,key=lambda r:r[0])],
        materials={"solid": dict(MATERIAL)}, fixed_dofs=fixed,
        loads=[{"node": i,"dof":"UZ","value":1e5/len(loaded)} for i in loaded],
        analysis={"type":"linear_static"}, units={"system":"SI"})


def precheck(model, n, contract):
    generic = GenericDistributedModel.from_finite_element_model(model)
    diagonal = np.zeros(generic.ndof)
    det_min, det_max, aspect, jac_cond = math.inf, 0., 0., 0.
    entry_min, entry_max = math.inf, 0.
    family_nodes = {f:set() for f in ("TET4","WEDGE6","HEX8")}
    for e in generic.iter_elements():
        x = generic.nodes[list(e.nodes)]
        family_nodes[e.family].update(e.nodes)
        distances = np.linalg.norm(x[:,None]-x[None,:],axis=2)
        positive = distances[distances>0]
        aspect = max(aspect, float(positive.max()/positive.min()))
        if e.family == "TET4":
            js = [(x[1:]-x[0]).T]
        else:
            kernel = Hex8Element if e.family == "HEX8" else Wedge6Element
            js = [kernel.jacobian(x,p) for p in kernel.integration_points]
        for jac in js:
            determinant = float(np.linalg.det(jac))
            det_min, det_max = min(det_min,determinant), max(det_max,determinant)
            jac_cond = max(jac_cond, float(np.linalg.cond(jac)))
        c = dispatch_element(generic,e)
        diagonal[c.global_dofs] += np.diag(c.stiffness)
        positive = np.abs(c.stiffness[c.stiffness != 0])
        entry_min,entry_max = min(entry_min,float(positive.min())),max(entry_max,float(positive.max()))
    connectivity, components = _element_graph(model)
    connectivity["mechanical_load_path"] = "LOAD -> TET4 -> WEDGE6 -> HEX8 -> SUPPORT"
    no_bypass = not family_nodes["TET4"].intersection(family_nodes["HEX8"])
    criteria = contract["conditioning_acceptance"]
    gates = {
        "aspect": aspect <= criteria["max_element_edge_aspect"],
        "jacobian_condition": jac_cond <= criteria["max_affine_jacobian_condition"],
        "jacobian_min": det_min*n**3 >= criteria["min_detJ_over_h_cubed"],
        "jacobian_max": det_max*n**3 <= criteria["max_detJ_over_h_cubed"],
        "diagonal": bool(np.all(diagonal>0)) and float(diagonal.max()/diagonal.min()) <= criteria["max_positive_assembled_diagonal_ratio"],
        "connected": connectivity["connected_components"] == 1,
        "no_bypass": no_bypass,
        "load_only_tet": connectivity["load_families"] == ["TET4"],
        "support_only_hex": connectivity["fixed_families"] == ["HEX8"],
        "valid_interfaces": not connectivity["scope_errors"],
    }
    return {"gates":gates,"max_aspect_ratio":aspect,"min_jacobian":det_min,
            "max_jacobian":det_max,"max_jacobian_condition":jac_cond,
            "stiffness_diagonal_range":[float(diagonal.min()),float(diagonal.max())],
            "stiffness_diagonal_ratio":float(diagonal.max()/diagonal.min()),
            "stiffness_entry_range":[entry_min,entry_max],
            "stiffness_entry_ratio":entry_max/entry_min,
            "condition_number":"NOT_COMPUTED; geometry and positive diagonal proxies only",
            "connectivity":connectivity,"direct_support_bypass":not no_bypass},components


def interface_forces(model, result):
    generic = GenericDistributedModel.from_finite_element_model(model)
    u = np.asarray(result["displacement"])
    forces = {f:np.zeros(generic.ndof) for f in ("TET4","WEDGE6","HEX8")}
    nodes = {f:set() for f in forces}
    for e in generic.iter_elements():
        c = dispatch_element(generic,e)
        forces[e.family][c.global_dofs] += c.stiffness @ u[c.global_dofs]
        nodes[e.family].update(e.nodes)
    checks = {}
    for a,b in [("TET4","WEDGE6"),("WEDGE6","HEX8")]:
        shared = sorted(nodes[a]&nodes[b])
        ids = np.array([generic.dofs.index(i,d) for i in shared for d in ("UX","UY","UZ")])
        fa,fb = forces[a][ids].reshape(-1,3),forces[b][ids].reshape(-1,3)
        ra,rb = fa.sum(axis=0),fb.sum(axis=0)
        checks[a+"_"+b] = {
            "shared_nodes":len(shared),"displacement_jump":0.,
            "nodal_force_jump_relative":float(np.linalg.norm(fa+fb)/1e5),
            "force_a_N":ra.tolist(),"force_b_N":rb.tolist(),
            "transfer_error_relative":float(np.linalg.norm(ra-np.array([0.,0.,-1e5]))/1e5),
            "unique_dofs":len(ids)==len(set(ids.tolist()))}
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["small","stage_a","stage_b"],required=True)
    parser.add_argument("--backend",choices=["serial","petsc"],default="petsc")
    parser.add_argument("--label",required=True)
    args = parser.parse_args()
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank,ranks = comm.rank,comm.size
    contract = json.loads(CONTRACT_PATH.read_text())
    n = contract["stages"][args.case]["n"]
    model = build(n)
    OUT.mkdir(parents=True,exist_ok=True)
    if rank == 0:
        pre,components = precheck(model,n,contract)
        assert model.dof_manager().ndof == contract["stages"][args.case]["dof"]
        (OUT/(args.label+"_pre.json")).write_text(json.dumps(pre,indent=2)+"\n")
        print(json.dumps({"precheck":args.label,"gates":pre["gates"]}),flush=True)
        ok = all(pre["gates"].values())
    else:
        ok = None
    if not comm.bcast(ok,root=0):
        return 2
    if args.backend == "serial":
        assert ranks == 1 and args.case == "small"
        result = _serial_run(model)
    else:
        result = _petsc_run(model,"lu","auto",2,True)
    if rank:
        return 0
    partition = _partition_metadata(model,ranks,components)
    interfaces = interface_forces(model,result)
    u = np.asarray(result["displacement"])
    residual = np.asarray(result["residual"])
    loads = np.asarray(result["loads"])
    fixed = _fixed_indices(model)
    reaction = np.zeros_like(residual)
    reaction[fixed] = residual[fixed]
    # All elements have XYZ translation DOFs in this benchmark.
    normal = reaction.reshape(-1,3).sum(axis=0)+loads.reshape(-1,3).sum(axis=0)
    stable = np.array([math.fsum(reaction.reshape(-1,3)[:,i])+math.fsum(loads.reshape(-1,3)[:,i]) for i in range(3)])
    denom = max(float(np.linalg.norm(loads.reshape(-1,3).sum(axis=0))),1.)
    g = contract["gates"]
    gates = {
        "residual":result["free_residual_relative"]<=g["free_residual"],
        "equilibrium":float(np.linalg.norm(normal)/denom)<=g["equilibrium"],
        "equilibrium_fsum":float(np.linalg.norm(stable)/denom)<=g["equilibrium"],
        "energy":result["energy_identity_relative"]<=g["energy_identity"],
        "reallocations":result["reallocations"]==0,
        "interfaces":all(v["nodal_force_jump_relative"]<=g["interface_nodal_force_jump_over_external_load_norm"]
                         and v["transfer_error_relative"]<=g["interface_resultant_transfer_relative"]
                         and v["unique_dofs"] for v in interfaces.values()),
        "cross_rank":ranks==1 or (
            sum(partition["cross_rank_interfaces"].values()) > 0
            and result["ghost_nodes_global_sum"] > 0),
    }
    np.savez_compressed(OUT/(args.label+".npz"),displacement=u,
                        reactions=reaction[fixed],residual=residual,energy=result["energy"])
    for field in ["displacement","reaction_vector","residual","loads"]:
        result.pop(field,None)
    payload = {"contract_id":contract["contract_id"],
               "contract_sha256":hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
               "case":args.case,"result":result,"partition":partition,"interfaces":interfaces,
               "force_defect_N":normal.tolist(),"force_defect_fsum_N":stable.tolist(),
               "force_defect_norm_N":float(np.linalg.norm(normal)),
               "equilibrium_normal":float(np.linalg.norm(normal)/denom),"gates":gates,
               "status":"PASS" if all(gates.values()) else "FAIL",
               "memory_limitations":"Global input model and partition metadata replicated; solution scattered to all; result vectors gathered to root. No structural MPI gather of K/connectivity."}
    (OUT/(args.label+".json")).write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps({"label":args.label,"status":payload["status"],"gates":gates,
                      "ndof":result["ndof"],"equilibrium":payload["equilibrium_normal"],
                      "residual":result["free_residual_relative"],"runtime":result["runtime_seconds"]}),flush=True)
    return 0 if all(gates.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
