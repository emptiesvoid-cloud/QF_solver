"""Build a controlled Saint-Venant torsion V&V study from benchmark evidence."""

from __future__ import annotations

from solveur.paths import project_root

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.io.manifest import sha256, write_json_file
from solveur.version import DISPLAY_NAME, __version__
from solveur.verification.vnv_visualization import (
    load_vtu_displacements,
    plot_tet4_deformation,
    write_tet4_displacement_vtu,
)


BENCHMARK_ID = "BM-SOL-TET4-TORSION-001"
STUDY_ID = "VNV-TET4-TORSION-ANALYTIC-001"
REFERENCE_PRODUCER = "Reference analytique Saint-Venant"
REFERENCE_VERSION = "saint-venant-circular-shaft-v1"
DEFAULT_SOURCES = (
    project_root() / "docs" / "generated" / "benchmarks" / BENCHMARK_ID,
    project_root() / "results" / "docs_benchmark_test" / BENCHMARK_ID,
)


class TorsionBenchmarkVnvImporter:
    """Convert the eight-level circular-shaft benchmark into V&V evidence."""

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
        rows = _rows(metrics.get("torsion_h_convergence"))
        if len(rows) < 3:
            raise InputValidationError("Torsion benchmark must contain at least three h-levels.")
        reference_twist = _finite(metrics.get("reference_twist_angle"), "reference_twist_angle")
        shear_modulus = _finite(metrics.get("shear_modulus"), "shear_modulus")
        polar_moment = _finite(metrics.get("polar_moment"), "polar_moment")
        levels = [_load_level(source, row, reference_twist) for row in rows]
        maximum_displacement = max(
            float(np.max(np.linalg.norm(field, axis=1)))
            for level in levels
            for field in (level["qf_translations"], level["reference_translations"])
        )
        length = float(np.ptp(np.asarray(levels[0]["model"]["nodes"], dtype=float)[:, 0]))
        scale = 0.18 * length / max(maximum_displacement, 1.0e-30)
        formula = output / "references" / "saint_venant_reference.md"
        formula.write_text(
            _reference_markdown(reference_twist, shear_modulus, polar_moment),
            encoding="utf-8",
        )
        source_manifest = _write_source_records(output, source, summary, levels)
        study_levels: list[dict[str, Any]] = []
        for index, level in enumerate(levels, start=1):
            level_id = f"h{index}"
            _write_level_artifacts(output, level_id, level, scale)
            _write_normalized_qf(output, level_id, level, scale, source_manifest)
            _write_normalized_reference(output, level_id, level, scale, formula)
            study_levels.append(
                {
                    "id": level_id,
                    "characteristic_size": level["mesh_size"],
                    "qf_result": f"results/{level_id}_qf.json",
                    "reference_result": f"references/{level_id}_saint_venant.json",
                }
            )
        study_path = output / "study.json"
        write_json_file(study_path, _study_payload(study_levels))
        (output / "STUDY.md").write_text(_study_markdown(levels, scale), encoding="utf-8")
        (output / "commercial_reference" / "README.md").write_text(
            _commercial_reference_markdown(len(levels)),
            encoding="utf-8",
        )
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
    for name in ("results", "references", "source", "commercial_reference"):
        (output / name).mkdir(parents=True, exist_ok=True)


def _load_level(source: Path, row: dict[str, Any], reference_twist: float) -> dict[str, Any]:
    level = int(_finite(row.get("level"), "convergence level"))
    prefix = f"h{level}"
    paths = {suffix: source / f"{prefix}.{suffix}" for suffix in ("model.json", "json", "vtu", "msh", "setup.json")}
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise InputValidationError(f"Missing torsion benchmark artifacts for {prefix}: {missing}")
    model = _read_json(paths["model.json"])
    nodes = np.asarray(model.get("nodes"), dtype=float)
    if nodes.ndim != 2 or nodes.shape[1] != 3:
        raise InputValidationError(f"Invalid node array in {paths['model.json']}.")
    qf_translations = load_vtu_displacements(paths["vtu"], len(nodes))
    reference_translations = _saint_venant_displacements(nodes, reference_twist)
    return {
        "level": level,
        "mesh_size": _finite(row.get("mesh_size"), f"{prefix}.mesh_size"),
        "twist_angle": _finite(row.get("twist_angle"), f"{prefix}.twist_angle"),
        "reference_twist_angle": _finite(row.get("reference_twist_angle"), f"{prefix}.reference_twist_angle"),
        "relative_twist_error": _finite(row.get("relative_twist_error"), f"{prefix}.relative_twist_error"),
        "relative_stress_l2_error": _finite(
            row.get("relative_stress_l2_error"), f"{prefix}.relative_stress_l2_error"
        ),
        "applied_torque": _finite(row.get("applied_torque"), f"{prefix}.applied_torque"),
        "resultant_force_norm": _finite(row.get("resultant_force_norm"), f"{prefix}.resultant_force_norm"),
        "free_relative_residual": _finite(
            row.get("free_relative_residual"), f"{prefix}.free_relative_residual"
        ),
        "model": model,
        "qf_translations": qf_translations,
        "reference_translations": reference_translations,
        "paths": paths,
    }


