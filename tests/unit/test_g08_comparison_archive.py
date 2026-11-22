"""Portable G08 contract and archive checks; no FEM calculation is run here."""

from hashlib import sha256
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from research.g08_compare.case import solve_one
from research.g08_compare.controlled import read_policy, validate_archive
from research.g08_compare.controller import ROOT, run_synthetic

RECEIPT = {"scope": "synthetic", "source": "mock", "inputs_sha256": "mock"}

PRODUCER = """
from pathlib import Path
import sys
from types import SimpleNamespace
from research.g08_compare.case import solve_one

kind, output = sys.argv[1], Path(sys.argv[2])
if kind == 'incomplete':
    sys.exit(0)
if kind == 'error':
    sys.exit(3)
if kind == 'nonpass':
    status, diagnostics = 'FAIL', {'preload_diagnostics': {'stop': 'mock'}}
else:
    status, diagnostics = 'PASS', {'critical_factor': 803.1904623282354, 'critical_mode_residual_relative': 1e-9}

def synthetic_solve(model):
    assert model == 'mock-model'
    return SimpleNamespace(status=status, solver=diagnostics, displacements=[1., 0., 0.])

receipt = dict(scope='synthetic', source='mock', inputs_sha256='mock', nodes=1, resultant_ux=-1.)
solve_one('mock-model', receipt, output, synthetic_solve)
if kind == 'tampered':
    (output / 'mode.npy').write_bytes(b'changed')
if kind == 'wrong_identity':
    import json
    path = output / 'result.json'
    result = json.loads(path.read_text())
    result['inputs_sha256'] = 'different-input'
    path.write_text(json.dumps(result))
"""


def test_g08_policy_records_consumed_attempts():
    policy = read_policy()
    assert policy["status"] == "DEVELOPMENT_ATTEMPTS_CONSUMED"
    assert [scope["id"] for scope in policy["scopes"]] == [
        "g08-tet10-before",
        "g08-tet10-after",
        "g08-tet10-before-retry-001",
    ]
    assert [scope["attempts"] for scope in policy["scopes"]] == [1, 1, 1]
    retry = policy["scopes"][2]
    assert retry["preflight_id"] == "pf-38b39cfebd81"
    assert retry["verdict"] == "G08_RESULT_ARCHIVED"
    assert "does not authorize another attempt" in policy["authorization_scope"]


def test_g08_case_calls_solver_without_analysis_specific_source_override(tmp_path):
    model = object()
    output = tmp_path / "output"
    output.mkdir()
    receipt = {
        "scope": "g08-tet10-after",
        "source": "6dd15ea007439a37327298690232cf81bf4c7f69",
        "inputs_sha256": "b" * 64,
        "nodes": 2,
        "resultant_ux": -1.0,
    }
    calls = []

    def solve(model_argument):
        calls.append(model_argument)
        return SimpleNamespace(
            status="PASS",
            solver={"critical_factor": 12.0, "critical_mode_residual_relative": 1e-10},
            displacements=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        )

    result = solve_one(model, receipt, output, solve)
    assert calls == [model]
    assert result["solver_status"] == "PASS"
    assert (output / "result.json").is_file()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("success", "SCREEN_PASS"),
        ("error", "RUNNER_ERROR"),
        ("incomplete", "RESULT_ARCHIVE_INCOMPLETE"),
        ("nonpass", "SOLVER_NON_PASS"),
        ("tampered", "RESULT_ARCHIVE_INCOMPLETE"),
        ("wrong_identity", "RESULT_ARCHIVE_INCOMPLETE"),
    ],
)
def test_g08_synthetic_runner_archive(tmp_path, kind, expected):
    store = tmp_path / "run"
    bootstrap = f"import sys; sys.path.insert(0, {str(ROOT)!r})\n"
    command = [sys.executable, "-B", "-c", bootstrap + PRODUCER, kind, str(store / "archive")]
    assert run_synthetic(command, store, RECEIPT) == expected
    final = json.loads((store / "attempt.final.json").read_bytes())
    assert final["state"] == expected
    with pytest.raises(FileExistsError):
        run_synthetic(command, store, RECEIPT)
    assert json.loads((store / "attempt.final.json").read_bytes()) == final


def test_g08_synthetic_runner_refuses_real_scope(tmp_path):
    before = dict(RECEIPT, scope="g08-tet10-before")
    store = tmp_path / "never-created"
    with pytest.raises(ValueError, match="only the synthetic scope"):
        run_synthetic([], store, before)
    assert not store.exists()


