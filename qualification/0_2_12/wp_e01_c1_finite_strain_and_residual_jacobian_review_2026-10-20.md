# WP-E01-C1 — Finite-strain elastic kernels and direct Newton/J2 Jacobian review

**Date:** 2026-10-20
**Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
**Branch/base:** `codex/qf-wp-e01-a-implementation-20261020` at `623fbd02b685071bd7d280c64e9d26603ce1cf5b`
**Disposition:** isolated material-point code plus the later exact-path Owner-authorized offline verification recorded in §9. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## 1. Scope and evidence boundary

This work advances two bounded items:

1. A direct, fixed-incoming-state finite-difference oracle for the synthetic Newton/J2 residual Jacobian used by B5. B5's prior passing result is retained as historical evidence. This direct residual check was prepared at the original review baseline and later executed under the exact-path Owner GO; bounded results are in §9.
2. Isolated material-point kernels for Total-Lagrangian StVK and the isochoric/volumetric compressible neo-Hookean law proposed in the current E01 candidate. The kernels are opt-in Python APIs and are not registered with element assembly, a nonlinear solver, the public API, or result serialization.

At the preparation baseline, no native FEM, `solve_model`, public nonlinear solve, Gmsh, backend, worker, subprocess, pytest, or newly prepared numerical calculation had been run. Historical test outcomes below are carried forward exactly and were not rerun. The later exact-path GO execution is recorded separately in §9.

## 2. Baseline and retained evidence

Read-only verification found the expected repository root, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch and clean base HEAD stated above. `qualification/0_2_12/ROADMAP.md` and the current E01 candidate were present. The roadmap continues to identify WP-E01 as `OPEN / EXPERIMENTAL_TARGET`; WP08–WP10 are bounded closures, not general nonlinear qualification.

The following are **historical records**, not reruns in this campaign:

| Evidence carried forward | Historical result / limitation |
|---|---|
| E01-A integrated tests | 39 PASS |
| E01-A policy and safety tests | 25 PASS |
| E01-B material-point constitutive oracles | 28 PASS |
| B4 extended J2 tangent | 11 PASS; 24 bounded branch-preserving sweeps met its then-proposed `tau_T=1e-8`, `C_ref=max(3K,2mu)` gate and two-decade plateau rule |
| B5 Newton/J2 traces | 3 PASS; perfect-plastic and hardening synthetic equilibria reached their target in two corrections each |
| B5 transaction/checkpoint | Synthetic rollback and accepted-state WP10 v2 round-trip passed |

B5 explicitly did **not** finite-difference the assembled force residual/Jacobian. Its one-direction stress-tangent comparison was diagnostic, at one step size, and did not make a route-level Armijo certificate. B4/B5 do not demonstrate native FEM, production material/contact retry, checkpoint crash durability, or global qualification.

## 3. Source and contract audit

### 3.1 Existing source facts

| Area | Source evidence | Interpretation for C1 |
|---|---|---|
| Small-strain isotropic J2 | `src/solveur/materials/solid.py::VonMisesElastoplasticMaterial.stress_tangent_state` (from line 143), `_algorithmic_tangent` (from line 276), `_plastic_strain_tensor` (from line 344) | Engineering-strain Voigt `[xx, yy, zz, gamma_xy, gamma_yz, gamma_xz]`; tensorial stress Voigt `[xx, yy, zz, tau_xy, tau_yz, tau_xz]`. The radial return is small-strain J2; its tangent is not promoted by this review. |
| Existing TL StVK TET4 | `src/solveur/elements/solid/tet4_total_lagrangian.py::TotalLagrangianTet4Kernel` (lines 12–100) | Computes `F`, `E`, StVK `S`, `P=F S`, reference-volume internal force, and material plus geometric stiffness. It rejects `det(F) <= 1e-10`; this is an implementation guard, not an approved physical or universal `J_min`. |
| Existing TL StVK HEX8 | `src/solveur/elements/solid/hex8_total_lagrangian_batch.py::TotalLagrangianHex8Assembly` (lines 12–216) | Uses 2x2x2 integration, StVK stress and reference-configuration assembly. It also rejects `det(F) <= 1e-10`. Existing route behavior is not changed. |
| TL J2-labelled path | `src/solveur/elements/solid/total_lagrangian_j2.py::TotalLagrangianJ2Element` (line 54 onward) | A Green–Lagrange strain fed to the existing small-strain J2 return map is not multiplicative finite-strain plasticity `F=F_eF_p`; it is excluded as a C1 constitutive claim. |
| Neo-Hookean | Search of the inspected `src/solveur` sources before this change found no Neo-Hookean law. | The new C1 module introduces only an isochoric/volumetric material-point kernel. There is still no Neo-Hookean element route, assembly, state/result schema, or V&V evidence. |
| Public route and material API | `src/solveur/__init__.py` lazily resolves public APIs; `src/solveur/materials/__init__.py` exports existing material families | The new kernel is not added to the package exports or any material factory, element, solver, or public API. Existing defaults remain unchanged. |

