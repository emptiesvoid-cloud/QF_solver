"""Exact-node pytest gate used only by the local development launcher."""

from __future__ import annotations

from typing import Iterable


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