def _saint_venant_displacements(nodes: np.ndarray, end_twist: float) -> np.ndarray:
    x = nodes[:, 0]
    length = float(np.max(x) - np.min(x))
    if length <= 0.0:
        raise InputValidationError("Torsion V&V model must have a positive X extent.")
    angle = end_twist * (x - float(np.min(x))) / length
    values = np.zeros_like(nodes)
    values[:, 1] = -angle * nodes[:, 2]
    values[:, 2] = angle * nodes[:, 1]
    return values


def _write_source_records(
    output: Path,
    source: Path,
    summary: dict[str, Any],
    levels: list[dict[str, Any]],
) -> Path:
    summary_path = output / "source" / "benchmark_summary.json"
    shutil.copy2(source / "benchmark_summary.json", summary_path)
    records: dict[str, Any] = {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_source": source.name,
        "benchmark_summary_sha256": sha256(summary_path),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "load_definition": "solveur.benchmarks.solid_extended.apply_consistent_circular_torsion",
        "levels": [],
    }
    for index, level in enumerate(levels, start=1):
        level_id = f"h{index}"
        paths = level["paths"]
        copied: dict[str, Path] = {}
        for key, suffix in (("model", "model.json"), ("mesh", "msh"), ("setup", "setup.json")):
            destination = output / "source" / f"{level_id}.{suffix}"
            shutil.copy2(paths[suffix], destination)
            copied[key] = destination
        records["levels"].append(
            {
                "id": level_id,
                "source_result": f"{source.name}/{paths['json'].name}",
                "source_result_sha256": sha256(paths["json"]),
                "source_vtu": f"{source.name}/{paths['vtu'].name}",
                "source_vtu_sha256": sha256(paths["vtu"]),
                "model": copied["model"].name,
                "model_sha256": sha256(copied["model"]),
                "mesh": copied["mesh"].name,
                "mesh_sha256": sha256(copied["mesh"]),
                "setup": copied["setup"].name,
                "setup_sha256": sha256(copied["setup"]),
            }
        )
    manifest = output / "source" / "source_manifest.json"
    write_json_file(manifest, records)
    return manifest


def _write_level_artifacts(output: Path, level_id: str, level: dict[str, Any], scale: float) -> None:
    qf_png = output / "results" / f"{level_id}_qf_deformation.png"
    qf_vtu = output / "results" / f"{level_id}_qf_deformation.vtu"
    reference_png = output / "references" / f"{level_id}_saint_venant_deformation.png"
    reference_vtu = output / "references" / f"{level_id}_saint_venant_deformation.vtu"
    plot_tet4_deformation(
        qf_png,
        level["model"],
        level["qf_translations"],
        scale,
        title=f"QF_solver TET4 - torsion {level_id}",
        view=(22.0, -60.0),
    )
    shutil.copy2(level["paths"]["vtu"], qf_vtu)
    plot_tet4_deformation(
        reference_png,
        level["model"],
        level["reference_translations"],
        scale,
        title=f"Saint-Venant analytique - torsion {level_id}",
        view=(22.0, -60.0),
    )
    write_tet4_displacement_vtu(reference_vtu, level["model"], level["reference_translations"])


def _write_normalized_qf(
    output: Path,
    level_id: str,
    level: dict[str, Any],
    scale: float,
    source_manifest: Path,
) -> None:
    node_count = len(level["model"]["nodes"])
    payload = {
        "schema_version": 1,
        "case_id": STUDY_ID,
        "producer": {"name": DISPLAY_NAME, "version": __version__, "run_id": f"{BENCHMARK_ID}-{level_id}"},
        "units_system": "SI",
        "mesh": {
            "nodes": node_count,
            "elements": len(level["model"]["elements"]),
            "dofs": 3 * node_count,
            "characteristic_size": level["mesh_size"],
        },
        "quantities": {
            "end_twist": {"value": level["twist_angle"], "unit": "rad"},
            "applied_torque": {"value": level["applied_torque"], "unit": "N.m"},
        },
        "diagnostics": {
            "free_relative_residual": level["free_relative_residual"],
            "resultant_force_norm": level["resultant_force_norm"],
            "relative_stress_l2_error_non_acceptance": level["relative_stress_l2_error"],
            "source_result_sha256": sha256(level["paths"]["json"]),
            "source_result_path": f"{BENCHMARK_ID}/{level['paths']['json'].name}",
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
            "source_model": f"../source/{level_id}.model.json",
            "source_mesh": f"../source/{level_id}.msh",
            "source_setup": f"../source/{level_id}.setup.json",
            "source_manifest": f"../source/{source_manifest.name}",
        },
    }
    write_json_file(output / "results" / f"{level_id}_qf.json", payload)


