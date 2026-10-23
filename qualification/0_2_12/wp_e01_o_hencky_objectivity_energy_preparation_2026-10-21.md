# WP-E01-O — Hencky Objectivity and Energy-Derivative Preparation

Date: 2026-10-21
Branch: `codex/qf-wp-e01-m-logarithmic-strain-20261021`
Scope: test and execution-profile preparation only; no collection or numerical execution.

## Outcome

The historical WP-E01-N result remains **36 collected, 35 passed, 1 failed**. The sole failed node and original output are preserved at `qualification/0_2_12/wp_e01_n_runs/20261021T132318Z/run/stdout.log`.

The failed node was `test_left_rotation_of_stretch_is_objective_for_all_stress_measures`. It compared an off-diagonal PK2 value of `9.57020104e-06 Pa` against exact zero using NumPy's default `atol=0`. Thus, for that component, `rtol` allowed no nonzero error. The earlier strain, energy and logarithmic-conjugate-stress checks passed; the test stopped before PK1 and Cauchy covariance. This remains historical failure evidence and is not relabeled as a pass.

The prepared module has a static inventory of **23 test functions and 41 AST-estimated cases**. This is not an observed pytest collection count. The revised tests were neither collected nor executed.

## PK2 scale and proposed comparison

For the original deformation `F = diag(1.25, 0.92, 1.08)`, the printed PK2 components imply a Frobenius norm of approximately `4.9731e10 Pa`. This is reconstructed from rounded log values. The recorded residual is about `1.92e-16` of that norm, or `0.87` binary64 epsilons. This is consistent with roundoff in `C=F^T F`, the symmetric eigensolve/reconstruction, and rotation products; it does not establish PK2 accuracy for other spectra.

The tested `C` eigenvalues are `0.8464`, `1.1664`, `1.5625`; hence `cond_2(C) ≈ 1.8461` and `cond_2(F) ≈ 1.3587`. The deformation is well conditioned.

The prepared comparison is

```text
||A_rot - A_ref||_F <= atol_S + rtol_S * max(||A_rot||_F, ||A_ref||_F)
atol_S = 64 * eps64 * max(mu, kappa)
rtol_S = 2e-13
```

For the base material (`mu=80 GPa`, `kappa=160 GPa`), the absolute term is about `2.27e-3 Pa`; the existing relative term at the historical stress norm is about `9.95e-3 Pa`, giving a total near `1.22e-2 Pa`. The relative coefficient is unchanged from the former componentwise assertion, but is applied to a tensor norm so an exact-zero component does not get zero tolerance. The modulus-scaled floor accounts for bounded binary64 matrix, eigensolve/reconstruction and push-forward operations over these well-conditioned fixtures. Both terms are **proposed test allowances**, not Owner-frozen or universal stress tolerances. The absolute term scales with `kappa` in the higher-bulk-modulus case.

A separate read-only reviewer independently agreed that the historical mismatch is a zero-component tolerance defect consistent with roundoff and recommended a normwise comparison with a modulus-scaled floor. The reviewer did not execute tests or numerical probes. The estimates above are based on the preserved printed data and source-level analysis.

## Prepared objectivity tests

For a proper rotation `Q`, the test checks the transformation identities

```text
C(QF)=C(F),  J(QF)=J(F),  E_H(QF)=E_H(F),  W(QF)=W(F)
S(QF)=S(F)
P(QF)=Q P(F)
sigma(QF)=Q sigma(F) Q^T
```

The same nontrivial proper rotation is applied to six deformation/material cases:

1. Historical stretch `diag(1.25, 0.92, 1.08)`.
2. Repeated stretches `diag(1.1, 1.1, 0.9)`.
3. Positive clustered stretches with relative split `1e-10`.
4. Simple shear of `0.4`.
5. Nonsymmetric general 3D shear/stretch map.
6. Isochoric stretch with `kappa` set to `1000` times the base value, as a bounded nearly-incompressible material case.

