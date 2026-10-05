"""Single-speed experimental gyroscopic modal route for BEAM2 disk rotors."""

from __future__ import annotations

import json
import platform

import numpy as np
import scipy

from solveur.core.analyses.qep import QuadraticEigenSolver
from solveur.core.analyses.rotating_input_validator import RotatingModalInputValidator
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.assembly.rotating_disk_gyro import RotatingDiskGyroAssembler
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.results import RotatingModalResult
from solveur.io.manifest import content_digest
from solveur.io.model_writer import model_to_dict
from solveur.mesh.validation import MeshValidator
from solveur.version import __version__


class RotatingModalSolver:
    """Solve one fixed signed spin-speed QEP; owns no Campbell or tracking logic."""

    def __init__(self) -> None:
        self.input_validator = RotatingModalInputValidator()
        self.mesh_validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.gyro_assembler = RotatingDiskGyroAssembler()
        self.qep_solver = QuadraticEigenSolver()

    def solve(self, model: FiniteElementModel) -> RotatingModalResult:
        validated = self.input_validator.validate(model)
        mesh_report = self.mesh_validator.validate(model)
        if mesh_report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(mesh_report.errors))

        dofs = model.dof_manager()
        stiffness, mass, stiffness_diagnostics, mass_diagnostics = self.assembler.assemble_stiffness_and_mass(
            model, dofs
        )
        gyro = self.gyro_assembler.assemble(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size == 0:
            raise InputValidationError("rotating_modal has no free DOF after homogeneous fixed constraints.")

        reduced_mass = mass[free, :][:, free].toarray()
        reduced_stiffness = stiffness[free, :][:, free].toarray()
        reduced_gyro = gyro[free, :][:, free].toarray()
        global_dof_names = tuple(
            name for node in sorted(dofs.node_dofs) for name in dofs.node_dofs[node]
        )
        free_dof_names = tuple(global_dof_names[index] for index in free)
        qep = self.qep_solver.solve(
            reduced_mass,
            reduced_stiffness,
            reduced_gyro,
            validated.rotation.speed_rad_s,
            length_reference=validated.length_reference,
            dof_names=free_dof_names,
        )

        order = np.lexsort((qep.eigenvalues.imag, qep.eigenvalues.real, np.abs(qep.eigenvalues.imag)))
        eigenvalues = qep.eigenvalues[order]
        reduced_modes = qep.modes[:, order]
        residuals = qep.residuals[order]
        reference = float(qep.diagnostics["frequency_reference_rad_s"])
        oscillatory_threshold = 64.0 * np.finfo(float).eps * np.maximum(reference, np.abs(eigenvalues))
        physical_indices = np.flatnonzero(eigenvalues.imag > oscillatory_threshold)
        if physical_indices.size == 0:
            raise NumericalConvergenceError("QEP returned no positive-imaginary physical modes.")
        frequencies = np.abs(eigenvalues.imag) / (2.0 * np.pi)
        selected_order = np.lexsort(
            (eigenvalues.imag[physical_indices], eigenvalues.real[physical_indices], frequencies[physical_indices])
        )
        selected_indices = tuple(
            int(index) for index in physical_indices[selected_order[: validated.requested_modes]]
        )

        full_modes = np.zeros((dofs.ndof, eigenvalues.size), dtype=np.complex128)
        full_modes[free, :] = reduced_modes
        if not np.all(np.isfinite(full_modes)):
            raise NumericalConvergenceError("QEP physical mode reconstruction produced non-finite values.")
        input_digest = _model_identity_digest(model)
        diagnostics = {
            **qep.diagnostics,
            "requested_physical_modes": validated.requested_modes,
            "selected_physical_mode_count": len(selected_indices),
            "selected_mode_indices_zero_based": list(selected_indices),
            "fixed_dof_count": int(fixed.size),
            "free_dof_count": int(free.size),
            "assembly": {"stiffness": stiffness_diagnostics, "mass": mass_diagnostics},
            "mesh_warnings": list(mesh_report.warnings),
            "route_status": "EXPERIMENTAL_ROUTE",
            "maturity_is_not_inferred_from_numerical_status": True,
        }
        provenance = {
            "source_package_version": __version__,
            "model_input_sha256": input_digest,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "execution": "serial",
        }
        return RotatingModalResult(
            numerical_status="PASS",
            maturity="EXPERIMENTAL",
            eigenvalues=eigenvalues,
            modes=full_modes,
            frequencies_hz=frequencies,
            growth_rate_per_s=eigenvalues.real.copy(),
            qep_residuals=residuals,
            selected_mode_indices=selected_indices,
            dofs=dofs,
            mesh_report=mesh_report,
            node_count=model.node_count,
            element_count=len(model.elements),
            spin_speed_rad_s=validated.rotation.speed_rad_s,
            axis_global=validated.rotation.axis_global,
            frame_convention=validated.rotation.frame_convention,
            solver_metadata={
                "method": "dense_qep",
                "backend": "scipy.linalg.eig(A,B)",
                "parallel": False,
                "linearization": "generalized first companion form",
            },
            diagnostics=diagnostics,
            provenance=provenance,
        )


def _model_identity_digest(model: FiniteElementModel) -> str:
    try:
        payload = json.dumps(model_to_dict(model), sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"rotating_modal cannot derive a finite canonical model identity: {exc}") from exc
    return content_digest(payload.encode("utf-8"))
