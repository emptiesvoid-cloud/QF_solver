from types import SimpleNamespace

from solveur.core.model import FiniteElementModel
from solveur.mesh.mixed_validation import declared_mixed_dynamic_scope_errors
from solveur.mesh.validation import MeshValidator


def test_declared_dynamic_scope_rejects_undeclared_family() -> None:
    model = SimpleNamespace(
        analysis=SimpleNamespace(parameters={"required_mixed_families": ["TET4", "WEDGE6", "HEX8"]}),
        elements=[SimpleNamespace(type="TET4"), SimpleNamespace(type="WEDGE6"), SimpleNamespace(type="HEX8"), SimpleNamespace(type="PYRAMID5")],
    )

    errors = declared_mixed_dynamic_scope_errors(model)

    assert errors == [
        "Declared mixed dynamic scope contains unsupported undeclared element family/families: PYRAMID5."
    ]


def test_harmonic_validation_applies_declared_mixed_scope() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        elements=[{"type": "TET4", "nodes": [0, 2, 1, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "young_modulus": 1.0e6, "poisson_ratio": 0.3, "density": 1.0}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}, {"node": 1, "dofs": ["UX", "UY", "UZ"]}],
        analysis={
            "type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": [0.0],
            "required_mixed_families": ["TET4", "WEDGE6", "HEX8"],
        },
    )

    report = MeshValidator().validate(model)

    assert report.status == "FAIL"
    assert any("missing required element family/families: HEX8, WEDGE6" in error for error in report.errors)
