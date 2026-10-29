"""Exact-node pytest gate used only by the local development launcher."""

from __future__ import annotations

import json
import os
from pathlib import Path
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

    def __init__(
        self,
        expected_nodeid: str,
        *,
        solver_origin: str,
        selected_dofs: int | None,
        max_dofs: int | None,
        schema: str = "qfsolver-rotor-collect-only-v1",
        marker: str = ROTOR_PREFLIGHT_MARKER,
    ) -> None:
        self.expected_nodeid = expected_nodeid
        self.solver_origin = solver_origin
        self.selected_dofs = selected_dofs
        self.max_dofs = max_dofs
        self.schema = schema
        self.marker = marker
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
            "schema": self.schema,
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
        print(self.marker + json.dumps(payload, sort_keys=True, separators=(",", ":")))


class Hex8SRIConvergence24Attestor:
    """Write an exclusive report proving exact, skip-free collection without test calls."""

    def __init__(self, expected_nodeid: str, *, scope_id: str) -> None:
        self.expected_nodeid = expected_nodeid
        self.scope_id = scope_id
        self.collected_nodeids: list[str] = []
        self.skip_markers: list[str] = []
        self.bodies_executed = False

    def pytest_collection_finish(self, session) -> None:
        self.collected_nodeids = [item.nodeid for item in session.items]
        selected = [item for item in session.items if item.nodeid == self.expected_nodeid]
        self.skip_markers = sorted(
            {marker.name for item in selected for marker in item.iter_markers() if marker.name in {"skip", "skipif"}}
        )

    def pytest_runtest_call(self, item) -> None:
        self.bodies_executed = True

    def pytest_sessionfinish(self, session, exitstatus: int) -> None:
        report_text = os.environ.get("QF_DEV_PREFLIGHT_COLLECTION_REPORT")
        if not report_text:
            return
        report = {
            "schema": "qfsolver-hex8sri-convergence24-collection-v1",
            "scope_id": self.scope_id,
            "target": self.expected_nodeid,
            "collected_nodeids": self.collected_nodeids,
            "skip_markers": self.skip_markers,
            "bodies_executed": self.bodies_executed,
            "exitstatus": int(exitstatus),
        }
        destination = Path(report_text).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())


class VV3DCollectOnlyAttestor:
    """Emit one exact-node VV3D collect-only report without invoking test bodies."""

    def __init__(self, expected_nodeid: str, *, scope_id: str) -> None:
        self.expected_nodeid = expected_nodeid
        self.scope_id = scope_id
        self.collected_nodeids: list[str] = []
        self.skip_markers: list[dict[str, str]] = []
        self.bodies_executed = False

    def pytest_collection_finish(self, session) -> None:
        self.collected_nodeids = [item.nodeid for item in session.items]
        for item in session.items:
            for marker in item.iter_markers():
                if marker.name in {"skip", "skipif"}:
                    self.skip_markers.append({"nodeid": item.nodeid, "marker": marker.name,
                                              "reason": str(marker.kwargs.get("reason", ""))})

    def pytest_runtest_call(self, item) -> None:
        self.bodies_executed = True

    def pytest_sessionfinish(self, session, exitstatus: int) -> None:
        report_text = os.environ.get("QF_DEV_PREFLIGHT_COLLECTION_REPORT")
        if not report_text:
            return
        report = {
            "schema": "qfsolver-wp12-vv3d-collection-v1", "scope_id": self.scope_id,
            "target": self.expected_nodeid, "collected_nodeids": self.collected_nodeids,
            "skip_markers": self.skip_markers, "bodies_executed": self.bodies_executed,
            "exitstatus": int(exitstatus),
        }
        destination = Path(report_text).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
