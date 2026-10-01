"""Independent algebraic kernels for the WP07-D references.

This module is intentionally limited to NumPy/SciPy algebra and frozen mesh
data.  In particular it must never import a production contact/friction
routine.  The authorized reference driver can build upon these kernels.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_wp07d_structural_vnv import (  # noqa: E402
    BODY_LOWER,
    BODY_UPPER,
    EXPECTED_MOMENT,
    EXPECTED_RESULTANT,
    TRACTION,
    accumulate_constant_t3_traction,
    generate_structured_tet4_mesh,
    resultant_and_moment,
)
from scripts.wp07d_execution_binding import (  # noqa: E402
    BINDING_PATH,
    EXPECTED_LEVELS,
    EXPECTED_ROUTES,
    UNAUTHORIZED_EXECUTION,
    _file_sha256,
    coordinate_grading_from_authorization,
    formal_contract_identity,
    mesh_axis_fractions_from_authorization,
    mesh_cell_counts_from_authorization,
    load_binding,
    penalty_integration_from_authorization,
    validate_authorized_execution_source,
    validate_binding,
    validate_formal_requalification_authorization,
)

AUTHORIZATION_TOKEN = "OWNER_AUTHORIZED_WP07D_STRUCTURAL_EXECUTION"


@dataclass(frozen=True)
class _TotalLagrangianResidualGeometry:
    """Fixed reference arrays used by repeated residual-only TET4 evaluations."""

    dof_indices: np.ndarray
    gradients: np.ndarray
    volumes: np.ndarray


class ReferenceTelemetry:
    """Flush reference-run lifecycle and solver progress without touching numerics."""

    def __init__(
        self,
        output: Path,
        *,
        route: str,
        mesh: str,
        heartbeat_interval: float = 5.0,
    ) -> None:
        if not np.isfinite(heartbeat_interval) or heartbeat_interval <= 0.0:
            raise ValueError("Telemetry heartbeat interval must be finite and positive.")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.events_path = self.output / "telemetry.jsonl"
        self.progress_path = self.output / "progress.json"
        existing = [
            path.name
            for path in (
                self.events_path,
                self.progress_path,
                self.output / "result.json",
                self.output / "run.json",
            )
            if path.exists()
        ]
        if existing:
            raise FileExistsError(f"Refusing to overwrite existing reference artifacts: {existing}")

        self.heartbeat_interval = float(heartbeat_interval)
        self._started = time.monotonic()
        self._last_solver_event_monotonic = self._started
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._closed = False
        self._state: dict[str, Any] = {
            "schema_version": 1,
            "status": "RUNNING",
            "route": route,
            "mesh": mesh,
            "process_id": os.getpid(),
            "phase": "INITIALIZING",
            "current_step": None,
            "total_steps": 8 if route == "PENALTY" else None,
            "load_factor": None,
            "current_newton_iteration": None,
            "linear_solver": None,
            "latest_residual": None,
            "current_accepted": None,
            "current_rejected": None,
            "telemetry_status": "PASS",
        }
        self._thread: threading.Thread | None = None
        with self._lock:
            self._emit_locked("RUN_START")
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"wp07d-reference-heartbeat-{route.lower()}-{mesh.lower()}",
            daemon=True,
        )
        self._thread.start()

    @property
    def telemetry_status(self) -> str:
        with self._lock:
            return str(self._state["telemetry_status"])

    def _mark_degraded_locked(self, error: OSError | TypeError | ValueError) -> None:
        self._state["telemetry_status"] = "DEGRADED"
        self._state["telemetry_error"] = f"{type(error).__name__}: {error}"

    @staticmethod
    def _resource_snapshot() -> dict[str, int | float | None]:
        rss_bytes: int | None = None
        private_bytes: int | None = None
        cpu_seconds: float | None = None
        try:
            import psutil

            process = psutil.Process(os.getpid())
            rss_bytes = int(process.memory_info().rss)
            full_memory = process.memory_full_info()
            private_value = getattr(full_memory, "uss", getattr(full_memory, "private", None))
            private_bytes = None if private_value is None else int(private_value)
            cpu = process.cpu_times()
            cpu_seconds = float(cpu.user + cpu.system)
        except Exception:
            pass
        return {
            "rss_bytes": rss_bytes,
            "private_memory_bytes": private_bytes,
            "cpu_time_seconds": cpu_seconds,
        }

    def _write_progress_locked(self, event: str) -> None:
        self._state["last_event"] = event
        self._state["elapsed_seconds"] = time.monotonic() - self._started
        self._state["last_solver_event_age_seconds"] = (
            time.monotonic() - self._last_solver_event_monotonic
        )
        self._state.update(self._resource_snapshot())
        temporary = self.progress_path.with_name(
            f".{self.progress_path.name}.{os.getpid()}.tmp"
        )
        try:
            payload = json.dumps(self._state, indent=2, sort_keys=True, allow_nan=False) + "\n"
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.progress_path)
        except (OSError, TypeError, ValueError) as error:
            self._mark_degraded_locked(error)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _emit_locked(self, event: str, **fields: Any) -> None:
        self._state.update(fields)
        if event != "HEARTBEAT":
            self._last_solver_event_monotonic = time.monotonic()
        self._state["last_event"] = event
        self._state["elapsed_seconds"] = time.monotonic() - self._started
        self._state["last_solver_event_age_seconds"] = (
            time.monotonic() - self._last_solver_event_monotonic
        )
        self._state.update(self._resource_snapshot())
        record = {
            **self._state,
            "event": event,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            serialized = json.dumps(record, sort_keys=True, allow_nan=False)
            with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except (OSError, TypeError, ValueError) as error:
            self._mark_degraded_locked(error)
        self._write_progress_locked(event)

    def emit(self, event: str, **fields: Any) -> None:
        with self._lock:
            if not self._closed:
                self._emit_locked(event, **fields)

    def update(self, **fields: Any) -> None:
        """Refresh the atomic progress snapshot without adding a JSONL event."""

        with self._lock:
            if not self._closed:
                self._state.update(fields)
                self._write_progress_locked(str(self._state.get("last_event", "STATE_UPDATE")))

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.heartbeat_interval):
            self.emit("HEARTBEAT")

    def close(self, *, status: str, error: BaseException | None = None) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join()
        with self._lock:
            if self._closed:
                return
            fields: dict[str, Any] = {"status": status, "phase": "TERMINAL"}
            if error is not None:
                fields.update({"error_type": type(error).__name__, "error": str(error)})
            event = "RUN_END" if status == "COMPLETED" else "RUN_FAIL_CLOSED"
            self._emit_locked(event, **fields)
            self._closed = True

    def __enter__(self) -> ReferenceTelemetry:
        return self

    def __exit__(
        self, exc_type: Any, exc: BaseException | None, _traceback: Any
    ) -> Literal[False]:
        self.close(status="COMPLETED" if exc is None else "FAIL_CLOSED", error=exc)
        return False


def tet4_linear_elastic_stiffness(coordinates: np.ndarray, *, young: float, poisson: float) -> np.ndarray:
    """Return an independently assembled 12x12 isotropic small-strain TET4 K."""

    points = np.asarray(coordinates, dtype=float)
    if points.shape != (4, 3) or not np.all(np.isfinite(points)):
        raise ValueError("TET4 coordinates must be finite with shape (4, 3).")
    if not young > 0.0 or not -1.0 < poisson < 0.5:
        raise ValueError("Invalid isotropic material constants.")
    affine = np.column_stack((np.ones(4), points))
    determinant = float(np.linalg.det(affine))
    volume = abs(determinant) / 6.0
    if volume <= 1.0e-15:
        raise ValueError("Degenerate independent TET4.")
    gradients = np.linalg.inv(affine)[1:, :].T
    b: np.ndarray = np.zeros((6, 12), dtype=float)
    for node, (gx, gy, gz) in enumerate(gradients):
        offset = 3 * node
        b[:, offset : offset + 3] = ((gx, 0.0, 0.0), (0.0, gy, 0.0), (0.0, 0.0, gz), (gy, gx, 0.0), (0.0, gz, gy), (gz, 0.0, gx))
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    constitutive = np.array(
        [[lam + 2 * shear, lam, lam, 0, 0, 0], [lam, lam + 2 * shear, lam, 0, 0, 0], [lam, lam, lam + 2 * shear, 0, 0, 0], [0, 0, 0, shear, 0, 0], [0, 0, 0, 0, shear, 0], [0, 0, 0, 0, 0, shear]],
        dtype=float,
    )
    return volume * b.T @ constitutive @ b


def _tet4_total_lagrangian_response_from_geometry(
    local_displacement: np.ndarray,
    gradients: np.ndarray,
    volume: float,
    *,
    young: float,
    poisson: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Evaluate the independent TET4 response from fixed reference geometry."""

    values = np.asarray(local_displacement, dtype=float)
    if values.shape != (4, 3) or not np.all(np.isfinite(values)):
        raise ValueError("Independent TET4 response requires finite (4, 3) displacements.")
    if gradients.shape != (4, 3) or not np.all(np.isfinite(gradients)):
        raise ValueError("Independent TET4 response requires finite reference gradients.")
    if not np.isfinite(volume) or volume <= 1.0e-15:
        raise ValueError("Independent TET4 response requires a positive reference volume.")
    if not young > 0.0 or not -1.0 < poisson < 0.5:
        raise ValueError("Invalid isotropic material constants.")
    deformation = np.eye(3) + np.einsum("ai,aJ->iJ", values, gradients, optimize=True)
    det_f = float(np.linalg.det(deformation))
    if not np.all(np.isfinite(deformation)) or not np.isfinite(det_f) or det_f <= 1.0e-10:
        raise ArithmeticError("Independent TET4 response produced an invalid deformation gradient.")
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    stress = lam * float(np.trace(green)) * np.eye(3) + 2.0 * shear * green
    first_piola = deformation @ stress
    internal = volume * np.einsum("iJ,aJ->ai", first_piola, gradients, optimize=True).reshape(-1)

    identity = np.eye(3)
    elasticity = (
        lam * np.einsum("IJ,KL->IJKL", identity, identity)
        + shear * np.einsum("IK,JL->IJKL", identity, identity)
        + shear * np.einsum("IL,JK->IJKL", identity, identity)
    )
    material = np.einsum(
        "iI,IJKL,kK->iJkL", deformation, elasticity, deformation, optimize=True
    )
    geometric = np.einsum("ik,LJ->iJkL", identity, stress, optimize=True)
    constitutive = material + geometric
    blocks = volume * np.einsum(
        "aJ,iJkL,bL->aibk", gradients, constitutive, gradients, optimize=True
    )
    tangent = blocks.reshape(12, 12)
    tangent = 0.5 * (tangent + tangent.T)
    energy = float(0.5 * lam * np.trace(green) ** 2 + shear * np.sum(green * green)) * volume
    if not np.all(np.isfinite(internal)) or not np.all(np.isfinite(tangent)) or not np.isfinite(energy):
        raise ArithmeticError("Independent TET4 response produced a non-finite result.")
    return internal, tangent, energy


