"""Publish the public TET4 torsion evidence used by the technical site."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from scripts.docs_support import write_markdown_table
from solveur.io.manifest import sha256


def publish_torsion_stress_probe(root: str | Path, generated: str | Path, assets: str | Path) -> None:
    """Publish controlled h9 evidence or the reproducible public h1-h8 fallback.

    The very fine h9 probe is intentionally kept outside the public checkout because
    it contains a large mesh. A public documentation build must still be complete,
    so it publishes the tracked h-convergence campaign when the probe is absent.
    """
    project_root = Path(root).resolve()
    generated_root = Path(generated)
    assets_root = Path(assets) / "benchmarks"
    source = project_root / "VNV-TET4-TORSION-ANALYTIC-001" / "stress_probe_h9"
    summary_path = source / "stress_probe_summary.json"
    manifest_path = source / "stress_probe_manifest.json"
    if summary_path.is_file() and manifest_path.is_file():
        _publish_controlled_probe(source, generated_root, assets_root, summary_path, manifest_path)
        return
    _publish_public_fallback(generated_root, assets_root)


def _publish_controlled_probe(
    source: Path,
    generated: Path,
    assets: Path,
    summary_path: Path,
    manifest_path: Path,
) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("files", []):
        path = source / str(entry["path"])
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise RuntimeError(f"Torsion h9 stress-probe artifact failed SHA-256 verification: {path}.")
    if summary.get("status") != "PASS" or any(check["status"] != "PASS" for check in summary["checks"]):
        raise RuntimeError("Controlled TET4 torsion h9 stress probe did not pass.")
    names = (
        "h9_qf_deformation.png",
        "h9_qf_von_mises.png",
        "h9_saint_venant_deformation.png",
        "h9_saint_venant_von_mises.png",
        "h9_stress_error.png",
    )
    for name in names:
        shutil.copy2(source / name, assets / f"torsion_{name}")
    aliases = {
        "h9_qf_deformation.png": "bm-sol-tet4-torsion-001_deformation.png",
        "h9_qf_von_mises.png": "bm-sol-tet4-torsion-001_von_mises.png",
        "h9_stress_error.png": "bm-sol-tet4-torsion-001_response.png",
    }
    for source_name, target_name in aliases.items():
        shutil.copy2(source / source_name, assets / target_name)
    metrics = summary["metrics"]
    write_markdown_table(
        generated / "benchmarks" / "torsion_h9_stress_probe.md",
        ("Grandeur h9", "Valeur", "Critere", "Verdict"),
        [
            ("TET4", metrics["element_count"], "3.8 <= N/N_h8 <= 4.2", True),
            ("Multiplicateur N/N_h8", metrics["element_multiplier_vs_h8"], "[3.8, 4.2]", True),
            ("Erreur rotation", metrics["relative_twist_error"], "<= 5 %", metrics["relative_twist_error"] <= 0.05),
            (
                "Erreur contrainte L2",
                metrics["relative_stress_l2_error"],
                "<= 20 %",
                metrics["relative_stress_l2_error"] <= 0.20,
            ),
            ("Residu libre relatif", metrics["free_relative_residual"], "<= 1e-8", metrics["free_relative_residual"] <= 1.0e-8),
        ],
    )


def _publish_public_fallback(generated: Path, assets: Path) -> None:
    """Publish tracked h1-h8 evidence without claiming the private h9 probe."""
    benchmark = generated / "benchmarks" / "BM-SOL-TET4-TORSION-001"
    summary_path = benchmark / "benchmark_summary.json"
    if not summary_path.is_file():
        raise RuntimeError("Public TET4 torsion benchmark summary is missing.")
    summary: dict[str, Any] = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS":
        raise RuntimeError("Public TET4 torsion benchmark did not pass.")
    metrics = summary["metrics"]
    rows = metrics["torsion_h_convergence"]
    finest = rows[-1]
    public_assets = {
        "deformation": assets / "bm-sol-tet4-torsion-001_deformation.png",
        "von_mises": assets / "bm-sol-tet4-torsion-001_von_mises.png",
        "response": assets / "bm-sol-tet4-torsion-001_response.png",
    }
    missing = [str(path) for path in public_assets.values() if not path.is_file()]
    if missing:
        raise RuntimeError("Public TET4 torsion benchmark images are missing: " + ", ".join(missing))
    output = generated / "benchmarks" / "torsion_h9_stress_probe.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_table(
        output,
        ("Grandeur", "Valeur h8", "Interpretation", "Statut"),
        [
            ("TET4", finest["element_count"], "dernier niveau public", "PASS"),
            ("Erreur rotation", finest["relative_twist_error"], "critere <= 15 %", "PASS"),
            ("Erreur contrainte L2", finest["relative_stress_l2_error"], "informative, hors acceptance", "WARNING"),
            ("Residu libre relatif", finest["free_relative_residual"], "critere <= 1e-8", "PASS"),
        ],
    )
    table = output.read_text(encoding="utf-8")
    output.write_text(
        "## Sonde h9 non incluse dans le checkout public\n\n"
        "La sonde h9 a quatre fois plus d'elements est une evidence V&V locale "
        "optionnelle. Elle n'est pas presente dans ce clone public; aucun resultat "
        "h9 ni aucune comparaison de contrainte Saint-Venant n'est revendique ici. "
        "Le tableau ci-dessous reprend uniquement le dernier niveau suivi de la "
        "campagne publique h1-h8.\n\n" + table,
        encoding="utf-8",
    )
