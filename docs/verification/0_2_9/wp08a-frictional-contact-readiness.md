---
doc_id: DOC-029-WP08A-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-A — frictional-contact readiness audit

**Status:** `PREPARATION_ONLY` — no WP08 point is awarded and no structural
qualification claim is made.

**Historical audit source:** `2c52bf8196a7d47d14ce1784290580160de26590` on
`0.2.9-wp08-prep`, repository `emptiesvoid-cloud/QF_solver`.

**Controlled reconstruction:** this record is carried on
`0.2.9-wp08-controlled-integration` from governing base
`7b93e71bab06a0e58108bd2479cd46808d533b67`; the historical evidence was not
silently regenerated.

This record audits the implementation that is actually present on the
pre-integration baseline. Existing documentation and historical V&V records
are treated as evidence of their recorded scope only; source behavior takes
precedence when the two differ.

## Executive conclusion

QF Solver contains a real but bounded frictional extension behind the legacy
`FrictionlessContact` data class. A positive per-contact coefficient activates
a regularized Coulomb return map in the serial, direct, small-displacement
`linear_static` active-set solver. The extension has useful analytical and
unit-level evidence for open, stick, slip, reversal and load-history memory.

It is not a general friction implementation. The common nonlinear/geometric
driver deliberately rejects frictional contact; updated-search/finite-sliding
with friction is rejected; there is no qualified friction-specific checkpoint
or restart; and the global structural tangent, energy decomposition and
external equivalence are not yet established. The correct current maturity is
therefore `RESEARCH`/experimental, with WP08 qualification still required.

## Implementation map

| Item | Observed implementation | Source location |
| --- | --- | --- |
| `FRICTION_FORMULATION` | Regularized Coulomb extension selected by `friction_coefficient > 0`; normal constraint remains Lagrange active-set. | `src/solveur/contact/entities.py::FrictionlessContact`; `src/solveur/contact/solver.py::FrictionlessActiveSetSolver` |
| `NORMAL_FORMULATION` | Node-to-triangle unilateral contact, signed gap, fixed initial geometry for frictional solves, exact normal multiplier. | `src/solveur/contact/entities.py::FrictionlessContact.face_geometry`; `src/solveur/contact/support.py::_proposed_active` |
| `TANGENTIAL_LAW` | Elastic tangential predictor followed by projection to `mu * max(pressure, 0)` when sliding. | `src/solveur/contact/support.py::_friction_update` |
| `REGULARIZATION` | Per-contact positive `tangential_stiffness` supplies the elastic stick predictor; it is not a smooth universal Coulomb regularization. | `src/solveur/contact/support.py::_friction_system`, `::_friction_update` |
| `STICK_CRITERION` | `||k_t(relative-slip_reference)|| <= mu*max(p,0) + contact_friction_tolerance`, except for prior-slip hysteresis. | `src/solveur/contact/support.py::_friction_update` |
| `SLIP_CRITERION` | Otherwise project the trial tangential force to the Coulomb radius and update the slip reference. | `src/solveur/contact/support.py::_friction_update` |
| `FRICTION_COEFFICIENT_SOURCE` | Scalar `FrictionlessContact.friction_coefficient` from the input contact; JSON input is checked by `ContactSchemaValidator`. | `src/solveur/contact/entities.py`; `src/solveur/io/contact_schema.py::ContactSchemaValidator.validate` |
| `TANGENTIAL_STATE_VARIABLES` | Two-component `slip_references` per expanded contact, local tangential force/displacement, and `open`/`stick`/`slip` labels. | `src/solveur/contact/support.py::_ContactOperator`, `::_FrictionIncrementState` |
| `STATE_OWNER` | `FrictionlessActiveSetSolver._solve_with_friction`; the state is local to one static load-path solve. | `src/solveur/contact/solver.py::_solve_with_friction` |
| `ROLLBACK_OWNER` | `StateTransaction` around the committed slip-reference array; failed `NumericalConvergenceError` rolls back the trial. | `src/solveur/core/nonlinear/material_state.py::StateTransaction`; `src/solveur/contact/solver.py` |
| `COMMIT_POINT` | After a load increment converges, the returned slip references are assigned to the transaction trial and committed before the next increment. | `src/solveur/contact/solver.py::_solve_with_friction` |
| `SEARCH_MODE_SUPPORT` | Frictional route requires initial search; `updated` is explicitly rejected. | `src/solveur/contact/solver.py::FrictionlessActiveSetSolver.solve`; `src/solveur/mesh/contact_validation.py` |
| `FINITE_SLIDING_SUPPORT` | Frictionless common penalty only; friction + finite sliding is explicitly rejected. | `src/solveur/contact/support.py::_finite_sliding`; `src/solveur/mesh/contact_validation.py` |
| `TANGENT_TYPE` | Stick: branch-local elastic tangent. Slip: force-projection algorithm with a frozen-branch root Jacobian fallback, not a qualified assembled global tangent. Transition: nonsmooth. Open: zero. | `src/solveur/contact/support.py::_friction_system`; `src/solveur/contact/slip_root.py::consistent_jacobian` |
| `DISSIPATION_TRACKING` | Local work from slip-reference updates is accumulated as `cumulative_local_dissipation`; only internal positivity checks exist. | `src/solveur/contact/support.py::_dissipation_increment`; `src/solveur/contact/solver.py::_solve_with_friction` |
| `RESTART_SUPPORT` | No friction-specific accepted-state serialization or end-to-end restart qualification. v1 migration rejects stateful contact history; common nonlinear restart path rejects friction. | `src/solveur/core/nonlinear/checkpoint.py::build_state_topology`, `::migrate_v1_checkpoint`; `src/solveur/core/nonlinear/solver.py` |
| `DIAGNOSTICS_AVAILABLE` | Contact method, gaps, pressure, active set, tangential state/force/displacement, friction limit, basis, iteration history, convergence reason and local dissipation. | `src/solveur/contact/support.py::_details`, `::_contact_convergence_diagnostics`; `src/solveur/contact/solver.py` |

