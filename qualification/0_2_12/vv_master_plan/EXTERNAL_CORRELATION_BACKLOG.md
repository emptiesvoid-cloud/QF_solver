# External solver correlation backlog

**Status:** PREPARATION_ONLY; no Code_Aster or CalculiX run performed.
**Execution:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

External agreement is numerical correlation between implementations. It is not experimental physical validation and does not prove either model is correct. A comparison becomes useful only after the element, formulation, integration, material, constraints, load resultant, units, sign, output point and observable have been mapped.

## Classification

- **EXTERNAL_REFERENCE_FEASIBLE:** a reasonably matched case exists and the comparison path is understood.
- **EXTERNAL_REFERENCE_CONDITIONAL:** plausible after specified formulation/output mapping or environment check.
- **EXTERNAL_REFERENCE_NOT_AVAILABLE:** no appropriate external implementation/route has been identified for the claim.
- **EXTERNAL_REFERENCE_NOT_NEEDED:** an exact independent analytical/algebraic oracle is more direct for the bounded claim.

## Candidate portfolio

| Domain/case | Class | Existing repository path | Comparison scope and prerequisites |
|---|---|---|---|
| TET4/TET10 static displacement and reactions | EXTERNAL_REFERENCE_FEASIBLE | `src/solveur/verification/code_aster_tet4_static.py`; `src/solveur/verification/code_aster_tet10_static.py`; `tests/verification/test_code_aster_tet4_dynamic_vnv.py` | Match mesh, material convention, constraints, traction/resultant, element integration, solution observable and solver tolerances. Historic report identities remain separate from frozen-candidate execution. |
| TET4/TET10 modal and transient response | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_tet4_dynamic.py`; `src/solveur/verification/code_aster_tet10_dynamic.py`; `tests/verification/test_code_aster_tet10_dynamic_vnv.py` | Match consistent/lumped mass, boundary conditions, modal normalization, damping, Newmark parameters, time grid and interpolation. The same input label is insufficient. |
| BEAM2 static/modal/transient | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_beam2.py`; `code_aster_beam2_modal.py`; `code_aster_beam2_newmark.py`; corresponding tests under `tests/verification/` | Code_Aster beam formulation/shear and mass conventions must be mapped. Separate axial, bending and shear claims; current one-case evidence does not automatically establish multi-element convergence. |
| MITC3/MITC4 shells and laminate response | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_mitc3.py`; `src/solveur/verification/code_aster_mitc3_hemisphere.py`; `src/solveur/verification/calculix_mitc4_conical_cutout.py`; MITC verification tests | Often the external element is not identical. Compare converged observables on both meshes and preserve differences in interpolation, drilling DOF, layer recovery and integration. CalculiX may be a better reference for selected composite cases. |
| Linear buckling | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/` buckling and Code_Aster routes; `tests/verification/test_028_hex8_buckling_vnv.py` | Verify the pre-stress state, eigenproblem, load scaling and boundary conditions. Postbuckling/imperfection is a separate nonlinear problem. |
| Frictionless contact | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_contact.py`; contact verification tests | Match contact surface pairing, normal convention, penalty/augmented formulation, search, active set and output reduction. Preserve WP-C01 negative evidence. |
| Frictional contact | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_friction_contact.py`; `tests/verification/test_code_aster_friction_contact_vnv.py` | Match Coulomb coefficient, regularization, slip convention, search update and load stepping. C02 closure remains AR/N03 only; external Docker limits and absent overlay must be resolved before replay. |
| RBE2 | EXTERNAL_REFERENCE_FEASIBLE for one historical bounded case | `src/solveur/verification/code_aster_rbe.py`; `tests/verification/test_code_aster_rbe_vnv.py` | One historical single-case comparison exists; it is not a general RBE2 certificate. Current integration identity and Owner completion decision remain distinct. |
| RBE3 rigid projection / weighted | EXTERNAL_REFERENCE_NOT_AVAILABLE in current records | `src/solveur/core/rbe.py`; RBE reports | No matching RBE3 external reference was available in the inspected report. Keep algebraic weighted least squares and wrench oracles; do not imply external validation. |
| J2 material-point / bounded patch | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/code_aster_j2.py`; `src/solveur/verification/rqg08_external_j2.py`; related verification tests | Match yield/hardening, stress measure, loading path, state convention and reaction extraction. Existing RQ-G08 is a bounded affine patch correlation, not cycles, mesh convergence, or global qualification. |
| Composite laminate/ply stress | EXTERNAL_REFERENCE_CONDITIONAL | `src/solveur/verification/calculix_composite.py`; conical-cutout and ply-stress modules | CalculiX routes are available for selected cases; shell order and integration differ. Require convergence in both formulations and fixed ply/location observables. |
| Reduced harmonic/Newmark | EXTERNAL_REFERENCE_CONDITIONAL | current route-specific verification and external dynamics sources | Compare full-order physical response only when mass, damping, excitation, constraints, state and sampled times/frequencies agree. Internal direct-vs-reduced agreement is a separate check. |
| Rotor QEP/Campbell | EXTERNAL_REFERENCE_NOT_AVAILABLE as a general external model | `src/solveur/core/analyses/rotating_modal.py`; `campbell.py`; v0.2.11 contracts | Use independent small matrix/QEP oracles. Do not invent a Code_Aster equivalence for disk gyro, branch tracking, distributed rotor physics, or the 100 rad/s ambiguity. |
| Hencky and finite-strain experimental kernels | EXTERNAL_REFERENCE_NOT_AVAILABLE for a production route | `src/solveur/materials/`; WP-E01 reports | Source-level experimental material-point checks do not map to a public assembled route; no general cross-solver claim. |
| Sparse/MPI/PETSc large workflow | EXTERNAL_REFERENCE_CONDITIONAL / NOT_AVAILABLE for scaling claims | `src/solveur/large/`; backend tests | A second code can compare small numerical outputs but does not demonstrate QF scaling. Mock readiness tests are not multi-node execution evidence. |

## Historical external evidence

The repository includes older Code_Aster and CalculiX reports. The v0.2.9 R2/R4 Code_Aster tasks and later RBE/J2/MITC/composite cases have their own commit, input, container, and extraction identities. They must not be counted as v0.2.12 runs unless a report explicitly binds them to the frozen science tree. WP-C02’s Docker limitation and missing identity-bound helper are retained; Docker is an optional future external-comparison environment, never a prerequisite for local V&V.

## Entry gate for each correlation

Before launching an external comparison, approve a case-level mapping table containing: element/interpolation, integration, material constants and axes, coordinate systems, constraints/MPC, load resultants and signs, solver controls, output variable/point, unit conversions, mesh sequence, reference uncertainty, and the exact external executable/version. If any of those changes the governing equations or observable, classify the result as a cross-formulation study and do not use a single-mesh PASS threshold.
