# QF Solver 0.2.9 — WP08-D Phase-1 runner freeze

## Scope

This record freezes execution tooling for the bounded WP08-D contract. It does
not claim structural qualification and it does not contain a structural,
contact, independent-reference, or replay solve.

The runner is based on governing SHA
`28cf9dd1886b72c6c7c9fc720dc778eddfce4441` on branch
`0.2.9-wp08d-phase1-runner`. The frozen contract digest is
`d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a` and the
governing policy digest is
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`.

## Implemented tooling

* `scripts/run_wp08d_frictional_structural.py` accepts M1, M2, or M3.
* `scripts/wp08d_phase1_common.py` reuses the existing deterministic TET4
  mesh and consistent T3 load preparation, writes immediate-flush progress,
  JSONL telemetry, raw NPZ, result, and hash manifests, and provides an
  evidence-only replay comparator.
* `scripts/wp08d_independent_kkt_reference.py` is a NumPy-only KKT plus
  regularized Coulomb return-map harness. It has no solver-package or
  production-contact imports and is not executed by this freeze.
* `qualification/0_2_9/wp08d_phase1/wp08d_phase1_artifact_schema.json`
  freezes the M1/M2/M3, independent-reference, and replay artifact layout.

The production model builder is imported lazily and is reachable only after
the explicit execution guard. The default CLI mode fails closed with
`UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED`. A versioned Owner authorization
file must contain the exact governing SHA, branch, scope, and authorization
token before `--execute-phase1` can import or invoke the production solver.

## Validation

The targeted WP08-B/WP08-C/WP08-D and Phase-1 tooling campaign passed 51
tests. Ruff, targeted mypy, compileall, JSON validation, and `git diff --check`
are required release checks for this freeze. No full repository suite was run.

The dry-run path checks only contract digest, governing policy digest,
deterministic mesh counts/orientation/coverage, consistent load resultant and
moment, and the artifact layout. It performs no contact solve, structural
solve, independent reference solve, or replay solve.

## Frozen status

```text
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
SOLVER_PARAMETERS_CHANGED = NO
FALLBACK_CHANGED = NO
STRUCTURAL_SOLVES_RUN = NO
REFERENCE_SOLVES_RUN = NO
REPLAY_RUN = NO
WP08D_FORMAL_STATUS = PREPARATION_ONLY
WP08_FORMAL_POINTS = 0/8
NEXT_STEP = OWNER AUTHORIZATION REQUIRED FOR ONE M1 PHASE-1 EXECUTION
```

