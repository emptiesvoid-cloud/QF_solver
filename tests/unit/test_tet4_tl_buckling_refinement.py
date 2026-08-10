import json
from pathlib import Path

import numpy as np

from solveur.verification.tet4_tl_buckling_refinement import _relative, _sample_edges
from solveur.verification.vnv_manifest import write_vnv_manifest


def test_refinement_probe_helpers() -> None:
    elements = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    edges = _sample_edges(elements, 100)
    assert edges.shape == (9, 2)
    assert _relative(95.0, 100.0) == 0.05


def test_vnv_manifest_uses_portable_repository_path(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")

    manifest_path = write_vnv_manifest(tmp_path, "VNV-PORTABLE-001")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source"]["repository"] == "."
