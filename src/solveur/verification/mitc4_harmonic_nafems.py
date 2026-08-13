"""Abaqus/NAFEMS Test 13H external correlation for MITC4 harmonic response."""

from __future__ import annotations

from solveur.paths import project_root

import cmath
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from mitc4.mesh import MeshFactory
from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor
from solveur.verification.external_correlation import (
    compare_nafems_13h,
    load_abaqus_nafems_13h_reference,
)


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-HARMONIC-NAFEMS13H-004"


class Mitc4Nafems13HStudy:
    """Reproduce the published NAFEMS 13H direct frequency sweep."""

    def run(self) -> dict[str, Any]:
        reference = load_abaqus_nafems_13h_reference()
        model, quads = build_nafems_13h_model(reference)
        result = solve_model(model, enforce_policy=False)
        center = _center_node(model.nodes)
        center_dof = result.dofs.index(center, "UZ")
        values = np.asarray([response[center_dof] for response in result.responses], dtype=complex)
        amplitudes_mm = 1000.0 * np.abs(values)
        phases = np.degrees(np.angle(values))
        stress_processor = HarmonicShellStressPostProcessor()
        center_stresses = np.asarray(
            [
                stress_processor.averaged_nodal_stress(
                    model,
                    result.dofs,
                    response,
                    center,
                    face="top",
                )
                for response in result.responses
            ],
            dtype=complex,
        )
        s11_amplitudes = np.abs(center_stresses[:, 0]) / 1.0e6
        navier_displacement, navier_stress = _navier_plate_response(
            np.asarray(result.frequencies_hz, dtype=float),
            reference,
        )
        theory = _navier_peak_reference(reference)
        peak_index = int(np.argmax(amplitudes_mm))
        stress_peak_index = int(np.argmax(s11_amplitudes))
        qf_peak = {
            "peak_displacement_mm": float(amplitudes_mm[peak_index]),
            "peak_frequency_hz": float(result.frequencies_hz[peak_index]),
            "peak_stress_n_mm2": float(s11_amplitudes[stress_peak_index]),
            "max_relative_residual": float(result.solver["max_relative_residual_norm"]),
        }
        theory["qf_relative_differences"] = {
            "displacement": abs(qf_peak["peak_displacement_mm"] - theory["peak_displacement_mm"])
            / theory["peak_displacement_mm"],
            "frequency": abs(qf_peak["peak_frequency_hz"] - theory["fundamental_frequency_hz"])
            / theory["fundamental_frequency_hz"],
            "stress": abs(qf_peak["peak_stress_n_mm2"] - theory["peak_stress_n_mm2"])
            / theory["peak_stress_n_mm2"],
        }
        correlation = compare_nafems_13h(qf_peak, reference)
        checks = {
            "external_correlation": correlation["status"] == "PASS",
            "all_external_metrics": all(correlation["checks"].values()),
            "same_frequency_grid": np.allclose(
                result.frequencies_hz,
                np.linspace(
                    reference["model"]["frequency_sweep_hz"]["start"],
                    reference["model"]["frequency_sweep_hz"]["stop"],
                    reference["model"]["frequency_sweep_hz"]["count"],
                ),
                rtol=0.0,
                atol=1.0e-14,
            ),
            "finite_frequency_response": bool(np.all(np.isfinite(values))),
            "finite_harmonic_stress": bool(np.all(np.isfinite(center_stresses))),
            "navier_stress_agreement": abs(qf_peak["peak_stress_n_mm2"] - theory["peak_stress_n_mm2"])
            / theory["peak_stress_n_mm2"]
            <= 0.05,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "reference_id": reference["reference_id"],
            "source": reference["source"],
            "model": {
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "mesh": [8, 8],
                "center_node": center,
                "boundary_conditions": reference["model"]["boundary_conditions"],
                "pressure_pa": reference["model"]["pressure_pa"],
                "rayleigh_damping": reference["model"]["rayleigh_damping"],
                "partial_rotation_contract": "aligned_with_global_shell_director_frame",
            },
            "frequency_response": [
                {
                    "frequency_hz": float(frequency),
                    "center_uz_real_mm": float(1000.0 * value.real),
                    "center_uz_imag_mm": float(1000.0 * value.imag),
                    "center_uz_amplitude_mm": float(amplitude),
                    "center_uz_phase_degrees": float(phase),
                    "center_top_s11_real_n_mm2": float(stress.real / 1.0e6),
                    "center_top_s11_imag_n_mm2": float(stress.imag / 1.0e6),
                    "center_top_s11_amplitude_n_mm2": float(stress_amplitude),
                    "center_top_s11_phase_degrees": float(np.degrees(np.angle(stress))),
                    "navier_center_uz_amplitude_mm": float(1000.0 * abs(theory_displacement)),
                    "navier_top_s11_amplitude_n_mm2": float(abs(theory_stress) / 1.0e6),
                }
                for frequency, value, amplitude, phase, stress, stress_amplitude, theory_displacement, theory_stress in zip(
                    result.frequencies_hz,
                    values,
                    amplitudes_mm,
                    phases,
                    center_stresses[:, 0],
                    s11_amplitudes,
                    navier_displacement,
                    navier_stress,
                    strict=True,
                )
            ],
            "peak": {
                **qf_peak,
                "phase_degrees": float(phases[peak_index]),
                "frequency_index": peak_index,
                "peak_stress_n_mm2": float(s11_amplitudes[stress_peak_index]),
                "peak_stress_frequency_hz": float(result.frequencies_hz[stress_peak_index]),
                "peak_stress_phase_degrees": float(
                    np.degrees(np.angle(center_stresses[stress_peak_index, 0]))
                ),
            },
            "classical_plate_theory": theory,
            "external_correlation": correlation,
            "checks": checks,
            "limitations": correlation["limitations"],
            "_plot_data": {
                "nodes": model.nodes,
                "quads": quads,
                "peak_response": result.responses[peak_index],
                "dofs": result.dofs,
            },
        }