def tet4_total_lagrangian_response(
    coordinates: np.ndarray,
    local_displacement: np.ndarray,
    *,
    young: float,
    poisson: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return an independent Saint-Venant--Kirchhoff TET4 response.

    This is deliberately self-contained.  The WP07-D PENALTY route is a
    geometrically nonlinear total-Lagrangian solve, so its reference must use
    the same kinematic formulation rather than the old small-strain matrix.
    No production assembly or contact routine is imported here.
    """

    gradients, volume = _tet4_total_lagrangian_reference_geometry(coordinates)
    return _tet4_total_lagrangian_response_from_geometry(
        local_displacement,
        gradients,
        volume,
        young=young,
        poisson=poisson,
    )


def _tet4_total_lagrangian_reference_geometry(
    coordinates: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Prepare immutable geometry data used by the residual-only TET4 kernel."""

    points = np.asarray(coordinates, dtype=float)
    if points.shape != (4, 3) or not np.all(np.isfinite(points)):
        raise ValueError("Independent TET4 response requires finite (4, 3) coordinates.")
    affine = np.column_stack((np.ones(4), points))
    determinant = float(np.linalg.det(affine))
    volume = determinant / 6.0
    if not np.isfinite(volume) or volume <= 1.0e-15:
        raise ValueError("Independent TET4 response requires a positive reference volume.")
    return np.linalg.inv(affine)[1:, :].T, volume


def _tet4_total_lagrangian_internal_force_from_geometry(
    local_displacement: np.ndarray,
    gradients: np.ndarray,
    volume: float,
    *,
    young: float,
    poisson: float,
) -> np.ndarray:
    """Evaluate an independent internal force from immutable TET4 geometry."""

    values = np.asarray(local_displacement, dtype=float)
    if values.shape != (4, 3) or not np.all(np.isfinite(values)):
        raise ValueError("Independent TET4 response requires finite (4, 3) displacements.")
    if gradients.shape != (4, 3) or not np.all(np.isfinite(gradients)):
        raise ValueError("Independent TET4 response requires finite reference gradients.")
    if not np.isfinite(volume) or volume <= 1.0e-15:
        raise ValueError("Independent TET4 response requires a positive reference volume.")
    if not young > 0.0 or not -1.0 < poisson < 0.5:
        raise ValueError("Invalid isotropic material constants.")
    deformation = np.eye(3) + np.einsum("ai,aJ->iJ", values, gradients, optimize=True)
    det_f = float(np.linalg.det(deformation))
    if not np.all(np.isfinite(deformation)) or not np.isfinite(det_f) or det_f <= 1.0e-10:
        raise ArithmeticError("Independent TET4 response produced an invalid deformation gradient.")
    green = 0.5 * (deformation.T @ deformation - np.eye(3))
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    stress = lam * float(np.trace(green)) * np.eye(3) + 2.0 * shear * green
    first_piola = deformation @ stress
    internal = volume * np.einsum("iJ,aJ->ai", first_piola, gradients, optimize=True).reshape(-1)
    if not np.all(np.isfinite(internal)):
        raise ArithmeticError("Independent TET4 response produced a non-finite result.")
    return internal


def tet4_total_lagrangian_internal_force(
    coordinates: np.ndarray,
    local_displacement: np.ndarray,
    *,
    young: float,
    poisson: float,
) -> np.ndarray:
    """Return only the independent total-Lagrangian TET4 internal force.

    Line-search candidates only need the residual, not a Newton tangent or
    strain energy.  This deliberately duplicates the force path of
    :func:`tet4_total_lagrangian_response` so that the candidate residual is
    evaluated with the identical constitutive and kinematic formulae while
    avoiding an unused 12x12 tangent construction.
    """

    gradients, volume = _tet4_total_lagrangian_reference_geometry(coordinates)
    return _tet4_total_lagrangian_internal_force_from_geometry(
        local_displacement,
        gradients,
        volume,
        young=young,
        poisson=poisson,
    )


def normal_gap(displacements: np.ndarray, slave_node: int, *, initial_clearance: float = 0.01) -> float:
    """Independent fixed-plane normal gap; positive means open."""

    values = np.asarray(displacements, dtype=float)
    return float(initial_clearance + values[3 * int(slave_node) + 2])


def fixed_normal_penalty_force(gap: float, *, penalty: float) -> float:
    """Compression-only scalar normal penalty reaction, no production imports."""

    if not penalty > 0.0:
        raise ValueError("Penalty must be positive.")
    return float(max(-gap, 0.0) * penalty)


def surface_lumped_penalty_weights(
    nodes: np.ndarray,
    slave_nodes: tuple[int, ...],
    slave_faces: tuple[tuple[int, int, int], ...],
) -> np.ndarray:
    """Independently derive normalized slave-surface tributary weights."""

    slave_set = set(int(node) for node in slave_nodes)
    if not slave_set or not slave_faces:
        raise ValueError("Surface-lumped penalty requires a non-empty slave patch and faces.")
    tributary = {node: 0.0 for node in slave_set}
    reference_area = 0.0
    for raw_face in slave_faces:
        face = tuple(int(node) for node in raw_face)
        if len(face) != 3 or len(set(face)) != 3 or any(node not in slave_set for node in face):
            raise ValueError("Slave faces must be non-degenerate faces of the slave patch.")
        triangle = np.asarray(nodes[list(face)], dtype=float)
        area = 0.5 * float(np.linalg.norm(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])))
        if not np.isfinite(area) or area <= 1.0e-14:
            raise ValueError("Slave face area must be finite and positive.")
        reference_area += area
        for node in face:
            tributary[node] += area / 3.0
    if not np.isfinite(reference_area) or reference_area <= 1.0e-14:
        raise ValueError("Slave patch reference area must be finite and positive.")
    weights = np.asarray([tributary[int(node)] / reference_area for node in slave_nodes], dtype=float)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0) or not np.isclose(np.sum(weights), 1.0):
        raise ValueError("Slave tributary weights must be positive and sum to one.")
    return weights


