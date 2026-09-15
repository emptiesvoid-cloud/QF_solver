---
doc_id: DOC-029-WP08B-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-B — frictional identities, zero-pressure safety and rollback

**Status:** `PASS_CANDIDATE_WITH_LIMITATIONS` — technical evidence only; no
WP08 point is awarded and no structural qualification claim is made.

**Historical evidence source:** `20c6d82e18bdf90fa3c3b0b2098339e399026439`
on `0.2.9-wp08-prep`, repository `emptiesvoid-cloud/QF_solver`. The R1
working change is the owner-authorized narrow correction in
`src/solveur/contact/support.py::_friction_update`.

The controlled reconstruction carries this historical result on
`0.2.9-wp08-controlled-integration` from governing base
`7b93e71bab06a0e58108bd2479cd46808d533b67`; the historical result is not
silently represented as a fresh structural qualification.

## Immutable R0/R1 history

R0 reproduced a real bug before this correction. With an active frictional
contact, `prior_state = slip`, `pressure = 0`, and a zero tangential trial,
the existing hysteresis selected the slip branch and evaluated
`limit * trial / trial_norm` as `0 / 0`. The force and slip reference became
non-finite.

R1 is the single authorized correction. When that existing slip branch has an
exactly zero trial norm, it keeps the `slip` state, emits a zero tangential
force, and sets the next slip reference to the current relative tangential
displacement. This avoids a directionless projection and prevents the stick
tangent from being added at zero Coulomb capacity. A finite-state guard raises
the existing typed `NumericalConvergenceError` with
`NAN_DETECTED` for any other non-finite force or reference; arbitrary values
are not sanitized to zero.

No friction coefficient, penalty/tangential stiffness, activation criterion,
hysteresis threshold, search mode, active-set algorithm, restart behavior,
Newton policy or line-search policy was changed.

## Bounded scope and frozen thresholds

The evidence covers the existing serial direct, small-displacement,
node-to-triangle, fixed-initial-face/normal static route with a positive
friction coefficient and positive tangential stiffness. The state vocabulary
remains `open`, `frictionless`, `stick`, `slip`.

The frozen WP08-B checks are:

| Check | Threshold |
| --- | --- |
| force/vector identity | relative `<= 1e-12`, absolute floor `1e-14` |
| Coulomb radius | relative `<= 1e-12` |
| slip direction cosine error | `<= 1e-12` |
| rollback digest | exact equality |
| replay | relative `<= 1e-12`, absolute floor `1e-14` |
| required values | finite |

At zero pressure the Coulomb capacity is exactly zero. The authorized branch
therefore has `t = [0, 0]` and does not add a stick tangent.

## Zero-pressure regression and nearby cases

The direct `_friction_update` regression uses the real contact operator from
the existing tiny fixture. All cases were evaluated with warning-as-error
floating-point handling where applicable.

| Case | Initial condition | Result |
| --- | --- | --- |
| A | prior `slip`, pressure `0`, zero increment | `slip`, force `[0, 0]`, reference `[0, 0]`, finite |
| B | prior `slip`, pressure `0`, positive tangential increment | `slip`, force `[0, 0]`, reference follows relative displacement, finite |
| C | prior `slip`, pressure `0`, reversed increment | `slip`, force `[0, 0]`, reference follows relative displacement, finite |
| D | zero-pressure free slip followed by pressure `100` at the same displacement | `stick`, force `[0, 0]`; no stored artificial force |

For the positive and reversed increments the local relative displacements
were `[0.1375, 0]` and `[-0.1375, 0]`, respectively. Repeating the exact
zero-pressure case produced identical state, force, relative displacement and
reference arrays.

The original R0 observation is retained as historical evidence: before R1,
the zero/zero projection emitted a non-finite force and reference. After R1,
the same case is finite and fail-safe.

## Non-degenerate friction identities

The existing positive-pressure fixture was replayed through the real solver.
For the positive-pressure stick case, the implemented force equals
`k_t (relative - reference)` with measured relative identity error `0.0` and
an unchanged zero reference. For the positive-pressure slip case, pressure is
`100`, `mu` is `0.5`, and the Coulomb limit is `50`; the measured radius,
direction and reference-update errors are all `0.0` in the deterministic
double-precision result.

The frozen load history contains stick, forward slip, reversal and reverse
slip. Its states are:

```text
stick, stick, slip, slip, slip, slip, slip
```

The tangential force sequence is `0`, `36.36363636363637`, `50`, `-50`,
`-50`, `-50`, `50`. Two complete solves produced identical load-step records
and displacement arrays. Existing unit and analytical friction V&V tests
also remained green.

## Rollback, commit and re-evaluation

`StateTransaction` remains the state owner for the friction solver's
per-contact slip-reference array. An injected `CONTACT_UPDATE_FAILURE` after
writing a trial reference rolls back to the exact committed digest:

```text
before / after rollback
c7a542a4ab9c7a0afbc6f7f741e71ecca582c23b4a62dffa543dcd5ab2866097
```

The rejected trial is discarded and the committed array remains zero. A
separate commit test verifies `S0 -> S1`, followed by a rejected later trial,
returns exactly to the accepted `S1` digest. Re-evaluating the same accepted
input after rollback returns identical arrays and state classification.

## Fail-closed boundary and limitations

The new guard proves that a non-finite friction state reaches the typed
`NAN_DETECTED` numerical error path. Public JSON input continues to reject
negative and non-finite friction coefficients. Direct construction of the
historical `FrictionlessContact` dataclass can still bypass that schema-level
validation; this is a separate input-validation gap and is intentionally not
fixed in R1.

Friction-specific accepted-state restart remains `NOT_QUALIFIED`; only the
bounded in-solve transaction and deterministic re-evaluation are evidenced
here. No structural, mesh-refinement, external, common-nonlinear-route or
updated-search friction qualification is claimed. Updated-search friction
remains `RESEARCH_ONLY`/rejected by the existing route guard.

## Validation record

The targeted WP08-B suite contains 17 tests and passed. The existing
frictional unit and cheap analytical V&V suites passed 27 tests together with
the affected frictionless-contact tests. No structural solve, external solver
run, heavy solve or full test suite was executed. The production change is
classified exactly as:

```text
PRODUCTION_MECHANICS_CHANGED = YES
CONTACT_MECHANICS_CHANGED = YES
CHANGE_CLASS = OWNER_AUTHORIZED_BUGFIX_ONLY
MATURITY_CHANGED = NO
```

WP08-A remains a technically frozen candidate at `1/1`; WP08-B remains
`0/2` formal points pending Owner review and later integration/revalidation.
