---
doc_id: DOC-027-022
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 WP11 - Existing J2 maturity and closure evidence

## Decision boundary

WP11 records a controlled maturity extension for the existing small-strain
von Mises J2 route. It does not change the material implementation, a solver
formulation, a default Newton path, or any Owner threshold. The source under
test is `94461602dfd1782be57c20e1801a0d5d8e262ef1`; the WP11 execution was
started from `4d0ee14f4aa61b9337874a991263a93b4f9a8c73`.

The resulting decision is `PASS_WITH_LIMITATIONS` for the work package and
`KEEP_QUALIFIED_BOUNDED_WITH_LIMITATIONS` for `MAT-J2-SMALL`, subject to
Owner review. `MAT-FINITE-J2` remains `EXPERIMENTAL`/`NOT_QUALIFIED`.

## Controlled evidence

The machine-readable case catalog and evidence are:

* `qualification/0_2_7/wp11_j2_cases.json`
* `qualification/0_2_7/wp11_j2_evidence.json`
* `qualification/0_2_7/wp11_state.json`

The result digest is
`5e4825625d40f2363ecefb8f96baa43acac42f23db7195d000ca0c09717ef536`.
The artifact records the environment, source SHA, input digest, result digest,
predeclared policies and all four element-family rows.

## Material-point and tangent checks

The direct J2 path covers elastic predictor, first yield, radial return,
plastic strain and equivalent plastic strain, stress consistency, unloading,
reloading and a simple reversal cycle. All checks are finite and pass. The
algorithmic tangent is symmetric as a diagnostic. Central finite differences
cover elastic, near-yield, traction, compression, shear, non-proportional,
reload and cyclic states at the declared perturbations; the maximum relative
error is `2.1204721119376345e-10`, below the existing G06 limit `1e-6`.

## Four-family structural evidence

| Family | Multi-element | Cyclic | Energy | Rollback | Full Newton | Modified Newton |
| --- | --- | --- | --- | --- | --- | --- |
| TET4 | PASS | PASS | PASS | PASS | PASS | non-converged, diagnostic |
| TET10 | PASS | PASS | PASS | PASS | PASS | non-converged, diagnostic |
| HEX8 | PASS | PASS | PASS | PASS | PASS | non-converged, diagnostic |
| HEX20 | PASS | PASS | PASS | PASS | PASS | non-converged, diagnostic |

Multi-element maximum relative residuals are `2.39e-8`, `1.93e-8`,
`3.39e-8` and `7.80e-8` in the table order. The maximum relative energy
balance errors are `1.84e-12`, `5.49e-9`, `8.64e-9` and `1.80e-9`.
Rollback injects one controlled rejected increment per family and verifies
the committed-state digest is restored before retry; no state contamination,
NaN/Inf or silent pass is recorded.

## Increment and failure characterization

A monotonic J2 path at load scale `0.2` is run with 1, 2 and 4 subdivisions
per branch for every family. The finest-level comparison records family-
specific displacement and internal-variable sensitivities, but no universal
partition-independence threshold is introduced. This evidence does not erase
the existing G06 bounded policy, whose strongest independent increment claim
remains the declared TET4 study.

Full Newton converges for all four families. Modified Newton non-convergence
is reproduced and classified as diagnostic rather than hidden or promoted.
Invalid yield stress and hardening inputs fail closed with deterministic
`ValueError` diagnostics. Existing rollback rejection is retained as the
transactional failure-path evidence.

## External and adjacent capability evidence

The Code_Aster 18.1.0 J2 correlation from
`qualification/0_2_6/g06_depth_evidence.json` is reused as controlled
material-level evidence. It is not a new WP11 run and does not extend the
structural increment claim. The existing bounded buckling result is referenced
by provenance only; WP11 adds no buckling qualification. Modal, Newmark and
harmonic/dynamics gaps are outside this work package and remain unchanged.

## Maturity and limitations

No capability is promoted or demoted by WP11. The bounded small-strain J2
scope is better characterized on TET4, TET10, HEX8 and HEX20. The following
remain explicit limitations:

* no universal structural increment-independence threshold;
* algorithmic tangent symmetry is not separately Owner-qualified;
* full Newton is the accepted nonlinear route for this evidence;
* cyclic calibration, Bauschinger behavior and physical validation are out of
  scope;
* finite-kinematic J2 and coupled nonlinear routes remain experimental or not
  qualified;
* no full regression is run in WP11, by policy.

`FIXES_APPLIED = NONE`; `FUNCTIONAL_SOURCE_CHANGED = NO`.
