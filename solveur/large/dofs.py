"""Direct degree-of-freedom indexing for large TET4 models."""

from __future__ import annotations

DOF_NAMES = ("UX", "UY", "UZ")
DOF_TO_COMPONENT = {name: index for index, name in enumerate(DOF_NAMES)}


def component_from_dof(value: str | int) -> int:
    """Return component index 0..2 for a TET4 translation dof."""
    if isinstance(value, int):
        component = int(value)
    else:
        key = str(value).upper()
        if key not in DOF_TO_COMPONENT:
            raise ValueError(f"Large TET4 model supports only UX, UY, UZ; got {value!r}.")
        component = DOF_TO_COMPONENT[key]
    if component < 0 or component > 2:
        raise ValueError(f"Large TET4 component must be in [0, 2]; got {component}.")
    return component


def dof_index(node: object, component: object) -> object:
    """Return compact global dof index for homogeneous TET4 translation dofs."""
    return 3 * node + component
