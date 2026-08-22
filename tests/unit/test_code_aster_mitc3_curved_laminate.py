from solveur.verification.code_aster_mitc3_curved_laminate import (
    CodeAsterMitc3CurvedLaminateCampaign,
    _command_text,
    _report,
)
from solveur.verification.mitc3_models import LAMINATE_MATERIAL


def test_curved_laminate_campaign_uses_projected_vector_and_layup() -> None:
    deck = _command_text(2, [0.5, 0.5])
    assert 'MODELISATION="DST"' in deck
    assert "DEFI_COMPOSITE" in deck
    assert "VECTEUR=(0.7, 1.0, 0.2)" in deck
    assert "ORIENTATION=90" in deck
    assert 'GROUP_NO="TIP_0000"' in deck


def test_curved_external_deck_uses_the_qf_laminate_constants() -> None:
    deck = _command_text(1, [1.0])
    assert f"E_L={LAMINATE_MATERIAL['E1']:.16g}" in deck
    assert f"E_T={LAMINATE_MATERIAL['E2']:.16g}" in deck
    assert f"G_LN={LAMINATE_MATERIAL['G13']:.16g}" in deck
    assert f"G_TN={LAMINATE_MATERIAL['G23']:.16g}" in deck
    assert f"RHO={LAMINATE_MATERIAL['density']:.16g}" in deck


def test_curved_laminate_campaign_exposes_independent_transverse_load_case() -> None:
    deck = _command_text(1, [1.0], load_case="transverse")

    assert 'FX=0' in deck
    assert 'FZ=-1000' in deck
    assert CodeAsterMitc3CurvedLaminateCampaign.load_cases == ("mixed", "transverse", "axial")


def test_curved_laminate_campaign_exposes_independent_axial_load_case() -> None:
    deck = _command_text(1, [1.0], load_case="axial")

    assert "FX=1000" in deck
    assert "FZ=0" in deck


def test_curved_laminate_campaign_rejects_single_level() -> None:
    try:
        CodeAsterMitc3CurvedLaminateCampaign("tmp", levels=((8, 4),))
    except ValueError as error:
        assert "at least two" in str(error)
    else:
        raise AssertionError("one level must be rejected")


def test_curved_laminate_campaign_allows_traceable_study_id() -> None:
    campaign = CodeAsterMitc3CurvedLaminateCampaign("tmp", study_id="VNV-TEST-029")

    assert campaign.study_id == "VNV-TEST-029"


def test_curved_laminate_campaign_can_target_one_load_family() -> None:
    campaign = CodeAsterMitc3CurvedLaminateCampaign("tmp", load_cases=("axial",))

    assert campaign.load_cases == ("axial",)


def test_curved_laminate_report_records_shared_material_contract() -> None:
    report = _report(
        {
            "study_id": "VNV-TEST-029",
            "status": "WARNING",
            "rows": [],
            "load_families": {"mixed": {}},
            "limitations": [],
        }
    )

    assert "LAMINATE_MATERIAL" in report
    assert f"{LAMINATE_MATERIAL['E1']:.6e} Pa" in report
    assert f"{LAMINATE_MATERIAL['density']:.6g} kg/m3" in report
