"""Generate documented examples for beam, discrete and rigid-link entities."""
from __future__ import annotations

from pathlib import Path

from scripts.docs_support import plot_link_model, write_markdown_table
from solveur.api import load_model, solve_model


def publish_assembly_element_examples(
    root: Path,
    generated: Path,
    assets: Path,
) -> None:
    """Solve the public examples and publish their table and deformed views."""
    rows = []
    cases = (
        ("BEAM2", "beam2_cantilever.json", "beam2_deformation.png"),
        ("Ressort-masse", "spring_mass_oscillator.json", "spring_mass_mode.png"),
        ("RBE2", "rbe2_rigid_arm.json", "rbe2_deformation.png"),
    )
    for label, filename, figure in cases:
        model = load_model(root / "examples" / filename)
        result = solve_model(model, enforce_policy=False)
        vector = result.modes[:, 0] if hasattr(result, "modes") else None
        scale = plot_link_model(
            model,
            result,
            assets / figure,
            title=f"{label} - geometrie initiale et reponse",
            vector=vector,
        )
        data = result.to_dict()
        observable = (
            float(result.frequencies_hz[0])
            if hasattr(result, "frequencies_hz")
            else float(data["max_displacement"])
        )
        rows.append((label, data["analysis"], observable, scale, data["status"]))
    write_markdown_table(
        generated / "assembly_element_results.md",
        ("Famille", "Analyse", "Observable SI", "Amplification", "Statut numerique"),
        rows,
    )
