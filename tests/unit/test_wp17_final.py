import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_wp17_final_state_is_bounded_and_complete() -> None:
    state = _load("qualification/0_2_7/wp17_final_state.json")

    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["runtime"]["petsc"] == "3.25.1"
    assert state["runtime"]["mpi"] == "MPICH 5.0.1 / MPI 5.0"
    assert state["runtime"]["fallback_policy"].startswith("no implicit fallback")
    assert state["contract"]["wp14_tolerances_changed"] is False
    assert state["contract"]["post_result_tuning"] is False
    assert state["evidence"]["subscale_equivalence"]["status"] == "PASS"
    assert state["evidence"]["one_million_true_dof"]["status"] == "PASS"
    assert state["evidence"]["one_million_true_dof"]["replays"] == 2
    assert state["evidence"]["three_million_silver"]["status"] == "PASS"
    assert state["evidence"]["three_million_silver"]["replays"] == 2
    assert state["acceptance"]["petsc_runtime_required"] is False
    assert state["acceptance"]["scipy_matrix_free_path_preserved"] is True

    for evidence_path in (
        state["evidence"]["subscale_equivalence"]["path"],
        state["evidence"]["one_million_true_dof"]["wp16_official_evidence"],
        state["evidence"]["three_million_silver"]["evidence"],
    ):
        assert (ROOT / evidence_path).is_file()


def test_wp17_final_governance_points_to_closeout() -> None:
    gates = _load("qualification/0_2_7/gates.json")
    gate = next(item for item in gates["level_up"]["gates"] if item["id"] == "LUP-027-G17")
    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert "qualification/0_2_7/wp17_final_state.json" in gate["evidence"]
    assert "docs/verification/0_2_7/0_2_7_wp17_final.md" in gate["evidence"]

    requirements = _load("qualification/0_2_7/requirements.json")
    requirement = next(
        item for item in requirements["level_up_requirements"] if item["id"] == "027-LU-REQ-017"
    )
    assert requirement["status"] == "PASS_WITH_LIMITATIONS"
    assert requirement["owner_decision"].startswith("PASS_WITH_LIMITATIONS:")
