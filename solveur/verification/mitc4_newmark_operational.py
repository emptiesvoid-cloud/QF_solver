"""Operational MITC4 Newmark V&V for loads, damping and restart."""

from __future__ import annotations

import math
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "VNV-MITC4-NEWMARK-OPERATIONAL-006"


class Mitc4NewmarkOperationalStudy:
    """Verify independent load histories, modal damping fit and restart identity."""

    superposition_limits = {
        "displacement": 1.0e-10,
        "velocity": 1.0e-9,
        "acceleration": 1.0e-7,
        "probe_history": 1.0e-7,
    }
    damping_fit_limit = 1.0e-12
    free_decay_rms_limit = 0.01
    restart_limit = 1.0e-11
    residual_limit = 1.0e-7

    def run(self, work_dir: str | Path) -> dict[str, Any]:
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        modal_model, quads = _plate_model(
            {"type": "modal", "method": "eigh", "modes": 6}, loads=False
        )
        modal = solve_model(modal_model, enforce_policy=False)
        first_frequency = float(modal.frequencies_hz[0])
        third_frequency = float(modal.frequencies_hz[2])
        targets = [
            {"frequency_hz": first_frequency, "damping_ratio": 0.02},
            {"frequency_hz": third_frequency, "damping_ratio": 0.04},
        ]
        expected_alpha, expected_beta = _rayleigh_fit(targets)
        period = 1.0 / first_frequency
        steps = 80
        dt = period / steps
        first_history = [math.sin(math.pi * step / steps) for step in range(steps + 1)]
        second_history = [
            math.sin(2.0 * math.pi * (0.25 * step / steps + 1.75 * (step / steps) ** 2))
            for step in range(steps + 1)
        ]

        combined = self._forced_run(
            targets, dt, steps, first_history, second_history
        )
        first_only = self._forced_run(
            targets, dt, steps, first_history, [0.0] * (steps + 1)
        )
        second_only = self._forced_run(
            targets, dt, steps, [0.0] * (steps + 1), second_history
        )
        superposition = {
            "displacement": _relative_state_error(
                combined.displacements,
                first_only.displacements + second_only.displacements,
            ),
            "velocity": _relative_state_error(
                combined.velocities,
                first_only.velocities + second_only.velocities,
            ),
            "acceleration": _relative_state_error(
                combined.accelerations,
                first_only.accelerations + second_only.accelerations,
            ),
            "probe_history": _history_superposition_error(
                combined, first_only, second_only
            ),
        }

        checkpoint = work / "newmark_operational_state.npz"
        checkpoint_run = self._forced_run(
            targets,
            dt,
            steps,
            first_history,
            second_history,
            checkpoint_path=checkpoint,
        )
        intermediate = checkpoint.with_name(
            f"{checkpoint.stem}.step{steps // 2:08d}{checkpoint.suffix}"
        )
        restarted = self._forced_run(
            targets,
            dt,
            steps,
            first_history,
            second_history,
            restart_from=intermediate,
        )
        restart = {
            "displacement": _relative_state_error(
                restarted.displacements, checkpoint_run.displacements
            ),
            "velocity": _relative_state_error(
                restarted.velocities, checkpoint_run.velocities
            ),
            "acceleration": _relative_state_error(
                restarted.accelerations, checkpoint_run.accelerations
            ),
            "restart_step": int(restarted.solver["restart_step"]),
            "history_is_partial": bool(restarted.solver["history_is_partial"]),
        }

        decay = _free_decay_run(modal_model, modal, targets, period)
        damping = combined.solver["damping_definition"]
        damping_fit = {
            "expected_alpha": expected_alpha,
            "computed_alpha": float(damping["rayleigh_alpha"]),
            "alpha_relative_error": _relative_scalar_error(
                float(damping["rayleigh_alpha"]), expected_alpha
            ),
            "expected_beta": expected_beta,
            "computed_beta": float(damping["rayleigh_beta"]),
            "beta_relative_error": _relative_scalar_error(
                float(damping["rayleigh_beta"]), expected_beta
            ),
            "source": damping["source"],
            "target_ratios": targets,
        }
        residual_max = max(
            max(float(value) for value in result.solver["residual_history"])
            for result in (combined, first_only, second_only, checkpoint_run, restarted)
        )
        checks = {
            "multicomponent_superposition": all(
                superposition[name] <= limit
                for name, limit in self.superposition_limits.items()
            ),
            "modal_damping_fit": max(
                damping_fit["alpha_relative_error"], damping_fit["beta_relative_error"]
            )
            <= self.damping_fit_limit,
            "first_mode_free_decay": decay["relative_rms_error"]
            <= self.free_decay_rms_limit,
            "nonnegative_damping_power": decay["minimum_damping_power"] >= -1.0e-12,
            "checkpoint_restart_identity": max(
                restart["displacement"], restart["velocity"], restart["acceleration"]
            )
            <= self.restart_limit,
            "restart_metadata": restart["restart_step"] == steps // 2
            and restart["history_is_partial"],
            "dynamic_residual": residual_max <= self.residual_limit,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "model": {
                "geometry": "MITC4 cantilever plate 1.0 m x 0.2 m x 0.01 m",
                "mesh": [6, 2],
                "element_count": len(modal_model.elements),
                "node_count": modal_model.node_count,
                "mass_formulation": "consistent",
                "drilling": "RZ constrained for stiffness-proportional damping proof",
                "load_components": ["tip UZ force", "tip RY moment"],
            },
            "modal_basis": {
                "first_frequency_hz": first_frequency,
                "third_frequency_hz": third_frequency,
                "target_damping_ratios": [0.02, 0.04],
            },
            "time_integration": {
                "time_step": dt,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
            },
            "superposition": superposition,
            "damping_fit": damping_fit,
            "free_decay": {key: value for key, value in decay.items() if key != "_plot"},
            "restart": restart,
            "maximum_dynamic_residual_norm": residual_max,
            "acceptance": {
                "superposition_relative_error_max": self.superposition_limits,
                "damping_fit_relative_error_max": self.damping_fit_limit,
                "free_decay_relative_rms_error_max": self.free_decay_rms_limit,
                "restart_relative_error_max": self.restart_limit,
                "dynamic_residual_norm_max": self.residual_limit,
            },
            "checks": checks,
            "limitations": [
                "Modal damping means Rayleigh coefficients fitted to two modal targets.",
                "Arbitrary independent damping ratios for every mode are not implemented.",
                "RZ is constrained in this proof so stiffness-proportional damping needs no drilling condensation.",
                "Restart identity is verified on NPZ checkpoints in a single-process calculation.",
            ],
            "_plot": {
                "combined": _probe_history(combined),
                "first": _probe_history(first_only),
                "second": _probe_history(second_only),
                "decay": decay["_plot"],
                "nodes": modal_model.nodes,
                "quads": quads,
            },
        }

    @staticmethod
    def _forced_run(
        targets: list[dict[str, float]],
        dt: float,
        steps: int,
        first: list[float],
        second: list[float],
        *,
        checkpoint_path: Path | None = None,
        restart_from: Path | None = None,
    ) -> object:
        analysis: dict[str, object] = {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": dt,
            "steps": steps,
            "modal_damping_targets": targets,
            "load_factors_by_load": {"0": first, "1": second},
            "history_probes": [
                {"node": 13, "dof": "UZ", "label": "tip_uz"},
                {"node": 20, "dof": "RY", "label": "tip_ry"},
            ],
        }
        if checkpoint_path is not None:
            analysis.update(
                {
                    "checkpoint_path": str(checkpoint_path),
                    "checkpoint_interval": steps // 2,
                    "checkpoint_keep_steps": True,
                }
            )
        if restart_from is not None:
            analysis["restart_from"] = str(restart_from)
        model, _ = _plate_model(analysis, loads=True)
        return solve_model(model, enforce_policy=False)


