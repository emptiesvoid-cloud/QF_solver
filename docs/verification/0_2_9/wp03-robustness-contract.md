---
doc_id: DOC-029-WP03-001
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03-A — Newton robustness and adaptive-control contract

> **Prospective contract record.** This page freezes WP03 before production
> implementation. It does not claim a robustness improvement, award WP03
> points, change numerical formulations or promote any capability.

The contract is based on the tracked branch at
ecc09f0bae2dab867c12d7e471860887f6ef0548. The machine-readable source is
qualification/0_2_9/wp03_robustness_contract.json.

## Current position

- WP00: **CLOSED**, 4/4.
- WP01: **CLOSED**, 12/12.
- WP02: **CLOSED**, 6/6, with the bounded limitations recorded by its
  independent audit.
- WP03: **CONTRACT_PHASE**, 0/7.
- Validated roadmap total: **22/100**.
- OD-029-01: **OPEN**, blocks WP09 only.
- OD-029-02: **CLOSED** as READ_V1_WRITE_V2_BOUNDED.

WP03-A does not authorize WP03-B implementation.

## Canonical diagnostic equations

The diagnostic residual convention is:

R(u, lambda, state) = lambda * F_ext - F_internal - F_contact

The tangent composition concept is:

K_T = K_material + K_geometric + K_contact

These equations define common diagnostics and ownership. Existing
formulation-specific signs and physical force definitions remain unchanged.
The driver reduces constrained systems to free DOFs for convergence norms;
fixed DOFs are handled by the existing boundary-condition machinery.

NonlinearAssemblyProtocol and CompositeNonlinearAssembly remain the
composition seam. The robustness controller must accumulate contribution
responses without knowing constitutive, geometric or contact equations.

## Actual current execution map

The current fixed-load public Newton authority is
UnifiedNewtonEngine in src/solveur/core/nonlinear/driver.py. The
compatibility entry point solve_full_newton delegates to it. The standard
material load-control path and the geometric fixed-load path also use that
engine.

The accepted-state authority is UnifiedContinuationController together with
NonlinearStateTransaction. Migrated fixed, adaptive and arc-length routes
use the shared transaction boundary for accepted-state publication.

The contract-phase inventory also found distinct policy surfaces that are
not silently treated as one already-complete robustness implementation:

- solve_adaptive_full_newton and
  NonlinearLoadControlMixin._solve_adaptive_load_steps both retain
  adaptive policy code and are planned for WP03-C consolidation.
- _line_search_assembly_with_diagnostics, line_search_factor and the
  geometric compatibility wrapper expose overlapping line-search helpers;
  WP03-B must make one dispatch authoritative.
- Arc-length keeps its augmented correction kernel and radius policy. This is
  an acceptable specialization, provided accepted-state ownership,
  retry classification and diagnostics remain common.
- NonlinearRobustnessOptions is explicit opt-in experimental R&D control,
  not the default public robustness authority.
- FrictionlessActiveSetSolver, frictional contact and slip-root loops remain
  linear-static/research compatibility paths. They are not promoted by WP03.

The full call graph and debt classification are recorded in
[the architecture map](wp03-architecture-map.md).

## Target robustness authority

Future WP03 implementation shall expose one formulation-neutral
UnifiedNonlinearRobustnessController responsibility, whether that name is
implemented literally or through an equivalent repository abstraction. It
owns:

- increment proposal and retry classification;
- cutback and growth policy;
- stagnation decision;
- line-search dispatch;
- global convergence lifecycle;
- terminal failure publication; and
- deterministic robustness diagnostics.

It must not own constitutive equations, geometric/contact search mathematics,
element formulations or an accepted-state publication path outside
NonlinearStateTransaction.

Arc-length may continue to use a specialized augmented correction kernel. It
must use the same accepted-state, rollback, failure and diagnostic contract.
WP03 does not force the fixed-load Newton equation onto arc-length.

## Stagnation contract

