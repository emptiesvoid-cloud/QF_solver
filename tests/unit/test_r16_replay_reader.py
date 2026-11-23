import json

import pytest

from scripts import replay_wp_c01_r16_archive as consumer


def _payload():
    events = []
    for step in range(1, 10):
        state = {"active_contacts": [0], "tangential_states": ["stick" if step <= 7 else "slip"],
                 "pressures": [10.0], "tangential_forces": [[0.0, 4.0]], "gaps": [0.0]}
        events.append({"event_type": "STEP_ACCEPTED", "status": "ACCEPTED", "step": step,
                       "metrics": {"active_contact_count": 1, "committed_contact_state": state}})
    return {"status": "PASS", "mode": "small_rotation_work_conjugate", "telemetry_events": events,
            "contact": {"converged": True, "contacts": [{"active": True, "tangential_state": "slip"}]}}


@pytest.mark.parametrize("serialized", [False, True])
def test_replay_decodes_events_before_identity_check(serialized):
    payload = _payload()
    if serialized:
        payload["telemetry_events"] = [json.dumps(e) for e in payload["telemetry_events"]]
    with pytest.raises(ValueError, match="identity mismatch"):
        consumer.replay(payload, {}, {})


@pytest.mark.parametrize("bad", ["{bad", "[]", None])
def test_replay_rejects_invalid_event(bad):
    payload = _payload()
    payload["telemetry_events"][0] = bad
    with pytest.raises(ValueError, match="telemetry event 0"):
        consumer.replay(payload, {}, {})
