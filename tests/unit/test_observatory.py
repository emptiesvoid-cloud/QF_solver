from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.benchmarks.runner import BenchmarkRunner
from solveur.benchmarks.types import BenchmarkDescriptor, BenchmarkRun
from solveur.verification.observatory import (
    ObservatoryValidationError,
    aggregate_rank_metrics,
    canonical_digest,
    compare_observatory_runs,
    make_observatory_record,
    read_observatory_record,
    record_benchmark_run,
    validate_observatory_record,
    write_observatory_record,
)


SOURCE = {"repository": ".", "revision": "e1703b5bc00e9cf2eb92e7e346783c9764201808", "dirty": False}
INPUT_DIGEST = "a" * 64
ROOT = Path(__file__).resolve().parents[2]


def make_record(**changes: object) -> dict:
    values = {
        "case_id": "LU2-WP01-SYNTHETIC-001",
        "requirement_id": "027-LU2-REQ-001",
        "capability_refs": ("linear-static/tet4",),
        "model_id": "synthetic-tet4",
        "element_family": "TET4",
        "analysis": "linear_static",
        "material": "isotropic_3d",
        "route": "matrix-free-tet4",
        "backend": "scipy",
        "solver": "CG",
        "preconditioner": "nodal_block_jacobi",
        "rank_count": 1,
        "dof": 12,
        "elements": 1,
        "input_digest": INPUT_DIGEST,
        "observables": {"displacement_norm": 1.25, "energy": 2.5},
        "tolerances": {"residual": {"value": 1e-8, "unit": "relative"}},
        "classification": "PASS",
        "metrics": {
            "timings_seconds": {"ksp_solve": 0.4, "total": 0.8},
            "iterations": 4,
            "matvecs": 5,
            "residual": 1e-10,
            "equilibrium": 2e-10,
            "energy": 1e-12,
            "resources": {"peak_rss_bytes": 1000, "peak_rss_per_rank_bytes": 1000, "imbalance": 0.0},
        },
        "source": SOURCE,
        "environment": {
            "hostname": "fixture",
            "os": "fixture-os",
            "cpu": "fixture-cpu",
            "python_version": "3.10-fixture",
            "petsc_version": None,
            "mpi_version": None,
            "container_digest": None,
            "ram_bytes": 10000,
            "threads": 1,
        },
        "command": ("python", "fixture"),
        "configuration": {"seed": 7},
    }
    values.update(changes)
    return make_observatory_record(**values)


def test_complete_record_validates_and_round_trips_canonically(tmp_path: Path) -> None:
    record = make_record()
    validate_observatory_record(record)
    path = write_observatory_record(tmp_path / "observation.json", record)

    assert read_observatory_record(path) == record
    assert canonical_digest(record) == canonical_digest(json.loads(path.read_text(encoding="utf-8")))
    assert path.read_bytes().endswith(b"\n")
    assert record["metrics"]["resources"]["gpu_vram_bytes"] is None


def test_controlled_sample_and_contract_are_readable() -> None:
    sample = read_observatory_record(ROOT / "qualification/0_2_7/wp01_observatory_sample.json")
    contract = json.loads((ROOT / "qualification/0_2_7/observatory_contract.json").read_text(encoding="utf-8"))

    assert sample["result"]["classification"] == "PASS"
    assert sample["source"]["revision"] == "e1703b5bc00e9cf2eb92e7e346783c9764201808"
    assert set(contract["classifications"]) >= {
        "PASS",
        "PASS_WITH_LIMITATIONS",
        "FAIL",
        "EXPECTED_FAILURE",
        "NOT_COMPARABLE",
        "UNAVAILABLE",
        "RESOURCE_LIMITED",
    }


def test_positive_verdict_requires_input_digest_and_committed_source() -> None:
    missing_input = make_record(input_digest=None)
    with pytest.raises(ObservatoryValidationError, match="input_digest"):
        validate_observatory_record(missing_input)

    dirty_source = make_record(source={**SOURCE, "dirty": True})
    with pytest.raises(ObservatoryValidationError, match="clean source"):
        validate_observatory_record(dirty_source)


