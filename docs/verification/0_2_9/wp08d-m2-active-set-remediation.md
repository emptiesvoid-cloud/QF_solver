# WP08-D M2 active-set remediation

## Scope

This record documents a minimal, local remediation for the active-set
robustness limitation identified by the archived WP08-D M2 run. It does not
reclassify or overwrite the original M2 evidence, and it does not authorize a
new M2 or M3 solve.

Historical evidence remains:

- `M2_STATUS = FAIL_CLOSED`;
- `FAILURE_CLASSIFICATION = NumericalConvergenceError`;
- message: `Frictional contact active set did not converge with direct or
  active-slip root iterations.`;
- accepted increments: `0/7`;
- prior classification: `ACTIVE_SET_ROBUSTNESS_LIMITATION`.

The original forensic record is preserved in
`qualification/0_2_9/wp08d_phase1/wp08d_m2_forensic_review.json` and its
corresponding controlled documentation.

## Minimal correction

The correction is limited to the production contact active-set path:

1. active-set transitions now retain the visited active-set signatures;
2. when a simultaneous proposed transition would repeat a visited signature,
   a deterministic one-contact pivot is selected in sorted contact-index
   order;
3. the existing gap/pressure tolerances, convergence criterion, direct
   solve, active-slip root fallback, state transaction and rollback semantics
   are unchanged;
4. direct and active-slip-root failure diagnostics are preserved separately;
5. contact increments emit `CONTACT_STATE` diagnostics and emit an explicit
   `STEP_REJECTED` event with the failure cause and rollback status.

The cycle-breaking branch does not accept an unconverged active set and does
not relax any threshold. It only changes the path after a repeated active-set
signature is detected.

Active-set correction commit: `653b1e8879ed33b9e03939d72167a1d6ab831399`.
Final telemetry-test commit: `25c3ab2fbbc0cded420b91d3a4428c1cc23e25ac`.

## M1 regression

One authorized M1 regression was run after the correction, using the existing
WP08-D M1 authorization and a separate temporary output directory:

`C:\Users\fari\AppData\Local\Temp\wp08d_m1_active_set_fix_regression_final\M1\`

The existing repository M1 evidence was not overwritten. The regression
completed with `PASS`, seven accepted load increments, zero active contacts,
and the frozen direct serial route. The following comparisons against the
existing M1 result were exact at the serialized-value level:

- `observables`;
- `equilibrium`;
- displacement vector.

The regression telemetry contained seven internal `CONTACT_STATE` events and
seven internal contact-increment `STEP_ACCEPTED` events (the stream also
contains seven wrapper-level step summaries). Each contact-state event carried
the step, active-set iteration and `convergence_cause`; no fallback or step
rejection occurred in this open-contact control.

M1 is a regression control only. It is not WP08-D structural qualification.

## Validation

- targeted WP08/contact regression tests: `54 passed`;
- Ruff on changed source and targeted test: `PASS`;
- targeted compileall: `PASS`;
- mypy: one pre-existing diagnostic remains in `support.py` at the
  `history[0].get("min_gap", 0.0)` conversion; no new diagnostic was added
  by this remediation;
- M2: **not rerun**;
- M3: **not run**;
- full test suite: **not run**.

## Decision boundary

The M1 result demonstrates numerical non-regression and the new diagnostic
path, but it does not demonstrate M2 recovery. Owner review is required
before any M2 or M3 execution. WP08-D remains unqualified and its formal
points remain `0/2`; WP08 remains `0/8`.
