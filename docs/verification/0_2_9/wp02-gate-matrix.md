---
doc_id: DOC-029-WP02-004
revision: 1.0
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP02-A prospective gates

| Gate | Requirement | Frozen acceptance |
| --- | --- | --- |
| G02-01 | Composite checkpoint completeness | Schema 2 represents all accepted state components, topology and digests |
| G02-02 | Round-trip exactness | Component and composite digests are exactly equal after save/load |
| G02-03 | Fixed-load restart | Continuous and interrupted/restarted result agrees at relative `1e-9`, absolute `1e-12` |
| G02-04 | Arc-length restart | Path, load factor, radius and continuation agree; persisted digests remain exact |
| G02-05 | Checkpoint integrity | Corrupt, non-finite and digest-mismatched inputs fail deterministically |
| G02-06 | Atomic persistence | Failed write cannot expose a partially valid canonical checkpoint |
| G02-07 | v1 compatibility | Supported v1 migrates safely; ambiguous contact-bearing v1 follows OD-029-02 |
| G02-08 | One state authority | Legacy helpers cannot publish a second accepted-state/checkpoint identity |
| G02-09 | No trial persistence | Rejected or unaccepted trial data never enters a checkpoint |
| G02-10 | Numerical preservation | Existing nonlinear behavior remains unchanged outside persistence plumbing |

Persisted deterministic quantities use relative `1e-12` and absolute `1e-14`.
Existing stricter tests remain authoritative. WP02-A freezes these gates and
awards **0/6**; implementation and independent closure are still required.
