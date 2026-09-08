from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from qf_solver import read_inp, solve_model
from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.mesh.validation import MeshValidator


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "qualification" / "0_2_8" / "wp13_05_inp_fixtures"


def _vector(audit: object, name: str) -> np.ndarray:
    values = getattr(audit, "vectors")
    row = next(item for item in values if item["name"] == name)
    result = np.zeros(int(row["size"]), dtype=float)
    for entry in row["nonzero_entries"]:
        result[int(entry["index"])] = float(entry["value"])
    return result


@pytest.mark.parametrize(
    ("fixture", "families"),
    [
        ("tet4_simple.inp", {"TET4": 1}),
        ("wedge6_simple.inp", {"WEDGE6": 1}),
        ("hex8_simple.inp", {"HEX8": 1}),
        ("mixed_tet4_wedge6_hex8.inp", {"TET4": 1, "WEDGE6": 1, "HEX8": 1}),
        ("mixed_multimaterial.inp", {"TET4": 1, "WEDGE6": 1, "HEX8": 1}),
    ],
)
def test_bounded_inp_fixtures_import_and_solve(fixture: str, families: dict[str, int]) -> None:
    imported = read_inp(FIXTURES / fixture)
    assert imported.report.elements_by_family == families
    assert imported.report.analysis == "linear_static"
    assert imported.report.units_policy == "USER_CONSISTENT / NO_AUTOMATIC_CONVERSION"
    assert MeshValidator().validate(imported.model).status == "PASS"
    result = solve_model(imported.model, enforce_policy=False)
    assert result.status == "PASS"
    assert result.audit is not None
    assert result.audit.equilibrium["free_relative_residual"] < 1.0e-10
    assert result.audit.equilibrium["linear_energy_identity_relative_error"] < 1.0e-10


def test_mixed_multimaterial_maps_regions_sets_and_is_numerically_transparent() -> None:
    imported = read_inp(FIXTURES / "mixed_multimaterial.inp")
    assert imported.node_sets["FIX"] == (8, 9, 10, 11)
    assert imported.node_sets["LOAD"] == (7,)
    assert imported.element_sets == {"EHEX": (3,), "ETET": (1,), "EWEDGE": (2,)}
    assert [element.material for element in imported.model.elements] == ["MAT_TET", "MAT_WEDGE", "MAT_HEX"]
    assert [element.type for element in imported.model.elements] == ["TET4", "WEDGE6", "HEX8"]

    native = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [-1.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0],
            [-1.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0],
            [0.0, 1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, 0.0, -1.0],
        ],
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 6], "material": "MAT_TET"},
            {"type": "WEDGE6", "nodes": [0, 2, 1, 3, 5, 4], "material": "MAT_WEDGE"},
            {"type": "HEX8", "nodes": [0, 3, 4, 1, 7, 10, 9, 8], "material": "MAT_HEX"},
        ],
        materials={
            "MAT_TET": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3},
            "MAT_WEDGE": {"type": "isotropic_3d", "E": 120.0e9, "nu": 0.3},
            "MAT_HEX": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3},
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(7, 11)],
        loads=[{"node": 6, "dof": "UZ", "value": 1000.0}],
        analysis={"type": "linear_static", "method": "direct"},
    )
    imported_result = solve_model(imported.model, enforce_policy=False)
    native_result = solve_model(native, enforce_policy=False)
    assert np.array_equal(imported.model.nodes, native.nodes)
    assert np.allclose(imported_result.displacements, native_result.displacements, rtol=1.0e-12, atol=0.0)
    assert imported_result.audit is not None and native_result.audit is not None
    assert np.allclose(_vector(imported_result.audit, "reactions"), _vector(native_result.audit, "reactions"), rtol=1.0e-12, atol=0.0)
    assert np.isclose(
        imported_result.audit.equilibrium["force_balance_relative_error"],
        native_result.audit.equilibrium["force_balance_relative_error"],
        rtol=1.0e-12,
        atol=1.0e-15,
    )


def test_import_is_deterministic_and_public_api_is_single_entrypoint() -> None:
    first = read_inp(FIXTURES / "mixed_tet4_wedge6_hex8.inp")
    second = read_inp(FIXTURES / "mixed_tet4_wedge6_hex8.inp")
    assert first.report.to_dict() == second.report.to_dict()
    assert first.model.nodes.tolist() == second.model.nodes.tolist()
    assert first.model.elements == second.model.elements


def test_negative_cases_fail_closed() -> None:
    base = (FIXTURES / "tet4_simple.inp").read_text(encoding="utf-8")
    cases = {
        "unknown_element_type": base.replace("TYPE=C3D4", "TYPE=C3D10"),
        "malformed_node": base.replace("1, 0., 0., 0.", "1, 0., 0."),
        "malformed_connectivity": base.replace("1, 1, 2, 3, 4", "1, 1, 2, 3"),
        "duplicate_ids": base.replace("4, 0., 0., 1.", "1, 0., 0., 1."),
        "missing_material": base.replace("MATERIAL=STEEL", "MATERIAL=MISSING"),
        "invalid_elset": base.replace("ELSET=EALL, MATERIAL=STEEL", "ELSET=NO_SUCH_SET, MATERIAL=STEEL"),
        "invalid_nset": base.replace("FIX, 1, 3, 0.", "NO_SUCH_SET, 1, 3, 0."),
        "unsupported_physical_keyword": base.replace("*CLOAD", "*DLOAD"),
        "invalid_boundary_dof": base.replace("FIX, 1, 3, 0.", "FIX, 1, 4, 0."),
        "invalid_material_property": base.replace("210000000000., 0.3", "210000000000., 0.6"),
    }
    for case_id, text in cases.items():
        with pytest.raises((InputValidationError, MeshValidationError), match=r".+") as captured:
            read_inp_from_text(text)
        assert captured.value.args, case_id


def test_inverted_tet_is_rejected_without_silent_repair() -> None:
    text = (FIXTURES / "tet4_simple.inp").read_text(encoding="utf-8").replace("1, 1, 2, 3, 4", "1, 1, 3, 2, 4")
    with pytest.raises(MeshValidationError, match="orientation|volume"):
        read_inp_from_text(text)


def read_inp_from_text(text: str):
    from solveur.io.inp_reader import InpModelImporter

    return InpModelImporter().from_text(text)
