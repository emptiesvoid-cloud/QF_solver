# WP16 - True 1M DOF qualification

## Decision

WP16 is **FAIL** under the frozen WP14 contract and remains a release blocker.
This is a negative qualification result, not a change to the numerical
formulation or to the acceptance criteria.

The official model contains 343,000 nodes, 1,971,054 structured six-tet TET4
elements and 1,029,000 true displacement DOF. It uses the WP14 SI material,
fixed `x=0` face, uniform 1,000,000 N nodal load on `x=1`, matrix-free CG,
nodal block-Jacobi, chunk size 4096, `rtol=1e-8`, `atol=0` and `maxiter=10000`.
The execution source SHA is
`15534b87387c3bd73c73971703e22bf275ffc8cc`.

## Run 1

The complete model-to-solve path completed in 1,371.06 s and 1,052 CG
iterations. The displacement is finite, the relative free residual is
`9.8225e-9`, the energy balance is `1.9195e-16`, and the deterministic SPD
probe passed. Peak RSS sampled by the evidence runner was 575,700,992 bytes.

The frozen reaction/equilibrium observable failed: the relative balance was
`3.81975e-8`, above the WP14 maximum `1e-8`. Because the criterion is frozen,
this result cannot be promoted to `1M_PASS` and no retuning was attempted.

## Subscale equivalence

The current source was rechecked against the assembled SciPy CG route on the
four WP14 subscale levels (81, 375, 2,187 and 14,739 DOF). Maximum errors were:

| Observable | Maximum relative error | WP14 limit |
| --- | ---: | ---: |
| Operator action | 1.25e-14 | 1e-8 |
| Displacement | 3.45e-13 | 1e-8 |
| Reaction | 2.30e-9 | 1e-8 |
| Strain energy | 3.36e-14 | 1e-8 |

The machine-readable record is
`qualification/0_2_7/wp16_runtime/wp16_subscale_current.json`.

## Replay and next step

WP14 requires a second independent replay only after a first 1M PASS. Since
run 1 failed the equilibrium criterion, run 2 was not launched. The complete
machine-readable run record is
`qualification/0_2_7/wp16_runtime/wp16_run1.json`, with the WP16 state in
`qualification/0_2_7/wp16_state.json`.

No 1M qualification claim is made. WP17 may address backend/resource or
solver-path evidence, but it must not alter WP14 tolerances or relabel this
negative result.
