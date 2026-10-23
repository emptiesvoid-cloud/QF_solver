# WP-E01-Q — Analytic Consistent Hencky Tangent

Date: 2026-10-21

Worktree: `C:/wpc01-frictionless-public-integration-wt/wp-e01-q`

Branch: `codex/qf-wp-e01-q-hencky-tangent-20261021`

Starting HEAD: `3972d68418b45a8e0b3529b6786917732f74ede9`

## Outcome

An isolated material-point directional action `A(F)[delta_F] = delta_P` is implemented in a new module. The existing Hencky response, its explicit `tangent_status="NOT_IMPLEMENTED"`, the public material dispatch, TET4/HEX8 force-only adapters, and all solver routes remain unchanged. No flattened 9x9 tangent was exposed because no component-flattening contract is established.

The accompanying focused numerical test module is prepared and registered as `NUMERICAL_UNIT`, but it was not collected or run. The 41/41 WP-E01-P3 result remains historical evidence for its frozen material-point test/kernel identity; it is not evidence for this new tangent.

## Mathematical definition and implementation

The implemented material remains the existing quadratic logarithmic-strain law:

```text
C = F^T F
E_H = 1/2 log(C)
M_H = 2 mu dev(E_H) + kappa tr(E_H) I
S = Dlog(C)[M_H]
P = F S
```

For a reference-basis perturbation `delta_F`, the directional derivative is assembled as:

```text
delta_C = F^T delta_F + delta_F^T F
delta_E_H = 1/2 Dlog(C)[delta_C]
delta_M_H = 2 mu dev(delta_E_H) + kappa tr(delta_E_H) I
delta_S = Dlog(C)[delta_M_H] + D^2log(C)[delta_C, M_H]
delta_P = delta_F S + F delta_S
```

The returned tensor is `delta_P` in the first Piola–Kirchhoff measure, with the same stress units as `mu` and `kappa`. Inputs and outputs are ordinary 3×3 Cartesian matrices; no Voigt or flattened-component ordering is implied. The operator validates the base deformation through the existing material response, so inverted, singular, non-finite, and float64 spectrally unresolved states fail closed. The direction must be a finite real 3×3 array. The result is read-only.

### Spectral Fréchet operators

For `C = V diag(lambda) V^T`, the first derivative is evaluated in the eigenbasis:

```text
(Dlog(C)[H])_ij = log[lambda_i, lambda_j] H_ij
```

The scalar first divided difference uses the confluent limit `log[x,x] = 1/x`. For close positive arguments it evaluates `log1p(r)/r` by a short series; for separated arguments it uses `log1p` directly.

The second derivative is:

```text
(D^2log(C)[H,K])_ij
  = sum_k log[lambda_i,lambda_k,lambda_j]
      (H_ik K_kj + K_ik H_kj)
```

This convention has the correct repeated-node limit `log[x,x,x] = -1/(2 x^2)`; the two ordered products provide the scalar second derivative when `H` and `K` commute. Eigenvalues are scaled by their maximum before evaluating second divided differences, then the result is rescaled by the inverse square. When the normalized three-node spread is at most 0.25, the code uses the Taylor expansion of `log(1+eta)` about the mean through degree 64, expressed with complete homogeneous polynomials. Since the largest normalized offset in this branch is at most 0.125, the omitted series tail is far below binary64 roundoff for the bounded 3×3 problem. The 0.25 value is an algorithm-selection switch, not a material or scientific acceptance threshold. Outside that cluster, the recursive symmetric divided difference has separated outer nodes; adjacent repeated nodes still use the stable first-difference limit. No near-coincident denominator is used.

The existing `ExperimentalHenckyElastic.evaluate` remains the source of the base `P`, `S`, `M_H`, and admissibility contract. The new code does not perturb or mutate an accepted state; this law has no evolving internal state.

### Symmetry and limiting checks

As a hyperelastic Hessian in `F`, the full fourth-order derivative should satisfy major symmetry under the paired work contraction:

```text
delta_F_1 : A(F)[delta_F_2] = delta_F_2 : A(F)[delta_F_1]
```

Minor symmetries are not asserted for a first-Piola derivative with respect to `F`. Frame covariance is prepared as `A(QF)[Q delta_F] = Q A(F)[delta_F]` for proper spatial rotations `Q`.

