# WP08: Nonlinear Stress Measures / Semantic Migration

**Status:** BLOCKED — RESCOPE_REQUIRED
**Branch:** codex/v0.2.12-wp08-nonlinear-stress-measures
**Baseline / base commit:** f85b6ad589a67e40782ff65b2e69e0e9e937e00a
**Scope:** audit and bounded diagnostics only. No numerical source or historical record was changed.

## Stop decision

WP08 cannot safely repair the corotational stress output by changing names or post-processing alone. The stress tensor used to form the existing internal force is P = R sigma_local, where sigma_local is produced by an additive small-strain J2 update on sym(U-I), with F = R U. The independent transformations

    S_alg = solve(F, P) = U^(-1) sigma_local
    sigma_alg = P F^T/J = R sigma_local U R^T/J

are algebraically well-defined for admissible invertible F, but both are required to be symmetric for the classical no-couple continuum interpretation claimed by second-Piola and Cauchy stress. They cease to be symmetric when the local plastic stress and right stretch are non-coaxial. The measured skew is far above roundoff and is tied to the existing internal-force tensor, not just to a mislabeled JSON field.

Fixing this while retaining physically meaningful P, S, Cauchy stress and the existing force response requires a constitutive/kinematic or force-mapping change. That is beyond a semantic migration and triggers the frozen WP01/WP00 rule. No symmetrization, constitutive update change, force change, postprocessor relabeling, or maturity change is made here. RESCOPE_REQUIRED is the next decision point for the Owner.

## Baseline and preservation

The dedicated branch was created from the exact WP07 commit above. The worktree was clean before this record was added. The published tag remains v0.2.11 -> afd2efa469a18e66581720ff4801f50de7d29eb4. The WP07 commit is an ancestor of this branch; the WP06 commit is also an ancestor. origin/main remains e367fe58b2b9ebb4aef321424ca775e80e82d9ca. No WP08 remote branch existed at audit time.

No historic result, qualification decision, checkpoint, or artifact was rewritten. The following remain unchanged:

    HISTORICAL_G03 = FAIL_PRESERVED
    HISTORICAL_WP14 = HOLD_NOT_PROMOTED
    WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO
    MATURITY_PROMOTION = NONE

## Producer and consumer audit

| Producer | Field | Actual payload / measure | Frame or configuration | Consumer | Serialization / export | Historical semantics | Correction required |
|---|---|---|---|---|---|---|---|
| _CorotationalJ2Mixin._force_and_states() in src/solveur/elements/solid/corotational_j2.py | stress, local_stress | Six-component additive small-strain J2 response sigma_local; stress-like local tensor, but not proven to be a finite-strain Cauchy or Piola measure conjugate to U-I | Element-corotated frame | Corotational stress postprocessing and generic principal/von-Mises recovery | SolveResult.to_dict(), nested integration-point JSON, CSV; generic VTU scalar projections | Legacy field meaning is implicit and has no semantic version/frame metadata | Yes; do not silently reinterpret |
| Same | first_piola_stress | R sigma_local, the nominal tensor used by the current internal-force assembly | Mixed spatial-force/reference-gradient components in the model basis; constitutive validity is not established by the name | Corotational integration-point result only; force assembly uses the same expression | JSON/CSV pass-through | Presented as first Piola without a constitutive-consistency qualification | Yes; physical interpretation unresolved |
| Same | second_piola_stress | The matrix sigma_local itself, not F^(-1)P in general | Element-corotated local frame, not identified as reference-configuration components | StressPostProcessor._total_lagrangian_j2_result() copies it into each corotational integration-point result; CSV/JSON consumers can observe it | JSON and nested CSV | Incorrect historical label; WP01 says preserve it as unresolved legacy meaning | Yes; confirmed semantic defect |
| Same | cauchy_stress | Algebraic P F^T/J; not symmetric for non-coaxial histories | Current/model spatial basis | Corotational integration-point output; generic nodal/element scalar recovery is separately based on stress, not this field | JSON/CSV pass-through; VTU exports generic stress-derived scalars | Called Cauchy without proving angular-momentum consistency | Yes; do not claim a physical Cauchy measure for the failing history |
| TotalLagrangianJ2*Element.integration_point_results() in src/solveur/elements/solid/total_lagrangian_j2.py | second_piola_stress, cauchy_stress | TL J2 stress from Green-Lagrange strain is used as S; P=F S; Cauchy is formed from F S F^T/J | Reference configuration for S; current configuration for Cauchy | TL postprocessor and geometric assembly | JSON/CSV; geometric result payload | Separate TL route; not produced by the corotational mixin | No WP08 defect inferred from the corotational finding; preserve and test separately |
| build_total_lagrangian_assembly()/element_states() in src/solveur/core/assembly/geometric.py and src/solveur/core/analyses/geometric_nonlinear.py | second_piola_stress | Consumes the separate TL element kernel's S for geometric tangent and reporting | Reference configuration | Geometric nonlinear analysis | SolveResult JSON | TL-specific, not the corotational producer | No change authorized or needed from this finding |

