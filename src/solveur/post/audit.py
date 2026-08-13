"""White-box audit helpers for post-processed element results."""

from __future__ import annotations

from typing import Any

import numpy as np

from mitc4.element import MITC4Element
from mitc4.material import ShellMaterial

from solveur.core.dofs import DofManager
from solveur.core.model import ElementDefinition, FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.beam.beam2 import Beam2Element
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.materials.factory import MaterialFactory
from solveur.materials.beam import BeamSectionMaterial
from solveur.materials.laminate import LaminateShellMaterial


class PostProcessingAuditor:
    """Trace element displacement inputs used to recover engineering results."""

    def element_audits(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        displacement: np.ndarray,
        element_results: list[dict[str, object]],
    ) -> list[dict[str, Any]]:
        recovered_by_index = {int(result["element"]): result for result in element_results if "element" in result}
        audits: list[dict[str, Any]] = []
        for index, definition in enumerate(model.elements):
            recovered = recovered_by_index.get(index)
            if recovered is None:
                continue
            spec = ElementRegistry.get(definition.type)
            global_dofs: list[int] = []
            for node in definition.nodes:
                global_dofs.extend(dofs.node_indices(node, spec.dofs))
            global_u = np.asarray(displacement[global_dofs], dtype=float)
            calculation_u, frame = self._calculation_displacement(model, definition, global_u)
            entry: dict[str, Any] = {
                "element": int(index),
                "type": definition.type,
                "nodes": [int(node) for node in definition.nodes],
                "material": definition.material,
                "dofs_per_node": list(spec.dofs),
                "global_dof_indices": [int(item) for item in global_dofs],
                "global_dof_displacement": _float_list(global_u),
                "calculation_frame": frame,
                "calculation_displacement": _float_list(calculation_u),
                "calculation_displacement_norm": float(np.linalg.norm(calculation_u)),
            }
            entry.update({key: value for key, value in recovered.items() if key not in {"element", "type"}})
            audits.append(entry)
        return audits

    @staticmethod
    def _calculation_displacement(
        model: FiniteElementModel,
        definition: ElementDefinition,
        global_displacement: np.ndarray,
    ) -> tuple[np.ndarray, str]:
        if definition.type == "BEAM2":
            material = MaterialFactory.create(model.materials[definition.material])
            if isinstance(material, BeamSectionMaterial):
                coords = model.nodes[list(definition.nodes)]
                transform = Beam2Element(material).transformation(coords)
                return transform @ np.asarray(global_displacement, dtype=float), "beam2_local"
        if definition.type not in {"MITC3", "MITC4"}:
            return np.asarray(global_displacement, dtype=float), "global"
        material = MaterialFactory.create(model.materials[definition.material])
        if not isinstance(material, (ShellMaterial, LaminateShellMaterial)):
            return np.asarray(global_displacement, dtype=float), "global"
        coords = model.nodes[list(definition.nodes)]
        element = Mitc3ShellElement(material) if definition.type == "MITC3" else MITC4Element(material)
        frame, _ = element.project_to_local_midplane(coords)
        transform = element.transform_dofs(frame)
        return (
            transform @ np.asarray(global_displacement, dtype=float),
            f"{definition.type.lower()}_midplane_local",
        )


def _float_list(values: np.ndarray) -> list[float]:
    return [float(value) for value in np.asarray(values, dtype=float).ravel()]
