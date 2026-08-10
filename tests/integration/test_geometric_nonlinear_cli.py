import json
import subprocess
import sys
from pathlib import Path

from solveur.api import load_model, solve_model


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "tet4_geometric_nonlinear_static.json"


def test_geometric_nonlinear_example_api_and_cli(tmp_path: Path) -> None:
    model = load_model(EXAMPLE)
    result = solve_model(model)
    assert result.analysis == "geometric_nonlinear_static"
    assert result.run_verdict.value == "WARNING"
    output = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "qf_solver.py"),
            "solve",
            "--input",
            str(EXAMPLE),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["solver"]["scope"] == "tet4-total-lagrangian-structural-v2"