The public class name is historical and misleading: `FrictionlessContact`
also carries the optional friction parameters. No rename is proposed in this
readiness task because that would be an API change.

## Route matrix

The entries below separate the normal frictionless variants from the
frictional extension. `IMPLEMENTED` describes code availability, not Owner
qualification or release maturity.

| Route | Frictionless active-set | Frictionless penalty | Frictional route | Assessment |
| --- | --- | --- | --- | --- |
| `linear_static` | `IMPLEMENTED` — serial direct node-to-triangle Lagrange active set | `UNSUPPORTED_ROUTE_LEVEL` — the common penalty contribution is nonlinear-route scoped | `IMPLEMENTED_BOUNDED` — same direct active-set solver with fixed initial search, `mu` and `k_t` | Bounded research/experimental only |
| `geometric_nonlinear_static` | `UNSUPPORTED` | `IMPLEMENTED_BOUNDED` common frictionless penalty, including its separate updated-search option where configured | `UNSUPPORTED_EXPLICIT` — validation error | No frictional route |
| `nonlinear_static` with small-strain or geometric/J2 material branch | `UNSUPPORTED` as an active-set route | `IMPLEMENTED_BOUNDED_WHEN_ROUTE_SCOPE_PERMITS` | `UNSUPPORTED_EXPLICIT` — common nonlinear path is frictionless only | No frictional route |
| Combined material + geometric nonlinear contact | `PARTIAL` for the frictionless common composition, subject to the route's own bounded scope | `PARTIAL` | `UNSUPPORTED` | No unified frictional composition |
| `transient_dynamic` / explicit dynamic | `UNSUPPORTED` | `UNSUPPORTED` by contact validation | `UNSUPPORTED` | No contact dynamics route |
| `modal` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | Contact is not a modal capability |
| `linear_buckling` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | Contact is not a buckling capability |
| `harmonic` | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | No frictional harmonic route |

`material_nonlinear` is not a separate public analysis identifier in this
baseline; it is represented by `nonlinear_static` kinematic/material branches.
The positive-friction rejection is therefore intentional and not silently
falling back to a frictionless solve.

## State transaction audit

| State | Trial mutation | Accept/commit | Reject/rollback | Restart serialization |
| --- | --- | --- | --- | --- |
| `slip_references[contact, tangent]` | `_friction_update` works on a copy; `_iterate_friction_increment` keeps the beginning-of-increment reference frozen during iterations. | `_solve_with_friction` commits only the converged return-map references after each load increment. | A `NumericalConvergenceError` calls `StateTransaction.rollback()`; committed references are protected by a digest. | Not serialized by the friction solver and not placed in common `NonlinearState.contact_state`; therefore not qualified. |
| Tangential state labels and forces | Local values returned in `_FrictionIncrementState`; no persistent mutation during a trial. | Recomputed and recorded in final/load-step details. | Discarded with the failed local increment. | Diagnostics only; not a restart state contract. |
| Normal active set/multipliers | Local outer-iteration variables. | Recomputed for the next independent static solve/increment. | No separate persistent normal-contact transaction. | Not a mid-solve restart state. |
| Selected face/normal/projection | Derived from immutable model coordinates for initial-search friction. | Recomputed from the same model on a fresh solve. | No accepted geometry mutation in the frictional initial-search route. | No frictional topology/configuration digest. |

