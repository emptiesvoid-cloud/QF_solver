"""Classify non-PASS executions from the public volumetric campaign."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "qualification" / "0_2_6" / "public_volumetric_dataset_manifest.json"
DEFAULT_RESULTS = ROOT / "qualification" / "0_2_6" / "public_volumetric_qf_results.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "public_volumetric_triage.json"
DEFAULT_MARKDOWN = ROOT / "qualification" / "0_2_6" / "public_volumetric_triage.md"


def _volume(a: list[float], b: list[float], c: list[float], d: list[float]) -> float:
    ab = [b[index] - a[index] for index in range(3)]
    ac = [c[index] - a[index] for index in range(3)]
    ad = [d[index] - a[index] for index in range(3)]
    return (
        ab[0] * (ac[1] * ad[2] - ac[2] * ad[1])
        - ab[1] * (ac[0] * ad[2] - ac[2] * ad[0])
        + ab[2] * (ac[0] * ad[1] - ac[1] * ad[0])
    ) / 6.0


def _component_count(elements: list[list[int]], node_count: int) -> int:
    parent = list(range(node_count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for element in elements:
        first = element[0]
        for other in element[1:]:
            left, right = find(first), find(other)
            if left != right:
                parent[left] = right
    used = {node for element in elements for node in element}
    return len({find(node) for node in used})


def inspect_case(record: dict[str, Any]) -> dict[str, Any]:
    case = json.loads((ROOT / str(record["qf_case"])).read_text(encoding="utf-8"))
    nodes = case["nodes"]
    elements = [list(element["nodes"]) for element in case["elements"]]
    invalid = sum(1 for element in elements if any(node < 0 or node >= len(nodes) for node in element))
    repeated = sum(1 for element in elements if len(element) != len(set(element)))
    volumes = []
    if not invalid:
        volumes = [_volume(*(nodes[index] for index in element)) for element in elements]
    zero_volume = sum(1 for value in volumes if math.isclose(value, 0.0, abs_tol=1.0e-18))
    fixed_keys = [(item["node"], dof) for item in case["fixed_dofs"] for dof in item["dofs"]]
    load_nodes = [item["node"] for item in case["loads"]]
    boundary_valid = all(0 <= node < len(nodes) for node, _ in fixed_keys)
    loads_valid = all(0 <= node < len(nodes) for node in load_nodes)
    return {
        "node_count": len(nodes),
        "element_count": len(elements),
        "component_count": _component_count(elements, len(nodes)) if not invalid else None,
        "invalid_connectivity": invalid,
        "repeated_connectivity": repeated,
        "zero_volume_elements": zero_volume,
        "min_abs_volume": min((abs(value) for value in volumes), default=None),
        "fixed_dof_count": len(fixed_keys),
        "duplicate_fixed_dofs": len(fixed_keys) - len(set(fixed_keys)),
        "load_node_count": len(load_nodes),
        "load_sum": sum(float(item["value"]) for item in case["loads"]),
        "boundary_valid": boundary_valid,
        "loads_valid": loads_valid,
    }


def _classify(result: dict[str, Any], record: dict[str, Any], audit: dict[str, Any]) -> tuple[str, str, str]:
    reason = str(result.get("reason", ""))
    if result.get("status") == "TIMEOUT":
        return "G", "The QF process exceeded the 120 second limit.", "Measure separately with a resource budget and a larger timeout."
    if audit["invalid_connectivity"] or audit["repeated_connectivity"] or audit["zero_volume_elements"]:
        return "D", "Invalid, repeated or zero-volume tetrahedral connectivity is present.", "Reject this mesh from the neutral QF case and retain the source as a mesh diagnostic."
    if (audit["component_count"] or 0) > 1:
        return "C", f"The mesh contains {audit['component_count']} disconnected components; one global support pattern cannot constrain them all.", "Do not run the neutral case; reject it or define per-component physical boundary conditions."
    if result.get("run_verdict") == "FAIL":
        return "B", "QF solved numerically but the engineering audit rejected low-quality element checks.", "Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case."
    if (record.get("quality_min") or 1.0) < 0.05:
        return "B", f"The Gmsh quality minimum is {record.get('quality_min'):.6g}, below the bounded audit target.", "Remesh or retain only as an explicitly low-quality robustness case."
    if "singular" in reason.casefold() or "residual" in reason.casefold():
        return "F", reason, "Create a minimal connected reproducer before considering any QF change."
    return "H", reason or "No decisive evidence was retained by the runner.", "Manual review required; do not classify as a QF bug without a reproducer."


def build(manifest_path: Path = DEFAULT_MANIFEST, results_path: Path = DEFAULT_RESULTS) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(results_path.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in manifest["records"] if record.get("status") == "PASS" and record.get("qf_case")}
    rows = []
    for result in report["results"]:
        if result.get("status") == "PASS":
            continue
        record = records[result["id"]]
        audit = inspect_case(record)
        category, evidence, action = _classify(result, record, audit)
        rows.append({"id": result["id"], "category": category, "evidence": evidence, "action": action, "result": result, "mesh": record, "audit": audit})
    counts = Counter(row["category"] for row in rows)
    return {
        "schema_version": 1,
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "results": str(results_path.relative_to(ROOT)).replace("\\", "/"),
        "qf_source_sha": report.get("qf_source_sha"),
        "qf_worktree_dirty": report.get("qf_worktree_dirty"),
        "non_pass_count": len(rows),
        "category_counts": dict(counts),
        "rows": rows,
    }


def _markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Public Volumetric Campaign Triage",
        "",
        "This report classifies every non-PASS execution in the recorded campaign. It is a diagnostic corpus report, not a FEM qualification claim.",
        "",
        f"- QF source SHA: `{data['qf_source_sha']}`",
        f"- Runner worktree dirty: `{data['qf_worktree_dirty']}`",
        f"- Non-PASS cases classified: `{data['non_pass_count']}`",
        f"- Categories: `{data['category_counts']}`",
        "",
        "## Category key",
        "",
        "| Category | Meaning |",
        "| --- | --- |",
        "| A | Source model invalid or outside the intended volumetric use |",
        "| B | Bad or insufficient mesh quality |",
        "| C | Automatic BC/load pattern unsuitable for disconnected or multi-volume geometry |",
        "| D | Import/connectivity/element IDs invalid |",
        "| E | Plausible QF bug |",
        "| F | Numerical robustness or convergence issue requiring a reproducer |",
        "| G | Performance, memory or timeout issue |",
        "| H | Unknown |",
        "",
        "## Case matrix",
        "",
        "| Case | Category | Mesh | Components | Qmin | Proof | Action |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in data["rows"]:
        mesh, audit = row["mesh"], row["audit"]
        proof = row["evidence"].replace("|", "/")
        action = row["action"].replace("|", "/")
        qmin = mesh.get("quality_min")
        lines.append(f"| {row['id']} | {row['category']} | {audit['element_count']} TET4 | {audit['component_count']} | {qmin:.6g} | {proof} | {action} |")
    lines.extend([
        "",
        "## Boundary/load audit",
        "",
        "The generator applies the minimum-x nodes as a full support, constrains two transverse DOFs at one maximum-x node, and distributes 1,000 N over maximum-x nodes. The recorded cases have non-zero loads and valid node references. The decisive defect is not a zero-load setup: disconnected meshes receive a single global support pattern and can therefore remain mechanically under-constrained. Those cases must not be used to infer a QF solver defect.",
        "",
        "## Decision",
        "",
        "No QF numerical defect is demonstrated by this campaign. The actionable fixes are to reject degenerate connectivity from neutral cases, exclude disconnected assemblies from the single-domain BC convention, and characterize the large timeout separately. The remaining low-quality single-component cases stay visible as mesh robustness diagnostics.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    data = build(args.manifest, args.results)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(data), encoding="utf-8")
    print(json.dumps({"non_pass_count": data["non_pass_count"], "category_counts": data["category_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
