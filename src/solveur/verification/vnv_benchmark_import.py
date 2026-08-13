"""Create a controlled V&V study from the existing TET4 cantilever benchmark."""

from __future__ import annotations

from solveur.paths import project_root

import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from solveur.core.errors import InputValidationError
from solveur.io.manifest import sha256, write_json_file
from solveur.version import DISPLAY_NAME, __version__
from solveur.verification.vnv_visualization import (
    plot_tet4_deformation,
    set_equal_3d_axes,
    translations_from_result,
)


BENCHMARK_ID = "BM-SOL-CANTILEVER-001"
DEFAULT_SOURCES = (
    project_root() / "docs" / "generated" / "benchmarks" / BENCHMARK_ID,
    project_root() / "results" / "docs_benchmark_test" / BENCHMARK_ID,
)
REFERENCE_PRODUCER = "Reference analytique Timoshenko"
REFERENCE_VERSION = "timoshenko-cantilever-v1"


class CantileverBenchmarkVnvImporter:
    """Convert the controlled TET4 cantilever mesh levels into a V&V study."""

    def import_study(
        self,
        output_dir: str | Path,
        *,
        source_dir: str | Path | None = None,
        overwrite: bool = False,
    ) -> Path:
        source = _source_directory(source_dir)
        output = Path(output_dir).resolve()
        _prepare_output(output, overwrite)
        summary = _read_json(source / "benchmark_summary.json")
        if summary.get("benchmark", {}).get("identifier") != BENCHMARK_ID:
            raise InputValidationError(f"Source directory is not benchmark {BENCHMARK_ID}: {source}")
        metrics = _object(summary.get("metrics"), "benchmark metrics")
        reference_tip = _finite(metrics.get("reference_tip_uz"), "reference_tip_uz")
        rows = _rows(metrics.get("tet4_h_convergence"))
        if len(rows) < 3:
            raise InputValidationError("Cantilever benchmark must contain at least three TET4 h-levels.")
        levels = [_load_level(source, row) for row in rows]
        length, width, height = _dimensions(levels[0]["model"])
        maximum = max(float(np.max(np.linalg.norm(level["translations"], axis=1))) for level in levels)
        scale = 0.15 * max(length, width, height) / max(maximum, abs(reference_tip), 1.0e-30)
        _write_source_records(output, source, summary, levels)
        reference_png = output / "references" / "timoshenko_deformation.png"
        reference_vtu = output / "references" / "timoshenko_deformation.vtu"
        _plot_reference(reference_png, length, width, height, reference_tip, scale)
        _write_reference_vtu(reference_vtu, length, width, height, reference_tip, scale)
        formula_path = output / "references" / "timoshenko_reference.md"
        formula_path.write_text(_reference_markdown(length, width, height, reference_tip), encoding="utf-8")
        source_manifest = output / "source" / "source_manifest.json"
        study_levels: list[dict[str, Any]] = []
        for index, level in enumerate(levels, start=1):
            level_id = f"h{index}"
            qf_png = output / "results" / f"{level_id}_qf_deformation.png"
            qf_vtu = output / "results" / f"{level_id}_qf_deformation.vtu"
            _plot_qf_deformation(qf_png, level["model"], level["translations"], scale, level_id)
            shutil.copy2(level["source_vtu"], qf_vtu)
            _write_normalized_qf(output, level_id, level, scale, source_manifest)
            _write_normalized_reference(output, level_id, level, reference_tip, scale, reference_png, reference_vtu, formula_path)
            study_levels.append(
                {
                    "id": level_id,
                    "characteristic_size": level["mesh_size"],
                    "qf_result": f"results/{level_id}_qf.json",
                    "reference_result": f"references/{level_id}_timoshenko.json",
                }
            )
        study_path = output / "study.json"
        write_json_file(study_path, _study_payload(study_levels))
        return study_path


def _source_directory(source_dir: str | Path | None) -> Path:
    candidates = (Path(source_dir).resolve(),) if source_dir is not None else DEFAULT_SOURCES
    for candidate in candidates:
        if (candidate / "benchmark_summary.json").is_file():
            return candidate
    formatted = ", ".join(str(item) for item in candidates)
    raise InputValidationError(f"Cannot find {BENCHMARK_ID} benchmark artifacts. Checked: {formatted}")


