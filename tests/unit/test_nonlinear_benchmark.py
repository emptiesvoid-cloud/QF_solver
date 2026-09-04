from __future__ import annotations

import json

import pytest

from scripts import benchmark_nonlinear_025 as benchmark


def test_nonlinear_benchmark_writes_raw_samples_and_summary(monkeypatch, tmp_path) -> None:
    def sample(family: str) -> dict[str, object]:
        return {
            "element": family,
            "status": "PASS",
            "dof_count": 12 if family == "TET4" else 24,
            "newton_iterations": 4,
            "elapsed_seconds": 0.25,
            "python_peak_allocated_bytes": 100,
        }

    monkeypatch.setattr(benchmark, "_run_once", sample)
    output = tmp_path / "benchmark.json"
    report = benchmark.run_campaign(["TET4", "HEX8"], repeats=2, output=output)

    assert len(report["samples"]) == 4
    assert report["summary"][1]["mean_elapsed_seconds"] == 0.25
    assert report["summary"][0]["median_elapsed_seconds"] == 0.25
    assert report["summary"][0]["min_elapsed_seconds"] == 0.25
    assert report["summary"][0]["max_elapsed_seconds"] == 0.25
    assert report["summary"][0]["elapsed_stddev_seconds"] == 0.0
    assert report["summary"][0]["elapsed_coefficient_variation"] == 0.0
    assert report["summary"][0]["successful_repeats"] == 2
    assert report["summary"][0]["failed_repeats"] == 0
    assert report["summary"][0]["max_rss_bytes"] is None
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["campaign"] == "qf-solver-nonlinear-performance-0.2.5a0"
    assert payload["samples"][0]["repeat"] == 1


def test_nonlinear_benchmark_preserves_structured_failure(monkeypatch, tmp_path) -> None:
    def failed_sample(_family: str) -> dict[str, object]:
        return {
            "element": "TET4",
            "status": "FAIL",
            "dof_count": None,
            "newton_iterations": None,
            "elapsed_seconds": 0.5,
            "python_peak_allocated_bytes": 256,
            "failure": {
                "type": "NumericalConvergenceError",
                "reason": "nan_detected",
                "diagnostics": {"element_index": 0},
            },
        }

    monkeypatch.setattr(benchmark, "_run_once", failed_sample)
    output = tmp_path / "failed-benchmark.json"
    report = benchmark.run_campaign(["TET4"], repeats=1, output=output)

    sample = report["samples"][0]
    assert sample["status"] == "FAIL"
    assert sample["failure"]["reason"] == "nan_detected"
    assert sample["failure"]["diagnostics"] == {"element_index": 0}
    assert report["summary"][0]["dof_count"] is None
    assert json.loads(output.read_text(encoding="utf-8"))["samples"][0]["failure"]


def test_nonlinear_benchmark_aggregates_phase_timings(monkeypatch, tmp_path) -> None:
    def timed_sample(_family: str) -> dict[str, object]:
        return {
            "element": "TET4",
            "status": "PASS",
            "dof_count": 12,
            "newton_iterations": 2,
            "elapsed_seconds": 0.5,
            "python_peak_allocated_bytes": 256,
            "assembly_seconds": 0.2,
            "linear_solve_seconds": 0.1,
            "line_search_seconds": 0.05,
            "element_setup_seconds": 0.02,
            "element_kernel_seconds": 0.12,
            "element_scatter_seconds": 0.03,
            "sparse_conversion_seconds": 0.01,
            "contact_assembly_seconds": 0.0,
            "element_cache_hits": 8,
            "element_cache_misses": 0,
            "reference_cache_hits": 6,
            "reference_cache_misses": 2,
            "max_sparse_chunk_count": 3,
            "max_sparse_peak_chunk_entries": 512,
            "max_sparse_peak_chunk_bytes_estimate": 24576,
            "max_sparse_accumulator_levels": 2,
            "max_element_kernel_calls": 2,
            "max_contact_assembly_calls": 0,
            "max_tangent_nnz": 144,
        }

    monkeypatch.setattr(benchmark, "_run_once", timed_sample)
    report = benchmark.run_campaign(["TET4"], repeats=1, output=tmp_path / "timed.json")

    sample = report["samples"][0]
    assert sample["assembly_seconds"] == 0.2
    assert sample["linear_solve_seconds"] == 0.1
    assert sample["line_search_seconds"] == 0.05
    assert report["summary"][0]["mean_assembly_seconds"] == 0.2
    assert report["summary"][0]["median_assembly_seconds"] == 0.2
    assert report["summary"][0]["mean_linear_solve_seconds"] == 0.1
    assert report["summary"][0]["median_linear_solve_seconds"] == 0.1
    assert report["summary"][0]["mean_line_search_seconds"] == 0.05
    assert report["summary"][0]["mean_element_kernel_seconds"] == 0.12
    assert report["summary"][0]["mean_element_cache_hits"] == 8.0
    assert report["summary"][0]["mean_element_cache_misses"] == 0.0
    assert report["summary"][0]["mean_reference_cache_hits"] == 6.0
    assert report["summary"][0]["mean_reference_cache_misses"] == 2.0
    assert report["summary"][0]["max_sparse_chunk_count"] == 3
    assert report["summary"][0]["max_sparse_peak_chunk_entries"] == 512
    assert report["summary"][0]["max_sparse_peak_chunk_bytes_estimate"] == 24576
    assert report["summary"][0]["max_sparse_accumulator_levels"] == 2
    assert report["summary"][0]["max_tangent_nnz"] == 144


