from solveur.verification.hex8_calculix import write_calculix_c3d8_input
from solveur.verification.hex8_tet_benchmark import _hex8_model


def test_hex8_calculix_deck_preserves_c3d8_connectivity_and_controls(tmp_path) -> None:
    path = write_calculix_c3d8_input(tmp_path / "hex8.inp", _hex8_model())
    text = path.read_text(encoding="ascii")
    assert "*ELEMENT,TYPE=C3D8,ELSET=EALL" in text
    assert "*BOUNDARY" in text
    assert "*CLOAD" in text
    assert "*NODE FILE,FREQUENCY=1" in text
