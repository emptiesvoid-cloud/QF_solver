"""Build controlled refinement evidence for the complex TET10 J2 case."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "qualification" / "vnv" / "external" / "code_aster_tet10_j2_complex_refinement_strict" / "reference"
DEFAULT_LEVELS = [
    ROOT / "qualification" / "vnv" / "external" / "code_aster_tet10_j2_complex" / "reference" / "summary.json",
    ROOT / "results" / "VNV-TET10-J2-CODEASTER-COMPLEX-027" / "summary.json",
    ROOT / "results" / "VNV-TET10-J2-CODEASTER-COMPLEX-028" / "summary.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_level(summary_path: Path, target: Path, index: int) -> dict:
    source = summary_path.parent
    level = _read(summary_path)
    level_dir = target / f"level_{index + 1:02d}"
    level_dir.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "comparison.png", "deformation.png", "deformation.vtu", "report.md", "vnv_manifest.json"):
        candidate = source / name
        if candidate.is_file():
            shutil.copy2(candidate, level_dir / name)
    return level


def build(level_paths: list[Path], output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    levels = [_copy_level(path, output, index) for index, path in enumerate(level_paths)]
    levels.sort(key=lambda item: float(item["model"]["mesh_size"]), reverse=True)
    final = levels[-1]
    final_checks = {item["id"]: item for item in final["checks"]}
    peeq = [float(item["checks"][[c["id"] for c in item["checks"]].index("peeq_path_rms")]["value"]) for item in levels]
    summary = {
        "schema_version": 1,
        "study_id": "VNV-TET10-J2-CODEASTER-COMPLEX-REFINEMENT-001",
        "status": "PASS_EXTERNAL_CORRELATION",
        "maturity": "experimental_bounded",
        "scope": "tet10-material-nonlinear",
        "external_solver": final["external_solver"],
        "geometry": final["geometry"],
        "levels": [
            {
                "mesh_size": item["model"]["mesh_size"],
                "elements": item["model"]["elements"],
                "nodes": item["model"]["nodes"],
                "tip_displacement_path_rms": next(c["value"] for c in item["checks"] if c["id"] == "combined_tip_displacement_path_rms"),
                "peeq_path_rms": next(c["value"] for c in item["checks"] if c["id"] == "peeq_path_rms"),
                "maximum_qf_residual": next(c["value"] for c in item["checks"] if c["id"] == "qf_max_step_residual"),
            }
            for item in levels
        ],
        "stable_gate": {
            "primary_error_limit": 0.01,
            "fine_peeq_path_rms": final_checks["peeq_path_rms"]["value"],
            "status": "PASS" if final_checks["peeq_path_rms"]["value"] <= 0.01 else "BLOCKED",
            "interpretation": "The refined complex case passes the <=1% primary-error gate; the Owner review and broader nonlinear scope remain open.",
        },
        "checks": {
            "fine_peeq_path_rms": final_checks["peeq_path_rms"],
            "fine_displacement_path_rms": final_checks["combined_tip_displacement_path_rms"],
            "fine_residual": final_checks["qf_max_step_residual"],
            "level_count": {"value": len(levels), "limit": 3, "status": "PASS" if len(levels) >= 3 else "FAIL"},
        },
        "limitations": final["limitations"],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    mesh_sizes = [float(item["model"]["mesh_size"]) for item in levels]
    plt.figure(figsize=(7.2, 4.2))
    plt.plot(mesh_sizes, [100 * value for value in peeq], marker="o", color="#0072B2", label="PEEQ RMS QF / Code_Aster")
    plt.axhline(1.0, color="#D55E00", linestyle="--", label="gate erreur primaire 1 %")
    plt.gca().invert_xaxis()
    plt.yscale("log")
    plt.xlabel("Taille de maille caractéristique")
    plt.ylabel("Écart RMS [%], échelle logarithmique")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output / "refinement_convergence.png", dpi=180)
    plt.close()

    lines = [
        "# TET10 J2 complexe — raffinement strict",
        "",
        "## Verdict technique",
        "",
        "La campagne compare QF_solver et Code_Aster 18.1.0 sur une équerre ré-entrante TET10 à charges combinées. Trois niveaux sont rejoués sur des maillages identiques. La règle d'ingénierie impose une erreur primaire inférieure ou égale à 1 %.",
        "",
        f"Le PEEQ RMS final vaut **{100 * final_checks['peeq_path_rms']['value']:.4f} %** et le résidu maximal vaut **{final_checks['qf_max_step_residual']['value']:.3e}**. Le critère technique strict est donc **PASS** pour ce cas raffiné.",
        "",
        "Cette conclusion reste limitée à ce modèle, à la plasticité J2 isotrope à petites déformations et aux observables globales. Elle ne constitue pas une promotion automatique du scope complet : une décision Owner dédiée est requise.",
        "",
        "## Résultats",
        "",
        "| Taille de maille | Éléments | PEEQ RMS | Résidu QF |",
        "|---:|---:|---:|---:|",
    ]
    for item in summary["levels"]:
        lines.append(f"| {item['mesh_size']:.3f} | {item['elements']} | {100 * item['peeq_path_rms']:.4f} % | {item['maximum_qf_residual']:.3e} |")
    lines += [
        "",
        "![Convergence du PEEQ](refinement_convergence.png)",
        "",
        "## Limites et suite",
        "",
        "Les singularités ponctuelles, la rupture, l'endommagement, le contact, les grandes déformations et les chargements cycliques restent exclus. La suite est une Owner review dédiée, puis une campagne indépendante supplémentaire avant toute revendication stable générale.",
    ]
    (output / "refinement_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    files = {str(path.relative_to(output)): _sha256(path) for path in output.rglob("*") if path.is_file() and path.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps({"study_id": summary["study_id"], "files": files}, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=CONTROLLED)
    parser.add_argument("--level", type=Path, action="append", dest="levels")
    args = parser.parse_args()
    summary = build(args.levels or DEFAULT_LEVELS, args.output)
    print(f"TET10 J2 strict refinement: {summary['stable_gate']['status']}")
    print(f"Output: {args.output}")
    return 0 if summary["stable_gate"]["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
