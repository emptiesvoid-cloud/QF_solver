"""Material policy shared by large-scale TET4 backends."""

from __future__ import annotations

from typing import Any

from solveur.materials.factory import MaterialFactory
from solveur.materials.solid import SolidConstitutiveMaterial

SUPPORTED_LARGE_MATERIAL_TYPES = frozenset({"isotropic_3d", "orthotropic_3d", "composite_orthotropic_3d"})


def create_large_material(data: dict[str, Any]) -> SolidConstitutiveMaterial:
    """Create a linear solid material accepted by the large-scale TET4 scope."""
    material_type = str(data.get("type", "")).lower()
    if material_type not in SUPPORTED_LARGE_MATERIAL_TYPES:
        supported = ", ".join(sorted(SUPPORTED_LARGE_MATERIAL_TYPES))
        raise ValueError(f"Large-scale TET4 supports linear materials {supported}; got {material_type!r}.")
    if "orientation_field" in data:
        raise ValueError(
            "Large-scale TET4 does not yet support orientation_field; use a constant orientation or the standard solver."
        )
    material = MaterialFactory.create(data)
    if not isinstance(material, SolidConstitutiveMaterial):
        raise TypeError(f"Material {material_type!r} does not implement the solid constitutive interface.")
    return material
