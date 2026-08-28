"""Compatibility alias for :mod:`solveur.core.analyses.geometric_nonlinear`."""

from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module("solveur.core.analyses.geometric_nonlinear")
