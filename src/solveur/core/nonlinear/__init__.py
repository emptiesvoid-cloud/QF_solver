"""Nonlinear state, constitutive contracts and solution strategies.

``NonlinearStaticSolver`` is resolved lazily so importing a contract or state
module does not introduce a cycle through the global solver orchestration.
"""

from typing import Any

__all__ = ["NonlinearStaticSolver"]


def __getattr__(name: str) -> Any:
    if name == "NonlinearStaticSolver":
        from solveur.core.nonlinear.solver import NonlinearStaticSolver

        return NonlinearStaticSolver
    raise AttributeError(name)
