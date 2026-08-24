from scripts.run_code_aster_hex20_vnv import _mesh_text
from solveur.verification.hex20_calculix import _hex20_model


def test_code_aster_hex20_deck_uses_the_aster_edge_order() -> None:
    model = _hex20_model(load_value=1.0, young_modulus=210.0e6)
    root = [index for index, point in enumerate(model.nodes) if abs(float(point[0])) < 1.0e-12]
    mesh = _mesh_text(model.nodes, model.elements, root, 1)
    connectivity = next(line for line in mesh.splitlines() if line.startswith("M1 "))

    assert connectivity == (
        "M1 N1 N2 N3 N4 N5 N6 N7 N8 N9 N12 N14 N10 N11 N13 N15 N16 N17 N19 N20 N18"
    )
