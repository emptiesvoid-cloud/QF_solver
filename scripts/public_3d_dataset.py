"""Acquire and qualify a small, reproducible public 3D geometry corpus.

The default source is the Google Scanned Objects collection exposed by the
official Open Robotics Gazebo Fuel API. Raw archives and generated meshes are
kept outside normal source history; the JSON manifest is the tracked record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API = "https://fuel.gazebosim.org/1.0"
OWNER = "GoogleResearch"
QUERY = "collections:Scanned Objects"
LICENSE_NAME = "Creative Commons Attribution 4.0 International"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
DEFAULT_CACHE = ROOT / "datasets" / "public_3d"
DEFAULT_MANIFEST = ROOT / "qualification" / "0_2_6" / "public_3d_dataset_manifest.json"
GMSH_TIMEOUT_SECONDS = 15
VOLUME_FACE_LIMIT = 500
EXCLUDED_TERMS = (
    "aircraft", "aerospace", "airplane", "helicopter", "jet engine", "rocket",
    "turbine", "compressor", "turbomach", "casing", "engine", "turbojet",
    "propeller", "fuselage", "airframe", "rotorcraft",
)


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "qf-solver-public-3d/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_catalog() -> list[dict[str, Any]]:
    """Fetch all pages from the official Fuel model catalog."""
    models: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"page": page, "per_page": 100, "q": QUERY})
        rows = _get_json(f"{API}/models?{query}")
        if not rows:
            break
        models.extend(row for row in rows if isinstance(row, dict))
        page += 1
    return models


def _search_text(model: dict[str, Any]) -> str:
    values = [model.get("name", ""), model.get("description", ""), *model.get("categories", [])]
    return " ".join(str(value) for value in values).casefold()


def _eligible(model: dict[str, Any]) -> tuple[bool, str]:
    if model.get("license_name") != LICENSE_NAME:
        return False, "license is not the explicitly accepted CC BY 4.0 license"
    text = _search_text(model)
    for term in EXCLUDED_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return False, f"excluded-domain keyword: {term}"
    return True, ""


def select_models(models: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select deterministically by category round-robin for shape diversity."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for model in sorted(models, key=lambda item: str(item.get("name", ""))):
        ok, reason = _eligible(model)
        if not ok:
            rejected.append({"name": model.get("name"), "status": "REJECTED", "reason": reason})
            continue
        categories = sorted(str(category) for category in model.get("categories", []) if category)
        bucket = categories[0] if categories else "Uncategorized"
        buckets[bucket].append(model)
    while len(accepted) < limit and buckets:
        for bucket in sorted(tuple(buckets)):
            if not buckets[bucket]:
                del buckets[bucket]
                continue
            accepted.append(buckets[bucket].pop(0))
            if len(accepted) >= limit:
                break
    return accepted, rejected


def _parse_obj(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v" and len(fields) >= 4:
            vertices.append((float(fields[1]), float(fields[2]), float(fields[3])))
        elif fields[0] == "f" and len(fields) >= 4:
            indices = []
            for field in fields[1:]:
                value = int(field.split("/", 1)[0])
                indices.append(value - 1 if value > 0 else len(vertices) + value)
            for index in range(1, len(indices) - 1):
                faces.append((indices[0], indices[index], indices[index + 1]))
    if not vertices or not faces:
        raise ValueError("OBJ has no usable vertices/faces")
    if any(index < 0 or index >= len(vertices) for face in faces for index in face):
        raise ValueError("OBJ face references an invalid vertex")
    return vertices, faces


def _write_ascii_stl(path: Path, name: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]]) -> None:
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(f"solid {name}\n")
        for first, second, third in faces:
            a, b, c = vertices[first], vertices[second], vertices[third]
            ab = tuple(b[index] - a[index] for index in range(3))
            ac = tuple(c[index] - a[index] for index in range(3))
            normal = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
            length = math.sqrt(sum(value * value for value in normal)) or 1.0
            unit = tuple(value / length for value in normal)
            stream.write(f"  facet normal {unit[0]:.17g} {unit[1]:.17g} {unit[2]:.17g}\n    outer loop\n")
            for point in (a, b, c):
                stream.write(f"      vertex {point[0]:.17g} {point[1]:.17g} {point[2]:.17g}\n")
            stream.write("    endloop\n  endfacet\n")
        stream.write(f"endsolid {name}\n")


def _qf_case(nodes: list[tuple[float, float, float]], elements: list[list[int]], destination: Path) -> None:
    x_values = [node[0] for node in nodes]
    minimum, maximum = min(x_values), max(x_values)
    tolerance = max((maximum - minimum) * 1.0e-6, 1.0e-12)
    left = [index for index, value in enumerate(x_values) if value <= minimum + tolerance]
    right = [index for index, value in enumerate(x_values) if value >= maximum - tolerance]
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in left]
    if right:
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


def _manifest_path(path: Path) -> str:
    """Prefer repository-relative evidence paths, while supporting temp caches."""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _is_closed_surface(faces: list[tuple[int, int, int]]) -> bool:
    """Use OBJ topology to avoid expensive Gmsh classification for open shells."""
    edges: Counter[tuple[int, int]] = Counter()
    for first, second, third in faces:
        if len({first, second, third}) != 3:
            return False
        for left, right in ((first, second), (second, third), (third, first)):
            edges[tuple(sorted((left, right)))] += 1
    return bool(edges) and all(count == 2 for count in edges.values())


def _mesh_stl(stl_path: Path, msh_path: Path, qf_path: Path, volume_candidate: bool) -> dict[str, Any]:
    """Create a Gmsh surface mesh, with bounded volume attempts."""
    try:
        import gmsh  # type: ignore
    except ImportError as exc:
        raise RuntimeError("gmsh is required for --mesh") from exc
    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(stl_path.stem)
        gmsh.merge(str(stl_path))

        def load_surface_model() -> None:
            """Reload the STL without classified geometry for open shells."""
            gmsh.model.remove()
            gmsh.model.add(f"{stl_path.stem}_surface")
            gmsh.merge(str(stl_path))

        try:
            if not volume_candidate:
                load_surface_model()
                dimension = 2
            else:
                gmsh.model.mesh.classifySurfaces(math.pi / 3.0, True, True, math.pi / 3.0)
                gmsh.model.mesh.createGeometry()
                if gmsh.model.getEntities(3):
                    dimension = 3
                else:
                    load_surface_model()
                    dimension = 2
        except Exception:
            load_surface_model()
            dimension = 2
        gmsh.model.mesh.generate(dimension)
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = [(float(coordinates[index]), float(coordinates[index + 1]), float(coordinates[index + 2])) for index in range(0, len(coordinates), 3)]
        node_index = {int(tag): index for index, tag in enumerate(node_tags)}
        types, element_tags, element_nodes = gmsh.model.mesh.getElements(dimension)
        elements: list[list[int]] = []
        quality_values: list[float] = []
        for element_type, tags, flat_nodes in zip(types, element_tags, element_nodes):
            properties = gmsh.model.mesh.getElementProperties(element_type)
            name, nodes_per_element = properties[0], int(properties[3])
            expected_name = {2: "Triangle", 3: "Tetrahedron"}[dimension]
            if not name.startswith(expected_name):
                continue
            for offset in range(0, len(flat_nodes), nodes_per_element):
                elements.append([node_index[int(tag)] for tag in flat_nodes[offset : offset + nodes_per_element]][:4])
            quality_values.extend(float(value) for value in gmsh.model.mesh.getElementQualities(tags))
        if not elements:
            raise RuntimeError("Gmsh produced no usable surface or volume elements")
        if dimension == 3:
            gmsh.model.mesh.setOrder(1)
        gmsh.write(str(msh_path))
        finite_quality = [value for value in quality_values if math.isfinite(value)]
        if dimension == 3:
            _qf_case(nodes, elements, qf_path)
        quality_status = "POSITIVE" if finite_quality and min(finite_quality) > 0.0 else "CHECK_REQUIRED"
        return {
            "category": "SOLID_TET" if dimension == 3 else "SHELL",
            "mesh_type": "TET4" if dimension == 3 else "TRI3_SURFACE",
            "nodes": len(nodes),
            "elements": len(elements),
            "quality_min": min(finite_quality) if finite_quality else None,
            "quality_mean": sum(finite_quality) / len(finite_quality) if finite_quality else None,
            "quality_status": quality_status,
            "status": "PASS" if quality_status == "POSITIVE" else "MESH_QUALITY_REVIEW",
        }
    finally:
        gmsh.finalize()


def _mesh_stl_isolated(stl_path: Path, msh_path: Path, qf_path: Path, volume_candidate: bool) -> dict[str, Any]:
    """Run one Gmsh attempt in a killable child process."""
    result_path = msh_path.with_suffix(".result.json")
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--mesh-one",
        str(stl_path),
        str(msh_path),
        str(qf_path),
        str(volume_candidate).lower(),
        str(result_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=GMSH_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return {
            "category": "UNMESHED",
            "status": "MESH_TIMEOUT",
            "reason": f"Gmsh mesh attempt exceeded {GMSH_TIMEOUT_SECONDS} seconds",
        }
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        reason = detail[-1] if detail else f"Gmsh worker exited with code {completed.returncode}"
        return {"category": "UNMESHED", "status": "MESH_FAILED", "reason": reason}
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        result_path.unlink(missing_ok=True)


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "qf-solver-public-3d/0.1"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)


def process(limit: int, cache: Path, manifest_path: Path, mesh: bool) -> dict[str, Any]:
    models = fetch_catalog()
    selected, rejected = select_models(models, limit)
    cache.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for index, model in enumerate(selected, start=1):
        name = str(model["name"])
        identifier = f"GSO-{index:04d}"
        model_dir = cache / identifier
        model_dir.mkdir(parents=True, exist_ok=True)
        archive = model_dir / "source.zip"
        owner = str(model.get("owner") or OWNER)
        encoded_name = urllib.parse.quote(name, safe="")
        record: dict[str, Any] = {
            "id": identifier,
            "dataset": "Gazebo Fuel Scanned Objects collection",
            "source_owner": owner,
            "source_url": f"{API}/{owner}/models/{encoded_name}",
            "download_url": f"{API}/{owner}/models/{encoded_name}.zip",
            "author": owner,
            "license": LICENSE_NAME,
            "license_url": LICENSE_URL,
            "original_format": "OBJ in Gazebo Fuel ZIP",
            "model_name": name,
            "description": model.get("description", ""),
            "source_categories": model.get("categories", []),
            "source_filesize": model.get("filesize"),
            "transformations": [],
        }
        try:
            if not archive.exists():
                _download(record["download_url"], archive)
            record["original_archive_sha256"] = _sha256(archive)
            with zipfile.ZipFile(archive) as bundle:
                members = [member for member in bundle.namelist() if member.lower().endswith(".obj")]
                if not members:
                    raise RuntimeError("archive contains no OBJ mesh")
                obj_member = sorted(members)[0]
                bundle.extract(obj_member, model_dir)
            obj = model_dir / obj_member
            record["original_mesh_sha256"] = _sha256(obj)
            vertices, faces = _parse_obj(obj)
            stl = model_dir / "surface.stl"
            _write_ascii_stl(stl, identifier, vertices, faces)
            record["transformations"].append("OBJ triangles converted to ASCII STL")
            record["topology_closed"] = _is_closed_surface(faces)
            record["volume_candidate"] = record["topology_closed"] and len(faces) <= VOLUME_FACE_LIMIT
            if mesh:
                result = _mesh_stl_isolated(
                    stl,
                    model_dir / "mesh.msh",
                    model_dir / "qf_case.json",
                    record["volume_candidate"],
                )
                record.update(result)
                record["transformations"].append(
                    "closed surface meshed with Gmsh first-order tetrahedra"
                    if result["category"] == "SOLID_TET"
                    else "surface meshed with Gmsh first-order triangles"
                )
                if result["category"] == "SOLID_TET":
                    record["qf_case"] = _manifest_path(model_dir / "qf_case.json")
            else:
                record.update({"category": "SHELL", "status": "DOWNLOADED", "vertices": len(vertices), "triangles": len(faces)})
        except Exception as exc:  # Each model is independently auditable.
            record.update({"category": "REJECTED", "status": "REJECTED", "reason": f"{type(exc).__name__}: {exc}"})
        records.append(record)
        print(f"{identifier} {record['status']} {name}")
    records.extend(rejected)
    summary = Counter(record.get("status") for record in records)
    categories = Counter(record.get("category") for record in records if record.get("status") == "PASS")
    manifest = {
        "schema_version": 1,
        "manifest_id": "QF-PUBLIC-3D-DATASET-026-001",
        "source": {"dataset": "Gazebo Fuel Scanned Objects collection", "api": f"{API}/models", "query": QUERY},
        "pipeline": {
            "script": "scripts/public_3d_dataset.py",
            "gmsh_requested": mesh,
            "gmsh_timeout_seconds": GMSH_TIMEOUT_SECONDS,
            "volume_face_limit": VOLUME_FACE_LIMIT,
            "raw_cache_policy": "local reproducible cache; not tracked",
        },
        "selection": {"requested": limit, "catalog_found": len(models), "selected": len(selected)},
        "license_policy": {"accepted": LICENSE_NAME, "license_url": LICENSE_URL, "excluded_terms": list(EXCLUDED_TERMS)},
        "records": records,
        "summary": {"status_counts": dict(summary), "accepted_categories": dict(categories), "models_downloaded": sum(record.get("status") != "REJECTED" for record in records)},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-one", nargs=5, metavar=("STL", "MSH", "QF", "CLOSED", "RESULT"), help=argparse.SUPPRESS)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mesh", action="store_true", help="convert and mesh each downloaded OBJ with Gmsh")
    args = parser.parse_args(argv)
    if args.mesh_one:
        result = _mesh_stl(Path(args.mesh_one[0]), Path(args.mesh_one[1]), Path(args.mesh_one[2]), args.mesh_one[3] == "true")
        Path(args.mesh_one[4]).write_text(json.dumps(result), encoding="utf-8")
        return 0
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    cache = args.cache if args.cache.is_absolute() else ROOT / args.cache
    process(args.limit, cache, manifest, args.mesh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