def _prepare_output(output: Path, overwrite: bool) -> None:
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise InputValidationError(f"V&V output directory is not empty: {output}. Use --overwrite to replace it.")
    if output.exists() and overwrite:
        shutil.rmtree(output)
    for name in ("results", "references", "source"):
        (output / name).mkdir(parents=True, exist_ok=True)


def _load_level(source: Path, row: dict[str, Any]) -> dict[str, Any]:
    level = int(_finite(row.get("level"), "convergence level"))
    prefix = f"tet4_h{level}"
    model_path = source / f"{prefix}.model.json"
    result_path = source / f"{prefix}.json"
    vtu_path = source / f"{prefix}.vtu"
    if not model_path.is_file() or not result_path.is_file() or not vtu_path.is_file():
        raise InputValidationError(f"Missing model, result or VTU for {prefix} in {source}.")
    model = _read_json(model_path)
    result = _read_json(result_path)
    nodes = np.asarray(model.get("nodes"), dtype=float)
    translations = translations_from_result(nodes.shape[0], result)
    return {
        "level": level,
        "mesh_size": _finite(row.get("mesh_size"), f"{prefix}.mesh_size"),
        "tip_uz": _finite(row.get("tip_uz"), f"{prefix}.tip_uz"),
        "relative_error": _finite(row.get("relative_error"), f"{prefix}.relative_error"),
        "free_relative_residual": _finite(row.get("free_relative_residual"), f"{prefix}.free_relative_residual"),
        "model": model,
        "result": result,
        "translations": translations,
        "source_model": model_path,
        "source_result": result_path,
        "source_vtu": vtu_path,
    }


def _write_source_records(output: Path, source: Path, summary: dict[str, Any], levels: list[dict[str, Any]]) -> None:
    copied_summary = output / "source" / "benchmark_summary.json"
    shutil.copy2(source / "benchmark_summary.json", copied_summary)
    records = {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_source": source.name,
        "benchmark_summary_sha256": sha256(copied_summary),
        "levels": [],
    }
    for index, level in enumerate(levels, start=1):
        copied_model = output / "source" / f"h{index}_model.json"
        shutil.copy2(level["source_model"], copied_model)
        records["levels"].append(
            {
                "id": f"h{index}",
                "source_result": f"{source.name}/{level['source_result'].name}",
                "source_result_sha256": sha256(level["source_result"]),
                "source_model": f"{source.name}/{level['source_model'].name}",
                "source_model_sha256": sha256(copied_model),
                "source_vtu": f"{source.name}/{level['source_vtu'].name}",
                "source_vtu_sha256": sha256(level["source_vtu"]),
            }
        )
    write_json_file(output / "source" / "source_manifest.json", records)


def _write_normalized_qf(
    output: Path,
    level_id: str,
    level: dict[str, Any],
    scale: float,
    source_manifest: Path,
) -> None:
    model = level["model"]
    result = level["result"]
    payload = {
        "schema_version": 1,
        "case_id": "VNV-TET4-CANTILEVER-ANALYTIC-001",
        "producer": {"name": DISPLAY_NAME, "version": __version__, "run_id": f"{BENCHMARK_ID}-{level_id}"},
        "units_system": "SI",
        "mesh": {
            "nodes": int(len(model["nodes"])),
            "elements": int(len(model["elements"])),
            "dofs": int(result["ndof"]),
            "characteristic_size": level["mesh_size"],
        },
        "quantities": {"tip_uz": {"value": level["tip_uz"], "unit": "m"}},
        "diagnostics": {
            "free_relative_residual": level["free_relative_residual"],
            "source_result_sha256": sha256(level["source_result"]),
            "source_result_path": f"{BENCHMARK_ID}/{level['source_result'].name}",
        },
        "visualization": {
            "deformation_scale": scale,
            "field": "displacement_magnitude",
            "view": "isometric_xyz",
            "undeformed_overlay": True,
        },
        "artifacts": {
            "deformation_png": f"{level_id}_qf_deformation.png",
            "deformation_vtu": f"{level_id}_qf_deformation.vtu",
            "source_model": f"../source/{level_id}_model.json",
            "source_manifest": "../source/source_manifest.json",
        },
    }
    write_json_file(output / "results" / f"{level_id}_qf.json", payload)


