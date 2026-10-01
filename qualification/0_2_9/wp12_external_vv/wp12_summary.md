# WP12 — Code_Aster multi-family external correlation

Status: **FAIL_CLOSED**

| Famille | Statut | Δu L2 | Δu L∞ | Δréaction L2 | énergie externe |
|---|---|---:|---:|---:|---:|
| TET4 | FAIL_CLOSED_EXECUTION | n/a | n/a | n/a | n/a |
| HEX8 | FAIL_CLOSED_EXECUTION | n/a | n/a | n/a | n/a |
| TET10 | FAIL_CLOSED_EXECUTION | n/a | n/a | n/a | n/a |
| HEX20 | FAIL_CLOSED_EXECUTION | n/a | n/a | n/a | n/a |

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
