from __future__ import annotations

from solveur.verification.calculix_mitc3 import calculix_triangle_input
from solveur.verification.code_aster_mitc3 import _qf_model


def test_calculix_mitc3_deck_uses_s3_and_preserves_total_load() -> None:
    model, triangles, root, tip = _qf_model(4, 2, dof="UZ", total_load=-12.0)
    text = calculix_triangle_input(
        model.nodes,
        triangles,
        root,
        tip,
        "UZ",
        -12.0,
    )
    assert "*ELEMENT,TYPE=S3" in text
    assert "*SHELL SECTION" in text
    assert "ROOT,1,6" in text
    assert text.count(",3,-4") == 3
