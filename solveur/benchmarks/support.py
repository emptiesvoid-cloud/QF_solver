"""Shared artifact and acceptance helpers for benchmark runners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from solveur.benchmarks.types import BenchmarkDescriptor, BenchmarkRun
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.io.manifest import discovered_file_entries, git_source_state, runtime_fingerprint, utc_timestamp, write_json_file
from solveur.io.json_writer import JsonResultWriter
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.version import DISPLAY_NAME, __version__


@dataclass
class BenchmarkContext:
    """Own the deterministic directory and common artifacts for one case."""

    descriptor: BenchmarkDescriptor
    root: Path
    profile: str

    @classmethod
    def create(
        cls,
        descriptor: BenchmarkDescriptor,
        output_dir: str | Path,
        profile: str,
    ) -> "BenchmarkContext":
        root = Path(output_dir).resolve() / descriptor.identifier
        root.mkdir(parents=True, exist_ok=True)
        return cls(descriptor, root, profile)

    def write_setup(self, value: dict[str, Any], name: str = "model.setup.json") -> Path:
        path = self.root / name
        write_json_file(path, value)
        return path

    def import_and_solve(
        self,
        mesh_path: str | Path,
        setup: dict[str, Any],
        *,
        prefix: str = "result",
        prepare_model: Callable[[object], None] | None = None,
    ) -> tuple[object, object, dict[str, str]]:
        setup_path = self.write_setup(setup, f"{prefix}.setup.json")
        imported = GmshModelImporter().import_model(mesh_path, setup_path)
        if prepare_model is not None:
            prepare_model(imported.model)
        model_path = self.root / f"{prefix}.model.json"
        report_path = self.root / f"{prefix}.import_report.json"
        result_path = self.root / f"{prefix}.json"
        vtu_path = self.root / f"{prefix}.vtu"
        JsonModelWriter().write(imported.model, model_path)
        write_json_file(report_path, imported.report.to_dict())
        result = enforce_qualification_policy(AnalysisRouter().solve(imported.model), imported.model)
        JsonResultWriter().write(result, result_path)
        if getattr(result, "analysis", "") in {"linear_static", "nonlinear_static", "transient_dynamic"}:
            VtuResultWriter().write(result, imported.model, vtu_path)
        files = {
            f"{prefix}_mesh": _relative(self.root, Path(mesh_path)),
            f"{prefix}_setup": _relative(self.root, setup_path),
            f"{prefix}_model": _relative(self.root, model_path),
            f"{prefix}_import_report": _relative(self.root, report_path),
            f"{prefix}_result": _relative(self.root, result_path),
        }
        if vtu_path.is_file():
            files[f"{prefix}_vtu"] = _relative(self.root, vtu_path)
        return imported.model, result, files

    def solve_model(
        self,
        model: FiniteElementModel,
        *,
        prefix: str = "result",
    ) -> tuple[object, dict[str, str]]:
        """Solve an in-memory benchmark model and persist standard artifacts."""
        model_path = self.root / f"{prefix}.model.json"
        result_path = self.root / f"{prefix}.json"
        vtu_path = self.root / f"{prefix}.vtu"
        JsonModelWriter().write(model, model_path)
        result = enforce_qualification_policy(AnalysisRouter().solve(model), model)
        JsonResultWriter().write(result, result_path)
        if getattr(result, "analysis", "") in {"linear_static", "nonlinear_static", "transient_dynamic"}:
            VtuResultWriter().write(result, model, vtu_path)
        files = {
            f"{prefix}_model": _relative(self.root, model_path),
            f"{prefix}_result": _relative(self.root, result_path),
        }
        if vtu_path.is_file():
            files[f"{prefix}_vtu"] = _relative(self.root, vtu_path)
        return result, files

    def finalize(self, run: BenchmarkRun) -> BenchmarkRun:
        run.files = dict(sorted(run.files.items()))
        summary_path = self.root / "benchmark_summary.json"
        write_json_file(summary_path, run.to_dict())
        run.files["summary"] = summary_path.name
        manifest_path = self.root / "benchmark_manifest.json"
        entries = discovered_file_entries(
            self.root,
            lambda relative: "benchmark_artifact",
            exclude_names=(manifest_path.name,),
        )
        write_json_file(
            manifest_path,
            {
                "manifest_schema_version": 1,
                "created_at_utc": utc_timestamp(),
                "solver": {"name": DISPLAY_NAME, "version": __version__},
                "benchmark_id": self.descriptor.identifier,
                "profile": self.profile,
                "status": run.status,
                "source": git_source_state(Path(__file__).resolve().parents[2]),
                "runtime": runtime_fingerprint(),
                "files": entries,
            },
        )
        run.files["manifest"] = manifest_path.name
        write_json_file(summary_path, run.to_dict())
        return run


def upper_check(identifier: str, value: float, limit: float, *, detail: str = "") -> dict[str, Any]:
    passed = bool(value <= limit)
    return {
        "id": identifier,
        "status": "PASS" if passed else "FAIL",
        "value": float(value),
        "limit": float(limit),
        "operator": "less_equal",
        "detail": detail,
    }


def lower_check(identifier: str, value: float, limit: float, *, detail: str = "") -> dict[str, Any]:
    passed = bool(value >= limit)
    return {
        "id": identifier,
        "status": "PASS" if passed else "FAIL",
        "value": float(value),
        "limit": float(limit),
        "operator": "greater_equal",
        "detail": detail,
    }


def run_status(checks: list[dict[str, Any]], *, expected_warning: bool = False) -> str:
    if any(check["status"] == "FAIL" for check in checks):
        return "FAIL"
    return "WARNING" if expected_warning else "PASS"


def free_residual(result: object) -> float:
    data = result.to_dict()
    audit = data.get("audit", {})
    equilibrium = audit.get("equilibrium", {})
    return float(equilibrium.get("free_relative_residual", 0.0))


def _relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return str(resolved)
