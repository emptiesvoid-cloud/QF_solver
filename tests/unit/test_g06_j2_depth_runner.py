"""Contract tests for the G06 deep evidence aggregator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_g06_j2_depth import _invariant_matrix


ROOT = Path(__file__).resolve().parents[2]


def _family_rows(status: str = "PASS") -> list[dict[str, object]]:
    return [{"element": family, "status": status} for family in ("TET4", "TET10", "HEX8", "HEX20")]


def test_invariant_matrix_keeps_all_four_j2_families_and_external_status() -> None:
    internal = {
        "mesh_refinement": {"rows": [{"element": family, "status": "PASS"} for family in ("TET4", "TET10", "HEX8", "HEX20")]},
        "multi_element": {"rows": _family_rows()},
        "energy_balance": {"rows": [{"element": family, "status": "PASS_INTERNAL_ENERGY"} for family in ("TET4", "TET10", "HEX8", "HEX20")]},
        "cyclic": {"rows": _family_rows()},
        "rollback": {"rows": [{"element": family, "status": "PASS_INTERNAL_ROLLBACK"} for family in ("TET4", "TET10", "HEX8", "HEX20")]},
    }
    external = {"families": {family: {"status": "PASS"} for family in ("TET4", "TET10", "HEX8", "HEX20")}}

    rows = _invariant_matrix(internal, external)

    assert [row["element"] for row in rows] == ["TET4", "TET10", "HEX8", "HEX20"]
    assert all(row["internal_pass"] and row["external_pass"] for row in rows)


def test_invariant_matrix_does_not_hide_missing_external_evidence() -> None:
    internal = {
        "mesh_refinement": {"rows": _family_rows()},
        "multi_element": {"rows": _family_rows()},
        "energy_balance": {"rows": [{"element": family, "status": "PASS_INTERNAL_ENERGY"} for family in ("TET4", "TET10", "HEX8", "HEX20")]},
        "cyclic": {"rows": _family_rows()},
        "rollback": {"rows": [{"element": family, "status": "PASS_INTERNAL_ROLLBACK"} for family in ("TET4", "TET10", "HEX8", "HEX20")]},
    }

    rows = _invariant_matrix(internal, {"families": {"TET4": {"status": "PASS"}}})

    assert rows[0]["external_pass"] is True
    assert all(row["external_pass"] is False for row in rows[1:])


def test_g06_owner_closeout_preserves_bounded_scope_and_provenance() -> None:
    gate_data = json.loads((ROOT / "qualification/0_2_6/gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in gate_data["gates"] if item["id"] == "026-G06")
    evidence = json.loads((ROOT / "qualification/0_2_6/g06_depth_evidence.json").read_text(encoding="utf-8"))

    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["official_gate_status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["execution_source_sha"] == "8bd0f2d8fdce7bf27ffc4c28e6aa26e69288fa63"
    assert evidence["finite_kinematic_j2"] == "RESEARCH_NOT_QUALIFIED"
    assert any("tangent symmetry" in limitation.lower() for limitation in evidence["limitations"])
    assert any("limited to TET4" in limitation for limitation in evidence["limitations"])
