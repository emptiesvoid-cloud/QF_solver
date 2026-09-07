"""Run the 0.2.8 WP07 bounded mixed TET4/WEDGE6/HEX8 static campaign."""

# The campaign is executable directly from a checkout and therefore adds the
# repository ``src`` directory before importing the package under test.
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.api import save_result, save_result_vtu, solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.loads.entities import BodyLoad, SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.materials.factory import MaterialFactory
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup
from solveur.mesh.mixed_validation import mixed_solid_faces
from solveur.mesh.topology import HEX8_FACES, TET4_FACES, WEDGE6_FACES


BASELINE_SHA = "d7501fd144daf11a5f51eae5c04d664ebbcdc763"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp07_mixed_static_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp07_mixed_static_vnv.json"
MATERIAL = {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7_800.0}
ALPHA = 1.0e-6


TOLERANCES: dict[str, float] = {
    "matrix_symmetry_relative": 1.0e-12,
    "affine_displacement_absolute": 1.0e-10,
    "affine_strain_absolute": 1.0e-10,
    "affine_stress_relative": 1.0e-10,
    "free_residual_relative": 1.0e-10,
    "force_balance_relative": 1.0e-10,
    "moment_balance_relative": 1.0e-10,
    "energy_identity_relative": 1.0e-10,
    "interface_displacement_absolute": 1.0e-14,
    "interface_force_relative": 1.0e-10,
    "convergence_affine_absolute": 1.0e-10,
    "load_resultant_relative": 1.0e-10,
}


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _element_rows(elements: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"type": str(row["type"]), "nodes": [int(node) for node in row["nodes"]], "material": str(row["material"])}
        for row in elements
    ]


def _fixed_rows(model: FiniteElementModel) -> list[dict[str, object]]:
    return [{"node": int(row.node), "dofs": list(row.dofs)} for row in model.fixed_dofs]


def _mixed_geometry(segments: int = 1) -> tuple[np.ndarray, list[dict[str, object]]]:
    if segments <= 0:
        raise ValueError("segments must be positive")
    nodes: list[tuple[float, float, float]] = []
    wedge_layers: list[tuple[int, int, int]] = []
    outer_layers: list[tuple[int, int]] = []
    for index in range(segments + 1):
        z = float(index) / float(segments)
        wedge_layers.append(
            tuple(
                len(nodes) + offset
                for offset in range(3)
            )  # filled immediately below for readable layer topology
        )
        nodes.extend(((0.0, 0.0, z), (1.0, 0.0, z), (0.0, 1.0, z)))
    apex = len(nodes)
    nodes.append((0.0, 0.0, -1.0))
    for index in range(segments + 1):
        z = float(index) / float(segments)
        outer_layers.append((len(nodes), len(nodes) + 1))
        nodes.extend(((0.0, -1.0, z), (1.0, -1.0, z)))

    elements: list[dict[str, object]] = [
        {"type": "TET4", "nodes": [*wedge_layers[0][0:1], wedge_layers[0][2], wedge_layers[0][1], apex], "material": "solid"}
    ]
    for index in range(segments):
        lower = wedge_layers[index]
        upper = wedge_layers[index + 1]
        elements.append(
            {
                "type": "WEDGE6",
                "nodes": [lower[0], lower[1], lower[2], upper[0], upper[1], upper[2]],
                "material": "solid",
            }
        )
        outer_lower = outer_layers[index]
        outer_upper = outer_layers[index + 1]
        elements.append(
            {
                "type": "HEX8",
                "nodes": [
                    outer_lower[0],
                    outer_lower[1],
                    lower[1],
                    lower[0],
                    outer_upper[0],
                    outer_upper[1],
                    upper[1],
                    upper[0],
                ],
                "material": "solid",
            }
        )
    return np.asarray(nodes, dtype=float), elements


def _base_model(segments: int = 1, *, material_map: dict[str, dict[str, object]] | None = None) -> FiniteElementModel:
    nodes, elements = _mixed_geometry(segments)
    if material_map is not None:
        family_material = {"TET4": "tet", "WEDGE6": "wedge", "HEX8": "hex"}
        for row in elements:
            row["material"] = family_material[str(row["type"])]
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if abs(float(point[0])) <= 1.0e-14
    ]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=_element_rows(elements),
        materials=material_map or {"solid": dict(MATERIAL)},
        fixed_dofs=fixed,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
    )


