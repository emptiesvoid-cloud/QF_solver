"""Write reproducible solver evidence bundles."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from solveur.core.model import FiniteElementModel
from solveur.core.qualification import qualification_metadata, qualification_summary
from solveur.io.audit_markdown import AuditMarkdownWriter
from solveur.io.csv_writer import CsvResultWriter
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import (
    command_line,
    git_source_state,
    locked_environment_fingerprints,
    manifest_file_entry,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.io.vtu_writer import VtuResultWriter
from solveur.verification.traceability import model_traceability_summary
from solveur.version import DISPLAY_NAME, __version__


class EvidenceBundleWriter:
    """Export the files needed to review and reproduce one solver run."""

    def write(
        self,
        *,
        model: FiniteElementModel,
        result: object,
        directory: str | Path,
        input_path: str | Path | None = None,
        include_vtu: bool = True,
        include_csv: bool = True,
    ) -> dict[str, Path]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        paths["input"] = self._write_input(model, target, input_path)
        paths["results"] = target / "results.json"
        JsonResultWriter().write(result, paths["results"])
        paths["audit"] = target / "audit.md"
        AuditMarkdownWriter().write(result, paths["audit"])
        paths["mesh_report"] = target / "mesh_report.json"
        write_json_file(paths["mesh_report"], result.mesh_report.to_dict())
        paths["solver_settings"] = target / "solver_settings.json"
        write_json_file(paths["solver_settings"], self._solver_settings(model, result))
        paths["qualification_summary"] = target / "qualification_summary.json"
        write_json_file(paths["qualification_summary"], qualification_summary(result, model))
        if include_csv:
            csv_paths = CsvResultWriter().write(result, target / "csv", model)
            paths.update({f"csv_{name}": path for name, path in csv_paths.items()})
        if include_vtu and getattr(result, "analysis", "") in {"linear_static", "nonlinear_static", "transient_dynamic"}:
            paths["vtu"] = target / "result.vtu"
            VtuResultWriter().write(result, model, paths["vtu"])
        paths["manifest"] = target / "evidence_manifest.json"
        write_json_file(paths["manifest"], self._manifest(model, result, target, paths, input_path))
        return paths

    @staticmethod
    def _write_input(model: FiniteElementModel, target: Path, input_path: str | Path | None) -> Path:
        destination = target / "input.json"
        if input_path is not None:
            shutil.copyfile(Path(input_path), destination)
            return destination
        data = {
            "schema_version": model.schema_version,
            "units": model.units,
            "verification_profile": model.verification_profile,
            "analysis": {
                "type": model.analysis.type,
                "method": model.analysis.method,
                "parameters": model.analysis.parameters,
            },
            "nodes": model.nodes.tolist(),
            "elements": [
                {"type": element.type, "nodes": list(element.nodes), "material": element.material}
                for element in model.elements
            ],
            "materials": model.materials,
            "fixed_dofs": [{"node": bc.node, "dofs": list(bc.dofs)} for bc in model.fixed_dofs],
            "loads": [{"node": load.node, "dof": load.dof, "value": load.value} for load in model.loads],
        }
        write_json_file(destination, data)
        return destination

    @staticmethod
    def _solver_settings(model: FiniteElementModel, result: object) -> dict[str, Any]:
        return {
            "analysis": model.analysis.type,
            "method": getattr(result, "method", model.analysis.method),
            "parameters": model.analysis.parameters,
            "solver": getattr(result, "solver", {}),
            "qualification": qualification_metadata(model),
        }

    @staticmethod
    def _manifest(
        model: FiniteElementModel,
        result: object,
        target: Path,
        paths: dict[str, Path],
        input_path: str | Path | None,
    ) -> dict[str, Any]:
        files = [
            manifest_file_entry(role, path, target)
            for role, path in sorted(paths.items())
            if role != "manifest" and path.is_file()
        ]
        return {
            "manifest_schema_version": 2,
            "created_at_utc": utc_timestamp(),
            "solver": {"name": DISPLAY_NAME, "version": __version__},
            "source": git_source_state(Path(__file__).resolve().parents[2]),
            "runtime": runtime_fingerprint(),
            "locked_environments": locked_environment_fingerprints(Path(__file__).resolve().parents[2]),
            "command_line": command_line(),
            "source_input_path": str(Path(input_path).resolve()) if input_path is not None else "",
            "input_sha256": sha256(paths["input"]),
            "analysis": model.analysis.type,
            "method": getattr(result, "method", model.analysis.method),
            "result_status": getattr(result, "status", ""),
            "schema_version": model.schema_version,
            "units": model.units,
            "verification_profile": model.verification_profile,
            "qualification_summary": qualification_summary(result, model),
            "traceability": model_traceability_summary(model),
            "file_count": len(files),
            "files": files,
        }
