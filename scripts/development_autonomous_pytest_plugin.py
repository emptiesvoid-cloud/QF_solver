"""Exact-node pytest gate used only by the local development launcher."""

from __future__ import annotations

from typing import Iterable

import pytest


_D01_NATIVE_NODE = (
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
    "test_wp05_native_modal_and_residual_flexibility_characterization[M3]"
)

class ExactNodeGate:
    def __init__(self, expected_nodeids: Iterable[str], *, allow_native_skip_override: bool = False) -> None:
        self.expected_nodeids = tuple(expected_nodeids)
        self.allow_native_skip_override = allow_native_skip_override

    def pytest_collection_modifyitems(self, session, config, items) -> None:
        import pytest

        collected = tuple(item.nodeid for item in items)
        if collected != self.expected_nodeids:
            raise pytest.UsageError(
                "DEVELOPMENT_AUTONOMOUS requires exactly its registered nodeid; "
                f"expected={self.expected_nodeids!r}, collected={collected!r}"
            )
        if not self.allow_native_skip_override:
            return
        if self.expected_nodeids != (_D01_NATIVE_NODE,):
            raise pytest.UsageError("native-V&V override is restricted to the registered D01 M3 node")
        if len(items) != 1:
            raise pytest.UsageError("native-V&V skip override is restricted to one exact node")
        item = items[0]
        native_skips = [
            marker
            for marker in item.own_markers
            if marker.name == "skip"
            and str(marker.kwargs.get("reason", "")).startswith("tier NATIVE_AUTH_REQUIRED:")
        ]
        if len(native_skips) != 1:
            raise pytest.UsageError(
                "D01 development override expected the existing NATIVE_AUTH_REQUIRED skip marker"
            )
        item.own_markers.remove(native_skips[0])

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item) -> Iterable[None]:
        if not self.allow_native_skip_override or item.nodeid != _D01_NATIVE_NODE:
            yield
            return

        # The development launcher has already checked the registered
        # worktree, branch, nodeid and source origin.  Reuse the solver's
        # process-local, fixed-boundary capability only for this exact call.
        from solveur.core.execution_guard import (
            authorized_native_test_scope,
            require_solver_execution_allowed,
        )

        with authorized_native_test_scope(item.nodeid):
            require_solver_execution_allowed(
                "solveur.core.analyses.reduced_harmonic.ReducedHarmonicResponseSolver.solve"
            )
            yield
