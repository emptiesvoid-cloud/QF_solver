"""Formal numerical proof of exact MITC4 harmonic drilling condensation."""

from __future__ import annotations

from solveur.paths import project_root

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.model import NodalLoad
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-HARMONIC-CONDENSATION-002"


class Mitc4HarmonicCondensationStudy:
    """Compare condensed responses and Schur complements to the full system."""

    schur_limit = 1.0e-11
    load_limit = 1.0e-11
    response_limit = 1.0e-9
    residual_limit = 1.0e-8

    def __init__(
        self,
        *,
        mesh: tuple[int, int] = (4, 1),
        frequency_ratios: tuple[float, ...] = (0.0, 0.25, 0.75, 1.25, 2.0),
        rayleigh_betas: tuple[float, ...] = (0.0, 1.0e-4, 1.0e-3, 1.0e-2),
    ) -> None:
        self.mesh = mesh
        self.frequency_ratios = frequency_ratios
        self.rayleigh_betas = rayleigh_betas

    def run(self) -> dict[str, Any]:
        model, nodes = Mitc4ModalCantileverStudy().build_model(*self.mesh)
        modal = solve_model(model, enforce_policy=False)
        natural_frequency = float(modal.frequencies_hz[0])
        alpha = 0.02 * 4.0 * math.pi * natural_frequency
        tip = _tip_node(nodes)
        model.loads = [
            NodalLoad(node=tip, dof="UZ", value=1.0),
            NodalLoad(node=tip, dof="RZ", value=0.05),
        ]
        matrices = _assembled_reduction(model)
        points: list[dict[str, float]] = []
        for beta in self.rayleigh_betas:
            frequencies = [ratio * natural_frequency for ratio in self.frequency_ratios]
            model.analysis = AnalysisSettings.from_raw(
                {
                    "type": "harmonic_response",
                    "method": "direct_frequency",
                    "frequencies_hz": frequencies,
                    "rayleigh_alpha": alpha,
                    "rayleigh_beta": beta,
                }
            )
            result = solve_model(model, enforce_policy=False)
            for ratio, frequency, response in zip(self.frequency_ratios, frequencies, result.responses):
                points.append(
                    _comparison_point(
                        matrices,
                        np.asarray(response, dtype=complex),
                        ratio,
                        frequency,
                        alpha,
                        beta,
                    )
                )
        maxima = {
            "schur_relative_error": max(point["schur_relative_error"] for point in points),
            "load_relative_error": max(point["load_relative_error"] for point in points),
            "response_relative_error": max(point["response_relative_error"] for point in points),
            "full_relative_residual": max(point["full_relative_residual"] for point in points),
        }
        checks = {
            "exact_schur_complement": maxima["schur_relative_error"] <= self.schur_limit,
            "exact_condensed_load": maxima["load_relative_error"] <= self.load_limit,
            "condensed_matches_full_solution": maxima["response_relative_error"] <= self.response_limit,
            "full_complex_equilibrium": maxima["full_relative_residual"] <= self.residual_limit,
            "stiffness_damping_exercised": max(self.rayleigh_betas) > 0.0,
            "direct_drilling_load_exercised": True,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "proof": {
                "impedance": "Z=a*K+b*M",
                "stiffness_factor": "a=1+i*omega*rayleigh_beta",
                "mass_factor": "b=-omega^2+i*omega*rayleigh_alpha",
                "condensed_impedance": "Zc=a*(Kpp-Kpd*Kdd^-1*Kdp)+b*Mpp",
                "drilling_reconstruction": "ud=Kdd^-1*(fd/a-Kdp*up)",
                "assumption": "Mpd=Mdp=Mdd=0 for every condensed drilling direction",
            },
            "model": {
                "mesh": list(self.mesh),
                "element_count": self.mesh[0] * self.mesh[1],
                "tip_node": tip,
                "condensed_drilling_dofs": matrices["reducer"].massless.size,
                "loads": ["tip UZ force", "tip RZ drilling moment"],
            },
            "parameters": {
                "natural_frequency_hz": natural_frequency,
                "rayleigh_alpha": alpha,
                "rayleigh_betas": list(self.rayleigh_betas),
                "frequency_ratios": list(self.frequency_ratios),
            },
            "acceptance": {
                "schur_relative_error_max": self.schur_limit,
                "load_relative_error_max": self.load_limit,
                "response_relative_error_max": self.response_limit,
                "full_relative_residual_max": self.residual_limit,
            },
            "maxima": maxima,
            "points": points,
            "checks": checks,
            "limitations": [
                "The proof applies to proportional Rayleigh damping C=alpha*M+beta*K.",
                "General non-proportional damping requires a frequency-dependent complex Schur complement.",
                "Only directions whose complete assembled mass row is null may be condensed.",
            ],
        }


