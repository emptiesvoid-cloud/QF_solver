from __future__ import annotations

import hashlib
import json

import numpy as np

from scripts import run_wp08_area_supported_m4_slip_forensic_r2 as runner


def test_sparse_basis_encoding_reconstructs_the_exact_float64_vector() -> None:
    vector = np.asarray([0.0, 1.0, 0.0, -0.25, 0.0], dtype=np.float64)

    encoded = runner._sparse_vector(vector)
    reconstructed = np.zeros(encoded["length"], dtype=np.float64)
    reconstructed[encoded["indices"]] = encoded["values"]

    assert np.array_equal(reconstructed, vector)
    assert encoded["dense_little_endian_sha256"] == hashlib.sha256(
        np.asarray(vector, dtype="<f8").tobytes()
    ).hexdigest()


def test_nested_solver_error_preserves_optimizer_and_contact_residuals() -> None:
    basis = np.zeros(1200, dtype=np.float64)
    basis[[4, 1150]] = [1.0, -1.0]
    error = RuntimeError("root failed")
    error.diagnostics = {
        "optimizer_status": 3,
        "optimizer_message": "xtol termination",
        "optimizer_nfev": 500,
        "contact_residuals": [
            {"contact": 17, "residual_norm": 1.5e-7, "scaled_residual_norm": 1.1e-8}
        ],
        "tangential_basis": [basis],
    }

    record = runner._exception_record(error)
    encoded = json.dumps(record, allow_nan=False)
    restored = json.loads(encoded)
    diagnostics = restored["diagnostics"]

    assert diagnostics["optimizer_status"] == 3
    assert diagnostics["optimizer_nfev"] == 500
    assert diagnostics["contact_residuals"][0]["contact"] == 17
    sparse = diagnostics["tangential_basis"][0]
    assert sparse["encoding"] == "exact_sparse_float64"
    assert sparse["indices"] == [4, 1150]
    assert sparse["values"] == [1.0, -1.0]


def test_oversized_numeric_vectors_are_summarized_with_a_reproducible_hash() -> None:
    values = np.linspace(-1.0, 1.0, runner.MAX_INLINE_VALUES + 1, dtype=np.float64)

    summary = runner._json_safe(values)

    assert summary["encoding"] == "bounded_numeric_array_summary"
    assert summary["shape"] == [runner.MAX_INLINE_VALUES + 1]
    assert summary["little_endian_float64_sha256"] == hashlib.sha256(
        np.asarray(values, dtype="<f8").tobytes()
    ).hexdigest()


def test_nonfinite_diagnostic_values_remain_explicit() -> None:
    safe = runner._json_safe({"residual": float("inf"), "candidate": [float("nan")]})

    assert safe == {"residual": "NONFINITE:inf", "candidate": ["NONFINITE:nan"]}


def test_frozen_execution_allows_only_its_own_untracked_evidence() -> None:
    allowed = "?? " + runner.OUTPUT_REL.as_posix() + "/contract.json"
    unrelated = "?? qualification/unrelated/result.json"

    assert runner._git_status_is_only_frozen_output(allowed)
    assert not runner._git_status_is_only_frozen_output(allowed + "\n" + unrelated)
    assert not runner._git_status_is_only_frozen_output(" M scripts/runner.py")
