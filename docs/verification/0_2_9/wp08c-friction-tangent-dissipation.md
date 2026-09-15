---
doc_id: DOC-029-WP08C-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-C — friction tangent and dissipation V&V

**Status:** `PASS_CANDIDATE_WITH_LIMITATIONS` — lightweight local evidence
only; no WP08 point is awarded and no structural or external qualification is
claimed.

**Source:** `d8da1caede03463971a748a46c5d416069eceb24` on
`0.2.9-wp08-prep`, repository `emptiesvoid-cloud/QF_solver`. The source
includes the owner-authorized WP08-B R1 zero-pressure bugfix; this WP08-C
artifact does not modify production mechanics.

## Frozen scope and thresholds

The checks use only the existing serial direct, small-displacement,
node-to-triangle, fixed initial face/normal `linear_static` route with exact
normal Lagrange active-set contact, positive `mu` and positive `k_t`. Updated
search/finite sliding, the common nonlinear friction route, dynamics,
restart, MPI/PETSc, structural refinement and external solvers are excluded.

The thresholds were fixed before the measurements:

| Quantity | Threshold |
| --- | --- |
| stick analytical tangent Frobenius / column | `1e-12` |
| stick tangent symmetry | `1e-14` |
| stick force FD Frobenius / column | `1e-7` / `5e-7` |
| slip local FD Frobenius / column | `1e-6` / `5e-6` |
| stick energy gradient | `1e-7` |
| dissipation floor | `-1e-14 * max(E_char, 1)` with `E_char = 1` |
| replay/finite values | relative `1e-12`, absolute floor `1e-14` |

## Stick tangent

For fixed active set, normal pressure, face basis, stick branch and slip
reference, the local law is

```text
t = k_t (u_t - s_ref)
dt/du_t = k_t I
K_t = sum_i k_t (v_i ⊗ v_i)
```

The actual `_friction_system` contribution equals that matrix exactly in the
tested floating-point representation. Measured Frobenius error, maximum
column error and symmetry error were all `0.0`.

A central finite-difference sweep of the real `_friction_update` stick map,
at a point strictly inside the Coulomb cone, used steps
`[1e-4, 1e-6, 1e-8]`. Frobenius errors were
`[0.0, 1.504877098319886e-14, 1.6480333556215981e-12]`; maximum-column
errors were `[0.0, 2.128217602148652e-14, 2.330671122763306e-12]`.
Therefore `STICK_ANALYTICAL_TANGENT = PASS` and
`STICK_FD_STATUS = PASS` for this fixed local branch.

## Open branch and slip local Jacobian

An open contact returns zero tangential force, retains its slip reference and
adds no tangent. The zero contribution is exact in the tested branch:
`OPEN_TANGENT_ZERO = PASS`.

For fixed positive pressure and a fixed slip branch, the tested analytical map
was

```text
trial = k_t (u_t - s_ref)
n_t = trial / ||trial||
dt/dtrial = (mu p / ||trial||) (I - n_t ⊗ n_t)
```

with the `k_t` chain factor included. A comfortably sliding state was
evaluated with three central-difference steps `[1e-5, 1e-7, 1e-9]`.
Frobenius errors were
`[4.3081326635943776e-7, 3.485598546029158e-11,
9.051499343873175e-10]`; maximum-column errors were
`[6.449809695613153e-7, 5.3010924197445456e-11,
1.622194685464252e-9]`. This supports
`SLIP_TANGENT_CLASSIFICATION = LOCAL_CONSISTENT_FIXED_PRESSURE` only.

The local `_friction_update` differentiation freezes the supplied pressure,
so its `p(u)` derivative is omitted. The separate nested
`slip_root.consistent_jacobian` includes a pressure-sensitivity term in its
coupled root fallback, but that Jacobian is not directly exposed as a public
local matrix and was not numerically compared here. No global structural
tangent consistency claim is made.

## Transition and zero-pressure boundary

