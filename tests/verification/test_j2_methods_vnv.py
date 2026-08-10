import pytest

from solveur.verification.j2_methods import J2NonlinearMethodsCampaign


@pytest.mark.benchmark
def test_j2_nonlinear_methods_campaign_characterizes_all_methods(tmp_path):
    summary = J2NonlinearMethodsCampaign(tmp_path).run()

    assert summary["status"] == "PASS_CHARACTERIZATION"
    assert summary["methods"]["newton_raphson"]["status"] == "CONVERGED"
    assert summary["methods"]["newton_line_search"]["status"] == "CONVERGED"
    assert summary["methods"]["modified_newton"]["status"] == "NON_CONVERGED"
    errors = summary["full_newton_line_search_relative_errors"]
    assert errors["axial_displacement"] < 1.0e-8
    assert errors["stress"] < 1.0e-8
    assert errors["equivalent_plastic_strain"] < 1.0e-8
    assert errors["displacement"] > 0.1
    assert (tmp_path / "report.md").is_file()