def _write_normalized_reference(
    output: Path,
    level_id: str,
    level: dict[str, Any],
    tip: float,
    scale: float,
    png: Path,
    vtu: Path,
    formula: Path,
) -> None:
    payload = {
        "schema_version": 1,
        "case_id": "VNV-TET4-CANTILEVER-ANALYTIC-001",
        "producer": {"name": REFERENCE_PRODUCER, "version": REFERENCE_VERSION, "run_id": f"TIMOSHENKO-{level_id}"},
        "units_system": "SI",
        "mesh": {
            "nodes": 101,
            "elements": 100,
            "dofs": 303,
            "characteristic_size": level["mesh_size"],
        },
        "quantities": {"tip_uz": {"value": tip, "unit": "m"}},
        "diagnostics": {"reference_type": "analytic", "formulation": "Timoshenko cantilever end-load"},
        "visualization": {
            "deformation_scale": scale,
            "field": "displacement_magnitude",
            "view": "isometric_xyz",
            "undeformed_overlay": True,
        },
        "artifacts": {
            "deformation_png": png.name,
            "deformation_vtu": vtu.name,
            "reference_formula": formula.name,
        },
    }
    write_json_file(output / "references" / f"{level_id}_timoshenko.json", payload)


def _study_payload(levels: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study_id": "VNV-TET4-CANTILEVER-ANALYTIC-001",
        "title": "Verification TET4 - convergence en flexion d'un porte-a-faux",
        "scope": "tet4-linear-static",
        "subject": {"kind": "element", "name": "TET4", "maturity": "stable_after_reinforced_tests"},
        "units_system": "SI",
        "author": {"name": "Quentin Farinazzo", "role": "auteur du solveur"},
        "validation": {
            "validator": {"name": "Quentin Farinazzo", "role": "validateur mecanique"},
            "mode": "self_review",
            "decision": "pending",
            "date": None,
            "comments": "",
        },
        "reference": {
            "kind": "analytic",
            "solver": REFERENCE_PRODUCER,
            "version": REFERENCE_VERSION,
            "manual_citation": "Poutre de Timoshenko sous charge en bout; expression utilisee par BM-SOL-CANTILEVER-001.",
            "case": "Porte-a-faux 3D L=8 m, section 1 m x 1 m, force verticale -1000 N.",
        },
        "quantities": [
            {
                "id": "tip_uz",
                "label": "Deplacement vertical moyen de la face libre",
                "metric": "relative_error",
                "limit": 0.5,
                "absolute_floor": 1.0e-15,
                "extraction": {
                    "location": "surface=x_max",
                    "component": "UZ",
                    "reduction": "average",
                },
            }
        ],
        "levels": levels,
        "convergence": [
            {
                "quantity": "tip_uz",
                "require_monotonic": True,
                "minimum_order": 1.0,
                "finest_error_limit": 0.2,
            }
        ],
        "acceptance": {"deformation_requirement": "all"},
    }


def _plot_qf_deformation(path: Path, model: dict[str, Any], translations: np.ndarray, scale: float, level: str) -> None:
    plot_tet4_deformation(path, model, translations, scale, title=f"QF_solver TET4 - deformee {level}")


