---
doc_id: DOC-029-WP02-002
revision: 1.0
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP02-A compatibility matrix

| Current component | Prospective role | Boundary |
| --- | --- | --- |
| `NonlinearStateTransaction` | **AUTHORITATIVE** | Sole accepted composite state authority |
| `StateTransaction` | **COMPATIBILITY** | Retain for legacy generic/contact/research helpers; never persist global nonlinear state |
| `MaterialStateSession` | **COMPATIBILITY** | Retain for legacy material-only callers; migrated routes delegate through composite state |
| `commit_material_states` | **COMPATIBILITY_ADAPTER** | Mirror accepted material state only after composite acceptance |
| `material_state.state_digest` | **DELEGATE** | Compatibility helper; cannot define accepted-state identity |
| `deterministic_state_digest` | **AUTHORITATIVE** | Component and composite checkpoint digests |
| `NonlinearCheckpoint` v1 | **COMPATIBILITY** | Read/migrate only within bounded v1 policy |
| fixed-load `restore` | **ADAPT** | Construct one accepted composite state |
| arc-length `restore_continuation` | **ADAPT** | Construct the same accepted state with continuation payload |
| `NpzNonlinearCheckpointStore` | **ADAPT** | Add schema 2, integrity checks and atomic durability |
| `FrictionlessActiveSetSolver` | **RESEARCH_COMPATIBILITY** | Not part of the public nonlinear checkpoint authority |

No public/used legacy class is removed in WP02-A. A later deprecation requires
compatibility evidence and Owner review.
