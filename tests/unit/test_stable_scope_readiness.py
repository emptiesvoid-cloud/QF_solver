"""Checks for the generated stable-scope readiness runner."""

from __future__ import annotations

import pytest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_runner():
    path = ROOT / "scripts" / "build_stable_scope_readiness.py"
    spec = importlib.util.spec_from_file_location("stable_scope_readiness_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readiness_runner_selects_latest_immutable_audit() -> None:
    runner = _load_runner()
    selected = runner._latest_audit()

    assert selected.name == "maturity_promotion_audit.json"
    assert "maturity_promotion_final_" in selected.parent.name
    assert runner._audit_sort_key(
        Path("maturity_promotion_final_20260821_v9/maturity_promotion_audit.json")
    ) < runner._audit_sort_key(
        Path("maturity_promotion_final_20260821_v20/maturity_promotion_audit.json")
    )


def test_latest_audit_contains_separated_release_fields() -> None:
    runner = _load_runner()
    payload = runner.json.loads(runner._latest_audit().read_text(encoding="utf-8"))

    assert payload["summary"]["scope_count"] == 37
    assert all(
        {"technical_status", "owner_decision", "release_readiness"}.issubset(row)
        for row in payload["scopes"]
    )

pytestmark = pytest.mark.evidence