Each case records `cond(C)`, relative eigenvalue gap, PK2 norm and normwise errors/limits for logarithmic-conjugate stress, PK2, PK1 and Cauchy stress. It checks the generated `Q` against binary64-scale orthogonality and determinant bounds. The cases and allowances are unexecuted; repeated/clustered-spectrum behavior still needs numerical evidence.

## PK1 energy-derivative diagnostics

For direction `D`, the multi-step sweep forms

```text
D_h = [W(F + h D) - W(F - h D)] / (2 h)
g = P(F) : D
```

with `h = 1.024e-3, 5.12e-4, 2.56e-4, 1.28e-4, 6.4e-5, 3.2e-5, 1.6e-5, 8e-6, 4e-6, 2e-6`. The three retained directions are axial entry, simple-shear entry, and mixed 3D. The output records absolute error, normalization by `max(|g|, ||P||_F ||D||_F, 64 eps max(mu,kappa))`, Richardson estimates, observed order only while errors exceed the estimated subtraction-roundoff floor, `cond(C)`, relative spectral gap, minimum eigenvalue of `C`, minimum `J`, and admissibility of both perturbed states.

The previous threshold at `h=2e-6`, `|D_h-g|/max(|g|,1) <= 2e-7`, remains unchanged. The added step sweep does not add a new accuracy gate; it reports whether a sequence shows an `O(h^2)` region, becomes roundoff limited, or is inconclusive. Its `plateau_estimate` only flags adjacent estimates differing by no more than the rough energy-subtraction estimate; it is not proof of convergence.

The generic directional sweep compares returned PK1 work with differences of returned energy, so it is explicitly a **kernel self-consistency check**, not an independent oracle. A separate uniaxial sweep compares energy differences with the independently derived scalar reference

```text
dW/dlambda = (4 mu/3 + kappa) * log(lambda) / lambda
```

for `F=diag(lambda,1,1)`. The same formula is used to check `P11`; it follows by differentiating the declared uniaxial energy and does not call the PK1 transformation routine. No sweep values are claimed here.

## Test identity and execution preparation

The future fixed parent invocation is:

```text
C:/Python313/python.exe -m experiments.wp_e01o_hencky_supervisor
```

After a separate exact Owner GO, this parent performs guarded collection, requires 41 unique nodes with the pinned function/fixture inventory and `numerical_unit` marker, rechecks input hashes, then runs that same module once. Each child is created suspended, assigned to a Windows Job Object before resume, and is subject in source to 256 MiB per-process and job committed-memory caps, a 120-second parent deadline per phase, active-process limit one, kill-on-close, and no breakaway. It stores phase logs, structured results and evidence hashes under the isolated WP-E01-O output directory. This new profile was reviewed by source only; resource enforcement has not been runtime verified.

The target remains `NUMERICAL_UNIT`; its classification was not broadened. Static AST review finds only `numpy`, `pytest`, `solveur`, and `__future__` imports, no public-solver/process/network/Gmsh imports or calls, and no test-side filesystem-mutator calls. The test imports the pinned Hencky module through `solveur.materials`; the package initializer imports pinned Python material definitions. The shared Gmsh capability probe is conditional on the optional mesh-test set, which does not include this target. The explicit guard validates the exact target, node and fixture inventory, marker, and hashes.

The child uses `python -S`; therefore `sitecustomize` is not loaded, and neither the manifest nor supervisor claims sitecustomize native-loader interception. The safety basis is the pinned target/import path, exact-module collection guard, disabled pytest plugin autoload, and Job Object process containment. NumPy native numerical-library extensions are part of the allowed algebra path; no native FEM backend or Gmsh route is selected. The supervisor itself was not launched.

### Frozen and prepared identities