This is a useful local rollback boundary, but it is not proof of a complete
common-driver transaction. Existing tests cover load-history memory and
positive accumulated work; they do not inject a rejected friction increment
and compare pre/post digests. That is a WP08-B/E requirement.

The repository also contains a formulation-neutral `NonlinearState` and
`NonlinearStateTransaction` with contact-state slots and finite/digest checks.
The frictional static solver does not use that common transaction because the
common nonlinear driver rejects positive friction. The two state mechanisms
must not be conflated.

## Coulomb law and edge cases

For a closed frictional contact, the implementation computes

```text
p                 = -normal_lagrange_multiplier       (compression positive)
t_trial           = k_t * (relative_tangent - slip_reference)
t_limit           = mu * max(p, 0)
stick              if ||t_trial|| <= t_limit + tolerance
slip               otherwise, t = t_limit * t_trial / ||t_trial||
slip_reference_new = relative_tangent - t / k_t
```

The normal gap is the signed fixed-face gap. A contact is newly active when
`gap < -gap_tolerance`; an active contact is retained within the tolerance
only while its pressure is not tensile. Tangential basis vectors are built
from the selected face and are orthonormalized against the face normal.

Observed edge-case policy:

| Case | Current behavior / evidence status |
| --- | --- |
| `mu = 0` | `has_friction` is false, so the active-set normal/frictionless path is selected. This is a formulation switch, not a frictional zero-coefficient proof. |
| `mu > 0` without positive `tangential_stiffness` | Rejected by JSON schema and again by `_operator`; explicit `InputValidationError`. |
| Negative or nonfinite `mu` | JSON input validation rejects it as non-negative finite. Direct construction of the internal dataclass bypasses that schema, so direct-construction validation remains a boundary to cover before any promotion; no source fix is made here. |
| Opening contact | `_friction_update` returns `open` and zero tangential force; the previous slip reference is retained for a later close. |
| Zero normal pressure | Coulomb limit is zero; undefined tangential directions or an impossible active-slip root fail through the route's numerical error path rather than producing a qualified result. Dedicated WP08 negative evidence is still missing. |
| Reversal | Positive/negative reversal and a cyclic load-history memory case are covered by the analytical campaign/unit tests. A general structural reversal claim is not justified. |
| Very small tangential increment | Classified by the tolerance and the prior-slip hysteresis branch; no dedicated transition-boundary V&V exists. |

The regularization is an elastic tangential predictor plus a Coulomb cap. It
does not establish a differentiable law at stick/slip or open/closed
switching.

## Tangent audit

| Branch | Classification | Reason |
| --- | --- | --- |
| Open contact | `CONSISTENT` for the declared zero contribution | `_friction_system` adds no contact tangent when the pair is open. |
| Stick, fixed face/normal and fixed branch | `SEMI_CONSISTENT` | `k_t v v^T` is the exact local elastic branch contribution, but no independent global finite-difference campaign has qualified the assembled coupled response. |
| Slip, fixed face/normal | `APPROXIMATE` at the global route level | The outer solve applies the projected force as an effective load. `slip_root.consistent_jacobian` differentiates the frozen active-slip residual by superposition, but it is not exposed as a full assembled structural tangent qualification. |
| Stick/slip transition | `UNKNOWN`/nonsmooth | No differentiability is required at the activation boundary and no transition tangent claim is made. |
| Updated search / finite sliding | `UNQUALIFIED` | Frictional updated search is rejected; frictionless updated geometry has separate approximate geometric derivatives and cannot be transferred to friction. |

No tangent is called globally `CONSISTENT` without a dedicated analytical or
finite-difference basis.

## Energy and dissipation

`_dissipation_increment(previous, current, forces)` computes the local work
associated with slip-reference evolution, and the solver reports the sum as
`cumulative_local_dissipation`. The analytical campaign checks nonnegative
local work, and the load-history unit test checks positive cumulative work and
sign reversal.

There is no separately exposed decomposition of:

1. recoverable elastic tangential regularization energy, and
2. irreversible Coulomb frictional dissipation.