The current WP-E01 candidate §5.3 proposed the isochoric/volumetric Neo-Hookean energy `mu/2 (J^(-2/3) tr(C)-3) + K/2 (ln J)^2`. That was a proposal, not an Owner-frozen formulation. The new material-point kernel follows this candidate. A distinct Lamé-log-J form, `mu/2 (I1-3-2 ln J) + lambda/2 (ln J)^2`, is a common alternative with the same infinitesimal moduli under consistent parameterization but different finite response; it is not implemented here. Owner approval is still required before C1 is frozen or the law is used in element assembly.

### 3.2 P0/P1/P2 findings

- **P0:** none identified in the inspected source or the isolated material-point implementation.
- **P1:** no direct finite-difference assertion of the assembled synthetic Newton/J2 residual Jacobian existed in B5. The B6 module now supplies a bounded synthetic check, passed under the exact-path Owner GO, but is not an independent external review or FEM result. The existing J2 tangent/Armijo production certificate remains blocked.
- **P1:** the log-J Lamé and isochoric/volumetric compressible Neo-Hookean energies are non-equivalent at finite strain. The kernel follows the existing E01 proposal, but Owner approval is still needed before it is frozen or integrated.
- **P2:** the existing TET4/HEX8 determinant cutoff is a code threshold, not an Owner-approved domain. No case-specific lower `J` bound, allowed StVK strain range, follower-load tangent, or finite-strain result-schema has been frozen here.

## 4. A — Independent Newton/J2 residual-Jacobian oracle

### 4.1 Synthetic residual and units

The prepared test models a six-mode affine material-point spring, not a finite element. Let `q` [m] be a generalized displacement vector and `L` [m] a declared reference length. Map it to engineering strain in the existing J2 order:

\[
\varepsilon_v(q)=q/L,
\qquad
\varepsilon_{tensor}=\begin{bmatrix}
\varepsilon_{xx}&\gamma_{xy}/2&\gamma_{xz}/2\\
\gamma_{xy}/2&\varepsilon_{yy}&\gamma_{yz}/2\\
\gamma_{xz}/2&\gamma_{yz}/2&\varepsilon_{zz}
\end{bmatrix}.
\]

For reference volume `V` [m³], the work-conjugate generalized internal force is `f_int=(V/L) sigma_v` [N]. At load parameter `lambda`,

\[
R(q,z_n,\lambda)=\lambda f_{ext}-(V/L)\sigma_v(q/L,z_n),\qquad
J_R=\frac{\partial R}{\partial q}=-\frac{V}{L^2}C_{alg}.
\]

Thus the residual is in N and its Jacobian in N/m. `f_ext` is fixed during perturbation. The trial constitutive response is recomputed from an immutable copy of the same accepted state `z_n` for every `q+h` and `q-h`; a perturbed trial state is never used as the next perturbation's input. The sign test is explicit: the residual derivative has the negative internal-stiffness sign.

### 4.2 Independent reference

`tests/unit/test_wp_e01b_b6_residual_jacobian.py` contains an independent tensor-form J2 reference. It derives Lamé constants from `(E, nu)`, forms the elastic trial tensor, computes `q=sqrt(3/2 s:s)`, and solves the scalar consistency equation by a bounded bisection. It does not call the production radial return or tangent. The flow direction, accumulated equivalent plastic strain, and corrected stress are reconstructed tensorially. Both production residual and reference residual use the same declared generalized force mapping; only the stress calculation differs.

The matrix reference is formed columnwise by central differences of the independent residual:

\[
J^{FD}_{:,j}(h)=\frac{R_{ref}(q+h e_j,z_n,\lambda)-R_{ref}(q-h e_j,z_n,\lambda)}{2h}.
\]

