"""Acquire and qualify public STEP solids from the FreeCAD parts library."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com/FreeCAD/FreeCAD-library"
REPOSITORY = "FreeCAD/FreeCAD-library"
BRANCH = "master"
LICENSE = "Creative Commons Attribution 3.0 Unported"
LICENSE_URL = "https://creativecommons.org/licenses/by/3.0/"
DEFAULT_CACHE = ROOT / "datasets" / "public_volumetric"
DEFAULT_MANIFEST = ROOT / "qualification" / "0_2_6" / "public_volumetric_dataset_manifest.json"
GMSH_TIMEOUT_SECONDS = 45
EXCLUDED_TERMS = (
    "aircraft", "aerospace", "airplane", "helicopter", "jet engine", "rocket",
    "turbine", "compressor", "turbomach", "casing", "engine", "turbojet",
    "propeller", "fuselage", "airframe", "rotorcraft", "crankshaft", "piston",
    "spark plug", "exhaust", "intake manifold", "motor", "motors",
)


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "qf-solver-volumetric-audit"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *arguments], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _worktree_dirty_except(path: Path) -> bool:
    excluded = path.relative_to(ROOT).as_posix()
    changed_paths: list[str] = []
    for arguments in (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        output = _git(*arguments)
        if output is None:
            return True
        changed_paths.extend(output.splitlines())
    return any(changed != excluded for changed in changed_paths)


def fetch_tree() -> tuple[str, list[dict[str, Any]]]:
    ref = _get_json(f"{API}/repos/{REPOSITORY}/git/ref/heads/{BRANCH}")
    commit = str(ref["object"]["sha"])
    tree = _get_json(f"{API}/repos/{REPOSITORY}/git/trees/{commit}?recursive=1")
    return commit, [item for item in tree["tree"] if item.get("type") == "blob"]


def _search_text(path: str) -> str:
    return path.casefold()


def select_models(tree: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in sorted(tree, key=lambda row: str(row.get("path", ""))):
        path = str(item.get("path", ""))
        text = _search_text(path)
        if not text.endswith((".step", ".stp")):
            continue
        reason = next((f"excluded-domain keyword: {term}" for term in EXCLUDED_TERMS if re.search(rf"\b{re.escape(term)}\b", text)), None)
        if reason:
            rejected.append({"path": path, "status": "REJECTED", "reason": reason})
            continue
        if not item.get("size"):
            rejected.append({"path": path, "status": "REJECTED", "reason": "empty STEP file"})
            continue
        parts = path.split("/")
        bucket = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        buckets[bucket].append(item)
    while len(selected) < limit and buckets:
        for bucket in sorted(tuple(buckets)):
            if not buckets[bucket]:
                del buckets[bucket]
                continue
            selected.append(buckets[bucket].pop(0))
            if len(selected) >= limit:
                break
    return selected, rejected


def _write_qf_case(nodes: list[tuple[float, float, float]], elements: list[list[int]], destination: Path) -> None:
    x_values = [node[0] for node in nodes]
    minimum, maximum = min(x_values), max(x_values)
    tolerance = max((maximum - minimum) * 1.0e-6, 1.0e-12)
    if maximum <= minimum + tolerance:
        raise ValueError("volume mesh has no distinct x-extreme nodes")
    left = [index for index, value in enumerate(x_values) if value <= minimum + tolerance]
    right = [index for index, value in enumerate(x_values) if value >= maximum - tolerance]
    if not left or not right:
        raise ValueError("volume mesh has no usable x-extreme nodes")
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in left]
    fixed.append({"node": right[0], "dofs": ["UY", "UZ"]})
    loads = [{"node": index, "dof": "UX", "value": 1000.0 / len(right)} for index in right]
    payload = {
        "analysis": {"type": "linear_static", "method": "direct"},
        "nodes": [list(node) for node in nodes],
        "elements": [{"type": "TET4", "nodes": element, "material": "steel"} for element in elements],
        "materials": {"steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}},
        "fixed_dofs": fixed,
        "loads": loads,
    }
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _tet_topology(elements: list[list[int]], node_count: int) -> tuple[int, int]:
    parent = list(range(node_count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    repeated = 0
    for element in elements:
        if len(element) != len(set(element)):
            repeated += 1
        first = element[0]
        for other in element[1:]:
            left, right = find(first), find(other)
            if left != right:
                parent[left] = right
    used = {node for element in elements for node in element}
    return repeated, len({find(node) for node in used})


def _mesh_step(step: Path, mesh4: Path, mesh10: Path, qf_case: Path) -> dict[str, Any]:
    import gmsh  # type: ignore

    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(step.stem)
        gmsh.merge(str(step))
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if not volumes:
            raise RuntimeError("STEP import produced no volume entities")
        gmsh.model.mesh.generate(3)
        # STEP assemblies can retain coincident nodes on touching entities.
        # Remove only exact mesh duplicates before exporting the QF case.
        gmsh.model.mesh.removeDuplicateNodes()
        nodes_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = [
            (float(coordinates[i]), float(coordinates[i + 1]), float(coordinates[i + 2]))
            for i in range(0, len(coordinates), 3)
        ]
        node_index = {int(tag): index for index, tag in enumerate(nodes_tags)}
        types, tags_by_type, nodes_by_type = gmsh.model.mesh.getElements(3)
        tet4: list[list[int]] = []
        counts: Counter[str] = Counter()
        qualities: list[float] = []
        for element_type, tags, flat_nodes in zip(types, tags_by_type, nodes_by_type):
            name, _, _, nodes_per_element, _, _ = gmsh.model.mesh.getElementProperties(element_type)
            counts[name] += len(tags)
            if name == "Tetrahedron 4":
                for offset in range(0, len(flat_nodes), nodes_per_element):
                    tet4.append([node_index[int(tag)] for tag in flat_nodes[offset : offset + nodes_per_element]])
                qualities.extend(float(value) for value in gmsh.model.mesh.getElementQualities(tags))
        if not tet4:
            raise RuntimeError("Gmsh produced no TET4 elements")
        mesh10.unlink(missing_ok=True)
        qf_case.unlink(missing_ok=True)
        gmsh.write(str(mesh4))
        repeated, components = _tet_topology(tet4, len(nodes))
        if repeated:
            return {
                "category": "REJECTED",
                "status": "REJECTED",
                "reason": f"{repeated} TET4 elements have repeated node connectivity",
                "component_count": components,
                "tet4_elements": len(tet4),
            }
        if components > 1:
            return {
                "category": "MESH_ONLY",
                "status": "MESH_ONLY",
                "reason": f"mesh contains {components} disconnected components; neutral single-domain BC not applicable",
                "component_count": components,
                "nodes": len(nodes),
                "tet4_elements": len(tet4),
                "quality_min": min(qualities) if qualities else None,
                "quality_mean": sum(qualities) / len(qualities) if qualities else None,
                "quality_status": "POSITIVE" if qualities and min(qualities) > 0.0 else "CHECK_REQUIRED",
            }
        second_counts: Counter[str] = Counter()
        tet10_error = None
        try:
            gmsh.model.mesh.setOrder(2)
            second_types, second_tags, _ = gmsh.model.mesh.getElements(3)
            second_counts = Counter({
                gmsh.model.mesh.getElementProperties(element_type)[0]: len(tags)
                for element_type, tags in zip(second_types, second_tags)
            })
            gmsh.write(str(mesh10))
        except Exception as exc:
            # A valid first-order mesh remains useful when Gmsh cannot elevate
            # a particular STEP topology to second order.
            tet10_error = f"{type(exc).__name__}: {exc}"
        _write_qf_case(nodes, tet4, qf_case)
        finite_quality = [value for value in qualities if value > 0.0]
        return {
            "category": "TET4_READY",
            "mesh_type": "TET4+TET10" if second_counts.get("Tetrahedron 10", 0) else "TET4",
            "volumes": len(volumes),
            "component_count": components,
            "nodes": len(nodes),
            "tet4_elements": counts.get("Tetrahedron 4", 0),
            "tet10_elements": second_counts.get("Tetrahedron 10", 0),
            "tet10_status": "PASS" if second_counts.get("Tetrahedron 10", 0) else "MESH_FAILED",
            "tet10_reason": tet10_error,
            "hex8_elements": counts.get("Hexahedron 8", 0),
            "hex20_elements": counts.get("Hexahedron 20", 0),
            "quality_min": min(finite_quality) if finite_quality else None,
            "quality_mean": sum(finite_quality) / len(finite_quality) if finite_quality else None,
            "quality_status": "POSITIVE" if finite_quality and min(finite_quality) > 0.0 else "CHECK_REQUIRED",
            "status": "PASS",
        }
    finally:
        gmsh.finalize()


def _mesh_isolated(step: Path, mesh4: Path, mesh10: Path, qf_case: Path) -> dict[str, Any]:
    result_path = mesh4.with_suffix(".result.json")
    command = [sys.executable, str(Path(__file__).resolve()), "--mesh-one", str(step), str(mesh4), str(mesh10), str(qf_case), str(result_path)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=GMSH_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return {"category": "MESH_ONLY", "status": "MESH_TIMEOUT", "reason": f"Gmsh exceeded {GMSH_TIMEOUT_SECONDS} seconds"}
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        return {"category": "MESH_ONLY", "status": "MESH_FAILED", "reason": detail[-1] if detail else f"worker exit {completed.returncode}"}
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        result_path.unlink(missing_ok=True)


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "qf-solver-volumetric-audit"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)


def process(limit: int, cache: Path, manifest_path: Path) -> dict[str, Any]:
    commit, tree = fetch_tree()
    selected, rejected = select_models(tree, limit)
    cache.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        path = str(item["path"])
        identifier = f"FCL-{index:04d}"
        model_dir = cache / identifier
        model_dir.mkdir(parents=True, exist_ok=True)
        step = model_dir / Path(path).name
        encoded = urllib.parse.quote(path, safe="/")
        record: dict[str, Any] = {
            "id": identifier,
            "dataset": "FreeCAD-library",
            "repository": REPOSITORY,
            "source_commit": commit,
            "source_path": path,
            "source_url": f"https://github.com/{REPOSITORY}/blob/{commit}/{encoded}",
            "download_url": f"{RAW}/{commit}/{encoded}",
            "source_blob_sha": item.get("sha"),
            "author": "respective FreeCAD-library contributor(s); see pinned source history",
            "license": LICENSE,
            "license_url": LICENSE_URL,
            "original_format": "STEP",
            "source_filesize": item.get("size"),
            "transformations": [],
        }
        try:
            _download(record["download_url"], step)
            record["original_sha256"] = _sha256(step)
            result = _mesh_isolated(step, model_dir / "mesh_tet4.msh", model_dir / "mesh_tet10.msh", model_dir / "qf_case.json")
            record.update(result)
            record["transformations"].append("native STEP imported by Gmsh OCC")
            if result.get("status") in {"PASS", "MESH_ONLY"}:
                record["mesh_tet4"] = str((model_dir / "mesh_tet4.msh").relative_to(ROOT)).replace("\\", "/")
                if (model_dir / "mesh_tet10.msh").exists():
                    record["mesh_tet10"] = str((model_dir / "mesh_tet10.msh").relative_to(ROOT)).replace("\\", "/")
                if (model_dir / "qf_case.json").exists():
                    record["qf_case"] = str((model_dir / "qf_case.json").relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            record.update({"category": "REJECTED", "status": "REJECTED", "reason": f"{type(exc).__name__}: {exc}"})
        records.append(record)
        print(f"{identifier} {record['status']} {path}")
    records.extend(rejected)
    summary = Counter(record.get("status") for record in records)
    categories = Counter(record.get("category") for record in records if record.get("status") == "PASS")
    manifest = {
        "schema_version": 1,
        "manifest_id": "QF-PUBLIC-VOLUMETRIC-DATASET-026-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "qf_source_sha": _git("rev-parse", "HEAD"),
        "qf_worktree_dirty": _worktree_dirty_except(manifest_path),
        "source": {"repository": REPOSITORY, "branch": BRANCH, "commit": commit, "license": LICENSE, "license_url": LICENSE_URL},
        "selection": {"requested": limit, "step_candidates": sum(str(row.get("path", "")).casefold().endswith((".step", ".stp")) for row in tree), "selected": len(selected)},
        "policy": {"excluded_terms": list(EXCLUDED_TERMS), "raw_cache": "local and ignored; manifest is the tracked index"},
        "records": records,
        "summary": {"status_counts": dict(summary), "accepted_categories": dict(categories), "downloaded": sum(record.get("original_sha256") is not None for record in records if isinstance(record.get("original_sha256"), str))},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-one", nargs=5, metavar=("STEP", "TET4", "TET10", "QF", "RESULT"), help=argparse.SUPPRESS)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    if args.mesh_one:
        result = _mesh_step(Path(args.mesh_one[0]), Path(args.mesh_one[1]), Path(args.mesh_one[2]), Path(args.mesh_one[3]))
        Path(args.mesh_one[4]).write_text(json.dumps(result), encoding="utf-8")
        return 0
    cache = args.cache if args.cache.is_absolute() else ROOT / args.cache
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    process(args.limit, cache, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