def write_mitc4_newmark_operational_evidence(output: str | Path) -> dict[str, Any]:
    """Run the study and write JSON, Markdown, PNG and manifest evidence."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4NewmarkOperationalStudy().run(target)
    plot = summary.pop("_plot")
    write_json_file(target / "summary.json", summary)
    _plot_results(plot, target / f"{STUDY_ID}.png")
    (target / f"{STUDY_ID}.md").write_text(_markdown(summary), encoding="utf-8")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_newmark_operational_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _plate_model(
    analysis: dict[str, object], *, loads: bool
) -> tuple[FiniteElementModel, np.ndarray]:
    mesh = MeshFactory.rectangular_plate(6, 2, 1.0, 0.2)
    root = set(np.flatnonzero(np.isclose(mesh.nodes[:, 0], 0.0)).tolist())
    fixed = [
        {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
        for node in sorted(root)
    ]
    fixed.extend(
        {"node": node, "dofs": ["RZ"]}
        for node in range(mesh.nodes.shape[0])
        if node not in root
    )
    load_data = (
        [
            {"node": 13, "dof": "UZ", "value": -100.0},
            {"node": 20, "dof": "RY", "value": 10.0},
        ]
        if loads
        else []
    )
    return (
        FiniteElementModel.from_raw(
            analysis=analysis,
            nodes=mesh.nodes.tolist(),
            elements=[
                {"type": "MITC4", "nodes": quad.tolist(), "material": "skin"}
                for quad in mesh.quads
            ],
            materials={
                "skin": {
                    "type": "shell_isotropic",
                    "E": 70.0e9,
                    "nu": 0.3,
                    "t": 0.01,
                    "density": 2700.0,
                    "drilling_scale": 1.0e-4,
                }
            },
            fixed_dofs=fixed,
            loads=load_data,
        ),
        mesh.quads,
    )


def _free_decay_run(
    modal_model: FiniteElementModel,
    modal: object,
    targets: list[dict[str, float]],
    period: float,
) -> dict[str, Any]:
    mode = np.asarray(modal.modes[:, 0], dtype=float)
    mode *= 1.0e-4 / max(float(np.max(np.abs(mode))), 1.0e-30)
    uz = np.asarray(
        [modal.dofs.index(node, "UZ") for node in range(modal_model.node_count)]
    )
    probe_node = int(np.argmax(np.abs(mode[uz])))
    initial = []
    for node, names in modal.dofs.node_dofs.items():
        for name in names:
            value = float(mode[modal.dofs.index(node, name)])
            if abs(value) > 1.0e-18:
                initial.append({"node": node, "dof": name, "value": value})
    steps_per_period = 80
    steps = 3 * steps_per_period
    analysis = {
        "type": "transient_dynamic",
        "method": "newmark",
        "time_step": period / steps_per_period,
        "steps": steps,
        "modal_damping_targets": targets,
        "load_factors": [0.0],
        "initial_displacements": initial,
        "history_probes": [{"node": probe_node, "dof": "UZ", "label": "mode_1"}],
    }
    model, _ = _plate_model(analysis, loads=False)
    result = solve_model(model, enforce_policy=False)
    times = np.asarray([row["time"] for row in result.solver["time_history"]])
    numerical = np.asarray(
        [row["probes"]["mode_1"]["displacement"] for row in result.solver["time_history"]]
    )
    amplitude = float(mode[modal.dofs.index(probe_node, "UZ")])
    omega = 2.0 * math.pi / period
    ratio = float(targets[0]["damping_ratio"])
    damped_omega = omega * math.sqrt(1.0 - ratio**2)
    analytical = amplitude * np.exp(-ratio * omega * times) * (
        np.cos(damped_omega * times)
        + ratio / math.sqrt(1.0 - ratio**2) * np.sin(damped_omega * times)
    )
    error = float(
        np.sqrt(np.mean((numerical - analytical) ** 2))
        / max(float(np.max(np.abs(analytical))), 1.0e-30)
    )
    return {
        "probe_node": probe_node,
        "damping_ratio": ratio,
        "relative_rms_error": error,
        "minimum_damping_power": min(
            float(row["damping_power"]) for row in result.solver["time_history"]
        ),
        "maximum_dynamic_residual_norm": max(
            float(value) for value in result.solver["residual_history"]
        ),
        "_plot": {
            "times": times,
            "numerical": numerical,
            "analytical": analytical,
        },
    }


def _rayleigh_fit(targets: list[dict[str, float]]) -> tuple[float, float]:
    omegas = np.asarray([2.0 * math.pi * item["frequency_hz"] for item in targets])
    ratios = np.asarray([item["damping_ratio"] for item in targets])
    return tuple(
        float(value)
        for value in np.linalg.solve(
            np.column_stack((0.5 / omegas, 0.5 * omegas)), ratios
        )
    )


def _relative_state_error(value: np.ndarray, reference: np.ndarray) -> float:
    return float(
        np.linalg.norm(value - reference) / max(float(np.linalg.norm(reference)), 1.0)
    )


def _relative_scalar_error(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _history_superposition_error(combined: object, first: object, second: object) -> float:
    errors = []
    references = []
    for combined_row, first_row, second_row in zip(
        combined.solver["time_history"],
        first.solver["time_history"],
        second.solver["time_history"],
        strict=True,
    ):
        for label in ("tip_uz", "tip_ry"):
            for field in ("displacement", "velocity", "acceleration"):
                reference = (
                    first_row["probes"][label][field]
                    + second_row["probes"][label][field]
                )
                errors.append(combined_row["probes"][label][field] - reference)
                references.append(reference)
    return float(
        np.linalg.norm(errors) / max(float(np.linalg.norm(references)), 1.0)
    )


def _probe_history(result: object) -> dict[str, list[float]]:
    rows = result.solver["time_history"]
    return {
        "time": [float(row["time"]) for row in rows],
        "tip_uz": [float(row["probes"]["tip_uz"]["displacement"]) for row in rows],
        "tip_ry": [float(row["probes"]["tip_ry"]["displacement"]) for row in rows],
    }


def _plot_results(data: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(12.0, 3.8))
    for name, color in (("first", "#1971c2"), ("second", "#e8590c"), ("combined", "#087f5b")):
        axes[0].plot(data[name]["time"], data[name]["tip_uz"], label=name, color=color)
        axes[1].plot(data[name]["time"], data[name]["tip_ry"], label=name, color=color)
    axes[0].set(xlabel="temps [s]", ylabel="UZ [m]", title="Charge force + moment")
    axes[1].set(xlabel="temps [s]", ylabel="RY [rad]", title="Superposition des composantes")
    decay = data["decay"]
    axes[2].plot(decay["times"], decay["numerical"], label="Newmark", color="#087f5b")
    axes[2].plot(decay["times"], decay["analytical"], "--", label="oracle modal", color="#343a40")
    axes[2].set(xlabel="temps [s]", ylabel="UZ [m]", title="Decroissance du mode 1")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _markdown(summary: dict[str, Any]) -> str:
    superposition = summary["superposition"]
    damping = summary["damping_fit"]
    decay = summary["free_decay"]
    restart = summary["restart"]
    limitations = "\n".join(f"- {item}" for item in summary["limitations"])
    return f"""# {STUDY_ID}