The prepared suite covers virgin elastic and smooth-plastic response, plus elastic unloading and smooth reloading from an independently constructed nonzero accepted history, for `H=0` and `H=1.5 GPa`. Each six-column Jacobian is probed in positive and negative directions using strain steps `10^-3,10^-4,...,10^-10`. Every pair must remain on the same branch. Separate yield-switch checks use one-sided left/elastic and right/plastic differences; no centered derivative crosses the switch.

### 4.3 Candidate acceptance record (not frozen)

The new test records per-step absolute tangent error [N/m], normalized error, production-residual finite-difference error, and adjacent-step plateau changes. It also records one-sided switch slopes and signed branch behavior. Candidate criteria carry forward B4's proposed normalization rather than introducing a looser threshold:

\[
C_{ref}=\max(3K,2\mu)\quad[\mathrm{Pa}],\qquad
J_{ref}=(V/L^2)C_{ref}\quad[\mathrm{N/m}],
\]

\[
e_{abs}=\max_j\|J_{candidate,:,j}-J_{FD,:,j}\|_2\quad[\mathrm{N/m}],\qquad
e_{rel}=e_{abs}/J_{ref}.
\]

Candidate tangent gate: `e_rel <= 1e-8` on a branch-preserving window, with three adjacent step sizes spanning two consecutive decades whose adjacent finite-difference changes are also at most `1e-8` after the same normalization. Candidate one-sided switch slopes use the same `C_ref` normalization. These values and window rules are **PROPOSED, not frozen**. The prior `tau_T=2e-5` proposal remains unapproved; the more specific B4 `1e-8` proposal is retained for Owner comparison because bounded B4 sweeps already used it. Neither historical B4 results nor these prepared B6 assertions verify the direct residual Jacobian.

The distinct claims remain separate:

1. constitutive stress accuracy against the independent radial-return oracle;
2. algorithmic tangent consistency against a fixed-state derivative;
3. synthetic assembled residual/Jacobian consistency;
4. Newton equilibrium convergence;
5. production Armijo route certification; and
6. FEM scientific qualification.

