"""Run a focused 10k-element MITC4 modal correlation for the +/-45 layup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.analysis import AnalysisSettings
from solveur.core.errors import SolverError
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc4_laminate_dynamic import _code_aster_mesh
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc4_laminate_dynamic import Mitc4LaminateDynamicStudy
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023"
LAYUP = (45.0, -45.0, -45.0, 45.0)


def _modal_comm(layup: tuple[float, ...]) -> str:
    layers = ",\n        ".join(
        f"_F(EPAIS=0.0025, MATER=lamina, ORIENTATION={angle:.1f})" for angle in layup
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DST"))
lamina = DEFI_MATERIAU(ELAS_ORTH=_F(E_L=135.0e9, E_T=10.0e9, E_N=10.0e9, NU_LT=0.3, NU_LN=0.3, NU_TN=0.3, G_LT=5.0e9, G_LN=4.5e9, G_TN=3.8e9, RHO=1600.0))
laminate = DEFI_COMPOSITE(COUCHE=(
        {layers}
))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=laminate))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.01, COQUE_NCOU=4))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=boundary)
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=boundary)
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=4))
with open("/work/code_aster_modal_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]]}}, stream, indent=2)
FIN()
'''


def run_modal(output_dir: Path, nx: int, ny: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    study = Mitc4LaminateDynamicStudy(mesh=(nx, ny), layup=LAYUP)
    model, _ = study.build_model()
    (output_dir / "mitc4_laminate_modal_10k.mail").write_text(_code_aster_mesh(model), encoding="ascii")
    (output_dir / "mitc4_laminate_modal_10k.comm").write_text(_modal_comm(LAYUP), encoding="utf-8")
    qf_error: str | None = None
    modal = None
    qf = np.empty(0, dtype=float)
    model.analysis = AnalysisSettings.from_raw(
        {
            "type": "modal",
            "method": "lobpcg",
            "modes": 4,
            "dense_modal_max_dofs": 6000,
            "modal_residual_failure_tolerance": 1.0e-7,
            "arpack_which": "SM",
            "arpack_tolerance": 1.0e-9,
            "arpack_maxiter": 30000,
            "arpack_ncv": 30,
            "lazy_drilling_condensation": True,
            "lobpcg_preconditioner": "ssor",
        }
    )
    try:
        modal = solve_model(model, enforce_policy=False)
        qf = np.asarray(modal.frequencies_hz[:4], dtype=float)
    except (SolverError, MemoryError, RuntimeError) as exc:
        qf_error = f"{type(exc).__name__}: {exc}"
    aster_error: str | None = None
    try:
        run_code_aster(output_dir, "mitc4_laminate_modal_10k", timeout=3600)
    except (SolverError, RuntimeError) as exc:
        aster_error = f"{type(exc).__name__}: {exc}"
    raw_path = output_dir / "code_aster_modal_raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else {"frequencies_hz": []}
    aster = np.asarray(raw["frequencies_hz"][:4], dtype=float)
    errors = np.abs(qf - aster) / np.maximum(np.abs(aster), 1.0e-30) if qf.size and aster.size else np.empty(0)
    qf_converged = modal is not None and qf.size == 4 and np.all(np.isfinite(qf))
    comparison_available = qf_converged and aster.size == qf.size and np.all(np.isfinite(errors))
    solver_residual = float(modal.solver["max_relative_residual"]) if modal is not None else None
    summary: dict[str, Any] = {
        "study_id": STUDY_ID,
        "status": (
            "PASS_EXTERNAL_CORRELATION"
            if comparison_available and np.max(errors) <= 0.10
            else "QF_NUMERICAL_FAILURE_REFERENCE_AVAILABLE"
            if not qf_converged and aster.size
            else "EXTERNAL_REFERENCE_FAILURE"
            if not aster.size
            else "FAIL"
        ),
        "maturity": "verified_development_external_correlation",
        "scope": "MITC4 planar symmetric laminate modal correlation, focused +/-45 layup",
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": CODE_ASTER_IMAGE,
            "element": "DST / QUAD4 / DEFI_COMPOSITE",
        },
        "model": {"mesh": [nx, ny], "quad4_elements": nx * ny, "layup_deg": list(LAYUP)},
        "modal": {
            "qf_frequencies_hz": qf.tolist(),
            "code_aster_frequencies_hz": aster.tolist(),
            "relative_differences": errors.tolist(),
            "maximum_relative_difference": float(np.max(errors)) if errors.size else None,
        },
        "diagnostics": {"qf_error": qf_error, "code_aster_error": aster_error},
        "checks": [
            {
                "id": "modal_frequencies",
                "value": float(np.max(errors)) if errors.size else None,
                "limit": 0.10,
                "status": "PASS" if comparison_available and np.max(errors) <= 0.10 else "NOT_ASSESSED",
            },
            {
                "id": "qf_modal_residual",
                "value": solver_residual,
                "limit": 1.0e-7,
                "status": "PASS" if solver_residual is not None and solver_residual <= 1.0e-7 else "FAIL",
            },
        ],
        "limitations": [
            "This campaign targets modal frequencies only; Newmark and harmonic response are not rerun here.",
            "The comparison is planar and symmetric with B coupling absent.",
            "The 10k QF_solver run remains open when the iterative modal residual does not reach 1e-7.",
            "A Code_Aster reference without a converged QF_solver result is not an external correlation verdict.",
        ],
    }
    write_json_file(output_dir / "summary.json", summary)
    (output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
    _plot(summary, output_dir / "mitc4_laminate_modal_10k_comparison.png")
    write_vnv_manifest(output_dir, STUDY_ID)
    return summary


def run_code_aster_reference(output_dir: Path, nx: int, ny: int) -> dict[str, Any]:
    """Generate and execute the same-mesh Code_Aster modal reference only."""
    output_dir.mkdir(parents=True, exist_ok=True)
    study = Mitc4LaminateDynamicStudy(mesh=(nx, ny), layup=LAYUP)
    model, _ = study.build_model()
    stem = "mitc4_laminate_modal_10k"
    (output_dir / f"{stem}.mail").write_text(_code_aster_mesh(model), encoding="ascii")
    (output_dir / f"{stem}.comm").write_text(_modal_comm(LAYUP), encoding="utf-8")
    aster_error: str | None = None
    try:
        run_code_aster(output_dir, stem, timeout=3600)
    except (SolverError, RuntimeError) as exc:
        aster_error = f"{type(exc).__name__}: {exc}"
    raw_path = output_dir / "code_aster_modal_raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else {"frequencies_hz": _parse_code_aster_frequencies(output_dir / "code_aster_stdout.log")}
    frequencies = list(raw.get("frequencies_hz", []))
    reference = {
        "study_id": STUDY_ID,
        "status": "PASS_EXTERNAL_REFERENCE_ONLY" if frequencies else "EXTERNAL_REFERENCE_FAILURE",
        "model": {"mesh": [nx, ny], "quad4_elements": nx * ny, "layup_deg": list(LAYUP)},
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": CODE_ASTER_IMAGE,
            "element": "DST / QUAD4 / DEFI_COMPOSITE",
        },
        "code_aster_frequencies_hz": frequencies,
        "diagnostics": {"code_aster_error": aster_error},
        "limitations": [
            "This is an external reference-only run; no QF_solver eigenpair converged at this mesh size.",
            "No external correlation verdict can be issued without a converged QF_solver result.",
        ],
    }
    write_json_file(output_dir / "code_aster_reference_summary.json", reference)
    return reference


def _parse_code_aster_frequencies(path: Path) -> list[float]:
    """Recover frequencies printed before a posteriori Code_Aster warnings."""
    import re

    if not path.is_file():
        return []
    values: list[float] = []
    in_table = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "frÃ©quence" in line or "fréquence" in line or "frequence" in line.lower():
            in_table = True
            continue
        if not in_table:
            continue
        match = re.match(r"\s*\d+\s+([-+]?\d+(?:\.\d+)?E[-+]?\d+)", line, re.IGNORECASE)
        if match:
            values.append(float(match.group(1)))
        if len(values) == 4:
            break
    return values


def _plot(summary: dict[str, Any], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    qf_values = summary["modal"]["qf_frequencies_hz"]
    aster_values = summary["modal"]["code_aster_frequencies_hz"]
    if qf_values:
        axis.plot(
            np.arange(1, len(qf_values) + 1),
            qf_values,
            "o-",
            color="#0072B2",
            label="QF_solver MITC4",
        )
    if aster_values:
        axis.plot(
            np.arange(1, len(aster_values) + 1),
            aster_values,
            "s--",
            color="#D55E00",
            label="Code_Aster DST reference",
        )
    axis.set_xticks(np.arange(1, max(len(qf_values), len(aster_values)) + 1))
    axis.set(xlabel="Mode", ylabel="Frequence [Hz]", title="MITC4 [45/-45/-45/45] - 10 000 QUAD4")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _report(summary: dict[str, Any]) -> str:
    modal = summary["modal"]
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "Cas ciblé : empilement `[45/-45/-45/45]`, maillage équilibré `200 x 50`, soit `10 000` QUAD4.",
        "",
        "| Mode | QF_solver [Hz] | Code_Aster [Hz] | Ecart relatif |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for index, (qf, aster, error) in enumerate(
        zip(modal["qf_frequencies_hz"], modal["code_aster_frequencies_hz"], modal["relative_differences"]),
        start=1,
    ):
        lines.append(f"| {index} | {qf:.8e} | {aster:.8e} | {100.0 * error:.5f} % |")
    if not modal["qf_frequencies_hz"]:
        lines.append("| - | non disponible | disponible ci-dessous | non calculable |")
    lines.extend(
        [
            "",
            f"Ecart maximal : `{100.0 * modal['maximum_relative_difference']:.5f} %`."
            if modal["maximum_relative_difference"] is not None
            else "Ecart maximal : non calculable, car aucun mode QF_solver n'a converge.",
            "Le seuil de corrélation modale retenu est `10 %`. Cette étude ne relance pas Newmark ni l'harmonique.",
            "",
            "![Comparaison des fréquences propres](mitc4_laminate_modal_10k_comparison.png)",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nx", type=int, default=200)
    parser.add_argument("--ny", type=int, default=50)
    parser.add_argument("--reference-only", action="store_true")
    args = parser.parse_args()
    if args.reference_only:
        summary = run_code_aster_reference(args.output.resolve(), args.nx, args.ny)
    else:
        summary = run_modal(args.output.resolve(), args.nx, args.ny)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] in {"PASS_EXTERNAL_CORRELATION", "PASS_EXTERNAL_REFERENCE_ONLY"} else 4


if __name__ == "__main__":
    raise SystemExit(main())
