"""Experimental Campbell sweep orchestration over the WP05 rotating_modal route."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import scipy

from solveur.core.analyses.modal_tracking import POLICY_ID, track_modal_sweep
from solveur.core.analyses.rotation_config import FRAME_CONVENTION, RotationConfig
from solveur.core.analyses.rotating_input_validator import RotatingModalInputValidator
from solveur.core.analyses.rotating_modal import RotatingModalSolver
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.assembly.rotating_disk_gyro import RotatingDiskGyroAssembler
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.results import CampbellResult, RotatingModalResult
from solveur.io.manifest import content_digest
from solveur.io.model_writer import model_to_dict
from solveur.mesh.validation import MeshValidator
from solveur.version import __version__


QEP_CONTRACT_ID = "wp05-frozen-qep-v1"
_ALLOWED_PARAMETERS = {"rotation", "spin_speeds_rad_s", "modes", "qep_settings", "tracking_policy"}


@dataclass(frozen=True)
class ValidatedCampbellInput:
    rotation: RotationConfig
    spin_speeds_rad_s: tuple[float, ...]
    requested_modes: int
    qep_settings: dict[str, str]
    tracking_policy: str


class CampbellInputValidator:
    """Validate the explicit, bounded WP06 sweep contract without mutating a model."""

    def validate(self, model: FiniteElementModel) -> ValidatedCampbellInput:
        if model.analysis.type != "campbell" or model.analysis.method != "complex_mac_hungarian":
            raise InputValidationError("The Campbell route requires method='complex_mac_hungarian'.")
        parameters = model.analysis.parameters
        unknown = sorted(set(parameters) - _ALLOWED_PARAMETERS)
        missing = sorted(_ALLOWED_PARAMETERS - set(parameters))
        if missing or unknown:
            detail = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if unknown:
                detail.append("unsupported " + ", ".join(unknown))
            raise InputValidationError("Invalid Campbell parameters: " + "; ".join(detail) + ".")

        rotation = parameters["rotation"]
        if not isinstance(rotation, Mapping) or set(rotation) != {"axis_global", "frame_convention"}:
            raise InputValidationError(
                "campbell.rotation must contain exactly axis_global and frame_convention; speed is supplied only by the sweep."
            )
        try:
            config = RotationConfig(
                axis_global=tuple(float(value) for value in rotation["axis_global"]),
                speed_rad_s=0.0,
                frame_convention=str(rotation["frame_convention"]),
            )
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Invalid Campbell rotation configuration: {exc}") from exc
        if config.frame_convention != FRAME_CONVENTION:
            raise InputValidationError(f"Campbell frame_convention must be {FRAME_CONVENTION!r}.")

        raw_speeds = parameters["spin_speeds_rad_s"]
        if not isinstance(raw_speeds, (list, tuple)) or not 2 <= len(raw_speeds) <= 101:
            raise InputValidationError("campbell.spin_speeds_rad_s must contain between 2 and 101 explicit values.")
        if any(isinstance(value, bool) for value in raw_speeds):
            raise InputValidationError("Campbell speed values must be finite numeric rad/s values, not booleans.")
        try:
            speeds = tuple(float(value) for value in raw_speeds)
        except (TypeError, ValueError) as exc:
            raise InputValidationError("Campbell speed values must be finite numeric rad/s values.") from exc
        if any(not np.isfinite(value) for value in speeds):
            raise InputValidationError("Campbell speed values must be finite.")
        if any(right <= left for left, right in zip(speeds, speeds[1:])):
            raise InputValidationError("Campbell speed values must be strictly increasing in rad/s.")

        modes = parameters["modes"]
        if isinstance(modes, bool) or not isinstance(modes, int) or modes <= 0:
            raise InputValidationError("campbell.modes must be a positive integer.")
        qep = parameters["qep_settings"]
        if not isinstance(qep, Mapping) or dict(qep) != {"contract": QEP_CONTRACT_ID}:
            raise InputValidationError(
                f"Campbell qep_settings must be exactly {{'contract': {QEP_CONTRACT_ID!r}}}; WP05 owns QEP options."
            )
        policy = parameters["tracking_policy"]
        if policy != POLICY_ID:
            raise InputValidationError(f"Campbell tracking_policy must be the frozen policy {POLICY_ID!r}.")
        return ValidatedCampbellInput(config, speeds, modes, dict(qep), str(policy))


class CampbellSolver:
    """Run a fixed-model speed sweep and associate the resulting complex modes."""

    def __init__(self) -> None:
        self.input_validator = CampbellInputValidator()
        self.rotating_validator = RotatingModalInputValidator()
        self.assembler = GlobalAssembler()
        self.gyro_assembler = RotatingDiskGyroAssembler()
        self.mesh_validator = MeshValidator()

    def solve(self, model: FiniteElementModel) -> CampbellResult:
        validated = self.input_validator.validate(model)
        structural_identity = _structural_identity(model, validated)
        model_digest = structural_identity
        modal_results: list[RotatingModalResult] = []
        invariant_matrix_hash: str | None = None
        mass_full: np.ndarray | None = None
        for speed in validated.spin_speeds_rad_s:
            point_model = copy.deepcopy(model)
            point_model.analysis = AnalysisSettings(
                type="rotating_modal",
                method="dense_qep",
                parameters={
                    "rotation": {
                        **validated.rotation.to_dict(),
                        "speed_rad_s": speed,
                    },
                    "modes": validated.requested_modes,
                },
            )
            self.rotating_validator.validate(point_model)
            point_hash, point_mass = self._matrix_invariant_hash(point_model)
            if invariant_matrix_hash is None:
                invariant_matrix_hash = point_hash
                mass_full = point_mass
            elif point_hash != invariant_matrix_hash:
                raise InputValidationError(
                    "Campbell K/M/G or DOF-reduction matrices changed during the speed sweep; speed-dependent models fail closed."
                )
            if _structural_identity(point_model, validated) != structural_identity:
                raise InputValidationError("Campbell model identity changed while constructing the speed sweep.")
            mesh_report = self.mesh_validator.validate(point_model)
            if mesh_report.status == "FAIL":
                raise MeshValidationError("Mesh validation failed: " + "; ".join(mesh_report.errors))
            result = RotatingModalSolver().solve(point_model)
            if result.numerical_status != "PASS":
                raise NumericalConvergenceError(
                    f"rotating_modal at {speed:g} rad/s returned numerical_status={result.numerical_status!r}."
                )
            if len(result.selected_mode_indices) != validated.requested_modes:
                raise NumericalConvergenceError(
                    f"rotating_modal at {speed:g} rad/s returned {len(result.selected_mode_indices)} selected modes; "
                    f"the Campbell contract requested {validated.requested_modes}."
                )
            modal_results.append(result)

        if mass_full is None or invariant_matrix_hash is None:
            raise InputValidationError("Campbell sweep produced no structural matrix identity.")
        branches, tracking_diagnostics = track_modal_sweep(modal_results, mass_full)
        source_hashes = tuple(_result_hash(item) for item in modal_results)
        source_keys = tuple(
            content_digest(
                json.dumps(
                    {
                        "model_identity_sha256": model_digest,
                        "spin_speed_rad_s": item.spin_speed_rad_s,
                        "result_sha256": result_hash,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            )
            for item, result_hash in zip(modal_results, source_hashes)
        )
        execution_identity, provenance = _execution_identity(
            model_digest=model_digest,
            validated=validated,
            matrix_hash=invariant_matrix_hash,
        )
        execution_key = content_digest(
            json.dumps(execution_identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        )
        diagnostics = {
            "route_status": "EXPERIMENTAL_ROUTE",
            "model_identity_sha256": model_digest,
            "invariant_reduced_k_m_g_sha256": invariant_matrix_hash,
            "speed_count": len(modal_results),
            "branch_count": len(branches),
            "ambiguity_count": sum(1 for item in tracking_diagnostics if item.get("status") != "CLEAR_MATCH"),
            "adaptive_refinement": "DISABLED_BY_WP06_CONTRACT",
            "maturity_is_not_inferred_from_numerical_status": True,
        }
        return CampbellResult(
            numerical_status="PASS",
            maturity="EXPERIMENTAL",
            spin_speeds_rad_s=validated.spin_speeds_rad_s,
            branches=branches,
            tracking_diagnostics=tracking_diagnostics,
            source_result_keys=source_keys,
            source_result_hashes=source_hashes,
            execution_identity=execution_identity,
            execution_key=execution_key,
            provenance=provenance,
            diagnostics=diagnostics,
            source_results=tuple(modal_results),
        )

    def _matrix_invariant_hash(self, model: FiniteElementModel) -> tuple[str, np.ndarray]:
        dofs = model.dof_manager()
        stiffness, mass, _, _ = self.assembler.assemble_stiffness_and_mass(model, dofs)
        gyro = self.gyro_assembler.assemble(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size == 0:
            raise InputValidationError("Campbell model has no free DOF after homogeneous fixed constraints.")
        reduced = [matrix[free, :][:, free].toarray() for matrix in (stiffness, mass, gyro)]
        digest = hashlib.sha256()
        for matrix in reduced:
            contiguous = np.ascontiguousarray(matrix, dtype=np.float64)
            digest.update(np.asarray(contiguous.shape, dtype="<i8").tobytes())
            digest.update(contiguous.astype("<f8", copy=False).tobytes())
        return digest.hexdigest(), mass.toarray()


def _structural_identity(model: FiniteElementModel, validated: ValidatedCampbellInput) -> str:
    payload = model_to_dict(model)
    payload["analysis"] = {
        "type": "rotating_modal",
        "method": "dense_qep",
        "parameters": {
            "rotation": {**validated.rotation.to_dict(), "speed_rad_s": 0.0},
            "modes": validated.requested_modes,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    model_digest = content_digest(canonical.encode("utf-8"))
    return model_digest


def _result_hash(result: RotatingModalResult) -> str:
    payload = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return content_digest(payload.encode("utf-8"))


def _execution_identity(
    *, model_digest: str, validated: ValidatedCampbellInput, matrix_hash: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_sha = os.environ.get("QF_SOURCE_SHA") or os.environ.get("GITHUB_SHA") or _git_source_sha()
    repository = Path(__file__).resolve().parents[4]
    authority_hashes = {}
    for relative in (
        "qualification/0_2_11/wp05_gyroscopic_contract.json",
        "qualification/0_2_11/wp06_campbell_contract.json",
    ):
        path = repository / relative
        authority_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    implementation_files = (
        "src/solveur/core/analyses/campbell.py",
        "src/solveur/core/analyses/modal_tracking.py",
        "src/solveur/core/analyses/rotation_config.py",
        "src/solveur/core/analyses/rotating_input_validator.py",
        "src/solveur/core/analyses/rotating_modal.py",
        "src/solveur/core/analyses/qep.py",
        "src/solveur/core/assembly/assembler.py",
        "src/solveur/core/assembly/rotating_disk_gyro.py",
        "src/solveur/core/results.py",
        "src/solveur/core/model.py",
        "src/solveur/post/campbell.py",
    )
    code_hashes = {
        relative: hashlib.sha256((repository / relative).read_bytes()).hexdigest()
        for relative in implementation_files
    }
    environment = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "execution": "serial",
    }
    identity = {
        "schema_version": 2,
        "case_contract_version": "0.2.11-wp06-campbell-v1",
        "case_definition": {
            "analysis": "campbell",
            "model_identity_sha256": model_digest,
            "invariant_reduced_k_m_g_sha256": matrix_hash,
            "rotation_axis_global": list(validated.rotation.axis_global),
            "frame_convention": validated.rotation.frame_convention,
            "spin_speeds_rad_s": list(validated.spin_speeds_rad_s),
            "requested_modes": validated.requested_modes,
            "tracking_policy": validated.tracking_policy,
            "qep_settings": validated.qep_settings,
            "refinement": {"enabled": False, "maximum_additional_solves": 0},
        },
        "reference_identity": {"id": "QF0211-WP06-CONTRACT-AND-GYRO-05-06", "role": "verification contract"},
        "authority_sha256": authority_hashes,
        "tolerance_policy": {
            "policy_id": POLICY_ID,
            "complex_mac_minimum": 0.8,
            "normalized_frequency_distance_maximum": 0.25,
            "ambiguity_margin_minimum": 0.05,
            "degenerate_cluster_relative_gap": 1e-8,
            "degenerate_subspace_minimum_singular_value": 0.99999999,
            "gyro05_relative_frequency_error_maximum": 1e-10,
            "gyro06_final_mesh_frequency_delta_maximum": 0.005,
            "qep_relative_residual_maximum": 1e-8,
        },
        "source_sha": source_sha,
        "software_versions": {"qf_solver": __version__, **environment},
        "implementation_sha256": code_hashes,
    }
    provenance = {
        "schema_version": 2,
        "source_sha": source_sha,
        "source_sha_availability": "AVAILABLE_AND_REPRODUCIBLE" if source_sha else "AVAILABLE_LOCAL_ONLY",
        "model_identity_sha256": model_digest,
        "invariant_reduced_k_m_g_sha256": matrix_hash,
        "implementation_sha256": code_hashes,
        "environment": environment,
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE" if source_sha else "AVAILABLE_LOCAL_ONLY",
        "timestamp_excluded_from_execution_identity": True,
        "output_paths_excluded_from_execution_identity": True,
    }
    return identity, provenance


def _git_source_sha() -> str | None:
    repository = Path(__file__).resolve().parents[4]
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if status.stdout.strip():
        return None
    value = result.stdout.strip()
    return value if len(value) == 40 else None