def _graded_contact_edge_nodes(nodes: np.ndarray, exponent: float) -> np.ndarray:
    """Independently apply the declared clamp/contact-edge coordinate grading."""

    if not np.isfinite(exponent) or exponent < 1.0:
        raise ValueError("Independent coordinate grading exponent must be finite and at least one.")
    output = np.asarray(nodes, dtype=float).copy()
    if exponent == 1.0:
        return output
    for coordinate, lower, upper in ((0, BODY_LOWER[0], BODY_UPPER[0]), (2, BODY_LOWER[2], BODY_UPPER[2])):
        normalized = (output[:, coordinate] - lower) / (upper - lower)
        output[:, coordinate] = lower + (upper - lower) * normalized**exponent
    return output


def _git(*arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _manifest_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _authorization(
    path: Path,
    binding: Mapping[str, Any],
    binding_path: Path,
    *,
    route: str,
    mesh: str,
    binding_root: Path = ROOT,
    execution_kind: str = "INDEPENDENT_REFERENCE",
) -> dict[str, Any]:
    if not path.is_file():
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    if (
        value.get("token") != binding["authorization"]["token"]
        or value.get("independent_references_allowed") is not True
        or value.get("route") != route
        or value.get("mesh") != mesh
        or value.get("binding_file_sha256") != _file_sha256(binding_path)
        or value.get("authorized_base_sha") != binding["governing"]["authorized_base_sha"]
    ):
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    declared_binding_root = value.get("binding_validation_root")
    if declared_binding_root is not None and Path(str(declared_binding_root)).resolve() != binding_root.resolve():
        raise PermissionError("WP07-D reference authorization has a different evidence-validation root.")
    validate_formal_requalification_authorization(
        value,
        binding,
        binding_path,
        route=route,
        mesh=mesh,
        execution_kind=execution_kind,
        root=binding_root,
    )
    penalty_integration_from_authorization(binding, value, route=route)
    coordinate_grading_from_authorization(binding, value)
    mesh_cell_counts_from_authorization(binding, value, level=mesh)
    mesh_axis_fractions_from_authorization(binding, value, level=mesh)
    validate_authorized_execution_source(value)
    return value


def _assemble_body(
    level: str,
    *,
    coordinate_grading_exponent: float = 1.0,
    mesh_cell_counts: tuple[int, int, int] | None = None,
    mesh_axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
) -> tuple[csr_matrix, np.ndarray, np.ndarray, tuple[int, ...], np.ndarray]:
    """Independent TET4 body assembly: no solver/contact implementation is used."""

    mesh = generate_structured_tet4_mesh(
        level, cell_counts=mesh_cell_counts, axis_fractions=mesh_axis_fractions
    )
    nodes = _graded_contact_edge_nodes(mesh.nodes, coordinate_grading_exponent)
    body_dofs = 3 * len(nodes)
    matrix = lil_matrix((body_dofs, body_dofs), dtype=float)
    for element in mesh.elements:
        local = tet4_linear_elastic_stiffness(nodes[list(element)], young=1.0e6, poisson=0.3)
        indices = np.array([3 * node + component for node in element for component in range(3)], dtype=int)
        for row, global_row in enumerate(indices):
            for column, global_column in enumerate(indices):
                matrix[global_row, global_column] += local[row, column]
    nodal_loads = accumulate_constant_t3_traction(nodes, mesh.top_faces, TRACTION)
    loads = nodal_loads.reshape(-1)
    return matrix.tocsr(), loads, nodes, mesh.slave_nodes, nodal_loads


def _solve_reduced(
    matrix: csr_matrix,
    loads: np.ndarray,
    fixed: tuple[int, ...],
    prescribed: Mapping[int, float] | None = None,
    *,
    telemetry: ReferenceTelemetry | None = None,
) -> np.ndarray:
    all_dofs: np.ndarray = np.arange(matrix.shape[0], dtype=int)
    free = np.setdiff1d(all_dofs, np.asarray(fixed, dtype=int), assume_unique=False)
    displacement = np.zeros(matrix.shape[0], dtype=float)
    values = np.zeros(matrix.shape[0], dtype=float)
    for index, value in (prescribed or {}).items():
        values[int(index)] = float(value)
    reduced_rhs = loads[free] - matrix[free, :][:, fixed] @ values[list(fixed)]
    reduced_matrix = matrix[free, :][:, free]
    if telemetry is not None:
        telemetry.emit(
            "LINEAR_SOLVE_START",
            phase="LINEAR_SOLVE",
            linear_solver="scipy.sparse.linalg.spsolve",
            linear_dimension=int(free.size),
            linear_iterations=None,
        )
    linear_started = time.monotonic()
    try:
        reduced_solution = np.asarray(spsolve(reduced_matrix, reduced_rhs), dtype=float)
    except Exception as error:
        if telemetry is not None:
            telemetry.emit(
                "LINEAR_SOLVE_ERROR",
                phase="LINEAR_SOLVE",
                linear_solver="scipy.sparse.linalg.spsolve",
                linear_solve_seconds=time.monotonic() - linear_started,
                error_type=type(error).__name__,
                error=str(error),
            )
        raise
    linear_seconds = time.monotonic() - linear_started
    if telemetry is not None:
        linear_residual = float(np.linalg.norm(reduced_matrix @ reduced_solution - reduced_rhs))
        telemetry.emit(
            "LINEAR_SOLVE_END",
            phase="NEWTON",
            linear_solver="scipy.sparse.linalg.spsolve",
            linear_iterations=None,
            linear_solve_seconds=linear_seconds,
            linear_residual_norm=linear_residual,
        )
    displacement[free] = reduced_solution
    displacement[list(fixed)] = values[list(fixed)]
    if not np.all(np.isfinite(displacement)):
        raise ArithmeticError("Independent reduced solve produced a non-finite displacement.")
    return displacement


def _assemble_total_lagrangian_body(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...],
    displacement: np.ndarray,
    *,
    residual_geometry: _TotalLagrangianResidualGeometry | None = None,
) -> tuple[np.ndarray, csr_matrix, float]:
    """Assemble the independent nonlinear TET4 body response."""

    values = np.asarray(displacement, dtype=float)
    prepared = (
        _prepare_total_lagrangian_residual_geometry(nodes, elements)
        if residual_geometry is None
        else residual_geometry
    )
    element_count = len(elements)
    if (
        prepared.dof_indices.shape != (element_count, 12)
        or prepared.gradients.shape != (element_count, 4, 3)
        or prepared.volumes.shape != (element_count,)
    ):
        raise ValueError("Independent residual geometry does not match the TET4 element count.")
    internal = np.zeros(values.size, dtype=float)
    tangent = lil_matrix((values.size, values.size), dtype=float)
    energy = 0.0
    for element_index in range(element_count):
        indices = prepared.dof_indices[element_index]
        local_internal, local_tangent, local_energy = _tet4_total_lagrangian_response_from_geometry(
            values[indices].reshape(4, 3),
            prepared.gradients[element_index],
            float(prepared.volumes[element_index]),
            young=1.0e6,
            poisson=0.3,
        )
        np.add.at(internal, indices, local_internal)
        for row, global_row in enumerate(indices):
            for column, global_column in enumerate(indices):
                tangent[global_row, global_column] += local_tangent[row, column]
        energy += local_energy
    return internal, tangent.tocsr(), float(energy)


