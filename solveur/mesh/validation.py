"""Model and mesh validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mitc4.element import MITC4Element
from mitc4.material import ShellMaterial

from solveur.core.dofs import normalize_dof_name
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.shell.frames import director_frame, rotation_subspace_is_invariant
from solveur.elements.solid.tet10 import Tet10Element
from solveur.loads.entities import BodyLoad, EdgeLoad, GravityLoad, LineLoad, SurfaceLoad
from solveur.materials.factory import MaterialFactory
from solveur.mesh.constraint_validation import multipoint_constraint_errors
from solveur.mesh.contact_validation import frictionless_contact_errors
from solveur.mesh.quality import MeshQuality, MeshQualityThresholds
from solveur.mesh.topology import MITC3_EDGES, MITC4_EDGES
from solveur.mesh.validation_helpers import (
    distributed_element_indices as _distributed_element_indices,
    distributed_target_elements as _distributed_target_elements,
    finite_float_or_nan as _finite_float_or_nan,
    is_finite_scalar as _is_finite_scalar,
    is_finite_vector3 as _is_finite_vector3,
    shell_node_directors as _shell_node_directors,
    valid_element_index as _valid_element_index,
)


@dataclass(frozen=True)
class MeshReport:
    """Validation report with blocking errors and non-blocking warnings."""

    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "errors": self.errors, "warnings": self.warnings, "details": self.details}
class MeshValidator:
    """Validate model references, dofs and element geometry before solving."""
    def __init__(self, thresholds: MeshQualityThresholds | None = None) -> None:
        self.thresholds = thresholds or MeshQualityThresholds()
    def validate(self, model: FiniteElementModel) -> MeshReport:
        errors: list[str] = []
        warnings: list[str] = []
        details = self._base_details(model)
        details["quality_thresholds"] = self.thresholds.to_dict()
        self._check_nodes(model, errors)
        self._check_elements(model, errors, warnings)
        self._check_shell_orientation(model, errors)
        details["element_quality"] = self._element_quality_details(model, warnings)
        self._enforce_qualification_shell_domain(model, details["element_quality"], errors)
        topology = self._topology_details(model, warnings)
        details.update(topology)
        self._check_materials(model, errors)
        self._check_analysis_requirements(model, errors)
        self._check_distributed_loads(model, errors)
        self._check_discrete_entities(model, errors)
        errors.extend(frictionless_contact_errors(model))
        dofs = model.dof_manager() if not errors else None
        if dofs is not None:
            self._check_conditions(model, dofs, errors, warnings)
            errors.extend(multipoint_constraint_errors(model, dofs))
            self._check_component_constraints(model, dofs, details, warnings)
            self._check_mechanical_rank(model, dofs, details, warnings)
        if not model.fixed_dofs:
            warnings.append("No fixed degree of freedom is defined; the solve may be singular.")
        status = "FAIL" if errors else "WARNING" if warnings else "PASS"
        details["error_count"] = len(errors)
        details["warning_count"] = len(warnings)
        return MeshReport(status=status, errors=errors, warnings=warnings, details=details)

    @staticmethod
    def _enforce_qualification_shell_domain(
        model: FiniteElementModel, quality: list[dict[str, Any]], errors: list[str]
    ) -> None:
        if model.verification_profile != "qualification":
            return
        for entry in quality:
            if entry.get("type") in {"MITC3", "MITC4"} and entry.get("quality_status") == "WARNING":
                errors.append(
                    "Qualification profile rejects shell element "
                    f"{entry['index']} outside the bounded mesh-quality domain: "
                    + "; ".join(entry.get("quality_warnings", []))
                )

    @staticmethod
    def _base_details(model: FiniteElementModel) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for element in model.elements:
            counts[element.type] = counts.get(element.type, 0) + 1
        return {
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "material_count": len(model.materials),
            "fixed_condition_count": len(model.fixed_dofs),
            "load_count": len(model.loads) + len(model.distributed_loads),
            "nodal_load_count": len(model.loads),
            "distributed_load_count": len(model.distributed_loads),
            "spring_count": len(model.springs),
            "concentrated_mass_count": len(model.concentrated_masses),
            "multipoint_constraint_count": len(model.multipoint_constraints),
            "rbe2_count": len(model.rbe2),
            "rbe3_count": len(model.rbe3),
            "contact_count": len(model.contacts),
            "element_types": dict(sorted(counts.items())),
        }

    @staticmethod
    def _check_nodes(model: FiniteElementModel, errors: list[str]) -> None:
        if model.node_count == 0:
            errors.append("Model contains no node.")
        if not np.all(np.isfinite(model.nodes)):
            errors.append("Node coordinates contain non-finite values.")
        unique = np.unique(model.nodes, axis=0)
        if unique.shape[0] != model.nodes.shape[0]:
            errors.append("Model contains exact duplicate nodes.")

    def _check_elements(self, model: FiniteElementModel, errors: list[str], warnings: list[str]) -> None:
        if not model.elements:
            if not model.springs:
                errors.append("Model contains neither finite element nor spring.")
            return
        for index, element in enumerate(model.elements):
            try:
                spec = ElementRegistry.get(element.type)
            except ValueError as exc:
                errors.append(f"Element {index}: {exc}")
                continue
            if len(element.nodes) != spec.node_count:
                errors.append(f"Element {index}: {element.type} expects {spec.node_count} nodes.")
                continue
            if len(set(element.nodes)) != len(element.nodes):
                errors.append(f"Element {index}: repeated node in connectivity.")
                continue
            if any(node < 0 or node >= model.node_count for node in element.nodes):
                errors.append(f"Element {index}: node index outside model node range.")
                continue
            coords = model.nodes[list(element.nodes)]
            self._check_element_geometry(index, element.type, coords, errors, warnings)

    def _element_quality_details(self, model: FiniteElementModel, warnings: list[str]) -> list[dict[str, Any]]:
        details: list[dict[str, Any]] = []
        for index, element in enumerate(model.elements):
            if any(node < 0 or node >= model.node_count for node in element.nodes):
                continue
            coords = model.nodes[list(element.nodes)]
            if element.type == "TET10":
                metrics = MeshQuality.tet10_metrics(coords)
                entry = {"index": index, "type": element.type, **metrics}
                local_warnings = self._tet_quality_warnings(index, element.type, metrics)
            elif element.type == "TET4":
                metrics = MeshQuality.tet_metrics(coords)
                entry = {"index": index, "type": element.type, **metrics}
                local_warnings = self._tet_quality_warnings(index, element.type, metrics)
            elif element.type == "MITC4":
                metrics = MeshQuality.quad_metrics(coords)
                entry = {"index": index, "type": element.type, **metrics}
                local_warnings = self._mitc4_quality_warnings(index, metrics)
            elif element.type == "MITC3":
                metrics = MeshQuality.triangle_metrics(coords)
                entry = {"index": index, "type": element.type, **metrics}
                local_warnings = self._mitc3_quality_warnings(index, metrics)
            elif element.type == "BEAM2":
                length = float(np.linalg.norm(coords[1] - coords[0]))
                entry = {"index": index, "type": element.type, "length": length}
                local_warnings = []
            else:
                entry = {"index": index, "type": element.type}
                local_warnings = []
            invalid_tet10_jacobian = (
                element.type == "TET10"
                and entry["sampled_jacobian_min"] <= self.thresholds.tet10_min_sampled_jacobian
            )
            if element.type == "BEAM2" and entry["length"] <= 1.0e-14:
                entry["quality_status"] = "FAIL"
            elif element.type == "MITC3" and entry["area"] <= 1.0e-14:
                entry["quality_status"] = "FAIL"
            elif element.type in {"TET4", "TET10"} and (
                entry["signed_volume"] <= self.thresholds.tet_min_signed_volume or invalid_tet10_jacobian
            ):
                entry["quality_status"] = "FAIL"
            else:
                entry["quality_status"] = "WARNING" if local_warnings else "PASS"
            entry["quality_warnings"] = local_warnings
            warnings.extend(local_warnings)
            details.append(entry)
        return details

    def _tet_quality_warnings(self, index: int, element_type: str, metrics: dict[str, float]) -> list[str]:
        thresholds = self.thresholds
        warnings: list[str] = []
        if metrics["quality"] < thresholds.tet_min_quality:
            warnings.append(f"Element {index}: low {element_type} quality {metrics['quality']:.3e}.")
        if metrics["radius_ratio"] < thresholds.tet_min_radius_ratio:
            warnings.append(f"Element {index}: low {element_type} radius ratio {metrics['radius_ratio']:.3e}.")
        if metrics["aspect_ratio"] > thresholds.tet_max_aspect_ratio:
            warnings.append(f"Element {index}: high {element_type} aspect ratio {metrics['aspect_ratio']:.3e}.")
        if metrics["relative_volume"] < thresholds.tet_min_relative_volume:
            warnings.append(f"Element {index}: low {element_type} relative volume {metrics['relative_volume']:.3e}.")
        if element_type == "TET10":
            if metrics["mid_edge_deviation_ratio_max"] > thresholds.tet10_max_mid_edge_deviation_ratio:
                warnings.append(
                    f"Element {index}: curved or misplaced TET10 midside node; maximum relative "
                    f"edge deviation {metrics['mid_edge_deviation_ratio_max']:.3e}."
                )
            if metrics["sampled_jacobian_ratio"] < thresholds.tet10_min_jacobian_ratio:
                warnings.append(
                    f"Element {index}: high TET10 Jacobian variation; sampled ratio "
                    f"{metrics['sampled_jacobian_ratio']:.3e}."
                )
        return warnings

    def _mitc4_quality_warnings(self, index: int, metrics: dict[str, float]) -> list[str]:
        thresholds = self.thresholds
        warnings: list[str] = []
        if metrics["aspect_ratio"] > thresholds.mitc4_max_aspect_ratio:
            warnings.append(f"Element {index}: high MITC4 aspect ratio {metrics['aspect_ratio']:.3e}.")
        if metrics["planarity_ratio"] > thresholds.mitc4_max_planarity_ratio:
            warnings.append(
                f"Element {index}: non-planar MITC4, normalized distance {metrics['planarity_ratio']:.3e}."
            )
        if (
            metrics["angle_min_degrees"] < thresholds.mitc4_min_angle_degrees
            or metrics["angle_max_degrees"] > thresholds.mitc4_max_angle_degrees
        ):
            warnings.append(
                f"Element {index}: distorted MITC4 angles "
                f"{metrics['angle_min_degrees']:.2f}/{metrics['angle_max_degrees']:.2f} degrees."
            )
        if metrics["warpage_degrees"] > thresholds.mitc4_max_warpage_degrees:
            warnings.append(f"Element {index}: warped MITC4 angle {metrics['warpage_degrees']:.2f} degrees.")
        return warnings

    def _mitc3_quality_warnings(self, index: int, metrics: dict[str, float]) -> list[str]:
        thresholds = self.thresholds
        warnings: list[str] = []
        if metrics["aspect_ratio"] > thresholds.mitc3_max_aspect_ratio:
            warnings.append(f"Element {index}: high MITC3 aspect ratio {metrics['aspect_ratio']:.3e}.")
        if metrics["relative_area"] < thresholds.mitc3_min_relative_area:
            warnings.append(f"Element {index}: low MITC3 relative area {metrics['relative_area']:.3e}.")
        if (
            metrics["angle_min_degrees"] < thresholds.mitc3_min_angle_degrees
            or metrics["angle_max_degrees"] > thresholds.mitc3_max_angle_degrees
        ):
            warnings.append(
                f"Element {index}: distorted MITC3 angles "
                f"{metrics['angle_min_degrees']:.2f}/{metrics['angle_max_degrees']:.2f} degrees."
            )
        return warnings

    @staticmethod
    def _check_shell_orientation(model: FiniteElementModel, errors: list[str]) -> None:
        uses: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        for index, definition in enumerate(model.elements):
            if definition.type not in {"MITC3", "MITC4"}:
                continue
            edges = MITC3_EDGES if definition.type == "MITC3" else MITC4_EDGES
            for first, second in edges:
                a, b = int(definition.nodes[first]), int(definition.nodes[second])
                uses.setdefault(tuple(sorted((a, b))), []).append((index, a, b))
        for edge, entries in uses.items():
            if len(entries) > 2:
                errors.append(f"Non-manifold shell edge {edge} belongs to {len(entries)} elements.")
            elif len(entries) == 2 and entries[0][1:] == entries[1][1:]:
                errors.append(f"Inconsistent shell orientation across edge {edge}.")

    @staticmethod
    def _topology_details(model: FiniteElementModel, warnings: list[str]) -> dict[str, Any]:
        adjacency: dict[int, set[int]] = {node: set() for node in range(model.node_count)}
        node_elements: dict[int, list[int]] = {node: [] for node in range(model.node_count)}
        referenced_nodes: set[int] = set()
        for element_index, element in enumerate(model.elements):
            valid_nodes = [int(node) for node in element.nodes if 0 <= int(node) < model.node_count]
            referenced_nodes.update(valid_nodes)
            for node in valid_nodes:
                node_elements[node].append(element_index)
            for node in valid_nodes:
                adjacency[node].update(other for other in valid_nodes if other != node)
        for spring in model.springs:
            if 0 <= spring.node_a < model.node_count:
                referenced_nodes.add(spring.node_a)
            if spring.node_b is not None and 0 <= spring.node_b < model.node_count:
                referenced_nodes.add(spring.node_b)
                adjacency[spring.node_a].add(spring.node_b)
                adjacency[spring.node_b].add(spring.node_a)
        referenced_nodes.update(mass.node for mass in model.concentrated_masses if 0 <= mass.node < model.node_count)
        for contact in model.contacts:
            contact_nodes = {node for node in (contact.slave_node, *contact.referenced_master_nodes) if 0 <= node < model.node_count}
            referenced_nodes.update(contact_nodes)
            for node in contact_nodes:
                adjacency[node].update(contact_nodes - {node})
        isolated = [node for node in range(model.node_count) if node not in referenced_nodes]
        if isolated:
            warnings.append(f"Mesh contains isolated nodes not referenced by any element: {isolated}.")
        visited: set[int] = set()
        components: list[dict[str, Any]] = []
        for start in range(model.node_count):
            if start in visited or start not in referenced_nodes:
                continue
            stack = [start]
            nodes: list[int] = []
            element_ids: set[int] = set()
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                nodes.append(node)
                element_ids.update(node_elements[node])
                stack.extend(sorted(adjacency[node] - visited))
            types: dict[str, int] = {}
            for element_id in element_ids:
                element_type = model.elements[element_id].type
                types[element_type] = types.get(element_type, 0) + 1
            components.append(
                {
                    "index": len(components),
                    "nodes": sorted(nodes),
                    "elements": sorted(element_ids),
                    "element_types": dict(sorted(types.items())),
                }
            )
        return {"component_count": len(components), "components": components, "isolated_nodes": isolated}

    @staticmethod
    def _check_materials(model: FiniteElementModel, errors: list[str]) -> None:
        for index, element in enumerate(model.elements):
            if element.material not in model.materials:
                errors.append(f"Element {index}: unknown material {element.material!r}.")
                continue
            try:
                expected = ElementRegistry.get(element.type).material_types
            except ValueError:
                continue
            material_type = str(model.materials[element.material].get("type", "")).lower()
            if material_type not in expected:
                errors.append(
                    f"Element {index}: material {element.material!r} has type "
                    f"{material_type!r}, expected one of {expected}."
                )
                continue
            if element.type == "BEAM2":
                try:
                    material = MaterialFactory.create(
                        model.materials[element.material],
                        coordinates=model.nodes[list(element.nodes)],
                    )
                    ElementRegistry.get(element.type).factory(material).local_frame(
                        model.nodes[list(element.nodes)]
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    errors.append(f"Element {index}: invalid BEAM2 section or orientation: {exc}")

    @staticmethod
    def _check_analysis_requirements(model: FiniteElementModel, errors: list[str]) -> None:
        if model.analysis.type not in {"modal", "transient_dynamic", "harmonic_response"}:
            if model.analysis.type == "nonlinear_static":
                for index, element in enumerate(model.elements):
                    if element.type not in {"TET4", "TET10"}:
                        errors.append(f"Element {index}: nonlinear static analysis is currently implemented for TET4/TET10 only.")
            return
        for index, element in enumerate(model.elements):
            if element.type not in {"TET4", "TET10", "MITC3", "MITC4", "BEAM2"}:
                errors.append(f"Element {index}: dynamic mass is not implemented for {element.type}.")
                continue
            material = model.materials.get(element.material, {})
            if str(material.get("type", "")).lower() == "shell_laminate":
                density = float(getattr(MaterialFactory.create(material), "density", 0.0))
            else:
                density = float(material.get("density", material.get("rho", 0.0)))
            if density <= 0.0:
                errors.append(f"Element {index}: {model.analysis.type} analysis requires positive density.")
            if element.type in {"MITC3", "MITC4"}:
                drilling_scale = float(material.get("drilling_scale", 1.0e-4))
                if drilling_scale <= 0.0:
                    errors.append(
                        f"Element {index}: {element.type} dynamic analysis requires drilling_scale > 0."
                    )
        if model.analysis.type in {"modal", "transient_dynamic", "harmonic_response"} and any(
            element.type in {"MITC3", "MITC4"} for element in model.elements
        ):
            rotational = {"RX", "RY", "RZ"}
            by_node: dict[int, set[str]] = {}
            for condition in model.fixed_dofs:
                by_node.setdefault(condition.node, set()).update(rotational.intersection(condition.dofs))
            directors = _shell_node_directors(model)
            for node, fixed_rotations in by_node.items():
                if fixed_rotations and fixed_rotations != rotational:
                    flags = [name in fixed_rotations for name in ("RX", "RY", "RZ")]
                    director = directors.get(node)
                    if director is not None and not rotation_subspace_is_invariant(
                        director_frame(director), flags
                    ):
                        errors.append(
                            "Shell partial rotational constraints must align with the nodal shell "
                            f"director frame at node {node}."
                        )

    @staticmethod
    def _check_distributed_loads(model: FiniteElementModel, errors: list[str]) -> None:
        """Validate typed loads created directly through the public Python API."""
        for load_index, load in enumerate(model.distributed_loads):
            path = f"Distributed load {load_index}"
            if isinstance(load, (GravityLoad, BodyLoad)):
                targets = _distributed_target_elements(load, len(model.elements), path, errors)
                vector = load.acceleration if isinstance(load, GravityLoad) else load.value
                if not _is_finite_vector3(vector):
                    errors.append(f"{path}: load vector must contain three finite components.")
                if isinstance(load, BodyLoad) and load.coordinate_system not in {"global", "local"}:
                    errors.append(f"{path}: coordinate system must be 'global' or 'local'.")
                for element_index in targets:
                    definition = model.elements[element_index]
                    if isinstance(load, BodyLoad) and load.coordinate_system == "local" and definition.type not in {"MITC3", "MITC4"}:
                        errors.append(f"{path}: local body force is supported for shell elements only.")
                    if isinstance(load, GravityLoad):
                        material = model.materials.get(definition.material, {})
                        density = _finite_float_or_nan(material.get("density", material.get("rho", 0.0)))
                        if not np.isfinite(density) or density <= 0.0:
                            errors.append(
                                f"{path}: gravity requires positive density on element {element_index}."
                            )
                continue
            if isinstance(load, SurfaceLoad):
                if not _valid_element_index(load.element, len(model.elements)):
                    errors.append(f"{path}: surface load references invalid element {load.element!r}.")
                    continue
                definition = model.elements[load.element]
                if load.kind not in {"pressure", "surface_traction"}:
                    errors.append(f"{path}: unsupported surface load type {load.kind!r}.")
                if load.follower:
                    errors.append(f"{path}: follower loads require a future large-transformation formulation.")
                if load.coordinate_system not in {"global", "local"}:
                    errors.append(f"{path}: coordinate system must be 'global' or 'local'.")
                if load.kind == "pressure":
                    if not _is_finite_scalar(load.value):
                        errors.append(f"{path}: pressure must be a finite scalar.")
                elif not _is_finite_vector3(load.value):
                    errors.append(f"{path}: surface traction must contain three finite components.")
                if definition.type in {"TET4", "TET10"}:
                    if not isinstance(load.face, int) or isinstance(load.face, bool) or not 0 <= load.face <= 3:
                        errors.append(f"{path}: {definition.type} face must be an integer from 0 to 3.")
                elif definition.type in {"MITC3", "MITC4"}:
                    if load.face is not None and load.face != 0:
                        errors.append(f"{path}: {definition.type} face must be omitted or zero.")
                else:
                    errors.append(f"{path}: surface loads are unsupported for {definition.type}.")
                continue
            if isinstance(load, EdgeLoad):
                if not _valid_element_index(load.element, len(model.elements)):
                    errors.append(f"{path}: edge load references invalid element {load.element!r}.")
                    continue
                family = model.elements[load.element].type
                if family not in {"MITC3", "MITC4"}:
                    errors.append(f"{path}: edge traction is supported for shell elements only.")
                edge_max = 2 if family == "MITC3" else 3
                if not isinstance(load.edge, int) or isinstance(load.edge, bool) or not 0 <= load.edge <= edge_max:
                    errors.append(f"{path}: {family} edge must be an integer from 0 to {edge_max}.")
                if not _is_finite_vector3(load.value):
                    errors.append(f"{path}: edge traction must contain three finite components.")
                if load.coordinate_system not in {"global", "local"}:
                    errors.append(f"{path}: coordinate system must be 'global' or 'local'.")
                continue
            if isinstance(load, LineLoad):
                if not _valid_element_index(load.element, len(model.elements)):
                    errors.append(f"{path}: line load references invalid element {load.element!r}.")
                    continue
                if model.elements[load.element].type != "BEAM2":
                    errors.append(f"{path}: line_load is supported for BEAM2 only.")
                if not _is_finite_vector3(load.value):
                    errors.append(f"{path}: line load must contain three finite components.")
                if load.coordinate_system not in {"global", "local"}:
                    errors.append(f"{path}: coordinate system must be 'global' or 'local'.")
                continue
            errors.append(f"{path}: unsupported distributed load object {type(load).__name__}.")

    @staticmethod
    def _check_discrete_entities(model: FiniteElementModel, errors: list[str]) -> None:
        for index, spring in enumerate(model.springs):
            path = f"Spring {index}"
            if not 0 <= spring.node_a < model.node_count:
                errors.append(f"{path}: node_a is outside the model node range.")
                continue
            if spring.node_b is not None:
                if not 0 <= spring.node_b < model.node_count:
                    errors.append(f"{path}: node_b is outside the model node range.")
                    continue
                if spring.node_a == spring.node_b:
                    errors.append(f"{path}: node_b must differ from node_a.")
            if not spring.dofs or len(set(spring.dofs)) != len(spring.dofs):
                errors.append(f"{path}: dofs must be non-empty and unique.")
                continue
            try:
                spring.nodal_stiffness()
            except ValueError as exc:
                errors.append(f"{path}: {exc}")
        for index, mass in enumerate(model.concentrated_masses):
            path = f"Concentrated mass {index}"
            if not 0 <= mass.node < model.node_count:
                errors.append(f"{path}: node is outside the model node range.")
                continue
            try:
                mass.matrix()
            except ValueError as exc:
                errors.append(f"{path}: {exc}")

    @staticmethod
    def _check_conditions(model: FiniteElementModel, dofs: object, errors: list[str], warnings: list[str]) -> None:
        constrained = 0
        for condition in model.fixed_dofs:
            if condition.node < 0 or condition.node >= model.node_count:
                errors.append(f"Fixed condition references invalid node {condition.node}.")
                continue
            for dof in condition.dofs:
                name = normalize_dof_name(dof)
                if not dofs.has(condition.node, name):
                    errors.append(f"Fixed DOF {name} is not active on node {condition.node}.")
                constrained += 1
        for load in model.loads:
            if load.node < 0 or load.node >= model.node_count:
                errors.append(f"Load references invalid node {load.node}.")
                continue
            name = normalize_dof_name(load.dof)
            if not dofs.has(load.node, name):
                errors.append(f"Load DOF {name} is not active on node {load.node}.")
        if constrained < 3:
            warnings.append("Fewer than three constrained dofs; rigid body motion is likely.")

    @staticmethod
    def _check_component_constraints(
        model: FiniteElementModel,
        dofs: object,
        details: dict[str, Any],
        warnings: list[str],
    ) -> None:
        components = details.get("components", [])
        node_to_component = {
            int(node): int(component["index"])
            for component in components
            for node in component.get("nodes", [])
        }
        counts = {
            int(component["index"]): {
                "fixed_dof_count": 0,
                "fixed_translation_dof_count": 0,
                "fixed_translation_nodes": set(),
                "load_count": 0,
            }
            for component in components
        }
        for condition in model.fixed_dofs:
            component = node_to_component.get(int(condition.node))
            if component is None:
                continue
            for dof in condition.dofs:
                name = normalize_dof_name(dof)
                if dofs.has(condition.node, name):
                    counts[component]["fixed_dof_count"] += 1
                    if name in {"UX", "UY", "UZ"}:
                        counts[component]["fixed_translation_dof_count"] += 1
                        counts[component]["fixed_translation_nodes"].add(int(condition.node))
        for load in model.loads:
            component = node_to_component.get(int(load.node))
            if component is not None:
                counts[component]["load_count"] += 1
        for load_index, load in enumerate(model.distributed_loads):
            target_components: set[int] = set()
            for element_index in _distributed_element_indices(load, len(model.elements)):
                if not _valid_element_index(element_index, len(model.elements)):
                    continue
                definition = model.elements[element_index]
                if definition.nodes:
                    component = node_to_component.get(int(definition.nodes[0]))
                    if component is not None:
                        target_components.add(component)
            for component in target_components:
                counts[component]["load_count"] += 1
        for component in components:
            index = int(component["index"])
            counts[index]["fixed_translation_node_count"] = len(counts[index].pop("fixed_translation_nodes"))
            component.update(counts[index])
            types = set(component.get("element_types", {}))
            required = 6 if types.intersection({"MITC3", "MITC4", "BEAM2"}) else 3
            if counts[index]["fixed_dof_count"] == 0:
                warnings.append(f"Component {index} has no fixed dof; rigid body motion is likely.")
            elif counts[index]["fixed_translation_dof_count"] < 3:
                warnings.append(
                    f"Component {index} has fewer than three fixed translation dofs; rigid body motion is likely."
                )
            elif (
                "BEAM2" not in types
                and counts[index]["fixed_translation_node_count"] < 2
                and len(component.get("nodes", [])) > 1
            ):
                warnings.append(
                    f"Component {index} has translation constraints on fewer than two nodes; rotations may remain free."
                )
            if counts[index]["fixed_dof_count"] < required:
                warnings.append(f"Component {index} has {counts[index]['fixed_dof_count']} fixed dofs; expected at least {required}.")

    @staticmethod
    def _check_mechanical_rank(
        model: FiniteElementModel,
        dofs: object,
        details: dict[str, Any],
        warnings: list[str],
    ) -> None:
        if dofs.ndof > 180:
            details["mechanical_rank"] = {"checked": False, "reason": "model too large", "ndof": dofs.ndof}
            return
        try:
            from solveur.core.assembler import GlobalAssembler

            assembler = GlobalAssembler()
            stiffness = assembler.assemble_stiffness(model, dofs)
            fixed = assembler.fixed_indices(model, dofs)
            free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
            reduced = stiffness[free, :][:, free]
            dense = 0.5 * (reduced.toarray() + reduced.toarray().T)
            if dense.size == 0:
                details["mechanical_rank"] = {"checked": True, "free_dof_count": int(free.size), "rank": 0, "zero_mode_count": 0}
                return
            eigenvalues = np.linalg.eigvalsh(dense)
            scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
            tolerance = max(scale * 1.0e-10, 1.0e-12)
            zero_modes = int(np.count_nonzero(eigenvalues <= tolerance))
            details["mechanical_rank"] = {
                "checked": True,
                "free_dof_count": int(free.size),
                "rank": int(np.linalg.matrix_rank(dense, tol=tolerance)),
                "zero_mode_count": zero_modes,
                "eigenvalue_min": float(np.min(eigenvalues)),
                "eigenvalue_max": float(np.max(eigenvalues)),
                "tolerance": float(tolerance),
            }
            if zero_modes > 0:
                warnings.append(f"Reduced stiffness has {zero_modes} near-zero modes; constraints may be insufficient.")
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            details["mechanical_rank"] = {"checked": False, "reason": str(exc), "ndof": dofs.ndof}

    def _check_element_geometry(
        self,
        index: int,
        element_type: str,
        coords: np.ndarray,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        if element_type in {"TET4", "TET10"}:
            volume = MeshQuality.tet4_volume(coords)
            if volume <= self.thresholds.tet_min_signed_volume:
                errors.append(f"Element {index}: invalid {element_type} signed corner volume {volume:.6e}.")
                return
            if element_type == "TET10":
                minimum = float(np.min(Tet10Element.jacobian_determinants(coords)))
                if minimum <= self.thresholds.tet10_min_sampled_jacobian:
                    errors.append(
                        f"Element {index}: invalid TET10 sampled Jacobian {minimum:.6e}; "
                        "the curved mapping is inverted or degenerate."
                    )
        elif element_type == "MITC4":
            material = ShellMaterial(E=1.0, nu=0.3, t=1.0)
            element = MITC4Element(material)
            try:
                _, coords_2d = element.project_to_local_midplane(coords)
                element._check_jacobian(coords_2d)
            except ValueError as exc:
                errors.append(f"Element {index}: invalid MITC4 geometry: {exc}")
        elif element_type == "MITC3":
            material = ShellMaterial(E=1.0, nu=0.3, t=1.0)
            try:
                Mitc3ShellElement(material).project_to_local_midplane(coords)
            except ValueError as exc:
                errors.append(f"Element {index}: invalid MITC3 geometry: {exc}")
        elif element_type == "BEAM2":
            length = float(np.linalg.norm(coords[1] - coords[0]))
            if not np.isfinite(length) or length <= 1.0e-14:
                errors.append(f"Element {index}: invalid BEAM2 length {length:.6e}.")
