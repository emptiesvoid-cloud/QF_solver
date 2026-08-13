"""Dispatch and execute controlled meshed benchmarks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from solveur.benchmarks.catalog import BenchmarkCatalog
from solveur.benchmarks.beam import run_beam2_cantilever
from solveur.benchmarks.dynamic import run_dynamic_cantilever
from solveur.benchmarks.nonlinear import run_j2_bar
from solveur.benchmarks.shell import run_cook, run_pinched_cylinder, run_scordelis
from solveur.benchmarks.solid import run_cantilever, run_lame, run_tet4_patch
from solveur.benchmarks.solid_extended import run_tet4_membrane, run_tet4_torsion
from solveur.benchmarks.support import BenchmarkContext
from solveur.benchmarks.types import BenchmarkDescriptor, BenchmarkRun
from solveur.core.errors import InputValidationError
from solveur.core.qualification import PROFILES


BenchmarkFunction = Callable[[BenchmarkContext], BenchmarkRun]


RUNNERS: dict[str, BenchmarkFunction] = {
    "BM-BEAM2-CANTILEVER-001": run_beam2_cantilever,
    "BM-SOL-TET4-PATCH-001": run_tet4_patch,
    "BM-SOL-TET4-MEMBRANE-001": run_tet4_membrane,
    "BM-SOL-TET4-TORSION-001": run_tet4_torsion,
    "BM-SOL-CANTILEVER-001": run_cantilever,
    "BM-SOL-TET10-LAME-001": run_lame,
    "BM-SHL-COOK-001": run_cook,
    "BM-SHL-SCORDELIS-001": run_scordelis,
    "BM-SHL-PINCHED-001": run_pinched_cylinder,
    "BM-DYN-CANTILEVER-001": run_dynamic_cantilever,
    "BM-NL-J2-BAR-001": run_j2_bar,
}


class BenchmarkRunner:
    """Run catalogued benchmarks through deterministic family-specific runners."""

    def __init__(self, catalog: BenchmarkCatalog | None = None) -> None:
        self.catalog = catalog or BenchmarkCatalog()
        catalog_ids = {item.identifier for item in self.catalog.list()}
        missing = sorted(catalog_ids - RUNNERS.keys())
        extra = sorted(RUNNERS.keys() - catalog_ids)
        if missing or extra:
            raise InputValidationError(
                f"Benchmark registry/runner mismatch: missing={missing}, extra={extra}."
            )

    def list(self) -> tuple[BenchmarkDescriptor, ...]:
        """Return descriptors in deterministic identifier order."""
        return self.catalog.list()

    def run(
        self,
        identifier: str,
        output_dir: str | Path,
        *,
        profile: str = "engineering",
    ) -> BenchmarkRun:
        """Execute one benchmark and write its controlled artifact directory."""
        if profile not in PROFILES:
            raise InputValidationError(
                f"Unknown verification profile {profile!r}; expected one of {PROFILES}."
            )
        descriptor = self.catalog.get(identifier)
        context = BenchmarkContext.create(descriptor, output_dir, profile)
        return RUNNERS[descriptor.identifier](context)
