"""Regression guards for the F2 bug and sensitive-zone audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from solveur.compatibility.preflight import REGISTRY_PATH, check_compatibility, get_maturity
from solveur.core.errors import InputValidationError
from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.json_reader import JsonModelReader
from solveur.io.json_writer import JsonResultWriter


ROOT = Path(__file__).resolve().parents[2]


def test_model_reader_rejects_duplicate_nested_json_keys(tmp_path: Path) -> None:
    source = tmp_path / "duplicate-model.json"
    source.write_text(
        """
        {
          "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
          "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
          "materials": {"solid": {"type": "isotropic_3d", "E": 1.0, "E": 2.0, "nu": 0.3}}
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(InputValidationError, match="Duplicate key.*'E'"):
        JsonModelReader().read(source)


@pytest.mark.parametrize("analysis", ["transient_dynamic", "newmark", "newmark_transient"])
def test_dynamic_registry_analysis_aliases_retain_registry_maturity(analysis: str) -> None:
    result = check_compatibility("TET4", analysis, "isotropic_3d")

    assert result.status == "SUPPORTED_ROUTE"
    assert result.registry_maturity == "QUALIFIED_BOUNDED"
    assert get_maturity("TET4", analysis) == "QUALIFIED_BOUNDED"


@pytest.mark.parametrize("analysis", ["harmonic_response", "harmonic"])
def test_harmonic_registry_analysis_aliases_retain_registry_maturity(analysis: str) -> None:
    result = check_compatibility("TET4", analysis, "isotropic_3d")

    assert result.status == "SUPPORTED_ROUTE"
    assert result.registry_maturity == "QUALIFIED_BOUNDED"


def test_runtime_preflight_resolves_source_registry() -> None:
    assert REGISTRY_PATH == ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
    assert REGISTRY_PATH.is_file()


def test_evidence_manifest_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "evidence_manifest.json"
    manifest.write_text(
        '{"manifest_schema_version": 1, "file_count": 0, "file_count": 1, "files": []}',
        encoding="utf-8",
    )

    report = EvidenceBundleVerifier().verify(tmp_path)

    assert report.status == "FAIL"
    assert any("Duplicate JSON key 'file_count'" in error for error in report.errors)


def test_authoritative_registry_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    module_path = ROOT / "scripts" / "capability_registry_v2.py"
    spec = importlib.util.spec_from_file_location("f2_capability_registry_v2", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "registry.json"
    source.write_text('{"schema_version": 2, "schema_version": 2}', encoding="utf-8")

    with pytest.raises(module.DuplicateJsonKeyError, match="Duplicate JSON key 'schema_version'"):
        module.load_registry(source)


def test_result_writer_rejects_nonfinite_values(tmp_path: Path) -> None:
    class NonFiniteResult:
        def to_dict(self) -> dict[str, object]:
            return {"status": "FAIL", "value": float("nan")}

    target = tmp_path / "result.json"
    with pytest.raises(InputValidationError, match="finite JSON"):
        JsonResultWriter().write(NonFiniteResult(), target)
    assert not target.exists()


def test_pyproject_packages_runtime_registry_source() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "qualification/0_2_7/capability_registry_v2.json" in pyproject
