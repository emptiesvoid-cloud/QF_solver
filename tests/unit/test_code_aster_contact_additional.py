"""Deck and geometry tests for the added Code_Aster contact correlation."""

import numpy as np

from solveur.verification.code_aster_contact_additional import (
    CodeAsterAdditionalContactCampaign,
    _aster_input,
    _gaps,
)
from solveur.verification.contact_additional_oracle import calculix_probe_deck
from solveur.verification.contact_additional_models import (
    _deformable_tet4_two_slaves,
    _dual_stop_corner,
    _faceted_ramp_patch,
)


def test_additional_contact_campaign_has_ten_load_points() -> None:
    assert np.allclose(
        CodeAsterAdditionalContactCampaign.load_factors,
        np.linspace(0.1, 1.0, 10),
    )


def test_requested_refined_grid_contains_nearly_ten_thousand_tet4() -> None:
    model = _deformable_tet4_two_slaves(nx=26, ny=8, nz=8)

    assert len(model["elements"]) == 9_984


def test_dual_stop_deck_contains_two_unilateral_constraints() -> None:
    mesh, commands = _aster_input("dual_stop_corner", _dual_stop_corner())

    assert "POI1" in mesh
    assert commands.count('FORMULATION="LIAISON_UNIL"') == 1
    assert 'NOM_CMP="DX"' in commands
    assert 'NOM_CMP="DZ"' in commands
    assert "NOMBRE=10" in commands


def test_faceted_ramp_deck_contains_three_normal_constraints() -> None:
    data = _faceted_ramp_patch()
    mesh, commands = _aster_input("faceted_ramp_patch", data)

    assert "P1 P2 P3" in mesh
    assert commands.count("COEF_IMPO=") == 3
    assert commands.count('NOM_CMP="DZ"') == 3


def test_deformable_tet4_deck_preserves_mesh_and_two_slaves() -> None:
    data = _deformable_tet4_two_slaves()
    mesh, commands = _aster_input("deformable_tet4_two_slaves", data)

    assert mesh.count("\nE") >= 576
    assert 'MODELISATION="3D"' in commands
    assert commands.count('NOM_CMP="DX"') == 2


def test_gap_reconstruction_matches_final_closed_states() -> None:
    dual = _gaps(
        "dual_stop_corner",
        _dual_stop_corner(),
        np.asarray([[-0.1, -0.1]]),
    )
    tet4 = _gaps(
        "deformable_tet4_two_slaves",
        _deformable_tet4_two_slaves(),
        np.asarray([[-0.1, -0.1]]),
    )

    assert np.allclose(dual, 0.0)
    assert np.allclose(tet4, 0.0)


def test_calculix_probe_uses_same_tet4_mesh_and_ten_percent_load() -> None:
    deck = calculix_probe_deck(_deformable_tet4_two_slaves())

    assert "*ELEMENT,TYPE=C3D4,ELSET=EALL" in deck
    assert deck.count("\n576,") == 1
    assert "SLAVE_1,1,-200." in deck
    assert "SLAVE_2,1,-200." in deck


def test_report_describes_first_sample_closure_on_refined_mesh() -> None:
    cases = [
        {
            "id": identifier,
            "displacement_curve_error": 0.0,
            "gap_curve_error": 0.0,
            "code_aster_gaps_m": [[0.0]],
            "diagnostics": {},
        }
        for identifier in ("dual_stop_corner", "faceted_ramp_patch")
    ]
    cases.append(
        {
            "id": "deformable_tet4_two_slaves",
            "displacement_curve_error": 1.0e-14,
            "gap_curve_error": 1.0e-14,
            "code_aster_gaps_m": [[0.0, 0.0]],
            "diagnostics": {"contacts_closed_at_first_sample": True},
        }
    )

    report = CodeAsterAdditionalContactCampaign._report(
        {
            "study_id": "VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010",
            "status": "PASS_EXTERNAL_CORRELATION",
            "cases": cases,
        }
    )

    assert "deja fermes au premier palier" in report
    assert "probe CalculiX avant contact n'est donc pas applicable" in report
    assert "Code_Aster ferme un esclave plus tot" not in report
