"""Pytest hook loaded only by the authenticated single-node WP12 executor."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import sys
from typing import Any

import pytest


class WP12ProvenancePlugin:
    def __init__(self) -> None:
        self.expected_nodeid = os.environ.get("QF_WP12_EXPECTED_NODEID", "")
        self.solver_root = Path(os.environ.get("QF_WP12_SOLVER_ROOT", "")).resolve(strict=True)
        self.evidence_root = Path(os.environ.get("QF_WP12_EVIDENCE_ROOT", "")).resolve(strict=True)
        self.report_path = self.evidence_root / "collection.json"
        self.report_written = False

    def _write_report(self, nodeids: list[str], *, valid: bool, reason: str | None) -> None:
        modules: list[dict[str, str]] = []
        origins_valid = True
        source_hashes: dict[str, str] = {}
        for name, module in sorted(sys.modules.items()):
            if name != "solveur" and not name.startswith("solveur."):
                continue
            origin = getattr(module, "__file__", None)
            if not isinstance(origin, str):
                continue
            candidate = Path(origin).resolve(strict=False)
            try:
                candidate.relative_to(self.solver_root)
            except ValueError:
                origins_valid = False
                continue
            if not candidate.is_file() or candidate.is_symlink():
                origins_valid = False
                continue
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            relative = candidate.relative_to(self.solver_root.parent).as_posix()
            source_hashes[relative] = digest
            modules.append({"module": name, "origin": str(candidate), "sha256": digest})
        try:
            expected_hashes = json.loads(os.environ.get("QF_WP12_EXPECTED_SOURCE_HASHES", "{}"))
        except json.JSONDecodeError:
            expected_hashes = None
        declared_hashes_valid = isinstance(expected_hashes, dict) and bool(expected_hashes)
        if declared_hashes_valid:
            declared_hashes_valid = all(source_hashes.get(path) == digest for path, digest in expected_hashes.items())
        valid = (
            valid
            and origins_valid
            and declared_hashes_valid
            and any(item["module"] == "solveur" for item in modules)
        )
        report: dict[str, Any] = {
            "schema": "qf-wp12-child-collection-provenance-v1",
            "expected_nodeid": self.expected_nodeid,
            "selected_nodeids": nodeids,
            "collection_exact": nodeids == [self.expected_nodeid],
            "solver_origin_root": str(self.solver_root),
            "solver_modules": modules,
            "loaded_solver_source_hashes": dict(sorted(source_hashes.items())),
            "declared_source_hashes_verified": declared_hashes_valid,
            "solver_origins_within_expected_root": origins_valid,
            "collection_valid": valid,
            "reason": reason,
        }
        try:
            self.report_path.resolve(strict=False).relative_to(self.evidence_root)
        except ValueError as exc:
            raise pytest.UsageError("provenance report path escapes its evidence directory") from exc
        try:
            with self.report_path.open("xb") as stream:
                stream.write((json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise pytest.UsageError("refusing to overwrite the collection provenance report") from exc
        self.report_written = True

    def pytest_collection_modifyitems(self, session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
        nodeids = [item.nodeid for item in items]
        exact = nodeids == [self.expected_nodeid]
        self._write_report(nodeids, valid=exact, reason=None if exact else "pytest selected a different item set")
        if not exact:
            raise pytest.UsageError("authenticated WP12 unit collected an unexpected pytest item set")


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(WP12ProvenancePlugin(), "qf-wp12-provenance")
