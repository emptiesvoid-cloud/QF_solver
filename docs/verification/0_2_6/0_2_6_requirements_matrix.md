# Requirements Matrix

| ID | Priority | Requirement | Verification | Gate |
| --- | --- | --- | --- | --- |
| `REQ-026-001` | MUST | Preserve the immutable 0.2.5 numerical source and claims. | baseline snapshot plus provenance review | `026-G00` |
| `REQ-026-002` | MUST | Provide a versioned machine-readable registry for controlled V&V cases. | registry schema and unit tests | `026-G02` |
| `REQ-026-003` | MUST | Separate planned definitions from executable evidence. | execution-state and smoke-selection tests | `026-G03` |
| `REQ-026-004` | MUST | Produce digest-first evidence with source, environment and threshold provenance. | runner manifest contract tests | `026-G02` |
| `REQ-026-005` | MUST | Keep external tools optional and record unavailable tools as skipped, never passed. | oracle registry and future adapter tests | `026-G13` |
| `REQ-026-006` | MUST | Keep public claims bounded by recorded evidence and Owner decisions. | gate and claim audit before release decision | `026-G15` |
| `REQ-026-007` | SHOULD | Characterize performance with repeatable measurements and hardware metadata. | scaling profiles and benchmark manifests | `026-G12` |
| `REQ-026-008` | MUST | Qualify only the declared bounded Total-Lagrangian elasticity scope; retain high-order routes as research unless separately evidenced. | G07 contract and capability matrix | `026-G07` |
| `REQ-026-009` | MUST | Exercise arc-length only as controlled internal research evidence; do not promote it to production qualification. | bounded Step 2 evidence manifest | `026-G07` |
