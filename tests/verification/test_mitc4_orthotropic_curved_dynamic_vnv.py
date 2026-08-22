from __future__ import annotations

from solveur.verification.mitc4_orthotropic_curved_dynamic import (
    Mitc4OrthotropicCurvedDynamicStudy,
)


def test_curved_one_ply_modal_newmark_harmonic_passes() -> None:
    summary = Mitc4OrthotropicCurvedDynamicStudy(
        mesh=(8, 4),
        steps_per_period=(20, 40, 80),
    ).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["geometry"]["type"] == "faceted cylindrical panel"
    assert all(summary["checks"].values())
    assert summary["modal"]["max_relative_residual"] <= 1.0e-7
    assert summary["harmonic"]["maximum_relative_error"] <= 1.0e-6
    assert summary["harmonic"]["zero_hz_static_relative_error"] <= 1.0e-9
