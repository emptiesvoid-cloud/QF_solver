"""Supported public Python facade for QF Solver.

Application code should import documented symbols from this namespace.
The implementation is packaged under ``solveur`` for internal use.
"""

from solveur.api import *  # noqa: F403 - explicit facade defined by solveur.api.__all__
from solveur.api import __all__ as _PUBLIC_API
from solveur.version import __version__


__all__ = ["__version__", *_PUBLIC_API]