def _write_valid_archive(directory):
    directory.mkdir(parents=True)
    scope = {
        "id": "g08-tet10-before",
        "source": "a" * 40,
        "inputs": "b" * 64,
        "nodes": 117,
    }
    receipt = {
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "resultant_ux": -1.0,
    }
    mode = np.zeros(scope["nodes"] * 3)
    mode[0] = 1.0
    mode_path = directory / "mode.npy"
    np.save(mode_path, mode, allow_pickle=False)
    diagnostics = {
        "backend": "scipy.sparse.linalg.eigsh",
        "eigen_formulation": "generalized_eigsh",
        "critical_factor": 803.1904623282354,
        "critical_mode_residual_relative": 1e-9,
        "critical_bracket": {
            "lower": 0.0,
            "upper": 803.1904623282354,
            "method": "generalized_eigsh",
        },
        "preload_diagnostics": {
            "converged": True,
            "increments": [
                {"load_factor": factor, "relative_residual": 1e-9}
                for factor in (0.25, 0.5, 0.75, 1.0)
            ],
        },
    }
    result = {
        **{key: scope[key] for key in ("id", "source")},
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "solver_status": "PASS",
        "diagnostics": diagnostics,
        "mode_rank": "NOT_ESTABLISHED",
        "factor": diagnostics["critical_factor"],
        "signed_load": -diagnostics["critical_factor"],
        "magnitude": diagnostics["critical_factor"],
        "residual": diagnostics["critical_mode_residual_relative"],
        "euler_relative_error": 0.0,
        "mode_sha256": sha256(mode_path.read_bytes()).hexdigest(),
    }
    result_path = directory / "result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    return scope, receipt, result, result_path, mode_path


def test_g08_archive_validator_accepts_valid_bundle_and_keeps_mode_rank_open(tmp_path):
    output = tmp_path / "result"
    scope, receipt, _, _, _ = _write_valid_archive(output)
    verdict = validate_archive(output, scope=scope, receipt=receipt, pytest_status="PASSED")
    assert verdict["archive_validation"] == "VALID"
    assert verdict["preload_status"] == "CONVERGED"
    assert verdict["spectral_status"] == "COMPUTED"
    assert verdict["screen_status"] == "SCREEN_PASS"
    assert verdict["first_mode_status"] == "FIRST_MODE_NOT_ESTABLISHED"


@pytest.mark.parametrize("mutation", ["missing", "incomplete", "altered"])
def test_g08_archive_validator_rejects_incomplete_archives(tmp_path, mutation):
    output = tmp_path / "result"
    scope, receipt, result, result_path, mode_path = _write_valid_archive(output)
    if mutation == "missing":
        result_path.unlink()
        mode_path.unlink()
    elif mutation == "incomplete":
        result["diagnostics"].pop("critical_bracket")
        result_path.write_text(json.dumps(result), encoding="utf-8")
    else:
        mode_path.write_bytes(b"tampered")
    verdict = validate_archive(output, scope=scope, receipt=receipt, pytest_status="PASSED")
    assert verdict["archive_validation"] == "INVALID"
    assert verdict["archive_errors"]


@pytest.mark.parametrize("mutation", ["identity", "mode_rank", "residual", "euler_error"])
def test_g08_archive_validator_rejects_identity_and_metric_drift(tmp_path, mutation):
    output = tmp_path / "result"
    scope, receipt, result, result_path, _ = _write_valid_archive(output)
    if mutation == "identity":
        result["inputs_sha256"] = "c" * 64
    elif mutation == "mode_rank":
        result["mode_rank"] = "FIRST_MODE_PASS"
    elif mutation == "residual":
        result["residual"] = 0.25
    else:
        result["euler_relative_error"] = 0.5
    result_path.write_text(json.dumps(result), encoding="utf-8")
    verdict = validate_archive(output, scope=scope, receipt=receipt, pytest_status="PASSED")
    assert verdict["archive_validation"] == "INVALID"


def test_g08_archive_validator_preserves_solver_exception(tmp_path):
    output = tmp_path / "result"
    output.mkdir()
    scope = {"id": "g08-tet10-before", "source": "a" * 40, "inputs": "b" * 64, "nodes": 117}
    receipt = {
        "scope": scope["id"],
        "source": scope["source"],
        "inputs_sha256": scope["inputs"],
        "resultant_ux": -1.0,
    }
    (output / "failure.json").write_text(
        json.dumps(
            {
                "scope": scope["id"],
                "source": scope["source"],
                "inputs_sha256": scope["inputs"],
                "exception_type": "NumericalConvergenceError",
                "message": "synthetic failure",
            }
        ),
        encoding="utf-8",
    )
    verdict = validate_archive(output, scope=scope, receipt=receipt, pytest_status="FAILED")
    assert verdict["archive_validation"] == "FAILURE_ARCHIVED"
    assert verdict["preload_status"] == "NOT_REPORTED"
    assert verdict["first_mode_status"] == "FIRST_MODE_NOT_ESTABLISHED"