StressPostProcessor._total_lagrangian_j2_result() uses corotational raw stress for generic principal/von-Mises values and aggregate/nodal recovery, then copies raw second_piola_stress and cauchy_stress into integration-point output. It also averages local Voigt components across integration points without transforming differing local frames to a common frame.

SolveResult.to_dict() passes element_results and nodal_results through without stress-semantic versioning. CsvResultWriter recursively flattens these structures. VtuResultWriter exports generic von Mises, trace and principal-stress arrays; those values originate from the local response on the corotational path and carry no frame/measure marker. There is no evidence that the geometric Total-Lagrangian assembly consumes the corotational second_piola_stress; it builds its own TL kernels. The defect must not be generalized to that route, buckling, or other J2 formulations without separate evidence.

## Preregistered diagnostic definitions

Before evaluating the reported cases, the following diagnostic thresholds were fixed:

    tensor transformation residual <= 1e-12 * max(||reference||_F, 1 Pa)
    relative skew = ||T - T^T||_F / max(||T||_F, 1 Pa)
    symmetry diagnostic threshold = 1e-10

The symmetry threshold is a diagnostic for a tensor asserted to be symmetric, not a qualification threshold or a post-hoc pass criterion. Tensors below the 1 Pa scale are not classified by a relative-skew-only check. No threshold was relaxed after observing results.

An independent NumPy calculation formed P, solved F S=P, and formed P F^T/J; it did not call the stress postprocessor or use its derived stress fields. The element force implementation was used only to obtain the constitutive response and to check its internal-force moment identity.

## Numerical observations

Fixture: unit linear TET4, E=210 GPa, nu=0.3, yield stress 250 MPa, isotropic hardening 1 GPa, and the existing ||U-I||_F <= 0.05 corotational bound. The two-step path used

    F1 = diag(1+a, 1-a/2, 1-a/2)
    F2 = Qz(0.42) diag(1+0.85a, 1-0.45a, 1-0.40a) Qz(0.42)^T

and carried the committed trial material state from step 1 to step 2.

| a | Step-2 equivalent plastic strain | rel_skew(S_alg) | rel_skew(sigma_alg) | Step-2 ||U-I||_F |
|---:|---:|---:|---:|---:|
| 0.0015 | 0.0004663 | 5.9906e-4 | 5.9872e-4 | 0.00156245 |
| 0.002 | 0.0011020 | 1.3769e-3 | 1.3762e-3 | 0.00208327 |
| 0.003 | 0.0026198 | 2.8949e-3 | 2.8939e-3 | 0.00312490 |
| 0.005 | 0.0058375 | 5.6263e-3 | 5.6261e-3 | 0.00520817 |
| 0.01 | 0.0140769 | 1.1981e-2 | 1.1987e-2 | 0.0104163 |
| 0.02 | 0.0306638 | 2.4377e-2 | 2.4408e-2 | 0.0208327 |

