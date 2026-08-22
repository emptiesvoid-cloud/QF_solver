from solveur.verification.calculix_mitc3_curved_composite import (
    CalculixMitc3CurvedCompositeCorrelation,
    build_curved_s6_mesh,
    write_s6_input,
)


def test_curved_calculix_campaign_accepts_axial_load_case(tmp_path) -> None:
    campaign = CalculixMitc3CurvedCompositeCorrelation(tmp_path, load_case="axial")
    assert campaign.load_case == "axial"


def test_curved_s6_axial_input_has_no_transverse_load(tmp_path) -> None:
    path = write_s6_input(tmp_path / "axial.inp", build_curved_s6_mesh(2, 1), load_case="axial")
    loads = path.read_text(encoding="ascii").split("*CLOAD", 1)[1].split("*NODE FILE", 1)[0]
    assert any(line.split(",")[1:] == ["1", "500"] for line in loads.splitlines() if line)
    assert all(line.split(",")[2] == "0" for line in loads.splitlines() if line and ",3," in line)


def test_curved_s6_transverse_input_has_no_axial_load(tmp_path) -> None:
    path = write_s6_input(tmp_path / "transverse.inp", build_curved_s6_mesh(2, 1), load_case="transverse")
    loads = path.read_text(encoding="ascii").split("*CLOAD", 1)[1].split("*NODE FILE", 1)[0]
    assert all(line.split(",")[2] == "0" for line in loads.splitlines() if line and ",1," in line)
    assert any(line.split(",")[1:] == ["3", "-500"] for line in loads.splitlines() if line)
