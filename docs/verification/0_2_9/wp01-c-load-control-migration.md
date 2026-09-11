---
doc_id: DOC-029-WP01-008
revision: 0.1
status: implementation_migration
applicable_version: 0.2.9-development
---

# WP01-C fixed load-control migration evidence

## Scope and baseline

WP01-C migrates the fixed load-control Full Newton routes onto the
formulation-neutral `UnifiedNewtonEngine`. The frozen baseline is
`ad7ee6bd469aa770929fd7a1d46f56da5e9bba1a`; the before/after records are
`qualification/0_2_9/wp01_c_baseline.json` and
`qualification/0_2_9/wp01_c_post_migration.json`.

The migration changes driver plumbing only. FEM kernels, constitutive
equations, element formulations, 0.2.8 evidence and maturity records are
unchanged.

## Migrated paths

- `solve_full_newton` is now a compatibility adapter over the authoritative
  engine; it no longer owns a second Newton iteration loop.
- `NonlinearStaticSolver._solve_load_step` uses the same engine and keeps
  material trial states detached until increment acceptance.
- `GeometricNonlinearStaticSolver` reaches the same lifecycle through its
  existing `solve_full_newton` delegation.
- Frictionless penalty contact remains a composable, stateless contribution;
  its formulation was not changed.

Adaptive cutback ownership, arc-length, active-set/frictional contact,
checkpoint persistence and PETSc/MPI remain intentionally unmigrated.

## Numerical equivalence

The frozen comparison uses relative tolerance `1e-9` with absolute floor
`1e-12`.

| Case | Result | Max displacement delta | Iterations before/after |
| --- | --- | ---: | ---: |
| Small-strain J2 | PASS | `0` | `1 / 1` |
| Geometric TET4 | PASS | `1.3552527156068805e-20` | `3 / 3` |
| Geometric HEX8 | PASS | `1.0587911840678754e-22` | `3 / 3` |
| Penalty contact | PASS | `0` | `5 / 5` |
| Geometric + penalty contact | PASS | `1.3552527156068805e-20` | `3 / 3` |

The singular Full Newton failure remains `SINGULAR_TANGENT` before and after
migration. The unified path adds a backend diagnostic but does not change the
failure reason; replay metadata is deterministic.

## Transaction evidence

- Accepted increments publish one composite commit.
- Intermediate Newton iterations do not commit material state.
- Rejected increments and line-search rejection leave the accepted state
  unchanged by digest.
- Load factor advances only after accepted increment publication.
- Geometric and J2 routes use the same lifecycle adapter path.

The migration tests T19–T30 pass (`12 passed`). The full targeted command list
and counts are recorded in
`qualification/0_2_9/wp01_c_migration_evidence.json`.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G01 | Partial pass | Fixed load-control paths use one engine; arc-length and research loops remain. |
| G02 | Pass for migrated routes | Material/geometric/penalty contributions compose through the common adapter. |
| G03 | Pass | Atomic rollback/commit evidence passes. |
| G04 | Pass | Contributions cannot independently commit composite state. |
| G05 | Pass, bounded | J2 targeted equivalence passes; this is not a new maturity claim. |
| G06 | Pass, bounded | TET4/HEX8 targeted equivalence passes; geometric route remains research-only. |
| G07 | Pass, bounded | Penalty composition equivalence passes within the exercised scope. |
| G08 | Pass | Failure reason and replay diagnostics are deterministic. |
| G09 | Pass | No maturity or public claim changed. |
| G10 | Partial pass | Compatibility adapter remains while later paths are unmigrated. |

WP01 remains `LOAD_CONTROL_MIGRATION` with **0 / 12** points awarded.
`OD-029-01` remains **OPEN**. No full repository suite was run.
