"""Public package for the finite element solver.

Only the version is imported eagerly.  The API facade is loaded on demand so
that element formulations can remain independent from campaigns and CLI code.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from solveur.version import __version__


_API_EXPORTS = frozenset(
    {
        "assess_result",
        "benchmark_large_model",
        "check_large_readiness",
        "check_mesh",
        "convert_model_to_large",
        "generate_large_tet4_block",
        "generate_large_tet4_cantilever",
        "inspect_large_model",
        "import_gmsh_model",
        "list_benchmarks",
        "list_methods",
        "load_large_model",
        "load_model",
        "qualify_large_tet4_pipeline",
        "qualification_readiness",
        "recommended_large_block",
        "run_benchmark",
        "run_linear_solver_verification",
        "run_mitc4_validation",
        "run_qualification_case",
        "run_release_vv",
        "save_evidence",
        "save_large_readiness",
        "save_large_verification",
        "save_model",
        "save_result",
        "save_result_csv",
        "save_result_vtu",
        "solve_large_model",
        "solve_model",
        "verify_evidence",
        "verify_large_qualification",
    }
)

_CORE_EXPORTS = {
    "ConstraintTerm": "solveur.core.constraints",
    "ExitCode": "solveur.core.errors",
    "FiniteElementModel": "solveur.core.model",
    "InfrastructureError": "solveur.core.errors",
    "InputValidationError": "solveur.core.errors",
    "LinearConstraint": "solveur.core.constraints",
    "MeshValidationError": "solveur.core.errors",
    "NumericalConvergenceError": "solveur.core.errors",
    "QualificationGateError": "solveur.core.errors",
    "Rbe2Definition": "solveur.core.rbe",
    "Rbe3Definition": "solveur.core.rbe",
    "RunVerdict": "solveur.core.qualification",
}

__all__ = [
    "__version__",
    *_CORE_EXPORTS,
    *_API_EXPORTS,
]


def __getattr__(name: str) -> Any:
    """Lazily resolve the historical top-level public API."""
    if name in _API_EXPORTS:
        value = getattr(import_module("solveur.api.public"), name)
    elif module_name := _CORE_EXPORTS.get(name):
        value = getattr(import_module(module_name), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
