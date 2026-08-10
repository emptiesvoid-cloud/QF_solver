from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from solveur.large.campaign import run_large_scale_campaign
from solveur.large.assembler import PetscTET4Assembler, apply_homogeneous_element_constraints, partition_range
from solveur.large.memory import process_memory_snapshot
from solveur.large.readiness import check_large_readiness


@pytest.mark.parametrize("targets", [(), (0,), (100, 100), (100, 50)])
def test_large_campaign_rejects_invalid_targets(tmp_path: Path, targets: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        run_large_scale_campaign(tmp_path, targets=targets, solver_backend="matrix_free")


def test_large_campaign_plan_is_file_backed_and_does_not_generate_models(tmp_path: Path) -> None:
    result = run_large_scale_campaign(
        tmp_path,
        targets=(24, 81),
        solver_backend="matrix_free",
        execute=False,
    )

    assert result["status"] == "PLANNED"
    assert result["mode"] == "plan_only"
    assert result["strong_scaling_measured"] is False
    assert result["weak_scaling_measured"] is False
    assert [stage["status"] for stage in result["stages"]] == ["READY", "READY"]
    assert result["evidence_verification"]["status"] == "PASS"
    assert not list(tmp_path.rglob("qualification_model.h5"))
    report = json.loads((tmp_path / "large_campaign.json").read_text(encoding="utf-8"))
    assert report["targets"] == [24, 81]
    assert (tmp_path / "large_campaign.md").is_file()
    assert (tmp_path / "evidence_manifest.json").is_file()


def test_large_campaign_executes_small_qualification_stage(tmp_path: Path) -> None:
    result = run_large_scale_campaign(
        tmp_path,
        targets=(24,),
        solver_backend="scipy",
        execute=True,
    )

    stage = result["stages"][0]
    assert result["status"] == "PASS"
    assert stage["status"] == "PASS"
    assert stage["metrics"]["pipeline_time_seconds"] > 0.0
    assert stage["metrics"]["elements_per_second"] > 0.0
    assert "process_peak_rss_bytes" in stage["metrics"]
    assert Path(stage["qualification_summary"]).is_file()
    assert result["evidence_verification"]["status"] == "PASS"


def test_process_memory_snapshot_has_stable_schema() -> None:
    snapshot = process_memory_snapshot()

    assert set(snapshot) == {"source", "current_rss_bytes", "peak_rss_bytes"}
    for name in ("current_rss_bytes", "peak_rss_bytes"):
        assert snapshot[name] is None or snapshot[name] > 0


@pytest.mark.parametrize("count,size", [(0, 1), (1, 4), (17, 3), (100, 8)])
def test_contiguous_partition_covers_each_item_once(count: int, size: int) -> None:
    intervals = [partition_range(count, rank, size) for rank in range(size)]

    assert intervals[0][0] == 0
    assert intervals[-1][1] == count
    assert all(left[1] == right[0] for left, right in zip(intervals, intervals[1:]))
    assert sum(stop - start for start, stop in intervals) == count


@pytest.mark.parametrize("count,rank,size", [(-1, 0, 1), (1, -1, 1), (1, 1, 1), (1, 0, 0)])
def test_contiguous_partition_rejects_invalid_arguments(count: int, rank: int, size: int) -> None:
    with pytest.raises(ValueError):
        partition_range(count, rank, size)


def test_readiness_accepts_nested_output_that_does_not_exist(tmp_path: Path) -> None:
    output = tmp_path / "several" / "missing" / "levels"

    report = check_large_readiness(output, target_dofs=24, solver_backend="matrix_free")

    disk = next(item for item in report["checks"] if item["id"] == "DISK-FREE")
    assert disk["status"] == "PASS"


def test_homogeneous_element_constraints_preserve_symmetry_and_source() -> None:
    source = np.arange(144, dtype=float).reshape((12, 12))
    source = source + source.T
    original = source.copy()
    dofs = np.arange(12, dtype=np.int64)

    constrained = apply_homogeneous_element_constraints(source, dofs, {0, 5, 11})

    assert np.array_equal(source, original)
    assert np.allclose(constrained, constrained.T)
    assert np.allclose(constrained[[0, 5, 11], :], 0.0)
    assert np.allclose(constrained[:, [0, 5, 11]], 0.0)
    assert np.any(constrained[1:5, 1:5] != 0.0)


def test_petsc_assembler_rejects_unknown_matrix_format() -> None:
    with pytest.raises(ValueError, match="matrix_format"):
        PetscTET4Assembler(matrix_format="dense")
