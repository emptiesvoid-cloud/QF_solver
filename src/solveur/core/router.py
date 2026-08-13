"""Dispatch models to the requested analysis solver."""

from __future__ import annotations

from solveur.core.analysis import AnalysisSettings
from solveur.core.dynamic import NewmarkDynamicSolver
from solveur.core.harmonic import HarmonicResponseSolver
from solveur.core.modal import ModalAnalysisSolver
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.core.solver import LinearStaticSolver


class AnalysisRouter:
    """Route one model to the solver matching its analysis settings."""

    def solve(self, model: FiniteElementModel) -> object:
        if not isinstance(model.analysis, AnalysisSettings):
            model.analysis = AnalysisSettings.from_raw(model.analysis)
        model.analysis.validate()
        if model.analysis.type == "linear_static":
            return LinearStaticSolver().solve(model)
        if model.analysis.type == "modal":
            return ModalAnalysisSolver().solve(model)
        if model.analysis.type == "nonlinear_static":
            from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore

            return NonlinearStaticSolver(checkpoint_store=NpzNonlinearCheckpointStore()).solve(model)
        if model.analysis.type == "geometric_nonlinear_static":
            from solveur.core.geometric_nonlinear import GeometricNonlinearStaticSolver

            return GeometricNonlinearStaticSolver().solve(model)
        if model.analysis.type == "transient_dynamic":
            from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore

            return NewmarkDynamicSolver(checkpoint_store=NpzDynamicCheckpointStore()).solve(model)
        if model.analysis.type == "harmonic_response":
            return HarmonicResponseSolver().solve(model)
        raise ValueError(f"Unsupported analysis type {model.analysis.type!r}.")