Consequently:

- `DISSIPATION_STATUS = INTERNAL_POSITIVE_WORK_CHECK_ONLY`;
- `ENERGY_STATUS = PARTIAL / NOT_QUALIFIED`;
- no global energy identity or external energy claim is made;
- a future WP08-C must define an increment convention and prove the sign with
  scale-aware tolerances.

## Open, stick, slip and reopen semantics

The currently implemented sequence is:

1. Start each frictional load increment with the previously committed
   `slip_references`.
2. Solve the normal active set and classify the tangential branch.
3. Use the elastic stick tangent or projected slip force during local
   iterations; do not publish trial references.
4. On convergence, commit the returned references; on
   `NumericalConvergenceError`, discard the trial.
5. For an open pair, report zero tangential force and keep the reference.
6. On reclosure, use the retained reference and seed a newly closed pair with
   the stick predictor.

This explains why a load-history solve can retain slip memory. It does not
prove a restartable accepted physical state: the reference is only held by a
local solver object and final diagnostic details.

## Restart and checkpoint boundaries

The general nonlinear checkpoint code is deliberately conservative: it marks
positive-friction contact as `stateful-required` and rejects legacy schema-1
migration when history was not persisted. The common nonlinear solver also
rejects positive friction before it reaches its normal checkpoint path.

Therefore the current statuses are:

- `FRESH_RECOMPUTATION`: available for the bounded static route when all
  contact input and load-history data are supplied again;
- `ACCEPTED_STATE_RESTART`: `NOT_QUALIFIED` for friction because the accepted
  slip references are not serialized by the friction solver;
- `MID_NEWTON_RESTART`: `UNSUPPORTED`/not claimed;
- minimum future state: ordered contact topology and face orientation,
  `mu`, `k_t`, gap/search/tolerance settings, accepted displacement/load
  factor, per-contact tangential slip references, active qualitative branch,
  and model/load-path signature with a deterministic digest.

## Updated search and finite sliding

`UPDATED_SEARCH_FINITE_SLIDING` remains `RESEARCH_ONLY` for the frictionless
common penalty path and is explicitly unavailable for positive friction. A
frictional model with `contact_search_mode="updated"` is rejected by both
model validation and the active-set solver. Selected facet, normal and
projection are trial-dependent in the frictionless research path; no
frictional restart, energy or tangent claim may inherit that evidence.

## Existing tests and evidence

The cheap targeted audit command executed on this baseline was:

```text
python -m pytest -q tests/unit/test_frictional_contact.py \
  tests/verification/test_frictional_contact_vnv.py \
  tests/unit/test_frictionless_contact.py
```

Result: **27 passed in 3.98 s**. This includes the tiny analytical Coulomb
campaign and affected frictionless-contact regressions. No structural/family
survey or external campaign was run in this readiness task.

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| `tests/unit/test_frictional_contact.py` | Open state, stick, slip/Coulomb bound, missing `k_t` rejection, load-history slip memory/dissipation and step-count behavior. | Rejected-trial digest rollback, restart, global tangent/energy identity or route breadth. |
| `tests/verification/test_frictional_contact_vnv.py` / `src/solveur/verification/frictional_contact.py` | Closed-form node/triangle spring block, stick/slip, reversal, cone and regularization sensitivity; status is internal/experimental. | Structural coupled qualification, external equivalence, updated search or incremental generality. |
| `tests/unit/test_frictional_contact_structural_limit.py` and structural V&V | Historical bounded structural fallback/research evidence. | Not run here; no promotion to WP08 qualification. |
| `tests/unit/test_frictional_contact_family_survey.py` | Historical three-family internal survey. | Not run here; no mesh/refinement or release claim. |
| `src/solveur/verification/code_aster_friction_contact.py` | Historical external comparison harness with an explicitly non-identical penalty/reference mapping. | Not run here; not formulation-equivalent proof. |
| `tests/unit/test_frictionless_contact.py` | Normal contact geometry, orientation, invalid inputs and explicit frictional updated-search rejection. | Frictional stick/slip maturity. |
| `src/solveur/core/qualification.py`, `qualification/technical_content_coverage.json` and `docs/elements/contact_avec_frottement.md` | Historical registry/docs inventory. | They do not override the source-level route restrictions or award WP08 points. |

Tests intentionally not run because of the no-structural-solve constraint:
`tests/unit/test_frictional_contact_structural_limit.py`,
`tests/unit/test_frictional_contact_family_survey.py` and
`tests/verification/test_frictional_contact_structural_vnv.py`.

