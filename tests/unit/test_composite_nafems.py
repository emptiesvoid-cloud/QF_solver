from __future__ import annotations

from solveur.verification.composite_nafems import (
    MESHES,
    NAFEMS_UZ_M,
    code_aster_commands,
    code_aster_mesh,
    solve_qf_nafems_case,
)


def test_nafems_mesh_sequence_reaches_five_thousand_elements() -> None:
    assert MESHES == ((10, 2), (20, 4), (40, 8), (80, 16), (160, 32))
    assert MESHES[-1][0] * MESHES[-1][1] == 5120


def test_nafems_qf_coarse_mesh_matches_published_displacement() -> None:
    row, _, _ = solve_qf_nafems_case(10, 2)
    assert abs(row["qf_uz_e_m"] - NAFEMS_UZ_M) / abs(NAFEMS_UZ_M) < 0.02
    assert row["qf_free_relative_residual"] < 1.0e-8


def test_code_aster_nafems_inputs_preserve_groups_and_seven_layers() -> None:
    mesh = code_aster_mesh(10, 2)
    commands = code_aster_commands("case")
    assert mesh.count("GROUP_NO") == 6
    assert "MODELISATION=\"DST\"" in commands
    assert "DEFI_COMPOSITE" in commands
    assert commands.count("_F(EPAIS=") == 7
    assert "G_LN=3.0e9" in commands