Evidence for one does not imply another. `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; the production Armijo certificate registry remains unchanged and no J2 route is registered.

## 5. C — Finite-strain elastic formulation

### 5.1 Kinematics, measures, and virtual work

For reference coordinates `X` and displacement `u(X)`:

\[
F=I+\nabla_Xu,\quad C=F^TF,\quad E=\tfrac12(C-I),\quad J=\det F.
\]

`E` is Green–Lagrange strain, not infinitesimal strain `eps=sym(grad_X u)`. The kernel's indices are explicit: `F_iJ` maps reference direction `J` to current direction `i`; `E_IJ` and PK2 `S_IJ` are reference-frame tensors; PK1 `P_iJ` is a full, generally nonsymmetric current/reference two-point tensor; Cauchy `sigma_ij` is symmetric in the current frame. No six-component PK1 representation is used.

For energy per reference volume `W(F)`, `P=partial W/partial F=F S`, and

\[
\delta W_{int}=\int_{\Omega_0}P:\nabla_X\delta u\,dV_0
=\int_{\Omega_0}S:\delta E\,dV_0.
\]

The element linearization contains both the material term and the initial-stress/geometric term. For StVK,

\[
C_{IJKL}=\lambda\delta_{IJ}\delta_{KL}+\mu(\delta_{IK}\delta_{JL}+\delta_{IL}\delta_{JK}),
\]

\[
A_{iJkL}=\frac{\partial P_{iJ}}{\partial F_{kL}}
=F_{iA}C_{AJBL}F_{kB}+\delta_{ik}S_{LJ}.
\]

The new API returns both full `dS/dE` and full `dP/dF` tensors. Boundary virtual work and follower-load tangents are not implemented; only a dead/external load vector that is independent of `F` is in the synthetic residual design.

### 5.2 StVK

The isolated StVK law is

\[
W(E)=\tfrac12\lambda(\mathrm{tr}E)^2+\mu E:E,\quad
S=\lambda\mathrm{tr}(E)I+2\mu E,\quad P=FS,
\]

with `mu>0` and `K=lambda+2mu/3>0`. It is stress-free at `F=I`, objective under proper superposed rotation, and shares its law with the existing bounded TL StVK source. Its quadratic strain-energy choice can be physically unsuitable at large distortions even though `J>0`; a validated strain/material domain is still required. No arbitrary large-strain claim follows from the kernel.

### 5.3 Selected isochoric/volumetric compressible Neo-Hookean kernel

The isolated implementation follows the existing E01 candidate form:

\[
W(F)=\frac{\mu}{2}(J^{-2/3}I_1-3)+\frac{K}{2}(\ln J)^2,
\quad I_1=\mathrm{tr}(C),\quad K=\lambda+\frac23\mu.
\]

Writing `B=C^-1` and `a=J^-2/3`, the stresses are

\[
S=\mu a\left(I-\frac{I_1}{3}B\right)+K\ln J\,B,\quad P=FS,
\]

\[
\sigma=J^{-1}FSF^T
=J^{-1}\left[\mu a\left(FF^T-\frac{I_1}{3}I\right)+K\ln J\,I\right].
\]

The material tangent is

\[
\mathbb C_{IJKL}=2\mu a\left[-\frac13B_{KL}\delta_{IJ}
+\frac{I_1}{9}B_{KL}B_{IJ}-\frac13\delta_{KL}B_{IJ}
+\frac{I_1}{6}(B_{IK}B_{LJ}+B_{IL}B_{KJ})\right]
+KB_{IJ}B_{KL}-K\ln J(B_{IK}B_{JL}+B_{IL}B_{JK}).
\]

The consistent first-Piola tangent follows from the material tangent and the geometric term:

\[
A_{iJkL}=F_{iA}\mathbb C_{AJBL}F_{kB}+\delta_{ik}S_{LJ}.
\]

This form has `W(I)=0`, zero stress at `F=I`, objectivity, and infinitesimal stress `lambda tr(eps) I + 2 mu eps`, where `lambda=K-2mu/3`. The distinct Lamé-log-J alternative is not implemented. Owner approval remains necessary before the candidate is frozen or integrated; this kernel is material-point only.

The choice of independent positive `K` and `mu` also avoids using a negative first Lamé parameter as the coefficient of `(ln J)^2`: negative `lambda` is compatible with a positive-definite infinitesimal isotropic tensor for some auxetic materials, but would make that alternative's volumetric energy unbounded below along sufficiently large logarithmic volume change. This is formulation-specific; it does not establish a universal material calibration or admissible strain range.

### 5.4 Admissibility and bounded first use

The material-point kernel fails closed unless `F` is finite, `J` is positive and representable, inverse operations succeed, and all returned fields are finite. It does not invent a universal `J_min`; representability and finite results are software checks, not a physical deformation-domain bound. Existing TET4/HEX8 assembly retains its `J<=1e-10` refusal unchanged. A future integrated route must declare a case/material admissible lower `J` bound before execution and must refuse inverted/degenerate configurations.

Recommended first use is element-independent material-point experiments only: verify undeformed zero response, analytical uniaxial and shear references, proper rotation/rotation-plus-stretch objectivity, energy gradient, `dP/dF`, `dS/dE`, symmetry, small-strain Neo-Hookean limit, and inverted/singular refusal. For later element work, use StVK only over an Owner-declared bounded deformation range and keep the isochoric/volumetric Neo-Hookean law separately identified. No TET4/HEX8 assembly change is included here.

The four behavior classes remain distinct:

1. small-strain J2 plasticity (`VonMisesElastoplasticMaterial`);
2. corotational small-strain constitutive updates (`corotational_j2.py`);
3. Total-Lagrangian finite-strain **elasticity** (StVK and the new material-point isochoric/volumetric law); and
4. finite-strain plasticity `F=F_eF_p` (not implemented and out of scope).

## 6. Implementation, test preparation, and safety

### 6.1 Files changed

- `src/solveur/materials/finite_strain_elastic.py`: isolated StVK and isochoric/volumetric compressible Neo-Hookean material-point response/tangent kernels. It is not exported through `solveur.materials`, `MaterialFactory`, element assembly, a solver route, or result serialization.
- `tests/unit/test_wp_e01b_b6_residual_jacobian.py`: direct synthetic residual/Jacobian oracle and branch-aware J2 checks, prepared only.
- `tests/unit/test_wp_e01c_finite_strain_material.py`: analytical, objectivity, energy/tangent, symmetry, small-strain and invalid-F checks, prepared only.
- `tests/conftest.py`: exact SHA-bound `NUMERICAL_UNIT` entries for the two modules; no tier or guard was weakened.
- `qualification/0_2_12/wp_e01_nonlinear_foundations_candidate.md`: dated status overlay that records the new implementation boundary and open C1 formulation choice.

### 6.2 Prepared test inventory

| Exact module | Prepared items | Main references |
|---|---:|---|
| `tests/unit/test_wp_e01b_b6_residual_jacobian.py` | 10 parameter-expanded cases | Independent tensor radial-return/bisection oracle; six-mode affine residual; fixed accepted state; `H=0` and `H=1.5 GPa`; virgin and nonzero-history unloading/reloading; branch-preserving central differences; one-sided yield-switch references. |
| `tests/unit/test_wp_e01c_finite_strain_material.py` | 17 parameter-expanded cases | Direct closed-form StVK and isochoric/volumetric Neo-Hookean response; identity; uniaxial stretch; simple shear; proper rotation and rotation plus stretch; centered energy/P and P/F finite differences; material `dS/dE`; symmetry; Neo-Hookean infinitesimal limit; invalid/inverted/singular F. |

Acceptance assertions in these modules are candidates, not a scientific freeze. In particular, the proposed J2 `1e-8` tangent/plateau gate and finite-strain material-point finite-difference tolerance `2e-6` have not been approved for qualification. Bounded observed results are reported in §9.

The finite-strain test's proposed reference scale is `M_ref=max(|lambda|+2mu, 1 Pa)`. It uses dimensionless `F` perturbation `h=1e-6`; energy-gradient and material-tangent errors are Frobenius-normalized by `M_ref`, while the nine-by-nine `dP/dF` error is RMS-normalized by `M_ref`. Its candidate acceptance is `2e-6` for those derivative checks. Direct uniaxial/shear comparisons use `rtol=1e-14`, `atol=1e-5 Pa` for stresses and the same relative/absolute values for energy density. Objectivity comparisons use `rtol=2e-13` and `atol=2e-5 Pa`; the stress-free rotation allowance is `1e-14 M_ref`. All these are test-preparation thresholds only and require Owner approval before they are treated as acceptance gates.

### 6.3 Import and execution boundary review

Both new modules are explicitly hash-bound as `NUMERICAL_UNIT`. The E01-C test imports only NumPy, pytest and the isolated material module; the J2 test imports NumPy, pytest and the small-strain J2 material API. Static import review includes `solveur.materials.__init__` eager imports (beam/composite/failure/laminate/orthotropic, NumPy-only), `solveur.core.nonlinear.contracts`, and the lazy `solveur` facade. The inspected selected paths do not import Gmsh or `ctypes`, do not reach a native solver, element assembly, public API solve, worker, or process launcher. The collection hook probes Gmsh only for two unrelated optional mesh modules; neither new module is in that set. The tests use no file writes and no subprocess calls.

The registry digest pins the exact source. If either test module changes, its reviewed digest must be refreshed by source review; do not run an unknown or hash-mismatched module. At preparation time, the proposed bounded authorization was exactly:

```text
python -m pytest -q -s tests/unit/test_wp_e01b_b6_residual_jacobian.py
python -m pytest -q -s tests/unit/test_wp_e01c_finite_strain_material.py
```

These are two sequential commands, with a stop-and-report after any first-module failure. They cover material-point/synthetic algebra only. They do not invoke FEM, `solve_model`, a production Newton route, Gmsh, a backend, a worker, or a child process. The second command need not be authorized if the first fails.

Static checks completed: AST parsing succeeded for the new kernel, both test modules, and `tests/conftest.py`; staged whitespace checks succeeded. Ruff was unavailable. No pytest command or numerical assertion had been executed at the preparation snapshot; later exact-path results are in §9.

## 7. Review disposition and remaining Owner decisions

- **P0:** none identified by source review.
- **P1:** the direct residual/Jacobian oracle passed on its bounded synthetic branches, but it is not an independent external review or full FEM result. The J2 production tangent remains blocked pending the separate Owner scientific gate, and no Armijo certificate is available.
- **P1:** the isochoric/volumetric model is still only a candidate. Owner approval of the exact E01-C energy, admissible deformation domain, and case-declared `J_min` policy is required before scientific freeze or element integration; the distinct Lamé-log-J alternative is documented but not implemented.
- **P2:** define allowed StVK deformation/material range; specify the case-declared `J_min` policy for any integrated route; approve candidate test tolerances; approve result frame/location/units and any public API integration; separately authorize tests and later any FEM work.

The `2e-6` finite-strain material-point derivative tolerance is merely a deterministic test-preparation threshold. The `1e-8` J2 candidate remains proposed per B4. Neither is a qualification gate without explicit Owner approval and separate execution.

## 8. Final statuses

```text
RESIDUAL_JACOBIAN_ORACLE: VERIFIED_BOUNDED
NEWTON_J2_SYNTHETIC: VERIFIED_BOUNDED_PREVIOUS_EVIDENCE (historical only; not rerun)
J2_TANGENT_GATE: READY_FOR_OWNER_FREEZE (candidate 1e-8 gate met on bounded synthetic plateau; not Owner-frozen)
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
FINITE_STRAIN_ELASTIC_FORMULATION: PROPOSED / INCOMPLETE
FINITE_STRAIN_CONSTITUTIVE_IMPLEMENTATION: IMPLEMENTED_BY_SOURCE (isolated material points only)
FINITE_STRAIN_MATERIAL_POINT_VNV: VERIFIED_BOUNDED
FINITE_STRAIN_FEM_VNV: NOT_RUN
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

