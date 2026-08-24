from solveur.verification.hex8 import Hex8MechanicalVerifier


def test_hex8_mechanical_verification_campaign_passes() -> None:
    report = Hex8MechanicalVerifier().run()
    assert report["status"] == "PASS"
    assert len(report["checks"]) == 10
