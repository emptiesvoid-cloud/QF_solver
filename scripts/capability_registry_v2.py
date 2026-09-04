"""Read, validate, and render the 0.2.7 combination-level capability registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
DEFAULT_VIEW = ROOT / "docs" / "verification" / "0_2_7" / "0_2_7_capability_matrix.md"
ALLOWED_STATES = {
    "SUPPORTED",
    "TESTED",
    "VERIFIED",
    "QUALIFIED_BOUNDED",
    "EXPERIMENTAL",
    "NOT_QUALIFIED",
    "SUPERSEDED",
}
REQUIRED_RECORD_FIELDS = {
    "capability_id",
    "record_kind",
    "element_family",
    "analysis",
    "material_model",
    "formulation_or_route",
    "backend_or_solver_route",
    "support_state",
    "verification_state",
    "qualification_state",
    "evidence_refs",
    "owner_decision",
    "limitations",
    "applicable_version",
    "source_snapshot",
    "supersedes",
    "historical_origin",
}


class RegistryValidationError(ValueError):
    """Raised when a v2 registry violates its machine-readable contract."""


class DuplicateJsonKeyError(ValueError):
    """Raised when the authoritative registry repeats an object key."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in pairs:
        if key in values:
            raise DuplicateJsonKeyError(f"Duplicate JSON key {key!r}.")
        values[key] = value
    return values


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def _record_errors(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = registry.get("records", [])
    record_ids = [record.get("capability_id") for record in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append("Duplicate v2 capability_id.")
    for record in records:
        identifier = record.get("capability_id", "<missing>")
        missing = REQUIRED_RECORD_FIELDS - record.keys()
        if missing:
            errors.append(f"{identifier}: missing fields {sorted(missing)}")
            continue
        for field in ("support_state", "verification_state", "qualification_state"):
            if record[field] not in ALLOWED_STATES:
                errors.append(f"{identifier}: invalid {field} {record[field]!r}")
        if record["record_kind"] not in {"capability_anchor", "combination"}:
            errors.append(f"{identifier}: invalid record_kind")
        if not record["applicable_version"] or not record["source_snapshot"]:
            errors.append(f"{identifier}: version and source_snapshot are required")
        if not isinstance(record["evidence_refs"], list):
            errors.append(f"{identifier}: evidence_refs must be a list")
        if record["qualification_state"] == "QUALIFIED_BOUNDED" and not record["evidence_refs"]:
            errors.append(f"{identifier}: qualified record has no evidence_refs")
        if record["support_state"] != "SUPPORTED" and record["qualification_state"] == "QUALIFIED_BOUNDED":
            errors.append(f"{identifier}: qualified record is not supported")
    return errors


def validate_registry(registry: dict[str, Any]) -> list[str]:
    """Return deterministic contract errors; an empty list means valid."""

    errors: list[str] = []
    if registry.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if registry.get("source_of_truth") is not True:
        errors.append("source_of_truth must be true")
    vocabulary = registry.get("vocabulary", {})
    if set(vocabulary) != ALLOWED_STATES:
        errors.append("vocabulary does not exactly match the active state vocabulary")
    errors.extend(_record_errors(registry))
    records = registry.get("records", [])
    by_id = {record.get("capability_id"): record for record in records}
    public_ids = registry.get("public_capability_ids", [])
    anchors = [record for record in records if record.get("record_kind") == "capability_anchor"]
    anchor_ids = [record.get("capability_id") for record in anchors]
    if len(public_ids) != len(set(public_ids)):
        errors.append("Duplicate public capability_id")
    if set(anchor_ids) != set(public_ids):
        errors.append("Capability anchors do not preserve the public legacy inventory")
    if registry.get("migration", {}).get("migrated_capability_count") != len(public_ids):
        errors.append("Migration count does not match public capability count")
    combinations = [record for record in records if record.get("record_kind") == "combination"]
    combination_ids = [record.get("capability_id") for record in combinations]
    if combination_ids != registry.get("combination_record_ids", []):
        errors.append("Combination record index is not deterministic")
    for public_id in public_ids:
        if public_id not in by_id:
            errors.append(f"Missing migrated public capability {public_id}")
    for record in combinations:
        if not record.get("historical_origin", {}).get("legacy_capability_id"):
            errors.append(f"{record['capability_id']}: missing historical origin")
    return errors


class CapabilityRegistryV2:
    """Minimal read contract for future descriptor and preflight work."""

    def __init__(self, registry: dict[str, Any]) -> None:
        errors = validate_registry(registry)
        if errors:
            raise RegistryValidationError("; ".join(errors))
        self._registry = registry

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._registry["records"])

    def query(self, **selectors: str) -> list[dict[str, Any]]:
        """Return combination rows matching declared non-empty selectors."""

        allowed = {
            "element_family",
            "analysis",
            "material_model",
            "formulation_or_route",
            "backend_or_solver_route",
        }
        unknown = set(selectors) - allowed
        if unknown:
            raise KeyError(f"Unknown registry selectors: {sorted(unknown)}")
        return [
            record
            for record in self.records
            if record["record_kind"] == "combination"
            and all(not value or record[key] == value for key, value in selectors.items())
        ]

    def maturity(self, record: dict[str, Any]) -> dict[str, str]:
        return {
            "support_state": record["support_state"],
            "verification_state": record["verification_state"],
            "qualification_state": record["qualification_state"],
        }

    def evidence(self, record: dict[str, Any]) -> tuple[str, ...]:
        return tuple(record["evidence_refs"])


def render_markdown(registry: dict[str, Any]) -> str:
    """Render a stable user-facing view from the controlled JSON source."""

    errors = validate_registry(registry)
    if errors:
        raise RegistryValidationError("; ".join(errors))
    combinations = [record for record in registry["records"] if record["record_kind"] == "combination"]
    combinations = sorted(combinations, key=lambda record: record["capability_id"])
    state_counts = {
        state: sum(record["qualification_state"] == state for record in combinations)
        for state in sorted(ALLOWED_STATES)
    }
    lines = [
        "---",
        "doc_id: DOC-027-016",
        "revision: 0.1",
        "status: controlled_candidate",
        "applicable_version: 0.2.7",
        'reviewer: ""',
        'approver: ""',
        "---",
        "",
        "# 0.2.7 Capability Registry v2",
        "",
        "**GENERATED_VIEW**: this matrix is rendered from `qualification/0_2_7/capability_registry_v2.json`, which is the source of truth.",
        "",
        f"The v2 registry preserves the 33 public 0.2.6 capability identifiers as traceable anchors and exposes {len(combinations)} explicit element-analysis combination records. Anchor rows retain aggregate historical scope; combination rows are not new execution evidence.",
        "",
        f"- Applicable version: `{registry['applicable_version']}`",
        f"- Source snapshot: `{registry['source_snapshot']}`",
        f"- Legacy capabilities preserved: {len(registry['public_capability_ids'])}",
        f"- Combination records: {len(combinations)}",
        f"- Qualification-state counts: {', '.join(f'{key}={value}' for key, value in state_counts.items() if value)}",
        "",
        "## Active Vocabulary",
        "",
        "`SUPPORTED` means an implementation path is declared. `TESTED` means a case was executed. `VERIFIED` means a quantitative check or invariant was recorded. `QUALIFIED_BOUNDED` requires recorded evidence and inherited scope controls. `EXPERIMENTAL`, `NOT_QUALIFIED`, and `SUPERSEDED` are explicit non-promotional states.",
        "",
        "## Element x Analysis Records",
        "",
        "| Combination | Element | Analysis | Material | Route | Support | Verification | Qualification | Gate / evidence | Limitations |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in combinations:
        evidence = "; ".join(record["evidence_refs"][:2])
        limitations = record["limitations"].replace("|", "\\|")
        lines.append(
            f"| `{record['capability_id']}` | {record['element_family']} | {record['analysis']} | {record['material_model']} | {record['formulation_or_route']} | {record['support_state']} | {record['verification_state']} | {record['qualification_state']} | {evidence} | {limitations} |"
        )
    lines.extend([
        "",
        "## Migration Boundary",
        "",
        "The anchor records preserve the exact legacy public identifiers and their historical status trace. They do not erase aggregate limitations and do not promote code presence. A future registry revision may replace an inherited combination state only with new evidence and an explicit Owner decision.",
        "",
        "Historical statuses such as `PRESENT_REQUALIFICATION_PENDING` remain available only under `historical_origin`; they are not active v2 maturity states.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-view", action="store_true")
    arguments = parser.parse_args()
    registry = load_registry(arguments.registry)
    errors = validate_registry(registry)
    if errors:
        print("\n".join(errors))
        return 1
    if arguments.write_view:
        DEFAULT_VIEW.write_text(render_markdown(registry), encoding="utf-8")
    print(f"Capability registry v2 PASS: {len(registry['public_capability_ids'])} anchors, {len(registry['combination_record_ids'])} combinations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
