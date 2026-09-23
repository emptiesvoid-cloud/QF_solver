# WP12 — Code_Aster multi-family external correlation

Status: **PASS_CANDIDATE**

| Famille | Statut | Δu L2 | Δu L∞ | Δréaction L2 | énergie externe |
|---|---|---:|---:|---:|---:|
| TET4 | PASS | 1.7816197808834443e-16 | 1.7816197808834443e-16 | 2.625485054475693e-16 | 1.8243786556246468e-16 |
| HEX8 | PASS | 7.501039756768504e-16 | 1.2402436043719e-15 | 1.0462640403296646e-15 | 7.93755906798016e-16 |
| TET10 | PASS | 4.733651614165304e-15 | 4.152424917460272e-15 | 6.043100203873072e-15 | 4.252083115479319e-15 |
| HEX20 | PASS | 1.2096814517532255e-14 | 1.619317582996786e-14 | 1.3582566582890024e-14 | 1.110061525831259e-14 |

Official points remain `0/4` pending explicit Owner review.

## Limitations

- one homogeneous one-element static elastic case per listed family only
- Code_Aster correlation applies only to the exact WP11 M1 mesh, material, fixed DOFs and nodal load vector
- TET4 and TET10 apply the resultant at the single x=1 vertex; this is not a face-load test
- HEX20 uses the explicit QF-to-Code_Aster local connectivity permutation frozen above
- no mesh-convergence, stress-field equivalence or cross-family equivalence claim
- no WP04/WP05 geometric nonlinearity, WP06 arc length, WP07/WP08 contact or friction correlation
- no WP09/WP10 J2 or coupled nonlinear correlation
- no dynamics, MPI/PETSc, scaling or general solver validation claim
- the Code_Aster run is a separate external FEM solve but shares the frozen mathematical model and is not experimental validation