def _prepare_total_lagrangian_residual_geometry(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...],
) -> _TotalLagrangianResidualGeometry:
    """Precompute fixed element geometry for repeated line-search residuals."""

    element_count = len(elements)
    dof_indices: np.ndarray = np.empty((element_count, 12), dtype=int)
    gradients: np.ndarray = np.empty((element_count, 4, 3), dtype=float)
    volumes: np.ndarray = np.empty(element_count, dtype=float)
    for element_index, element in enumerate(elements):
        dof_indices[element_index] = np.array(
            [3 * node + component for node in element for component in range(3)], dtype=int
        )
        element_gradients, element_volume = _tet4_total_lagrangian_reference_geometry(
            np.asarray(nodes[list(element)], dtype=float)
        )
        gradients[element_index] = element_gradients
        volumes[element_index] = element_volume
    dof_indices.setflags(write=False)
    gradients.setflags(write=False)
    volumes.setflags(write=False)
    return _TotalLagrangianResidualGeometry(dof_indices, gradients, volumes)


def _assemble_total_lagrangian_internal_force(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...],
    displacement: np.ndarray,
    *,
    residual_geometry: _TotalLagrangianResidualGeometry | None = None,
) -> np.ndarray:
    """Assemble only the nonlinear body residual for a line-search candidate.

    The candidate path uses the same element formulation and flattened
    element-accumulation order as the full body assembly.  It batches the
    independent residual work over the fixed mesh and omits tangent and energy
    work, neither of which the candidate acceptance test can consume.
    """

    values = np.asarray(displacement, dtype=float)
    prepared = (
        _prepare_total_lagrangian_residual_geometry(nodes, elements)
        if residual_geometry is None
        else residual_geometry
    )
    element_count = len(elements)
    if (
        prepared.dof_indices.shape != (element_count, 12)
        or prepared.gradients.shape != (element_count, 4, 3)
        or prepared.volumes.shape != (element_count,)
    ):
        raise ValueError("Independent residual geometry does not match the TET4 element count.")
    internal = np.zeros(values.size, dtype=float)
    local_displacements = values[prepared.dof_indices].reshape(element_count, 4, 3)
    deformation = np.eye(3)[None, :, :] + np.einsum(
        "eai,eaJ->eiJ", local_displacements, prepared.gradients, optimize=True
    )
    det_f = np.linalg.det(deformation)
    if (
        not np.all(np.isfinite(deformation))
        or not np.all(np.isfinite(det_f))
        or np.any(det_f <= 1.0e-10)
    ):
        raise ArithmeticError("Independent TET4 response produced an invalid deformation gradient.")
    green = 0.5 * (
        np.einsum("eiJ,eiK->eJK", deformation, deformation, optimize=True) - np.eye(3)[None, :, :]
    )
    young = 1.0e6
    poisson = 0.3
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    shear = young / (2.0 * (1.0 + poisson))
    stress = (
        lam * np.trace(green, axis1=1, axis2=2)[:, None, None] * np.eye(3)[None, :, :]
        + 2.0 * shear * green
    )
    first_piola = np.matmul(deformation, stress)
    local_internal = prepared.volumes[:, None, None] * np.einsum(
        "eiJ,eaJ->eai", first_piola, prepared.gradients, optimize=True
    )
    if not np.all(np.isfinite(local_internal)):
        raise ArithmeticError("Independent TET4 response produced a non-finite result.")
    np.add.at(internal, prepared.dof_indices.reshape(-1), local_internal.reshape(-1))
    return internal