def write_mitc4_harmonic_condensation_evidence(output: str | Path) -> dict[str, Any]:
    """Write controlled JSON, Markdown, plot and SHA-256 manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4HarmonicCondensationStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_errors(summary, target / f"{STUDY_ID}-errors.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_harmonic_condensation_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _assembled_reduction(model: object) -> dict[str, Any]:
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
    free = reducer.free
    transform = reducer.transform
    return {
        "stiffness": stiffness,
        "mass": mass,
        "loads": loads,
        "free": free,
        "reducer": reducer,
        "stiffness_local": (transform @ stiffness[free, :][:, free] @ transform.T).tocsr(),
        "mass_local": (transform @ mass[free, :][:, free] @ transform.T).tocsr(),
        "load_local": np.asarray(transform @ loads[free]).ravel(),
    }


def _comparison_point(
    matrices: dict[str, Any],
    condensed_response: np.ndarray,
    frequency_ratio: float,
    frequency_hz: float,
    alpha: float,
    beta: float,
) -> dict[str, float]:
    reducer = matrices["reducer"]
    omega = 2.0 * math.pi * frequency_hz
    stiffness_factor = 1.0 + 1j * omega * beta
    mass_factor = -(omega**2) + 1j * omega * alpha
    impedance = stiffness_factor * matrices["stiffness"] + mass_factor * matrices["mass"]
    free = matrices["free"]
    full_reference = np.zeros(reducer.full_size, dtype=complex)
    full_reference[free] = spsolve(impedance[free, :][:, free].tocsc(), matrices["loads"][free])

    local_impedance = stiffness_factor * matrices["stiffness_local"] + mass_factor * matrices["mass_local"]
    physical = reducer.physical
    massless = reducer.massless
    zpp = local_impedance[physical, :][:, physical].tocsr()
    zpd = local_impedance[physical, :][:, massless].tocsr()
    zdp = local_impedance[massless, :][:, physical].tocsr()
    zdd = local_impedance[massless, :][:, massless].tocsc()
    transfer = _matrix_solution(zdd, zdp)
    exact_schur = np.asarray(zpp.toarray() - zpd @ transfer)
    expected_schur = np.asarray(
        (stiffness_factor * reducer.stiffness + mass_factor * reducer.mass).toarray()
    )

    local_load = matrices["load_local"]
    exact_load = local_load[physical] - np.asarray(
        zpd @ spsolve(zdd, local_load[massless].astype(complex))
    ).ravel()
    reduced_load = reducer.reduce_load(matrices["loads"]).astype(complex)
    residual = impedance @ condensed_response - matrices["loads"]
    return {
        "rayleigh_beta": beta,
        "frequency_ratio": frequency_ratio,
        "frequency_hz": frequency_hz,
        "stiffness_factor_abs": float(abs(stiffness_factor)),
        "schur_relative_error": _relative_norm(exact_schur - expected_schur, exact_schur),
        "load_relative_error": _relative_norm(exact_load - reduced_load, exact_load),
        "response_relative_error": _relative_norm(
            condensed_response[free] - full_reference[free], full_reference[free]
        ),
        "full_relative_residual": _relative_norm(residual[free], matrices["loads"][free]),
    }


def _matrix_solution(matrix: csr_matrix, rhs: csr_matrix) -> np.ndarray:
    solution = spsolve(matrix, rhs.tocsc())
    return np.asarray(solution.toarray() if hasattr(solution, "toarray") else solution)


def _relative_norm(error: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(error) / max(float(np.linalg.norm(reference)), 1.0e-30))


def _tip_node(nodes: np.ndarray) -> int:
    x_max = float(np.max(nodes[:, 0]))
    candidates = np.flatnonzero(np.isclose(nodes[:, 0], x_max))
    y_mid = 0.5 * (float(np.min(nodes[:, 1])) + float(np.max(nodes[:, 1])))
    return int(candidates[np.argmin(np.abs(nodes[candidates, 1] - y_mid))])


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    maxima = summary["maxima"]
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Verifier la condensation harmonique exacte des rotations de drilling MITC4
sans masse, y compris avec amortissement de Rayleigh proportionnel a la
rigidite et moment harmonique applique directement sur `RZ`.

## Demonstration

Avec `Z=a*K+b*M`, les blocs de masse du drilling sont nuls. Le complement de
Schur devient exactement `Zc=a*(Kpp-Kpd*Kdd^-1*Kdp)+b*Mpp`, et la rotation
eliminee est `ud=Kdd^-1*(fd/a-Kdp*up)`.

| Controle | Erreur maximale | Limite |
| --- | ---: | ---: |
| Complement de Schur | {maxima['schur_relative_error']:.3e} | {summary['acceptance']['schur_relative_error_max']:.1e} |
| Charge condensee | {maxima['load_relative_error']:.3e} | {summary['acceptance']['load_relative_error_max']:.1e} |
| Reponse condensee / systeme complet | {maxima['response_relative_error']:.3e} | {summary['acceptance']['response_relative_error_max']:.1e} |
| Equilibre complexe complet | {maxima['full_relative_residual']:.3e} | {summary['acceptance']['full_relative_residual_max']:.1e} |

Statut : **{summary['status']}**.

![Erreurs de condensation]({STUDY_ID}-errors.png)
""",
        encoding="utf-8",
    )


def _plot_errors(summary: dict[str, Any], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 4.6))
    for beta in summary["parameters"]["rayleigh_betas"]:
        rows = [point for point in summary["points"] if point["rayleigh_beta"] == beta]
        axis.semilogy(
            [point["frequency_ratio"] for point in rows],
            [max(point["response_relative_error"], 1.0e-18) for point in rows],
            "o-",
            label=f"beta={beta:g} s",
        )
    axis.set_xlabel("frequence / f1")
    axis.set_ylabel("erreur relative reponse condensee / complete")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
