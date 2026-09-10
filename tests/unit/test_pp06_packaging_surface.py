"""Targeted guards for the 0.2.8 packaging, license and install surface."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_package_declares_complete_license_set_and_documentation_engine() -> None:
    project = tomllib.loads(_text("pyproject.toml"))["project"]
    assert project["name"] == "qf-solver"
    assert project["version"] == "0.2.8"
    assert set(project["license-files"]) == {"LICENSE", "LICENSE-DOCS", "NOTICE", "THIRD_PARTY_LICENSES.md"}
    docs = set(project["optional-dependencies"]["docs"])
    assert "mkdocs>=1.6,<2" in docs
    assert "mkdocs-material>=9.5,<10" in docs


def test_manifest_and_license_inventory_cover_public_license_documents() -> None:
    manifest = _text("MANIFEST.in")
    for filename in ("LICENSE", "LICENSE-DOCS", "NOTICE", "THIRD_PARTY_LICENSES.md"):
        assert filename in manifest
    inventory = _text("THIRD_PARTY_LICENSES.md")
    for component in ("NumPy", "SciPy", "Matplotlib", "Gmsh", "h5py", "mpi4py", "PETSc", "SLEPc", "MkDocs"):
        assert component in inventory


def test_installation_document_matches_extras_and_runtime_boundaries() -> None:
    installation = _text("docs/getting-started/installation.md")
    for extra in ("mesh", "hdf5", "large", "hpc", "docs"):
        assert f'qf-solver[{extra}]' in installation
    assert "python -m mkdocs build --strict -f .github/pages/mkdocs.yml" in installation
    assert "--branch 0.2.8-pre-publication" in installation
    assert "default branch" in installation
    assert "Linux" in installation and "native Windows" in installation
    assert "NOT_VALIDATED" in installation
    assert "```powershell" not in installation


def test_public_license_and_package_files_are_present() -> None:
    for filename in ("LICENSE", "LICENSE-DOCS", "NOTICE", "THIRD_PARTY_LICENSES.md"):
        assert (ROOT / filename).is_file(), filename
