from __future__ import annotations

from solveur.verification.mitc4_newmark_broadband import Mitc4NewmarkBroadbandStudy


def test_reduced_wideband_newmark_campaign_passes() -> None:
    summary = Mitc4NewmarkBroadbandStudy(
        steps_per_period=(40, 80),
        period_count=1.0,
    ).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert set(summary["cases"]) == {"pulse", "chirp", "tabulated"}