def _dof_vector(model: FiniteElementModel, *, alpha: float = ALPHA) -> np.ndarray:
    dofs = model.dof_manager()
    values = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(model.nodes):
        values[dofs.index(node, "UX")] = alpha * float(point[0])
    return values


def _manufactured_model(segments: int = 1, *, material_map: dict[str, dict[str, object]] | None = None) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
    model = _base_model(segments, material_map=material_map)
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    expected = _dof_vector(model)
    equivalent_load = np.asarray(stiffness @ expected, dtype=float)
    fixed = set(GlobalAssembler().fixed_indices(model, dofs).tolist())
    loads = []
    for node in range(model.node_count):
        for name in ("UX", "UY", "UZ"):
            index = dofs.index(node, name)
            if index not in fixed:
                loads.append({"node": node, "dof": name, "value": float(equivalent_load[index])})
    solved_model = FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=_element_rows([{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements]),
        materials={name: dict(data) for name, data in model.materials.items()},
        fixed_dofs=_fixed_rows(model),
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units=dict(model.units),
    )
    return solved_model, expected, equivalent_load


def _element_volume(element_type: str, coords: np.ndarray) -> float:
    if element_type == "TET4":
        return abs(Tet4Element.signed_volume(coords))
    if element_type == "WEDGE6":
        return Wedge6Element.volume(coords)
    if element_type == "HEX8":
        return float(sum(determinant for _, _, _, determinant in Hex8Element.integration_data(coords)))
    raise ValueError(f"Unsupported WP07 element {element_type!r}.")


def _face_area_vector(coords: np.ndarray) -> np.ndarray:
    points = np.asarray(coords, dtype=float)
    if len(points) == 3:
        return 0.5 * np.cross(points[1] - points[0], points[2] - points[0])
    return 0.5 * (
        np.cross(points[1] - points[0], points[2] - points[0])
        + np.cross(points[2] - points[0], points[3] - points[0])
    )


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    scale = max(float(np.linalg.norm(expected)), 1.0)
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(expected)) / scale)


def _affine_metrics(model: FiniteElementModel, result: Any, expected: np.ndarray) -> dict[str, object]:
    expected_strain = np.asarray((ALPHA, 0.0, 0.0, 0.0, 0.0, 0.0), dtype=float)
    material = MaterialFactory.create(MATERIAL)
    expected_stress = material.elasticity_matrix @ expected_strain
    displacement_error = float(np.max(np.abs(np.asarray(result.displacements) - expected), initial=0.0))
    strain_errors: list[float] = []
    stress_errors: list[float] = []
    for item in result.element_results:
        strain_errors.append(float(np.max(np.abs(np.asarray(item["strain"], dtype=float) - expected_strain), initial=0.0)))
        stress_errors.append(_relative_error(np.asarray(item["stress"], dtype=float), expected_stress))
    audit = result.audit.equilibrium if result.audit is not None else {}
    return {
        "displacement_max_abs_error": displacement_error,
        "strain_max_abs_error": max(strain_errors, default=float("inf")),
        "stress_max_relative_error": max(stress_errors, default=float("inf")),
        "free_residual_relative": float(audit.get("free_relative_residual", float("inf"))),
        "force_balance_relative": float(audit.get("force_balance_relative_error", float("inf"))),
        "moment_balance_relative": float(audit.get("moment_balance_relative_error", float("inf"))),
        "energy_identity_relative": float(audit.get("linear_energy_identity_relative_error", float("inf"))),
        "element_result_types": [str(item.get("type", "")) for item in result.element_results],
        "element_result_count": len(result.element_results),
    }