The deterministic path used trial norms `10`, `49.99999`, `50`,
`50.000009999999996`, and `100` against a Coulomb limit of `50`. States were
`stick, stick, stick, slip, slip`; force norms were
`10, 49.99999, 50, 50, 50`. Force is continuous across the sampled boundary,
but no tangent continuity is claimed: `TRANSITION_TANGENT_CLASSIFICATION =
NONSMOOTH`.

The WP08-B R1 zero-pressure path remains explicitly degenerate and is not
differentiated. With prior `slip` and pressure `0`, it returns finite zero
force, keeps `slip`, recenters the reference, and adds no stick tangent:
`ZERO_PRESSURE_TANGENT_CLASSIFICATION = DEGENERATE_NOT_QUALIFIED`.

## Dissipation semantics

The implementation is exactly:

```text
_dissipation_increment(previous, current, forces)
    = sum(forces * (current - previous))
```

Here `previous` and `current` are committed and newly returned slip
references. The adopted sign convention is therefore positive force dotted
with the slip-reference increment. It is a local work proxy, not a proved
global energy decomposition.

The seven-step stick/slip/reversal history produced these reported
increments:

| Step | State | Force x | Slip reference x | Delta reference x | Increment | Cumulative |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | stick | 0 | 0 | 0 | 0 | 0 |
| 2 | stick | 36.36363636363637 | 0 | 0 | 0 | 0 |
| 3 | slip | 50 | 0.145 | 0.145 | 7.25 | 7.25 |
| 4 | slip | -50 | 0.095 | -0.05 | 2.5 | 9.75 |
| 5 | slip | -50 | 0.015 | -0.08 | 4 | 13.75 |
| 6 | slip | -50 | -0.145 | -0.16 | 8 | 21.75 |
| 7 | slip | 50 | -0.055 | 0.09 | 4.5 | 26.25 |

All values are finite; every increment is above the frozen floor and the
cumulative value is non-decreasing. Pure stick, open contact and zero-
pressure free slip each have zero irreversible work. First slip, continued
slip and reversal all have positive finite local work.

There is no separately exposed recoverable tangential energy plus
irreversible dissipation decomposition over the full route. Accordingly,
`ENERGY_DECOMPOSITION_STATUS = NOT_QUALIFIED`.

## Recoverable stick energy

Within the fixed stick branch,

```text
Psi_t = 0.5 k_t ||u_t - s_ref||²
grad(Psi_t) = k_t (u_t - s_ref) = t
```

The central-difference gradient sweep used `[1e-4, 1e-6, 1e-8]` and produced
relative errors
`[3.9720546451956367e-16, 7.732181583938453e-14,
7.365257932457724e-12]`, below the frozen `1e-7` limit. This is a stick-only
identity and is not extended through slip or switching.

## Negative and finiteness controls

NaN/positive-infinite pressure and NaN slip-reference inputs reach the typed
`NumericalConvergenceError` / `NAN_DETECTED` fail-closed path. The exact
zero-trial slip case is covered by WP08-B R1. Public JSON rejects negative or
non-finite `mu`, while direct construction of the historical
`FrictionlessContact` dataclass still bypasses that schema validation; this
remains a documented, unqualified input gap and is not fixed here. Invalid
positive-friction stiffness remains covered by the existing rejection tests.

## Decision boundary

The evidence supports local open, stick and fixed-pressure slip identities,
the sampled nonsmooth transition, and non-negative local dissipation in the
existing tiny history. It does not qualify a pressure-coupled global tangent,
a differentiable transition tangent, a global energy balance, restart,
structural mesh convergence, external correlation, or updated-search
friction. No mechanics, contact formulation, numerical policy or maturity
status changed.

```text
PRODUCTION_MECHANICS_CHANGED = NO
CONTACT_MECHANICS_CHANGED = NO
MATURITY_CHANGED = NO
WP08_C_FORMAL_POINTS = 0/2
```
