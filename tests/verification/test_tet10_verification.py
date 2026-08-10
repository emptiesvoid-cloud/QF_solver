from solveur.verification.tet10 import Tet10MechanicalVerifier


def test_tet10_mechanical_verification_campaign_passes():
    report = Tet10MechanicalVerifier().run()
    assert report["status"] == "PASS"
    assert len(report["checks"]) == 8
    assert all(check["status"] == "PASS" for check in report["checks"])
    assert {check["name"] for check in report["checks"]} >= {
        "consistent mass total",
        "affine strain patch",
        "affine analytical energy",
        "quadratic field recovery",
        "closed-form one-dof edge eigenvalue",
    }