The update does not change the canonical roadmap, approved WP-E01-A controls, E01-B principles, production Armijo registry, existing StVK assembly routes, WP10 v2 checkpoint semantics, or qualification statuses.

The required final read-only review was performed as a separate pass by the same primary agent. No independent second reviewer was available in this turn; this is not represented as an independent review.

## 9. Owner GO exact-path execution addendum — 2026-10-20

### 9.1 Preflight and execution boundary

The preflight verified origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch `codex/qf-wp-e01-a-implementation-20261020`, clean HEAD `c994d074701557692f533f6c14b692d9c2c9bfc7`, and the four Owner-specified baseline digests. Both modules were hash-bound as `NUMERICAL_UNIT`; their parameter expansion was 10 B6 cases and 17 C1 cases. Static import/call-path review found NumPy, pytest and the reviewed material package imports only. The selected paths do not match the Gmsh collection-probe module set, and contain no reachable native backend, Gmsh initialization, FEM assembly, public solve, `solve_model`, worker, or child-process call. Numerical shapes are bounded to 6-by-6 and 3-by-3/9-by-9 tensors.

No safety classification was changed. After the test-only corrections below, both exact test hashes were refreshed in `tests/conftest.py` and rechecked before the affected module was rerun.

### 9.2 Executions and preserved failures

