# WP-E01-U — Experimental Hencky global assembly V&V

## Scope and provenance

U implements an isolated experimental TET4/HEX8 total-Lagrangian Hencky assembly path and its bounded global-algebra test suite. It is not registered in public material dispatch and does not call the production nonlinear solver. The constitutive material and directional tangent are those from the previously tested WP-E01-Q path.

The testable source was frozen at source commit `b1ce4620a6dc0c2d4812a704b119fabab0bc227e` on branch `codex/wp-e01-uvw-hencky-global-newton-20261021`. The fixed-target invocation was run once, after static preflight and an independent read-only manifest review. The invocation was:

```text
C:/Python313/python.exe -m experiments.wp_e01uvw_global_supervisor
```

The supervisor performed collection and then the conditional run in one process. No test retry was made.

## Implemented formulation

For each reference quadrature point, the adapter forms `F = I + grad_X(u)`, obtains the Hencky PK1 stress from the material point, and assembles `f_int[a,i] = sum_q P[i,J] Grad_X(N_a)[J] dV0`. It assembles the consistent tangent from both the constitutive/material action and the geometric action `delta_F S`; the returned matrices are raw, unsymmetrized sparse matrices. The element tangent is scattered with canonical node-major UX/UY/UZ maps into the global operator.

The load convention is `R = F_int - lambda F_dead`; prescribed displacements are applied in the full vector before free residual extraction. The diagnostic uses `K_ff = P_f^T K P_f`, and rejects unsupported or numerically degenerate reduced spaces. This remains an experimental, dead-load-only algebra adapter. It is not the production `NonlinearAssemblyPlan` or a production solve route.

The TET4 rule is one positive-orientation centroid point. HEX8 uses the full 2x2x2 rule and `Grad_X N = Grad_xi N J^{-T}`. Current deformation admissibility is checked at integration points; a positive Jacobian between HEX8 points is not established by these tests.

## Collection and execution

The collection receipt accepted exactly 31 allowlisted `NUMERICAL_UNIT` nodes. Collection child PID 38144 exited 0 in 1.568067 s. The run child PID 40604 exited 0 in 3.591137 s; pytest reported `31 passed in 2.95s`.

| Outcome | Count |
|---|---:|
| PASS | 31 |
| FAIL | 0 |
| SKIP | 0 |
| XFAIL / XPASS | 0 / 0 |

Both phases ran with Job Object readback showing one active process maximum, breakaway disabled, kill-on-close enabled, and both process and job committed-memory caps set to 268,435,456 bytes. Peak committed memory was 53,534,720 bytes for collection and 87,248,896 bytes for run. Both phases completed below their 120 s deadlines. Active PID lists were `[38144]` / `[40604]` after resume and empty after exit; cleanup status was `VERIFIED_WINDOWS_JOB_CLOSED`. The receipt records no automatic retry.

The complete node inventory is in `wp_e01_uvw_execution_2026-10-21/20261021T170231Z/collection_nodes.json`; the accepted receipt and process evidence are adjacent. The runtime manifest pins the source commit and source map for this execution.

## Observed numerical results

Absolute and relative force values below are the actual stdout diagnostics from this run; they are not new universal acceptance limits.

| Check | TET4 | HEX8 |
|---|---:|---:|
| Single-element affine force absolute error (N) | 7.215421e-13 | 6.158779e-12 |
| Single-element affine force relative error | 1.064515e-15 | 3.028751e-15 |
| Single-element energy absolute error | 4.440892e-16 | 1.021405e-14 |
| Two-element shared-scatter force absolute error (N) | 2.905138e-12 | 1.192662e-11 |
| Two-element shared-scatter force relative error | 3.202894e-15 | 4.528428e-15 |
| Tangent norm, reference configuration | 7.894266555e5 | 1.198936429e6 |
| Tangent norm, affine state | 7.754107011e5 | 1.178520937e6 |
| Tangent split absolute discrepancy, affine | 6.537774e-11 | 1.306219e-10 |
| Geometric block reconstruction absolute discrepancy, affine | 0 | 2.952440e-12 |
| Relative tangent skew, affine | 1.709730e-16 | 9.758286e-17 |
| Reduced tangent condition estimate, 2-norm | 7.251096 | 112.4935 |
| Synthetic force-balance absolute error (N) | 4.196443e-14 | 1.136868e-13 |
| Synthetic moment-balance absolute error | 1.019135e-15 | 1.588822e-14 |
| Reaction norm (N) | 436.4841351 | 814.8778319 |
| Rigid-translation force difference (N) | 6.407387e-12 | 7.663700e-12 |
| Superposed-rotation force absolute difference (N) | 8.286281e-14 | 6.133036e-12 |
| Objectivity relative difference | 1.079284e-16 | 2.662749e-15 |

