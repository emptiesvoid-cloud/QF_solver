from __future__ import annotations

from solveur.verification.mitc3_refined import refined_cases


def test_refined_shell_meshes_preserve_expected_counts_and_ratios() -> None:
    scordelis, pinched = refined_cases()
    assert scordelis.element_count == 2 * scordelis.nx * scordelis.ny == 20_000
    assert pinched.element_count == 2 * pinched.nx * pinched.ny == 19_600
    assert pinched.ny == 2 * pinched.nx
    assert scordelis.tolerance == 0.05
    assert pinched.tolerance == 0.10
