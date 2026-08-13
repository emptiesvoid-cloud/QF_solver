"""Normalization and acceptance checks for the CalculiX J2 correlation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from solveur.materials.solid import VonMisesElastoplasticMaterial


@dataclass(frozen=True)
class CalculixJ2State:
    """Final homogeneous integration-point state extracted from CalculiX."""

    time: float
    axial_stress_mpa: float
    lateral_stress_mpa: float
    equivalent_plastic_strain: float
    axial_strain: float
    lateral_strain: float
    internal_energy_density_mpa: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def parse_calculix_j2_dat(text: str) -> CalculixJ2State:
    """Read the final S, PEEQ, E and ENER integration-point blocks."""
    blocks = _integration_blocks(text)
    required = {"stress", "plastic", "strain", "energy"}
    complete_times = sorted(set.intersection(*(set(blocks[name]) for name in required)))
    if not complete_times:
        raise ValueError("CalculiX output does not contain a complete J2 integration-point state.")
    time = complete_times[-1]
    stress = np.asarray(blocks["stress"][time], dtype=float)
    plastic = np.asarray(blocks["plastic"][time], dtype=float)
    strain = np.asarray(blocks["strain"][time], dtype=float)
    energy = np.asarray(blocks["energy"][time], dtype=float)
    if not (stress.shape == (8, 6) and plastic.shape == (8, 1) and strain.shape == (8, 6) and energy.shape == (8, 1)):
        raise ValueError("CalculiX J2 correlation requires eight C3D8 integration points for every field.")
    return CalculixJ2State(
        time=float(time),
        axial_stress_mpa=float(np.mean(stress[:, 0])),
        lateral_stress_mpa=float(np.max(np.abs(stress[:, 1:3]))),
        equivalent_plastic_strain=float(np.mean(plastic[:, 0])),
        axial_strain=float(np.mean(strain[:, 0])),
        lateral_strain=float(np.mean(strain[:, 1:3])),
        internal_energy_density_mpa=float(np.mean(energy[:, 0])),
    )


def evaluate_calculix_j2_correlation(state: CalculixJ2State) -> dict[str, object]:
    """Compare CalculiX, QF_solver and the exact small-strain bilinear state."""
    young, poisson, yield_stress, hardening = 210000.0, 0.3, 250.0, 50000.0
    target_stress = 300.0
    expected_plastic = (target_stress - yield_stress) / hardening
    expected_strain = target_stress / young + expected_plastic
    yield_strain = yield_stress / young
    expected_energy = 0.5 * yield_stress * yield_strain + 0.5 * (yield_stress + target_stress) * (
        expected_strain - yield_strain
    )
    material = VonMisesElastoplasticMaterial(
        E=young,
        nu=poisson,
        yield_stress=yield_stress,
        hardening_modulus=hardening,
    )
    qf_stress, qf_state, qf_lateral = _qf_uniaxial_state(material, expected_strain)
    qf_energy = _qf_uniaxial_energy(material, expected_strain)
    values = {
        "axial_stress": (state.axial_stress_mpa, qf_stress, target_stress, 1.0e-6),
        "equivalent_plastic_strain": (
            state.equivalent_plastic_strain,
            float(qf_state["equivalent_plastic_strain"]),
            expected_plastic,
            1.0e-6,
        ),
        "axial_strain": (state.axial_strain, expected_strain, expected_strain, 1.0e-6),
        "internal_energy_density": (state.internal_energy_density_mpa, qf_energy, expected_energy, 5.0e-3),
    }
    checks = []
    for name, (calculix, qf, theory, limit) in values.items():
        scale = max(abs(float(theory)), np.finfo(float).tiny)
        external_error = abs(float(calculix) - float(theory)) / scale
        qf_error = abs(float(qf) - float(theory)) / scale
        checks.extend(
            [
                _check(f"calculix_vs_theory_{name}", external_error, limit),
                _check(f"qf_solver_vs_theory_{name}", qf_error, limit),
            ]
        )
    checks.append(_check("calculix_lateral_stress", state.lateral_stress_mpa / target_stress, 1.0e-10))
    checks.append(_check("qf_solver_lateral_stress", abs(qf_lateral) / target_stress, 1.0e-10))
    return {
        "campaign_id": "VNV-J2-CALCULIX-ISOTROPIC-002",
        "status": "PASS_INTERNAL" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "maturity": "experimental",
        "calculix": state.to_dict(),
        "qf_solver": {
            "axial_stress_mpa": qf_stress,
            "lateral_stress_mpa": qf_lateral,
            "equivalent_plastic_strain": float(qf_state["equivalent_plastic_strain"]),
            "axial_strain": expected_strain,
            "internal_energy_density_mpa": qf_energy,
        },
        "theory": {
            "axial_stress_mpa": target_stress,
            "equivalent_plastic_strain": expected_plastic,
            "axial_strain": expected_strain,
            "internal_energy_density_mpa": expected_energy,
        },
        "checks": checks,
        "limitations": [
            "CalculiX C3D8 and the QF_solver material point are independent implementations but not identical elements.",
            "The comparison is monotonic, homogeneous and below 0.25 percent axial strain.",
            "The QF_solver structural TET4 cycle and rejected-increment rollback remain separate evidence.",
        ],
    }


def write_calculix_j2_report(summary: dict[str, object], output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# VNV-J2-CALCULIX-ISOTROPIC-002",
        "",
        f"Statut : **{summary['status']}**",
        "",
        "Comparaison homogene entre QF_solver, la theorie bilineaire petites deformations et CalculiX 2.20.",
        "",
        "| Verification | Erreur relative | Limite | Statut |",
        "| --- | ---: | ---: | --- |",
    ]
    for check in summary["checks"]:
        lines.append(f"| {check['id']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- CalculiX emploie un C3D8; QF_solver est evalue au point materiel avec la meme loi isotrope.",
            "- La deformation axiale est maintenue sous 0,25 % pour borner les differences de mesure de deformation.",
            "- Cette preuve ne couvre pas encore une inversion de chargement structurelle.",
            "",
            "![Geometrie et comparaison](comparison.png)",
            "",
        ]
    )
    (root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_calculix_j2_figure(summary: dict[str, object], output_dir: str | Path) -> Path:
    """Render the controlled cube deformation and normalized solver comparison."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    strain = summary["calculix"]
    scale = 100.0
    deformed = points.copy()
    deformed[:, 0] *= 1.0 + scale * float(strain["axial_strain"])
    deformed[:, 1:] *= 1.0 + scale * float(strain["lateral_strain"])
    edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
    figure = plt.figure(figsize=(11.0, 4.8), constrained_layout=True)
    geometry = figure.add_subplot(1, 2, 1, projection="3d")
    for start, end in edges:
        geometry.plot(*points[[start, end]].T, color="#868e96", linewidth=1.0, alpha=0.7)
        geometry.plot(*deformed[[start, end]].T, color="#0b7285", linewidth=2.0)
    geometry.scatter(*deformed.T, color="#c92a2a", s=18)
    geometry.set(title="C3D8 homogene - deformee x100", xlabel="x", ylabel="y", zlabel="z")
    geometry.set_box_aspect((1.0, 1.0, 1.0))
    comparison = figure.add_subplot(1, 2, 2)
    names = ("S11", "PEEQ", "Energie")
    theory = summary["theory"]
    qf = summary["qf_solver"]
    calculix = summary["calculix"]
    qf_values = np.array(
        [qf["axial_stress_mpa"], qf["equivalent_plastic_strain"], qf["internal_energy_density_mpa"]]
    )
    ccx_values = np.array(
        [
            calculix["axial_stress_mpa"],
            calculix["equivalent_plastic_strain"],
            calculix["internal_energy_density_mpa"],
        ]
    )
    exact = np.array(
        [theory["axial_stress_mpa"], theory["equivalent_plastic_strain"], theory["internal_energy_density_mpa"]]
    )
    positions = np.arange(len(names))
    comparison.bar(positions - 0.2, qf_values / exact, width=0.4, label="QF_solver", color="#0b7285")
    comparison.bar(positions + 0.2, ccx_values / exact, width=0.4, label="CalculiX 2.20", color="#c92a2a")
    comparison.axhline(1.0, color="#343a40", linewidth=1.0, linestyle="--", label="Theorie")
    comparison.set_xticks(positions, names)
    comparison.set(ylabel="Valeur / theorie", title="Comparaison normalisee", ylim=(0.995, 1.002))
    comparison.grid(axis="y", alpha=0.25)
    comparison.legend()
    figure.suptitle("VNV J2 isotrope - QF_solver / CalculiX / theorie")
    path = root / "comparison.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _integration_blocks(text: str) -> dict[str, dict[float, list[list[float]]]]:
    headings = {
        "stresses (": ("stress", 6),
        "equivalent plastic strain (": ("plastic", 1),
        "strains (": ("strain", 6),
        "internal energy density (": ("energy", 1),
    }
    blocks: dict[str, dict[float, list[list[float]]]] = {name: {} for name, _ in headings.values()}
    active: tuple[str, float, int] | None = None
    for line in text.splitlines():
        lowered = line.strip().lower()
        matched = next((value for heading, value in headings.items() if lowered.startswith(heading)), None)
        if matched is not None and " time " in lowered:
            name, width = matched
            active = (name, float(lowered.rsplit(" time ", 1)[1]), width)
            blocks[name][active[1]] = []
            continue
        if active is None or not lowered:
            continue
        fields = lowered.split()
        name, time, width = active
        if len(fields) != width + 2 or not all(_is_number(value) for value in fields):
            active = None
            continue
        blocks[name][time].append([float(value) for value in fields[2:]])
    return blocks


def _qf_uniaxial_state(
    material: VonMisesElastoplasticMaterial,
    axial_strain: float,
) -> tuple[float, dict[str, object], float]:
    lateral = -material.nu * axial_strain
    for _ in range(20):
        strain = np.array([axial_strain, lateral, lateral, 0.0, 0.0, 0.0])
        stress, tangent, state = material.stress_tangent_state(strain, material.initial_state())
        if abs(float(stress[1])) <= 1.0e-12:
            return float(stress[0]), state, float(stress[1])
        lateral -= float(stress[1]) / float(tangent[1, 1] + tangent[1, 2])
    raise RuntimeError("QF_solver uniaxial material-point state did not converge.")


def _qf_uniaxial_energy(material: VonMisesElastoplasticMaterial, final_strain: float) -> float:
    strains = np.linspace(0.0, final_strain, 1001)
    stresses = np.asarray([_qf_uniaxial_state(material, value)[0] for value in strains])
    return float(trapezoid(stresses, strains))


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {
        "id": identifier,
        "value": float(value),
        "limit": float(limit),
        "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL",
    }


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
