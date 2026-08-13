"""Validated and auditable transient response history probes."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor, STRESS_COMPONENTS


def history_row(
    step: int,
    time: float,
    load_factor: float,
    displacement: np.ndarray,
    velocity: np.ndarray,
    acceleration: np.ndarray,
    stiffness: csr_matrix,
    mass: csr_matrix,
    damping: csr_matrix,
    residual_norm: float,
    initial_energy: float,
    probes: list[tuple[str, int]],
    *,
    model: FiniteElementModel,
    dofs: DofManager,
    shell_stress_probes: list[tuple[str, int, str, int]],
    shell_stress_post: HarmonicShellStressPostProcessor | None,
) -> dict[str, object]:
    """Build one history record without storing full nodal state arrays."""
    strain_energy = float(0.5 * displacement @ (stiffness @ displacement))
    kinetic_energy = float(0.5 * velocity @ (mass @ velocity))
    total_energy = strain_energy + kinetic_energy
    row: dict[str, object] = {
        "step": step,
        "time": float(time),
        "load_factor": float(load_factor),
        "max_displacement": float(np.max(np.abs(displacement))),
        "max_velocity": float(np.max(np.abs(velocity))),
        "max_acceleration": float(np.max(np.abs(acceleration))),
        "strain_energy": strain_energy,
        "kinetic_energy": kinetic_energy,
        "total_energy": total_energy,
        "relative_energy_drift": _relative_energy_drift(total_energy, initial_energy),
        "damping_power": float(velocity @ (damping @ velocity)),
        "dynamic_residual_norm": residual_norm,
    }
    if probes:
        row["probes"] = {
            label: {
                "displacement": float(displacement[index]),
                "velocity": float(velocity[index]),
                "acceleration": float(acceleration[index]),
            }
            for label, index in probes
        }
    if shell_stress_probes and shell_stress_post is not None:
        row["shell_stress_probes"] = {
            label: float(
                shell_stress_post.averaged_nodal_stress(
                    model, dofs, displacement, node, face=face
                )[component].real
            )
            for label, node, face, component in shell_stress_probes
        }
    return row


def validated_history_probes(dofs: DofManager, entries: object) -> list[tuple[str, int]]:
    """Validate signed nodal displacement/velocity/acceleration probes."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise InputValidationError("history_probes must be a list of node/dof objects.")
    probes: list[tuple[str, int]] = []
    labels: set[str] = set()
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict) or "node" not in entry or "dof" not in entry:
            raise InputValidationError(f"history_probes[{position}] must define node and dof.")
        node = int(entry["node"])
        dof = str(entry["dof"]).upper()
        label = str(entry.get("label", f"node_{node}_{dof}"))
        if not label or label in labels:
            raise InputValidationError("history_probes labels must be non-empty and unique.")
        try:
            index = dofs.index(node, dof)
        except (KeyError, ValueError) as exc:
            raise InputValidationError(
                f"history_probes[{position}] references unavailable dof {dof} at node {node}."
            ) from exc
        labels.add(label)
        probes.append((label, index))
    return probes


def validated_shell_stress_probes(
    model: FiniteElementModel,
    entries: object,
) -> list[tuple[str, int, str, int]]:
    """Validate shell face-stress probes used by transient V&V."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise InputValidationError("history_shell_stress_probes must be a list of probe objects.")
    shell_nodes = {
        node for element in model.elements if element.type in {"MITC3", "MITC4"} for node in element.nodes
    }
    probes: list[tuple[str, int, str, int]] = []
    labels: set[str] = set()
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict) or "node" not in entry or "component" not in entry:
            raise InputValidationError(
                f"history_shell_stress_probes[{position}] must define node and component."
            )
        node = int(entry["node"])
        face = str(entry.get("face", "top")).lower()
        component_name = str(entry["component"]).upper()
        label = str(entry.get("label", f"node_{node}_{face}_{component_name}"))
        if not label or label in labels:
            raise InputValidationError(
                "history_shell_stress_probes labels must be non-empty and unique."
            )
        if node not in shell_nodes:
            raise InputValidationError(
                f"history_shell_stress_probes[{position}] node {node} has no adjacent shell element."
            )
        if face not in {"top", "bottom"}:
            raise InputValidationError("Shell stress probe face must be 'top' or 'bottom'.")
        if component_name not in STRESS_COMPONENTS:
            raise InputValidationError(
                "Shell stress probe component must be one of S11, S22 or S12."
            )
        labels.add(label)
        probes.append((label, node, face, STRESS_COMPONENTS.index(component_name)))
    return probes


def _relative_energy_drift(total_energy: float, initial_energy: float) -> float:
    if abs(initial_energy) <= 1.0e-30:
        return 0.0
    return float((total_energy - initial_energy) / initial_energy)