| Artifact | SHA-256 | Meaning |
|---|---|---|
| Historical test module | `55e8cb65c77f724799b40415451759dc8a99f980194e95c4ccb2eacfadec6e83` | WP-E01-N identity; 35/36 with one failure |
| Prepared test module | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` | WP-E01-O target; static 41 cases, not collected |
| Safety registry | `33304c38c2ef53aca2b3abc647e490db91245e56b1eb8d04963db1c86e9d8605` | Target remains `NUMERICAL_UNIT` |
| Collection guard | `a9ff067c68887d2d0a291acaf847ee4be1548f4120ce789ca39395760caaa945` | Fixed-target 41-case gate |
| Supervisor | `462a279b1f79b240c8dbb7f2f79cd42c15ce1a8f68c994b5bc93ca4678c9cd5a` | WP-E01-O fixed-target Job Object profile |
| Runtime execution manifest | `7d6167670a8a1dee67c9de41fd0928e6535de16f17259ac81505dd6d78335121` | Prepared; collection/run not authorized here |
| Production Hencky kernel | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` | Preserved unchanged |
| Job Object helper | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` | Pinned existing helper |
| Historical WP-E01-M manifest | `42ca471ba4ae6379efa819573ed1c19f743754f48b4d21213bbc2673fdde75ed` | Preserved and pinned |

All 26 historical source-map entries were checked: the 24 non-target/non-registry entries match their prior hashes; the target and registry entries use the updated hashes above. The guard and supervisor each bind target and registry hashes. The runtime manifest binds target, kernel, registry, guard, supervisor, helper, Python/pytest/NumPy profile and the full source map. Its digest is listed separately for the next Owner GO to bind alongside the final committed HEAD.

## Future consistent total-Lagrangian tangent

For `C=F^T F`, `E_H=1/2 log(C)`, and `M_H=dW/dE_H=2 mu dev(E_H)+kappa tr(E_H) I`, the work-conjugate PK2 stress is `S=D log_C[M_H]`. For `H=dF`:

```text
dC = F^T H + H^T F
dE_H = 1/2 D log_C[dC]
dM_H = 2 mu dev(dE_H) + kappa tr(dE_H) I
dS = D^2 log_C[dC, M_H] + D log_C[dM_H]
dP = H S + F dS
A:H = dP
```

The future tangent requires stable first and second Fréchet derivatives of the symmetric matrix logarithm, including confluent divided-difference limits for repeated/clustered positive eigenvalues. Verify the material-point action `A=dP/dF` independently before forming element stiffness. In total-Lagrangian assembly, separate constitutive/material `F dS` and initial-stress/geometric `H S` terms. The current material remains force-only: no consistent tangent is implemented, integrated or qualified.

## Review, status and next Owner GO

The separate read-only reviewer examined the old trace, scale argument, stress transformations and diagnostic design. This is independent source/evidence review, not an independent numerical run. The old zero-component mismatch does not demonstrate a production defect; it demonstrates that the old componentwise comparison had no allowance for nonzero roundoff against exact zero. The broader transformation claims and new diagnostics remain unverified.

| Status | Result |
|---|---|
| `HENCKY_PREVIOUS_VNV` | `35_PASS_1_FAIL` |
| `PK2_OBJECTIVITY_CORRECTION` | `PREPARED_NOT_RUN` |
| `FULL_STRESS_OBJECTIVITY` | `PREPARED_NOT_RUN` |
| `PK1_ENERGY_DERIVATIVE` | `PREPARED_NOT_RUN` |
| `HENCKY_CONSISTENT_TANGENT` | `NOT_IMPLEMENTED` |
| `GLOBAL_HENCKY_FEM` | `NOT_RUN` |
| `FINITE_STRAIN_J2` | `NOT_IMPLEMENTED` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

No production material, public route, historical report, or WP-E01-N execution artifact changed. No collection, pytest, numerical sweep, FEM, Gmsh, public solver, or worker ran.

The next Owner GO should authorize one guarded collection and, only if it records exactly the 41 authorized nodes, one execution through the fixed parent command above. Bind it to the then-current clean HEAD, this report, the runtime manifest SHA above, test/registry/guard/supervisor hashes above, and unchanged kernel/helper hashes. Do not authorize source or threshold changes under that executable identity. Keep the objectivity allowances proposed and the Hencky tangent unimplemented.
