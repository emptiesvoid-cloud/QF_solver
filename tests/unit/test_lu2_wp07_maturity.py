import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
MATRIX = ROOT / "qualification/0_2_7/lu2_wp07_maturity_matrix.json"


def load_matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_wp07_audits_all_requested_routes_without_promotion():
    matrix = load_matrix()
    routes = {record["route"]: record for record in matrix["routes"]}
    assert set(routes) == {
        "linear_static",
        "modal",
        "buckling",
        "harmonic",
        "dynamics_newmark",
        "nonlinear_static",
        "arc_length",
        "j2_small_strain",
        "contact",
        "wedge6",
    }
    assert matrix["status"] == "PASS_WITH_LIMITATIONS"
    assert matrix["maturity_actions"] == {
        "promotions": [],
        "demotions": [],
        "unchanged": ["all audited routes and element families"],
    }
    assert matrix["governance"]["public_claims_without_evidence"] == []


def test_wp07_reuses_bounded_adversarial_and_j2_evidence():
    matrix = load_matrix()
    assert matrix["external_campaign"]["new_runs"] is False
    assert matrix["adversarial"] == {
        "evidence": [
            "qualification/0_2_7/wp19_state.json",
            "qualification/0_2_7/lu2_wp06_state.json",
            "qualification/0_2_7/wp20_state.json",
        ],
        "cases_reused": 24,
        "expected_failures": 14,
        "fail_closed": True,
        "no_nan_inf": True,
        "silent_fallback": False,
        "new_cases_required": False,
    }
    assert matrix["governance"]["wp04_changed"] is False
    assert matrix["governance"]["numerical_source_changed"] is False
