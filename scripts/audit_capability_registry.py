"""Validate and render the controlled QF Solver capability registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
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
    "RESEARCH_DEFERRED", "EXPERIMENTAL_DEFERRED", "NOT_IN_RELEASE_SCOPE",
}
ELEMENT_PATTERN = re.compile(r'^\s*"([A-Z][A-Z0-9]*)": ElementSpec', re.MULTILINE)
ROUTE_PATTERN = re.compile(r'model\.analysis\.type == "([a-z_]+)"')

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
    "INF-RBE-CONSTRAINTS": [("src/solveur/core/rbe.py", "Rbe2Definition")],
    "ANA-STATIC": [("src/solveur/core/router.py", '"linear_static"')],
    "ANA-MODAL": [("src/solveur/core/router.py", '"modal"')],
    "ANA-NEWMARK": [("src/solveur/core/router.py", '"transient_dynamic"')],
    "ANA-HARMONIC": [("src/solveur/core/router.py", '"harmonic_response"')],
    "ANA-BUCKLING": [("src/solveur/core/router.py", '"linear_buckling"')],
    "ANA-NONLINEAR-LOAD": [("src/solveur/core/router.py", '"nonlinear_static"')],
    "ANA-GEOMETRIC-NONLINEAR": [("src/solveur/core/router.py", '"geometric_nonlinear_static"')],
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


def _current_source(path_text: str) -> str:
    return (ROOT / path_text).read_text(encoding="utf-8")


def _revision_source(revision: str, path_text: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path_text}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode:
        raise RuntimeError(f"Cannot read historical source {revision}:{path_text}: {completed.stderr.strip()}")
    return completed.stdout


def _element_names(source: str) -> set[str]:
    return set(ELEMENT_PATTERN.findall(source))


def _analysis_routes(source: str) -> set[str]:
    return set(ROUTE_PATTERN.findall(source))


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
    current_elements = _element_names(_current_source("src/solveur/elements/registry.py"))
    registered_elements = {
        row["ELEMENT"] for row in rows if row.get("DOMAIN") == "ELEMENT" and row.get("ELEMENT") in current_elements
    }
    for element in sorted(current_elements - registered_elements):
        errors.append(f"Public element family is unregistered: {element}.")
    current_routes = _analysis_routes(_current_source("src/solveur/core/router.py"))
    registered_routes = {row["ANALYSIS"] for row in rows if row.get("DOMAIN") == "ANALYSIS"}
    for route in sorted(current_routes - registered_routes):
        errors.append(f"Public analysis route is unregistered: {route}.")
    for release in registry.get("historical_releases", []):
        try:
            historical_elements = _element_names(_revision_source(release["sha"], "src/solveur/elements/registry.py"))
            historical_routes = _analysis_routes(_revision_source(release["sha"], "src/solveur/core/router.py"))
        except RuntimeError as error:
            errors.append(str(error))
            continue
        if historical_elements != set(release["elements"]):
            errors.append(f"Historical element inventory changed unexpectedly for {release['tag']}.")
        if historical_routes != set(release["analysis_routes"]):
            errors.append(f"Historical analysis inventory changed unexpectedly for {release['tag']}.")
        for element in sorted(historical_elements - current_elements):
            errors.append(f"Historical element family removed without retirement evidence: {element} from {release['tag']}.")
        for route in sorted(historical_routes - current_routes):
            errors.append(f"Historical analysis route removed without retirement evidence: {route} from {release['tag']}.")
    return errors


def render_document(registry: dict[str, Any]) -> str:
    rows = registry["capabilities"]
    counts = {level: sum(row["VNV_LEVEL"] == level for row in rows) for level in sorted(VNV_LEVELS)}
    g05_gaps = (
        "The G05-B family campaign covers TET4, TET10, HEX8, HEX20, BEAM2, MITC3/MITC3+, MITC4 and discrete; "
        "refinement policies are OWNER_APPROVED_BOUNDED and final clean provenance remains open."
    )
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
        f"- Public element-analysis combinations: {len(registry['public_analysis_combinations'])}",
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
        "| Family | Static | Modal | Newmark | Harmonic | Buckling | Load-control | Geometric | 0.2.6 gap |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        "| BEAM2 | code/tests | G05-B prequal | G05-B prequal | G05-B prequal | n/a | n/a | n/a | official G05 remains open |",
        "| MITC3 | READY corpus | READY corpus | READY corpus | READY corpus | n/a | n/a | n/a | G05 acceptance remains open |",
        "| MITC4 | READY corpus | READY corpus | READY corpus | READY corpus | n/a | n/a | n/a | G05 acceptance remains open |",
        "| TET4 | READY corpus | G05-B prequal | G05-B prequal | G05-B prequal | READY/planned | READY | bounded evidence | official G05 remains open |",
        "| TET10 | READY/planned | G05-B prequal | G05-B prequal | G05-B prequal | planned | READY/planned | research route | official G05 remains open |",
        "| HEX8 | READY/planned | G05-B prequal | G05-B prequal | G05-B prequal | planned | READY/planned | bounded evidence | official G05 remains open |",
        "| HEX20 | READY/planned | G05-B prequal | G05-B prequal | G05-B prequal | planned | READY/planned | research route | official G05 remains open |",
        "| Discrete | READY/planned | G05-B prequal | G05-B prequal | G05-B prequal | n/a | n/a | n/a | official G05 remains open |",
        "",
        "## G05-B Integration And Open Gaps",
        "",
        "- `G05-B` is supplemented by an all-family campaign with MOD 14, DYN 32 and HAR 12 controlled cases. It remains internal prequalification and does **not** close `026-G05`.",
        "- The family campaign executes MOD 14, DYN 32 time-level cases and HAR 12 across all eight requested family rows. See `0_2_6_g05_family_coverage.md`; it remains internal prequalification.",
        f"- {g05_gaps}",
        "- The modal mesh, Newmark time-refinement, and harmonic frequency-refinement policies are `OWNER_APPROVED_BOUNDED`; final clean provenance and Owner closeout remain required.",
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
        "| Release | SHA | Element inventory | Analysis routes |",
        "| --- | --- | --- | --- |",
    ])
    for release in registry["historical_releases"]:
        lines.append(
            f"| `{release['tag']}` | `{release['sha']}` | {', '.join(release['elements'])} | "
            f"{', '.join(release['analysis_routes'])} |"
        )
    lines.extend([
        "",
        "The audit reads these release sources directly from Git. It fails if the recorded historical inventory changes, "
        "if a released family or route disappears without a retirement record, or if the current source adds an element family or analysis route without a registry entry.",
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