def _write_normalized_reference(
    output: Path,
    level_id: str,
    level: dict[str, Any],
    scale: float,
    formula: Path,
) -> None:
    node_count = len(level["model"]["nodes"])
    payload = {
        "schema_version": 1,
        "case_id": STUDY_ID,
        "producer": {
            "name": REFERENCE_PRODUCER,
            "version": REFERENCE_VERSION,
            "run_id": f"SAINT-VENANT-{level_id}",
        },
        "units_system": "SI",
        "mesh": {
            "nodes": node_count,
            "elements": len(level["model"]["elements"]),
            "dofs": 3 * node_count,
            "characteristic_size": level["mesh_size"],
        },
        "quantities": {
            "end_twist": {"value": level["reference_twist_angle"], "unit": "rad"},
            "applied_torque": {"value": 1000.0, "unit": "N.m"},
        },
        "diagnostics": {
            "reference_type": "analytic",
            "formulation": "Saint-Venant torsion of a circular shaft",
            "stress_field": "tau_xy=-T*z/J; tau_xz=T*y/J",
        },
        "visualization": {
            "deformation_scale": scale,
            "field": "displacement_magnitude",
            "view": "isometric_xyz",
            "undeformed_overlay": True,
        },
        "artifacts": {
            "deformation_png": f"{level_id}_saint_venant_deformation.png",
            "deformation_vtu": f"{level_id}_saint_venant_deformation.vtu",
            "reference_formula": formula.name,
        },
    }
    write_json_file(output / "references" / f"{level_id}_saint_venant.json", payload)


def _study_payload(levels: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "title": "V&V TET4 - torsion d'un arbre circulaire",
        "scope": "tet4-linear-static",
        "subject": {"kind": "element", "name": "TET4", "maturity": "stable_after_reinforced_tests"},
        "units_system": "SI",
        "author": {"name": "Quentin Farinazzo", "role": "auteur du solveur"},
        "validation": {
            "validator": {"name": "Quentin Farinazzo", "role": "validateur mecanique"},
            "mode": "self_review",
            "decision": "accepted_with_reservations",
            "date": "2026-07-14",
            "comments": (
                "Rotation globale et equilibre acceptes pour l'usage engineering interne. "
                "Les contraintes locales de torsion restent exclues: erreur L2 de 29.06 % au niveau h8. "
                "Auto-revue non independante, sans revendication de certification externe."
            ),
        },
        "reference": {
            "kind": "analytic",
            "solver": REFERENCE_PRODUCER,
            "version": REFERENCE_VERSION,
            "manual_citation": "Solution de Saint-Venant pour un arbre circulaire plein en torsion uniforme.",
            "case": "Arbre L=3 m, R=0.5 m, E=80 GPa, nu=0.3, couple T=1000 N.m.",
        },
        "quantities": [
            {
                "id": "end_twist",
                "label": "Rotation moyenne de la face terminale",
                "metric": "relative_error",
                "limit": 0.4,
                "absolute_floor": 1.0e-15,
                "extraction": {
                    "location": "surface=x_max",
                    "component": "rotation_about_X",
                    "reduction": "least_squares_rigid_rotation",
                },
            },
            {
                "id": "applied_torque",
                "label": "Couple resultant applique",
                "metric": "relative_error",
                "limit": 1.0e-12,
                "absolute_floor": 1.0e-12,
                "extraction": {
                    "location": "surface=x_max",
                    "component": "moment_about_X",
                    "reduction": "sum_nodal_moments",
                },
            },
        ],
        "levels": levels,
        "convergence": [
            {
                "quantity": "end_twist",
                "require_monotonic": True,
                "minimum_order": 0.5,
                "finest_error_limit": 0.15,
            }
        ],
        "acceptance": {"deformation_requirement": "all"},
    }