def build_nafems_13h_model(
    reference: dict[str, Any] | None = None,
    *,
    analysis: dict[str, Any] | None = None,
    pressure: bool = True,
) -> tuple[FiniteElementModel, np.ndarray]:
    """Build the exact 8x8 geometry and constraints from Abaqus input nfh13f4x."""
    data = reference or load_abaqus_nafems_13h_reference()
    mesh = MeshFactory.rectangular_plate(8, 8, 10.0, 10.0)
    nodes = mesh.nodes.copy()
    nodes[:, 1] += 5.0
    x = nodes[:, 0]
    y = nodes[:, 1]
    left = np.flatnonzero(np.isclose(x, 0.0))
    right = np.flatnonzero(np.isclose(x, 10.0))
    bottom = np.flatnonzero(np.isclose(y, 0.0))
    top = np.flatnonzero(np.isclose(y, 10.0))
    edge = np.unique(np.concatenate((left, right, bottom, top)))
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "RZ"]} for node in range(nodes.shape[0])]
    fixed.extend({"node": int(node), "dofs": ["UZ"]} for node in edge)
    fixed.extend({"node": int(node), "dofs": ["RY"]} for node in np.concatenate((bottom, top)))
    fixed.extend({"node": int(node), "dofs": ["RX"]} for node in np.concatenate((left, right)))
    sweep = data["model"]["frequency_sweep_hz"]
    damping = data["model"]["rayleigh_damping"]
    settings = analysis or {
        "type": "harmonic_response",
        "method": "direct_frequency",
        "frequencies_hz": np.linspace(sweep["start"], sweep["stop"], sweep["count"]).tolist(),
        "rayleigh_alpha": damping["alpha_s_inv"],
        "rayleigh_beta": damping["beta_s"],
    }
    distributed = (
        [
            {"type": "pressure", "element": index, "value": data["model"]["pressure_pa"]}
            for index in range(mesh.quads.shape[0])
        ]
        if pressure
        else []
    )
    material = data["model"]["material"]
    model = FiniteElementModel.from_raw(
        analysis=settings,
        nodes=nodes.tolist(),
        elements=[
            {"type": "MITC4", "nodes": quad.tolist(), "material": "plate"}
            for quad in mesh.quads
        ],
        materials={
            "plate": {
                "type": "shell_isotropic",
                "E": material["young_modulus_pa"],
                "nu": material["poisson_ratio"],
                "t": data["model"]["geometry_m"]["thickness"],
                "density": material["density_kg_m3"],
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=fixed,
        distributed_loads=distributed,
    )
    return model, mesh.quads


def write_mitc4_nafems_13h_evidence(output: str | Path) -> dict[str, Any]:
    """Write external-correlation JSON, Markdown, figures and manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4Nafems13HStudy().run()
    plot_data = summary.pop("_plot_data")
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_model_setup(plot_data, summary, target / f"{STUDY_ID}-model-setup.png")
    _plot_response(summary, target / f"{STUDY_ID}-response.png")
    _plot_stress_response(summary, target / f"{STUDY_ID}-stress-response.png")
    _plot_deformed(plot_data, summary, target / f"{STUDY_ID}-deformed.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "external_reference": summary["source"],
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_nafems_13h_external_correlation",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _center_node(nodes: np.ndarray) -> int:
    return int(np.argmin((nodes[:, 0] - 5.0) ** 2 + (nodes[:, 1] - 5.0) ** 2))


def _navier_peak_reference(reference: dict[str, Any]) -> dict[str, Any]:
    geometry = reference["model"]["geometry_m"]
    material = reference["model"]["material"]
    young = float(material["young_modulus_pa"])
    poisson = float(material["poisson_ratio"])
    thickness = float(geometry["thickness"])
    density = float(material["density_kg_m3"])
    length = float(geometry["length"])
    width = float(geometry["width"])
    bending = young * thickness**3 / (12.0 * (1.0 - poisson**2))
    omega_11 = np.pi**2 * (1.0 / length**2 + 1.0 / width**2) * np.sqrt(
        bending / (density * thickness)
    )
    frequency = float(omega_11 / (2.0 * np.pi))
    displacement, stress = _navier_plate_response(np.asarray([frequency]), reference)
    return {
        "method": "Kirchhoff-Love Navier odd-odd series",
        "series_max_odd_index": 51,
        "bending_stiffness_n_m": float(bending),
        "fundamental_frequency_hz": frequency,
        "peak_displacement_mm": float(1000.0 * abs(displacement[0])),
        "peak_stress_n_mm2": float(abs(stress[0]) / 1.0e6),
        "stress_definition": "top-face local S11 at plate center",
    }


def _navier_plate_response(
    frequencies_hz: np.ndarray,
    reference: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Return center displacement and top-face S11 from classical plate theory."""
    geometry = reference["model"]["geometry_m"]
    material = reference["model"]["material"]
    young = float(material["young_modulus_pa"])
    poisson = float(material["poisson_ratio"])
    density = float(material["density_kg_m3"])
    thickness = float(geometry["thickness"])
    length = float(geometry["length"])
    width = float(geometry["width"])
    pressure = float(reference["model"]["pressure_pa"])
    damping = reference["model"]["rayleigh_damping"]
    alpha = float(damping["alpha_s_inv"])
    beta = float(damping["beta_s"])
    bending = young * thickness**3 / (12.0 * (1.0 - poisson**2))
    omega = 2.0 * np.pi * np.asarray(frequencies_hz, dtype=float)
    displacement = np.zeros(omega.size, dtype=complex)
    stress = np.zeros(omega.size, dtype=complex)
    for m in range(1, 52, 2):
        for n in range(1, 52, 2):
            kx = m * np.pi / length
            ky = n * np.pi / width
            wave_fourth = (kx**2 + ky**2) ** 2
            load_coefficient = 16.0 * pressure / (np.pi**2 * m * n)
            denominator = (
                bending * wave_fourth
                - density * thickness * omega**2
                + 1j
                * omega
                * (alpha * density * thickness + beta * bending * wave_fourth)
            )
            coefficient = load_coefficient / denominator
            center_sign = np.sin(0.5 * m * np.pi) * np.sin(0.5 * n * np.pi)
            displacement += center_sign * coefficient
            stress += (
                center_sign
                * young
                * (0.5 * thickness)
                / (1.0 - poisson**2)
                * (kx**2 + poisson * ky**2)
                * coefficient
            )
    return displacement, stress


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    correlation = summary["external_correlation"]
    differences = correlation["relative_differences"]
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Correlation externe de la reponse harmonique MITC4 avec le Test 13H NAFEMS
publie dans la documentation Abaqus/Standard 2024. Le modele QF_solver reprend
le maillage `8x8`, la geometrie, les blocages, la pression, l'amortissement de
Rayleigh et les 200 frequences du fichier officiel `nfh13f4x.inp`.

| Resultat | QF_solver | Abaqus S4R | Abaqus S4 | NAFEMS |
| --- | ---: | ---: | ---: | ---: |
| Pic deplacement (mm) | {summary['peak']['peak_displacement_mm']:.6f} | {correlation['abaqus_s4r']['peak_displacement_mm']:.6f} | {correlation['abaqus_s4']['peak_displacement_mm']:.6f} | {correlation['nafems']['peak_displacement_mm']:.6f} |
| Pic S11 face (N/mm2) | {summary['peak']['peak_stress_n_mm2']:.6f} | {correlation['abaqus_s4r']['peak_stress_n_mm2']:.6f} | {correlation['abaqus_s4']['peak_stress_n_mm2']:.6f} | {correlation['nafems']['peak_stress_n_mm2']:.6f} |
| Frequence du pic (Hz) | {summary['peak']['peak_frequency_hz']:.6f} | {correlation['abaqus_s4r']['peak_frequency_hz']:.6f} | {correlation['abaqus_s4']['peak_frequency_hz']:.6f} | {correlation['nafems']['peak_frequency_hz']:.6f} |

- ecart deplacement QF/Abaqus: `{100.0 * differences['abaqus_displacement']:.3f} %`;
- ecart frequence QF/Abaqus: `{100.0 * differences['abaqus_frequency']:.3f} %`;
- ecart S11 QF/Abaqus: `{100.0 * differences['abaqus_stress']:.3f} %`;
- ecart S11 QF/Abaqus S4: `{100.0 * differences['abaqus_s4_stress']:.3f} %`;
- ecart deplacement QF/NAFEMS: `{100.0 * differences['nafems_displacement']:.3f} %`;
- ecart frequence QF/NAFEMS: `{100.0 * differences['nafems_frequency']:.3f} %`;
- ecart S11 QF/NAFEMS: `{100.0 * differences['nafems_stress']:.3f} %`;
- residu relatif maximal: `{summary['peak']['max_relative_residual']:.3e}`.

Statut : **{summary['status']}**.

![Reponse frequentielle]({STUDY_ID}-response.png)

![Contrainte harmonique S11]({STUDY_ID}-stress-response.png)

![Deformee au pic]({STUDY_ID}-deformed.png)

## Provenance et limite

Source primaire: {summary['source']['url']}

La contrainte comparee est l'amplitude de `S11` en face superieure au noeud
central, obtenue par moyenne complexe des quatre facettes adjacentes, comme la
sortie Abaqus `POSITION=AVERAGED AT NODES, ELSET=EMID`.
""",
        encoding="utf-8",
    )


def _plot_response(summary: dict[str, Any], path: Path) -> None:
    rows = summary["frequency_response"]
    correlation = summary["external_correlation"]
    figure, axis = plt.subplots(figsize=(7.4, 4.7))
    axis.plot(
        [row["frequency_hz"] for row in rows],
        [row["center_uz_amplitude_mm"] for row in rows],
        color="#006d77",
        label="QF_solver MITC4",
    )
    for label, record, color in (
        ("Abaqus S4R", correlation["abaqus_s4r"], "#ca6702"),
        ("NAFEMS", correlation["nafems"], "#6c757d"),
    ):
        axis.scatter(
            [record["peak_frequency_hz"]],
            [record["peak_displacement_mm"]],
            label=label,
            color=color,
            zorder=3,
        )
    axis.set_xlabel("frequence (Hz)")
    axis.set_ylabel("amplitude UZ au centre (mm)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_stress_response(summary: dict[str, Any], path: Path) -> None:
    rows = summary["frequency_response"]
    correlation = summary["external_correlation"]
    figure, axes = plt.subplots(2, 1, figsize=(7.4, 6.0), sharex=True)
    axes[0].plot(
        [row["frequency_hz"] for row in rows],
        [row["center_top_s11_amplitude_n_mm2"] for row in rows],
        color="#006d77",
        label="QF_solver MITC4",
    )
    axes[0].plot(
        [row["frequency_hz"] for row in rows],
        [row["navier_top_s11_amplitude_n_mm2"] for row in rows],
        "--",
        color="#6c757d",
        label="theorie de Navier",
    )
    for label, record, color in (
        ("Abaqus S4R", correlation["abaqus_s4r"], "#ca6702"),
        ("Abaqus S4", correlation["abaqus_s4"], "#ee9b00"),
        ("NAFEMS", correlation["nafems"], "#ae2012"),
    ):
        axes[0].scatter(
            [record["peak_frequency_hz"]],
            [record["peak_stress_n_mm2"]],
            color=color,
            label=label,
            zorder=3,
        )
    axes[1].plot(
        [row["frequency_hz"] for row in rows],
        [row["center_top_s11_phase_degrees"] for row in rows],
        color="#006d77",
    )
    axes[0].set_ylabel("amplitude S11 (N/mm2)")
    axes[1].set_ylabel("phase S11 (deg)")
    axes[1].set_xlabel("frequence (Hz)")
    axes[0].legend()
    for axis in axes:
        axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_model_setup(plot_data: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    """Show the undeformed mesh, edge constraints and applied pressure."""
    nodes = np.asarray(plot_data["nodes"], dtype=float)
    quads = np.asarray(plot_data["quads"], dtype=int)
    x = nodes[:, 0]
    y = nodes[:, 1]
    masks = (np.isclose(x, 0.0), np.isclose(x, 10.0), np.isclose(y, 0.0), np.isclose(y, 10.0))
    figure, axis = plt.subplots(figsize=(8.0, 6.2))
    for quad in quads:
        closed = np.append(quad, quad[0])
        axis.plot(nodes[closed, 0], nodes[closed, 1], color="#8d99ae", linewidth=0.65)
    for mask in masks:
        axis.scatter(x[mask], y[mask], color="#c1121f", s=12)
    for coordinate in np.linspace(0.625, 9.375, 8):
        axis.arrow(coordinate, coordinate, 0.0, -0.55, color="#0077b6", width=0.008,
                   head_width=0.16, head_length=0.18, length_includes_head=True)
    axis.scatter([], [], color="#c1121f", label="blocages de bord: UZ, RX ou RY")
    axis.scatter([], [], color="#0077b6", marker="v", label="pression p = 100 Pa, -UZ")
    axis.plot([], [], color="#8d99ae", label="maillage MITC4 8x8")
    axis.set_aspect("equal")
    axis.set_xlim(-0.7, 10.7)
    axis.set_ylim(-0.8, 10.7)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_title("NAFEMS 13H: geometrie, maillage, blocages et pression")
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8)
    axis.grid(True, alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_deformed(plot_data: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    nodes = np.asarray(plot_data["nodes"], dtype=float)
    response = np.asarray(plot_data["peak_response"], dtype=complex)
    dofs = plot_data["dofs"]
    center = int(summary["model"]["center_node"])
    phase = cmath.phase(response[dofs.index(center, "UZ")])
    aligned = response * np.exp(-1j * phase)
    translations = np.asarray(
        [[aligned[dofs.index(node, name)].real for name in ("UX", "UY", "UZ")] for node in range(nodes.shape[0])]
    )
    scale = 1.5 / max(float(np.max(np.abs(translations[:, 2]))), 1.0e-30)
    deformed = nodes + scale * translations
    figure = plt.figure(figsize=(7.4, 5.0))
    axis = figure.add_subplot(111, projection="3d")
    for quad in np.asarray(plot_data["quads"], dtype=int):
        closed = np.append(quad, quad[0])
        axis.plot(*nodes[closed].T, color="#8d99ae", linewidth=0.35)
        axis.plot(*deformed[closed].T, color="#006d77", linewidth=0.8)
    axis.set_title(f"NAFEMS 13H, deformee au pic, facteur {scale:.3e}")
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_zlabel("UZ aligne en phase")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
