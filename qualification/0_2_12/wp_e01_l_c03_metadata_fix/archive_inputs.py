#!/usr/bin/env python3
"""Verify immutable WP-E01-L archives and derive exact C03 trial-path inputs.

This offline script reads archive JSON and frozen source files only. It does
not import the solver, numerical kernels, NumPy, SciPy, pytest, or run FEM.
Binary64 JSON numbers are mapped to their exact rational value. HEX8
quadrature's 1/sqrt(3) is enclosed by exact rational interval arithmetic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


SNAPSHOT_COMMIT = "87e54913077c7d9fce6f259fb4a4a11f5295e6a5"
SNAPSHOT_TREE = "c42e3c2241af1862d66cab51a38fda74a1167361"
PROBE_DEFAULT = Path(os.environ["QF_WP_E01_PROBE_ARCHIVE"]) if os.environ.get("QF_WP_E01_PROBE_ARCHIVE") else None
HEX8_DEFAULT = Path(os.environ["QF_WP_E01_HEX8_ARCHIVE"]) if os.environ.get("QF_WP_E01_HEX8_ARCHIVE") else None
SNAPSHOT_DEFAULT = Path(os.environ["QF_WP_E01_HISTORICAL_ROOT"]) if os.environ.get("QF_WP_E01_HISTORICAL_ROOT") else None
ADAPTER_REPO_DEFAULT = Path(os.environ["QF_WP_E01_ADAPTER_REPO"]) if os.environ.get("QF_WP_E01_ADAPTER_REPO") else None
OUT_DEFAULT = Path(__file__).parent
SEGMENT = (Fraction(-1, 10000), Fraction(1, 10000))
HEX_SIGNS = ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def extraction_stage_metadata() -> dict[str, Any]:
    """Return provisional fields only; extraction does not classify branches."""
    return {
        "extraction_stage": {
            "status": "INPUTS_EXTRACTED_PENDING_PROOF_EVALUATION",
            "strict_action_proofs_ready": False,
            "reason": "Extraction verifies frozen inputs and archives only. Full-segment mathematical signs and production base-branch linkage are evaluated later by integrate_proofs.py.",
        },
        "technical_aggregate_verdict": "NOT_EVALUATED",
    }


def q(v: Any) -> Fraction:
    if isinstance(v, bool):
        raise TypeError("boolean is not a frozen numeric input")
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError("nonfinite archived float")
        return Fraction(*v.as_integer_ratio())
    raise TypeError(f"unsupported archived numeric type: {type(v).__name__}")


def rat(x: Fraction) -> dict[str, str]:
    return {"numerator": str(x.numerator), "denominator": str(x.denominator)}


def iv(a: Fraction, b: Fraction | None = None) -> tuple[Fraction, Fraction]:
    b = a if b is None else b
    if a > b:
        raise ValueError("invalid interval")
    return a, b


def iadd(x, y): return (x[0] + y[0], x[1] + y[1])
def ineg(x): return (-x[1], -x[0])
def isub(x, y): return iadd(x, ineg(y))
def imul(x, y):
    vals = (x[0]*y[0], x[0]*y[1], x[1]*y[0], x[1]*y[1])
    return min(vals), max(vals)
def idiv(x, y):
    if y[0] <= 0 <= y[1]: raise ZeroDivisionError("interval denominator includes zero")
    return imul(x, (1/y[1], 1/y[0]))
def iscale(c: Fraction, x): return imul(iv(c), x)
def isquare(x):
    if x[0] <= 0 <= x[1]: return Fraction(0), max(x[0]*x[0], x[1]*x[1])
    vals=(x[0]*x[0],x[1]*x[1]); return min(vals),max(vals)
def ijson(x): return {"lo": rat(x[0]), "hi": rat(x[1])}


def sqrt_interval(x: Fraction, bits: int = 192) -> tuple[Fraction, Fraction]:
    if x < 0: raise ValueError("negative radicand")
    scale = 1 << bits
    n = math.isqrt((x.numerator * scale * scale) // x.denominator)
    lo = Fraction(n, scale)
    exact = n*n*x.denominator == x.numerator*scale*scale
    return (lo, lo if exact else Fraction(n+1, scale))


def safe_inventory(root: Path, file_name: str, items_name: str = "files") -> dict[str, str]:
    manifest = json.loads((root / file_name).read_text(encoding="utf-8"))
    if items_name == "files":
        items = manifest["files_excluding_this_manifest"]
        files = {item["path"]: item["sha256"] for item in items}
        sizes = {item["path"]: item["size_bytes"] for item in items}
        if len(files) != manifest["file_count_excluding_this_manifest"]:
            raise ValueError(f"{root}: inventory count mismatch")
    else:
        items = manifest["artifacts"]
        files = {item["path"]: item["sha256"] for item in items}
        sizes = {item["path"]: item["size_bytes"] for item in items}
        if len(files) != manifest["artifact_count"]:
            raise ValueError(f"{root}: inventory count mismatch")
    actual = set()
    for rel, expected in files.items():
        p = (root / rel).resolve(strict=True)
        if root.resolve() not in p.parents:
            raise ValueError(f"unsafe inventory path {rel}")
        if sha256(p).lower() != expected.lower():
            raise ValueError(f"archive hash mismatch: {root / rel}")
        if p.stat().st_size != sizes[rel]:
            raise ValueError(f"archive size mismatch: {root / rel}")
        actual.add(rel.replace("\\", "/"))
    actual_files={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != file_name}
    if actual != actual_files:
        raise ValueError(f"{root}: archive file set differs from inventory")
    return files


def source_identity(root: Path) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root, text=True).strip()
    if head != SNAPSHOT_COMMIT or tree != SNAPSHOT_TREE:
        raise ValueError(f"historical source identity mismatch: {head}/{tree}")
    if status:
        raise ValueError("historical checkout is dirty")
    result = {"commit": head, "tree": tree, "clean": True, "source_files": {}}
    for rel in ("tests/unit/test_wp_e01l_j2_reduced_space_diagnostic.py", "tests/conftest.py",
                "src/solveur/elements/solid/j2_state.py", "src/solveur/core/nonlinear/material_state.py"):
        result["source_files"][rel] = sha256(root / rel)
    return result


def canonical_state(value: Any) -> Any:
    """Reproduce the frozen digest's primitive/list/mapping encoding.

    Observed histories contain Python dict/list/scalar values; json_value
    stringifies mapping keys, so restore the original integer element keys.
    The archived records contain no ndarray state values.
    """
    if value is None: return {"type":"none"}
    if isinstance(value,bool): return {"type":"bool","value":value}
    if isinstance(value,str): return {"type":"str","value":value}
    if isinstance(value,int): return {"type":"int","value":str(value)}
    if isinstance(value,float):
        if not math.isfinite(value): raise ValueError("nonfinite state value")
        return {"type":"float","value":value.hex()}
    if isinstance(value,list): return {"type":"list","items":[canonical_state(item) for item in value]}
    if isinstance(value,dict):
        entries=[]
        for key,item in value.items():
            if isinstance(key,str) and key.isdecimal(): key=int(key)
            ck={"type":"str","value":key} if isinstance(key,str) else {"type":"int","value":str(key)}
            entries.append((ck,canonical_state(item)))
        entries.sort(key=lambda entry:json.dumps(entry[0],sort_keys=True))
        return {"type":"mapping","entries":entries}
    raise TypeError(f"unsupported canonical state type {type(value).__name__}")


def verify_history_digest(record: dict[str, Any]) -> str:
    history=record["observed_data"]["accepted_history"]
    payload=json.dumps(canonical_state(history),sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if digest != record.get("accepted_history_digest_before") or digest != record.get("accepted_history_digest_after"):
        raise ValueError(f"accepted history digest mismatch for {record.get('case_id')}")
    return digest


def solve3(a: list[list[Fraction]], b: list[Fraction]) -> list[Fraction]:
    m = [row[:] + [v] for row, v in zip(a, b)]
    for col in range(3):
        pivot = next((r for r in range(col, 3) if m[r][col]), None)
        if pivot is None: raise ValueError("singular tet geometry")
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        m[col] = [v/scale for v in m[col]]
        for r in range(3):
            if r == col: continue
            f = m[r][col]
            m[r] = [m[r][j] - f*m[col][j] for j in range(4)]
    return [m[i][3] for i in range(3)]


def gradients(element_nodes, nodes, family, signs=None):
    coords = [[q(v) for v in nodes[index]] for index in element_nodes]
    if family == "TET4":
        # J rows are physical coordinates; columns are the three reference edges.
        j = [[coords[a+1][i] - coords[0][i] for a in range(3)] for i in range(3)]
        # Solve J^T * grad(N_a) = grad_ref(N_a).
        out = [solve3([[j[k][i] for k in range(3)] for i in range(3)], [-1,-1,-1])]
        out.extend(solve3([[j[k][i] for k in range(3)] for i in range(3)], [1 if a == i else 0 for i in range(3)]) for a in range(3))
        return [[iv(x) for x in row] for row in out]
    # Frozen source uses a regular 0.5 m cube grid; verify this element is axis-aligned.
    axis = []
    for d in range(3):
        vals = {p[d] for p in coords}
        if len(vals) != 2: raise ValueError("HEX8 input is not the archived affine cube")
        axis.append(sorted(vals)[1] - sorted(vals)[0])
    if axis != [Fraction(1,2)]*3:
        raise ValueError("HEX8 affine cube dimensions differ from the archived source fixture")
    center=[(min(p[d] for p in coords)+max(p[d] for p in coords))/2 for d in range(3)]
    for local,(sx,sy,sz) in enumerate(HEX_SIGNS):
        expected=[center[0]+Fraction(sx,4),center[1]+Fraction(sy,4),center[2]+Fraction(sz,4)]
        if coords[local] != expected:
            raise ValueError(f"HEX8 connectivity/order differs from frozen source at local node {local}")
    eta = [iscale(Fraction(sign), iv(*sqrt_interval(Fraction(1,3)))) for sign in signs]
    ret=[]
    for sx,sy,sz in HEX_SIGNS:
        ret.append([
            iscale(Fraction(sx,2), imul(iadd(iv(1), iscale(Fraction(sy), eta[1])), iadd(iv(1), iscale(Fraction(sz), eta[2])))),
            iscale(Fraction(sy,2), imul(iadd(iv(1), iscale(Fraction(sx), eta[0])), iadd(iv(1), iscale(Fraction(sz), eta[2])))),
            iscale(Fraction(sz,2), imul(iadd(iv(1), iscale(Fraction(sx), eta[0])), iadd(iv(1), iscale(Fraction(sy), eta[1])))),
        ])
    return ret


def grad_u(element_nodes, gradients_, displacement):
    # Return the full displacement gradient; symmetrize at the strain boundary.
    local = [[q(displacement[3*n+i]) for i in range(3)] for n in element_nodes]
    gu=[]
    for i in range(3):
        row=[]
        for j in range(3):
            total=iv(Fraction(0))
            for a in range(len(element_nodes)):
                total=iadd(total,imul(iv(local[a][i]),gradients_[a][j]))
            row.append(total)
        gu.append(row)
    return gu


def small_strain(element_nodes, gradients_, displacement):
    gu=grad_u(element_nodes,gradients_,displacement)
    return [[iscale(Fraction(1,2),iadd(gu[i][j],gu[j][i])) for j in range(3)] for i in range(3)]


def affine_deviators(element_nodes, nodes, family, base_u, direction, history, point_signs, young, poisson):
    g = gradients(element_nodes, nodes, family, point_signs)
    e0=small_strain(element_nodes,g,base_u); e1=small_strain(element_nodes,g,direction)
    p=history["plastic_strain"]
    # State ordering is xx, yy, zz, xy, yz, zx in engineering-shear convention.
    plastic=[q(v) for v in p]
    ep=[[iv(plastic[0]),iv(plastic[3]/2),iv(plastic[5]/2)],
        [iv(plastic[3]/2),iv(plastic[1]),iv(plastic[4]/2)],
        [iv(plastic[5]/2),iv(plastic[4]/2),iv(plastic[2])]]
    eel=[[isub(e0[i][j],ep[i][j]) for j in range(3)] for i in range(3)]
    E,nu=young,poisson
    mu=E/(2*(1+nu)); lam=E*nu/((1+nu)*(1-2*nu))
    def deviator(strain):
        trace=iadd(iadd(strain[0][0],strain[1][1]),strain[2][2])
        stress=[]
        for i in range(3):
            row=[]
            for j in range(3):
                val=iscale(2*mu,strain[i][j])
                if i==j: val=iadd(val,iscale(lam,trace))
                row.append(val)
            stress.append(row)
        tr=iadd(iadd(stress[0][0],stress[1][1]),stress[2][2])
        return [[isub(stress[i][j],iscale(Fraction(1,3),tr) if i==j else iv(Fraction(0))) for j in range(3)] for i in range(3)]
    d0=deviator(eel); d1=deviator(e1)
    return [v for row in d0 for v in row], [v for row in d1 for v in row]


def coefficient_intervals(s0, ds):
    # q^2=3/2 dev:dev; independent interval products remain conservative.
    A=iv(Fraction(0));B=iv(Fraction(0));C=iv(Fraction(0))
    for x,y in zip(s0,ds):
        A=iadd(A,iscale(Fraction(3,2),isquare(x)))
        B=iadd(B,iscale(Fraction(3),imul(x,y)))
        C=iadd(C,iscale(Fraction(3,2),isquare(y)))
    return A,B,C


def branch_state(data, element, point):
    states=data["observed_data"]["production_trial_state_by_integration_point"][str(element)]
    if point >= len(states): raise ValueError(f"production branch record missing for element {element}, point {point}")
    state=states[point]
    return ("elastic" if state["elastic"] else "plastic"), state


def load_case(archive: Path, case_id: str):
    path=archive/"cases"/case_id/"case.json"
    record=json.loads(path.read_text(encoding="utf-8"))
    if record.get("case_id") != case_id or record.get("status") != "COMPLETE_EXPLORATORY":
        raise ValueError(f"case absent/incomplete: {path}")
    if record.get("historical_snapshot_commit") != SNAPSHOT_COMMIT:
        raise ValueError(f"historical commit mismatch in {path}")
    if record.get("rigorous_roundoff_and_truncation_bounds") != "NOT_ESTABLISHED_BY_EXPLORATORY_PROBE":
        raise ValueError(f"unexpected archive status metadata: {path}")
    verify_history_digest(record)
    return record, path


def exact_input(v):
    return rat(q(v))


def point_input(v):
    return ijson(iv(q(v)))


def extract_action(record, case_path: Path, source: dict[str, Any], capture: dict[str, Any], family: str, hmod: float):
    obs=record["observed_data"]
    nodes=obs["nodes"]; base=obs["base_state_displacement_m"]
    elems=obs["elements"]
    if family not in ("TET4","HEX8"): raise ValueError(family)
    expected_dofs=len(base)
    if expected_dofs != 3*len(nodes): raise ValueError("mesh/displacement shape mismatch")
    step=record["centered_difference_observations"]
    dirs=[o["full_projected_direction"] for o in step]
    if not dirs or any(len(d)!=expected_dofs for d in dirs): raise ValueError("archived action direction missing or malformed")
    # All finite-difference records preserve the same exact projected direction.
    if any(d != dirs[0] for d in dirs[1:]): raise ValueError("direction changed across records")
    direction=dirs[0]
    # Constants are source literals evaluated as binary64 in the historical test.
    E=q(210.0e9); nu=q(0.30); sigma_y=q(250.0e6); hardening=q(hmod)
    action_id=record["case_id"]
    proof_points=[]
    obs_sha=sha256(case_path)
    for element in elems:
        elidx=element["index"]
        if str(elidx) not in obs["accepted_history"]: raise ValueError(f"history missing element {elidx}")
        states=obs["accepted_history"][str(elidx)]
        expected_n=1 if family=="TET4" else 8
        if len(states)!=expected_n: raise ValueError(f"history point count mismatch at element {elidx}")
        for pi,hist in enumerate(states):
            point_id=f"e{elidx}:q{pi}"
            branch, prod_state=branch_state(record,elidx,pi)
            # Frozen reference oracle enumerates product((-1, 1), repeat=3),
            # with z varying fastest, then y, then x.
            signs=((-1 if pi < 4 else 1),(-1 if (pi % 4) < 2 else 1),(-1 if pi % 2 == 0 else 1)) if family=="HEX8" else None
            s0,ds=affine_deviators(element["nodes"],nodes,family,base,direction,hist,signs,E,nu)
            A,B,C=coefficient_intervals(s0,ds)
            resistance=sigma_y+hardening*q(hist["equivalent_plastic_strain"])
            point={
                "action_id":action_id,"point_id":point_id,"expected_branch":branch,
                "segment_s_m":{"lo":rat(SEGMENT[0]),"hi":rat(SEGMENT[1])},
                "A_pa2":ijson(A),"B_pa2_per_m":ijson(B),"C_pa2_per_m2":ijson(C),
                "R_pa":ijson(iv(resistance)),
                "affine_deviator_base_pa":[ijson(x) for x in s0],
                "affine_deviator_direction_pa_per_m":[ijson(x) for x in ds],
                "production_base_branch_archived":branch,
                "production_base_state_record":prod_state,
                "incoming_plastic_strain_voigt_binary64_exact":[point_input(v) for v in hist["plastic_strain"]],
                "incoming_equivalent_plastic_strain_binary64_exact":point_input(hist["equivalent_plastic_strain"]),
                "production_branch_linkage_valid":False,"production_rounding_budget_valid":False,
                "provenance_valid":True,
                "provenance_refs":{
                    "case_json":case_path.relative_to(case_path.parents[2]).as_posix(),"case_json_sha256":obs_sha,
                    "history_field":f"observed_data.accepted_history.{elidx}[{pi}]",
                    "direction_field":"centered_difference_observations[*].full_projected_direction",
                    "geometry_fields":["observed_data.nodes","observed_data.elements"],
                    "base_state_field":"observed_data.base_state_displacement_m",
                "production_branch_field":f"observed_data.production_trial_state_by_integration_point.{elidx}[{pi}].elastic",
                    "historical_commit":source["commit"],"historical_tree":source["tree"],
                    "historical_test_sha256":source["source_files"]["tests/unit/test_wp_e01l_j2_reduced_space_diagnostic.py"],
                    "capture_commit":capture["commit"],"capture_tree":capture["tree"],
                    "capture_serializer_hashes":capture["file_sha256"]
                }
            }
            proof_points.append(point)
    return {"schema_version":1,"action_id":action_id,"family":family,
            "elasticity_modulus_pa":exact_input(210.0e9),"poisson_ratio":exact_input(0.30),
            "yield_stress_pa":exact_input(250.0e6),"hardening_modulus_pa":exact_input(hmod),
            "frozen_inputs":{
                "binary64_interpretation":"Each archived/source binary64 value is represented as its exact integer-ratio rational point interval.",
                "material_constants":{"E_pa":point_input(210.0e9),"nu":point_input(0.30),"sigma_y0_pa":point_input(250.0e6),"H_pa":point_input(hmod)},
                "nodes_m_binary64_exact":[[point_input(v) for v in row] for row in nodes],
                "elements_connectivity_zero_based":[{"index":e["index"],"nodes":e["nodes"]} for e in elems],
                "base_state_displacement_m_binary64_exact":[point_input(v) for v in base],
                "direction_binary64_exact":[point_input(v) for v in direction],
                "direction_source":"centered_difference_observations[*].full_projected_direction",
                "base_state_source":"observed_data.base_state_displacement_m",
                "geometry_source":["observed_data.nodes","observed_data.elements"],
                "quadrature_reference_coordinate":"HEX8 exact-real ±1/sqrt(3); TET4 one exact rational reference point"
            },
            "number_of_points":len(proof_points),"archive_status":record["status"],
            "accepted_history_digest":verify_history_digest(record),"input_record_sha256":obs_sha,
            "provenance_valid":True,"source_identity_valid":True,"production_branch_linkage_valid":False,
            "production_rounding_budget_valid":False,"points":proof_points}


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--probe-archive",type=Path,default=PROBE_DEFAULT,help="exact probe archive (or QF_WP_E01_PROBE_ARCHIVE)")
    ap.add_argument("--hex8-archive",type=Path,default=HEX8_DEFAULT,help="exact HEX8 archive (or QF_WP_E01_HEX8_ARCHIVE)")
    ap.add_argument("--historical-root",type=Path,default=SNAPSHOT_DEFAULT,help="exact frozen source checkout (or QF_WP_E01_HISTORICAL_ROOT)")
    ap.add_argument("--adapter-repo",type=Path,default=ADAPTER_REPO_DEFAULT,help="exact adapter source repository (or QF_WP_E01_ADAPTER_REPO)")
    ap.add_argument("--output-dir",type=Path,default=OUT_DEFAULT)
    args=ap.parse_args()
    missing=[name for name,value in (("--probe-archive",args.probe_archive),("--hex8-archive",args.hex8_archive),("--historical-root",args.historical_root),("--adapter-repo",args.adapter_repo)) if value is None]
    if missing:
        ap.error(
            "provide "
            + ", ".join(missing)
            + " or their QF_WP_E01_* environment variables; no historical path will be substituted"
        )
    # Verify archived manifests first; preserve the archives read-only.
    probe_files=safe_inventory(args.probe_archive,"archive_integrity.json")
    hex_files=safe_inventory(args.hex8_archive,"artifact_inventory.json","artifacts")
    src=source_identity(args.historical_root)
    probe_result=json.loads((args.probe_archive/"campaign_result.json").read_text(encoding="utf-8"))
    hex_result=json.loads((args.hex8_archive/"campaign_result.json").read_text(encoding="utf-8"))
    adapter_commits=[]
    for result, archive in ((probe_result,args.probe_archive),(hex_result,args.hex8_archive)):
        commit=result["adapter"]["commit"]
        tree=result["adapter"]["tree"]
        observed_tree=subprocess.check_output(["git","rev-parse",f"{commit}^{{tree}}"],cwd=args.adapter_repo,text=True).strip()
        if observed_tree != tree: raise ValueError(f"adapter source tree mismatch for {commit}")
        hashes={}
        for rel, expected in result["adapter_file_sha256"].items():
            content=subprocess.check_output(["git","show",f"{commit}:{rel}"],cwd=args.adapter_repo)
            observed=hashlib.sha256(content).hexdigest()
            if observed != expected: raise ValueError(f"adapter source hash mismatch: {commit}:{rel}")
            hashes[rel]=observed
        adapter_commits.append({"archive":archive.name,"commit":commit,"tree":tree,"file_sha256":hashes})
    for result in (probe_result,hex_result):
        hist=result["historical_snapshot"]
        if hist["commit"]!=SNAPSHOT_COMMIT or hist["tree"]!=SNAPSHOT_TREE: raise ValueError("campaign source identity mismatch")
        for rel, expected in hist.get("historical_file_sha256",{}).items():
            if sha256(args.historical_root/rel) != expected: raise ValueError(f"historical file hash differs: {rel}")
        pins=hist.get("production_pin_sha256",{})
        if hist.get("production_pin_count") != 29 or len(pins) != 29: raise ValueError("production pin count mismatch")
        for rel, expected in pins.items():
            if sha256(args.historical_root/rel) != expected: raise ValueError(f"production pin hash differs: {rel}")
    case_ids=("tet4-perfect-historical-weak-projected","tet4-perfect-mixed-projected","tet4-hardening-historical-weak-projected","tet4-hardening-mixed-projected",
              "hex8-perfect-historical-weak-projected","hex8-perfect-mixed-projected","hex8-hardening-historical-weak-projected","hex8-hardening-mixed-projected")
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    action_inventory=[]
    for cid in case_ids:
        archive=args.probe_archive if cid.startswith("tet4-") else args.hex8_archive
        capture=next(item for item in adapter_commits if item["archive"]==archive.name)
        rec,path=load_case(archive,cid)
        hval=1.5e9 if "hardening" in cid else 0.0
        action=extract_action(rec,path,src,capture,"TET4" if cid.startswith("tet4-") else "HEX8",hval)
        dest=out/f"{cid}.proof_input.json"
        dump(dest,action)
        action_inventory.append({"action_id":cid,"proof_input_path":dest.name,"sha256":sha256(dest),"point_count":action["number_of_points"],"accepted_history_digest":action["accepted_history_digest"],"branch_linkage_valid":False,"production_rounding_budget_valid":False})
    dump(out/"archive_inventory.json",{
        "schema_version":1,"snapshot_commit":src["commit"],"snapshot_tree":src["tree"],
        "archives":[{"path":args.probe_archive.name,"manifest":"archive_integrity.json","manifest_sha256":sha256(args.probe_archive/"archive_integrity.json"),"verified_files":len(probe_files),"campaign_status":probe_result.get("status")},
                     {"path":args.hex8_archive.name,"manifest":"artifact_inventory.json","manifest_sha256":sha256(args.hex8_archive/"artifact_inventory.json"),"verified_files":len(hex_files),"campaign_status":hex_result.get("status")}],
        "historical_source_files":src["source_files"],"capture_source_commits":adapter_commits,"actions":action_inventory,
        "all_eight_raw_input_archives_complete":True,
        **extraction_stage_metadata()
    })
    return 0


if __name__=="__main__": raise SystemExit(main())
