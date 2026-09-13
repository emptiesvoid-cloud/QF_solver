---
doc_id: DOC-029-WP06B-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-B — Continuation State and Rollback Contract

## Status and scope

This document audits the continuation-state, rollback and restart semantics
actually present at source revision 03166e98a9a0b8cc7978c7ad2a370e441aefdc1e.
It is a technical candidate for WP06-B only. It awards no formal points:
WP06-B remains 0/1 formal and WP06 remains 0/8.

The scope is the arc-length continuation path on nonlinear_static. No
structural restart campaign, postbuckling solve, external solver, heavy solve,
or full test suite is included. No production mechanics or maturity state is
changed.

## State owners and fields

The formulation-neutral state is NonlinearState in
src/solveur/core/nonlinear/state.py. Immutable model data, mesh connectivity
and global matrices remain outside the transaction.

| State category | Actual fields or source values | Ownership |
|---|---|---|
| Mechanical accepted state | displacement, material_state, contact_state | NonlinearState |
| Continuation scalar | load_factor | NonlinearState |
| Continuation step | accepted_step | continuation_state |
| Radius | radius, maximum_radius | continuation_state |
| Mixed-space scale | load_scale | continuation_state |
| Previous direction | previous_du, previous_dlambda | continuation_state |
| Policy compatibility | target_load_factor, stop_mode, allow_load_factor_turning, control_dof | continuation_state |
| Trial step increments | delta_u_step, delta_lambda | local variables in _solve_arc_length_step |
| Accepted-step metadata | step, attempted radius, next accepted radius, accepted load factor | accepted_increment_metadata |
| Rejection history | rejected increments and rejection log | UnifiedContinuationController and route diagnostics |

delta_u_step and delta_lambda are deliberately trial-local quantities. The
accepted continuation snapshot persists the previous converged direction and
load-factor increment rather than pretending that an unaccepted trial
increment is accepted state.

## Accepted versus trial state

The arc route creates a detached accepted NonlinearState and installs it in a
UnifiedContinuationController. Each attempted continuation step follows:

1. begin_trial creates a detached copy of the complete accepted composite;
2. the predictor and corrector modify only the trial displacement/load factor
   and trial material state;
3. on convergence, the route fills accepted continuation and metadata fields;
4. controller.commit validates and publishes the complete replacement;
5. the caller-visible displacement/material mirrors are updated from the
   committed state;
6. a checkpoint is saved only after physical acceptance.

The accepted state therefore contains no partially applied trial correction.
The arc path copies material updates returned by the assembly before commit.
The current frictionless contact path is stateless for this contract; a
stateful contact or friction history is not silently included in the restart
claim.

## Rollback contract

For a rejected step:

1. the error is captured without replacing its original typed reason;
2. UnifiedContinuationController.rollback verifies the accepted composite
   digest before and after transaction rollback;
3. component digests, load factor and continuation payload are recorded;
4. rejected-increment count and rejection log are updated;
5. only then does UnifiedArcLengthRadiusPolicy choose a retry or terminal
   outcome.

The mechanical rollback includes displacement, material state and contact
state slots. The continuation rollback includes load factor, radius,
maximum-radius, load scale, previous displacement direction, previous
load-factor direction and compatibility policy fields. The accepted state
must have identical composite and component digests after rejection.

Existing focused evidence covers accepted/rejected arc ownership, exact
displacement/material/load-factor/previous-direction preservation, rollback
ordering, rejected-radius non-persistence, checkpoint ordering and
deterministic state/diagnostic replay. The WP06-specific tests add two
accepted-state epochs with a rejected trial after each epoch.

## Radius rollback semantics

The carried policy radius belongs to the accepted continuation payload until
the next accepted commit. A rejected solver step cannot publish its trial
radius or any trial mechanical state.

The retry radius is different: after rollback, a retryable failure may cause
the radius policy to calculate a smaller next-trial radius. That value is a
retry-policy decision, not a mutation of the accepted state. It can later
become accepted state only when a subsequent physical step converges and is
committed.

