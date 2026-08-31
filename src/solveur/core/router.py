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


class AnalysisRouter:
    """Route one model to the solver matching its analysis settings."""

    def solve(self, model: FiniteElementModel) -> object:
        if not isinstance(model.analysis, AnalysisSettings):
            model.analysis = AnalysisSettings.from_raw(model.analysis)
        model.analysis.validate()
        preflight_model(model).raise_for_error()
        if model.analysis.type == "linear_static":
            return LinearStaticSolver().solve(model)
        if model.analysis.type == "modal":
            return ModalAnalysisSolver().solve(model)
        if model.analysis.type == "nonlinear_static":
            from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore

            return NonlinearStaticSolver(checkpoint_store=NpzNonlinearCheckpointStore()).solve(model)
        if model.analysis.type == "geometric_nonlinear_static":
            from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver

            return GeometricNonlinearStaticSolver().solve(model)
        if model.analysis.type == "linear_buckling":
            from solveur.core.analyses.buckling import LinearBucklingSolver

            return LinearBucklingSolver().solve(model)
        if model.analysis.type == "transient_dynamic":
            from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore

            return NewmarkDynamicSolver(checkpoint_store=NpzDynamicCheckpointStore()).solve(model)
        if model.analysis.type == "harmonic_response":
            return HarmonicResponseSolver().solve(model)
        raise ValueError(f"Unsupported analysis type {model.analysis.type!r}.")
