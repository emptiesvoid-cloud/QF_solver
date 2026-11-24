from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from research.contact_r10_r16.m4_stick_capture import (
    CAPTURE_ARRAYS,
    CAPTURE_SCHEMA,
    tet4_internal_force,
    validate_capture_archive,
)


def _synthetic_archive(output: Path, *, missing_key: str | None = None, nonfinite: bool = False) -> str:
    output.mkdir(parents=True)
    nodes = np.zeros((81, 3), dtype=float)
    nodes[:4] = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    arrays = {
        "nodes": nodes,
        "tet4_connectivity": np.asarray([[0, 1, 2, 3]], dtype=np.int64),
        "displacements": np.zeros((1, 243), dtype=float),
        "loads": np.zeros((1, 243), dtype=float),
        "fixed_dof_indices": np.asarray([0], dtype=np.int64),
        "dof_map": np.arange(243, dtype=np.int64).reshape(81, 3),
        "contact_slave_nodes": np.arange(81, dtype=np.int64),
        "contact_normals": np.tile(np.asarray([[-1.0, 0.0, 0.0]]), (81, 1)),
        "contact_tangents": np.tile(np.asarray([[[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]]), (81, 1, 1)),
        "contact_pressures": np.ones((1, 81), dtype=float),
        "contact_gaps": np.zeros((1, 81), dtype=float),
        "contact_active": np.ones((1, 81), dtype=bool),
        "contact_states": np.ones((1, 81), dtype=np.int8),
        "slip_references_in": np.zeros((1, 81, 2), dtype=float),
        "slip_references_out": np.zeros((1, 81, 2), dtype=float),
        "tangential_displacements": np.zeros((1, 81, 2), dtype=float),
        "trial_tangential_forces": np.zeros((1, 81, 2), dtype=float),
        "tangential_forces": np.zeros((1, 81, 2), dtype=float),
        "friction_capacities": np.ones((1, 81), dtype=float),
        "coulomb_margins": -np.ones((1, 81), dtype=float),
        "gap_tolerances": np.full(81, 1e-10, dtype=float),
        "tangent_stiffnesses": np.full(81, 2.0, dtype=float),
    }
    if nonfinite:
        arrays["contact_pressures"][0, 0] = np.nan
    if missing_key:
        arrays.pop(missing_key)
    archive_path = output / "m4-stick-fields.npz"
    with archive_path.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest = {
        "schema": CAPTURE_SCHEMA,
        "contract_sha256": "c" * 64,
        "archive_sha256": digest,
        "captured_steps": 1,
        "contact_count": 81,
        "node_count": 81,
        "element_count": 1,
        "fixed_dof_count": 1,
    }
    (output / "capture-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest["contract_sha256"]


def test_tet4_stress_recovery_matches_affine_strain_resultant() -> None:
    nodes = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    connectivity = np.asarray([[0, 1, 2, 3]], dtype=np.int64)
    gradient = np.asarray(
        [[0.01, 0.02, -0.01], [-0.03, 0.005, 0.01], [0.0, 0.04, -0.02]], dtype=float
    )
    displacement_by_node = nodes @ gradient.T
    displacement = displacement_by_node.reshape(-1)
    young, poisson = 1.0e6, 0.3
    shear = young / (2 * (1 + poisson))
    lame = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    strain = 0.5 * (gradient + gradient.T)
    stress = lame * np.trace(strain) * np.eye(3) + 2 * shear * strain
    shape_gradients = np.asarray([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    expected = np.zeros((4, 3), dtype=float)
    for local, grad in enumerate(shape_gradients):
        expected[local] = (1.0 / 6.0) * stress @ grad
    actual = tet4_internal_force(
        nodes,
        connectivity,
        displacement,
        young_modulus_pa=young,
        poisson_ratio=poisson,
    ).reshape(4, 3)
    np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=2e-10)
    np.testing.assert_allclose(actual.sum(axis=0), 0.0, atol=2e-10)


def test_capture_archive_validates_complete_synthetic_fields(tmp_path: Path) -> None:
    contract_sha = _synthetic_archive(tmp_path / "valid")
    result = validate_capture_archive(tmp_path / "valid", contract_sha256=contract_sha)
    assert result["captured_steps"] == 1
    assert result["contact_count"] == 81
    assert result["node_count"] == 81


@pytest.mark.parametrize("invalid", ["missing_key", "bad_digest", "nonfinite"])
def test_capture_archive_rejects_incomplete_or_corrupt_fields(tmp_path: Path, invalid: str) -> None:
    kwargs = {"missing_key": "contact_pressures"} if invalid == "missing_key" else {"nonfinite": invalid == "nonfinite"}
    contract_sha = _synthetic_archive(tmp_path / "invalid", **kwargs)
    if invalid == "bad_digest":
        with (tmp_path / "invalid" / "capture-manifest.json").open("r+", encoding="utf-8") as stream:
            manifest = json.load(stream)
            manifest["archive_sha256"] = "0" * 64
            stream.seek(0)
            json.dump(manifest, stream)
            stream.truncate()
    with pytest.raises(ValueError):
        validate_capture_archive(tmp_path / "invalid", contract_sha256=contract_sha)


def test_capture_schema_declares_all_fields() -> None:
    assert "displacements" in CAPTURE_ARRAYS
    assert "contact_pressures" in CAPTURE_ARRAYS
    assert "coulomb_margins" in CAPTURE_ARRAYS