def _plot_reference(path: Path, length: float, width: float, height: float, tip: float, scale: float) -> None:
    x = np.linspace(0.0, length, 101)
    z0 = np.full_like(x, 0.5 * height)
    y = np.full_like(x, 0.5 * width)
    deformation = _normalized_timoshenko_shape(x, length, tip)
    figure = plt.figure(figsize=(8.2, 5.8))
    axis = figure.add_subplot(111, projection="3d")
    axis.plot(x, y, z0, color="#7f8c8d", linestyle="--", linewidth=1.2, label="forme initiale")
    axis.plot(x, y, z0 + scale * deformation, color="#007f7b", linewidth=2.8, label="reference Timoshenko")
    points = np.vstack((np.column_stack((x, y, z0)), np.column_stack((x, y, z0 + scale * deformation))))
    set_equal_3d_axes(axis, points)
    axis.set_xlabel("X [m]")
    axis.set_ylabel("Y [m]")
    axis.set_zlabel("Z [m]")
    axis.set_title(f"Reference analytique Timoshenko\nAmplification = {scale:.4g}")
    axis.view_init(elev=25.0, azim=-56.0)
    axis.legend(loc="upper left")
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _write_reference_vtu(path: Path, length: float, width: float, height: float, tip: float, scale: float) -> None:
    x = np.linspace(0.0, length, 101)
    displacement = _normalized_timoshenko_shape(x, length, tip)
    points = [(float(value), 0.5 * width, 0.5 * height + scale * float(w)) for value, w in zip(x, displacement)]
    connectivity = " ".join(f"{index} {index + 1}" for index in range(len(points) - 1))
    offsets = " ".join(str(2 * (index + 1)) for index in range(len(points) - 1))
    types = " ".join("3" for _ in range(len(points) - 1))
    coordinates = " ".join(f"{a:.16e} {b:.16e} {c:.16e}" for a, b, c in points)
    values = " ".join(f"{value:.16e}" for value in displacement)
    path.write_text(
        "<?xml version=\"1.0\"?>\n"
        "<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">\n"
        "  <UnstructuredGrid>\n"
        f"    <Piece NumberOfPoints=\"{len(points)}\" NumberOfCells=\"{len(points) - 1}\">\n"
        "      <PointData Scalars=\"UZ\"><DataArray type=\"Float64\" Name=\"UZ\" format=\"ascii\">"
        f"{values}</DataArray></PointData>\n"
        "      <Points><DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">"
        f"{coordinates}</DataArray></Points>\n"
        "      <Cells>\n"
        f"        <DataArray type=\"Int64\" Name=\"connectivity\" format=\"ascii\">{connectivity}</DataArray>\n"
        f"        <DataArray type=\"Int64\" Name=\"offsets\" format=\"ascii\">{offsets}</DataArray>\n"
        f"        <DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">{types}</DataArray>\n"
        "      </Cells>\n    </Piece>\n  </UnstructuredGrid>\n</VTKFile>\n",
        encoding="utf-8",
    )


def _dimensions(model: dict[str, Any]) -> tuple[float, float, float]:
    nodes = np.asarray(model["nodes"], dtype=float)
    extent = np.max(nodes, axis=0) - np.min(nodes, axis=0)
    return tuple(float(value) for value in extent)


def _normalized_timoshenko_shape(x: np.ndarray, length: float, tip: float) -> np.ndarray:
    ratio = x / length
    bending = 0.96 * ratio**2 * (3.0 - ratio) / 2.0
    shear = 0.04 * ratio
    return tip * (bending + shear)


def _reference_markdown(length: float, width: float, height: float, tip: float) -> str:
    return (
        "# Reference analytique Timoshenko\n\n"
        "Cette reference est une solution de poutre de Timoshenko sous force terminale, "
        "utilisee uniquement pour comparer le deplacement vertical moyen de la face libre.\n\n"
        f"- Longueur : {length:.6g} m\n- Section : {width:.6g} m x {height:.6g} m\n"
        f"- Deplacement terminal de reference : {tip:.12e} m\n\n"
        "La PNG et le VTU de reference representent la ligne moyenne analytique. Ils ne doivent "
        "pas etre interpretes comme un champ 3D de contraintes.\n"
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Cannot read benchmark JSON {path}: {exc}") from exc


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputValidationError(f"{label} must be a JSON object.")
    return value


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
        raise InputValidationError("tet4_h_convergence must be a non-empty array of objects.")
    return value


def _finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be numeric.") from exc
    if not np.isfinite(number):
        raise InputValidationError(f"{label} must be finite.")
    return number
