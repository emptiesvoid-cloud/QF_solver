"""Fail-closed and provenance checks for WP08-D Phase-1 tooling."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.wp08d_phase1_common import (
    AUTHORIZED_INTEGRATION_BRANCH,
    PHASE1_AUTHORIZATION_TOKEN,
    REQUIRED_GOVERNING_SHA,
    require_phase1_authorization,
)


def test_missing_authorization_is_rejected_before_any_phase1_work(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED"):
        require_phase1_authorization(None, mesh="M1")


def test_incomplete_authorization_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    path.write_text(
        '{"authorization": "OWNER_AUTHORIZED_WP08D_PHASE1_EXECUTION", "governing_sha": "bad"}',
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED"):
        require_phase1_authorization(path, mesh="M1")


def test_authorization_contract_fields_are_explicit(tmp_path: Path) -> None:
    path = tmp_path / "authorization.json"
    path.write_text(
        "{"
        f'"authorization": "{PHASE1_AUTHORIZATION_TOKEN}", '
        f'"governing_base_sha": "{REQUIRED_GOVERNING_SHA}", '
        f'"governing_sha": "{REQUIRED_GOVERNING_SHA}", '
        f'"branch": "{AUTHORIZED_INTEGRATION_BRANCH}", '
        '"scope": "WP08-D_PHASE1_STRUCTURAL_EXECUTION", "meshes": ["M1"]}',
        encoding="utf-8",
    )
    payload = require_phase1_authorization(path, mesh="M1")
    assert payload["scope"] == "WP08-D_PHASE1_STRUCTURAL_EXECUTION"

