"""Safe in-process runner for registered QF Solver V&V models."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from solveur.core.router import AnalysisRouter
from solveur.io.json_reader import JsonModelReader

from .case import VnvCase
from .environment import capture_environment
from .manifest import write_manifest
from .registry import VnvRegistry, canonical_json
from .result import VnvCaseResult


class VnvRunner:
    """Execute only explicit JSON-model cases from a validated registry.

    The runner has no generic shell command escape hatch.  External-oracle
    execution belongs to explicit future adapters, never to arbitrary strings
    embedded in case JSON.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parents[4]).resolve()

    def run(
        self,
        registry: VnvRegistry,
        output_dir: str | Path,
        *,
        profile: str = "SMOKE",
        case_ids: Iterable[str] = (),
        tags: Iterable[str] = (),
        resume: bool = False,
    ) -> dict[str, Any]:
        selected = registry.select(case_ids=case_ids, profile=profile, tags=tags)
        if not selected:
            raise ValueError(f"No READY V&V cases selected for profile {profile!r}.")
        target = Path(output_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)
        environment = capture_environment(self.project_root)
        run_id = f"vnv026-{profile.lower()}-{registry.digest[:12]}"
        result_paths = [self._run_case(case, target, run_id, environment, resume=resume) for case in selected]
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in result_paths]
        manifest = write_manifest(
            target,
            source=environment["source"],
            registry_digest=registry.digest,
            profile=profile.upper(),
            result_paths=result_paths,
            environment=environment,
        )
        summary = {
            "schema_version": 1,
            "run_id": run_id,
            "profile": profile.upper(),
            "source": environment["source"],
            "registry_digest": registry.digest,
            "case_count": len(rows),
            "pass_count": sum(row["status"] == "PASS" for row in rows),
            "expected_failure_count": sum(row["status"] == "EXPECTED_FAILURE" for row in rows),
            "failed_count": sum(row["status"] == "FAIL" for row in rows),
            "blocked_count": sum(row["status"] == "BLOCKED" for row in rows),
            "status": "PASS" if all(row["status"] in {"PASS", "EXPECTED_FAILURE"} for row in rows) else "FAIL",
            "results": [path.name for path in result_paths],
            "manifest": manifest.name,
        }
        (target / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def _run_case(
        self,
        case: VnvCase,
        output_dir: Path,
        run_id: str,
        environment: dict[str, Any],
        *,
        resume: bool,
    ) -> Path:
        result_path = output_dir / f"{case.case_id.lower()}.json"
        if resume and result_path.exists():
            previous = json.loads(result_path.read_text(encoding="utf-8"))
            if previous.get("source_sha") == environment["source"]["sha"]:
                return result_path
        started = perf_counter()
        try:
            model_path = self._model_path(case)
            raw_model = json.loads(model_path.read_text(encoding="utf-8"))
            _apply_model_overrides(raw_model, case.model_overrides)
            model = JsonModelReader().from_dict(raw_model)
            result_data = AnalysisRouter().solve(model).to_dict()
            actual_status = str(result_data.get("status", "FAIL")).upper()
            if case.expected_failure:
                status = "FAIL"
                failure_category = "UNEXPECTED_SUCCESS"
                diagnostics = {"message": "Case was expected to fail but returned a result.", "result_status": actual_status}
            elif actual_status in {"PASS", "SUCCESS"}:
                status = "PASS"
                failure_category = None
                diagnostics = {"result_status": actual_status}
            else:
                status = "FAIL"
                failure_category = "SOLVER_REPORTED_FAILURE"
                diagnostics = {"result_status": actual_status, "message": result_data.get("message", "")}
            metrics = _metrics(result_data)
        except Exception as exc:  # controlled expected-failure cases deliberately exercise this path
            if case.expected_failure:
                status = "EXPECTED_FAILURE"
                failure_category = case.expected_failure
            else:
                status = "FAIL"
                failure_category = "UNEXPECTED_EXCEPTION"
            diagnostics = {"exception_type": type(exc).__name__, "message": str(exc)}
            metrics = {}
        case_payload_digest = hashlib.sha256(
            canonical_json(
                {
                    "case_id": case.case_id,
                    "status": status,
                    "failure_category": failure_category,
                    "metrics": metrics,
                    "diagnostics": diagnostics,
                }
            ).encode("utf-8")
        ).hexdigest()
        final = VnvCaseResult(
            case_id=case.case_id,
            run_id=run_id,
            source_sha=environment["source"]["sha"],
            timestamp_utc=environment["captured_at_utc"],
            solver_version=environment["solver_version"],
            status=status,
            failure_category=failure_category,
            environment=environment,
            configuration={
                "analysis_type": case.analysis_type,
                "solver_configuration": dict(case.solver_configuration),
                "cost_profile": case.cost_profile,
            },
            threshold_source="qualification/0_2_6/tolerance_policy.json",
            metrics=metrics,
            diagnostics=diagnostics,
            artifact_digests={"case_payload": case_payload_digest},
            wall_time_seconds=perf_counter() - started,
        )
        result_path.write_text(json.dumps(final.to_mapping(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result_path

    def _model_path(self, case: VnvCase) -> Path:
        if not case.input_model:
            raise ValueError(f"{case.case_id} has no executable model.")
        candidate = (self.project_root / case.input_model).resolve()
        examples_root = (self.project_root / "examples").resolve()
        if examples_root not in candidate.parents or candidate.suffix.lower() != ".json":
            raise ValueError(f"{case.case_id} model path is outside the controlled examples directory.")
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate


def _metrics(result: dict[str, Any]) -> dict[str, Any]:
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    values = {
        "analysis": result.get("analysis"),
        "node_count": result.get("node_count"),
        "element_count": result.get("element_count"),
        "n_dof": result.get("ndof"),
        "max_displacement": result.get("max_displacement"),
        "iterations": solver.get("iterations"),
        "residual_norm": solver.get("residual_norm"),
        "relative_residual_norm": solver.get("relative_residual_norm"),
    }
    values["numerical_fingerprint"] = hashlib.sha256(canonical_json(values).encode("utf-8")).hexdigest()
    return values


def _apply_model_overrides(model: dict[str, Any], overrides: dict[str, Any]) -> None:
    """Apply only declared, deterministic model perturbations for V&V variants."""

    if not overrides:
        return
    allowed = {"load_scale", "analysis", "material_updates"}
    unknown = set(overrides).difference(allowed)
    if unknown:
        raise ValueError(f"Unsupported V&V model overrides: {', '.join(sorted(unknown))}.")
    load_scale = overrides.get("load_scale", 1.0)
    if not isinstance(load_scale, (int, float)) or isinstance(load_scale, bool) or load_scale <= 0:
        raise ValueError("V&V load_scale must be a positive number.")
    if load_scale != 1.0:
        for load in model.get("loads", []):
            if isinstance(load, dict) and isinstance(load.get("value"), (int, float)):
                load["value"] *= load_scale
    analysis_updates = overrides.get("analysis", {})
    if not isinstance(analysis_updates, dict):
        raise ValueError("V&V analysis overrides must be an object.")
    if analysis_updates:
        current_analysis = model.get("analysis", {})
        if isinstance(current_analysis, str):
            model["analysis"] = {"type": current_analysis}
        elif not isinstance(current_analysis, dict):
            raise ValueError("V&V model analysis must be an object or analysis type string.")
        model.setdefault("analysis", {}).update(deepcopy(analysis_updates))
    material_updates = overrides.get("material_updates", {})
    if not isinstance(material_updates, dict):
        raise ValueError("V&V material_updates must be an object.")
    for material_name, updates in material_updates.items():
        if material_name not in model.get("materials", {}) or not isinstance(updates, dict):
            raise ValueError(f"Invalid V&V material override for {material_name!r}.")
        model["materials"][material_name].update(deepcopy(updates))
