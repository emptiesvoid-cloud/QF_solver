---
doc_id: DOC-028-WP03-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP03 — BEAM2 and DISCRETE V&V

This record closes the WP03 technical V&V campaign for four narrowly bounded
routes selected by the WP01 maturity baseline. It does not rewrite 0.2.7
evidence and does not claim universal validation, certification, or a general
BEAM2/DISCRETE maturity promotion.

The machine-readable record is
[`wp03_beam2_discrete_vnv.json`](../../../qualification/0_2_8/wp03_beam2_discrete_vnv.json).
The WP03 decision delta is maintained separately in
[`wp03_maturity_matrix.json`](../../../qualification/0_2_8/wp03_maturity_matrix.json);
the WP01 baseline remains unchanged.
The executable campaign is
[`test_028_beam2_discrete_vnv.py`](../../../tests/verification/test_028_beam2_discrete_vnv.py).

## Frozen campaign contract

The baseline is `598704c834b4642f7c2a9a1fdc7595895f9e4130`. Before execution,
the campaign froze the scope, hypotheses, analytical oracle and tolerance for
each case in the JSON record. Each case was executed twice and the replay
digests were identical. The test also reruns both replays, so the committed
observations are checked against the current implementation rather than being
treated as unchecked narrative.

| Case | WP01 state | Oracle | Decision | Public maturity action |
| --- | --- | --- | --- | --- |
| BEAM2 static | `NEEDS_MINOR_VNV` | Timoshenko cantilever closed form | `QUALIFIED_BOUNDED` | Owner confirmation pending |
| BEAM2 modal | `NEEDS_MINOR_VNV` | slender cantilever first two bending frequencies | `QUALIFIED_BOUNDED` | Owner confirmation pending |
| DISCRETE static | `NEEDS_MINOR_VNV` | scalar spring solutions and assembly invariants | `QUALIFIED_BOUNDED` | Owner confirmation pending |
| DISCRETE modal | `NEEDS_MINOR_VNV` | closed-form uncoupled mass-spring frequencies | `QUALIFIED_BOUNDED` | Owner confirmation pending |

`QUALIFIED_BOUNDED` is the technical V&V decision recorded by WP03. The
technical evidence record retains `promotion_applied: false`; the separate
[`final WP03 Owner gate`](wp03_owner_gate_final.md) applies the approved
bounded maturity action without rewriting this campaign record.

## BEAM2 static

The campaign covers a straight, constant-section, isotropic BEAM2 cantilever
in small displacement linear statics. It exercises axial traction, transverse
flexion in both planes and torsion on one-, two- and four-element meshes.

The oracle is the closed-form Timoshenko cantilever tip displacement. The
checks also require reaction balance, strain-energy identity, solver residual
and six rigid-body modes in the unconstrained element stiffness. The maximum
observed relative displacement error is `2.32e-15`; the maximum reaction
equilibrium error is `2.40e-14`; the maximum relative residual is `4.97e-14`.
All are below the predeclared `1e-10` limits.

The qualified scope excludes releases, offsets, variable sections, plasticity,
contact, large rotations and distributed dynamic loading.

## BEAM2 modal

The modal case is a straight slender cantilever with coherent mass, positive
density, fixed root and no damping. The first two bending frequencies on one-,
two- and four-element meshes are compared with the Euler-Bernoulli slender
reference. This oracle is deliberately bounded: it does not qualify thick-beam
shear behavior.

The maximum frequency error is `0.4333 %`, below the frozen `1 %` limit. The
maximum eigen-residual is `5.26e-12`, and the maximum mass-orthogonality error
is `2.38e-16`, both below `1e-8`. The declared fixed-root model has two
positive frequencies in the requested first-two-mode replay; rigid-body and
rank behavior is checked separately by the static stiffness invariant.

The qualified scope excludes damping, nonlinear dynamics, joints, offsets,
multi-body coupling and thick-beam extrapolation.

## DISCRETE static

The static campaign uses three uncoupled translational ground springs with
`k = (1000, 4000, 9000) N/m`, a concentrated mass of `10 kg`, and loads
`(25, -20, 45) N`. The closed-form oracle is `u = F/k`. It additionally checks
static equilibrium, energy identity, a two-node rigid translation null mode,
and equal/opposite spring forces.

All observed scalar errors are zero at the recorded precision and are below
the frozen `1e-12` limits. The scope excludes coupled multi-DOF systems,
rotational inertia, local orientations, nonlinear laws, gaps and damping.

## DISCRETE modal

The modal campaign uses the same three uncoupled translational spring
directions and mass. The oracle is `f_i = sqrt(k_i/m)/(2 pi)`, producing
`1.5915494309`, `3.1830988618` and `4.7746482928 Hz`.

The replay matches all three frequencies at recorded precision. The maximum
eigen-residual is `1.80e-16` and mass-orthogonality error is zero, below the
frozen `1e-12` limits. The scope excludes rotational inertia, coupled mass,
multi-node coupling, damping and transient extrapolation.

## Routes not closed by WP03

BEAM2 Newmark, BEAM2 harmonic, DISCRETE Newmark and DISCRETE harmonic remain
`EXPERIMENTAL`. Their required independent time-history or frequency-response
oracles, phase/amplitude conventions and route-specific tolerances were not
executed in this WP. Existing historical references are not substituted for
the absent reproducible 0.2.8 evidence.

## Decision and next gate

WP03 establishes four technical `QUALIFIED_BOUNDED` decisions and its
historical route list remains unchanged. The final Owner gate is recorded
separately after WP03B, so the frozen evidence is not rewritten.
