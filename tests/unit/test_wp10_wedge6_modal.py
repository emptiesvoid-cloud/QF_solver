"""Targeted WP10 tests for the experimental WEDGE6 modal route."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.errors import MeshValidationError
from solveur.verification.wedge6_modal import (
    CATALOG,
    _aster_comm,
    _aster_mesh,
    mass_metrics,
    modal_metrics,
    modal_model,
    prism_chain,
    refinement_metrics,
)
from solveur.verification.v2 import load_cases


def test_wp10_catalog_declares_the_independent_modal_cases() -> None:
    cases = load_cases(CATALOG)
    assert len(cases) == 16
    assert {case.case_id for case in cases} >= {
        "WP10-MASS-CONSERVATION",
        "WP10-MODAL-SINGLE",
        "WP10-MODAL-MULTI",
        "WP10-MODAL-REFINEMENT",
        "WP10-MODAL-REPLAY",
        "WP10-MODAL-CODE-ASTER",
        "WP10-MODAL-NO-DENSITY",
    }
    assert all(case.requirement_id == "027-REQ-011" for case in cases)
    assert all(case.element == "WEDGE6" and case.analysis == "modal" for case in cases)


def test_consistent_mass_meets_wp10_invariants() -> None:
    metrics = mass_metrics()
    assert metrics["mass_shape"] == [18, 18]
    assert metrics["symmetry_error"] <= 1.0e-14
    assert metrics["positive_definite"] is True
    assert metrics["mass_conservation_error"] <= 1.0e-10
    assert metrics["reference_mass_relative_difference"] <= 1.0e-12
    assert metrics["density_scaling_pass"] is True
    assert metrics["geometry_scaling_pass"] is True
    assert metrics["distorted_positive"] is True


@pytest.mark.parametrize("segments", (1, 3))
def test_common_modal_route_has_finite_positive_deterministic_modes(segments: int) -> None:
    metrics = modal_metrics(segments)
    assert metrics["status"] == "PASS"
    assert metrics["frequency_count"] == 6
    assert metrics["finite_frequencies"] is True
    assert metrics["positive_frequencies"] is True
    assert metrics["finite_modes"] is True
    assert metrics["mode_norms_finite"] is True
    assert metrics["max_relative_residual"] <= 1.0e-7
    assert metrics["mass_orthogonality_error"] <= 1.0e-12
    assert metrics["deterministic_frequencies"] is True
    assert metrics["deterministic_modes"] is True


def test_distorted_modal_case_and_refinement_are_reported_without_monotonic_claim() -> None:
    transform = np.asarray(((1.0, 0.12, 0.0), (0.0, 1.0, 0.08), (0.0, 0.0, 1.0)))
    distorted = modal_metrics(3, transform=transform)
    refinement = refinement_metrics()
    assert distorted["status"] == "PASS"
    assert distorted["finite_modes"] is True
    assert distorted["max_relative_residual"] <= 1.0e-7
    assert len(refinement["levels"]) == 4
    assert refinement["finite"] is True
    assert refinement["trend_reported_without_monotonicity_claim"] is True


def test_modal_route_fails_closed_without_positive_density() -> None:
    with pytest.raises(MeshValidationError, match="requires positive density"):
        from solveur.core.router import AnalysisRouter

        AnalysisRouter().solve(modal_model(density=0.0))


def test_code_aster_modal_deck_uses_the_declared_penta6_contract() -> None:
    nodes, elements = prism_chain()
    mesh = _aster_mesh(nodes, elements)
    comm = _aster_comm()
    assert "PENTA6" in mesh
    assert "N1 N2 N3 N4 N5 N6" in mesh
    assert 'OPTION="MASS_MECA"' in comm
    assert 'OPTION="PLUS_PETITE"' in comm
    assert 'NMAX_FREQ=6' in comm
    assert "VERI_MODE" in comm