def _penalty_contact_response(
    displacement: np.ndarray,
    slave_nodes: tuple[int, ...],
    activation_hints: set[int],
    *,
    penalty: float = 1.0e8,
    activation_tolerance: float = 1.0e-10,
    integration_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, csr_matrix, np.ndarray]:
    """Return the independent fixed-plane compression-only penalty response."""

    values = np.asarray(displacement, dtype=float)
    internal = np.zeros_like(values)
    tangent = lil_matrix((values.size, values.size), dtype=float)
    gaps = np.asarray([normal_gap(values, node) for node in slave_nodes], dtype=float)
    weights = np.ones(len(slave_nodes), dtype=float) if integration_weights is None else np.asarray(integration_weights, dtype=float)
    if weights.shape != gaps.shape or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("Independent penalty integration weights are invalid.")
    for node, gap, weight in zip(slave_nodes, gaps, weights, strict=True):
        dof = 3 * int(node) + 2
        effective_penalty = float(penalty) * float(weight)
        if gap < 0.0:
            internal[dof] = effective_penalty * float(gap)
            tangent[dof, dof] += effective_penalty
        elif int(node) in activation_hints and abs(float(gap)) <= activation_tolerance:
            tangent[dof, dof] += effective_penalty
    return internal, tangent.tocsr(), gaps


