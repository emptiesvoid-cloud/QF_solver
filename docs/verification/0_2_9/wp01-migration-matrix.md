---
doc_id: DOC-029-WP01-004
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 migration matrix

| Existing path | Classification | Direction |
| --- | --- | --- |
| `solve_full_newton` | RETAIN | Closest shared driver foundation; evolve behind the unified contract. |
| `solve_adaptive_full_newton` | ADAPT | Preserve cutback but replace displacement-only rollback. |
| `NonlinearStaticSolver._solve_load_step` | MIGRATE | Remove material-specific Newton ownership by delegation. |
| Arc-length corrector | ADAPT | Retain continuation mathematics as a shared driver mode. |
| `GeometricNonlinearStaticSolver` | WRAP | Preserve public compatibility; it already composes through the shared seam. |
| `assemble_internal_tangent` | ADAPT | Retain immutable plan/trial states; return common contribution response. |
| `assemble_penalty_contact` | ADAPT | Retain bounded penalty mechanics, return contact contribution diagnostics/state. |
| `FrictionlessActiveSetSolver` | RESEARCH_COMPATIBILITY | Retain bounded route until separately adapted. |
| Frictional active-set/fixed-point/semi-smooth path | RESEARCH_COMPATIBILITY | No WP01 frictional integration or promotion. |
| Checkpoint/restart | MIGRATE | Retain storage boundary; later adopt declared unified payload. |
| Duplicate load-control line search | DEPRECATE_LATER | Preserve compatibility until shared dispatch passes gates. |
| Geometric compatibility line-search wrapper | WRAP | Keep temporarily because it delegates shared behavior. |

No deletion, removal or implementation migration occurs during WP01-A.
