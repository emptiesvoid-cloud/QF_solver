from pathlib import Path

import numpy as np

from solveur.verification.calculix_tl_structural import (
    parse_calculix_buckling_factors,
    parse_calculix_element_stresses,
    write_buckling_input,
    write_stress_patch_input,
)
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def test_calculix_structural_writers(tmp_path: Path) -> None:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 1.0, 0.75)
    stress = write_stress_patch_input(tmp_path / "stress.inp", nodes, elements, np.eye(3))
    buckling = write_buckling_input(tmp_path / "buckling.inp", nodes, elements)
    assert "*EL PRINT" in stress.read_text(encoding="ascii")
    assert "*BUCKLE" in buckling.read_text(encoding="ascii")


def test_calculix_structural_parsers(tmp_path: Path) -> None:
    stress = tmp_path / "stress.dat"
    stress.write_text(
        " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set EALL and time  1.0\n"
        " 1 1 10 20 30 4 5 6\n\n",
        encoding="ascii",
    )
    factors = tmp_path / "buckling.dat"
    factors.write_text(
        " B U C K L I N G   F A C T O R   O U T P U T\n\n"
        " MODE NO BUCKLING\n FACTOR\n\n 1 8.0e2\n 2 9.0e2\n\n",
        encoding="ascii",
    )
    assert parse_calculix_element_stresses(stress).shape == (1, 6)
    assert parse_calculix_buckling_factors(factors) == [800.0, 900.0]
