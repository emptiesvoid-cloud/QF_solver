"""Deck-level tests for the complex MITC4/CalculiX external correlation."""

from __future__ import annotations

import numpy as np

from solveur.core.assembler import GlobalAssembler
from solveur.verification.calculix_mitc4_conical_cutout import (
    _qf_consistent_translation_loads,
    write_calculix_conical_cutout_input,
)
from solveur.verification.mitc4_conical_cutout import build_conical_cutout_model


def test_calculix_s4_deck_preserves_the_qf_mesh_and_consistent_pressure_vector(tmp_path) -> None:
    model, _ = build_conical_cutout_model(4, 16)
    deck = write_calculix_conical_cutout_input(tmp_path / "panel.inp", model).read_text(encoding="ascii")
    assert "*ELEMENT,TYPE=S4,ELSET=EALL" in deck
    assert "*CLOAD" in deck
    assert "*DLOAD" not in deck
    assert "*NODE PRINT,NSET=FIXED,TOTALS=YES\nRF" in deck
    assert deck.count("*BOUNDARY") == 1
    assert str(model.node_count) in deck


def test_transferred_calculix_cload_vector_equals_qf_pressure_resultant() -> None:
    model, _ = build_conical_cutout_model(4, 16)
    expected = GlobalAssembler().assemble_loads(model, model.dof_manager())
    translated = np.zeros_like(expected)
    for node, component, value in _qf_consistent_translation_loads(model):
        translated[model.dof_manager().index(node - 1, ("UX", "UY", "UZ")[component - 1])] = value
    assert np.allclose(translated, expected, rtol=0.0, atol=1.0e-12)
