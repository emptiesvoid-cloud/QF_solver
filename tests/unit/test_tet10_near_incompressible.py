from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.verification.tet10_near_incompressible import (
    bulk_to_shear_ratio,
    timoshenko_tip_displacement,
)


ROOT = Path(__file__).resolve().parents[2]


def test_near_incompressible_reference_is_well_ordered() -> None:
    assert timoshenko_tip_displacement(0.499) < timoshenko_tip_displacement(0.30) < 0.0
    assert bulk_to_shear_ratio(0.30) == pytest.approx(13.0 / 6.0)
    assert bulk_to_shear_ratio(0.499) > 400.0


def test_controlled_near_incompressible_characterization_passes() -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_near_incompressible" / "reference"
    summary = json.loads((reference / "summary.json").read_text(encoding="utf-8"))

    assert summary["study_id"] == "VNV-TET10-NEAR-INCOMPRESSIBLE-015"
    assert summary["status"] == "PASS_CHARACTERIZATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["families"]["TET4"]["levels"]) == 12
    assert len(summary["families"]["TET10"]["levels"]) == 12
    assert (reference / "tet10_near_incompressible.png").stat().st_size > 1000