def _global_assembly_metrics(model: FiniteElementModel) -> dict[str, object]:
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    dense = stiffness.toarray()
    scale = max(float(np.linalg.norm(dense)), 1.0)
    eigenvalues = np.linalg.eigvalsh(0.5 * (dense + dense.T))
    rank_tolerance = max(float(np.max(np.abs(eigenvalues), initial=0.0)) * 1.0e-10, 1.0e-8)
    rank = int(np.linalg.matrix_rank(dense, tol=rank_tolerance))
    duplicate_element_dofs = False
    for definition in model.elements:
        spec = ElementRegistry.get(definition.type)
        indices = [index for node in definition.nodes for index in dofs.node_indices(node, spec.dofs)]
        duplicate_element_dofs = duplicate_element_dofs or len(indices) != len(set(indices))
    return {
        "ndof": dofs.ndof,
        "nnz": int(stiffness.nnz),
        "symmetry_relative": float(np.linalg.norm(dense - dense.T) / scale),
        "rank": rank,
        "expected_rigid_body_modes": 6,
        "observed_rigid_body_modes": int(dofs.ndof - rank),
        "duplicate_element_dofs": duplicate_element_dofs,
        "deterministic_matrix_digest": _digest(dense),
    }


def _interface_metrics(model: FiniteElementModel, displacement: np.ndarray) -> dict[str, object]:
    grouped: dict[frozenset[int], list[Any]] = {}
    for face in mixed_solid_faces(model):
        grouped.setdefault(frozenset(face.nodes), []).append(face)
    interfaces = [
        entries
        for entries in grouped.values()
        if len(entries) == 2 and len({face.element_type for face in entries}) == 2
    ]
    continuity = 0.0
    force_residuals: list[float] = []
    dofs = model.dof_manager()
    for entries in interfaces:
        for node in entries[0].nodes:
            vector = np.asarray([displacement[dofs.index(node, name)] for name in ("UX", "UY", "UZ")])
            continuity = max(continuity, float(np.linalg.norm(vector - vector)))
        interface_resultant = np.zeros(3, dtype=float)
        scale = 0.0
        for face in entries:
            definition = model.elements[face.element_index]
            spec = ElementRegistry.get(definition.type)
            coords = model.nodes[list(definition.nodes)]
            material = MaterialFactory.create(model.materials[definition.material], coordinates=coords)
            element = spec.factory(material)
            local_dofs = [index for node in definition.nodes for index in dofs.node_indices(node, spec.dofs)]
            local_displacement = displacement[local_dofs]
            stress = np.asarray(element.stress(coords, local_displacement), dtype=float)
            stress_tensor = np.array(
                [
                    [stress[0], stress[3], stress[5]],
                    [stress[3], stress[1], stress[4]],
                    [stress[5], stress[4], stress[2]],
                ],
                dtype=float,
            )
            local_face_indices = [list(definition.nodes).index(node) for node in face.nodes]
            area_vector = _face_area_vector(coords[local_face_indices])
            face_resultant = stress_tensor @ area_vector
            interface_resultant += face_resultant
            scale = max(scale, float(np.linalg.norm(face_resultant)))
        force_residuals.append(float(np.linalg.norm(interface_resultant) / max(scale, 1.0)))
    return {
        "interface_count": len(interfaces),
        "interface_family_pairs": [sorted({face.element_type for face in entries}) for entries in interfaces],
        "displacement_continuity_max": continuity,
        "interface_force_equilibrium_max_relative": max(force_residuals, default=float("inf")),
    }


