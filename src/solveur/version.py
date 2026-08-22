"""Canonical public identity and version for QF_solver."""

DISPLAY_NAME = "QF_solver"
DISTRIBUTION_NAME = "qf-solver"
PRIMARY_CLI = "qf-solver"
LEGACY_CLI = "solveur-ef"
LEGACY_LAUNCHER = "main_solveur.py"
DEPRECATION_REMOVAL_VERSION = "0.3.0"
__version__ = "0.2.1a0"


def legacy_entrypoint_warning(entrypoint: str) -> str:
    """Return the stable warning emitted by temporary compatibility launchers."""
    return (
        f"WARNING: {entrypoint} is deprecated and will be removed in "
        f"QF_solver {DEPRECATION_REMOVAL_VERSION}; use {PRIMARY_CLI}."
    )
