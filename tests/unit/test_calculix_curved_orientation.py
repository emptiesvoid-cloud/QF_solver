from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from solveur.verification.calculix_curved_composite import build_curved_s8r_mesh
from solveur.verification.calculix_curved_orientation import (
    CalculixCurvedOrientationCorrelation,
    tangent_orientations,
    write_tangent_oriented_input,
)


ROOT = Path(__file__).resolve().parents[2]


def test_tangent_orientations_are_right_handed_and_tangent() -> None:
    definitions = tangent_orientations(
        6,
        (0.0, 45.0, -45.0, 90.0),
        np.array([1.0, 1.0, 0.0]),
    )

    assert len(definitions) == 24
    for definition in definitions:
        frame = np.vstack(
            (definition.first_axis, definition.second_axis, definition.normal)
        )
        np.testing.assert_allclose(frame @ frame.T, np.eye(3), atol=1.0e-14)
        np.testing.assert_allclose(np.linalg.det(frame), 1.0, atol=1.0e-14)


def test_tangent_input_assigns_every_element_and_ply(tmp_path: Path) -> None:
    nx, ny = 4, 2
    mesh = build_curved_s8r_mesh(nx, ny)
    path = tmp_path / "curved.inp"
    orientations = write_tangent_oriented_input(
        path,
        mesh,
        nx=nx,
        ny=ny,
        angles=(0.0, 45.0, -45.0, 90.0),
        reference_direction=np.array([1.0, 1.0, 0.0]),
    )
    text = path.read_text(encoding="ascii")

    assert len(orientations) == 4 * ny
    assert text.count("*SHELL SECTION,ELSET=ROW") == ny
    assert text.count("*ORIENTATION,NAME=") == 4 * ny
    assert text.count(",,LAMINA,R") == 4 * ny
    assert max(len(line) for line in text.splitlines()) < 132


def test_controlled_curved_orientation_evidence_is_complete() -> None:
    reference = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "calculix_curved_orientation"
        / "reference"
    )
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == CalculixCurvedOrientationCorrelation.study_id
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["closed_anomaly"] == "ANOM-COMP-CURVED-ORIENTATION-001"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