Every invocation used the exact authorized module path and no other test modules:

| Module / attempt | Result | Pytest duration | Disposition |
|---|---:|---:|---|
| B6, initial | 5 passed, 5 failed | 1.02 s | Four plastic cases applied the local-derivative tolerance to coarse `h=1e-3`; one preloaded perfect-plastic unloading perturbation crossed the yield switch. |
| B6, after plateau-gate correction | 9 passed, 1 failed | 1.17 s | The `h=1e-3` `+xx` perturbation in preloaded perfect-plastic unloading was elastic at the center and plastic at the perturbed point. |
| B6, after branch-crossing correction | 10 passed | 0.93 s | All prescribed synthetic smooth-branch and one-sided cases passed the proposed plateau gate. |
| C1, initial | 15 passed, 2 failed | 0.89 s | StVK simple-shear closed-form oracle used `mu*gamma` in `S_yy` instead of `mu*gamma**2`; the Neo-Hookean rigid-rotation energy check demanded `1e-11 J/m^3`, below modulus-scaled roundoff. |
| C1, after reference/tolerance correction | 17 passed | 0.81 s | Both material-point laws passed the bounded checks. |

The initial B6 tool response was truncated by the execution-output cap and was not saved as a standalone log. Its reported failures were `virgin-plastic` for `H=0` and `H=1.5 GPa`, `history-unloading-perfect-plastic`, and `history-reloading` for `H=0` and `H=1.5 GPa`. Representative coarse-step normalized errors were `3.290547776449592e-3` and `3.2613182628062577e-3` at strain step `1e-3`; these are finite-step truncation errors, not plateau errors. The second and final B6 outputs were saved outside the repository:

