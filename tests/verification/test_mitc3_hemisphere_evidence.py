from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3" / "hemisphere_v1"
)


def test_controlled_mitc3_hemisphere_correlation_passes_declared_limits() -> None:
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS_EXTERNAL_CORRELATION"
    assert len(summary["levels"]) == 6
    assert summary["levels"][-1]["quarter_triangles"] == 2048
    assert summary["levels"][-1]["qf_reference_error"] < 0.01
    assert summary["levels"][-1]["probe_difference"] < 0.001
    assert summary["levels"][-1]["vector_difference"] < 0.002
    assert summary["final_increment"] < 0.003
    assert all(check["status"] == "PASS" for check in summary["checks"])


def test_controlled_mitc3_hemisphere_code_aster_figures_are_readable() -> None:
    paths = [
        EVIDENCE / "geometry_boundary_loads.png",
        EVIDENCE / "convergence_qf_code_aster.png",
        EVIDENCE / "level_32" / "fine_deformation_qf_code_aster.png",
        EVIDENCE / "level_32" / "code_aster_displacement_field.png",
    ]
    for path in paths:
        assert path.is_file()
        with Image.open(path) as image:
            assert image.width >= 1000
            assert image.height >= 800
            assert image.getbbox() is not None
