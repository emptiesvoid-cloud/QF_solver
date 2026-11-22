
"""Prepare and record a single, source-bound TET10 G08 input."""
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def scope_for(scope_id):
    policy = json.loads((HERE / "policy.json").read_text(encoding="utf-8"))
    return next(scope for scope in policy["scopes"] if scope["id"] == scope_id)


def topology(nodes, elements, tet4, tet10):
    owners = defaultdict(list)
    edges, mids = defaultdict(set), defaultdict(set)
    volumes, jacobians = [], []
    for index, element in enumerate(elements):
        corners = element[:4]
        volumes.append(tet4.signed_volume(nodes[corners]))
        jacobians.extend(tet10.jacobian_determinants(nodes[element]))
        for (i, j), mid in zip(EDGES, element[4:], strict=True):
            edge = tuple(sorted((corners[i], corners[j])))
            if not np.allclose(nodes[mid], nodes[list(edge)].mean(axis=0), rtol=0, atol=1e-13):
                raise ValueError("TET10 middle node geometry")
            edges[edge].add(mid)
            mids[mid].add(edge)
        for face in combinations(sorted(corners), 3):
            owners[face].append(index)
    low, high = nodes.min(axis=0), nodes.max(axis=0)
    adjacent = [set() for _ in elements]
    unmatched = 0
    for face, cells in owners.items():
        triangle = nodes[list(face)]
        if len(cells) == 1:
            unmatched += int(not np.any(np.all(triangle == low, axis=0) | np.all(triangle == high, axis=0)))
        elif len(cells) == 2:
            a, b = cells
            adjacent[a].add(b)
            adjacent[b].add(a)
        else:
            raise ValueError("nonmanifold triangle")
    unseen = set(range(len(elements)))
    components = 0
    while unseen:
        components += 1
        todo = [unseen.pop()]
        while todo:
            new = adjacent[todo.pop()] & unseen
            unseen.difference_update(new)
            todo.extend(new)
    if any(len(ids) != 1 for ids in edges.values()):
        raise ValueError("inconsistent middle node on a shared edge")
    return {
        "open_faces": unmatched, "components": components,
        "aliases": sum(len(value) > 1 for value in mids.values()),
        "min_volume": min(volumes), "volume": math.fsum(volumes),
        "min_sampled_jacobian": float(min(jacobians)),
    }


def prepare(root, scope_id):
    """This function constructs a model and performs no structural solve."""
    scope = scope_for(scope_id)
    root = Path(root).resolve(strict=True)
    source = git(root, "rev-parse", "HEAD")
    if source != scope["source"] or git(root, "status", "--porcelain"):
        raise ValueError("unexpected or dirty science source")
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "src"))
    import solveur
    from solveur.elements.solid.tet4 import Tet4Element
    from solveur.elements.solid.tet10 import Tet10Element
    from solveur.compatibility.preflight import preflight_model

    g08 = importlib.import_module("scripts.run_g08_high_order_analytical")
    if (Path(solveur.__file__).resolve() != root / "src/solveur/__init__.py"
            or Path(g08.__file__).resolve() != root / "scripts/run_g08_high_order_analytical.py"):
        raise ValueError("unexpected Python import origin")
    model, _ = g08._model("TET10", 2, 2)
    nodes = np.asarray(model.nodes)
    elements = [list(e.nodes) for e in model.elements]
    mesh = digest([nodes.tolist(), elements])
    mesh_stats = topology(nodes, elements, Tet4Element, Tet10Element)
    fixed = sorted((nodes[entry.node].tolist(), sorted(entry.dofs)) for entry in model.fixed_dofs)
    loads = sorted((nodes[entry.node].tolist(), entry.dof, float(entry.value)) for entry in model.loads)
    positions = [[y / 8, z / 8] for y in range(5) for z in range(5)]
    if (mesh != scope["mesh"] or len(nodes) != scope["nodes"] or len(elements) != scope["elements"]
            or any(mesh_stats[key] != scope[key] for key in ("open_faces", "components", "aliases"))
            or mesh_stats["min_volume"] <= 0 or mesh_stats["min_sampled_jacobian"] <= 0
            or not math.isclose(mesh_stats["volume"], 1, abs_tol=1e-12)
            or nodes.min(axis=0).tolist() != [0, 0, 0] or nodes.max(axis=0).tolist() != [4, .5, .5]
            or fixed != [([0, *yz], ["UX", "UY", "UZ"]) for yz in positions]
            or loads != [([4, *yz], "UX", -1/25) for yz in positions]
            or model.materials != {"solid": {"type": "isotropic_3d", "E": 1e6, "nu": .3}}):
        raise ValueError("input contract mismatch")
    import scipy

    compatibility = preflight_model(model)
    receipt = {
        "scope": scope_id, "source": source, "source_tree": git(root, "rev-parse", "HEAD^{tree}"),
        "solver_origin": str(Path(solveur.__file__).resolve()),
        "solver_tree": git(root, "rev-parse", "HEAD:src"),
        "generator_blob": git(root, "rev-parse", "HEAD:scripts/run_g08_high_order_analytical.py"),
        "mesh_sha256": mesh, "stats": mesh_stats,
        "inputs_sha256": digest([mesh, model.materials, vars(model.analysis), fixed, loads]),
        "boundary_sha256": digest([fixed, loads]),
        "common_sha256": digest([model.materials, vars(model.analysis), fixed, loads]),
        "nodes": len(nodes), "elements": len(elements), "free_dofs": 3 * (len(nodes) - len(fixed)),
        "resultant_ux": math.fsum(row[2] for row in loads),
        "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
        "compatibility": str(getattr(compatibility.status, "value", compatibility.status)),
        "bodies_executed": False,
    }
    return model, receipt


def solve_one(model, receipt, output, solve):
    """One case with the solver's default policy. Called only by an authorized runner."""
    result = solve(model)
    diagnostics = result.solver
    payload = {
        "scope": receipt["scope"], "source": receipt["source"], "inputs_sha256": receipt["inputs_sha256"],
        "solver_status": result.status, "diagnostics": diagnostics, "mode_rank": "NOT_ESTABLISHED",
    }
    if result.status == "PASS":
        factor = float(diagnostics["critical_factor"])
        residual = float(diagnostics["critical_mode_residual_relative"])
        mode = np.asarray(result.displacements, dtype=float)
        if (not math.isfinite(factor) or factor <= 0 or not math.isfinite(residual) or residual < 0
                or mode.size != receipt["nodes"] * 3 or not np.isfinite(mode).all()):
            raise ValueError("invalid eigenpair data")
        load = receipt["resultant_ux"] * factor
        payload.update(factor=factor, signed_load=load, magnitude=abs(load), residual=residual,
                       euler_relative_error=abs(abs(load) - 803.1904623282354) / 803.1904623282354)
        np.save(output / "mode.npy", mode, allow_pickle=False)
        payload["mode_sha256"] = sha256((output / "mode.npy").read_bytes()).hexdigest()
    (output / "result.json").write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    return payload


if __name__ == "__main__":
    _, receipt = prepare(sys.argv[1], sys.argv[2])
    print(json.dumps(receipt, allow_nan=False))
