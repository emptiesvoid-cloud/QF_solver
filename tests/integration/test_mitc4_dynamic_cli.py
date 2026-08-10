from __future__ import annotations

import json
from pathlib import Path

from tests.helpers.cli import PROJECT_ROOT, run_solver_cli


def test_cli_solves_official_mitc4_dynamic_examples(tmp_path: Path) -> None:
    for name, analysis in (
        ("mitc4_modal_cantilever.json", "modal"),
        ("mitc4_newmark_cantilever.json", "transient_dynamic"),
        ("mitc4_harmonic_cantilever.json", "harmonic_response"),
    ):
        output = tmp_path / f"{analysis}.json"
        completed = run_solver_cli(
            "solve",
            "--input",
            PROJECT_ROOT / "examples" / name,
            "--output",
            output,
        )
        assert completed.returncode == 0, completed.stderr
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["analysis"] == analysis
        assert data["status"] == "PASS"
        assert data["solver"]["dynamic_reduction"]["condensed_drilling_dof_count"] == 2
        if analysis == "harmonic_response":
            assert data["solver"]["rayleigh_beta"] == 1.0e-4
            assert data["solver"]["harmonic_condensation"] == {
                "strategy": "exact_scalar_schur_complement",
                "stiffness_factor": "1 + i*omega*rayleigh_beta",
                "supports_stiffness_proportional_damping": True,
            }
