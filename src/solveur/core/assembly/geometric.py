"""Factories for the shared bounded Total-Lagrangian solid assemblies."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.model import FiniteElementModel
from solveur.core.assembly.sparse import SparseCsrAccumulator
from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Tet10Element,
)
from solveur.materials.solid import SolidMaterial


class TotalLagrangianHighOrderAssembly:
    """Sparse elastic TL assembly backed by the common high-order kernel.

    The kernel is constitutive-law agnostic at runtime and accepts the linear
    ``SolidMaterial`` response.  It is shared by geometric static and bounded
    buckling analyses; it does not introduce a second nonlinear driver.
    """

    _element_classes = {
        "TET10": TotalLagrangianJ2Tet10Element,
        "HEX20": TotalLagrangianJ2Hex20Element,
    }

    def __init__(
        self,
        model: FiniteElementModel,
        material: SolidMaterial,
    ) -> None:
        self.nodes = np.asarray(model.nodes, dtype=float)
        self.elements = np.asarray([element.nodes for element in model.elements], dtype=int)
        self.material = material
        self.element_type = model.elements[0].type
        if self.element_type not in self._element_classes:
            raise ValueError(f"Unsupported high-order Total-Lagrangian family {self.element_type!r}.")
        if self.elements.ndim != 2 or self.elements.shape[0] == 0:
            raise ValueError("High-order Total-Lagrangian assembly requires non-empty connectivity.")
        self.element_dofs = (3 * self.elements[:, :, None] + np.arange(3)).reshape(
            self.elements.shape[0], -1
        )
        chunk_size = model.analysis.parameters.get("nonlinear_assembly_chunk_size", 256)
        if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
            raise ValueError("nonlinear_assembly_chunk_size must be a positive integer.")
        self._assembly_chunk_size = int(chunk_size)
        self._last_assembly_metrics: dict[str, int] = {
            "sparse_chunk_count": 0,
            "sparse_peak_chunk_entries": 0,
            "sparse_peak_chunk_bytes_estimate": 0,
            "sparse_accumulator_levels": 0,
        }
        quadrature = str(model.analysis.parameters.get("tet10_nonlinear_quadrature", "hammer4"))
        element_class = self._element_classes[self.element_type]
        self._kernels = tuple(
            element_class(material, nonlinear_quadrature=quadrature)
            if self.element_type == "TET10"
            else element_class(material)
            for _ in range(self.elements.shape[0])
        )
        self._validate_mesh()

    @property
    def ndof(self) -> int:
        return 3 * self.nodes.shape[0]

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        """Assemble high-order internal force and sparse tangent."""
        values = self._validate_displacement(displacement)
        internal = np.zeros(self.ndof, dtype=float)
        accumulator = SparseCsrAccumulator((self.ndof, self.ndof))
        chunk_rows: list[np.ndarray] = []
        chunk_cols: list[np.ndarray] = []
        chunk_values: list[np.ndarray] = []
        chunk_entry_count = 0
        peak_entries = 0
        peak_bytes = 0
        chunk_count = 0
        for index, kernel in enumerate(self._kernels):
            edofs = self.element_dofs[index]
            local_internal, local_tangent, _ = kernel.internal_force_tangent_state(
                self.nodes[self.elements[index]], values[edofs]
            )
            np.add.at(internal, edofs, local_internal)
            if tangent_required:
                local_size = int(edofs.size)
                chunk_rows.append(np.repeat(edofs, local_size))
                chunk_cols.append(np.tile(edofs, local_size))
                chunk_values.append(np.asarray(local_tangent, dtype=float).reshape(-1))
                chunk_entry_count += int(local_tangent.size)
                peak_entries = max(peak_entries, chunk_entry_count)
                peak_bytes = max(peak_bytes, _sparse_chunk_bytes_estimate(chunk_entry_count))
                if chunk_entry_count >= self._assembly_chunk_size or index == len(self._kernels) - 1:
                    chunk = coo_matrix(
                        (
                            np.concatenate(chunk_values),
                            (np.concatenate(chunk_rows), np.concatenate(chunk_cols)),
                        ),
                        shape=(self.ndof, self.ndof),
                    ).tocsr()
                    accumulator.add(chunk)
                    chunk_rows.clear()
                    chunk_cols.clear()
                    chunk_values.clear()
                    chunk_entry_count = 0
                    chunk_count += 1
        if not tangent_required:
            self._last_assembly_metrics = {
                "sparse_chunk_count": 0,
                "sparse_peak_chunk_entries": 0,
                "sparse_peak_chunk_bytes_estimate": 0,
                "sparse_accumulator_levels": 0,
            }
            return internal, None
        tangent = accumulator.finalize()
        self._last_assembly_metrics = {
            "sparse_chunk_count": chunk_count,
            "sparse_peak_chunk_entries": peak_entries,
            "sparse_peak_chunk_bytes_estimate": peak_bytes,
            "sparse_accumulator_levels": accumulator.occupied_levels,
        }
        return internal, 0.5 * (tangent + tangent.T)

    def assembly_diagnostics(self) -> dict[str, int]:
        """Return diagnostics from the most recent sparse tangent assembly."""

        return dict(self._last_assembly_metrics)

    def geometric_tangent(self, displacement: np.ndarray) -> csr_matrix:
        """Assemble the initial-stress geometric tangent in sparse form."""
        values = self._validate_displacement(displacement)
        local_tangents: list[np.ndarray] = []
        identity = np.eye(3)
        rows: list[np.ndarray] = []
        cols: list[np.ndarray] = []
        for index, kernel in enumerate(self._kernels):
            edofs = self.element_dofs[index]
            local_size = int(edofs.size)
            local_tangent = np.zeros((local_size, local_size), dtype=float)
            coords = self.nodes[self.elements[index]]
            points = kernel.integration_point_results(coords, values[edofs])
            for (measure, gradients), point in zip(
                kernel._cached_reference_data(coords), points, strict=True
            ):
                second = np.asarray(point["second_piola_stress"], dtype=float)
                scalar_blocks = np.einsum(
                    "aJ,JL,bL->ab", gradients, second, gradients, optimize=True
                )
                local_tangent += np.einsum(
                    "ab,ik->aibk", scalar_blocks, identity, optimize=True
                ).reshape(local_size, local_size) * float(measure)
            local_tangents.append(0.5 * (local_tangent + local_tangent.T))
            rows.append(np.repeat(edofs, local_size))
            cols.append(np.tile(edofs, local_size))
        tangent = coo_matrix(
            (
                np.concatenate(local_tangents).ravel(),
                (np.concatenate(rows), np.concatenate(cols)),
            ),
            shape=(self.ndof, self.ndof),
        ).tocsr()
        return 0.5 * (tangent + tangent.T)

    def strain_energy(self, displacement: np.ndarray) -> float:
        """Integrate the elastic energy in the reference configuration."""
        values = self._validate_displacement(displacement)
        total = 0.0
        for index, kernel in enumerate(self._kernels):
            points = kernel.integration_point_results(
                self.nodes[self.elements[index]], values[self.element_dofs[index]]
            )
            total += sum(
                float(point["weight"])
                * 0.5
                * float(np.dot(np.asarray(point["strain"], dtype=float), point["stress"]))
                for point in points
            )
        return float(total)

    def deformation_determinants(self, displacement: np.ndarray) -> np.ndarray:
        """Return the minimum current ``det(F)`` per element."""
        values = self._validate_displacement(displacement)
        output = []
        for index, kernel in enumerate(self._kernels):
            points = kernel.integration_point_results(
                self.nodes[self.elements[index]], values[self.element_dofs[index]]
            )
            output.append(min(float(point["det_f"]) for point in points))
        return np.asarray(output, dtype=float)

    def element_states(self, displacement: np.ndarray) -> dict[str, np.ndarray]:
        """Return measure-weighted Gauss-point fields for each element."""
        values = self._validate_displacement(displacement)
        fields = {
            key: []
            for key in (
                "deformation_gradient",
                "green_lagrange_strain",
                "second_piola_stress",
                "cauchy_stress",
            )
        }
        energies: list[float] = []
        determinants: list[float] = []
        for index, kernel in enumerate(self._kernels):
            points = kernel.integration_point_results(
                self.nodes[self.elements[index]], values[self.element_dofs[index]]
            )
            measure = sum(float(point["weight"]) for point in points)
            if measure <= 0.0 or not np.isfinite(measure):
                raise ValueError("High-order Total-Lagrangian integration measure must be positive.")
            for key in fields:
                fields[key].append(
                    sum(
                        float(point["weight"]) * np.asarray(point[key], dtype=float)
                        for point in points
                    )
                    / measure
                )
            energies.append(
                sum(
                    float(point["weight"])
                    * 0.5
                    * float(np.dot(np.asarray(point["strain"], dtype=float), point["stress"]))
                    for point in points
                )
                / measure
            )
            determinants.append(min(float(point["det_f"]) for point in points))
        return {
            **{key: np.asarray(value) for key, value in fields.items()},
            "strain_energy_density": np.asarray(energies),
            "det_f": np.asarray(determinants),
        }

    def _validate_displacement(self, displacement: np.ndarray) -> np.ndarray:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"{self.element_type}-TL displacement must be a finite vector of size {self.ndof}.")
        return values

    def _validate_mesh(self) -> None:
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3 or not np.all(np.isfinite(self.nodes)):
            raise ValueError("High-order Total-Lagrangian nodes must be a finite [n, 3] array.")
        expected = self._kernels[0].node_count
        if self.elements.shape[1] != expected:
            raise ValueError(f"{self.element_type}-TL connectivity must have {expected} nodes per element.")
        if np.min(self.elements) < 0 or np.max(self.elements) >= self.nodes.shape[0]:
            raise ValueError("High-order Total-Lagrangian connectivity contains an invalid node index.")
        if np.any(np.apply_along_axis(lambda row: np.unique(row).size, 1, self.elements) != expected):
            raise ValueError(f"{self.element_type}-TL elements must reference distinct nodes.")


def build_total_lagrangian_assembly(
    model: FiniteElementModel,
) -> TotalLagrangianTet4Assembly | TotalLagrangianHex8Assembly | TotalLagrangianHighOrderAssembly:
    """Build a homogeneous reference-configuration assembly."""
    connectivity = np.asarray([element.nodes for element in model.elements], dtype=int)
    raw_material = model.materials[model.elements[0].material]
    material = SolidMaterial(E=float(raw_material["E"]), nu=float(raw_material["nu"]))
    if model.elements[0].type == "TET4":
        return TotalLagrangianTet4Assembly(model.nodes, connectivity, material)
    if model.elements[0].type == "HEX8":
        return TotalLagrangianHex8Assembly(model.nodes, connectivity, material)
    if model.elements[0].type in {"TET10", "HEX20"}:
        return TotalLagrangianHighOrderAssembly(model, material)
    raise ValueError(f"Unsupported Total-Lagrangian element family {model.elements[0].type!r}.")


def _sparse_chunk_bytes_estimate(entry_count: int) -> int:
    """Estimate source plus concatenated sparse staging buffers."""

    if entry_count <= 0:
        return 0
    bytes_per_entry = 2 * np.dtype(np.int64).itemsize + np.dtype(np.float64).itemsize
    return int(2 * entry_count * bytes_per_entry)
