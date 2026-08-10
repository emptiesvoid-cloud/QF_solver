"""Input-deck checks for the MITC4 conical Code_Aster correlation."""

from __future__ import annotations

from solveur.verification.code_aster_mitc4_conical_cutout import (
    _qf_consistent_translation_loads,
    code_aster_quad_mesh,
    code_aster_static_comm,
)
from solveur.verification.mitc4_conical_cutout import build_conical_cutout_model


def test_code_aster_conical_decks_preserve_quad_mesh_and_qf_load_vector() -> None:
    model, _ = build_conical_cutout_model(4, 16)
    mesh = code_aster_quad_mesh(model)
    command = code_aster_static_comm(model)

    assert "QUAD4" in mesh
    assert "GROUP_NO\nFIXED" in mesh
    assert mesh.count("M") >= len(model.elements)
    assert 'MODELISATION="DKT"' in command
    assert "REAC_NODA" in command
    assert command.count("_F(NOEUD=") == len(_qf_consistent_translation_loads(model))
