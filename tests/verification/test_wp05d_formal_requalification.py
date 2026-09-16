"""Targeted tests for the WP05-D formal observable reference boundary."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.wp05_cd_structural_harness import MESH_LEVELS, build_mesh
from scripts.wp05d_hex20_independent_reference import evaluate_raw


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_CONTRACT = ROOT / "qualification" / "0_2_9" / "wp05_cd_stress_window_remediation_candidate.json"
REFERENCE_SOURCE = ROOT / "scripts" / "wp05d_hex20_independent_reference.py"


def test_independent_reference_has_no_production_or_candidate_import() -> None:
    source = REFERENCE_SOURCE.read_text(encoding="utf-8")
    assert "from solveur" not in source
    assert "import solveur" not in source
    assert "wp05_stress_window_candidate" not in source


def test_independent_reference_zero_field_has_exact_window_volume(tmp_path: Path) -> None:
    contract = json.loads(CANDIDATE_CONTRACT.read_text(encoding="utf-8"))
    values = []
    volumes = []
    for level in MESH_LEVELS:
        mesh = build_mesh("HEX20", level)
        raw_path = tmp_path / f"{level.name}.npz"
        np.savez(
            raw_path,
            coordinates=np.asarray(mesh.coordinates, dtype=float),
            connectivity=np.asarray(mesh.connectivity, dtype=int),
            displacement=np.zeros(mesh.dofs, dtype=float),
        )
        result = evaluate_raw(raw_path, CANDIDATE_CONTRACT)
        assert result["status"] == "PASS"
        values.append(result["representative_sigma_xx"])
        volumes.append(result["reference_volume"])
    np.testing.assert_allclose(values, 0.0, rtol=0.0, atol=1.0e-10)
    np.testing.assert_allclose(volumes, 0.03, rtol=0.0, atol=1.0e-14)
    assert contract["observable"]["expected_reference_volume"] == 0.03
