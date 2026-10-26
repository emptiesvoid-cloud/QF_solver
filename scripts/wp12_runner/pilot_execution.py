"""Fail-closed boundary for future scientific pilot execution.

The Windows SYSTEM worker currently authenticates and archives bytes but does
not attest which child process ran or whether it executed the approved pytest
node. Until that control exists and is independently reviewed, this module
must not launch a command. Synthetic process supervision lives in
``synthetic_orchestrator`` and cannot select QF Solver tests.
"""

from __future__ import annotations

from typing import Any, Mapping


def execute_authenticated_pilot_unit(
    *,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    owner_decision_sha256: str,
    owner_decision_id: str,
    context: Mapping[str, Any],
    environment_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Deny until protected child-process attestation and review are implemented.

    Parameters are retained to make the intended production boundary explicit.
    None of them can turn this denial into an execution authorization.
    """
    return {
        "mode": "EXECUTE",
        "campaign_id": manifest.get("campaign_id"),
        "decision_id": owner_decision_id,
        "manifest_sha256": manifest_sha256,
        "owner_decision_sha256": owner_decision_sha256,
        "context_observed": bool(context),
        "environment_observed": bool(environment_report),
        "status": "DENY_EXECUTION",
        "reason": "SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED",
        "execution_started": False,
    }