At `F=I`, `M_H=S=0`, and `Dlog(I)` is the identity on symmetric tensors. Therefore:

```text
A(I)[delta_F] = 2 mu dev(sym(delta_F)) + kappa tr(sym(delta_F)) I
```

An infinitesimal skew spin maps to zero. For an isotropic stretch `F=lambda I` and `delta_F=a I`:

```text
P = 3 kappa log(lambda)/lambda I
A(F)[a I] = 3 kappa (1-log(lambda)) a/lambda^2 I
```

These are independent closed-form references included in the prepared tests.

## Prepared test package

`tests/unit/test_wp_e01q_hencky_tangent.py` contains **13 test functions and 35 static parameter-expanded cases**. This count comes from source AST inspection and the authored `pytest.param` IDs; it is not a pytest collection result. Exact authored node identities are frozen in the adjacent execution manifest.

| Test group | Cases | Reference / purpose |
|---|---:|---|
| Identity tangent and infinitesimal rigid spin | 2 | Closed-form small-strain tangent and zero spin response |
| Isotropic volumetric tangent | 3 | Closed-form compression, identity, and extension actions |
| Diagonal action and stress | 2 | 70-digit `Decimal` closed forms from decimal-string inputs; includes a high-bulk-modulus state |
| Centered PK1 action sweep | 6 | Seven step sizes for general stretch, repeated/clustered stretch, rotated stretch, 3D shear, and near-incompressible isochoric state |
| Tangent frame covariance | 4 | `A(QF)[QD]` versus `Q A(F)[D]` |
| Major Hessian symmetry | 4 | Work-contracted symmetry for paired directions |
| Repeated spectral nodes | 3 | All equal, pair equal, and near-repeat finite actions |
| Invalid base deformation | 3 | Singular, inverted, and spectrally unresolved `F` refusal |
| Invalid direction | 3 | NaN, wrong shape, and infinity refusal |
| Explicit response limitation | 1 | Existing response continues to state `NOT_IMPLEMENTED` |
| Read-only / unchanged response | 1 | Directional diagnostic does not mutate or relabel base response |
| Energy Hessian | 3 | Centered energy second difference versus tangent quadratic form |
| **Total** | **35** | **13 test functions** |

The Decimal diagonal oracle independently differentiates the analytic scalar energy

```text
W = mu sum_i e_i^2 + (kappa/2 - mu/3) (sum_i e_i)^2,
e_i = ln(lambda_i),
```

using Decimal inputs and arithmetic, then compares the resulting diagonal `P` and `dP` to the implementation. It does not manufacture precision by converting production binary64 outputs. The general matrix cases compare the analytic action with centered differences of the same implementation's `P(F)`; those are derivative self-consistency checks, not an independent constitutive oracle. The energy second-difference tests are likewise self-consistency checks. The separate Decimal energy Hessian and closed-form identity/volumetric cases supply independent analytical checks on selected states.

Candidate test tolerances in this new module remain **PROPOSED_NOT_APPROVED**. Multi-step output records absolute error, a modulus/reference-action-normalized error, step size, analytic-action norm, and difference norm. The run should characterize truncation and roundoff rather than require every step to improve monotonically. No existing Hencky threshold or prior test was changed.

## TET4/HEX8 integration design (not implemented)

At each reference quadrature point, the displacement direction maps to a deformation-gradient direction:

```text
delta_F_q = sum_b delta_u_b tensor Grad_X(N_b)_q
delta_f_int[a,i] = sum_q w_q det(J_0)_q A(F_q)[delta_F_q]_iJ Grad_X(N_a)_q,J
```

Equivalently, a future element stiffness action uses the full derivative

```text
K[a,i,b,k] = sum_q w_q det(J_0)_q
              Grad_X(N_a)_J A_iJkL(F_q) Grad_X(N_b)_L
```

The action includes the derivative of `P(F)` and therefore the complete material-point linearization; an implementation should not add a second geometric term on top of this already complete derivative. TET4 and HEX8 would use their existing reference shape gradients and quadrature rules. Tests should compare assembled force differences with the assembled action for fixed geometry, include affine and nonuniform nodal directions, then separately verify free-DOF reduction and reactions. This campaign implements no element adapter, assembly, checkpoint, or Newton route.

