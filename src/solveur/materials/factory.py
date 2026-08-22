"""Material factory for JSON and API input."""

from __future__ import annotations

from typing import Any

from solveur.elements.shell.mitc4 import ShellMaterial

from solveur.materials.beam import BeamSectionMaterial
from solveur.materials.composite import OrthotropicLamina
from solveur.materials.failure import PlyStrainAllowables, PlyStrengths
from solveur.materials.laminate import ClassicalLaminate, LaminaPly, LaminateShellMaterial
from solveur.materials.orthotropic import (
    OrthotropicSolidMaterial,
    cylindrical_tangent_orientation,
    material_orientation,
)
from solveur.materials.solid import NonlinearSolidMaterial, SolidMaterial, VonMisesElastoplasticMaterial


class MaterialFactory:
    """Create concrete material objects from dictionaries."""

    @staticmethod
    def create(data: dict[str, Any], *, coordinates: object | None = None) -> object:
        material_type = str(data.get("type", "")).lower()
        if material_type == "beam_isotropic":
            if "G" in data:
                shear_modulus = float(data["G"])
            elif "nu" in data:
                shear_modulus = float(data["E"]) / (2.0 * (1.0 + float(data["nu"])))
            else:
                raise ValueError("beam_isotropic requires G or nu.")
            reference = data.get("reference_vector")
            return BeamSectionMaterial(
                E=float(data["E"]),
                G=shear_modulus,
                A=float(data["A"]),
                Iy=float(data["Iy"]),
                Iz=float(data["Iz"]),
                J=float(data["J"]),
                density=float(data.get("density", data.get("rho", 0.0))),
                kappa_y=float(data.get("kappa_y", 5.0 / 6.0)),
                kappa_z=float(data.get("kappa_z", 5.0 / 6.0)),
                reference_vector=tuple(float(value) for value in reference) if reference is not None else None,
            )
        if material_type == "isotropic_3d":
            return SolidMaterial(
                E=float(data["E"]),
                nu=float(data["nu"]),
                density=float(data.get("density", data.get("rho", 0.0))),
            )
        if material_type in {"orthotropic_3d", "composite_orthotropic_3d"}:
            if material_type == "composite_orthotropic_3d":
                if not isinstance(data.get("provenance"), dict) or not str(data.get("homogenization", "")):
                    raise ValueError(
                        "composite_orthotropic_3d requires provenance and a non-empty homogenization method."
                    )
            metadata_keys = ("provenance", "homogenization", "layup", "fiber_volume_fraction", "strengths")
            orientation_field = data.get("orientation_field")
            if orientation_field is not None:
                if not isinstance(orientation_field, dict):
                    raise ValueError("orientation_field must be an object.")
                if coordinates is None:
                    raise ValueError("orientation_field requires element coordinates.")
                orientation = cylindrical_tangent_orientation(coordinates, orientation_field)
            else:
                orientation = material_orientation(data.get("orientation"), data.get("e1"), data.get("e2_hint"))
            return OrthotropicSolidMaterial(
                E1=float(data["E1"]),
                E2=float(data["E2"]),
                E3=float(data["E3"]),
                nu12=float(data["nu12"]),
                nu13=float(data["nu13"]),
                nu23=float(data["nu23"]),
                G12=float(data["G12"]),
                G13=float(data["G13"]),
                G23=float(data["G23"]),
                density=float(data.get("density", data.get("rho", 0.0))),
                orientation=orientation,
                material_type=material_type,
                metadata={key: data[key] for key in metadata_keys if key in data},
            )
        if material_type == "nonlinear_isotropic_3d":
            return NonlinearSolidMaterial(
                E=float(data["E"]),
                nu=float(data["nu"]),
                density=float(data.get("density", data.get("rho", 0.0))),
                hardening=float(data.get("hardening", 0.0)),
            )
        if material_type == "von_mises_elastoplastic_3d":
            return VonMisesElastoplasticMaterial(
                E=float(data["E"]),
                nu=float(data["nu"]),
                density=float(data.get("density", data.get("rho", 0.0))),
                yield_stress=float(data["yield_stress"]),
                hardening_modulus=float(data.get("hardening_modulus", data.get("H", 0.0))),
            )
        if material_type == "shell_isotropic":
            return ShellMaterial(
                E=float(data["E"]),
                nu=float(data["nu"]),
                t=float(data["t"]),
                shear_factor=float(data.get("shear_factor", 5.0 / 6.0)),
                drilling_scale=float(data.get("drilling_scale", 1.0e-4)),
                density=float(data.get("density", data.get("rho", 0.0))),
            )
        if material_type == "orthotropic_lamina":
            return OrthotropicLamina(
                E1=float(data["E1"]),
                E2=float(data["E2"]),
                nu12=float(data["nu12"]),
                G12=float(data["G12"]),
                density=float(data.get("density", data.get("rho", 0.0))),
                G13=float(data["G13"]) if "G13" in data else None,
                G23=float(data["G23"]) if "G23" in data else None,
            )
        if material_type == "shell_laminate":
            plies = tuple(MaterialFactory._create_ply(item, index) for index, item in enumerate(data["plies"]))
            return LaminateShellMaterial(
                ClassicalLaminate(plies),
                shear_factor=float(data.get("shear_factor", 5.0 / 6.0)),
                drilling_scale=float(data.get("drilling_scale", 1.0e-4)),
                reference_direction=(
                    data.get("reference_direction") if data.get("reference_direction") is not None else None
                ),
            )
        raise ValueError(f"Unsupported material type {material_type!r}.")

    @staticmethod
    def _create_ply(data: dict[str, Any], index: int) -> LaminaPly:
        material = OrthotropicLamina(
            E1=float(data["E1"]),
            E2=float(data["E2"]),
            nu12=float(data["nu12"]),
            G12=float(data["G12"]),
            G13=float(data["G13"]),
            G23=float(data["G23"]),
            density=float(data.get("density", data.get("rho", 0.0))),
        )
        strengths_data = data.get("strengths")
        strain_data = data.get("strain_allowables")
        strengths = (
            PlyStrengths(
                Xt=float(strengths_data["Xt"]),
                Xc=float(strengths_data["Xc"]),
                Yt=float(strengths_data["Yt"]),
                Yc=float(strengths_data["Yc"]),
                S12=float(strengths_data["S12"]),
                f12_star=float(strengths_data.get("f12_star", -0.5)),
            )
            if isinstance(strengths_data, dict)
            else None
        )
        strain_allowables = (
            PlyStrainAllowables(
                e1t=float(strain_data["e1t"]),
                e1c=float(strain_data["e1c"]),
                e2t=float(strain_data["e2t"]),
                e2c=float(strain_data["e2c"]),
                g12=float(strain_data["g12"]),
            )
            if isinstance(strain_data, dict)
            else None
        )
        return LaminaPly(
            material=material,
            thickness=float(data["thickness"]),
            angle_deg=float(data.get("angle_deg", 0.0)),
            name=str(data.get("name", f"ply-{index + 1}")),
            strengths=strengths,
            strain_allowables=strain_allowables,
        )
