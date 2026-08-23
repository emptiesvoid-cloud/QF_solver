"""Supported public Python facade for QF Solver.

Application code should import documented symbols from this namespace.  The
``solveur`` package remains the internal implementation namespace and the
compatibility surface for releases preceding 0.2.2.
"""

from solveur.api import *  # noqa: F403 - explicit facade defined by solveur.api.__all__
from solveur.api import __all__ as _PUBLIC_API
from solveur.version import __version__


__all__ = ["__version__", *_PUBLIC_API]