| Log | SHA-256 |
|---|---|
| `%TEMP%/qf_wp_e01_b6_cycle2.log` | `83DFB131C5CD0D82EBAC11AE48F11DA8EC4CDACFAEAC2CC0B331F8D880FFD01A` |
| `%TEMP%/qf_wp_e01_b6_cycle3.log` | `F870A260DACE1AA45B0BD913D2615B2FDE0D72F56ED668670BA56E89F2B03CFE` |

The first C1 failure output is retained in the task execution record; the final C1 run printed the following exact diagnostics directly to the execution record. No test output was altered to remove a failure.

### 9.3 B6 bounded Jacobian results

The B6 correction does not change the `1e-8` candidate tolerance. It records all finite-difference errors, applies the candidate gate only to a branch-preserving three-step window spanning two decades, and records/omits any centered difference whose perturbations cross the yield switch. Direction-local normalization uses each FD Jacobian column norm with a floor of `sqrt(machine_epsilon)*J_ref`. Coarse-step errors remain visible in the saved diagnostics.

| Case (`H`, center, history, branch) | Accepted `h` window | Max tangent absolute error [N/m] | Max tangent global / direction-local relative error | Max production-residual FD error [N/m]; global / local relative error | Plateau global / local change |
|---|---:|---:|---:|---:|---:|
| `0`, `0.0002`, virgin, elastic | `1e-3..1e-5` | `8.68838651575e-6` | `8.27465382453e-16 / 1.31418281798e-15` | `8.58306884766e-6`; `8.17435128348e-16 / 1.29825274056e-15` | `8.27465382453e-16 / 1.31418281798e-15` |
| `1.5 GPa`, `0.0002`, virgin, elastic | `1e-3..1e-5` | `8.68838651575e-6` | `8.27465382453e-16 / 1.31418281798e-15` | `8.58306884766e-6`; `8.17435128348e-16 / 1.29825274056e-15` | `8.27465382453e-16 / 1.31418281798e-15` |
| `0`, `0.006`, virgin, plastic | `1e-7..1e-9` | `3.70670167155` | `3.53019206814e-10 / 6.08578965821e-10` | `3.56447673331`; `3.39473974601e-10 / 5.85227988726e-10` | `3.49784492706e-10 / 6.03002558280e-10` |
| `1.5 GPa`, `0.006`, virgin, plastic | `1e-7..1e-9` | `3.29231712119` | `3.13554011542e-10 / 5.40453092150e-10` | `2.05795171389`; `1.95995401323e-10 / 3.37824798258e-10` | `3.06781287413e-10 / 5.28779378650e-10` |
| `0`, `0.003`, preloaded, elastic unloading | `1e-4..1e-6` | `8.72547115978e-4` | `8.30997253312e-14 / 1.31979214508e-13` | `7.27653503418e-4`; `6.93003336589e-14 / 1.10062982339e-13` | `8.08734609596e-14 / 1.28443455252e-13` |
| `1.5 GPa`, `0.003`, preloaded, elastic unloading | `1e-3..1e-5` | `1.18731494884e-4` | `1.13077614176e-14 / 1.79590180809e-14` | `1.62495161637e-4`; `1.54757296797e-14 / 2.45785968478e-14` | `1.21150782564e-14 / 1.92412009259e-14` |
| `0`, `0.006`, preloaded, plastic reloading | `1e-7..1e-9` | `3.00307816448` | `2.86007444236e-10 / 4.88818108090e-10` | `2.05795171389`; `1.95995401323e-10 / 3.39473993060e-10` | `2.83008110533e-10 / 4.83691917652e-10` |
| `1.5 GPa`, `0.006`, preloaded, plastic reloading | `1e-7..1e-9` | `1.83338720438` | `1.74608305179e-10 / 3.02429372176e-10` | `1.45519161224`; `1.38589677357e-10 / 2.36780786423e-10` | `1.76395848346e-10 / 3.05525476665e-10` |

All eight smooth cases found a three-step plateau below the proposed `1e-8` relative gate. At yield, the one-sided residual Jacobians were `-5.653846153846152e9 N/m` on the elastic side and `-3.500000000000000e9 N/m` on the plastic side for `H=0`; for `H=1.5 GPa`, the plastic-side value was `-3.513251301467108e9 N/m`. Maximum one-sided normalized errors were respectively `3.30056508382e-10` left / `5.87620235625e-10` right (`H=0`) and `3.30056508382e-10` / `1.67845044817e-10` (`H=1.5 GPa`). The test used no centered difference across the yield switch. These are synthetic material-point results; they do not validate Newton integration, production Armijo certification, or FEM.

