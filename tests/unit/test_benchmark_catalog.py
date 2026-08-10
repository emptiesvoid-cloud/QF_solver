from pathlib import Path
import json

import pytest

from solveur.benchmarks import BenchmarkCatalog, BenchmarkRunner
from solveur.core.errors import InputValidationError


EXPECTED_IDS = {
    "BM-BEAM2-CANTILEVER-001",
    "BM-SOL-TET4-PATCH-001",
    "BM-SOL-TET4-MEMBRANE-001",
    "BM-SOL-TET4-TORSION-001",
    "BM-SOL-CANTILEVER-001",
    "BM-SOL-TET10-LAME-001",
    "BM-SHL-COOK-001",
    "BM-SHL-SCORDELIS-001",
    "BM-SHL-PINCHED-001",
    "BM-DYN-CANTILEVER-001",
    "BM-NL-J2-BAR-001",
}


def test_controlled_benchmark_catalog_contains_eleven_unique_cases() -> None:
    descriptors = BenchmarkCatalog().list()
    requirement_ids = {
        item["id"]
        for item in json.loads(
            (Path(__file__).resolve().parents[2] / "qualification" / "requirements.json").read_text(encoding="utf-8")
        )["requirements"]
    }
    assert {item.identifier for item in descriptors} == EXPECTED_IDS
    assert all(item.criteria for item in descriptors)
    assert all(item.reference for item in descriptors)
    assert all(item.reference_url.startswith("https://") for item in descriptors)
    assert all(set(item.requirements) <= requirement_ids for item in descriptors)
    assert {item.maturity for item in descriptors} <= {
        "stable",
        "stable_after_reinforced_tests",
        "experimental",
        "research",
    }


def test_benchmark_runner_registry_matches_catalog() -> None:
    assert {item.identifier for item in BenchmarkRunner().list()} == EXPECTED_IDS


def test_benchmark_runner_rejects_unknown_profile(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="verification profile"):
        BenchmarkRunner().run("BM-SOL-TET4-PATCH-001", tmp_path, profile="unsupported")