The canonical primary measure is the free-DOF residual force norm. Relative
residual and displacement-correction norms are secondary diagnostics; an
energy/work norm is optional when a route supplies it.

The prospective default is a four-sample window with a plateau threshold of
1e-10 relative change. CONVERGENCE_STAGNATION is emitted only when the
normal convergence criteria are not met and the residual has failed to
decrease across the window. Non-finite values take precedence and map to
NAN_DETECTED or INF_DETECTED.

The decision must be independent of timing, thread scheduling and mapping
order. Residual history, window and threshold belong in deterministic
diagnostics. The current UnifiedNewtonEngine four-sample check is recorded
as the compatibility baseline; WP03-B must test its boundaries before any
change.

## Line-search contract

For the common fixed-load path, the prospective merit is:

M(alpha) = ||R_free(u + alpha * delta_u)||_2

The full trial starts at alpha = 1. Rejected trials halve alpha. The
prospective common floor is 1e-4, with at most 12 reductions. The first
finite trial with strict merit decrease is accepted by default. When an
explicit Armijo coefficient c is configured, acceptance is:

M(alpha) <= (1 - c * alpha) M(0)

Exhausting the reduction budget or reaching the floor yields
LINE_SEARCH_FAILURE and cannot mutate the accepted state. Arc-length's
augmented correction may retain its own algebraic kernel, but it cannot
create a second accepted-state or retry authority.

The existing helper defaults are not silently declared identical: their
current values and compatibility wrappers are part of the WP03-B audit
surface.

## Adaptive-control contract

The accepted physical state contains displacement, load factor, material
state, contact state, continuation state and accepted-increment metadata.
The next-trial policy state contains proposed increment, retry index, cutback
count and policy history. The latter may guide a trial but is not an
accepted physical state until a global transaction commits.

The following invariants are frozen:

1. Only a globally accepted composite transaction advances physical state.
2. Rollback precedes every retry or cutback.
3. A second retry starts from the same accepted digest as the first retry.
4. MIN_INCREMENT_REACHED is an explicit terminal outcome.
5. A checkpoint failure is infrastructure failure and does not cause physical
   cutback by default.

The existing default cutback_factor = 0.5, growth_factor = 1.5 and
maximum_cutbacks = 25 are preserved as the compatibility baseline.

## Failure and retry contract

The canonical NonlinearFailureReason values are retained; no duplicate
reason is introduced. The exact context matrix is in
[the failure/retry matrix](wp03-failure-retry-matrix.md). In particular,
non-retryable material/state/non-finite/invalid-element failures are never
hidden as cutbacks, and CHECKPOINT_FAILURE never masquerades as physical
non-convergence.

## Public boundary and maturity

The public robustness contract covers the existing bounded routes only.
Experimental solver/scaling/line-search settings remain explicit opt-in.
Geometric nonlinear, arc-length, active-set/friction contact and distributed
nonlinear PETSc/MPI remain bounded by their existing status. Robustness work
cannot promote:

- general nonlinear mechanics;
- general finite-strain plasticity;
- general contact or finite sliding;
- nonlinear HPC;
- any element or analysis combination without its own evidence.

## Prospective gates

G03-01 through G03-10 are frozen but not demonstrated in WP03-A. Their
acceptance evidence is listed in [the gate matrix](wp03-gate-matrix.md).
Every gate remains PROSPECTIVE_NOT_DEMONSTRATED until the corresponding
implementation and targeted evidence exist.

## Non-goals and next decomposition

WP03-A does not implement finite-strain plasticity, frictional-contact
migration, formulation changes, new elements, distributed nonlinear
mechanics, nonlinear dynamics or maturity changes. The implementation
decomposition is recorded in
[the WP03 plan](wp03-implementation-plan.md).

The 16-case baseline campaign is frozen in
[the baseline record](wp03-baseline-campaign.md); no numerical values are
invented in this contract phase. The next permitted action is Owner review
before WP03-B.
