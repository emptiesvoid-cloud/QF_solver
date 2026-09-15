# WP08-D active-set remediation — corrected M1/M2 report

## Decision

The reviewed active-set transition remediation was integrated under the Owner's
explicit authorization. Corrected M1 production, independent KKT reference,
and deterministic replay all passed. The single corrected M2 production run
failed closed at its first load increment with the frozen route. M3 was not
run. No formal WP08 points are awarded.

`FINAL_STATUS = M2_FAIL_CLOSED_OWNER_REVIEW_REQUIRED_BEFORE_ANY_M3`

## Provenance and integration

| Field | Value |
|---|---|
| Pre-remediation remote governing SHA | `7e46335f0f24de1943a951d561f70359ec6c36cd` |
| Remediation source SHA | `804a3e6ac12a451f04f2688d90766e7f61554682` |
| Remediation integration SHA | `e711661b24b6be22fb23136df838bcb7feef30fe` |
| M1 evidence commit | `3b2e3027b67468d886bbc5a94994674944719211` |
| M2 authorization/evidence base | `2ccdce2a334a1c29108acaf6405944bbba8af789` |
| Branch | `0.2.9-wp08d-m1-phase1` |
| WP08-D contract digest | `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a` |
| Governing policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |

The authorized production change is limited to the reviewed active-set
transition/convergence robustness and its internal telemetry. Mesh, loads,
material, contact parameters, tolerances, backend, fallback policy, and
acceptance thresholds were unchanged. WP05, WP06, and H4 were not touched.

## Targeted validation before integration

- Targeted tests: `54 passed in 4.32s`.
- Ruff: PASS.
- Compileall: PASS.
- JSON validation: PASS.
- `git diff --check`: PASS.
- Mypy: one inherited diagnostic remains at
  `src/solveur/contact/support.py:478`; the same diagnostic is present in the
  pre-remediation governing baseline and no new diagnostic was introduced.
- Full test suite: NOT RUN.

## Corrected M1

Artifact root:
`qualification/0_2_9/wp08d_phase1_remediation/`

| Check | Result |
|---|---|
| Production | PASS; 7/7 increments accepted |
| Fallback count | 0 |
| Force equilibrium | `4.8074305725478e-15` |
| Moment equilibrium | `7.806091302554032e-15` |
| Independent KKT/reference | PASS; `independent_numpy_kkt_return_map` |
| Production contact routines called by reference | `false` |
| Replay | PASS; relative tolerance `1e-12`, absolute floor `1e-14` |
| Replay structural solve | `false` |
| Active-set telemetry | Present for increment, inner iteration, transition cause, rollback and accepted/rejected state |

Reference deltas versus production were within the recorded machine-scale
values: selected displacement `4.683194093724405e-15`, reaction
`2.9124602944169367e-15`, moment `3.4278894313603834e-15`, and zero deltas for
normal contact, tangential contact, and dissipation.

## Corrected M2

Artifact root:
`qualification/0_2_9/wp08d_phase1_remediation/M2/`

The run used the frozen M2 route and exited with code `1`:

`NumericalConvergenceError: Frictional contact active set did not converge with direct or active-slip root iterations.`

Observed evidence:

- Accepted increments: `0/7`.
- Failure location: load increment `1`; the step was rejected and rollback was
  performed.
- Direct active-set path reached a stable normal active set `[3, 7, 11]` but
  did not satisfy the tangential convergence condition within the frozen 25
  active-set iterations.
- The explicit active-slip root path was then attempted and failed with
  `ROOT_SOLVE_FAILURE`, reporting that it could not resolve opening frictional
  contacts.
- No unauthorized fallback was enabled; manifest fallback policy remains
  `disabled` and fallback count is zero.
- No completed `result.json` or `raw.npz` exists because the run failed before
  final structural serialization. The flushed `manifest.json`,
  `progress.json`, `telemetry.jsonl`, `console.log`, and `console.err.log` are
  the authoritative fail-closed evidence.
- The M2 telemetry contains 42 valid events, including 30 contact-state
  events, direct active-set failure, active-slip root failure, step rejection,
  rollback metadata, and terminal analysis failure.

The technical classification is:

`ACTIVE_SET_ROBUSTNESS_LIMITATION_PERSISTS`

with terminal solver type `NumericalConvergenceError`. This is not a reason to
alter thresholds or parameters, and it does not authorize a retry or M3.

## Formal status and governance

| Item | Status |
|---|---|
| Corrected M1 production | PASS |
| Corrected M1 independent reference | PASS |
| Corrected M1 replay | PASS |
| Corrected M2 production | FAIL_CLOSED |
| Corrected M2 reference | NOT RUN — blocked by production failure |
| Corrected M2 replay | NOT RUN — blocked by production failure |
| M3 | NOT RUN — Owner review required |
| WP08-D formal points | `0/2` |
| WP08 formal points | `0/8` |
| Full test suite | NO |

Historical M1/M2 evidence remains preserved. This report records the corrected
run separately and does not rewrite the prior M2 failure. No further run is
authorized by this task.

