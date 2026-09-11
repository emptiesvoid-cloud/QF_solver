---
doc_id: DOC-029-WP02-003
revision: 1.0
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP02-A checkpoint failure matrix

| Situation | Outcome | State effect |
| --- | --- | --- |
| Convergence and save succeed | `PASS` | Accepted state and checkpoint valid |
| Convergence succeeds, save fails | `CHECKPOINT_FAILURE` | Accepted physical state remains authoritative; no silent success or cutback |
| Corrupt/truncated NPZ | Input validation error | No state installed |
| Persisted digest mismatch | `STATE_CORRUPTION` | No state installed; expose digest diagnostics |
| Wrong model signature | Input validation error | No state installed |
| Wrong topology or DOF count | Input validation error | No state installed |
| Unsupported schema or missing field | Input validation error | No state installed |
| Non-finite accepted state | `STATE_CORRUPTION` | No state installed |

`CHECKPOINT_FAILURE` describes failure while producing/persisting a valid
accepted state. Input validation describes an absent, unsupported or
model-incompatible input. `STATE_CORRUPTION` describes a present checkpoint
whose accepted-state integrity or finite-value contract is violated.

These failures are non-retryable by default. Storage retry, if ever allowed,
must be an explicit infrastructure policy and must not become physical load
cutback.
