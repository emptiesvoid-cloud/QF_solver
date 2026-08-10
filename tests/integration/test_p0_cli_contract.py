import json

from tests.helpers.cli import run_solver_cli
from tests.helpers.models import write_tet10_model


def test_tet10_qualification_run_is_accepted_after_signed_review(tmp_path):
    model = tmp_path / "tet10.json"
    result = tmp_path / "result.json"
    write_tet10_model(model)
    completed = run_solver_cli(
        "solve",
        "--input",
        model,
        "--output",
        result,
        "--verification-profile",
        "qualification",
    )
    assert completed.returncode == 0
    assert "RUN VERDICT: PASS" in completed.stdout
    data = json.loads(result.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["run_verdict"] == "PASS"


def test_tet10_engineering_run_is_accepted(tmp_path):
    model = tmp_path / "tet10.json"
    result = tmp_path / "result.json"
    write_tet10_model(model)
    completed = run_solver_cli(
        "solve",
        "--input",
        model,
        "--output",
        result,
        "--verification-profile",
        "engineering",
    )
    assert completed.returncode == 0
    assert "RUN VERDICT: PASS" in completed.stdout
    assert json.loads(result.read_text(encoding="utf-8"))["run_verdict"] == "PASS"


def test_evidence_propagates_tet10_qualification_acceptance(tmp_path):
    model = tmp_path / "tet10.json"
    evidence = tmp_path / "evidence"
    write_tet10_model(model)
    completed = run_solver_cli(
        "evidence",
        "--input",
        model,
        "--output",
        evidence,
        "--verification-profile",
        "qualification",
    )
    assert completed.returncode == 0
    assert (evidence / "evidence_manifest.json").exists()
    summary = json.loads((evidence / "qualification_summary.json").read_text(encoding="utf-8"))
    assert summary["run_verdict"] == "PASS"


def test_malformed_json_returns_exit_code_2_without_traceback(tmp_path):
    model = tmp_path / "bad.json"
    model.write_text('{"nodes": [', encoding="utf-8")
    completed = run_solver_cli("check-mesh", "--input", model)
    assert completed.returncode == 2
    assert "InputValidationError" in completed.stderr
    assert "Traceback" not in completed.stderr

    debug = run_solver_cli("check-mesh", "--input", model, "--debug")
    assert debug.returncode != 2
    assert "Traceback" in debug.stderr
    assert "InputValidationError" in debug.stderr


def test_singular_model_returns_numerical_exit_code_3(tmp_path):
    model = tmp_path / "singular.json"
    result = tmp_path / "result.json"
    model.write_text(
        json.dumps(
            {
                "analysis": "linear_static",
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25}},
                "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
                "loads": [{"node": 1, "dof": "UX", "value": 1.0}],
            }
        ),
        encoding="utf-8",
    )
    completed = run_solver_cli("solve", "--input", model, "--output", result)
    assert completed.returncode == 3
    assert "NumericalConvergenceError" in completed.stderr


def test_qualification_readiness_exit_codes_are_stable(tmp_path):
    accepted = run_solver_cli(
        "qualification-readiness",
        "--scope",
        "tet4-linear-static",
        "--json-report",
        tmp_path / "ready.json",
    )
    rejected = run_solver_cli("qualification-readiness", "--scope", "material-nonlinear")
    laminate = run_solver_cli("qualification-readiness", "--scope", "mitc4-laminate-static")
    orthotropic = run_solver_cli("qualification-readiness", "--scope", "orthotropic-solid-tet4-tet10")
    harmonic = run_solver_cli("qualification-readiness", "--scope", "mitc4-harmonic-response")
    condensation = run_solver_cli(
        "qualification-readiness", "--scope", "mitc4-harmonic-condensation"
    )
    singular_stress = run_solver_cli(
        "qualification-readiness", "--scope", "orthotropic-solid-singular-stress-assessment"
    )
    assert accepted.returncode == 0
    assert rejected.returncode == 4
    assert laminate.returncode == 4
    assert orthotropic.returncode == 0
    assert "scope status: candidate" in orthotropic.stdout
    assert "scope status: development" in laminate.stdout
    assert harmonic.returncode == 0
    assert "scope status: candidate" in harmonic.stdout
    assert condensation.returncode == 0
    assert "scope status: candidate" in condensation.stdout
    assert singular_stress.returncode == 0
    assert "scope status: candidate" in singular_stress.stdout
    assert json.loads((tmp_path / "ready.json").read_text(encoding="utf-8"))["status"] == "PASS"


def test_corrupted_hdf5_cli_returns_input_exit_code_2(tmp_path):
    source = tmp_path / "corrupt.h5"
    source.write_bytes(b"broken-hdf5")
    completed = run_solver_cli("inspect-large", "--input", source, "--output", tmp_path / "audit.json")
    assert completed.returncode == 2
    assert "InputValidationError" in completed.stderr
