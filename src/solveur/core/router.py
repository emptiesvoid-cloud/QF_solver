"""Dispatch models to the requested analysis solver."""

from __future__ import annotations

from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.analyses.dynamic import NewmarkDynamicSolver
from solveur.core.analyses.harmonic import HarmonicResponseSolver
from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.core.solvers.static import LinearStaticSolver
from solveur.compatibility import preflight_model
from solveur.compatibility.preflight import CompatibilityError
from solveur.core.errors import MeshValidationError
from solveur.mesh.validation import MeshValidator
from solveur.core.telemetry.events import EventStatus, EventType
from solveur.core.telemetry.observer import (
    TelemetryEmitter,
    TelemetryHandle,
    emit_analysis_failed_best_effort,
    emit_route_event_best_effort,
)


PHASE1_INSTRUMENTED_ROUTES = frozenset({"linear_static", "modal"})


class AnalysisRouter:
    """Route one model to the solver matching its analysis settings."""

    def solve(self, model: FiniteElementModel, *, telemetry: TelemetryEmitter | None = None) -> object:
        """Solve a model and preserve the original exception after failure telemetry."""

        if not isinstance(model.analysis, AnalysisSettings):
            model.analysis = AnalysisSettings.from_raw(model.analysis)
        actual_route = model.analysis.type
        route_telemetry = (
            telemetry.bind_route(actual_route, actual_route)
            if telemetry is not None and actual_route in PHASE1_INSTRUMENTED_ROUTES
            else None
        )
        if route_telemetry is not None:
            start_metrics: dict[str, object] = {
                "nodes": model.node_count,
                "elements": len(model.elements),
            }
            if actual_route == "modal":
                start_metrics["requested_modes"] = model.analysis.parameters.get("modes", 6)
            emit_route_event_best_effort(
                route_telemetry,
                EventType.ANALYSIS_START,
                status=EventStatus.STARTED,
                metrics=start_metrics,
            )
        try:
            return self._solve(model, telemetry=route_telemetry)
        except BaseException as error:
            emit_analysis_failed_best_effort(route_telemetry, error)
            raise

    def _solve(self, model: FiniteElementModel, *, telemetry: TelemetryHandle | None = None) -> object:
        if not isinstance(model.analysis, AnalysisSettings):
            model.analysis = AnalysisSettings.from_raw(model.analysis)
        model.analysis.validate()
        compatibility = preflight_model(model)
        try:
            compatibility.raise_for_error()
        except CompatibilityError as exc:
            if exc.result.reason != "MESH_GEOMETRY_INVALID":
                raise
            legacy_report = MeshValidator().validate(model)
            if legacy_report.errors:
                raise MeshValidationError("Mesh validation failed: " + "; ".join(legacy_report.errors)) from exc
            raise MeshValidationError(exc.result.message) from exc
        if model.analysis.type == "linear_static":
            return LinearStaticSolver().solve(model, telemetry=telemetry)
        if model.analysis.type == "modal":
            return ModalAnalysisSolver().solve(model, telemetry=telemetry)
        if model.analysis.type == "nonlinear_static":
            from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore

            return NonlinearStaticSolver(checkpoint_store=NpzNonlinearCheckpointStore()).solve(model)
        if model.analysis.type == "geometric_nonlinear_static":
            from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver
            from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore

            return GeometricNonlinearStaticSolver(checkpoint_store=NpzNonlinearCheckpointStore()).solve(model)
        if model.analysis.type == "linear_buckling":
            from solveur.core.analyses.buckling import LinearBucklingSolver

            return LinearBucklingSolver().solve(model)
        if model.analysis.type == "transient_dynamic":
            from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore

            return NewmarkDynamicSolver(checkpoint_store=NpzDynamicCheckpointStore()).solve(model)
        if model.analysis.type == "harmonic_response":
            return HarmonicResponseSolver().solve(model)
        raise ValueError(f"Unsupported analysis type {model.analysis.type!r}.")