Statut automatique: **{summary['status']}**.

## Chargements multi-composantes

| Indicateur de superposition | Erreur relative |
| --- | ---: |
| deplacement final | {superposition['displacement']:.3e} |
| vitesse finale | {superposition['velocity']:.3e} |
| acceleration finale | {superposition['acceleration']:.3e} |
| historiques des sondes | {superposition['probe_history']:.3e} |

## Amortissement cale sur deux modes

```text
zeta(omega) = alpha / (2 omega) + beta omega / 2
```

| Coefficient | Reference | Calcule | Erreur relative |
| --- | ---: | ---: | ---: |
| alpha | {damping['expected_alpha']:.6e} | {damping['computed_alpha']:.6e} | {damping['alpha_relative_error']:.3e} |
| beta | {damping['expected_beta']:.6e} | {damping['computed_beta']:.6e} | {damping['beta_relative_error']:.3e} |

Erreur RMS de decroissance libre du premier mode: `{decay['relative_rms_error']:.3e}`.

## Reprise checkpoint

| Etat final | Erreur relative reprise/continu |
| --- | ---: |
| deplacement | {restart['displacement']:.3e} |
| vitesse | {restart['velocity']:.3e} |
| acceleration | {restart['acceleration']:.3e} |

![Resultats]({STUDY_ID}.png)

## Limites

{limitations}
"""