## Static safety, validation, and review

The new module and test were syntax-compiled with Python 3.13's `py_compile`; this compiles source but does not import the module or execute tests. `git diff --check` passed. No pytest collection, test, numerical probe, FEM, Gmsh, public solve, worker, or subprocess was run.

Static import review found test imports limited to `decimal`, `numpy`, `pytest`, and `solveur`. The tangent module imports the isolated Hencky material and NumPy. `solveur` eagerly imports only its version and lazy API facade. Importing `solveur.materials` executes its initializer and imports Python material definitions (`beam`, `composite`, `failure`, `laminate`, `orthotropic`) using dataclasses, standard math, and NumPy; no native FEM, Gmsh, process, network, or public solver initialization was found in this reviewed closure. The Hencky TET4/HEX8 force helpers contain deferred element imports but the prepared tangent tests do not call those helpers. `tests/conftest.py` retains the existing safety classification and Gmsh capability probe is conditional on its separate optional mesh-module set; this target is not in that set.

Review limitation: no separate reviewer agent was used. A second read-only mathematical and source pass by the implementation agent confirms the index ordering and chain rule shown above, the confluent limits, and that the test oracle is independent only for the declared diagonal/closed-form cases. This is **self-review**, not independent verification. The principal remaining scientific risk is numerical accuracy of the 3×3 second divided difference and the resulting action across clustered spectra; static inspection cannot resolve it.

## Source identity and history

The P3 worktree recorded raw SHA-256 `b318dad5...b09eab2` for the unchanged Hencky kernel and `cdd2651e...dde84bfc` for its unchanged 41-pass test. In the new Q worktree, `core.autocrlf=true` checks those same Git blobs out with CRLF bytes. The Q raw file hashes are therefore different, while `git hash-object` confirms identical blob OIDs between P3 and Q for both files. No content change was made to either file. The historical 41/41 result remains attached to the exact P3 recorded source/test identity and is not inherited as tangent evidence.

Frozen source/test commit: `e3d086735b120eb3652dfb9a4f4029f9a50bce4e`.

| File | SHA-256 in Q worktree |
|---|---|
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135` |
| `tests/unit/test_wp_e01q_hencky_tangent.py` | `a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50` |
| `tests/conftest.py` | `23db87ce25e78f54bb23e382014d69e322fdf2cbe68823914930c8d6d8969305` |
| Existing `src/solveur/materials/finite_strain_hencky.py` (unchanged) | `b87706cecfb036d3a4b31461c83da1b8af0b7aeb7098037e2cf7e65cdf466f50` |
| Existing P3 test (unchanged) | `0d58ad2a499d13f84752f931c872c987577f8d3faae52cac06a8449ab2e2cec4` |
| Static next-run manifest | `22dfce5f7daac1a1c96628a6d93c82381880a934f11639927f3bf6d6f8ee1e55` |

The registry retains the existing 41-pass module binding and adds only the new Q test as `NUMERICAL_UNIT`, bound to its exact hash. The full execution proposal, static authored node inventory, source map, resource proposal, and explicit non-authorization are in `wp_e01_q_hencky_tangent_execution_manifest_2026-10-21.json`.

## Status

| Gate | Result |
|---|---|
| `HENCKY_MATERIAL_POINT_VNV` | `PREVIOUS_41_PASS_BOUNDED` |
| `HENCKY_CONSISTENT_TANGENT` | `IMPLEMENTED_BY_SOURCE / PARTIAL` |
| `HENCKY_TANGENT_VNV` | `PREPARED_NOT_RUN` |
| `HENCKY_GLOBAL_FEM` | `NOT_RUN` |
| `FINITE_STRAIN_J2` | `NOT_IMPLEMENTED` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Exact next Owner GO

Authorize one fixed-target numerical campaign for `tests/unit/test_wp_e01q_hencky_tangent.py` at the manifest's frozen source/test identity. The campaign should first prepare/review a Q-specific fixed-target supervisor (the WP-E01-O supervisor is bound to its different 41-case target), then collect only the 35 authored cases and execute the same module once only after the exact inventory, hash, process-containment, and collection gates pass. No element assembly or Newton integration should be included in that GO.
