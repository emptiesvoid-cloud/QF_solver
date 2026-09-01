"""Technical element descriptors used by the compatibility preflight."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementCapabilityDescriptor:
    """Describe technical routes without duplicating qualification maturity."""

    canonical_name: str
    aliases: tuple[str, ...]
    dimension: int
    node_count: int
    dofs: tuple[str, ...]
    topology: str
    face_topology: tuple[str, ...]
    integration_family: str
    supported_material_families: tuple[str, ...]
    supported_analyses: tuple[str, ...]
    supported_load_categories: tuple[str, ...]
    mass_availability: str
    stress_result_recovery: str
    gmsh_mapping: str
    backend_restrictions: tuple[str, ...]
    route_restrictions: tuple[str, ...]
    registry_capability_refs: tuple[str, ...]


_SOLID_MATERIALS = (
    "isotropic_3d",
    "orthotropic_3d",
    "composite_orthotropic_3d",
    "nonlinear_isotropic_3d",
    "von_mises_elastoplastic_3d",
    "finite_kinematic_j2",
)
_SOLID_ANALYSES = (
    "linear_static",
    "modal",
    "transient_dynamic",
    "harmonic_response",
    "linear_buckling",
    "nonlinear_static",
    "geometric_nonlinear_static",
)
_SOLID_LOADS = (
    "nodal",
    "gravity",
    "body_force",
    "pressure",
    "surface_traction",
    "frictionless_contact",
)


DESCRIPTORS: dict[str, ElementCapabilityDescriptor] = {
    "BEAM2": ElementCapabilityDescriptor(
        "BEAM2", ("BEAM2", "BEAM"), 3, 2, ("UX", "UY", "UZ", "RX", "RY", "RZ"),
        "line", ("POINT",), "Timoshenko 2-node", ("beam_isotropic",),
        ("linear_static", "modal", "transient_dynamic", "harmonic_response"),
        ("nodal", "gravity", "body_force", "line_load"), "consistent", "beam resultants",
        "Gmsh line2", ("scipy_sparse",), ("nonlinear routes are not declared"), ("ELE-BEAM2",),
    ),
    "MITC3": ElementCapabilityDescriptor(
        "MITC3", ("MITC3", "MITC3+"), 3, 3, ("UX", "UY", "UZ", "RX", "RY", "RZ"),
        "triangle", ("LINE2",), "MITC3 assumed strain", ("shell_isotropic", "shell_laminate", "orthotropic_lamina"),
        ("linear_static", "modal", "transient_dynamic", "harmonic_response"),
        ("nodal", "gravity", "body_force", "pressure", "surface_traction", "edge_traction"),
        "consistent", "shell stress/resultants", "Gmsh triangle3", ("scipy_sparse",),
        ("nonlinear routes are not declared",), ("ELE-MITC3",),
    ),
    "MITC4": ElementCapabilityDescriptor(
        "MITC4", ("MITC4",), 3, 4, ("UX", "UY", "UZ", "RX", "RY", "RZ"),
        "quadrilateral", ("LINE2",), "MITC4 assumed strain", ("shell_isotropic", "shell_laminate", "orthotropic_lamina"),
        ("linear_static", "modal", "transient_dynamic", "harmonic_response"),
        ("nodal", "gravity", "body_force", "pressure", "surface_traction", "edge_traction"),
        "consistent", "shell stress/resultants", "Gmsh quadrilateral4", ("scipy_sparse",),
        ("nonlinear routes are not declared",), ("ELE-MITC4",),
    ),
    "TET4": ElementCapabilityDescriptor(
        "TET4", ("TET4", "TETRA4"), 3, 4, ("UX", "UY", "UZ"), "tetrahedron",
        ("TRI3",), "constant-strain tetrahedron", _SOLID_MATERIALS, _SOLID_ANALYSES, _SOLID_LOADS,
        "consistent", "Gauss-point stress", "Gmsh tetra4", ("scipy_sparse",),
        ("finite_kinematic_j2 is not qualified",), ("ELE-TET4",),
    ),
    "TET10": ElementCapabilityDescriptor(
        "TET10", ("TET10", "TETRA10"), 3, 10, ("UX", "UY", "UZ"), "tetrahedron",
        ("TRI6",), "quadratic tetrahedron", _SOLID_MATERIALS, _SOLID_ANALYSES, _SOLID_LOADS,
        "consistent", "Gauss-point stress", "Gmsh tetra10", ("scipy_sparse",),
        ("finite_kinematic_j2 is not qualified",), ("ELE-TET10",),
    ),
    "HEX8": ElementCapabilityDescriptor(
        "HEX8", ("HEX8", "HEXA8"), 3, 8, ("UX", "UY", "UZ"), "hexahedron",
        ("QUAD4",), "trilinear hexahedron, full integration", _SOLID_MATERIALS, _SOLID_ANALYSES, _SOLID_LOADS,
        "consistent", "Gauss-point stress", "Gmsh hexahedron8", ("scipy_sparse",),
        ("finite_kinematic_j2 is not qualified",), ("ELE-HEX8",),
    ),
    "HEX20": ElementCapabilityDescriptor(
        "HEX20", ("HEX20", "HEXA20"), 3, 20, ("UX", "UY", "UZ"), "hexahedron",
        ("QUAD8",), "quadratic hexahedron", _SOLID_MATERIALS, _SOLID_ANALYSES, _SOLID_LOADS,
        "consistent", "Gauss-point stress", "Gmsh hexahedron20", ("scipy_sparse",),
        ("finite_kinematic_j2 is not qualified",), ("ELE-HEX20",),
    ),
    "WEDGE6": ElementCapabilityDescriptor(
        "WEDGE6", ("WEDGE6", "PRISM6"), 3, 6, ("UX", "UY", "UZ"), "linear triangular prism",
        ("TRI3", "TRI3", "QUAD4", "QUAD4", "QUAD4"), "TRI3_X_GAUSS2",
        ("isotropic_3d",), ("linear_static", "modal"), ("nodal", "gravity", "body_force", "pressure", "surface_traction"), "consistent",
        "Gauss-point strain/stress recovery with integration energy",
        "Gmsh Prism6 import and canonical face/load mapping validated by WP08",
        ("scipy_sparse",),
        (
            "Newmark/harmonic routes are not implemented",
            "J2, TL, contact, external correlation and robustness qualification are deferred",
        ),
        ("COMB-WEDGE6-linear_static", "COMB-WEDGE6-modal"),
    ),
    "DISCRETE": ElementCapabilityDescriptor(
        "DISCRETE", ("DISCRETE", "SPRING", "MASS"), 0, 0, (), "discrete entity", (),
        "entity-level spring/mass", ("discrete_linear",),
        ("linear_static", "modal", "transient_dynamic", "harmonic_response"),
        ("nodal", "frictionless_contact"), "entity-specific", "entity-specific", "none", ("scipy_sparse",),
        ("element definitions are not used for discrete entities",), ("ELE-DISCRETE",),
    ),
}

_ALIASES = {alias: name for name, descriptor in DESCRIPTORS.items() for alias in descriptor.aliases}


def normalize_element_name(name: str) -> str:
    """Return a canonical family name or raise a deterministic error."""

    key = str(name).strip().upper()
    if key not in _ALIASES:
        raise KeyError(f"Unknown element family {name!r}.")
    return _ALIASES[key]


def get_element_descriptor(name: str) -> ElementCapabilityDescriptor:
    """Return a technical descriptor by canonical name or alias."""

    return DESCRIPTORS[normalize_element_name(name)]


def get_supported_analyses(name: str) -> tuple[str, ...]:
    return get_element_descriptor(name).supported_analyses


def get_supported_loads(name: str) -> tuple[str, ...]:
    return get_element_descriptor(name).supported_load_categories
