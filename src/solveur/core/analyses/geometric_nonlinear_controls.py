"""Controls shared by future geometrically nonlinear analyses."""

from __future__ import annotations

from dataclasses import dataclass


MINIMUM_LOAD_INCREMENTS = 6
DEFAULT_LOAD_INCREMENTS = 10


@dataclass(frozen=True)
class GeometricNonlinearControls:
    """Validated load controls for total-Lagrangian structural solves."""

    load_increments: int = DEFAULT_LOAD_INCREMENTS

    def __post_init__(self) -> None:
        if isinstance(self.load_increments, bool) or not isinstance(self.load_increments, int):
            raise ValueError("load_increments must be an integer.")
        if self.load_increments < MINIMUM_LOAD_INCREMENTS:
            raise ValueError(
                f"load_increments must be at least {MINIMUM_LOAD_INCREMENTS}; "
                f"the recommended default is {DEFAULT_LOAD_INCREMENTS}."
            )
