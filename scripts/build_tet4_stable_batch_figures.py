"""Generate reproducible figures for the ST-01-A TET4 evidence batch."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "qualification" / "maturity_evidence_0_2_1" / "tet4_stable_batch_01"
STATIC = BATCH / "static_benchmark" / "BM-SOL-CANTILEVER-001"
DYNAMIC = BATCH / "dynamic_benchmark" / "BM-DYN-CANTILEVER-001"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(figure: plt.Figure, name: str) -> None:
    figure.tight_layout()
    figure.savefig(BATCH / name, dpi=180, bbox_inches="tight")
    plt.close(figure)


def build() -> list[Path]:
    static = _load(STATIC / "benchmark_summary.json")
    dynamic = _load(DYNAMIC / "benchmark_summary.json")
    convergence = static["metrics"]["tet4_h_convergence"]
    elements = [row["element_count"] for row in convergence]
    errors = [100.0 * row["relative_error"] for row in convergence]
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.semilogy(elements, errors, "o-", color="#1261A0", linewidth=2, label="TET4 cantilever")
    axis.set(xlabel="Nombre d'elements", ylabel="Erreur relative tip UZ [%]", title="ST-01-A - convergence statique TET4")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    convergence_path = BATCH / "tet4_static_convergence.png"
    _save(fig, convergence_path.name)
    frequencies = dynamic["metrics"]["harmonic_frequencies_hz"]
    amplitudes = [1.0e6 * value for value in dynamic["metrics"]["harmonic_tip_amplitudes"]]
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.plot(frequencies, amplitudes, "o-", color="#B23A48", linewidth=2)
    axis.set(xlabel="Frequence [Hz]", ylabel="Amplitude pointe [micrometres]", title="ST-01-A - reponse harmonique TET4")
    axis.grid(True, alpha=0.3)
    harmonic_path = BATCH / "tet4_dynamic_harmonic.png"
    _save(fig, harmonic_path.name)
    model = _load(STATIC / "tet4_h6.model.json")
    result = _load(STATIC / "tet4_h6.json")
    nodes = np.asarray(model["nodes"], dtype=float)
    uz = np.asarray([row["dofs"]["UZ"] for row in result["displacements"]], dtype=float)
    scale = 2500.0
    fig = plt.figure(figsize=(8.0, 5.2))
    axis = fig.add_subplot(111, projection="3d")
    axis.scatter(nodes[:, 0], nodes[:, 1], nodes[:, 2], c=uz, cmap="viridis", s=7, label="initial")
    axis.scatter(nodes[:, 0], nodes[:, 1], nodes[:, 2] + scale * uz, c=uz, cmap="plasma", s=7, marker=".", label="deformed x2500")
    axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]", title="ST-01-A - maillage et deformee TET4")
    axis.legend(loc="upper left")
    mesh_path = BATCH / "tet4_static_mesh_deformed.png"
    _save(fig, mesh_path.name)
    return [convergence_path, harmonic_path, mesh_path]


if __name__ == "__main__":
    for path in build():
        print(path)