def test_nonlinear_benchmark_uses_median_and_bounds_for_variable_repeats(monkeypatch, tmp_path) -> None:
    elapsed = iter((0.2, 0.8, 0.4))

    def variable_sample(_family: str) -> dict[str, object]:
        value = next(elapsed)
        return {
            "element": "TET4",
            "status": "PASS",
            "dof_count": 12,
            "newton_iterations": 2,
            "elapsed_seconds": value,
            "python_peak_allocated_bytes": 256,
        }

    monkeypatch.setattr(benchmark, "_run_once", variable_sample)
    report = benchmark.run_campaign(["TET4"], repeats=3, output=tmp_path / "variable.json")

    summary = report["summary"][0]
    assert summary["mean_elapsed_seconds"] == pytest.approx(0.4666666667)
    assert summary["median_elapsed_seconds"] == pytest.approx(0.4)
    assert summary["min_elapsed_seconds"] == pytest.approx(0.2)
    assert summary["max_elapsed_seconds"] == pytest.approx(0.8)
    assert summary["elapsed_stddev_seconds"] == pytest.approx(0.3055050463)


def test_nonlinear_benchmark_rejects_nonpositive_repeats(tmp_path) -> None:
    with pytest.raises(ValueError, match="repeats must be positive"):
        benchmark.run_campaign(["TET4"], repeats=0, output=tmp_path / "invalid.json")


def test_nonlinear_benchmark_exposes_explicit_arc_length_path(monkeypatch, tmp_path) -> None:
    def path_sample(family: str, kinematics: str = "small_strain", *, path: str = "load_control"):
        return {
            "element": family,
            "kinematics": kinematics,
            "path": path,
            "status": "PASS",
            "dof_count": 12,
            "newton_iterations": 3,
            "elapsed_seconds": 0.1,
            "python_peak_allocated_bytes": 128,
        }

    monkeypatch.setattr(benchmark, "_run_once", path_sample)
    report = benchmark.run_campaign(
        ["TET4"], repeats=1, output=tmp_path / "arc.json", path="arc_length"
    )

    assert report["path"] == "arc_length"
    assert report["samples"][0]["path"] == "arc_length"
    assert report["summary"][0]["path"] == "arc_length"


def test_nonlinear_benchmark_builds_finite_kinematic_arc_length_path() -> None:
    model = benchmark._benchmark_model("TET4", "small_strain", "arc_length_finite_kinematic")

    assert model.analysis.method == "arc_length"
    assert model.analysis.parameters["kinematics"] == "total_lagrangian_j2"
    assert model.analysis.parameters["adaptive_arc_length"] is True
    assert model.analysis.parameters["target_load_factor"] == 0.5
    assert model.analysis.parameters["max_arc_steps"] == 512


@pytest.mark.parametrize("path", ["geometric_static", "arc_length", "contact", "finite_sliding", "coupled"])
def test_nonlinear_benchmark_paths_execute_bounded_profiles(path: str) -> None:
    report = benchmark.run_campaign(["TET4"], repeats=1, path=path)

    sample = report["samples"][0]
    assert sample["path"] == path
    if path == "finite_sliding":
        assert sample["status"] == "FAIL"
        assert sample["failure"]["type"] == "CompatibilityError"
        assert sample["failure"]["reason"] == "ANALYSIS_NOT_SUPPORTED"
        return
    assert sample["status"] == "PASS"
    assert sample["dof_count"] is not None
    assert sample["failure"] is None
    if path == "arc_length":
        assert sample["assembly_seconds"] > 0.0
        assert sample["linear_solve_seconds"] > 0.0
    if path == "geometric_static":
        assert sample["newton_iterations"] > 0
    elif path != "finite_sliding":
        assert sample["element_kernel_seconds"] > 0.0
        assert sample["sparse_conversion_seconds"] >= 0.0
