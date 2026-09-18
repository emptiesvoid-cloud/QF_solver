---
doc_id: DOC-029-WP06D-R2-GUARD-HARDENING
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.9-development
---

# WP06-D R2 execution-guard hardening audit

## Outcome

The WP06-D preparation guard now independently queries Git and rejects
caller-supplied provenance that disagrees with the repository. Its tests use
temporary committed Git repositories rather than synthetic SHA/branch values.
This closes a safety-preparation weakness, but **does not make WP06-D ready to
execute**: there is still no frozen R2 contract and no dedicated R2 runner
invoking this guard.

No structural solve, independent reference solve, replay, merge, or push was
performed. The stale R1 entrypoint remains quarantined.

## R1 evidence diagnosis retained

The historical M2 R1 evidence remains `FAIL_CLOSED` and unchanged:

- The declared monitor is `q = -mean(UZ at nodes 2,3,4)`. The quarantined R1
  runner recorded the single node-4 control displacement instead. Static
  source inspection shows `arc_length_control_dof` feeds the recorded scalar
  diagnostic; this mismatch invalidates the declared path observable but does
  not, by itself, establish that the mechanical continuation equations
  changed.
- The archived R1 path has 80 accepted M2 steps with strictly increasing
  load factor; no limit point was demonstrated inside that frozen horizon.
  The new R2 work must not silently extend the horizon or alter continuation
  parameters to force a turning point.
- M2 moment-equilibrium relative error was `2.438196359642231e-05` against
  `1e-8` (about 2,438 times the gate). This is not a numerical-floor pass.
- Full accepted displacement states were not retained in the authoritative
  R1 raw package, so the per-state support moment could not be reconstructed
  from that package. The cause of the moment imbalance remains unresolved;
  no mechanical correction is justified from the available R1 evidence.
- The quarantined runner's limit-point helper detects a sign change in load
  factor increments but does not implement the contract's additional
  monitored-path continuity check. R2 needs a separately tested,
  contract-matched evaluator.

These are evidence/runner defects and unresolved qualification gates, not
proof that a particular production mechanics change will make D pass.

## Guard changes

`scripts/prepare_wp06d_requalification.py` now:

- reads the actual Git worktree root, branch, `HEAD`, and dirty status itself;
- requires supplied branch/SHA values to match the queried repository state;
- requires the frozen contract to be tracked and committed;
- accepts the Owner grant only from outside the repository, so the grant does
  not silently dirty or self-bind the reviewed source tree;
- requires the explicit `WP06D-R2` revision and exact contract, branch, SHA,
  policy digest, and M1/M2/M3 grant fields;
- restricts output to a new child under
  `qualification/0_2_9/wp06d_r2_runs/`, refusing reuse and symlink output
  paths.

The guard is still a validator helper, **not an effective execution gate**,
because no R2 runner calls it yet. Its passing synthetic Owner-grant fixture
tests exercise only validation logic; they are not an Owner authorization.

## Verification and provenance

```text
BRANCH = codex/wp06-score-requalification
GUARD_IMPLEMENTATION_SHA = e5b821af2b2a93aade2d7d8119b5dc2494e50892
WP06_OWNER_AWARD = 4/8 (A 1/1, B 1/1, C 2/2)
LOCAL_CONSOLIDATED_LEDGER = 70/100
WP06D_R2_EXECUTION_AUTHORIZED = NO
R2_CONTRACT = NOT_CREATED
R2_RUNNER_INTEGRATION = NOT_CREATED
STRUCTURAL_SOLVES = NO
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

Targeted tests: **30 passed** across
`tests/unit/test_wp06_premerge_tools.py` and
`tests/unit/test_wp06d_structural_limit_point_contract.py`. Ruff, targeted
mypy, compileall, JSON validation, and `git diff --check` passed. Documentation
generation tests: **17 passed, 2 skipped**. The full repository suite was not
run.

The governing and remote branch remain at
`915d0d4e8a8df462d7928f77b96f4480f53fbae7`; the 70/100 ledger is local to the
isolated WP06 branch and has not been merged or pushed.

## Required next work; no solve authorized

1. Draft a new R2 contract that binds the accepted current-source/policy
   lineage while preserving the R1 geometry, material, load, mesh hierarchy,
   limits, and thresholds. Keep the R1 contract and all R1 evidence immutable.
2. Implement a dedicated R2 runner that invokes the self-checking guard before
   any solve, uses only new SHA-specific output, records the frozen mean-crown
   monitor, and losslessly archives every accepted displacement state.
3. Independently reconstruct force and moment equilibrium per accepted state;
   implement and test limit-point/path-continuity gates against the contract.
4. Add no-solve tests for fail-closed dependencies and mocked runner behavior.
5. Present the bound R2 contract and runner for Owner review. Structural
   execution remains prohibited until a separate explicit authorization is
   granted for the exact final branch/SHA/contract/policy digest.

```text
WP06D_R2_STATUS = PREPARATION_ONLY_GUARD_HARDENED
WP06D_FORMAL_POINTS = 0/2
NEXT_GATE = R2 CONTRACT + DEDICATED RUNNER, THEN SEPARATE OWNER EXECUTION AUTHORIZATION
```