For the five free-DOF tangent steps `h=(2e-4,1e-4,5e-5,2.5e-5,1.25e-5)`, TET4 absolute derivative errors were `(0.38418571698, 0.09604625869, 0.02401153238, 0.00600286018, 0.00150082647)`, with successive ratios `(4.0000071,4.0000054,4.0000153,3.9997030)`. HEX8 errors were `(0.13773945462,0.03443486664,0.00860870723,0.00215219425,0.00053814138)`, with ratios `(3.9999997,4.0000044,3.9999676,3.9993101)`. These observed sequences support second-order centered-difference truncation over the measured windows. They do not establish a roundoff plateau or a general tangent acceptance criterion.

Global energy directional work agreed with the force-work reference to `8.881784e-15` for TET4 and `1.563194e-13` for HEX8. Centered energy-difference errors decreased over the four tested steps with observed ratios about `(4.0003, 4.0077, 3.9240)` for each family. The scalar diagonal constitutive formula and affine interpolation provide independent checks for the affine fixtures. The stress/tangent directional finite differences and the assembly adapter share the same material implementation, so those checks are consistency checks rather than a fully independent constitutive oracle.

## Scientific limitations and review

The independent read-only reviewer checked the quadrature/gradient conventions, `B^T A B` plus geometric stiffness, scatter maps, load/residual sign, free-DOF projection, and manifest/source identities. No P0/P1 issue was found.

Remaining P2 limitations:

* The material tangent block is formed as total tangent minus geometric block; that subtraction is not an independent material-block oracle.
* Reaction force/moment closure is a synthetic assembled-force closure; there is no independently solved support-reaction reference.
* Rotation/permutation/scale metamorphic checks reuse the same constitutive law.
* Positive HEX8 Jacobian is checked at quadrature points only.
* No path-dependent history, Newton convergence, line search, restart, crash durability, native FEM, or production route was exercised.

Consequently the results establish bounded in-memory global assembly algebra and a tested residual derivative for the selected small meshes. They do not establish global nonlinear solver convergence, material qualification, or production FEM readiness.

## Identity and evidence hashes

| Artifact | SHA-256 |
|---|---|
| Adapter `experimental_hencky_global.py` | `e02baaf346c3b8f853049990c8ac053b5e76ffab92f0a138f167f997cd2503b9` |
| Test `test_wp_e01uvw_global_assembly.py` | `10fba4667e3792cfeade6bb5a3be9db2cbeb9c2e59e994d4c0c895dc2102f84b` |
| Safety registry `tests/conftest.py` | `bccf52ec94f06653addb12f9219f842a08f74f30a8640cf295027f0ae73d9908` |
| Collection guard | `863c818a7e565dcb61a0831125bbf51ed08fcaac1b52c90a8fc07e4b3ed80463` |
| Supervisor | `39cf46747d032dc0144676cec537a691b3e105465dd8e28cfbbfc8c100ed0fdf` |
| Static manifest | `ed1b2b048a0e8e7a90eb67f61562bbff73a540f39d3ecc6bc14955a09ec8444a` |
| Runtime manifest | `29a990c82decdaee18c7ece0bd49aba6ed5c6a821484540d7bb870d71241fe63` |
| Persistent evidence hash index | `5efa622ec1b74a7edaa94dc9a4957071495182bee62ff90c7d79e6b089ea04d2` |
| Collection receipt | `31d45fab6b0f8f4ccfed9779373392fb7bceea338a548e1c8a0e8d807c3c20a5` |
| Collection nodes | `b69c51e172fb7c8b74cd271248baac7172fd235f0ad8942588e4e99fdb297ed2` |
| Preflight | `03ab51ed7925943dee71dee0b54396d19de217ca384447770c944474072da281` |
| Collection stdout | `f79300d89b12567d3c0b368824f0ece6585eebea000555973598d1c6da9d2a61` |
| Run stdout | `dcea2700855f90fe748eb6cc7c8b4fe5aebeda63b20716835eb13740544297f1` |
| Run results | `238e2e3700cdf68413a82b64d171a5c296cf2ab84ef0c8d3000c68fca4b42137` |
| Summary | `8a7bd168458e66f6a9accc0b8fc038791b9801378683c6cffd64598b559a038c` |

Empty stderr logs have the SHA-256 of the empty file, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Both phase-result files and the summary are also individually listed in `evidence_hashes.json`.

## Status

* `HENCKY_GLOBAL_ASSEMBLY`: `VERIFIED_BOUNDED` for the 31 listed in-memory algebra cases.
* `HENCKY_GLOBAL_TANGENT`: `VERIFIED_BOUNDED` for the tested free-space directions and states; no general criterion is approved.
* `HENCKY_ELEMENT_TANGENT_VNV`: remains prior bounded evidence; U adds global scatter and reduced residual checks.
* `HENCKY_GLOBAL_NEWTON`: not run in U; authorized next-stage work may proceed.
* `NATIVE_FEM`, `FINITE_STRAIN_J2`, scientific qualification: not run / not implemented / not acquired.
* `WP_E01`: `OPEN / EXPERIMENTAL_TARGET`.
