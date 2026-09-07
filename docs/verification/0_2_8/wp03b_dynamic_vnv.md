---
doc_id: DOC-028-WP03B-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP03B — BEAM2 and DISCRETE dynamic V&V

This addendum records a bounded analytical campaign for the four BEAM2 and
DISCRETE dynamic routes left experimental by WP03A. It does not modify 0.2.7
evidence, numerical source code, or the four static/modal decisions recorded
by WP03A. It does not claim universal dynamic validation or certification.

The machine-readable record is
[`wp03b_dynamic_vnv.json`](../../../qualification/0_2_8/wp03b_dynamic_vnv.json).
Its decision delta is
[`wp03b_maturity_matrix.json`](../../../qualification/0_2_8/wp03b_maturity_matrix.json),
which explicitly preserves the WP03A static/modal decisions. The executable
campaign is
[`test_028_beam2_discrete_dynamic_vnv.py`](../../../tests/verification/test_028_beam2_discrete_dynamic_vnv.py).

## Frozen campaign contract

The baseline is `6b9c08f91c876bf5136a9da39555149b89dc2b98`. Before execution,
the machine-readable record froze each route's system, assumptions, analytical
oracle, observables and tolerances. Each route is executed twice and must yield
identical canonical replay digests. This is reproducible analytical V&V, not a
substitution for an unavailable historical external artefact.

| Route | Analytical oracle | Decision | Public maturity action |
| --- | --- | --- | --- |
| BEAM2 Newmark | exact axial SDOF free vibration | `QUALIFIED_BOUNDED` | Owner confirmation pending |
| BEAM2 harmonic | exact damped axial SDOF FRF | `QUALIFIED_BOUNDED` | Owner confirmation pending |
| DISCRETE Newmark | exact damped mass-spring response | `EXPERIMENTAL` | No maturity action |
| DISCRETE harmonic | exact damped mass-spring FRF | `QUALIFIED_BOUNDED` | Owner confirmation pending |

The analytical oracle is appropriate because each system is deliberately a
single declared physical degree of freedom with closed-form coefficients. The
oracle is independent of the Newmark time stepping and direct complex solve;
it does not extend the result to general beam or discrete assemblies.

## BEAM2 Newmark

The case is one straight, constant-section, isotropic BEAM2 with fixed root,
consistent axial mass and UX-only initial displacement. It is undamped free
vibration for four periods using Newmark average acceleration at 40 and 80
samples per period. The physical reference is
`u(t) = u0 cos(omega t)` with `omega = sqrt((EA/L)/(rho A L/3))`.

The frozen checks cover displacement and velocity histories, zero-crossing
frequency, state-plane phase, amplitude, mechanical-energy conservation, time
step refinement and deterministic replay. The scope excludes transverse
dynamics, releases, joints, offsets, distributed loads, nonlinear response and
multi-element extrapolation.

## BEAM2 harmonic

The same axial BEAM2 is driven by a unit UX harmonic load with a declared
mass-proportional damping ratio of `0.02`. Seven frozen frequency ratios span
below resonance, the sampled resonance point and above resonance. The oracle
is `H(omega) = 1/(k - omega^2 m + i omega alpha m)`.

Amplitude, wrapped phase, complex response, solver residual, sampled resonance
and two off-resonance comparisons are checked. The sampled peak is not a
continuous resonance search and does not qualify transverse or general BEAM2
frequency response.

## DISCRETE Newmark

The case is one grounded UX spring (`1000 N/m`) and one `10 kg` concentrated
mass, with initial displacement `0.02 m`, zero initial velocity and declared
mass-proportional damping ratio `0.02`. The underdamped closed form supplies
displacement, velocity, damped frequency and state-plane phase references.

The campaign checks two time steps, deterministic replay, monotone mechanical
energy, and the balance of mechanical energy plus trapezoid-integrated damping
power. The energy quadrature is only a verification observable; it does not
add a new solver output. Coupled stiffness/mass, rotational inertia, local
orientations, gaps, nonlinear springs and multi-node systems remain outside
the qualified scope.

## DISCRETE harmonic

The same scalar spring-mass system uses the same declared damping ratio and
seven frozen frequency ratios. The damped SDOF complex FRF is the closed-form
oracle. The campaign checks amplitude, phase, complex response, residual,
sampled resonance and off-resonance behavior. It does not qualify general MDOF
or alternative damping-model harmonic response.

## Decision and Owner gate

BEAM2 Newmark, BEAM2 harmonic and DISCRETE harmonic meet their predeclared
bounded technical gates. DISCRETE Newmark is intentionally retained as
`EXPERIMENTAL`: its coarse-step phase error is `0.0128952201 rad`, above the
frozen `0.012 rad` limit. The tolerance and time grid were not adjusted after
the result.

The technical record retains its pre-Owner state. The final Owner decision is
maintained separately in the
[`final WP03 Owner gate`](wp03_owner_gate_final.md), so its frozen scope,
tolérances and replay observations are not rewritten.
