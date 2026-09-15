# WP08-D mixed open / active-slip remediation

## Status

`FINAL_STATUS = READY_FOR_OWNER_REVIEW`

This is a prospective contact-mechanics remediation only. No WP08-D
structural solve was launched. M1, M2, and M3 qualification runs were not
run, and no formal points are awarded.

## Frozen provenance

| Field | Value |
|---|---|
| Base SHA | `6ebbf92c961ae12d8198045a469b11fe866a7af0` |
| Branch | `0.2.9-wp08d-mixed-open-active-slip` |
| Implementation/test SHA before audit commit | `1a09f0350c9e3c785ca2c27ec26be745c5a9339a` |
| WP08-D contract digest | `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a` |
| Governing policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Final audit commit SHA | recorded by the commit containing this report |

The base was checked against `origin/0.2.9-unified-nonlinear` before branch
creation. The working tree was clean and no WP05, WP06, H4, WP07, or WP08
solve was active.

## Mechanical scope

`PRODUCTION_MECHANICS_CHANGED = YES`

The only production file changed is:

`src/solveur/contact/slip_root.py`

The correction is limited to the reviewed active-slip path:

1. Tangential unknowns are built only for frictional contacts in the normal
   active set with valid positive compression.
2. Frictional contacts outside that set remain `open`, contribute an exactly
   zero tangential force, and retain their incoming slip reference.
3. After the root solve, gaps, pressures, the proposed normal active set,
   finite-state checks, open-contact state, and scaled complementarity are
   verified.
4. If the post-root normal set changes, the candidate is rejected without
   committing references. The existing deterministic transition is applied
   and the root is rerun, with the existing limit of 25 active-set
   consistency iterations unchanged.
5. Telemetry now exposes the closed frictional subset, open frictional subset,
   tangential unknown dimension, post-root active set, transition cause, and
   stable/retry decision through the existing contact trace events.

No thresholds, mesh, loads, material, `mu`, `kt`, tolerances, backend, or
fallback policy changed. The old direct active-set route remains primary.

## Targeted validation

- Mixed open/closed active-slip unit test: PASS.
- Post-root normal-set change and no-intermediate-reference-commit test: PASS.
- Stable post-root acceptance and complementarity test: PASS.
- WP08-B/C/D, active-set, friction, rollback, runner, and related contact
  targeted tests: `104 passed in 5.43s`.
- Ruff: PASS.
- Targeted mypy for `slip_root.py`: PASS.
- Compileall: PASS.
- JSON validation: PASS.
- `git diff --check`: PASS.
- Full repository test suite: NOT RUN.

The existing authorization-fixture test was made branch-independent at the
test boundary only; production authorization behavior was not changed.

## Required gates and formal status

| Gate | Result |
|---|---|
| Mixed open/active root subset | PASS |
| Post-root normal-set change handling | PASS |
| Stable post-root acceptance | PASS |
| Structural M1/M2/M3 solves | NOT RUN |
| WP08-D formal status | `PREPARATION_ONLY` |
| WP08-D formal points | `0/2` |
| WP08 formal points | `0/8` |

Owner review is required before any structural execution or qualification
decision. This branch has not been merged or pushed.
