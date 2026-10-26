"""Exact-node pytest gate used only by the local development launcher."""

from __future__ import annotations

import json
import os
from typing import Iterable

import pytest


_D01_NATIVE_NODES = (
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
    "test_wp05_native_modal_and_residual_flexibility_characterization[M1]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
    "test_wp05_native_modal_and_residual_flexibility_characterization[M2]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
    "test_wp05_native_modal_and_residual_flexibility_characterization[M3]",
)

ROTOR_PREFLIGHT_MARKER = "QF_DEV_ROTOR_PREFLIGHT="


class ExactNodeGate:
    def __init__(self, expected_nodeids: Iterable[str], *, allow_native_skip_override: bool = False) -> None:
        self.expected_nodeids = tuple(expected_nodeids)
        self.allow_native_skip_override = allow_native_skip_override

    @pytest.hookimpl(trylast=True)
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
        if len(self.expected_nodeids) != 1 or self.expected_nodeids[0] not in _D01_NATIVE_NODES:
            raise pytest.UsageError("native-V&V override is restricted to one registered D01 M1/M2/M3 node")
        if len(items) != 1:
            raise pytest.UsageError("native-V&V skip override is restricted to one exact node")
        item = items[0]
        native_skips = [
            marker
            for marker in item.own_markers
            if marker.name == "skip" and str(marker.kwargs.get("reason", "")).startswith("tier NATIVE_AUTH_REQUIRED:")
        ]
        if len(native_skips) != 1:
            raise pytest.UsageError("D01 development override expected the existing NATIVE_AUTH_REQUIRED skip marker")
        item.own_markers.remove(native_skips[0])

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item) -> Iterable[None]:
        if not self.allow_native_skip_override or item.nodeid not in _D01_NATIVE_NODES:
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


class ExactCollectOnlyAttestor:
    """Emit a machine-readable record for one exact, non-skipped collect-only node."""

    def __init__(self, expected_nodeid: str, *, solver_origin: str, selected_dofs: int, max_dofs: int) -> None:
        self.expected_nodeid = expected_nodeid
        self.solver_origin = solver_origin
        self.selected_dofs = selected_dofs
        self.max_dofs = max_dofs
        self.collected_nodeids: list[str] = []
        self.skip_markers: list[dict[str, str]] = []
        self.bodies_executed = False

    def pytest_collection_finish(self, session) -> None:
        self.collected_nodeids = [item.nodeid for item in session.items]
        for item in session.items:
            for marker in item.iter_markers():
                if marker.name in {"skip", "skipif"}:
                    self.skip_markers.append(
                        {
                            "nodeid": item.nodeid,
                            "marker": marker.name,
                            "reason": str(marker.kwargs.get("reason", "")),
                        }
                    )

    def pytest_runtest_call(self, item) -> None:
        self.bodies_executed = True

    def pytest_sessionfinish(self, session, exitstatus: int) -> None:
        payload = {
            "schema": "qfsolver-rotor-collect-only-v1",
            "expected_nodeid": self.expected_nodeid,
            "collected_nodeids": self.collected_nodeids,
            "skip_markers": self.skip_markers,
            "bodies_executed": self.bodies_executed,
            "solver_origin": self.solver_origin,
            "worktree_id": os.environ.get("QF_DEV_WORKTREE_ID"),
            "selected_dofs_expected": self.selected_dofs,
            "selected_dofs": os.environ.get("QF_DEV_SELECTED_DOFS"),
            "max_dofs_expected": self.max_dofs,
            "max_dofs": os.environ.get("QF_DEV_MAX_DOFS"),
            "exitstatus": int(exitstatus),
        }
        print(ROTOR_PREFLIGHT_MARKER + json.dumps(payload, sort_keys=True, separators=(",", ":")))