### 9.4 C1 bounded material-point results

Both laws passed 17/17 parameter-expanded checks. Test `F` perturbation was `1e-6`; symmetric `C` perturbation was `1e-6`. The proposed finite-difference relative limit remained `2e-6`.

| Check | StVK observed error | Isochoric/volumetric Neo-Hookean observed error |
|---|---:|---:|
| Uniaxial closed form, `lambda=1.12`, `J=1.12` | PK2 `0 Pa`, PK1 `0 Pa`, energy `0 J/m^3` | PK2 `0 Pa`, PK1 `0 Pa`, energy `0 J/m^3` |
| Simple shear, `gamma=0.18`, `J=1` | PK2 `3.16297987972e-6 Pa`, PK1 `3.69356474515e-6 Pa`, energy `0 J/m^3` | PK2 `0 Pa`, PK1 `0 Pa`, energy `7.15255737305e-7 J/m^3` |
| Energy gradient / `dP/dF`, centered `F` step `1e-6`, base `J=1.077266` | normalized `1.20433734188e-11` / `1.91176199157e-11` | normalized `7.58545144459e-11` / `2.56057745088e-11` |
| `dS/dE`, symmetric `C` step `1e-6` | max absolute `44.5595500048 Pa`, normalized `1.57625619064e-10` | max absolute `24.9730412562 Pa`, normalized `8.83400098860e-11` |
| Rigid rotation energy | `1.74620647561e-21 J/m^3` | `1.79343719363e-5 J/m^3`; scale-based roundoff allowance `5.02162414215e-4 J/m^3` |
| Rotation plus stretch objectivity (`J=1.15667`) | PK2 covariance `1.08064100170e-4 Pa`; PK1 covariance `1.17034141210e-4 Pa`; Cauchy covariance `9.40614929652e-5 Pa` | PK2 covariance `1.17074007641e-4 Pa`; PK1 covariance `1.19555923036e-4 Pa`; Cauchy covariance `9.26194041609e-5 Pa` |
| Neo-Hookean infinitesimal limit | — | normalized stress error `7.26881491782e-14`, absolute `0.0205483806331 Pa`, `J=1.000000149999978` |

Across valid material-point fixtures, observed `J` ranged from `1.0` to `1.15667`; no universal `J_min` was introduced. Both laws refused `det(F)=-1`, `det(F)=0`, and nonfinite `F`. The rotation checks compared reference tensors appropriately: `E` and PK2 remain unchanged under a superposed left rotation, PK1 transforms as `R P`, and Cauchy stress transforms as `R sigma R^T`; componentwise invariance of spatial/two-point tensors was not assumed.

### 9.5 Corrections, review, and final disposition

Only the two prepared test modules and their exact digest entries in `tests/conftest.py` changed during the GO campaign; `finite_strain_elastic.py`, solver routes, material registration, and scientific contracts did not change. The B6 correction moved the candidate threshold to a three-step branch-preserving plateau and made branch-crossing steps diagnostic; the `1e-8` value was not changed. The C1 corrections fixed a test-only StVK closed-form term and used a modulus-scaled floating-point allowance for rigid-rotation energy; the `2e-6` derivative limit was not changed. Numerical results are evidence for these bounded tests, not approved qualification thresholds.

**Read-only scientific review:** no P0 finding. P1: the B6 tangent result is bounded to the independent synthetic oracle; the J2 tangent remains blocked pending the Owner-approved scientific gate and broader independent evidence. P1: the Neo-Hookean equation is still a proposed candidate law and has no element route or approved `J_min`. P2: StVK was checked only over the listed moderate deformation fixtures; no large-distortion suitability or FEM claim follows. The same primary agent performed this review; it is not an independent reviewer.

Final disposition: `RESIDUAL_JACOBIAN_ORACLE: VERIFIED_BOUNDED`; `J2_TANGENT_GATE: READY_FOR_OWNER_FREEZE`; `J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; `FINITE_STRAIN_MATERIAL_POINT_VNV: VERIFIED_BOUNDED`; `FINITE_STRAIN_FEM_VNV: NOT_RUN`; `ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED`; `SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED`; `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`.
