"""Public-facade smoke test for the 0.2.11 experimental rotating route."""

from __future__ import annotations

import json

from qf_solver import load_model, save_result, solve_model


def test_public_json_load_solve_and_save_support_experimental_rotating_modal(tmp_path) -> None:
    radius = 0.05
    area = 3.141592653589793 * radius**2
    inertia = area**2 / (4.0 * 3.141592653589793)
    model_data = {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "shaft"}],
        "materials": {
            "shaft": {
                "type": "beam_isotropic",
                "E": 210.0e9,
                "nu": 0.3,
                "A": area,
                "Iy": inertia,
                "Iz": inertia,
                "J": 2.0 * inertia,
                "density": 7800.0,
            }
        },
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        "concentrated_masses": [
            {
                "type": "rotating_disk",
                "node": 1,
                "mass": 1.0,
                "diametral_inertia": 0.01,
                "polar_inertia": 0.02,
                "axis_global": [1.0, 0.0, 0.0],
            }
        ],
        "analysis": {
            "type": "rotating_modal",
            "method": "dense_qep",
            "parameters": {
                "rotation": {
                    "axis_global": [1.0, 0.0, 0.0],
                    "speed_rad_s": 20.0,
                    "frame_convention": "global_fixed_right_hand_rule",
                },
                "modes": 6,
            },
        },
    }
    model_path = tmp_path / "rotating-model.json"
    result_path = tmp_path / "rotating-result.json"
    model_path.write_text(json.dumps(model_data), encoding="utf-8")

    model = load_model(model_path)
    result = solve_model(model)
    save_result(result, result_path)

    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert type(result).__name__ == "RotatingModalResult"
    assert result.numerical_status == "PASS"
    assert result.maturity == "EXPERIMENTAL"
    assert result.run_verdict.value == "WARNING"
    assert saved["analysis"] == "rotating_modal"
    assert set(saved["raw_eigenvalues"]) == {"real", "imag"}
