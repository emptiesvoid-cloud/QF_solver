from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "contact" / "frictional_bstar_small_rotation"
FIXTURE_SHA256 = "b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5"


def test_example_fixture_is_the_archived_r14_input_and_selects_bstar() -> None:
    fixture = EXAMPLE / "model_r14_bstar_slip.json"
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == FIXTURE_SHA256
    model = json.loads(fixture.read_text(encoding="utf-8"))
    assert model["analysis"]["type"] == "linear_static"
    assert model["analysis"]["contact_search_mode"] == "initial"
    assert model["analysis"]["contact_finite_sliding"] is False
    assert model["analysis"]["contact_tangential_transfer"] == "small_rotation_work_conjugate"
    assert len(model["contacts"]) == 1
    assert len(model["contacts"][0]["master_nodes"]) == 3
    assert len(model["analysis"]["contact_load_history"]) == 9


def test_example_fixture_loads_through_public_api_with_bstar_opt_in() -> None:
    from qf_solver import load_model

    model = load_model(EXAMPLE / "model_r14_bstar_slip.json")
    assert model.analysis.parameters["contact_tangential_transfer"] == "small_rotation_work_conjugate"


def test_example_default_invocation_does_not_launch_a_calculation() -> None:
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE / "run_example.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "No calculation launched" in completed.stdout
    assert "--run" in completed.stdout
    assert "Saved B* result" not in completed.stdout


def test_explicit_run_refuses_to_overwrite_before_loading_solver(tmp_path: Path) -> None:
    output = tmp_path / "existing.json"
    output.write_text("preserve", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE / "run_example.py"), "--run", "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 2
    assert "refusing to overwrite existing result file" in completed.stderr
    assert output.read_text(encoding="utf-8") == "preserve"


def test_experimental_bounded_maturity_is_scoped_without_registry_vocabulary_change() -> None:
    from scripts.capability_registry_v2 import ALLOWED_STATES

    record_path = ROOT / "qualification" / "0_2_12" / "wp_c01_bstar_capability_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["B_STAR_CAPABILITY_MATURITY"] == "EXPERIMENTAL_BOUNDED"
    assert "EXPERIMENTAL_BOUNDED" not in ALLOWED_STATES
    assert record["qualification_promotion"] == "NONE"
    assert record["implementation_limitations"]["numeric_angle_threshold"].startswith("none")
    assert "finite sliding or updated projection" in record["exclusions"]
    assert "a qualified global consistent slip tangent" in record["exclusions"]
