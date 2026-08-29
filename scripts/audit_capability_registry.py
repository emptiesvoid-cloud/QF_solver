"""Validate and render the controlled QF Solver capability registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "qualification" / "capability_registry.json"
DEFAULT_DOCUMENT = ROOT / "docs" / "verification" / "0_2_6" / "capability_coverage.md"
REQUIRED_FIELDS = {
    "CAPABILITY_ID", "DOMAIN", "ELEMENT", "ANALYSIS", "MATERIAL_PHYSICS",
    "PRESENT_IN_CODE", "PUBLIC", "MATURITY", "TESTS", "VNV_LEVEL",
    "026_GATE_OR_WP", "EVIDENCE", "LAST_VERIFIED_SHA", "LIMITATIONS", "STATUS",
}
VNV_LEVELS = {"L0", "L1", "L2", "L3"}
STATUSES = {
    "PRESENT_DEFERRED", "PRESENT_PARTIALLY_MAPPED", "PRESENT_REQUALIFICATION_PENDING",
    "PRESENT_GAP_RECORDED", "OPEN_QUALIFICATION", "EXPERIMENTAL_NOT_QUALIFIED",
    "RESEARCH_DEFERRED", "NOT_IN_RELEASE_SCOPE",
}

# Each source sentinel is deliberately narrow: it detects an implemented public
# family or route without attempting to infer maturity from source code.
SOURCE_SENTINELS = {
    "ELE-BEAM2": [("src/solveur/elements/registry.py", '"BEAM2"')],
    "ELE-MITC3": [("src/solveur/elements/registry.py", '"MITC3"')],
    "ELE-MITC4": [("src/solveur/elements/registry.py", '"MITC4"')],
    "ELE-TET4": [("src/solveur/elements/registry.py", '"TET4"')],
    "ELE-TET10": [("src/solveur/elements/registry.py", '"TET10"')],
    "ELE-HEX8": [("src/solveur/elements/registry.py", '"HEX8"')],
    "ELE-HEX20": [("src/solveur/elements/registry.py", '"HEX20"')],
    "ELE-DISCRETE": [("src/solveur/elements/discrete.py", "class")],
    "ANA-STATIC": [("src/solveur/core/router.py", '"linear_static"')],
    "ANA-MODAL": [("src/solveur/core/router.py", '"modal"')],
    "ANA-NEWMARK": [("src/solveur/core/router.py", '"transient_dynamic"')],
    "ANA-HARMONIC": [("src/solveur/core/router.py", '"harmonic_response"')],
    "ANA-BUCKLING": [("src/solveur/core/router.py", '"linear_buckling"')],
    "ANA-NONLINEAR-LOAD": [("src/solveur/core/router.py", '"nonlinear_static"')],
    "ANA-ARC-LENGTH": [("src/solveur/core/nonlinear/solver.py", "arc_length")],
    "MAT-ELASTIC": [("src/solveur/materials/solid.py", "SolidMaterial")],
    "MAT-ORTHOTROPIC-LAMINATE": [("src/solveur/materials", "")],
    "MAT-J2-SMALL": [("src/solveur/materials/solid.py", "VonMisesElastoplasticMaterial")],
    "MAT-TL-ELASTIC": [("src/solveur/core/analyses/geometric_nonlinear.py", "TotalLagrangian")],
    "MAT-FINITE-J2": [("src/solveur/elements/solid/total_lagrangian_j2.py", "TotalLagrangianJ2")],
    "MAT-COUPLED-NL": [("src/solveur/core/assembly/nonlinear.py", "TotalLagrangianJ2")],
    "CON-FRICTIONLESS": [("src/solveur/contact/solver.py", "Frictionless")],
    "CON-FRICTION": [("src/solveur/contact/support.py", "friction_coefficient")],
    "INF-MESH-GMSH": [("src/solveur/io/gmsh_importer.py", "")],
    "INF-LOADS-BC": [("src/solveur/core/model.py", "loads")],
    "INF-POST": [("src/solveur/post/stress.py", "")],
    "INF-SPARSE-SCIPY": [("src/solveur/core/assembly", "")],
    "INF-PETSC-SLEPC": [("src/solveur/large/solver.py", "PETSc")],
    "INF-DIAGNOSTICS-FAILURES": [("src/solveur/core/nonlinear/solver.py", "failure")],
    "INF-PERF-SCALING": [("src/solveur/large/profiling.py", "")],
    "INF-EXTERNAL-CORRELATION": [("src/solveur/verification/code_aster_j2.py", "")],
}


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sentinel_exists(path_text: str, token: str) -> bool:
    path = ROOT / path_text
    return path.exists() and (not token or token in path.read_text(encoding="utf-8"))


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = registry.get("capabilities", [])
    identifiers = [row.get("CAPABILITY_ID") for row in rows]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate CAPABILITY_ID in capability registry.")
    by_id = {row.get("CAPABILITY_ID"): row for row in rows}
    for row in rows:
        capability_id = row.get("CAPABILITY_ID", "<missing>")
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            errors.append(f"{capability_id}: missing required fields: {', '.join(sorted(missing))}.")
            continue
        if row["VNV_LEVEL"] not in VNV_LEVELS:
            errors.append(f"{capability_id}: invalid VNV_LEVEL {row['VNV_LEVEL']!r}.")
        if row["STATUS"] not in STATUSES:
            errors.append(f"{capability_id}: invalid STATUS {row['STATUS']!r}.")
        if row["PRESENT_IN_CODE"] and not (row["TESTS"] or row["026_GATE_OR_WP"] or row["LIMITATIONS"]):
            errors.append(f"{capability_id}: implemented capability has no test, gate or limitation justification.")
    for capability_id in registry.get("public_capability_ids", []):
        if capability_id not in by_id:
            errors.append(f"Public capability orphaned from registry: {capability_id}.")
        elif not by_id[capability_id].get("PUBLIC"):
            errors.append(f"Public capability is not marked PUBLIC: {capability_id}.")
    for combination in registry.get("public_analysis_combinations", []):
        element = combination.get("element")
        analysis = combination.get("analysis")
        if element not in by_id or analysis not in by_id:
            errors.append(f"Public element/analysis combination is orphaned: {element} / {analysis}.")
    retired = {row["CAPABILITY_ID"] for row in registry.get("retired_capabilities", [])}
    for capability_id in registry.get("historical_capability_ids", []):
        if capability_id not in by_id and capability_id not in retired:
            errors.append(f"Historical capability silently removed: {capability_id}.")
    for capability_id, sentinels in SOURCE_SENTINELS.items():
        if all(_sentinel_exists(path, token) for path, token in sentinels) and capability_id not in by_id:
            errors.append(f"Implemented capability is unregistered: {capability_id}.")
    return errors


def render_document(registry: dict[str, Any]) -> str:
    rows = registry["capabilities"]
    counts = {level: sum(row["VNV_LEVEL"] == level for row in rows) for level in sorted(VNV_LEVELS)}
    g05_gaps = "TET10, HEX8, HEX20, BEAM2, and discrete have no G05 READY mapping; refinement policies remain UNDEFINED_POLICY."
    lines = [
        "# Capability Coverage Register",
        "",
        "This generated view is derived from `qualification/capability_registry.json`, the controlled source of truth. "
        "Code presence is never interpreted as qualification.",
        "",
        "## Baseline",
        "",
        f"- Registry: `{registry['registry_id']}`",
        f"- Historical qualified source: `{registry['historical_baseline']['qualified_source_sha']}`",
        f"- Capability count: {len(rows)}; public mappings: {len(registry['public_capability_ids'])}",
        f"- V&V distribution: L0={counts['L0']}, L1={counts['L1']}, L2={counts['L2']}, L3={counts['L3']}",
        "",
        "## Maturity Meaning",
        "",
        "- **L0**: code/inventory only. **L1**: executable smoke or route evidence. **L2**: quantitative verification. "
        "**L3**: bounded qualification backed by recorded evidence.",
        "- `EXPERIMENTAL`, `RESEARCH`, and `NOT_IN_RELEASE_SCOPE` remain visible even when code and historical tests exist.",
        "",
        "## Capability To Gate Matrix",
        "",
        "| ID | Domain | Element | Analysis | Maturity | V&V | 0.2.6 gate/WP | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['CAPABILITY_ID']}` | {row['DOMAIN']} | {row['ELEMENT']} | {row['ANALYSIS']} | "
            f"{row['MATURITY']} | {row['VNV_LEVEL']} | `{row['026_GATE_OR_WP']}` | {row['STATUS']} |"
        )
    lines.extend([
        "",
        "## Element x Analysis Coverage",
        "",
        "| Family | Static | Modal | Newmark | Harmonic | Buckling | Nonlinear | 0.2.6 gap |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| BEAM2 | code/tests | historical tests | historical tests | historical tests | n/a | n/a | G05 READY mapping missing |",
        "| MITC3 | READY corpus | READY corpus | READY corpus | READY corpus | n/a | n/a | G05 acceptance remains open |",
        "| MITC4 | READY corpus | READY corpus | READY corpus | READY corpus | n/a | n/a | G05 acceptance remains open |",
        "| TET4 | READY corpus | G05-B READY | G05-B READY | G05-B READY | READY/planned | READY | family evidence is partial |",
        "| TET10 | READY/planned | historical only | historical only | historical only | planned | READY/planned | G05 READY mapping missing |",
        "| HEX8 | READY/planned | planned only | planned only | planned only | planned | READY/planned | G05 READY mapping missing |",
        "| HEX20 | READY/planned | planned only | planned only | planned only | planned | READY/planned | G05 READY mapping missing |",
        "| Discrete | READY/planned | historical only | historical only | historical only | n/a | n/a | G05 READY mapping missing |",
        "",
        "## G05-B Integration And Open Gaps",
        "",
        "- `G05-B` executed 4 modal, 4 Newmark, and 4 harmonic TET4 cases on `fbae9d983da451052d95e111a85970f93899e409` with 12 PASS. It supplements the official G05 evidence; it does **not** close `026-G05`.",
        f"- {g05_gaps}",
        "- The modal mesh, Newmark time-refinement, and harmonic frequency-refinement policies remain `UNDEFINED_POLICY` until an Owner approves justified acceptance bands.",
        "",
        "## Historical Continuity",
        "",
        "All capabilities tracked from 0.2.5a0 remain represented. No historical capability is silently retired. "
        "Historical tests that have not yet been mapped into a 0.2.6 READY case are recorded as explicit gaps, rather than treated as lost evidence or a current qualification claim.",
        "",
        "| Capability | Historical reference | Current maturity | Continuity assessment |",
        "| --- | --- | --- | --- |",
    ])
    for row in rows:
        reference = "0.2.5 recorded" if row["LAST_VERIFIED_SHA"] == registry["historical_baseline"]["qualified_source_sha"] else "0.2.6 supplemental/current"
        gap = "explicit 0.2.6 mapping gap" if "GAP" in row["STATUS"] else "present; no silent maturity downgrade"
        lines.append(f"| `{row['CAPABILITY_ID']}` | {reference} | {row['MATURITY']} | {gap} |")
    lines.extend([
        "",
        "No capability is removed, renamed, or retired in this foundation registry. Any future removal must enter `retired_capabilities` with a rationale and retained evidence reference; the audit otherwise fails.",
        "",
        "## Anti-Forgetting Contract",
        "",
        "`scripts/audit_capability_registry.py --check` fails on duplicate IDs, missing required fields, orphan public claims, unregistered source sentinels, silent historical removal, or an implemented capability lacking a test, gate, or limitation justification. "
        "It intentionally does not require L3 for every capability.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-document", action="store_true")
    arguments = parser.parse_args()
    registry = load_registry(arguments.registry)
    errors = validate_registry(registry)
    if errors:
        print("\n".join(errors))
        return 1
    if arguments.write_document:
        DEFAULT_DOCUMENT.write_text(render_document(registry), encoding="utf-8")
    print(f"Capability registry PASS: {len(registry['capabilities'])} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
