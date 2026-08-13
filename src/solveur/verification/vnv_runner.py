"""Execute traceable comparisons against analytic or commercial references."""

from __future__ import annotations

from solveur.paths import project_root

import math
import shutil
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.io.manifest import (
    command_line,
    discovered_file_entries,
    git_source_state,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.verification.vnv_report import write_vnv_report
from solveur.verification.vnv_schema import VnvResultLoader, VnvStudyLoader
from solveur.verification.vnv_types import VnvNormalizedResult, VnvQuantitySpec, VnvStudy, VnvStudyRun
from solveur.version import DISPLAY_NAME, __version__


class VnvStudyRunner:
    """Compare QF_solver to normalized references and create an auditable Markdown study."""

    def run(self, study_path: str | Path, output_dir: str | Path) -> VnvStudyRun:
        study = VnvStudyLoader().load(study_path)
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        comparisons: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        loaded: list[tuple[str, str, VnvNormalizedResult]] = []
        comparison_by_quantity: dict[str, list[dict[str, Any]]] = {
            item.identifier: [] for item in study.quantities
        }
        artifacts: list[dict[str, Any]] = []
        for index, level in enumerate(study.levels):
            qf = VnvResultLoader().load(level.qf_result, study=study, role="qf")
            reference = VnvResultLoader().load(level.reference_result, study=study, role="reference")
            loaded.extend(((level.identifier, "qf_result", qf), (level.identifier, "reference_result", reference)))
            checks.extend(_visualization_checks(level.identifier, qf, reference))
            for spec in study.quantities:
                row = _compare(level.identifier, level.characteristic_size, spec, qf, reference)
                comparisons.append(row)
                comparison_by_quantity[spec.identifier].append(row)
                checks.append(
                    _check(
                        f"CMP-{level.identifier}-{spec.identifier}",
                        row["metric_value"],
                        row["limit"],
                        row["status"],
                        f"{spec.metric}; unit={row['unit']}",
                    )
                )
            level_artifacts = _copy_artifacts(output, level.identifier, qf, reference)
            artifacts.extend(level_artifacts)
            if _deformation_required(study, index):
                checks.extend(_deformation_checks(level.identifier, level_artifacts))
        convergence, convergence_checks = _convergence(study, comparison_by_quantity)
        checks.extend(convergence_checks)
        artifacts.extend(_copy_source_inputs(output, study, loaded))
        automated_verdict = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
        human_decision = str(study.validation["decision"])
        status = _overall_status(automated_verdict, human_decision)
        run = VnvStudyRun(
            study,
            status,
            automated_verdict,
            human_decision,
            comparisons,
            convergence,
            checks,
            artifacts,
            {
                "comparison": "comparison.json",
                "report": "study_report.md",
                "manifest": "vnv_manifest.json",
            },
        )
        plot_path = write_vnv_report(run, output / run.files["report"])
        if plot_path is not None:
            run.files["convergence_plot"] = plot_path.name
        write_json_file(output / run.files["comparison"], run.to_dict())
        _write_manifest(output, run, loaded)
        return run


def _compare(
    level: str,
    characteristic_size: float,
    spec: VnvQuantitySpec,
    qf: VnvNormalizedResult,
    reference: VnvNormalizedResult,
) -> dict[str, Any]:
    if spec.identifier not in qf.quantities or spec.identifier not in reference.quantities:
        raise InputValidationError(f"Quantity {spec.identifier!r} is missing from one normalized result.")
    qf_value = qf.quantities[spec.identifier]
    reference_value = reference.quantities[spec.identifier]
    if qf_value.unit != reference_value.unit:
        raise InputValidationError(
            f"Unit mismatch for {spec.identifier}: QF_solver={qf_value.unit!r}, reference={reference_value.unit!r}."
        )
    absolute_error = abs(qf_value.value - reference_value.value)
    relative_error = absolute_error / max(abs(reference_value.value), spec.absolute_floor)
    metric_value = relative_error if spec.metric == "relative_error" else absolute_error
    return {
        "level": level,
        "h": characteristic_size,
        "quantity": spec.identifier,
        "label": spec.label,
        "qf": qf_value.value,
        "reference": reference_value.value,
        "unit": qf_value.unit,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "metric": spec.metric,
        "metric_value": metric_value,
        "limit": spec.limit,
        "status": "PASS" if metric_value <= spec.limit else "FAIL",
    }


def _convergence(
    study: VnvStudy,
    rows_by_quantity: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    for spec in study.convergence:
        rows = rows_by_quantity[spec.quantity]
        errors = [float(row["metric_value"]) for row in rows]
        sizes = [float(row["h"]) for row in rows]
        monotonic = all(fine <= coarse + 1.0e-15 for coarse, fine in zip(errors, errors[1:]))
        order = _observed_order(sizes, errors)
        finest = errors[-1]
        statuses = [finest <= spec.finest_error_limit]
        checks.append(
            _check(
                f"CONV-{spec.quantity}-finest",
                finest,
                spec.finest_error_limit,
                "PASS" if statuses[-1] else "FAIL",
                "finest-mesh error",
            )
        )
        if spec.require_monotonic:
            statuses.append(monotonic)
            checks.append(
                {
                    "id": f"CONV-{spec.quantity}-monotonic",
                    "value": monotonic,
                    "expected": True,
                    "status": "PASS" if monotonic else "FAIL",
                    "detail": "error must not increase under h-refinement",
                }
            )
        if spec.minimum_order is not None:
            order_passed = order is None or order >= spec.minimum_order
            statuses.append(order_passed)
            checks.append(
                {
                    "id": f"CONV-{spec.quantity}-order",
                    "value": order,
                    "limit": spec.minimum_order,
                    "operator": "greater_equal",
                    "status": "PASS" if order_passed else "FAIL",
                    "detail": "None means exact agreement at numerical precision",
                }
            )
        records.append(
            {
                "quantity": spec.quantity,
                "metric": rows[0]["metric"],
                "series": [{"level": row["level"], "h": row["h"], "error": row["metric_value"]} for row in rows],
                "finest_error": finest,
                "finest_error_limit": spec.finest_error_limit,
                "observed_order": order,
                "minimum_order": spec.minimum_order,
                "monotonic": monotonic,
                "status": "PASS" if all(statuses) else "FAIL",
            }
        )
    return records, checks


def _observed_order(sizes: list[float], errors: list[float]) -> float | None:
    if all(error <= 1.0e-15 for error in errors):
        return None
    positive = [(math.log(size), math.log(error)) for size, error in zip(sizes, errors) if error > 0.0]
    if len(positive) < 2:
        return None
    mean_x = sum(item[0] for item in positive) / len(positive)
    mean_y = sum(item[1] for item in positive) / len(positive)
    denominator = sum((item[0] - mean_x) ** 2 for item in positive)
    if denominator == 0.0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in positive) / denominator


def _copy_artifacts(
    output: Path,
    level: str,
    qf: VnvNormalizedResult,
    reference: VnvNormalizedResult,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for producer_role, result in (("qf", qf), ("reference", reference)):
        for key, source in sorted(result.artifacts.items()):
            if not source.is_file():
                raise InputValidationError(f"Declared V&V artifact does not exist: {source}")
            suffix = "".join(source.suffixes) or ".dat"
            destination = output / "artifacts" / level / f"{producer_role}_{key}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            records.append(
                {
                    "level": level,
                    "producer_role": producer_role,
                    "artifact_key": key,
                    "role": f"{producer_role}_{key}",
                    "path": destination.relative_to(output).as_posix(),
                    "size_bytes": destination.stat().st_size,
                    "sha256": sha256(destination),
                    "visualization": result.visualization,
                }
            )
    return records


def _copy_source_inputs(
    output: Path,
    study: VnvStudy,
    loaded: list[tuple[str, str, VnvNormalizedResult]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    sources: list[tuple[str, str, str, Path, dict[str, Any]]] = [
        ("study", "control", "study_definition", study.source_path, {}),
    ]
    for level, role, result in loaded:
        producer = "qf" if role == "qf_result" else "reference"
        sources.append((level, producer, "normalized_result", result.source_path, result.visualization))
    for level, producer, key, source, visualization in sources:
        filename = "study.json" if level == "study" else f"{level}_{producer}.json"
        destination = output / "inputs" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        records.append(
            {
                "level": level,
                "producer_role": producer,
                "artifact_key": key,
                "role": f"{producer}_{key}",
                "path": destination.relative_to(output).as_posix(),
                "size_bytes": destination.stat().st_size,
                "sha256": sha256(destination),
                "visualization": visualization,
            }
        )
    return records


def _deformation_required(study: VnvStudy, level_index: int) -> bool:
    if study.deformation_requirement == "none":
        return False
    if study.deformation_requirement == "all":
        return True
    return level_index == len(study.levels) - 1


def _deformation_checks(level: str, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = {(item["producer_role"], item["artifact_key"]) for item in artifacts}
    checks = []
    for producer in ("qf", "reference"):
        for key in ("deformation_png", "deformation_vtu"):
            present = (producer, key) in available
            checks.append(
                {
                    "id": f"ART-{level}-{producer}-{key}",
                    "value": present,
                    "expected": True,
                    "status": "PASS" if present else "FAIL",
                    "detail": "visual and field deformation evidence",
                }
            )
    return checks


def _visualization_checks(
    level: str,
    qf: VnvNormalizedResult,
    reference: VnvNormalizedResult,
) -> list[dict[str, Any]]:
    qf_scale = float(qf.visualization["deformation_scale"])
    reference_scale = float(reference.visualization["deformation_scale"])
    scale_error = abs(qf_scale - reference_scale) / max(abs(reference_scale), 1.0e-15)
    checks = [
        _check(
            f"VIS-{level}-scale",
            scale_error,
            1.0e-12,
            "PASS" if scale_error <= 1.0e-12 else "FAIL",
            f"QF={qf_scale:.6e}; reference={reference_scale:.6e}",
        )
    ]
    for key in ("field", "view"):
        matches = qf.visualization[key] == reference.visualization[key]
        checks.append(
            {
                "id": f"VIS-{level}-{key}",
                "value": qf.visualization[key],
                "expected": reference.visualization[key],
                "status": "PASS" if matches else "FAIL",
                "detail": "visual comparison metadata must match",
            }
        )
    return checks


def _check(identifier: str, value: float, limit: float, status: str, detail: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "operator": "less_equal",
        "status": status,
        "detail": detail,
    }


def _overall_status(automated: str, human: str) -> str:
    if automated == "FAIL":
        return "FAIL"
    if human == "rejected":
        return "REJECTED"
    if human == "accepted":
        return "ACCEPTED"
    if human == "accepted_with_reservations":
        return "ACCEPTED_WITH_RESERVATIONS"
    return "PENDING_REVIEW"


def _write_manifest(
    output: Path,
    run: VnvStudyRun,
    loaded: list[tuple[str, str, VnvNormalizedResult]],
) -> None:
    source_inputs = [
        {
            "role": "study_definition",
            "path": str(run.study.source_path),
            "size_bytes": run.study.source_path.stat().st_size,
            "sha256": sha256(run.study.source_path),
        }
    ]
    for level, role, result in loaded:
        source_inputs.append(
            {
                "level": level,
                "role": role,
                "path": str(result.source_path),
                "producer": result.producer,
                "size_bytes": result.source_path.stat().st_size,
                "sha256": sha256(result.source_path),
            }
        )
    payload = {
        "manifest_schema_version": 1,
        "created_at_utc": utc_timestamp(),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "study_id": run.study.identifier,
        "status": run.status,
        "automated_verdict": run.automated_verdict,
        "human_decision": run.human_decision,
        "source": git_source_state(project_root()),
        "runtime": runtime_fingerprint(),
        "command": command_line(),
        "source_inputs": source_inputs,
        "files": discovered_file_entries(
            output,
            lambda relative: "vnv_artifact" if relative.startswith("artifacts/") else Path(relative).stem,
            exclude_names=(run.files["manifest"],),
        ),
    }
    write_json_file(output / run.files["manifest"], payload)