def _reference_markdown(reference_twist: float, shear_modulus: float, polar_moment: float) -> str:
    return (
        "# Reference analytique de Saint-Venant\n\n"
        "Arbre circulaire plein, axe X, torsion uniforme et petites transformations.\n\n"
        "```text\n"
        "G = E / (2 * (1 + nu))\n"
        "J = pi * R^4 / 2\n"
        "phi(x) = T * x / (G * J)\n"
        "u_x = 0\n"
        "u_y = -phi(x) * z\n"
        "u_z =  phi(x) * y\n"
        "tau_xy = -T * z / J\n"
        "tau_xz =  T * y / J\n"
        "```\n\n"
        f"- Module de cisaillement : `{shear_modulus:.12e} Pa`\n"
        f"- Moment polaire : `{polar_moment:.12e} m^4`\n"
        f"- Rotation terminale : `{reference_twist:.12e} rad`\n\n"
        "La reference de deplacement est evaluee sur les memes noeuds que QF_solver. "
        "Les contraintes locales TET4 restent hors du verdict d'acceptation de cette etude.\n"
    )


def _study_markdown(levels: list[dict[str, Any]], scale: float) -> str:
    lines = [
        "# V&V TET4 - torsion circulaire de Saint-Venant",
        "",
        "**Decision interne : accepted_with_reservations.** La rotation globale, le couple et la convergence sont",
        "acceptes pour l'usage engineering interne. Les contraintes locales restent exclues du domaine valide.",
        "Cette decision est une auto-revue non independante et ne constitue pas une certification externe.",
        "",
        "## Resultats de convergence",
        "",
        "| Niveau | h [m] | Noeuds | Elements | Rotation QF [rad] | Reference [rad] | Erreur rotation | Erreur contraintes L2 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for level in levels:
        lines.append(
            f"| h{level['level']} | {level['mesh_size']:.6g} | {len(level['model']['nodes'])} | "
            f"{len(level['model']['elements'])} | {level['twist_angle']:.6e} | "
            f"{level['reference_twist_angle']:.6e} | {level['relative_twist_error']:.3%} | "
            f"{level['relative_stress_l2_error']:.3%} |"
        )
    lines.extend(
        [
            "",
            f"Facteur d'amplification commun aux images : `{scale:.6e}`.",
            "",
            "## Deformees comparables",
            "",
            "Les deux images d'un niveau utilisent le meme maillage, la meme vue et le meme facteur d'amplification.",
            "",
            "| Niveau | QF_solver | Saint-Venant |",
            "| --- | --- | --- |",
        ]
    )
    for level in levels:
        identifier = f"h{level['level']}"
        lines.append(
            f"| {identifier} | [PNG](results/{identifier}_qf_deformation.png) | "
            f"[PNG](references/{identifier}_saint_venant_deformation.png) |"
        )
    lines.extend(
        [
            "",
            "## Tracabilite",
            "",
            "- protocole machine-readable : `study.json`;",
            "- solution fermee : `references/saint_venant_reference.md`;",
            "- modeles, maillages, configurations et empreintes : `source/`;",
            "- resultats normalises QF_solver : `results/`;",
            "- resultats normalises analytiques : `references/`;",
            "- emplacement d'une future comparaison commerciale : `commercial_reference/`.",
            "",
            "Execution :",
            "",
            "```powershell",
            "qf-solver vnv-compare --study .\\study.json --output .\\evidence --require-approval",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _commercial_reference_markdown(level_count: int) -> str:
    return (
        "# Emplacement de la reference Abaqus ou Ansys\n\n"
        "Aucun resultat commercial n'est fourni dans la baseline. Ce dossier ne doit jamais contenir de valeur "
        "inventee ou recopilee manuellement depuis une capture d'ecran.\n\n"
        f"Pour chacun des {level_count} niveaux `h1` a `h{level_count}`, fournir :\n\n"
        "- le fichier d'entree controle (`.inp`, archive Ansys ou script);\n"
        "- la version exacte du solveur et du manuel de verification;\n"
        "- un JSON conforme a `qualification/vnv/schema/normalized_result.schema.json`;\n"
        "- une deformee PNG avec echelle, vue, unite et champ identiques;\n"
        "- un VTU ou export champ equivalent;\n"
        "- le journal de calcul, le statut de convergence et les empreintes SHA-256.\n\n"
        "La comparaison commerciale doit former une etude distincte, par exemple "
        "`VNV-TET4-TORSION-ABAQUS-001`, afin de ne pas remplacer silencieusement la reference analytique.\n"
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
        raise InputValidationError("torsion_h_convergence must be a non-empty array of objects.")
    return value


def _finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be numeric.") from exc
    if not np.isfinite(number):
        raise InputValidationError(f"{label} must be finite.")
    return number
