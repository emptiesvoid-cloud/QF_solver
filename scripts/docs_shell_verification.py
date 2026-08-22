"""Shell-specific evidence generation used by the technical site builder."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from solveur.compat.mitc4.benchmarks import ShearLockingStudy
from solveur.compat.mitc4.verification import MechanicalVerifier
from scripts.docs_support import plot_line_series, write_markdown_table
from solveur.verification.mitc3_dynamic_extended import write_mitc3_dynamic_extended_evidence
from solveur.verification.mitc3_laminate_dynamic import write_mitc3_laminate_dynamic_evidence
from solveur.verification.mitc4_laminate_dynamic import write_mitc4_laminate_dynamic_evidence


def publish_shell_verification(generated: Path, assets: Path) -> None:
    """Regenerate MITC4/MITC3 mechanical and dynamic documentation evidence."""
    verifier = MechanicalVerifier()
    results = verifier.run(include_benchmark=True, png=assets / "scordelis_lo.png")
    write_markdown_table(
        generated / "scordelis_results.md",
        ("Controle", "Valeur", "Limite", "Verdict", "Detail"),
        [(item.name, item.value, item.limit, item.passed, item.details) for item in results if "Scordelis" in item.name],
    )
    study = ShearLockingStudy(nx=8, ny=2).run().values
    thicknesses = (1.0e-2, 1.0e-3, 1.0e-4)
    mitc = [study[f"mitc_ratio_t_{value:.0e}"] for value in thicknesses]
    full = [study[f"full_ratio_t_{value:.0e}"] for value in thicknesses]
    plot_line_series(
        assets / "mitc4_shear_locking.png",
        [
            {"x": thicknesses, "y": np.abs(mitc), "label": "MITC4"},
            {"x": thicknesses, "y": np.abs(full), "label": "Q4 cisaillement complet"},
        ],
        title="Sensibilite au verrouillage de cisaillement",
        xlabel="Epaisseur t [m]",
        ylabel="|deplacement / reference plaque|",
        yscale="log",
    )
    write_markdown_table(
        generated / "mitc4_locking_results.md",
        ("Epaisseur", "Ratio MITC4", "Ratio Q4 complet", "Contraste"),
        [(thickness, left, right, left / max(abs(right), 1.0e-30)) for thickness, left, right in zip(thicknesses, mitc, full)],
    )
    _copy_dynamic_evidence(
        write_mitc4_laminate_dynamic_evidence(generated / "mitc4_laminate_dynamic"),
        generated / "mitc4_laminate_dynamic",
        assets,
        ("VNV-MITC4-LAMINATE-DYNAMIC-001-newmark.png", "VNV-MITC4-LAMINATE-DYNAMIC-001-harmonic.png"),
        "MITC4 laminate dynamic",
    )
    _copy_dynamic_evidence(
        write_mitc3_laminate_dynamic_evidence(generated / "mitc3_laminate_dynamic"),
        generated / "mitc3_laminate_dynamic",
        assets,
        ("VNV-MITC3-LAMINATE-DYNAMIC-001-newmark.png", "VNV-MITC3-LAMINATE-DYNAMIC-001-harmonic.png"),
        "MITC3 laminate dynamic",
    )
    _copy_dynamic_evidence(
        write_mitc3_dynamic_extended_evidence(generated / "mitc3_dynamic_extended"),
        generated / "mitc3_dynamic_extended",
        assets,
        ("VNV-MITC3-MODAL-FREEFREE-013.png", "VNV-MITC3-MODAL-CURVED-014.png", "VNV-MITC3-NEWMARK-HARMONIC-CURVED-016.png"),
        "MITC3 extended dynamic",
    )


def _copy_dynamic_evidence(summary: dict[str, object], source: Path, assets: Path, names: tuple[str, ...], label: str) -> None:
    if summary["status"] != "PASS_INTERNAL":
        raise RuntimeError(f"{label} documentation evidence did not pass.")
    for name in names:
        shutil.copy2(source / name, assets / name)
