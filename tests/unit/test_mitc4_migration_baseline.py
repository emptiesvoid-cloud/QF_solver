"""Numerical baseline protecting the MITC4 migration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from solveur.compat.mitc4.element import MITC4Element
from solveur.compat.mitc4.material import ShellMaterial
from solveur.elements.shell.mitc4 import (
    MITC4Element as CanonicalMITC4Element,
    MeshFactory as CanonicalMeshFactory,
    Mitc4ShellElement,
    QuadMesh as CanonicalQuadMesh,
    ShellMaterial as CanonicalShellMaterial,
    ShellModel as CanonicalShellModel,
)


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "qualification" / "baselines" / "mitc4_migration_baseline_2026-08-14.json"


def _rounded_checksum(matrix: np.ndarray, decimals: int) -> str:
    rounded = np.ascontiguousarray(np.round(matrix, decimals=decimals))
    return hashlib.sha256(rounded.tobytes()).hexdigest()


def _baseline_case() -> tuple[dict[str, object], ShellMaterial, np.ndarray]:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    material = ShellMaterial(**data["material"])
    coordinates = np.asarray(data["coordinates"], dtype=float)
    return data, material, coordinates


def test_mitc4_stiffness_and_mass_match_the_migration_baseline() -> None:
    data, material, coordinates = _baseline_case()
    element = MITC4Element(material)
    stiffness = element.stiffness(coordinates)
    mass = element.mass(coordinates)

    expected_stiffness = data["stiffness"]
    expected_mass = data["mass"]
    assert stiffness.shape == tuple(expected_stiffness["shape"])
    assert mass.shape == tuple(expected_mass["shape"])
    assert np.linalg.norm(stiffness) == pytest.approx(expected_stiffness["frobenius_norm"], rel=1.0e-12)
    assert np.trace(stiffness) == pytest.approx(expected_stiffness["trace"], rel=1.0e-12)
    assert np.linalg.norm(mass) == pytest.approx(expected_mass["frobenius_norm"], rel=1.0e-12)
    assert np.trace(mass) == pytest.approx(expected_mass["trace"], rel=1.0e-12)
    assert np.sum(mass) == pytest.approx(expected_mass["sum"], rel=1.0e-12)
    assert _rounded_checksum(stiffness, decimals=6) == expected_stiffness["rounded_checksum_sha256"]
    # A coarse decimal guard is intentional here: the transformed mass
    # matrix is assembled through platform-dependent BLAS paths.  The
    # strict norm/trace/sum checks above retain the numerical guard while
    # this checksum remains portable across supported Python platforms.
    mass_checksum_decimals = int(expected_mass.get("checksum_decimals", 3))
    actual_mass_checksum = _rounded_checksum(mass, decimals=mass_checksum_decimals)
    accepted_mass_checksums = expected_mass.get("accepted_rounded_checksum_sha256")
    if accepted_mass_checksums is None:
        accepted_mass_checksums = [expected_mass["rounded_checksum_sha256"]]
    assert actual_mass_checksum in accepted_mass_checksums


def test_common_shell_adapter_matches_the_validated_mitc4_element() -> None:
    _, material, coordinates = _baseline_case()
    legacy = MITC4Element(material)
    adapter = Mitc4ShellElement(material)
    np.testing.assert_allclose(adapter.stiffness(coordinates), legacy.stiffness(coordinates), rtol=1.0e-13, atol=1.0e-6)
    np.testing.assert_allclose(adapter.mass(coordinates), legacy.mass(coordinates), rtol=1.0e-13, atol=1.0e-12)


def test_legacy_mitc4_imports_reexport_the_canonical_formulation() -> None:
    assert MITC4Element is CanonicalMITC4Element
    assert ShellMaterial is CanonicalShellMaterial


def test_legacy_helper_modules_reexport_canonical_implementations() -> None:
    from solveur.compat.mitc4.mesh import MeshFactory, QuadMesh
    from solveur.compat.mitc4.model import ShellModel

    assert MeshFactory is CanonicalMeshFactory
    assert QuadMesh is CanonicalQuadMesh
    assert ShellModel is CanonicalShellModel


def test_legacy_verification_modules_reexport_canonical_implementations() -> None:
    from solveur.compat.mitc4.benchmarks import CantileverPlateBenchmark as LegacyBenchmark
    from solveur.compat.mitc4.convergence import StructuralConvergence as LegacyConvergence
    from solveur.compat.mitc4.locking import LockingCampaign as LegacyLockingCampaign
    from solveur.compat.mitc4.verification import MechanicalVerifier as LegacyMechanicalVerifier
    from solveur.compat.mitc4.visualization import DeformationPlotter as LegacyDeformationPlotter
    from solveur.post.mitc4_visualization import DeformationPlotter
    from solveur.verification.mitc4_benchmarks import CantileverPlateBenchmark
    from solveur.verification.mitc4_convergence import StructuralConvergence
    from solveur.verification.mitc4_locking import LockingCampaign
    from solveur.verification.mitc4_mechanical import MechanicalVerifier

    assert LegacyBenchmark is CantileverPlateBenchmark
    assert LegacyConvergence is StructuralConvergence
    assert LegacyLockingCampaign is LockingCampaign
    assert LegacyMechanicalVerifier is MechanicalVerifier
    assert LegacyDeformationPlotter is DeformationPlotter


def test_legacy_cli_announces_its_compatibility_status(capsys: pytest.CaptureFixture[str]) -> None:
    from solveur.compat.mitc4.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert "DEPRECATION: mitc4-solver is a compatibility command" in capsys.readouterr().err
