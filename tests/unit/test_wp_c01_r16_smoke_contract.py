from __future__ import annotations

import json

import pytest

from tests.verification.wp_c01_r16_smoke_contract import (
    decode_telemetry_event,
    decode_telemetry_events,
    validate_smoke_payload,
)
from scripts.replay_wp_c01_r16_archive import _assert_moment_contract


def test_decode_event_mapping() -> None:
    event = {"event_type": "STEP_ACCEPTED", "step": 1}
    assert decode_telemetry_event(event, index=0) == event


def test_decode_event_json_string() -> None:
    event = {"event_type": "STEP_ACCEPTED", "step": 1}
    assert decode_telemetry_event(json.dumps(event), index=0) == event


@pytest.mark.parametrize("value", ["{bad json", "null", "[]", "42", "\"text\""])
def test_decode_rejects_invalid_event_json(value: str) -> None:
    with pytest.raises(ValueError, match="telemetry event 0"):
        decode_telemetry_event(value, index=0)


@pytest.mark.parametrize("value", [None, 1, [], b'{"event_type":"STEP_ACCEPTED"}'])
def test_decode_rejects_invalid_event_values(value: object) -> None:
    with pytest.raises(ValueError, match="telemetry event 0"):
        decode_telemetry_events([value])


def test_decode_rejects_non_sequence_container() -> None:
    with pytest.raises(ValueError, match="telemetry_events"):
        decode_telemetry_events('{"event_type":"STEP_ACCEPTED"}')


def _valid_smoke_payload() -> dict[str, object]:
    events = []
    for step in range(1, 10):
        events.append(
            {
                "event_type": "STEP_ACCEPTED",
                "status": "ACCEPTED",
                "step": step,
                "metrics": {
                    "active_contact_count": 1,
                    "committed_contact_state": {
                        "active_contacts": [0],
                        "tangential_states": ["stick" if step <= 7 else "slip"],
                        "pressures": [10.0],
                        "tangential_forces": [[0.0, 4.0]],
                        "gaps": [0.0],
                    },
                },
            }
        )
    return {
        "status": "PASS",
        "mode": "small_rotation_work_conjugate",
        "telemetry_events": events,
        "contact": {
            "converged": True,
            "contacts": [{"active": True, "tangential_state": "slip"}],
        },
    }


def test_smoke_payload_requires_active_contact_on_every_accepted_step() -> None:
    payload = _valid_smoke_payload()
    validate_smoke_payload(payload)
    event = payload["telemetry_events"][4]
    event["metrics"]["committed_contact_state"]["active_contacts"] = []
    with pytest.raises(AssertionError, match="exactly one active contact"):
        validate_smoke_payload(payload)


@pytest.mark.parametrize("moment", [0.0, 0.002])
def test_independent_moment_contract_accepts_limit(moment: float) -> None:
    _assert_moment_contract(moment)


@pytest.mark.parametrize("moment", [0.0020000001, float("nan"), float("inf")])
def test_independent_moment_contract_rejects_invalid_result(moment: float) -> None:
    with pytest.raises(AssertionError):
        _assert_moment_contract(moment)