def test_non_finite_metrics_are_rejected() -> None:
    record = make_record(metrics={"residual": float("nan")})
    with pytest.raises(ObservatoryValidationError, match="Non-finite"):
        validate_observatory_record(record)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")

    with pytest.raises(ObservatoryValidationError, match="Duplicate JSON key"):
        read_observatory_record(path)


def test_comparison_is_descriptive_and_requires_compatible_workload() -> None:
    left = make_record()
    right = make_record(metrics={"timings_seconds": {"ksp_solve": 0.2, "total": 0.5}, "iterations": 3})
    comparison = compare_observatory_runs(left, right)

    assert comparison["compatible"] is True
    assert comparison["timing_deltas_seconds"]["total"] == pytest.approx(-0.3)
    assert "no regression or improvement verdict" in comparison["comparison_policy"]

    incompatible = compare_observatory_runs(left, make_record(input_digest="b" * 64))
    assert incompatible["compatible"] is False
    assert "input_digest differs" in incompatible["compatibility_reasons"]


def test_rank_aggregation_is_deterministic_and_explicit() -> None:
    aggregate = aggregate_rank_metrics(
        [
            {"rank": 1, "peak_rss_bytes": 120, "iterations": 8, "timings_seconds": {"ksp_solve": 2.0}},
            {"rank": 0, "peak_rss_bytes": 100, "iterations": 7, "timings_seconds": {"ksp_solve": 1.5}},
        ]
    )

    assert aggregate == {
        "rank_count": 2,
        "peak_rss_per_rank_bytes": 120,
        "peak_rss_total_bytes": 220,
        "iterations": 8,
        "timings_seconds": {name: (2.0 if name == "ksp_solve" else None) for name in (
            "model_setup",
            "preflight",
            "assembly_operator",
            "redistribution",
            "pc_setup",
            "ksp_solve",
            "communication",
            "io",
            "post_processing",
            "total",
        )},
        "imbalance": pytest.approx(0.0909090909),
    }


def test_legacy_benchmark_adapter_does_not_invent_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("solveur.verification.observatory.git_source_state", lambda root: SOURCE)
    descriptor = BenchmarkDescriptor(
        identifier="LEGACY-001",
        title="Legacy fixture",
        family="TET4",
        analyses=("linear_static",),
        maturity="stable",
        reference_type="analytical",
        reference="fixture",
        reference_id="fixture",
        reference_url="",
        requirements=(),
        criteria={"relative_error": 1e-8},
    )
    run = BenchmarkRun(descriptor=descriptor, status="PASS", metrics={"observables": {"u": 1.0}}, checks=[])

    record_benchmark_run(run, tmp_path / "legacy.json", input_digest=INPUT_DIGEST, command=("pytest",))
    observed = read_observatory_record(tmp_path / "legacy.json")
    assert observed["result"]["classification"] == "PASS"

    record_benchmark_run(run, tmp_path / "legacy-unproven.json")
    unproven = read_observatory_record(tmp_path / "legacy-unproven.json")
    assert unproven["result"]["classification"] == "NOT_COMPARABLE"


def test_benchmark_runner_observation_hook_is_opt_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    descriptor = BenchmarkDescriptor(
        identifier="LEGACY-HOOK-001",
        title="Legacy hook fixture",
        family="TET4",
        analyses=("linear_static",),
        maturity="stable",
        reference_type="analytical",
        reference="fixture",
        reference_id="fixture",
        reference_url="",
        requirements=(),
        criteria={},
    )
    run = BenchmarkRun(descriptor=descriptor, status="PASS", metrics={"observables": {}}, checks=[])
    runner = BenchmarkRunner()
    monkeypatch.setattr(runner, "run", lambda identifier, output_dir, profile: run)
    monkeypatch.setattr("solveur.verification.observatory.git_source_state", lambda root: SOURCE)

    returned = runner.run_observed(
        "LEGACY-HOOK-001",
        tmp_path / "legacy-output",
        tmp_path / "observed.json",
        input_digest=INPUT_DIGEST,
        command=("pytest",),
    )

    assert returned is run
    assert read_observatory_record(tmp_path / "observed.json")["result"]["classification"] == "PASS"