All paths are inside the existing corotational strain bound. The skew is between roughly 6e-4 and 2.4e-2, not numerical roundoff. At a=0.02, the unit-TET4 nodal internal-force resultant torque was [0, 0, 661464.4237900935] in the fixture's force units. Independently, reference volume times the axial skew of P F^T gave [0, 0, 661464.4237900872], a relative difference of 9.50e-15. This confirms the skew is mechanically coupled to the current force stress, rather than introduced by export formatting.

For the affine coaxial stretch F=diag(1.01,0.995,1), the old field contains sigma_local, while the independently calculated F^(-1)P differs from it by 7.1688e-3 relative. Coaxiality makes both transformed tensors symmetric in this case, but does not make the old field equal to second Piola stress.

Under a superposed rigid rotation of 0.71 rad applied to the entire same two-step history, covariance/invariance residuals for local stress, P, algebraic Cauchy and S_alg were each about 1.5e-13. The Cauchy skew stayed 1.9457e-2. Thus this test supports objectivity of the algebraic transport for the fixture, but does not establish constitutive angular-momentum consistency.

The transform identities passed at roundoff in the sampled invertible cases. This is not a physical validation of the constitutive law. The current producer rejects det(F) <= 1e-10; it does not expose an explicit condition-number policy. A determinant rejection test alone would not resolve the observed consistency issue.

## Classification

| Observation | Classification | Finding |
|---|---|---|
| second_piola_stress equals sigma_local rather than F^(-1)P | SEMANTIC_DEFECT and ALGEBRAIC_TRANSFORMATION_DEFECT | Confirmed; the field payload is the wrong tensor for its name. |
| P=R sigma_local gives nonsymmetric S_alg and Cauchy after non-coaxial plastic history | CONSTITUTIVE_CONSISTENCY_ISSUE | Confirmed within the accepted small-corotational-strain domain; not roundoff and not an export-only issue. |
| Superposed rigid-rotation covariance of the tested algebraic tensors | No defect observed in this fixture | Does not negate the angular-momentum issue. |
| Total-Lagrangian J2 / geometric consumer | OUT_OF_SCOPE for this defect | Separate producer/assembly; no blanket defect claim. |

## Tests and campaign status

The existing focused regression set passed:

    python -m pytest -q tests/unit/test_corotational_j2.py tests/unit/test_tet4_tl_stress.py tests/unit/test_total_lagrangian_tet4_batch.py tests/unit/test_wp01_shared_contracts.py
    33 passed in 7.56 s

These tests establish legacy behavior and separate TL route regressions; they do not validate physical consistency of the corotational stress history. The full unit suite, documentation suite, Ruff, formatting and typing were not run because the required rescope stop prevents implementation/closure work. No WP08 production test was added. The current existing corotational test checks post-processing labels but does not establish the tensor identity for S or symmetry of reconstructed Cauchy stress.

## Gate and rescope

| Gate sub-check | Status | Reason |
|---|---|---|
| QF0212_G03_NL stress measure formulation | BLOCKED | Constitutive/force consistency unresolved. |
| QF0212_G04_NL noncoaxial stress behavior | BLOCKED | Accepted-domain history produces material skew and internal moment. |
| QF0212_G05 interfaces / migration | NOT_YET_APPLICABLE | No prospective output or serializer change was implemented. |

Required Owner decision: rescope the corotational formulation/force mapping as a distinct nonlinear mechanics task, or explicitly narrow/disable claims and outputs through an authorized contract. WP08 must not silently choose either path. Until that decision and subsequent technical work, do not claim second_piola_stress or cauchy_stress as physically validated for the noncoaxial corotational plastic route. No WP09 tangent change was started.

**WP08 verdict:** BLOCKED
**Production numerical source changed:** NO
**Historical records changed:** NO
**Maturity promoted:** NO
