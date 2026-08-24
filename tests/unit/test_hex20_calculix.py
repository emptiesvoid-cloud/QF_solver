from solveur.verification.hex20_calculix import _hex20_model, write_calculix_c3d20_input


def test_hex20_calculix_deck_preserves_c3d20_connectivity_and_boundary_data(tmp_path) -> None:
    model = _hex20_model(load_value=1.0, young_modulus=210.0e6)
    deck = write_calculix_c3d20_input(tmp_path / "hex20.inp", model)
    content = deck.read_text(encoding="ascii")

    assert "*ELEMENT,TYPE=C3D20,ELSET=EALL" in content
    element_lines = content.split("*ELEMENT,TYPE=C3D20,ELSET=EALL\n", 1)[1].split("*SOLID SECTION", 1)[0].strip().splitlines()
    assert len(element_lines) == 2
    assert len(element_lines[0].split(",")) == 16
    assert len(element_lines[1].split(",")) == 5
    assert element_lines[0].startswith("1,")
    assert element_lines[0].split(",")[1:] == [str(value) for value in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 14, 10, 17, 19, 20)]
    assert element_lines[1].split(",") == ["18", "11", "13", "15", "16"]
    assert content.count("\n") >= 20
    assert "*BOUNDARY" in content
    assert "*CLOAD" in content
