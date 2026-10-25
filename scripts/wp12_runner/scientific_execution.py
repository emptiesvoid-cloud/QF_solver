"""Reserved name for the future scientific WP12 executor.

WP12-A does not enable the scientific EXECUTE mode. The only subprocesses that
the current runner can launch are the fixed synthetic SELF_TEST children.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def execute_pilot(
    *,
    runner_root: Path,
    manifest_path: Path,
    owner_decision_path: Path | None,
    supplied_manifest_sha256: str | None,
) -> dict[str, Any]:
    """Refuse every scientific run, regardless of manifest or Owner inputs."""
    del runner_root, manifest_path, owner_decision_path, supplied_manifest_sha256
    return {
        "mode": "EXECUTE",
        "campaign_id": "WP12-1-PILOT-001",
        "unit_id": "WP12-1-PILOT-001-UNIT-01",
        "event": "DENY_EXECUTION",
        "status": "DENY_EXECUTION",
        "execution_started": False,
        "attempt_reserved": False,
        "blockers": ["REAL_EXECUTION_DISABLED_IN_WP12_A"],
    }