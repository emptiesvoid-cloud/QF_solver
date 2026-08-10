from mitc4.verification import MechanicalVerifier
from mitc4.locking import EnhancedShearLockingStudy
from mitc4.convergence import Mitc4StructuralConvergence
import pytest


def test_existing_mitc4_quick_verification_passes():
    results = MechanicalVerifier().run(include_benchmark=False)
    assert all(result.passed for result in results)


def test_reinforced_shear_locking_acceptance_on_reduced_matrix():
    campaign = EnhancedShearLockingStudy(
        meshes=((4, 1), (8, 2)),
        thickness_ratios=(1.0e-3, 1.0e-4),
        distortions=(0.0, 0.3),
    ).run()
    assert campaign.status == "PASS"
    assert all(check["status"] == "PASS" for check in campaign.checks)
    assert len(campaign.cases) == 16


def test_drilling_scale_has_a_stable_response_plateau():
    study = Mitc4StructuralConvergence.drilling_sensitivity()
    assert study["status"] == "PASS"
    assert study["selected_scale"] == 1.0e-4
    assert study["plateau_relative_change"] < 1.0e-2


@pytest.mark.benchmark
def test_full_reinforced_shear_locking_matrix_passes():
    campaign = EnhancedShearLockingStudy().run()
    assert campaign.status == "PASS"
    assert len(campaign.cases) == 160


@pytest.mark.benchmark
def test_structural_convergence_includes_cook_64_by_64_review():
    studies = Mitc4StructuralConvergence().run()
    assert set(studies) == {"cook", "scordelis", "pinched"}
    assert all(study.status == "PASS" for study in studies.values())
    assert len(studies["cook"].points) == 6
    assert all(len(studies[name].points) == 5 for name in ("scordelis", "pinched"))
    assert studies["cook"].review_status == "WARNING"
    assert studies["cook"].points[-1].relative_error == pytest.approx(0.045214471228735675)
