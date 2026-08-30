"""Contract checks for the supplemental G08 mesh extension harness."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_g08_mesh_extension_keeps_official_policy_and_scope() -> None:
    source = (ROOT / "scripts" / "run_g08_mesh_extension.py").read_text(encoding="utf-8")
    assert "EXTENSION_LEVELS = (16, 32)" in source
    assert "CONVERGED_BOUNDED_LIMIT = 0.01" in source
    assert "NEAR_CONVERGED_BOUNDED_LIMIT = 0.04" in source
    assert "official_policy_changed" in source
    assert "historical G08 closeout remains immutable" in source


def test_g08_mesh_extension_forces_local_source_imports() -> None:
    source = (ROOT / "scripts" / "run_g08_mesh_extension.py").read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(ROOT / \"src\"))" in source
    assert "source_dirty" in source