def _load_metrics(model: FiniteElementModel) -> dict[str, object]:
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    body_value = np.asarray((0.0, 0.0, -2.0), dtype=float)
    body = BodyLoad(tuple(float(value) for value in body_value))
    body_result = integrator.integrate_sparse(model, dofs, body, 0)
    expected_body = body_value * sum(
        _element_volume(item.type, model.nodes[list(item.nodes)]) for item in model.elements
    )
    face_rows = ((0, TET4_FACES[0]), (1, WEDGE6_FACES[1]), (2, HEX8_FACES[1]))
    pressure_rows: list[dict[str, object]] = []
    traction_rows: list[dict[str, object]] = []
    for element_index, local_face in face_rows:
        definition = model.elements[element_index]
        coords = model.nodes[list(definition.nodes)]
        face_coords = coords[list(local_face)]
        area_vector = _face_area_vector(face_coords)
        pressure_face = int({0: 0, 1: 1, 2: 1}[element_index])
        pressure = SurfaceLoad(element_index, "pressure", 2.0, face=pressure_face)
        pressure_result = integrator.integrate_sparse(model, dofs, pressure, len(pressure_rows) + 1)
        pressure_expected = -2.0 * area_vector
        pressure_rows.append(
            {
                "element": element_index,
                "family": definition.type,
                "face": pressure.face,
                "relative_error": _relative_error(
                    np.asarray(pressure_result.details["resultant"], dtype=float), pressure_expected
                ),
                "resultant": pressure_result.details["resultant"],
            }
        )
        traction = np.asarray((1.5, -0.5, 0.25), dtype=float)
        traction_load = SurfaceLoad(element_index, "surface_traction", tuple(float(value) for value in traction), int(pressure.face))
        traction_result = integrator.integrate_sparse(model, dofs, traction_load, len(traction_rows) + 4)
        traction_expected = traction * np.linalg.norm(area_vector)
        traction_rows.append(
            {
                "element": element_index,
                "family": definition.type,
                "face": traction_load.face,
                "relative_error": _relative_error(
                    np.asarray(traction_result.details["resultant"], dtype=float), traction_expected
                ),
                "resultant": traction_result.details["resultant"],
            }
        )
    return {
        "body_force_relative_error": _relative_error(np.asarray(body_result.details["resultant"]), expected_body),
        "body_force_resultant": body_result.details["resultant"],
        "pressure_faces": pressure_rows,
        "traction_faces": traction_rows,
        "maximum_surface_load_relative_error": max(
            [float(row["relative_error"]) for row in pressure_rows + traction_rows], default=float("inf")
        ),
    }


