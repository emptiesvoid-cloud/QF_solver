from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from solveur.verification.tet4_structured_petsc import _read_displacements


def test_read_petsc_probe_npz_displacements(tmp_path: Path) -> None:
    output = tmp_path / "probe"
    output.mkdir()
    expected = np.arange(12, dtype=float).reshape((4, 3))
    np.savez(output / "displacements.npz", displacements=expected)
    values = _read_displacements(output, 4)
    assert np.array_equal(values, expected)


def test_probe_summary_contract_is_json_serializable() -> None:
    data = {"status": "PASS", "relative_error": 0.009, "checks": {"residual": True}}
    assert json.loads(json.dumps(data))["status"] == "PASS"
