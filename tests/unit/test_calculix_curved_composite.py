from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from solveur.verification.calculix_curved_composite import (
    build_curved_s8r_mesh,
    write_curved_calculix_input,
)


ROOT = Path(__file__).resolve().parents[2]


def test_curved_s8r_mesh_has_quadratic_edges_and_normalized_load_weights():
    mesh = build_curved_s8r_mesh(4, 2)

    assert len(mesh.elements) == 8
    assert all(len(element) == 8 for element in mesh.elements)
    assert mesh.corner_quads.shape == (8, 4)
    assert len(mesh.tip_nodes) == 5
    np.testing.assert_allclose(np.sum(mesh.tip_weights), 1.0, rtol=0.0, atol=1.0e-15)
    assert np.all(mesh.tip_weights > 0.0)
    assert len(set(node for element in mesh.elements for node in element)) == len(mesh.nodes)


def test_curved_calculix_input_contains_composite_orientation_and_balanced_loads(tmp_path):
    mesh = build_curved_s8r_mesh(4, 2)
    path = write_curved_calculix_input(tmp_path / "curved.inp", mesh)
    text = path.read_text(encoding="ascii")

    assert "*ELEMENT,TYPE=S8R,ELSET=EALL" in text
    assert "*SHELL SECTION,ELSET=EALL,COMPOSITE" in text
    assert "*ORIENTATION,NAME=ORIP0" in text
    assert "*ORIENTATION,NAME=ORIP90" in text
    assert "1.,0.,0.,0.,1.,0." in text
    assert "*ORIENTATION,NAME=ORIP45" not in text
    assert text.count("0.002,,LAMINA,ORIP0") == 2
    assert text.count("0.002,,LAMINA,ORIP90") == 2
    load_lines = text.split("*CLOAD\n", maxsplit=1)[1].split("*NODE FILE", maxsplit=1)[0]
    fx = sum(float(line.split(",")[2]) for line in load_lines.splitlines()[::2])
    fz = sum(float(line.split(",")[2]) for line in load_lines.splitlines()[1::2])
    np.testing.assert_allclose(fx, 1000.0, rtol=0.0, atol=1.0e-12)
    np.testing.assert_allclose(fz, -20.0, rtol=0.0, atol=1.0e-12)


def test_curved_calculix_input_preserves_one_ply_orientation_and_total_thickness(
    tmp_path,
):
    mesh = build_curved_s8r_mesh(2, 1)
    path = write_curved_calculix_input(tmp_path / "one_ply.inp", mesh, layup=(45.0,))
    text = path.read_text(encoding="ascii")

    assert "*ORIENTATION,NAME=ORIP45" in text
    assert "*ORIENTATION,NAME=ORIP0" not in text
    assert "0.008,,LAMINA,ORIP45" in text


def test_controlled_curved_calculix_evidence_is_complete() -> None:
    reference = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "calculix_curved_composite"
        / "reference"
    )
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((reference / "vnv_manifest.json").read_text(encoding="utf-8"))

    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert summary["open_anomaly"]["id"] == "ANOM-COMP-CURVED-ORIENTATION-001"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["rows"][-1]["vector_difference"] < 0.005
    for entry in manifest["files"]:
        artifact = reference / entry["path"]
        assert artifact.is_file(), entry["path"]
        assert artifact.stat().st_size == entry["size_bytes"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
