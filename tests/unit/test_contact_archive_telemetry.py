from __future__ import annotations

import json

import pytest

from scripts.contact_archive_telemetry import decode_telemetry_event, decode_telemetry_events


def test_decode_mapping_returns_a_copy() -> None:
    event = {"event_type": "STEP_ACCEPTED", "step": 1}

    decoded = decode_telemetry_event(event, index=0)

    assert decoded == event
    assert decoded is not event


def test_decode_json_string_event() -> None:
    event = {"event_type": "STEP_ACCEPTED", "step": 1}

    assert decode_telemetry_event(json.dumps(event), index=0) == event


@pytest.mark.parametrize("value", ["{bad json", "null", "[]", "42", '"text"'])
def test_decode_rejects_invalid_or_non_object_json(value: str) -> None:
    with pytest.raises(ValueError, match="telemetry event 0"):
        decode_telemetry_event(value, index=0)


@pytest.mark.parametrize("value", [None, 1, [], b'{"event_type":"STEP_ACCEPTED"}'])
def test_decode_rejects_non_mapping_event_values(value: object) -> None:
    with pytest.raises(ValueError, match="telemetry event 0"):
        decode_telemetry_events([value])


def test_decode_events_rejects_a_string_container() -> None:
    with pytest.raises(ValueError, match="telemetry_events"):
        decode_telemetry_events('{"event_type":"STEP_ACCEPTED"}')


def test_decode_events_normalizes_a_sequence() -> None:
    events = [
        {"event_type": "STEP_ACCEPTED", "step": 1},
        json.dumps({"event_type": "STEP_ACCEPTED", "step": 2}),
    ]

    assert decode_telemetry_events(events) == [
        {"event_type": "STEP_ACCEPTED", "step": 1},
        {"event_type": "STEP_ACCEPTED", "step": 2},
    ]
