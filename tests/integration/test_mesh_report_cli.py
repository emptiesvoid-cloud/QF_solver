import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TET4_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_static.json"


def test_cli_check_mesh_writes_json_report(tmp_path: Path):
    report_path = tmp_path / "mesh_report.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main_solveur.py"),
            "check-mesh",
            "--input",
            str(TET4_EXAMPLE),
            "--json-report",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "json report:" in completed.stdout
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["details"]["component_count"] == 1
    assert data["details"]["components"][0]["fixed_translation_node_count"] == 3
    assert data["details"]["element_types"] == {"TET4": 1}
