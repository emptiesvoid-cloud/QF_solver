"""Synthetic serialization checks for WP-D01 diagnostic operands; no FEM route."""

from __future__ import annotations

import base64
import hashlib
import json

import numpy as np
from scipy.sparse import csr_matrix

from experiments.wp_d01_cg_damping_evidence import (
    _numeric_array_snapshot,
    projected_damping_evidence,
    source_operator_evidence,
)


def test_numeric_array_snapshot_roundtrips_exact_dtype_shape_and_bytes() -> None:
    source = np.asarray([[1.25, -2.5], [3.75, 4.0]], dtype=np.float64)
    snapshot = _numeric_array_snapshot(source)
    raw = base64.b64decode(snapshot["raw_bytes_base64"])
    restored = np.frombuffer(raw, dtype=np.dtype(snapshot["dtype"])).reshape(snapshot["shape"])

    np.testing.assert_array_equal(restored, source)
    identity = json.dumps(
        {"dtype": source.dtype.str, "shape": list(source.shape), "order": "C"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    assert snapshot["raw_representation_sha256"] == hashlib.sha256(identity + b"\0" + raw).hexdigest()


def test_source_and_projected_damping_evidence_preserve_synthetic_operands() -> None:
    mass = csr_matrix(np.eye(2))
    stiffness = csr_matrix(np.diag([4.0, 9.0]))
    alpha, beta = 0.2, 2.0e-5
    damping = (alpha * mass + beta * stiffness).tocsr()
    modes = np.eye(2, dtype=np.float64)
    projected_mass = np.eye(2)
    projected_stiffness = np.diag([4.0, 9.0])
    frequencies = [0.0, 1.0]
    response = np.asarray([1.0 + 0.25j, -0.5j], dtype=np.complex128)

    source = json.loads(
        source_operator_evidence(
            mesh_id="SYNTHETIC",
            elements=0,
            free_dofs=2,
            source_sha="a" * 40,
            operator_identity="synthetic-operator",
            alpha_per_s=alpha,
            beta_s=beta,
            mass=mass,
            stiffness=stiffness,
            damping=damping,
            frequencies_hz=frequencies,
            reduced_force=np.ones(2, dtype=np.complex128),
            direct_responses=[response, response],
            direct_relative_residuals=[0.0, 1.0e-14],
        )
    )
    projected = json.loads(
        projected_damping_evidence(
            mesh_id="SYNTHETIC",
            mode_count=2,
            source_sha="a" * 40,
            basis_identity="synthetic-basis",
            operator_identity="synthetic-operator",
            basis_diagnostics={"status": "synthetic"},
            modal_clusters_zero_based=((0,), (1,)),
            modes=modes,
            eigenvalues_rad2_s2=np.asarray([4.0, 9.0]),
            mass=mass,
            damping=damping,
            projected_mass=projected_mass,
            projected_stiffness=projected_stiffness,
            alpha_per_s=alpha,
            beta_s=beta,
            symmetry_tolerance=1.0e-12,
        )
    )

    assert source["exact_numeric_arrays"]["frequencies_hz"]["values"] == frequencies
    assert source["operators"]["C_used_by_experiment"]["stored_representation_sha256"]
    assert projected["acceptance_verdict"] == "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTANCE_OVERRIDE"
    assert projected["projection_expression"] == "Phi.T @ (C @ Phi), with C=alpha*M+beta*K"
    assert projected["exact_numeric_arrays"]["projected_damping"]["shape"] == [2, 2]
