"""Contract tests for the G06 deep evidence aggregator."""

from __future__ import annotations

from scripts.run_g06_j2_depth import _invariant_matrix


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
