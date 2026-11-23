"""Offline validation helpers for the WP-C01-R16 integrated smoke archive."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


from scripts.contact_archive_telemetry import decode_telemetry_events


def validate_smoke_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Replay the R16 smoke assertions without importing or calling the solver."""
    if str(payload.get("status", "")).upper() != "PASS":
        raise AssertionError(f"solver status is {payload.get('status')!r}, expected PASS")
    if payload.get("mode") != "small_rotation_work_conjugate":
        raise AssertionError("unexpected tangential transfer mode")

    events = decode_telemetry_events(payload.get("telemetry_events"))
    accepted = [
        event
        for event in events
        if event.get("event_type") == "STEP_ACCEPTED" and event.get("status") == "ACCEPTED"
    ]
    if [event.get("step") for event in accepted] != list(range(1, 10)):
        raise AssertionError("expected exactly accepted steps 1 through 9")

    for step, event in enumerate(accepted, start=1):
        committed = event.get("metrics", {}).get("committed_contact_state")
        if not isinstance(committed, Mapping):
            raise AssertionError(f"step {step} has no committed contact state")
        active_contacts = committed.get("active_contacts")
        active_count = event.get("metrics", {}).get("active_contact_count")
        if active_contacts != [0] or active_count != 1:
            raise AssertionError(f"step {step} must contain exactly one active contact")
        states = committed.get("tangential_states")
        if states != (["stick"] if step <= 7 else ["slip"]):
            raise AssertionError(f"unexpected contact state at step {step}: {states!r}")
        pressures = committed.get("pressures")
        forces = committed.get("tangential_forces")
        gaps = committed.get("gaps")
        if not (isinstance(pressures, list) and len(pressures) == 1):
            raise AssertionError(f"step {step} must have one normal pressure")
        if not (isinstance(forces, list) and len(forces) == 1 and len(forces[0]) == 2):
            raise AssertionError(f"step {step} must have one two-component tangential force")
        if not (isinstance(gaps, list) and len(gaps) == 1):
            raise AssertionError(f"step {step} must have one normal gap")
        pressure = float(pressures[0])
        gap = float(gaps[0])
        force_components = [float(component) for component in forces[0]]
        if not math.isfinite(pressure) or pressure <= 0.0:
            raise AssertionError(f"step {step} pressure must be finite and positive")
        if not math.isfinite(gap) or not all(math.isfinite(component) for component in force_components):
            raise AssertionError(f"step {step} contact values must be finite")
        force_norm = math.hypot(*force_components)
        capacity = 0.4 * pressure
        if step <= 7:
            if force_norm > capacity + 1e-6:
                raise AssertionError(f"stick force exceeds Coulomb capacity at step {step}")
        elif not math.isclose(force_norm, capacity, rel_tol=1e-8, abs_tol=1e-6):
            raise AssertionError(f"slip force is not on the Coulomb limit at step {step}")

    contact = payload.get("contact")
    if not isinstance(contact, Mapping) or contact.get("converged") is not True:
        raise AssertionError("final contact result must be converged")
    final_contacts = contact.get("contacts")
    if not isinstance(final_contacts, list) or len(final_contacts) != 1:
        raise AssertionError("expected one final contact record")
    final_contact = final_contacts[0]
    if final_contact.get("active") is not True or final_contact.get("tangential_state") != "slip":
        raise AssertionError("final contact must be active and slipping")
    return events
