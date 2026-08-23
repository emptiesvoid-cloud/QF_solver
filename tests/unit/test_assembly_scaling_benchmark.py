from __future__ import annotations

from scripts.benchmark_assembly_scaling import run_campaign


def test_assembly_scaling_campaign_archives_repeated_phase_medians(tmp_path) -> None:
    report = run_campaign([1000], tmp_path / "assembly.json", repeats=2)

    row = report["sizes"][0]
    assert row["repeat_count"] == 2
    assert len(row["assembly_seconds_samples"]) == 2
    assert row["nnz"] == row["assembly_diagnostics"]["final_nnz"]
    phases = row["assembly_diagnostics"]["assembly_phase_seconds"]
    assert phases["chunk_build"] >= phases["element_kernel"]
    assert phases["chunk_build"] >= phases["chunk_sparse_conversion"]
    assert row["assembly_diagnostics"]["material_cache_reused"] is True
    assert (tmp_path / "assembly.json").is_file()


def test_assembly_scaling_rejects_non_positive_repeat_count() -> None:
    try:
        run_campaign([1000], repeats=0)
    except ValueError as exc:
        assert "repeats" in str(exc)
    else:
        raise AssertionError("run_campaign must reject repeats=0")


def test_assembly_scaling_can_archive_a_second_mesh_and_material_configuration(tmp_path) -> None:
    report = run_campaign(
        [1000],
        tmp_path / "centered.json",
        repeats=1,
        decomposition="centered",
        material={"type": "isotropic_3d", "E": 70.0e9, "nu": 0.27, "density": 2700.0},
    )

    assert report["configuration"]["decomposition"] == "centered"
    assert report["configuration"]["material"]["E"] == 70.0e9
    assert report["sizes"][0]["assembly_diagnostics"]["final_nnz"] > 0
