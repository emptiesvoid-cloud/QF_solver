"""Run a bounded, paired TET10 sample from the public volumetric corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.public_volumetric_dataset import _write_qf_case
from scripts.run_public_volumetric_cases import _run_case

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "qualification" / "0_2_6" / "public_volumetric_dataset_manifest.json"
TET4_RESULTS = ROOT / "qualification" / "0_2_6" / "public_volumetric_qf_results.json"
OUTPUT = ROOT / "qualification" / "0_2_6" / "public_volumetric_tet10_results.json"
MARKDOWN = ROOT / "qualification" / "0_2_6" / "public_volumetric_tet10_results.md"
CASE_DIR = ROOT / "qualification" / "0_2_6" / "public_volumetric_tet10_cases"
RESULT_DIR = ROOT / "qualification" / "0_2_6" / "public_volumetric_tet10_runtime"


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


def _read_tet10_mesh(path: Path) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    import gmsh  # type: ignore

    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = [
            (float(coordinates[index]), float(coordinates[index + 1]), float(coordinates[index + 2]))
            for index in range(0, len(coordinates), 3)
        ]
        node_index = {int(tag): index for index, tag in enumerate(node_tags)}
        elements: list[list[int]] = []
        types, _, nodes_by_type = gmsh.model.mesh.getElements(3)
        for element_type, flat_nodes in zip(types, nodes_by_type):
            name, _, _, nodes_per_element, _, _ = gmsh.model.mesh.getElementProperties(element_type)
            if name != "Tetrahedron 10":
                continue
            for offset in range(0, len(flat_nodes), nodes_per_element):
                elements.append([node_index[int(tag)] for tag in flat_nodes[offset : offset + nodes_per_element]])
        if not elements:
            raise ValueError(f"No Tetrahedron 10 elements found in {path}")
        return nodes, elements
    finally:
        gmsh.finalize()


def _sample(records: list[dict[str, Any]], count: int, max_nodes: int) -> list[dict[str, Any]]:
    eligible = sorted(
        (record for record in records if record.get("status") == "PASS" and record.get("tet10_status") == "PASS" and record.get("nodes", 0) <= max_nodes),
        key=lambda record: (int(record.get("nodes", 0)), str(record.get("id", ""))),
    )
    if not eligible:
        return []
    count = min(count, len(eligible))
    indices = sorted({round(index * (len(eligible) - 1) / max(count - 1, 1)) for index in range(count)})
    return [eligible[index] for index in indices]


def _comparison(tet4: dict[str, Any] | None, tet10: dict[str, Any]) -> dict[str, Any]:
    if tet4 is None:
        return {"tet4_status": "NOT_RECORDED"}
    comparison: dict[str, Any] = {"tet4_status": tet4.get("status"), "tet4_run_verdict": tet4.get("run_verdict")}
    for key in ("max_displacement", "reaction_norm", "external_work", "strain_energy"):
        left, right = tet4.get(key), tet10.get(key)
        comparison[f"tet4_{key}"] = left
        comparison[f"tet10_{key}"] = right
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            scale = max(abs(float(left)), abs(float(right)), 1.0e-30)
            comparison[f"relative_difference_{key}"] = abs(float(right) - float(left)) / scale
    comparison["duration_ratio_tet10_over_tet4"] = _ratio(tet10.get("duration_seconds"), tet4.get("duration_seconds"))
    comparison["rss_ratio_tet10_over_tet4"] = _ratio(tet10.get("peak_rss_bytes"), tet4.get("peak_rss_bytes"))
    return comparison


def _ratio(numerator: Any, denominator: Any) -> float | None:
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)) or float(denominator) <= 0.0:
        return None
    return float(numerator) / float(denominator)


def run(count: int, timeout: float, max_nodes: int) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tet4_report = json.loads(TET4_RESULTS.read_text(encoding="utf-8"))
    tet4_by_id = {result["id"]: result for result in tet4_report["results"]}
    selected = _sample(manifest["records"], count, max_nodes)
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in selected:
        nodes, elements = _read_tet10_mesh(ROOT / str(record["mesh_tet10"]))
        case_path = CASE_DIR / f"{record['id']}.json"
        _write_qf_case(nodes, elements, case_path, "TET10")
        case = {"id": record["id"], "source_path": record["source_path"], "mesh_type": "TET10", "qf_case": str(case_path.relative_to(ROOT)).replace("\\", "/")}
        result = _run_case(ROOT, case, timeout, RESULT_DIR)
        result["comparison"] = _comparison(tet4_by_id.get(record["id"]), result)
        result["node_count"] = len(nodes)
        result["element_count"] = len(elements)
        rows.append(result)
        case_path.unlink(missing_ok=True)
    counts = {status: sum(row.get("status") == status for row in rows) for status in ("PASS", "FAIL", "TIMEOUT")}
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": _sha256(MANIFEST),
        "qf_source_sha": _git("rev-parse", "HEAD"),
        "qf_worktree_dirty": bool(_git("status", "--porcelain")),
        "requested_cases": count,
        "selected_cases": len(rows),
        "selection_max_nodes": max_nodes,
        "timeout_seconds": timeout,
        "status_counts": counts,
        "results": rows,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    _write_markdown(report)
    print(json.dumps({"selected_cases": len(rows), "status_counts": counts}, indent=2))
    return report


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Public Volumetric TET10 Sample",
        "",
        "This is a bounded paired TET10/TET4 execution sample. It is not a TET10 qualification campaign.",
        "",
        f"- QF source SHA: `{report['qf_source_sha']}`",
        f"- Worktree dirty at capture: `{report['qf_worktree_dirty']}`",
        f"- Selected cases: `{report['selected_cases']}` of `{report['requested_cases']}` requested",
        f"- Selection limit: `{report['selection_max_nodes']}` nodes",
        f"- Status counts: `{report['status_counts']}`",
        "",
        "| Case | TET4 status | TET10 status | TET10 nodes | TET10 elements | displacement relative difference | duration ratio | RSS ratio |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["results"]:
        comparison = row.get("comparison", {})
        lines.append(
            f"| {row['id']} | {comparison.get('tet4_status')} | {row.get('status')} | {row.get('node_count')} | {row.get('element_count')} | {comparison.get('relative_difference_max_displacement')} | {comparison.get('duration_ratio_tet10_over_tet4')} | {comparison.get('rss_ratio_tet10_over_tet4')} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The paired comparison uses the same neutral support and 1,000 N loading convention, while changing only the element order. Reactions, external work and strain energy are retained when the QF result is available. A failed or timed-out TET10 case is evidence about the current robustness envelope, not evidence of a solver defect by itself.",
        "",
        "Large TET10 meshes above the selection limit were intentionally not executed in this bounded run to avoid an uncontrolled memory experiment. HEX8/HEX20 are absent from this corpus and are not inferred.",
    ])
    MARKDOWN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-nodes", type=int, default=10000)
    args = parser.parse_args(argv)
    run(args.count, args.timeout, args.max_nodes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
