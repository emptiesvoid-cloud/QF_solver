from __future__ import annotations

from types import SimpleNamespace

from solveur.verification.calculix_tet10 import write_calculix_tet10_input


def test_calculix_tet10_writer_preserves_quadratic_connectivity(tmp_path) -> None:
    model = SimpleNamespace(
        nodes=[[0.0, 0.0, 0.0]] * 10,
        elements=[SimpleNamespace(nodes=tuple(range(10)), material="solid")],
        materials={"solid": {"E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[SimpleNamespace(node=0, dofs=("UX", "UY", "UZ"))],
        loads=[SimpleNamespace(node=1, dof="UZ", value=-10.0)],
    )

    text = write_calculix_tet10_input(tmp_path / "case.inp", model).read_text(encoding="ascii")

    assert "*ELEMENT,TYPE=C3D10,ELSET=EALL" in text
    assert "1,1,2,3,4,5,6,7,8,9,10" in text
    assert "1,1,1,0." in text
    assert "2,3,-10" in text


def test_calculix_tet10_writer_normalizes_roundoff_coordinates(tmp_path) -> None:
    nodes = [[0.0, 0.0, 0.0] for _ in range(10)]
    nodes[8] = [3.0, -4.724167021116776e-15, -0.5]
    model = SimpleNamespace(
        nodes=nodes,
        elements=[SimpleNamespace(nodes=tuple(range(10)), material="solid")],
        materials={"solid": {"E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[],
        loads=[SimpleNamespace(node=8, dof="UY", value=5.0e-15)],
    )

    text = write_calculix_tet10_input(tmp_path / "case.inp", model).read_text(encoding="ascii")

    assert "9,3,0,-0.5" in text
    assert "9,2,5e-15" not in text
