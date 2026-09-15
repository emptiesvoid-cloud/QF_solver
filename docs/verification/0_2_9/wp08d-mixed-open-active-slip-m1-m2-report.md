# WP08-D mixed open / active-slip M1–M2 requalification

## Scope and provenance

The reviewed mixed open/active-slip remediation was integrated from
`0.2.9-wp08d-mixed-open-active-slip` at
`78179c793950c79e00877c9346bb5a69891d5cf7` into the execution branch with
merge commit `4b891aea040bc900d290fe3cc3de696126656ee7`. The governing branch
was at `6ebbf92c961ae12d8198045a469b11fe866a7af0` before integration and was
advanced normally; no force push was used.

The only production mechanics change is the authorized mixed open/closed
active-slip subset and post-root normal-set consistency logic in
`src/solveur/contact/slip_root.py`. Thresholds, mesh, loads, material,
contact parameters, tolerances, solver backend and fallback policy were not
changed. WP05, WP06 and H4 were not touched.

Contract digest:
`d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`

Governing policy digest:
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`

## Corrected M1

M1 production completed with `PASS`, all 7/7 frozen increments accepted and
zero unauthorized fallback. Force and moment equilibrium relative errors were
`4.8074305725478e-15` and `7.806091302554032e-15`. All four contacts remained
open, with zero tangential force; the contact-state telemetry was emitted, but
the mixed subset was not exercised by this M1 state.

The independent NumPy KKT/return-map reference completed with
`PASS_REFERENCE`. Production/reference deltas were:

- displacement: `4.683194093724405e-15`;
- reaction: `2.9124602944169367e-15`;
- reaction moment: `3.4278894313603834e-15`;
- cumulative dissipation: `0`.

Reference equilibrium errors were `6.2477991893329175e-15` for force and
`1.1073971008993349e-14` for moment.

The deterministic production replay completed with `PASS`; terminal status,
mesh identity, displacement, dissipation and equilibrium comparisons all
matched under the existing replay tolerances.

## Corrected M2

M2 used the frozen 4×2×2 TET4 contact mesh, seven load increments, serial
direct backend, no fallback, and unchanged contact parameters. Increments 1
and 2 were accepted. Increment 3 was rejected and rolled back after the
direct active-set route reached its existing 25-iteration limit and the
active-slip root subsequently failed. The run ended with:

`NumericalConvergenceError: Frictional contact active set did not converge
with direct or active-slip root iterations.`

The failure is preserved as `FAIL_CLOSED`; no retry or tuning was performed.
The raw M2 telemetry contains 109 JSONL events and records the mixed state:

- normal active set: `[3, 7, 11]`;
- closed frictional subset passed to the root: `[3, 7, 11]`;
- open frictional subset excluded from the root:
  `[0, 1, 2, 4, 5, 6, 8, 9, 10]`;
- tangential unknown dimension: `6`;
- post-root normal set stable for the successful mixed attempts;
- step 3 ended with `ROOT_SOLVE_FAILURE` and rollback.

Accepted increments: `2/7`. M2 has no final `result.json` because the runner
failed closed before a converged result could be serialized; its manifest,
progress file, JSONL telemetry and console logs are preserved.

## Decision

`M3_STATUS = NOT_RUN_OWNER_REVIEW_REQUIRED`.

No formal points are awarded:

`WP08D_FORMAL_POINTS = 0/2`  
`WP08_FORMAL_POINTS = 0/8`

The evidence is ready for Owner review before any further M3 authorization.

