"""Public API contract for documented demonstrations."""

from pathlib import Path

import pytest

from solveur.api import list_demonstrations, run_demonstration, run_qualification_case


def test_library_lists_demonstrations_without_loading_the_documentation_site() -> None:
    values = list_demonstrations(family="MITC4", method="linear_static")
    assert {item.demo_id for item in values} == {
        "DEMO-MITC4-COOK-001",
        "DEMO-MITC4-LAMINATE-STATIC-001",
        "DEMO-MITC4-PINCHED-001",
        "DEMO-MITC4-SCORDELIS-001",
        "DEMO-MITC4-STATIC-QUAL-001",
    }
    assert all(item.references and item.documentation for item in values)


def test_library_reuses_controlled_benchmark_runner(tmp_path: Path, monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run(self, identifier: str, output_dir: Path, *, profile: str):
        called.update(identifier=identifier, output_dir=output_dir, profile=profile)
        return "controlled-run"

    monkeypatch.setattr("solveur.benchmarks.demonstrations.BenchmarkRunner.run", fake_run)
    assert run_demonstration("DEMO-TET4-PATCH-001", tmp_path, profile="engineering") == "controlled-run"
    assert called == {"identifier": "BM-SOL-TET4-PATCH-001", "output_dir": tmp_path, "profile": "engineering"}


def test_library_runs_controlled_qualification_demonstration(tmp_path: Path) -> None:
    output = tmp_path / "qualification_demo"
    row = run_demonstration("DEMO-TET4-STATIC-QUAL-001", output, profile="quick")

    assert row["id"] == "SOV-TET4-STATIC-001"
    assert row["passed"] is True
    assert (output / "qualification_case_summary.json").is_file()
    assert (output / "qualification_case_summary.md").is_file()
    assert (Path(row["evidence_dir"]) / "evidence_manifest.json").is_file()


def test_library_runs_one_qualification_case_directly(tmp_path: Path) -> None:
    row = run_qualification_case("SOV-TET4-PRESSURE-001", tmp_path / "pressure")

    assert row["id"] == "SOV-TET4-PRESSURE-001"
    assert row["passed"] is True


@pytest.mark.parametrize(
    ("identifier", "expected_status"),
    [
        ("DEMO-ORTHO-TET4-STATIC-001", "WARNING"),
        ("DEMO-ORTHO-TET10-NEWMARK-001", "WARNING"),
        ("DEMO-MITC4-LAMINATE-STATIC-001", "WARNING"),
        ("DEMO-MITC4-MODAL-001", "PASS"),
        ("DEMO-MITC4-NEWMARK-001", "PASS"),
        ("DEMO-MITC4-HARMONIC-001", "PASS"),
    ],
)
def test_library_runs_documented_json_model_with_evidence(
    tmp_path: Path, identifier: str, expected_status: str
) -> None:
    summary = run_demonstration(identifier, tmp_path / identifier)

    assert summary["status"] == expected_status
    assert summary["qualification"]["status"] == expected_status
    artifacts = {name: Path(path) for name, path in summary["artifacts"].items()}
    assert artifacts["results"].is_file()
    assert artifacts["manifest"].is_file()
    assert (tmp_path / identifier / "demonstration_summary.json").is_file()


def test_library_plans_large_scale_demonstration_without_allocating_model(tmp_path: Path) -> None:
    summary = run_demonstration("DEMO-LARGE-PETSC-PLAN-001", tmp_path / "large_plan")

    assert summary["mode"] == "plan_only"
    assert summary["status"] in {"PLANNED", "BLOCKED"}
    assert summary["targets"] == [1_000_000]
    assert summary["evidence_verification"]["status"] == "PASS"
    assert (tmp_path / "large_plan" / "large_campaign.json").is_file()
    assert (tmp_path / "large_plan" / "evidence_manifest.json").is_file()