## Ordered gaps

### Critical for any WP08 qualification claim

1. Friction is not integrated with the common nonlinear driver; only the
   bounded static direct route can currently be considered.
2. No accepted friction-state checkpoint/restart contract exists.
3. Rejected-trial rollback has an implementation boundary but no dedicated
   injected-failure digest proof.
4. No independent structural reference campaign is available for both
   formulations.

These are qualification blockers, not observed release bugs in this audit.

### Major

1. Global coupled tangent finite-difference/analytical verification for stick,
   slip and transition branches.
2. Separate recoverable regularization energy and irreversible dissipation
   identity, including unloading/reversal.
3. Structural stick-to-slip, slip-to-stick/reversal, opening/reclosure and
   multi-contact evidence.
4. Explicit tests for zero normal pressure, invalid direct-construction
   coefficients and nonfinite friction diagnostics.
5. Mesh/refinement and compatible external/reference comparison.
6. A clear public diagnostic/state schema that does not rely on the legacy
   `FrictionlessContact` name.

### Minor

1. Broader geometry-family survey and surface-patch coverage.
2. Normalized friction diagnostics and route-level telemetry.
3. Documentation of tolerance sensitivity at the stick/slip boundary.

## Proposed WP08 structure

The following Owner candidate split sums exactly to the frozen eight points;
it is a plan only and awards zero points here.

| Work package | Weight | Candidate scope |
| --- | ---: | --- |
| `WP08-A` | 1 | Formulation, input, state ownership and bounded route contract. |
| `WP08-B` | 2 | Stick/slip identities, open/reclose, rejected-trial rollback and deterministic state evidence. |
| `WP08-C` | 2 | Tangent finite-difference/analytical checks plus energy/dissipation V&V. |
| `WP08-D` | 2 | Structural three-level evidence and independent formulation-matched reference. |
| `WP08-E` | 1 | Replay, accepted-state restart, negative controls and fail-closed closure. |
| **Total** | **8** | No partial point award is implied. |

WP08-A readiness is complete only as an audit. The implementation and
qualification work must remain gated by Owner review and by the governing
nonlinear integration train.

## Narrow prospective bounded scope

The narrowest credible future target, subject to all later evidence, is:

- `linear_static` only;
- small displacement and small/moderate tangential motion;
- node-to-triangle contact with a fixed initial face and normal;
- serial direct sparse solve;
- exact normal Lagrange active set;
- per-contact `mu >= 0`, with positive `k_t` whenever `mu > 0`;
- elastic tangential predictor and regularized Coulomb projection;
- homogeneous material scope inherited from the selected static route;
- explicit load-history/replay only after state and restart evidence is added.

This is not a claim that all `linear_static` element/material/contact
combinations are covered.

Explicit exclusions remain:

- common `nonlinear_static` or `geometric_nonlinear_static` frictional
  production routes;
- updated-search or finite-sliding friction;
- surface-to-surface, mortar, segment-to-segment and general multi-body
  contact;
- large sliding, rotating normals and general 3-D path dependence;
- transient, harmonic, modal and buckling frictional contact;
- MPI/PETSc/distributed frictional mechanics;
- friction-specific checkpoint/restart until its state is serialized and
  validated;
- universal smooth tangent, energy or dissipation claims;
- external equivalence where the reference formulation is not identical.

## Future negative controls

The following controls are prepared for WP08 execution and are not run here:

`mu < 0`; nonfinite `mu`; positive `mu` without `k_t`; opening after a stick
state; stick-to-slip; slip-to-stick/reversal; rejected trial and rollback;
friction with zero normal pressure; unsupported updated-search friction;
restart with missing tangential state; reversed master orientation; and
nonfinite required diagnostics. Expected outcomes must be typed, deterministic
and fail-closed; a negative case is never structural qualification PASS.

## Governance and validation

```text
PRODUCTION_MECHANICS_CHANGED = NO
CONTACT_MECHANICS_CHANGED = NO
MATURITY_CHANGED = NO
STRUCTURAL_SOLVES_RUN = NO
EXTERNAL_SOLVER_RUN = NO
HEAVY_SOLVE_RUN = NO
FULL_TEST_SUITE_RUN = NO
WP08_FORMAL = 0/8
VALIDATED_TOTAL = 29/100
```

The current capability registry remains unchanged: frictional contact is
experimental/research and outside the release qualification boundary. No
promotion is inferred from this audit.
