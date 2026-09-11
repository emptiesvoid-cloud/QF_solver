---
doc_id: DOC-029-WP01-009
revision: 0.1
status: implementation_migration
applicable_version: 0.2.9-development
---

# WP01-D adaptive and arc-length continuation migration

## Scope and boundary

WP01-D moves accepted-step ownership for adaptive load control and
arc-length continuation to `UnifiedContinuationController`. The controller
owns the detached trial, composite commit, rollback proof, retry diagnostics
and cutback/radius policy boundary. The standard Newton and arc-length
correction kernels remain separate numerical kernels.

The geometric stateless adaptive helper is included so the public geometric
nonlinear route does not retain a second accepted-state transaction model.
FEM kernels, constitutive equations, contact formulations and checkpoint
persistence format were not changed.

The inherited adaptive penalty-contact case remains
`NOT_SUPPORTED_AT_BASELINE`: its existing `analysis.load_path` is not
compatible with `adaptive_load_steps`. No contact capability is promoted by
this result.

## Atomic lifecycle

Each accepted increment follows:

```text
accepted composite state
  -> begin detached trial
  -> correction kernel and admissibility checks
  -> commit all state families once
```

A failure follows:

```text
trial failure
  -> rollback and digest verification
  -> retry/cutback or explicit terminal failure
```

The accepted state contains displacement, load factor, material state,
structural contact state, continuation state and accepted-increment metadata.
For arc-length, `previous_du`, `previous_dlambda`, radius and load-scale
variables are accepted continuation state. A radius reduction for the next
trial is controller policy; it does not mutate the preceding accepted state.
Checkpoint saves remain after composite acceptance and the persistence schema
is unchanged.

## Baseline equivalence

The frozen baseline is commit
`9bc07ea5d4e7878702fca58ef7e90af53b039247`. The complete machine-readable
records are `qualification/0_2_9/wp01_d_baseline.json` and
`qualification/0_2_9/wp01_d_post_migration.json`.

All supported adaptive and arc-length cases have identical state digests,
accepted-step counts, rejection counts, Newton counts, load-factor histories
and arc-radius histories before and after migration. The comparison uses
relative tolerance `1e-9` and absolute floor `1e-12`. The two controlled
adaptive failure cases preserve both their failure reasons and their accepted
state digests.

## Lifecycle inventory

- `NonlinearStaticSolver` fixed and adaptive load control use the common
  accepted-state controller.
- `solve_full_newton` remains a compatibility adapter to
  `UnifiedNewtonEngine`.
- `solve_adaptive_full_newton` remains a compatibility adapter but now uses
  the common controller; this covers the public geometric adaptive route.
- `solve_arc_length_correction` remains a specialized augmented correction
  kernel and does not publish accepted state.
- `FrictionlessActiveSetSolver` belongs to the linear-static contact path,
  not the public nonlinear global lifecycle.
- Frictional active-set, fixed-point, slip-root and semi-smooth paths remain
  research/compatibility paths and are not promoted or migrated here.

## Prospective gate result

| Gate | Status | Evidence boundary |
| --- | --- | --- |
| G01 | Pass with research boundary | All public fixed/adaptive/arc accepted-state lifecycles use the common controller; research compatibility loops remain outside it. |
| G02 | Pass | Standard and augmented correction kernels share the transaction boundary. |
| G03 | Pass | Rejected trials preserve the complete accepted digest. |
| G04 | Pass | Contributions and correction kernels do not publish global state. |
| G05 | Pass, bounded | J2 targeted regression is unchanged; no maturity promotion. |
| G06 | Pass, bounded | TET4/HEX8 geometric targeted regression is unchanged. |
| G07 | Pass, bounded | Penalty composition targeted regression is unchanged; adaptive contact remains baseline-limited. |
| G08 | Pass | Failure reason, retry class and rollback diagnostics are deterministic. |
| G09 | Pass | No maturity registry or public claim changed. |
| G10 | Pass with research boundary | Compatibility adapters delegate; remaining research loops are explicitly out of public nonlinear ownership. |

WP01 remains `CONTINUATION_MIGRATION` with **0 / 12** points awarded.
`OD-029-01` remains **OPEN**. No full repository suite was run.

## Validation note

Ruff, compileall and all focused runtime groups passed. The repository’s
existing mypy invocation still reports mixin/typing diagnostics; comparison
with the start commit shows no WP01-D-added diagnostics (34 current versus 38
at baseline). This is recorded as technical debt, not hidden as a green type
gate.