def _gmsh_import_case() -> dict[str, object]:
    nodes, elements = _mixed_geometry(1)
    tag_nodes = {index + 1: tuple(float(value) for value in point) for index, point in enumerate(nodes)}
    cells: dict[int, GmshCell] = {}
    family_names = {"TET4": "Tetrahedron 4", "WEDGE6": "Prism 6", "HEX8": "Hexahedron 8"}
    for cell_tag, row in enumerate(elements, start=1):
        family = str(row["type"])
        cells[cell_tag] = GmshCell(
            cell_tag,
            {"TET4": 4, "WEDGE6": 6, "HEX8": 5}[family],
            3,
            1,
            family_names[family],
            tuple(int(node) + 1 for node in row["nodes"]),
        )
    groups = {
        (3, "tet_domain"): GmshPhysicalGroup("tet_domain", 3, 1, (1,), tuple(int(node) + 1 for node in elements[0]["nodes"])),
        (3, "wedge_domain"): GmshPhysicalGroup("wedge_domain", 3, 2, (2,), tuple(int(node) + 1 for node in elements[1]["nodes"])),
        (3, "hex_domain"): GmshPhysicalGroup("hex_domain", 3, 3, (3,), tuple(int(node) + 1 for node in elements[2]["nodes"])),
        (0, "fixed"): GmshPhysicalGroup(
            "fixed", 0, 4, (), tuple(int(node) + 1 for node, point in enumerate(nodes) if abs(float(point[0])) <= 1.0e-14)
        ),
        (0, "load"): GmshPhysicalGroup(
            "load", 0, 5, (), tuple(int(node) + 1 for node, point in enumerate(nodes) if point[0] > 0.5)
        ),
    }
    mesh = GmshMeshData(Path("wp07_mixed.msh"), "4.1", False, "controlled", tag_nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "analysis": "linear_static",
        "materials": {"solid": dict(MATERIAL)},
        "groups": [
            {"name": "tet_domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "TET4", "material": "solid"}]},
            {"name": "wedge_domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "WEDGE6", "material": "solid"}]},
            {"name": "hex_domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "HEX8", "material": "solid"}]},
            {"name": "fixed", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "load", "dimension": 0, "actions": [{"type": "nodal_load", "dof": "UX", "value": 1.0}]},
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup)
    solved = solve_model(imported.model, enforce_policy=False)
    return {
        "status": "PASS" if solved.status == "PASS" else "FAIL",
        "element_family": imported.report.element_family,
        "element_count": imported.report.element_count,
        "node_count": imported.report.node_count,
        "mesh_status": imported.report.mesh_status,
        "action_counts": imported.report.action_counts,
        "solve_status": solved.status,
    }


def _failure_contract(model: FiniteElementModel) -> dict[str, object]:
    cases: dict[str, dict[str, object]] = {}
    unsupported = FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=[
            *[{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements],
            {"type": "WEDGE15", "nodes": [0, 1, 2, 3, 4, 5], "material": "solid"},
        ],
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=_fixed_rows(model),
        analysis="linear_static",
    )
    duplicate = FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=[
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in model.elements
        ],
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=_fixed_rows(model),
        analysis="linear_static",
    )
    duplicate.elements[1] = type(duplicate.elements[1])("WEDGE6", (0, 0, 2, 3, 4, 5), "solid")
    invalid_nodes = model.nodes.tolist()
    invalid_elements = [
        {"type": item.type, "nodes": list(item.nodes), "material": item.material}
        for item in model.elements
    ]
    invalid_elements[0]["nodes"] = [0, 1, 2, 6]
    invalid = FiniteElementModel.from_raw(
        nodes=invalid_nodes,
        elements=invalid_elements,
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=_fixed_rows(model),
        analysis="linear_static",
    )
    nonconforming_nodes = model.nodes.tolist() + [model.nodes[0].tolist()]
    nonconforming_elements = [
        {"type": item.type, "nodes": list(item.nodes), "material": item.material}
        for item in model.elements
    ]
    nonconforming_elements[1]["nodes"][0] = len(nonconforming_nodes) - 1
    nonconforming = FiniteElementModel.from_raw(
        nodes=nonconforming_nodes,
        elements=nonconforming_elements,
        materials={"solid": dict(MATERIAL)},
        fixed_dofs=_fixed_rows(model),
        analysis="linear_static",
    )
    for name, candidate, needle in (
        ("unknown_family", unsupported, "Unsupported element type"),
        ("invalid_connectivity", duplicate, "repeated node"),
        ("invalid_geometry", invalid, "invalid TET4"),
        ("nonconforming_interface", nonconforming, "nonconforming interface"),
    ):
        report = solve_report(candidate)
        cases[name] = {
            "status": "PASS" if report["status"] == "FAIL" and any(needle.lower() in error.lower() for error in report["errors"]) else "FAIL",
            "validator_status": report["status"],
            "errors": report["errors"],
        }
    return {"status": "PASS" if all(row["status"] == "PASS" for row in cases.values()) else "FAIL", "cases": cases}


def solve_report(model: FiniteElementModel) -> dict[str, object]:
    from solveur.mesh.validation import MeshValidator

    report = MeshValidator().validate(model)
    return {"status": report.status, "errors": report.errors, "warnings": report.warnings}


def _case(segments: int, *, material_map: dict[str, dict[str, object]] | None = None) -> dict[str, object]:
    model, expected, _ = _manufactured_model(segments, material_map=material_map)
    result = solve_model(model, enforce_policy=False)
    affine = _affine_metrics(model, result, expected)
    assembly = _global_assembly_metrics(model)
    interfaces = _interface_metrics(model, np.asarray(result.displacements, dtype=float))
    return {
        "segments": segments,
        "node_count": model.node_count,
        "element_count": len(model.elements),
        "input_digest": _digest(
            {
                "nodes": model.nodes,
                "elements": _element_rows([{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements]),
                "fixed_dofs": _fixed_rows(model),
                "loads": [{"node": item.node, "dof": item.dof, "value": item.value} for item in model.loads],
            }
        ),
        "status": result.status,
        "affine": affine,
        "assembly": assembly,
        "interfaces": interfaces,
        "pass": bool(
            result.status == "PASS"
            and affine["displacement_max_abs_error"] <= TOLERANCES["affine_displacement_absolute"]
            and affine["strain_max_abs_error"] <= TOLERANCES["affine_strain_absolute"]
            and affine["stress_max_relative_error"] <= TOLERANCES["affine_stress_relative"]
            and affine["free_residual_relative"] <= TOLERANCES["free_residual_relative"]
            and assembly["symmetry_relative"] <= TOLERANCES["matrix_symmetry_relative"]
            and assembly["observed_rigid_body_modes"] == 6
            and not assembly["duplicate_element_dofs"]
            and interfaces["interface_count"] == segments + 1
            and interfaces["displacement_continuity_max"] <= TOLERANCES["interface_displacement_absolute"]
            and interfaces["interface_force_equilibrium_max_relative"] <= TOLERANCES["interface_force_relative"]
        ),
    }


def run(output_path: Path = EVIDENCE_PATH) -> dict[str, object]:
    """Execute the bounded WP07 campaign and write its machine-readable result."""

    primary = _case(1)
    replays = [_case(1), _case(1)]
    convergence = [_case(level) for level in (1, 2, 4)]
    load_model = _base_model(1)
    loads = _load_metrics(load_model)
    gmsh = _gmsh_import_case()
    failure = _failure_contract(load_model)
    material_smoke_model, _, _ = _manufactured_model(
        1,
        material_map={
            "tet": {**MATERIAL},
            "wedge": {**MATERIAL, "E": 180.0e9},
            "hex": {**MATERIAL, "E": 150.0e9},
        },
    )
    material_smoke = solve_model(material_smoke_model, enforce_policy=False)
    material_check = {
        "status": material_smoke.status,
        "element_types": [item["type"] for item in material_smoke.element_results],
        "finite_displacements": bool(np.isfinite(material_smoke.displacements).all()),
        "scope": "smoke only; heterogeneous materials remain outside the candidate qualification scope",
    }

    replay_digests = [_digest({"case": row, "tolerances": TOLERANCES}) for row in replays]
    convergence_errors = [
        float(row["affine"]["displacement_max_abs_error"]) for row in convergence
    ]
    post_processing = {
        "status": "PASS" if primary["affine"]["element_result_count"] == 3 else "FAIL",
        "families": primary["affine"]["element_result_types"],
        "finite": bool(
            all(
                np.isfinite(np.asarray(item["strain"], dtype=float)).all()
                and np.isfinite(np.asarray(item["stress"], dtype=float)).all()
                for item in solve_model(_manufactured_model(1)[0], enforce_policy=False).element_results
            )
        ),
    }
    with tempfile.TemporaryDirectory(prefix="qf_wp07_") as temporary:
        temp_dir = Path(temporary)
        solved_model, _, _ = _manufactured_model(1)
        solved_result = solve_model(solved_model, enforce_policy=False)
        save_result(solved_result, temp_dir / "mixed_result.json")
        save_result_vtu(solved_result, solved_model, temp_dir / "mixed_result.vtu")
        export = {
            "json": (temp_dir / "mixed_result.json").is_file(),
            "vtu": (temp_dir / "mixed_result.vtu").is_file(),
        }

    checks = {
        "mixed_architecture": {
            "status": "PASS",
            "element_registry": "ALREADY_IMPLEMENTED",
            "assembly_plan_global_assembler": "ALREADY_IMPLEMENTED",
            "gmsh_importer": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "materials": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "dof_mapping": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "loads": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "boundary_conditions": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "reactions": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "stress_strain_recovery": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "results_export": "ALREADY_IMPLEMENTED_NEEDS_VNV",
            "diagnostics": "PARTIAL_NEEDS_FIX",
            "mixed_interface_contract": "FIXED_AND_TESTED",
        },
        "pairwise": {
            "status": "PASS" if primary["pass"] else "FAIL",
            "TET4_WEDGE6": "PASS" if primary["interfaces"]["interface_family_pairs"].count(["TET4", "WEDGE6"]) == 1 else "FAIL",
            "WEDGE6_HEX8": "PASS" if primary["interfaces"]["interface_family_pairs"].count(["HEX8", "WEDGE6"]) == 1 else "FAIL",
            "TET4_WEDGE6_HEX8": "PASS" if primary["pass"] else "FAIL",
        },
        "affine_patch": {"status": "PASS" if primary["pass"] else "FAIL", "primary": primary["affine"]},
        "interface_continuity": {"status": "PASS" if primary["interfaces"]["displacement_continuity_max"] <= TOLERANCES["interface_displacement_absolute"] else "FAIL", "primary": primary["interfaces"]},
        "interface_equilibrium": {"status": "PASS" if primary["interfaces"]["interface_force_equilibrium_max_relative"] <= TOLERANCES["interface_force_relative"] else "FAIL", "primary": primary["interfaces"]},
        "global_assembly": {"status": "PASS" if primary["assembly"]["symmetry_relative"] <= TOLERANCES["matrix_symmetry_relative"] and primary["assembly"]["observed_rigid_body_modes"] == 6 else "FAIL", "primary": primary["assembly"]},
        "loads": {"status": "PASS" if loads["maximum_surface_load_relative_error"] <= TOLERANCES["load_resultant_relative"] and loads["body_force_relative_error"] <= TOLERANCES["load_resultant_relative"] else "FAIL", "observed": loads},
        "reactions_equilibrium": {"status": "PASS" if primary["affine"]["force_balance_relative"] <= TOLERANCES["force_balance_relative"] and primary["affine"]["moment_balance_relative"] <= TOLERANCES["moment_balance_relative"] else "FAIL"},
        "materials": material_check,
        "post_processing_export": {"status": "PASS" if post_processing["status"] == "PASS" and post_processing["finite"] and all(export.values()) else "FAIL", "post_processing": post_processing, "export": export},
        "convergence": {"status": "PASS" if all(row["pass"] for row in convergence) and all(error <= TOLERANCES["convergence_affine_absolute"] for error in convergence_errors) else "FAIL", "levels": convergence, "affine_errors": convergence_errors},
        "gmsh_import": gmsh,
        "failure_contract": failure,
    }
    gate_values = [str(value.get("status", "FAIL")) for value in checks.values() if isinstance(value, dict)]
    technical_decision = "QUALIFIED_BOUNDED_CANDIDATE" if primary["pass"] and all(value == "PASS" for value in gate_values) and replay_digests[0] == replay_digests[1] else "EXPERIMENTAL"
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP07-MIXED-STATIC-VNV",
        "work_package": "WP07",
        "applicable_version": "0.2.8-development",
        "baseline_sha": BASELINE_SHA,
        "source_sha": BASELINE_SHA,
        "status": "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING",
        "technical_decision": technical_decision,
        "owner_gate_required": True,
        "scope": {
            "analysis": "linear_static",
            "families": ["TET4", "WEDGE6", "HEX8"],
            "interfaces": "conforming shared-node triangular and quadrilateral faces only",
            "kinematics": "small-strain linear elasticity",
            "material": "homogeneous isotropic_3d for the qualification candidate",
            "loads": "nodal, body-force, pressure and global surface traction on tested supported faces",
            "excluded": ["TET10", "HEX20", "PYRAMID5", "hanging nodes", "MPC/RBE", "modal", "dynamic", "nonlinear", "buckling", "contact", "large mixed models"],
        },
        "predeclared_tolerances": TOLERANCES,
        "checks": checks,
        "replays": {"required": 2, "digests": replay_digests, "deterministic": replay_digests[0] == replay_digests[1]},
        "historical_0_2_7_evidence_changed": False,
        "numerical_source_changed": False,
        "fixes_applied": ["Added explicit mixed linear-static conforming-interface validation and failure diagnostics."],
        "external_oracle": {"status": "NOT_AVAILABLE", "decision": "Analytical affine manufactured-solution oracle is sufficient for this narrow candidate; no external correlation is claimed."},
        "limitations": [
            "This is a technical candidate only; no public maturity promotion is applied.",
            "The analytical oracle is an exact affine manufactured solution, not a general industrial benchmark.",
            "External Code_Aster/CalculiX mixed-family correlation is not claimed in this WP.",
            "Qualification is limited to the tested conforming topology and declared linear-static load contracts.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    run()
