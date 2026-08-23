from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from solveur.cli import large
from solveur.core.errors import ExitCode


def _args(**overrides: object) -> SimpleNamespace:
    values = {
        "input": Path("input.h5"),
        "output": Path("output"),
        "solver_backend": "scipy",
        "preconditioner": "jacobi",
        "chunk_size": 4096,
        "matrix_format": "baij",
        "partition_strategy": "contiguous",
        "graph_partitioner": "none",
        "restart_from": None,
        "targets": [1000],
        "memory_budget_mb": None,
        "execute": False,
        "continue_on_failure": False,
        "preconditioners": ["jacobi"],
        "displacement_tolerance": 1.0e-7,
        "inputs": [Path("one.json")],
        "mode": "strong",
        "weak_work_tolerance": 0.05,
        "efficiency_warning_threshold": 0.5,
        "labels": None,
        "topologies": ["serial"],
        "presets": ["default"],
        "displacements": Path("displacements.h5"),
        "resume": False,
        "overwrite": False,
        "max_chunks": None,
        "target_dofs": 24,
        "nx": None,
        "ny": None,
        "nz": None,
        "length": 1.0,
        "height": 1.0,
        "depth": 1.0,
        "young": 210.0e9,
        "poisson": 0.3,
        "density": 7800.0,
        "total_load": 1.0,
        "material_json": None,
        "max_solver_residual": 1.0e-7,
        "json_report": None,
        "markdown": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_convert_inspect_and_generate_commands_forward_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model = SimpleNamespace(node_count=4, element_count=1, ndof=12)
    audit = SimpleNamespace(status="PASS")
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(large, "convert_model_to_large", lambda source, target: calls.append(("convert", target)) or model)
    monkeypatch.setattr(large, "load_large_model", lambda source: calls.append(("load", source)) or model)
    monkeypatch.setattr(large, "inspect_large_model", lambda value: audit)
    monkeypatch.setattr(large, "save_result", lambda value, target: calls.append(("save", target)))
    monkeypatch.setattr(large, "generate_large_tet4_block", lambda target, **kwargs: calls.append(("generate", kwargs)) or model)

    assert large.command_convert_model(_args(output=tmp_path / "converted.h5")) == 0
    assert large.command_inspect_large(_args(output=tmp_path / "audit.json")) == int(ExitCode.ACCEPTED)
    assert large.command_generate_large(_args(output=tmp_path / "generated.h5", target_dofs=None, nx=1, ny=1, nz=1)) == 0
    assert {item[0] for item in calls} == {"convert", "load", "save", "generate"}


def test_large_material_and_dimension_helpers_validate_json_and_dimensions(tmp_path: Path) -> None:
    material_path = tmp_path / "material.json"
    material_path.write_text(json.dumps({"type": "isotropic_3d", "E": 1.0, "nu": 0.3}), encoding="utf-8")
    material = large._large_material_from_json(material_path)
    assert material["type"] == "isotropic_3d"
    assert large._large_block_dimensions(_args(target_dofs=None, nx=2, ny=3, nz=4)) == (2, 3, 4)
    assert large._optional_large_block_dimensions(_args()) is None
    with pytest.raises(ValueError, match="all of --nx"):
        large._optional_large_block_dimensions(_args(nx=1))
    with pytest.raises(ValueError, match="one JSON object"):
        bad = tmp_path / "bad.json"
        bad.write_text("[]", encoding="utf-8")
        large._large_material_from_json(bad)
    with pytest.raises(ValueError, match="positive"):
        large._memory_budget_bytes(_args(memory_budget_mb=0))


def test_solve_benchmark_and_campaign_commands_report_status(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    model = SimpleNamespace(node_count=2, element_count=1, ndof=6)
    solve_result = SimpleNamespace(status="PASS", backend="scipy", output_files={"summary": "summary.json"})
    monkeypatch.setattr(large, "load_large_model", lambda _: model)
    monkeypatch.setattr(large, "load_distributed_large_model", lambda **_: model)
    monkeypatch.setattr(large, "solve_large_model", lambda *args, **kwargs: solve_result)
    monkeypatch.setattr(large, "benchmark_large_model", lambda *args, **kwargs: {
        "status": "PASS", "backend": "scipy", "ndof": 6, "evidence_manifest": "manifest.json",
        "evidence_verification": {"status": "PASS"},
    })
    monkeypatch.setattr(large, "run_large_scale_campaign", lambda *args, **kwargs: {
        "status": "PASS", "mode": "plan_only", "backend": "scipy", "targets": [1000],
        "markdown_report": "report.md", "evidence_verification": {"status": "PASS"},
    })

    assert large.command_solve_large(_args()) == 0
    assert large.command_benchmark_large(_args()) == 0
    assert large.command_large_campaign(_args()) == int(ExitCode.ACCEPTED)
    assert "SOLVE LARGE STATUS: PASS" in capsys.readouterr().out


def test_campaign_and_report_commands_forward_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(large, "run_large_preconditioner_campaign", lambda *args, **kwargs: {
        "status": "PASS", "preconditioners": ["jacobi"]
    })
    monkeypatch.setattr(large, "analyze_large_scaling", lambda *args, **kwargs: {
        "status": "PASS", "mode": "strong", "minimum_efficiency": 0.9
    })
    monkeypatch.setattr(large, "write_petsc_profile_report", lambda *args, **kwargs: {
        "status": "PASS", "profiles": ["profile"], "evidence_manifest": "manifest.json"
    })
    monkeypatch.setattr(large, "analyze_petsc_tuning", lambda *args, **kwargs: {
        "status": "PASS", "runs": ["run"], "default_policy_change_recommended": False,
        "evidence_manifest": "manifest.json"
    })
    monkeypatch.setattr(large, "postprocess_large_model", lambda *args, **kwargs: {
        "status": "PASS", "processed_element_count": 1, "element_count": 1,
        "result_file": "results.h5", "checkpoint_file": "checkpoint.json"
    })
    args = _args()
    assert large.command_large_preconditioners(args) == int(ExitCode.ACCEPTED)
    assert large.command_large_scaling_report(args) == int(ExitCode.ACCEPTED)
    assert large.command_petsc_profile_report(args) == int(ExitCode.ACCEPTED)
    assert large.command_petsc_tuning_report(args) == int(ExitCode.ACCEPTED)
    assert large.command_postprocess_large(args) == int(ExitCode.ACCEPTED)


def test_readiness_qualification_and_verification_commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    report = {
        "status": "PASS", "backend": "matrix_free", "sizing": {"ndof": 24},
        "checks": [{"id": "CHECK", "status": "PASS", "detail": "ok"}],
    }
    monkeypatch.setattr(large, "check_large_readiness", lambda *args, **kwargs: report)
    monkeypatch.setattr(large, "save_large_readiness", lambda value, output: {"json": "readiness.json", "markdown": "readiness.md"})
    qualification = {"status": "PASS", "backend": "scipy", "target_dofs": 24, "actual_dofs": 24,
                     "summary_path": "summary.json", "evidence_manifest": "manifest.json"}
    monkeypatch.setattr(large, "qualify_large_tet4_pipeline", lambda *args, **kwargs: qualification)
    verification = SimpleNamespace(status="PASS", checks=())
    monkeypatch.setattr(large, "verify_large_qualification", lambda *args, **kwargs: verification)
    monkeypatch.setattr(large, "save_large_verification", lambda *args, **kwargs: None)
    args = _args(output=tmp_path / "out", json_report=tmp_path / "verify.json", markdown=tmp_path / "verify.md")

    assert large.command_large_readiness(args) == 0
    assert large.command_qualify_large(args) == int(ExitCode.ACCEPTED)
    assert large.command_verify_large(args) == int(ExitCode.ACCEPTED)


def test_mpi_reporting_helpers_have_safe_serial_fallback() -> None:
    assert large._reporting_rank("scipy") is True
    assert large._reporting_rank("petsc") is True
    assert large._mpi_size() == 1
