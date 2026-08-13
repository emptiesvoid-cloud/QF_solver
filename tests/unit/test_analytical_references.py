import ast
from pathlib import Path

import pytest

from solveur.verification.analytical_references import Tet4StaticClosedFormOracle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORACLE_SOURCE = PROJECT_ROOT / "src" / "solveur" / "verification" / "analytical_references.py"


def test_tet4_closed_form_oracle_matches_hand_calculated_uniaxial_state() -> None:
    oracle = Tet4StaticClosedFormOracle(young_modulus=210.0e9, poisson_ratio=0.3)
    tension = oracle.constrained_uniaxial(1000.0)
    compression = oracle.constrained_uniaxial(-1000.0)

    assert oracle.constrained_modulus == pytest.approx(282_692_307_692.3077)
    assert tension["ux"] == pytest.approx(2.1224489795918366e-8)
    assert tension["stress_x"] == pytest.approx(6000.0)
    assert tension["lateral_stress"] == pytest.approx(2571.4285714285716)
    assert tension["von_mises"] == pytest.approx(3428.5714285714284)
    assert compression["ux"] == pytest.approx(-tension["ux"])
    assert compression["stress_x"] == pytest.approx(-tension["stress_x"])
    assert compression["von_mises"] == pytest.approx(tension["von_mises"])


def test_tet4_closed_form_oracle_integrates_constant_body_force_consistently() -> None:
    oracle = Tet4StaticClosedFormOracle(young_modulus=210.0e9, poisson_ratio=0.3)
    displacement = oracle.consistent_body_force_displacement(6000.0)
    assert displacement == pytest.approx(6000.0 / (4.0 * oracle.constrained_modulus))


@pytest.mark.parametrize(
    ("young", "poisson", "volume"),
    [(0.0, 0.3, 1.0 / 6.0), (1.0, 0.5, 1.0 / 6.0), (1.0, 0.3, 0.0)],
)
def test_tet4_closed_form_oracle_rejects_invalid_domain(young: float, poisson: float, volume: float) -> None:
    with pytest.raises(ValueError):
        Tet4StaticClosedFormOracle(young, poisson, volume)


def test_analytical_oracle_has_no_dependency_on_solver_implementation() -> None:
    tree = ast.parse(ORACLE_SOURCE.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    assert all(not name.startswith(("solveur", "mitc4", "numpy", "scipy")) for name in imported_modules)
