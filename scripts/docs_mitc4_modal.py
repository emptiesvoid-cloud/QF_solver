"""Publish generated MITC4 modal plate evidence into the offline site."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.docs_support import write_markdown_table
from solveur.verification.mitc4_harmonic import STUDY_ID as HARMONIC_STUDY_ID
from solveur.verification.mitc4_harmonic_broadband import STUDY_ID as HARMONIC_BROADBAND_STUDY_ID
from solveur.verification.mitc4_harmonic_condensation import STUDY_ID as HARMONIC_CONDENSATION_STUDY_ID
from solveur.verification.mitc4_harmonic_nafems import STUDY_ID as NAFEMS_13H_STUDY_ID
from solveur.verification.mitc4_modal_plate import STUDY_ID
from solveur.verification.mitc4_newmark import STUDY_ID as NEWMARK_STUDY_ID
from solveur.verification.mitc4_newmark_extended import STUDY_ID as NEWMARK_EXTENDED_STUDY_ID
from solveur.verification.mitc4_newmark_broadband import STUDY_ID as NEWMARK_BROADBAND_STUDY_ID


def publish_mitc4_modal_plate(generated: Path, assets: Path) -> None:
    """Run the plate study and expose its controlled table and figures."""
    evidence = generated / "mitc4_modal_plate_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_modal_plate", "write_mitc4_modal_plate_evidence", evidence
    )
    rows: list[tuple[object, ...]] = []
    for point in summary["points"]:
        rows.append(
            (
                f"{point['mesh'][0]}x{point['mesh'][1]}",
                point["element_count"],
                ", ".join(f"{value:.4f}" for value in point["frequencies_hz"]),
                ", ".join(f"{100.0 * value:.3f} %" for value in point["relative_frequency_errors"]),
                f"{point['first_mode_mac']:.8f}",
                f"{point['repeated_mode_subspace_mac']:.8f}",
                f"{point['fourth_mode_mac']:.8f}",
            )
        )
    write_markdown_table(
        generated / "mitc4_modal_plate_results.md",
        ("Maillage", "Elements", "Frequences (Hz)", "Ecarts", "MAC 11", "MAC 12/21", "MAC 22"),
        rows,
    )
    for suffix in ("convergence", "mode-11"):
        shutil.copy2(
            evidence / f"{STUDY_ID}-{suffix}.png",
            assets / f"mitc4_modal_plate_{suffix}.png",
        )
    _publish_newmark(generated, assets)
    _publish_newmark_extended(generated, assets)
    _publish_newmark_broadband(generated, assets)
    _publish_harmonic(generated, assets)
    _publish_harmonic_condensation(generated, assets)
    _publish_harmonic_broadband(generated, assets)
    _publish_nafems_13h(generated, assets)


def _publish_newmark(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_newmark_vnv"
    summary = _write_isolated_evidence("solveur.verification.mitc4_newmark", "write_mitc4_newmark_evidence", evidence)
    write_markdown_table(
        generated / "mitc4_newmark_results.md",
        ("Pas/periode", "Delta t (s)", "Erreur RMS", "Retour periode", "Derive energie", "Residu max"),
        [
            (
                point["steps_per_period"],
                point["time_step_s"],
                point["normalized_rms_error"],
                point["period_return_error"],
                point["maximum_relative_energy_drift"],
                point["maximum_dynamic_residual_norm"],
            )
            for point in summary["points"]
        ],
    )
    for suffix in ("convergence", "history"):
        shutil.copy2(
            evidence / f"{NEWMARK_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_newmark_{suffix}.png",
        )


def _publish_newmark_extended(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_newmark_extended_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_newmark_extended", "write_mitc4_newmark_extended_evidence", evidence
    )
    rows: list[tuple[object, ...]] = []
    for family, points in (("libre amorti", summary["damped_points"]), ("force sinusoidal", summary["forced_points"])):
        rows.extend(
            (
                family,
                point["steps_per_period"],
                point["time_step_s"],
                point["normalized_rms_error"],
                point["maximum_dynamic_residual_norm"],
            )
            for point in points
        )
    write_markdown_table(
        generated / "mitc4_newmark_extended_results.md",
        ("Cas", "Pas/periode", "Delta t (s)", "Erreur RMS", "Residu max"),
        rows,
    )
    for suffix in ("convergence", "histories"):
        shutil.copy2(
            evidence / f"{NEWMARK_EXTENDED_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_newmark_extended_{suffix}.png",
        )


def _publish_newmark_broadband(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_newmark_broadband_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_newmark_broadband", "write_mitc4_newmark_broadband_evidence", evidence
    )
    rows = []
    for case, points in summary["cases"].items():
        final = points[-1]
        rows.append(
            (
                case,
                final["steps_per_period"],
                f"{100.0 * final['displacement_rms_error']:.4f} %",
                f"{100.0 * final['stress_rms_error']:.4f} %",
                f"{100.0 * final['energy_balance_error']:.4f} %",
                f"{final['maximum_relative_residual']:.3e}",
            )
        )
    write_markdown_table(
        generated / "mitc4_newmark_broadband_results.md",
        ("Excitation", "Pas/periode", "RMS UZ", "RMS S11", "Bilan energie", "Residu"),
        rows,
    )
    for suffix in ("excitations", "displacement", "stress", "convergence"):
        shutil.copy2(
            evidence / f"{NEWMARK_BROADBAND_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_newmark_broadband_{suffix}.png",
        )
    code_aster_plot = (
        generated.parents[1]
        / "results"
        / "VNV-MITC4-NEWMARK-CODEASTER-DKQ-005"
        / "code-aster-newmark-comparison.png"
    )
    if code_aster_plot.is_file():
        shutil.copy2(code_aster_plot, assets / "mitc4_code_aster_newmark.png")


def _publish_harmonic(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_harmonic_vnv"
    summary = _write_isolated_evidence("solveur.verification.mitc4_harmonic", "write_mitc4_harmonic_evidence", evidence)
    acceptance = summary["acceptance"]
    write_markdown_table(
        generated / "mitc4_harmonic_results.md",
        ("Verification", "Valeur", "Limite", "Verdict"),
        (
            (
                "Limite statique a 0 Hz",
                f"{summary['zero_hz_static_relative_error']:.3e}",
                f"{acceptance['static_relative_error_max']:.1e}",
                "PASS",
            ),
            (
                "Reponse complexe analytique",
                f"{summary['maximum_relative_error']:.3e}",
                f"{acceptance['complex_response_relative_error_max']:.1e}",
                "PASS",
            ),
            (
                "Frequence du pic / f1",
                f"{summary['peak']['frequency_ratio']:.6f}",
                "[0.95 ; 1.05]",
                "PASS",
            ),
            (
                "Residu harmonique maximal",
                f"{summary['maximum_residual_norm']:.3e}",
                f"{acceptance['residual_norm_max']:.1e}",
                "PASS",
            ),
        ),
    )
    for suffix in ("response", "damping"):
        shutil.copy2(
            evidence / f"{HARMONIC_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_harmonic_{suffix}.png",
        )


def _publish_harmonic_condensation(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_harmonic_condensation_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_harmonic_condensation", "write_mitc4_harmonic_condensation_evidence", evidence
    )
    maxima = summary["maxima"]
    acceptance = summary["acceptance"]
    write_markdown_table(
        generated / "mitc4_harmonic_condensation_results.md",
        ("Controle", "Erreur maximale", "Limite", "Verdict"),
        (
            (
                "Complement de Schur",
                f"{maxima['schur_relative_error']:.3e}",
                f"{acceptance['schur_relative_error_max']:.1e}",
                "PASS",
            ),
            (
                "Charge condensee",
                f"{maxima['load_relative_error']:.3e}",
                f"{acceptance['load_relative_error_max']:.1e}",
                "PASS",
            ),
            (
                "Reponse condensee / complete",
                f"{maxima['response_relative_error']:.3e}",
                f"{acceptance['response_relative_error_max']:.1e}",
                "PASS",
            ),
            (
                "Equilibre complexe complet",
                f"{maxima['full_relative_residual']:.3e}",
                f"{acceptance['full_relative_residual_max']:.1e}",
                "PASS",
            ),
        ),
    )
    shutil.copy2(
        evidence / f"{HARMONIC_CONDENSATION_STUDY_ID}-errors.png",
        assets / "mitc4_harmonic_condensation_errors.png",
    )


def _publish_harmonic_broadband(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_harmonic_broadband_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_harmonic_broadband", "write_mitc4_harmonic_broadband_evidence", evidence
    )
    rows: list[tuple[object, ...]] = [
        (
            index,
            f"{peak['modal_frequency_hz']:.6f}",
            f"{peak['direct_peak_frequency_hz']:.6f}",
            f"{peak['direct_peak_amplitude_m']:.6e}",
            f"{100.0 * peak['relative_frequency_error']:.3f} %",
        )
        for index, peak in enumerate(summary["peaks"], start=1)
    ]
    metrics = summary["metrics"]
    rows.append(
        (
            "max",
            "-",
            "-",
            f"erreur champ {metrics['maximum_complex_response_relative_error']:.3e}",
            f"residu {metrics['maximum_relative_residual']:.3e}",
        )
    )
    write_markdown_table(
        generated / "mitc4_harmonic_broadband_results.md",
        ("Famille", "Frequence modale (Hz)", "Pic direct (Hz)", "Amplitude (m)", "Ecart"),
        rows,
    )
    for suffix in ("response", "agreement", "peak-shapes"):
        shutil.copy2(
            evidence / f"{HARMONIC_BROADBAND_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_harmonic_broadband_{suffix.replace('-', '_')}.png",
        )


def _publish_nafems_13h(generated: Path, assets: Path) -> None:
    evidence = generated / "mitc4_nafems13h_vnv"
    summary = _write_isolated_evidence(
        "solveur.verification.mitc4_harmonic_nafems", "write_mitc4_nafems_13h_evidence", evidence
    )
    correlation = summary["external_correlation"]
    differences = correlation["relative_differences"]
    write_markdown_table(
        generated / "mitc4_nafems13h_results.md",
        ("Resultat", "QF_solver", "Abaqus S4R", "Abaqus S4", "NAFEMS", "Ecart QF/S4R"),
        (
            (
                "Pic deplacement (mm)",
                f"{summary['peak']['peak_displacement_mm']:.6f}",
                f"{correlation['abaqus_s4r']['peak_displacement_mm']:.6f}",
                f"{correlation['abaqus_s4']['peak_displacement_mm']:.6f}",
                f"{correlation['nafems']['peak_displacement_mm']:.6f}",
                f"{100.0 * differences['abaqus_displacement']:.3f} %",
            ),
            (
                "Pic S11 face (N/mm2)",
                f"{summary['peak']['peak_stress_n_mm2']:.6f}",
                f"{correlation['abaqus_s4r']['peak_stress_n_mm2']:.6f}",
                f"{correlation['abaqus_s4']['peak_stress_n_mm2']:.6f}",
                f"{correlation['nafems']['peak_stress_n_mm2']:.6f}",
                f"{100.0 * differences['abaqus_stress']:.3f} %",
            ),
            (
                "Frequence du pic (Hz)",
                f"{summary['peak']['peak_frequency_hz']:.6f}",
                f"{correlation['abaqus_s4r']['peak_frequency_hz']:.6f}",
                f"{correlation['abaqus_s4']['peak_frequency_hz']:.6f}",
                f"{correlation['nafems']['peak_frequency_hz']:.6f}",
                f"{100.0 * differences['abaqus_frequency']:.3f} %",
            ),
            (
                "Residu relatif maximal",
                f"{summary['peak']['max_relative_residual']:.3e}",
                "-",
                "-",
                "-",
                "limite 1e-8",
            ),
        ),
    )
    for suffix in ("model-setup", "response", "stress-response", "deformed"):
        shutil.copy2(
            evidence / f"{NAFEMS_13H_STUDY_ID}-{suffix}.png",
            assets / f"mitc4_nafems13h_{suffix}.png",
        )
    calculix_plot = (
        generated.parents[1]
        / "results"
        / "VNV-MITC4-HARMONIC-CALCULIX13H-S8R-006"
        / "calculix-comparison.png"
    )
    if calculix_plot.is_file():
        shutil.copy2(calculix_plot, assets / "mitc4_calculix_nafems13h.png")
    code_aster_plot = (
        generated.parents[1]
        / "results"
        / "VNV-MITC4-HARMONIC-CODEASTER13H-DKQ-007"
        / "code-aster-comparison.png"
    )
    if code_aster_plot.is_file():
        shutil.copy2(code_aster_plot, assets / "mitc4_code_aster_nafems13h.png")


def _write_isolated_evidence(module: str, function: str, target: Path) -> dict[str, Any]:
    """Generate one memory-intensive V&V study in a fresh Python process."""
    source = (
        "from importlib import import_module; from pathlib import Path; import sys; "
        "getattr(import_module(sys.argv[1]), sys.argv[2])(Path(sys.argv[3]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", source, module, function, str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic"
        raise RuntimeError(f"MITC4 documentation study {function} failed: {message}")
    try:
        payload = json.loads((target / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"MITC4 documentation study {function} did not create a readable summary.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"MITC4 documentation study {function} returned an invalid summary.")
    return payload