The source records both policy_radius and effective_attempt_radius. The latter
also captures target clipping. The policy ensures a clipped retry is strictly
below the failed effective radius when required, preventing an invisible
repeat of the same attempted step.

Checkpoint writes occur after commit. A checkpoint failure after physical
acceptance is CHECKPOINT_FAILURE and does not enter the physical rollback or
radius cutback path.

## Restart and suffix semantics

The current classification is:

    PARTIAL_RESTART_STATE

NonlinearCheckpointV2 and NonlinearCheckpointSession persist an accepted
NonlinearState, topology metadata, model signature and the arc continuation
fields required to restore a continuation path. Restore is detached and
validated before caller-owned displacement or material mappings are
installed. The arc route additionally checks accepted-step consistency,
target/stop/turning/control settings, radius ordering, load scale and previous
direction shape/finiteness.

Focused tests already exercise v2 restore, accepted-only save, continuation
field equality, rejected-trial non-persistence, adaptive radius/rejection
restart, suffix determinism, retained accepted files, checkpoint failures and
bounded v1-read/v2-write migration.

This is not yet full restart qualification because:

- structural suffix replay under the future governing 0.2.9 policy is not
  demonstrated here;
- stateful friction contact history is not persisted by the bounded v1
  migration and remains NOT_CLAIMED;
- branch-switching/bifurcation state is not represented;
- cross-process or MPI global ordering is not claimed;
- restart compatibility is not external V&V.

## Failure and non-finite controls

The following controls are present and are checked by unit evidence:

| Input or event | Expected behavior |
|---|---|
| NaN load factor in NonlinearState | ValueError before transaction installation |
| NaN/Inf continuation payload | ValueError during state validation |
| non-positive or non-finite radius | InputValidationError/ValueError at controls or route boundary |
| non-finite reduced linear input | typed NAN_DETECTED failure from nonlinear adapter |
| singular augmented correction | ARC_LENGTH_FAILURE |
| non-finite augmented correction | ARC_LENGTH_FAILURE |
| non-finite mechanical residual entering correction | no finite correction can be published; typed arc failure path |
| typed trial failure | rollback, digest verification, then frozen retry classification |
| rollback digest mismatch | STATE_CORRUPTION; no silent retry |

The current route distinguishes physical failure from checkpoint failure and
does not replace the original solver error with a checkpoint error. Arc
predictor/correction sub-stages currently share ARC_LENGTH_FAILURE in several
cases; finer taxonomy is a future WP06-C/F gap, not a reason to relabel an
existing result.

## Telemetry contract preparation

Future arc-length telemetry must preserve, per accepted or rejected step:

- analysis and route identity;
- step and iteration;
- load_factor and delta_lambda;
- delta_u summary;
- radius, maximum radius and load_scale;
- predictor sign and branch direction;
- direction alignment;
- constraint_residual;
- physical residual and residual history;
- accepted/rejected status;
- retry count and failure reason;
- accepted-state digest and rollback digest comparison;
- checkpoint status when persistence is enabled.

These fields are already available in NonlinearStep, continuation diagnostics
or controller rejection logs in varying forms. This document does not
implement WP15 instrumentation and does not claim a generic event sink is
connected to every arc route.

## Technical-candidate decision

WP06-B candidate evidence is sufficient for:

- explicit accepted/trial state ownership;
- composite mechanical and continuation rollback semantics;
- separation of rollback from retry-radius policy;
- bounded checkpoint continuation metadata;
- deterministic digest-based rollback checks;
- fail-closed non-finite and typed failure boundaries.

It is not sufficient for:

- full structural restart qualification;
- stateful frictional-contact restart;
- branch-switching or bifurcation restart;
- external or distributed restart qualification.

Candidate status: WP06-B technical candidate 1/1, formal points 0/1 pending
integration and Owner closure.