def _penalty_contact_internal_force(
    displacement: np.ndarray,
    slave_nodes: tuple[int, ...],
    *,
    penalty: float = 1.0e8,
    integration_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the fixed-plane penalty force and gaps without a tangent.

    Activation hints affect the one-sided tangent only; they do not affect the
    candidate contact force.  Omitting that unused sparse tangent is therefore
    algebraically equivalent for line-search residual evaluation.
    """

    values = np.asarray(displacement, dtype=float)
    internal = np.zeros_like(values)
    gaps = np.asarray([normal_gap(values, node) for node in slave_nodes], dtype=float)
    weights = (
        np.ones(len(slave_nodes), dtype=float)
        if integration_weights is None
        else np.asarray(integration_weights, dtype=float)
    )
    if weights.shape != gaps.shape or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("Penalty integration weights are invalid.")
    for node, gap, weight in zip(slave_nodes, gaps, weights, strict=True):
        dof = 3 * int(node) + 2
        effective_penalty = float(penalty) * float(weight)
        if gap < 0.0:
            internal[dof] = effective_penalty * float(gap)
    return internal, gaps


def _solve_penalty_increment(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...],
    residual_geometry: _TotalLagrangianResidualGeometry,
    loads: np.ndarray,
    slave_nodes: tuple[int, ...],
    fixed: tuple[int, ...],
    initial_displacement: np.ndarray,
    factor: float,
    activation_hints: set[int],
    integration_weights: np.ndarray,
    *,
    telemetry: ReferenceTelemetry | None = None,
    step_index: int | None = None,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray, float]:
    """Solve one frozen penalty load factor with an independent Newton loop."""

    displacement = np.asarray(initial_displacement, dtype=float).copy()
    free = np.setdiff1d(np.arange(displacement.size, dtype=int), np.asarray(fixed, dtype=int))
    target = float(factor) * np.asarray(loads, dtype=float)
    scale = max(float(np.linalg.norm(target[free])), 1.0)
    tolerance = 1.0e-10
    for iteration in range(1, 101):
        if telemetry is not None:
            telemetry.emit(
                "NEWTON_ITERATION_START",
                phase="BODY_ASSEMBLY",
                current_step=step_index,
                load_factor=float(factor),
                current_newton_iteration=iteration,
                current_accepted=False,
                current_rejected=False,
            )
        material_internal, material_tangent, energy = _assemble_total_lagrangian_body(
            nodes,
            elements,
            displacement,
            residual_geometry=residual_geometry,
        )
        contact_internal, contact_tangent, gaps = _penalty_contact_response(
            displacement, slave_nodes, activation_hints, integration_weights=integration_weights
        )
        residual = material_internal + contact_internal - target
        residual_norm = float(np.linalg.norm(residual[free]))
        relative_residual = residual_norm / scale
        if telemetry is not None:
            telemetry.emit(
                "ASSEMBLY_END",
                phase="NEWTON",
                current_step=step_index,
                load_factor=float(factor),
                current_newton_iteration=iteration,
                latest_residual=relative_residual,
                absolute_residual=residual_norm,
                active_contact_count=int(np.count_nonzero(gaps < 0.0)),
            )
        if relative_residual <= tolerance:
            if telemetry is not None:
                telemetry.emit(
                    "NEWTON_CONVERGED",
                    phase="STEP_ACCEPTANCE",
                    current_step=step_index,
                    load_factor=float(factor),
                    current_newton_iteration=iteration,
                    latest_residual=relative_residual,
                    current_accepted=True,
                    current_rejected=False,
                )
            return displacement, {
                "load_factor": float(factor),
                "iterations": iteration,
                "relative_residual": relative_residual,
                "active_contacts": [
                    int(node) for node, gap in zip(slave_nodes, gaps, strict=True) if gap < 0.0
                ],
            }, material_internal, energy

        correction = _solve_reduced(
            material_tangent + contact_tangent,
            -residual,
            fixed,
            telemetry=telemetry,
        )
        if not np.all(np.isfinite(correction)):
            raise ArithmeticError("Independent penalty Newton correction is non-finite.")
        event_alphas: dict[float, tuple[int, ...]] = {}
        for node, gap in zip(slave_nodes, gaps, strict=True):
            dof = 3 * int(node) + 2
            derivative = float(correction[dof])
            if gap > 1.0e-10 and derivative < 0.0:
                alpha = -float(gap) / derivative
                if 0.0 < alpha <= 1.0 and np.isfinite(alpha):
                    event_alphas[alpha] = (int(node),)
        candidates = [2.0 ** (-power) for power in range(0, 15)]
        candidates.extend(event_alphas)
        ordered = sorted(set(float(alpha) for alpha in candidates), reverse=True)
        accepted = False
        selected_alpha: float | None = None
        selected_merit: float | None = None
        best: tuple[float, np.ndarray, float] | None = None
        if telemetry is not None:
            telemetry.emit(
                "LINE_SEARCH_START",
                phase="LINE_SEARCH",
                current_step=step_index,
                load_factor=float(factor),
                current_newton_iteration=iteration,
                line_search_candidate_count=len(ordered),
                line_search_evaluator="batched_residual_and_gap_only",
            )
        for alpha in ordered:
            if telemetry is not None:
                telemetry.update(
                    phase="LINE_SEARCH",
                    current_step=step_index,
                    current_newton_iteration=iteration,
                    current_line_search_alpha=float(alpha),
                )
            candidate = displacement + alpha * correction
            candidate_internal = _assemble_total_lagrangian_internal_force(
                nodes,
                elements,
                candidate,
                residual_geometry=residual_geometry,
            )
            candidate_contact, candidate_gaps = _penalty_contact_internal_force(
                candidate,
                slave_nodes,
                integration_weights=integration_weights,
            )
            candidate_residual = candidate_internal + candidate_contact - target
            candidate_merit = float(np.linalg.norm(candidate_residual[free]))
            if best is None or candidate_merit < best[0]:
                best = (candidate_merit, candidate, alpha)
            if np.isfinite(candidate_merit) and candidate_merit < residual_norm:
                displacement = candidate
                selected_alpha = float(alpha)
                selected_merit = candidate_merit
                if alpha in event_alphas:
                    activation_hints.update(event_alphas[alpha])
                else:
                    activation_hints.update(
                        int(node)
                        for node, gap in zip(slave_nodes, candidate_gaps, strict=True)
                        if abs(float(gap)) <= 1.0e-10
                    )
                accepted = True
                break
        if not accepted and best is not None and np.isfinite(best[0]) and best[0] < residual_norm:
            displacement = best[1]
            selected_alpha = float(best[2])
            selected_merit = float(best[0])
            accepted = True
        if telemetry is not None:
            telemetry.emit(
                "LINE_SEARCH_END",
                phase="NEWTON",
                current_step=step_index,
                load_factor=float(factor),
                current_newton_iteration=iteration,
                accepted=accepted,
                selected_alpha=selected_alpha,
                selected_residual=selected_merit,
                current_accepted=accepted,
                current_rejected=not accepted,
            )
        if not accepted:
            raise ArithmeticError(
                f"Independent penalty Newton line search failed at load factor {factor} "
                f"and iteration {iteration}."
            )
    raise ArithmeticError(f"Independent penalty reference did not converge at load factor {factor}.")


def _reference_observables(
    route: str,
    stiffness: csr_matrix | None,
    loads: np.ndarray,
    nodes: np.ndarray,
    slave_nodes: tuple[int, ...],
    displacement: np.ndarray,
    *,
    contact_nodal_forces: np.ndarray | None = None,
    internal_force: np.ndarray | None = None,
    strain_energy: float | None = None,
    penalty_integration_weights: np.ndarray | None = None,
) -> dict[str, Any]:
    """Serialize the contract observables using only independent algebra."""

    fixed = np.asarray(
        [
            3 * node + component
            for node, point in enumerate(nodes)
            if np.isclose(point[0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)
            for component in range(3)
        ],
        dtype=int,
    )
    body_contact: np.ndarray = np.zeros((len(nodes), 3), dtype=float)
    gaps = np.asarray([normal_gap(displacement, node) for node in slave_nodes], dtype=float)
    if route == "ACTIVE_SET":
        if contact_nodal_forces is None:
            raise ArithmeticError("Active-set reference contact forces are missing.")
        body_contact = np.asarray(contact_nodal_forces, dtype=float).copy()
        contact_energy = None
        contact_energy_status = "NOT_APPLICABLE_ACTIVE_SET"
    else:
        weights = np.ones(len(slave_nodes), dtype=float) if penalty_integration_weights is None else np.asarray(
            penalty_integration_weights, dtype=float
        )
        if weights.shape != gaps.shape or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
            raise ArithmeticError("Independent penalty observable weights are invalid.")
        for node, gap, weight in zip(slave_nodes, gaps, weights, strict=True):
            body_contact[int(node), 2] = 1.0e8 * float(weight) * max(-float(gap), 0.0)
        contact_energy = float(0.5 * 1.0e8 * np.sum(weights * np.maximum(-gaps, 0.0) ** 2))
        contact_energy_status = "COMPUTED_FIXED_NORMAL_PENALTY_POTENTIAL"
    contact_vector = body_contact.reshape(-1)
    if internal_force is None:
        if stiffness is None:
            raise ArithmeticError("Reference observables require stiffness or internal force.")
        material_internal = np.asarray(stiffness @ displacement, dtype=float)
        reported_energy = float(0.5 * displacement @ material_internal)
    else:
        material_internal = np.asarray(internal_force, dtype=float)
        reported_energy = float(strain_energy) if strain_energy is not None else float("nan")
    residual = np.asarray(material_internal - contact_vector - loads, dtype=float)
    support = np.zeros_like(residual)
    support[fixed] = residual[fixed]
    support_matrix = support.reshape(len(nodes), 3) + body_contact
    external_matrix = np.asarray(loads, dtype=float).reshape(len(nodes), 3)
    contact_resultant = np.sum(body_contact, axis=0)
    reference_positions = np.asarray(nodes, dtype=float)
    current_positions = reference_positions + np.asarray(displacement, dtype=float).reshape((-1, 3))
    moment_positions = current_positions if route == "PENALTY" else reference_positions
    contact_moment = np.sum(np.cross(moment_positions, body_contact), axis=0)
    contact_moment_reference = np.sum(np.cross(reference_positions, body_contact), axis=0)
    reaction_resultant = np.sum(support_matrix, axis=0)
    reaction_moment = np.sum(np.cross(moment_positions, support_matrix), axis=0)
    reaction_moment_reference = np.sum(np.cross(reference_positions, support_matrix), axis=0)
    external_resultant = np.sum(external_matrix, axis=0)
    external_moment = np.sum(np.cross(moment_positions, external_matrix), axis=0)
    external_moment_reference = np.sum(np.cross(reference_positions, external_matrix), axis=0)
    force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
    free = np.setdiff1d(np.arange(material_internal.shape[0], dtype=int), fixed)
    free_residual = float(np.linalg.norm(residual[free]))
    free_scale = max(float(np.linalg.norm(loads[free])), 1.0)
    return {
        "schema_version": 2,
        "source": "independent_numpy_scipy_reference_postprocessed",
        "reaction_resultant": {"vector": reaction_resultant.tolist(), "norm": float(np.linalg.norm(reaction_resultant))},
        "reaction_moment_about_origin": {"vector": reaction_moment.tolist(), "norm": float(np.linalg.norm(reaction_moment))},
        "reaction_moment_about_reference_origin": {"vector": reaction_moment_reference.tolist(), "norm": float(np.linalg.norm(reaction_moment_reference))},
        "contact_resultant_body_side": {"vector": contact_resultant.tolist(), "norm": float(np.linalg.norm(contact_resultant))},
        "contact_moment_body_side_about_origin": {"vector": contact_moment.tolist(), "norm": float(np.linalg.norm(contact_moment))},
        "contact_moment_body_side_about_reference_origin": {"vector": contact_moment_reference.tolist(), "norm": float(np.linalg.norm(contact_moment_reference))},
        "maximum_penetration": float(np.max(np.maximum(-gaps, 0.0), initial=0.0)),
        "contact_energy": contact_energy,
        "contact_energy_status": contact_energy_status,
        "strain_energy": reported_energy,
        "equilibrium": {
            "force_balance_relative_error": float(np.linalg.norm(external_resultant + reaction_resultant) / force_scale),
            "moment_balance_relative_error": float(np.linalg.norm(external_moment + reaction_moment) / moment_scale),
            "free_residual_relative": free_residual / free_scale,
            "coordinate_configuration": "CURRENT_DEFORMED_BODY" if route == "PENALTY" else "REFERENCE",
            "reaction_definition": "BODY_SUPPORT_PLUS_BODY_SIDE_CONTACT",
            "reference_configuration_moment_balance_relative_error": float(
                np.linalg.norm(external_moment_reference + reaction_moment_reference)
                / max(float(np.linalg.norm(external_moment_reference)), float(np.linalg.norm(reaction_moment_reference)), 1.0)
            ),
            "reference_configuration_moment_limit_unchanged": True,
        },
        "finite": bool(np.all(np.isfinite(body_contact)) and np.all(np.isfinite(residual))),
    }


def active_set_reference(
    level: str,
    *,
    coordinate_grading_exponent: float = 1.0,
    mesh_cell_counts: tuple[int, int, int] | None = None,
    mesh_axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
    telemetry: ReferenceTelemetry | None = None,
) -> dict[str, Any]:
    """Independent fixed-plane unilateral active-set solution for one mesh."""

    if telemetry is not None:
        telemetry.emit("ASSEMBLY_START", phase="BODY_ASSEMBLY")
    stiffness, loads, nodes, slave_nodes, nodal_loads = _assemble_body(
        level,
        coordinate_grading_exponent=coordinate_grading_exponent,
        mesh_cell_counts=mesh_cell_counts,
        mesh_axis_fractions=mesh_axis_fractions,
    )
    if telemetry is not None:
        element_count = (
            int(np.prod(mesh_cell_counts) * 6) if mesh_cell_counts is not None else None
        )
        telemetry.emit(
            "ASSEMBLY_END",
            phase="ACTIVE_SET",
            node_count=int(len(nodes)),
            element_count=element_count,
            dof_count=int(stiffness.shape[0]),
            slave_node_count=int(len(slave_nodes)),
        )
    fixed: tuple[int, ...] = tuple(
        3 * node + component
        for node, point in enumerate(nodes)
        if np.isclose(point[0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)
        for component in range(3)
    )
    active: tuple[int, ...] = ()
    for iteration in range(1, 51):
        if telemetry is not None:
            telemetry.emit(
                "ACTIVE_SET_ITERATION_START",
                phase="ACTIVE_SET",
                active_set_iteration=iteration,
                active_contact_count=len(active),
                current_accepted=False,
                current_rejected=False,
            )
        contact_fixed = tuple(3 * node + 2 for node in active)
        prescribed = {index: -0.01 for index in contact_fixed}
        displacement = _solve_reduced(
            stiffness, loads, fixed + contact_fixed, prescribed, telemetry=telemetry
        )
        residual = stiffness @ displacement - loads
        newly_penetrating = {node for node in slave_nodes if normal_gap(displacement, node) < -1.0e-12}
        compressive_active = {
            node for node in active if residual[3 * node + 2] > 1.0e-10
        }
        next_active = tuple(sorted(newly_penetrating | compressive_active))
        if telemetry is not None:
            telemetry.emit(
                "ACTIVE_SET_ITERATION_END",
                phase="ACTIVE_SET",
                active_contact_count=len(active),
                next_active_contact_count=len(next_active),
                penetrating_contact_count=len(newly_penetrating),
                compressive_contact_count=len(compressive_active),
                current_accepted=next_active == active,
                current_rejected=False,
            )
        if next_active == active:
            contact = np.zeros_like(nodal_loads)
            for node in active:
                contact[node, 2] = residual[3 * node + 2]
            resultant, moment = resultant_and_moment(nodes, nodal_loads + contact)
            return {
                "status": "PASS",
                "route": "ACTIVE_SET",
                "iterations": iteration,
                "active_slave_nodes": list(active),
                "displacements": displacement.tolist(),
                "contact_nodal_forces": contact.tolist(),
                "applied_resultant": EXPECTED_RESULTANT.tolist(),
                "applied_moment": EXPECTED_MOMENT.tolist(),
                "combined_resultant": resultant.tolist(),
                "combined_moment": moment.tolist(),
                "wp07d_observables": _reference_observables(
                    "ACTIVE_SET",
                    stiffness,
                    loads,
                    nodes,
                    tuple(int(node) for node in slave_nodes),
                    displacement,
                    contact_nodal_forces=contact,
                ),
            }
        active = next_active
    raise ArithmeticError("Independent active-set did not stabilize within 50 iterations.")


def penalty_reference(
    level: str,
    *,
    penalty_integration: str = "nodal",
    coordinate_grading_exponent: float = 1.0,
    mesh_cell_counts: tuple[int, int, int] | None = None,
    mesh_axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
    telemetry: ReferenceTelemetry | None = None,
) -> dict[str, Any]:
    """Independent fixed-normal TL penalty continuation for the frozen factors."""

    if telemetry is not None:
        telemetry.emit("MESH_GENERATION_START", phase="MESH_GENERATION")
    mesh = generate_structured_tet4_mesh(
        level, cell_counts=mesh_cell_counts, axis_fractions=mesh_axis_fractions
    )
    if telemetry is not None:
        telemetry.emit(
            "MESH_GENERATION_END",
            phase="BODY_ASSEMBLY",
            node_count=int(len(mesh.nodes)),
            element_count=int(len(mesh.elements)),
            dof_count=int(3 * len(mesh.nodes)),
            slave_node_count=int(len(mesh.slave_nodes)),
        )
        telemetry.emit("ASSEMBLY_START", phase="BODY_ASSEMBLY")
    linear_stiffness, loads, nodes, slave_nodes, _ = _assemble_body(
        level,
        coordinate_grading_exponent=coordinate_grading_exponent,
        mesh_cell_counts=mesh_cell_counts,
        mesh_axis_fractions=mesh_axis_fractions,
    )
    if telemetry is not None:
        telemetry.emit(
            "ASSEMBLY_END",
            phase="PENALTY_CONTINUATION",
            node_count=int(len(nodes)),
            element_count=int(len(mesh.elements)),
            dof_count=int(linear_stiffness.shape[0]),
            slave_node_count=int(len(slave_nodes)),
        )
    fixed = tuple(
        3 * node + component
        for node, point in enumerate(nodes)
        if np.isclose(point[0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)
        for component in range(3)
    )
    displacement = np.zeros(linear_stiffness.shape[0], dtype=float)
    accepted: list[dict[str, Any]] = []
    activation_hints: set[int] = set()
    final_internal = np.zeros_like(displacement)
    final_energy = 0.0
    elements: tuple[tuple[int, int, int, int], ...] = tuple(
        (int(element[0]), int(element[1]), int(element[2]), int(element[3]))
        for element in mesh.elements
    )
    residual_geometry = _prepare_total_lagrangian_residual_geometry(nodes, elements)
    if penalty_integration == "nodal":
        integration_weights: np.ndarray = np.ones(len(slave_nodes), dtype=float)
    elif penalty_integration == "surface_lumped":
        integration_weights = surface_lumped_penalty_weights(nodes, slave_nodes, mesh.bottom_faces)
    else:
        raise ValueError("Unknown independent WP07-D penalty integration mode.")
    factors = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)
    for step_index, factor in enumerate(factors, start=1):
        if telemetry is not None:
            telemetry.emit(
                "STEP_START",
                phase="BODY_ASSEMBLY",
                current_step=step_index,
                total_steps=len(factors),
                load_factor=float(factor),
                current_accepted=False,
                current_rejected=False,
                current_newton_iteration=None,
                latest_residual=None,
            )
        displacement, increment, final_internal, final_energy = _solve_penalty_increment(
            nodes,
            elements,
            residual_geometry,
            loads,
            slave_nodes,
            fixed,
            displacement,
            factor,
            activation_hints,
            integration_weights,
            telemetry=telemetry,
            step_index=step_index,
        )
        accepted.append(increment)
        if telemetry is not None:
            telemetry.emit(
                "STEP_ACCEPTED",
                phase="STEP_ACCEPTED",
                current_step=step_index,
                total_steps=len(factors),
                load_factor=float(factor),
                newton_iterations=int(increment["iterations"]),
                latest_residual=float(increment["relative_residual"]),
                current_accepted=True,
                current_rejected=False,
                active_contact_count=len(increment["active_contacts"]),
            )
    return {
        "status": "PASS",
        "route": "PENALTY",
        "accepted_increments": accepted,
        "displacements": displacement.tolist(),
        "penalty": 1.0e8,
        "penalty_integration": penalty_integration,
        "penalty_integration_weights": integration_weights.tolist(),
        "normal_model": "fixed_plane_compression_only",
        "kinematics": "independent_total_lagrangian_saint_venant_kirchhoff",
        "wp07d_observables": _reference_observables(
            "PENALTY",
            None,
            loads,
            nodes,
            tuple(int(node) for node in slave_nodes),
            displacement,
            internal_force=final_internal,
            strain_energy=final_energy,
            penalty_integration_weights=integration_weights,
        ),
    }


def execute(
    route: str,
    mesh: str,
    authorization_path: Path,
    output: Path,
    *,
    binding_path: Path = BINDING_PATH,
    binding_root: Path = ROOT,
    telemetry_heartbeat_interval: float = 5.0,
) -> dict[str, Any]:
    """Run one authorized independent reference and immediately archive its JSON."""

    binding = load_binding(binding_path)
    validate_binding(binding, root=binding_root)
    authorization = _authorization(
        authorization_path,
        binding,
        binding_path,
        route=route,
        mesh=mesh,
        binding_root=binding_root,
        execution_kind="INDEPENDENT_REFERENCE",
    )
    penalty_integration = penalty_integration_from_authorization(binding, authorization, route=route)
    coordinate_grading_exponent = coordinate_grading_from_authorization(binding, authorization)
    mesh_cell_counts = mesh_cell_counts_from_authorization(binding, authorization, level=mesh)
    mesh_axis_fractions = mesh_axis_fractions_from_authorization(binding, authorization, level=mesh)
    result_path = output / "result.json"
    with ReferenceTelemetry(
        output,
        route=route,
        mesh=mesh,
        heartbeat_interval=telemetry_heartbeat_interval,
    ) as telemetry:
        telemetry.emit(
            "REFERENCE_START",
            phase="REFERENCE_SETUP",
            binding_file_sha256=_file_sha256(binding_path),
            authorization_file_sha256=_file_sha256(authorization_path),
            coordinate_grading_exponent=coordinate_grading_exponent,
            mesh_cell_counts=list(mesh_cell_counts) if mesh_cell_counts is not None else None,
            linear_solver="scipy.sparse.linalg.spsolve",
        )
        payload = (
            active_set_reference(
                mesh,
                coordinate_grading_exponent=coordinate_grading_exponent,
                mesh_cell_counts=mesh_cell_counts,
                mesh_axis_fractions=mesh_axis_fractions,
                telemetry=telemetry,
            )
            if route == "ACTIVE_SET"
            else penalty_reference(
                mesh,
                penalty_integration=penalty_integration,
                coordinate_grading_exponent=coordinate_grading_exponent,
                mesh_cell_counts=mesh_cell_counts,
                mesh_axis_fractions=mesh_axis_fractions,
                telemetry=telemetry,
            )
        )
        payload["mesh_cell_counts"] = list(mesh_cell_counts) if mesh_cell_counts is not None else None
        payload["coordinate_grading_exponent"] = coordinate_grading_exponent
        payload["mesh_axis_fractions"] = (
            {axis: list(values) for axis, values in zip(("x", "y", "z"), mesh_axis_fractions, strict=True)}
            if mesh_axis_fractions is not None
            else None
        )
        contract_identity = formal_contract_identity(binding, root=binding_root)
        if contract_identity is not None:
            payload["formal_contract_provenance"] = contract_identity
            payload["owner_decision"] = binding["owner_decision"]
        payload["execution_kind"] = "INDEPENDENT_REFERENCE"
        telemetry.emit("RESULT_WRITE_START", phase="RESULT_ARCHIVE")
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        telemetry.emit(
            "RESULT_ARCHIVED",
            phase="RESULT_ARCHIVE",
            result_file_sha256=_file_sha256(result_path),
            reference_status=payload.get("status"),
        )
    report = {
        "status": "COMPLETED",
        "route": route,
        "mesh": mesh,
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": _git("rev-parse", "HEAD"),
        "binding_path": _manifest_path(binding_path),
        "binding_validation_root": _manifest_path(binding_root),
        "authorization_path": _manifest_path(authorization_path),
        "binding_file_sha256": _file_sha256(binding_path),
        "authorization_file_sha256": _file_sha256(authorization_path),
        "result_file_sha256": _file_sha256(result_path),
        "authorization_token": authorization["token"],
        "execution_kind": "INDEPENDENT_REFERENCE",
        "penalty_integration": penalty_integration,
        "coordinate_grading_exponent": coordinate_grading_exponent,
        "mesh_cell_counts": list(mesh_cell_counts) if mesh_cell_counts is not None else None,
        "mesh_axis_fractions": (
            {axis: list(values) for axis, values in zip(("x", "y", "z"), mesh_axis_fractions, strict=True)}
            if mesh_axis_fractions is not None
            else None
        ),
        "telemetry_status": telemetry.telemetry_status,
        "telemetry_path": "telemetry.jsonl",
        "telemetry_file_sha256": (
            _file_sha256(output / "telemetry.jsonl")
            if (output / "telemetry.jsonl").is_file()
            else None
        ),
        "progress_path": "progress.json",
        "progress_file_sha256": (
            _file_sha256(output / "progress.json")
            if (output / "progress.json").is_file()
            else None
        ),
    }
    contract_identity = formal_contract_identity(binding, root=binding_root)
    if contract_identity is not None:
        report["formal_contract_provenance"] = contract_identity
        report["owner_decision"] = binding["owner_decision"]
        report["source_contains_wp07_candidate_changes_since_governing_base"] = binding[
            "source_lineage_disclosure"
        ]["source_contains_wp07_candidate_changes_since_governing_base"]
    (output / "run.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=EXPECTED_ROUTES, required=True)
    parser.add_argument("--mesh", choices=EXPECTED_LEVELS, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--binding", type=Path, default=BINDING_PATH)
    parser.add_argument("--binding-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.binding = args.binding.resolve()
    args.binding_root = args.binding_root.resolve()
    args.authorization = args.authorization.resolve()
    args.output = args.output.resolve()
    try:
        print(
            json.dumps(
                execute(
                    args.route,
                    args.mesh,
                    args.authorization,
                    args.output,
                    binding_path=args.binding,
                    binding_root=args.binding_root,
                ),
                indent=2,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, PermissionError, ArithmeticError, subprocess.CalledProcessError) as error:
        print(f"WP07-D independent reference blocked or failed closed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
