# WP-E01-D/E — Bounded TET4/HEX8 Integration and V&V Preparation

**Date:** 2026-10-20<br>
**Repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`<br>
**Branch/base:** `codex/qf-wp-e01-a-implementation-20261020` at `151c94538abfcfd7817fb40ef0569175c39e95ec`<br>
**Origin:** `https://github.com/emptiesvoid-cloud/QF_solver.git`<br>
**Disposition:** source audit and documentation/test preparation only. No production source, test module, or solver route was changed; no test or FEM execution occurred in this campaign.

## 1. Executive disposition

The verified baseline is the Owner-designated v0.2.12 repository. The canonical roadmap attachment hash matches its entry-point record. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`; WP08–WP10 remain bounded closures.

The existing source already contains:

* Small-strain J2 updates through the existing constitutive contract and standard TET4/HEX8 element paths, with per-integration-point material state.
* A separate corrected corotational J2 route for bounded local small strains.
* Total-Lagrangian StVK TET4 and HEX8 assembly through `geometric_nonlinear_static`.
* Isolated StVK and isochoric/volumetric Neo-Hookean **material-point** kernels; the latter is not connected to an element, material factory, or public solver route.

The B6 and C1 reports provide bounded synthetic/material-point evidence. They do not establish an element-level J2 tangent, a Neo-Hookean FEM route, native FEM evidence, or scientific qualification. I did not rerun those modules or any other test here.

No production implementation was justified in this turn. StVK and small-strain J2 element assemblies already exist; adding another implementation would duplicate them. Neo-Hookean integration needs an Owner-selected material formulation/domain and changes to the protected geometric material/assembly dispatch. The integration seam and changes requiring Owner review are specified below.

## 2. Independent scientific review of B6 and C1 evidence

This is a read-only scientific self-review by the primary agent, not an independent second review.

### B6 synthetic residual/Jacobian

The reported oracle evaluates

\[
R(q,z_n,\lambda)=\lambda f_{ext}-\frac{V}{L}\sigma(q/L,z_n),\qquad
J_R=-\frac{V}{L^2}C_{alg},
\]

with force in N, generalized displacement in m, and residual derivative in N/m. Its independent tensor radial return uses a scalar bisection consistency solve rather than the production return map. Each positive/negative perturbation is recomputed from the same accepted incoming state. The `H=0` and `H=1.5 GPa` cases include virgin elastic/plastic response and preloaded unloading/reloading; the yield switch uses one-sided slopes. The final reported run passed 10/10, with a branch-preserving candidate plateau below `1e-8`.

Limits on that claim:

* This is a six-mode affine material-point spring, not element assembly. Its six columns are Voigt coordinate directions; it does not include a prescribed set of rotated/mixed directions or a global assembled TET4/HEX8 stiffness action.
* The local column scale uses `max(||J_FD[:,j]||, sqrt(eps) J_ref)`. This is a useful guard for weak columns, but a floor can conceal a very weak constitutive response if its size is below the floor. The V&V contract should report both absolute error and response/floor values, and add explicit mixed/weak directions.
* The `1e-8` tangent/plateau threshold remains a candidate, not Owner-frozen. B6 does not un-block `J2_TANGENT_CONSISTENCY` and does not validate a production Armijo certificate.
* Compare the raw element tangent before symmetrization. Existing `Tet4Element`, `Hex8Element`, and `TotalLagrangianJ2Element` return symmetrized tangents; comparing only those outputs cannot reveal skew error hidden by symmetrization.

### C1 finite-strain material points

C1 has direct uniaxial/shear formulas, an energy-gradient finite difference, `dP/dF` finite differences, symmetric `dS/dE` perturbations, objectivity checks, an infinitesimal Neo-Hookean limit, and invalid-`F` refusals. The reported 17/17 result is bounded to the two material-point laws and stated test states. Its derivative checks use one principal deformation state and one perturbation size (`1e-6`); they do not yet establish a step-size plateau, element quadrature, assembled residual/tangent, or load-path solver behavior.

Objectivity is assessed with the correct tensor transformations: under a superposed proper rotation, `E` and `S` are invariant, `P` transforms as `Q P`, and Cauchy stress as `Q sigma Q^T`. Componentwise invariance of `P` or Cauchy stress is not required. The C1 kernel accepts finite orientation-preserving, representable `F` but has no application-specific positive lower bound for `J`; an element route must declare and justify its admissible domain. No universal `J_min` is inferred from C1.

The selected Neo-Hookean candidate is

\[
W=\frac{\mu}{2}(J^{-2/3}\operatorname{tr}C-3)+\frac{K}{2}(\ln J)^2,
\quad S=2\frac{\partial W}{\partial C},\quad P=FS,
\quad \sigma=J^{-1}P F^T.
\]

It is not the alternative Lamé-log-J energy. The C1 kernel’s finite-strain response is not the existing small-strain `ConstitutiveModel.evaluate(strain, accepted_state)` contract and must remain a distinct interface. Owner approval is still needed to freeze this energy and the admissible `F/J` domain for element integration.

## 3. Existing route and compatibility matrix

| Formulation | TET4 source path | HEX8 source path | State / tangent / present boundary |
|---|---|---|---|
| Small-strain isotropic J2 | `Tet4Element`, one constant-strain point | `Hex8Element`, eight 2x2x2 Gauss points | `evaluate_constitutive` calls the J2 return map at each point. Strain Voigt is `[xx,yy,zz,gamma_xy,gamma_yz,gamma_xz]`; stress shear entries are tensorial. Trial states are returned separately. These are small-strain elements; B6 validates only its affine material-point mapping, not these assembled element tangents. |
| Corrected corotational small-strain J2 | `CorotationalJ2Tet4Element` | `CorotationalJ2Hex8Element` | Explicit `kinematics='corotational_j2'` and corrected formulation ID; bounded local-strain cap is at most 0.05. State is transported between local frames. Its finite-difference tangent and WP09 scope remain separate from TL elasticity. Corrected route rejects contact in the current model validation. |
| Green–Lagrange/J2 research route | `TotalLagrangianJ2Tet4Element`, one point | `TotalLagrangianJ2Hex8Element`, eight points | Feeds Green–Lagrange strain to the small-strain J2 return map and interprets output as PK2. This is not multiplicative `F=Fe Fp` plasticity; exclude it from an E01-C finite-strain plasticity claim. Tangent output is symmetrized. |
| TL StVK elasticity | `TotalLagrangianTet4Assembly`, one point | `TotalLagrangianHex8Assembly`, eight 2x2x2 points | Already connected to the bounded `geometric_nonlinear_static` route. Uses reference gradients, `F`, `E`, `S`, `P=FS`, material plus geometric tangent, and reference-volume integration. Current route accepts one element family/material, `isotropic_3d`, nodal dead loads, and optional explicitly selected frictionless penalty contact. E01-D/E fixtures should exclude contact. Existing code rejects `det(F)<=1e-10`; this is a software guard, not an approved physical domain. |
| TL isochoric/volumetric Neo-Hookean elasticity | No element integration | No element integration | `finite_strain_elastic.py` is an isolated material-point API only. `build_total_lagrangian_assembly` constructs `SolidMaterial(E,nu)` and the public geometric solver validates `isotropic_3d`; neither dispatches this law. No material-factory registration, element results, or route exists. |

Other relevant compatibility facts:

* `geometric_nonlinear_static` calls the existing Full Newton engine with its route parameters (default `tolerance=1e-9`, `max_iterations=30`) and existing robustness/line-search policy. This does not automatically apply the frozen E01-A experimental 25-correction profile or certify an Armijo derivative for a new material route. Do not change the legacy default to make it appear E01-A compliant.
* The standard nonlinear assembly owns trial/accepted material-state tables. It calls each element with the accepted material state and collects detached trial states; the nonlinear driver commits after acceptance and rolls back a failed trial. `initial_material_states` creates one state per element integration point. Checkpoint and restart evidence still needs a route-level E01-E fixture.
* The geometric StVK route’s public element result contains `det_f`, Green strain, PK2 stress, Cauchy stress, and strain-energy density. For HEX8 the existing `element_states` path volume-averages Gauss-point quantities; it does not expose PK1 or the full per-point field. The TL J2 integration-point results do expose point entries but the route is not finite-strain J2. New E01-E results need explicit measure/frame/location metadata and must retain full nine-component PK1 separately from symmetric six-component stress tensors.
* TET4 TL has both a direct verification kernel and the batch class used by the geometric route. Their formulas are duplicated. Keep one as an independent cross-check; do not fork another TET4 law.

## 4. Element residual and tangent contract

### 4.1 Small-strain J2

At reference integration point `g`, let `B_g` map nodal increments to engineering strain in the order above. With accepted material history `z_n`, compute a detached trial response

\[
\epsilon_g=B_g u,\qquad (\sigma_g,z_g^{trial},C_{alg,g})=\mathcal{M}(\epsilon_g;z_n).
\]

For reference quadrature measure `w_g det(J_0)_g`,

\[
f_{int,e}=\sum_g w_g\det(J_0)_g B_g^T\sigma_g,\qquad
K_{int,e}=\sum_g w_g\det(J_0)_g B_g^T C_{alg,g}B_g.
\]

The global dead-load equilibrium residual is `R_f=(lambda f_ext-f_int)_f`; its Jacobian is `J_R=-K_int` on free DOFs. Prescribed DOFs are eliminated/reconstructed; reaction entries are excluded from the free residual. Repeat each Newton/finite-difference material evaluation from the same accepted `z_n`; only the accepted increment commits `z_g`. TET4 uses one point; HEX8 uses the existing eight-point rule. Do not substitute a Green–Lagrange strain or PK2 measure into this small-strain contract.

### 4.2 Total-Lagrangian elastic response

At reference node `a`, with reference gradient `N_{a,J}`:

\[
F_{iJ}=\delta_{iJ}+\sum_a u_{ai}N_{a,J},\quad
C=F^TF,\quad E=\tfrac12(C-I),\quad J=\det F.
\]

The material law returns reference-frame symmetric `S`, full current/reference PK1 `P=FS`, current-frame symmetric `sigma=J^{-1}P F^T`, energy per reference volume `W`, and a consistent tangent. The virtual work and element internal force are

\[
\delta W_{int}=\int_{\Omega_0}P:\nabla_X\delta u\,dV_0,
\qquad f_{int,ai}=\int_{\Omega_0}P_{iJ}N_{a,J}\,dV_0.
\]

For hyperelasticity, `C_{IJKL}=dS_{IJ}/dE_{KL}` and the full material-plus-geometric linearization is

\[
A_{iJkL}=\frac{dP_{iJ}}{dF_{kL}}
=F_{iA}C_{AJBL}F_{kB}+\delta_{ik}S_{LJ},
\]

\[
K_{abik}=\int_{\Omega_0}N_{a,J}
\left[F_{iA}C_{AJBL}F_{kB}+\delta_{ik}S_{LJ}\right]
N_{b,L}\,dV_0=K_{mat}+K_{geo}.
\]

For StVK, `W=0.5 lambda (tr E)^2 + mu E:E`, `S=lambda tr(E)I+2mu E`, and `C=lambda I⊗I+2mu I_sym`. TET4 has constant reference gradients and one exact point for homogeneous affine states; HEX8 uses eight 2x2x2 Gauss points. Existing assembly uses reference-volume quadrature. The selected first integration scope should use dead nodal loads `R=lambda f_ext-f_int`; follower loads require an external-load tangent and are out of scope. `J>0` is necessary but not sufficient for a physically admissible or well-conditioned case. Preserve existing code guards and require a case/material domain decision before any new route.

## 5. Minimum opt-in interfaces and Owner review boundary

Keep two constitutive paths separate:

1. **Small-strain J2:** reuse `evaluate_constitutive(material, strain, accepted_state)` and the existing element state protocol. Do not pass finite-strain `F` to this API.
2. **TL elasticity:** retain the separate `FiniteStrainElasticResponse`-style `evaluate(F)` contract with `W`, `S`, `P`, `sigma`, `dS/dE`, and `dP/dF`. The element adapter evaluates one response per integration point and assembles the reference internal force and full tangent. It must not register this response through the small-strain factory by duck typing.

Existing StVK routes remain unchanged. The C1 Neo-Hookean route cannot be added without changes to `core/assembly/geometric.py`, `core/analyses/geometric_nonlinear.py`, material input validation/factory dispatch, result fields, and likely checkpoint/identity metadata. These are protected integration/solver surfaces under the current mandate. Prepare that patch only after Owner approval of the exact Neo-Hookean energy/domain, route-specific Newton profile, result contract, and qualification boundary. No material registration or solver dispatch was changed here.

## 6. Proposed independent element V&V fixtures — NOT EXECUTED

All limits below are **proposed**, not frozen. Reference forces and energy are computed independently from closed-form `P/S/W` or analytic manufactured-solution derivatives; do not use the element’s own assembly to generate its oracle.

| ID | Mesh/material/boundary data | Observable/reference and proposed gate | Expected refusal / diagnostic |
|---|---|---|---|
| `DE-01-zero` | One unit tetrahedron (4 nodes, 1 TET4, 12 local DOF) and one unit cube (8 nodes, 1 HEX8, 24 local DOF); StVK `E=70 GPa, nu=0.30`; zero load and zero `u`; minimum rigid-mode supports, leaving free DOFs. | `W=0`, `S=P=sigma=0`, `J=1`; free residual norm divided by `E L^2` no greater than proposed `1e-12`. | Nonfinite fields, negative/zero reference Jacobian, or nonzero zero-state force beyond the declared scale fail. |
| `DE-02-linear-limit` | Same single elements; StVK and candidate Neo-Hookean; affine `H=diag(1e-6,-nu*1e-6,-nu*1e-6)` prescribed at every node. | Compare resulting stress and nodal force to independent infinitesimal isotropic elasticity. Proposed relative error `<=1e-5` normalized by `max(||C eps||, C_ref||eps||)`; report absolute error too. | This is a limiting check, not evidence of broad finite-strain accuracy. |
| `DE-03-affine-patch` | One TET4 and one HEX8; each elastic law separately; `E=70 GPa, nu=.30` (for Neo-Hookean convert to `K,mu`); prescribe affine `F=diag(1.05,.98,1.00)` on all element nodes. | Compare `E,S,P,sigma,W` and nodal internal forces to direct tensor formulas plus independent quadrature. Proposed normalized force/stress/energy error `<=1e-10`; report every absolute error. | `J=1.029`; response must be finite and preserve measure labels. |
| `DE-04-rigid-rotation` | One element of each family and each elastic law; `F=Q`, `Q` a fixed proper 73-degree in-plane rotation; prescribe `u=(Q-I)X`. | `E=S=P=sigma=W=0` up to roundoff; proposed normalized force/energy bound `1e-12` with material/element scales. Test tensor covariance, not componentwise invariance of spatial tensors. | `det Q` must be positive; a reflection is not a rigid rotation fixture. |
| `DE-05-element-tangent` | One TET4 and HEX8; StVK and Neo-Hookean; base `F` from `DE-03`; test six symmetric tensor basis directions, at least three independent mixed/rotated directions, and weak-response directions. | Compare raw `K_int p` against centered FD of `f_int(u)` at fixed configuration; normalize by `max(||FD||, K_ref||p||)` and also report direction-local error. Proposed gate `1e-7` with three-step plateau; step scale dimensionless in strain and displacement perturbation `h_u=L_char h_eps`. | Refuse centered differences if `J<=0` or step crosses a constitutive/domain boundary. |
| `DE-06-tangent-split` | Same TL fixtures, material states as `DE-05`. | Independently assemble `K_mat` and `K_geo`; verify `K=K_mat+K_geo` and compare both to the exact tensor contraction above. Proposed normalized sum error `<=1e-12`; also compare unsymmetrized matrices before any assembly symmetrization. | A missing or double-counted geometric term is a mandatory failure. |
| `DE-07-invalid-geometry` | TET4 reversed reference node order; HEX8 inverted/folded reference geometry; positive reference elements with a current `F` of nonpositive determinant. | No tolerance: validation must fail closed before returning force, tangent, or result fields. Include near-guard positive `J` as diagnostic only. | Do not treat existing `1e-10` as an Owner-approved physical `J_min`; record case-declared admissibility margin. |
| `DE-08-elastic-increments` | Unit cube, 2x2x2 HEX8 mesh (8 elements, 27 nodes, 81 DOFs; 1 interior node) and matched 48-TET4 split; StVK `E=210 GPa, nu=.30`; affine uniaxial-strain ramp to `F_xx=1.03`, y/z fixed, boundary displacement prescribed from the affine field. | Four accepted load factors `0.25,0.50,0.75,1.0`; compare the interior affine solution, energy, and reactions to homogeneous closed form. Proposed relative reaction/energy error `<=1e-8`; require exact final target and accepted-state continuity. | Failed increment must leave last accepted displacement/state unchanged; final target not accepted until all checks pass. |
| `DE-09-J2-transition` | Same 8 HEX8 / 48 TET4 meshes; small-strain J2 `E=210 GPa, nu=.30, sigma_y0=250 MPa`; cases `H=0` and `H=1.5 GPa`; prescribed affine uniaxial-strain path to `eps_xx=.003`, transverse strain zero, four equal increments. | Independent tensor radial-return oracle at every point; compare stress, alpha, and internal variables at fixed incoming state. Proposed stress relative error `<=3e-12` plus `0.02 Pa` absolute floor from B6 candidate; proposed smooth-branch tangent gate `1e-8` only after Owner approval and a multi-direction plateau. | Elastic/plastic transition uses one-sided checks; never use centered FD across yield. No J2 Full Newton claim while tangent gate is blocked. |
| `DE-10-transaction-checkpoint` | Same stateful J2 mesh and path; checkpoint only after accepted increments; inject a typed finite increment failure at the next increment in a synthetic contributor. | Verify rejected attempt restores displacement and every GP state digest, ledger persists, accepted commit count increments once, and restart replays the same accepted state. These are exact invariants, not tolerance gates. | This is a Python checkpoint/restart study; it does not prove abrupt-crash or filesystem durability. Unknown/missing state identity fails closed. |
| `DE-11-mesh-sensitivity` | Manufactured smooth displacement `u_x=A sin(pi x) sin(pi y) sin(pi z)`, `u_y=u_z=0`, `A/L=.01`; cube meshes at 1, 2, 4 subdivisions per edge. HEX8 counts 1/8/64; split each subcube into 6 TET4s for 6/48/384. StVK first; Neo-Hookean only after formulation approval. Prescribe exact boundary `u`, derive body force `b=-Div_X P` independently from analytic `P(F(X))`. | Record energy-norm displacement error, reaction error, and three-level rates. `J>=1-pi*.01>0` for this field. Mesh/rate gate and physical quantity-of-interest tolerance remain Owner decisions; initially diagnostic, not a pass/fail promotion. | Fail on nonfinite or nonpositive `J`; report geometric conditioning at every quadrature point. |

The mesh sizes are bounded (at most 384 TET4 or 64 HEX8, 375 global DOFs, one material, eight quadrature points per HEX8). Proposed run cap for a later offline Python element campaign: one process, no children, <=256 MiB memory and <=120 s per exact module. These are planning bounds, not evidence. Any full public solver run, external backend, or native FEM requires its own Owner execution GO and manifest.

## 7. Test/collection safety inventory

No new pytest module was created. B6/C1 hashes below are current and their exact `NUMERICAL_UNIT` registry entries match. The selected B6/C1 imports are reviewed NumPy/SciPy/material-point paths without element assembly, public solve, Gmsh, native backend, worker, or child process.

| Exact path | Current test IDs / count | Current safety status and SHA-256 | Execution status here |
|---|---|---|---|
| `tests/unit/test_wp_e01b_b6_residual_jacobian.py` | 10 expanded cases; fixed-state J2 residual/Jacobian and one-sided yield cases | Registered `NUMERICAL_UNIT`; `2BC4CB5EF8AC4FB08DC78868EEEB90641CDF6D7B2C9A75B3BCCB8490762C09FF` | Prior exact-path Owner GO: 10/10 PASS; not rerun. |
| `tests/unit/test_wp_e01c_finite_strain_material.py` | 17 expanded cases; material point only | Registered `NUMERICAL_UNIT`; `F64A3F9B2E296A2366A977A782C27635AB2E6868F2C44D55A84560D9A59399F9` | Prior exact-path Owner GO: 17/17 PASS; not rerun. |
| `tests/unit/test_total_lagrangian_tet4.py` | 6 test functions: linear reference, rotation, extension energy, tangent FD, force-only parity, inverted `F` | No explicit reviewed digest entry. Imports/instantiates project element classes; the collection classifier conservatively yields `NATIVE_AUTH_REQUIRED` unless a specific hash-bound review is added. SHA `A90E765029B8D2A0F207ACD3093C187175D2AADA199A81CB34830A02AD03A6CB`. | NOT RUN. |
| `tests/unit/test_total_lagrangian_hex8.py` | 4 test functions: zero/reference, rotation, tangent FD, distorted positive mesh | No explicit reviewed digest entry; same conservative collection behavior. SHA `7A3CB92DF6C7664536940D6AF8D30DB34C161291B700933ABD6CF7B95C05E542`. | NOT RUN. |
| `tests/unit/test_corotational_j2.py` | 6 test functions: bounded Newton, rotation, state transport/isolation, strain refusal | No explicit reviewed digest entry; imports project route classes, so do not run under this mandate. SHA `0B7FDA1D57BC949D6ED1DDB731D54CCFAB563ACC74EA269E50D7D195E849B218A`. | NOT RUN. |
| `tests/unit/test_nonlinear_state_transaction_contract.py` | 5 test functions: generic/material rollback, commit, corruption | No explicit reviewed digest entry. SHA `252ACEC314F0949AC65BEEA18A1815A0A29C50C29D22272F49925571DD963985`. | NOT RUN. |
| `tests/unit/test_nonlinear_assembly_plan.py` | 4 test functions: plan reuse, uncached path, sparse assembly, chunk guards | No explicit reviewed digest entry; assembly tests are FEM numerical execution and require Owner authorization. SHA `73645C7908ACC830732DA92D17E6E4DB021C38F859525E0E89CFAF0C882230C8`. | NOT RUN. |
| Proposed `tests/unit/test_wp_e01de_element_algebra.py` | 30 planned parameter-expanded element algebra cases from `DE-01`–`DE-07` and J2 material tangent actions | NOT CREATED; hash TBD. Candidate `NUMERICAL_UNIT` only after import-closure review, exact hash registration and explicit Owner GO. | NOT RUN; requires separate exact-path Owner authorization because it executes element kernels. |
| Proposed `tests/unit/test_wp_e01de_path_state.py` | 8 planned path/rollback/checkpoint cases from `DE-08`–`DE-10` | NOT CREATED; hash TBD. Solver/state route and temporary-file closure require separate safety review; no classification granted. | NOT RUN; requires separate Owner GO. |
| Proposed `tests/unit/test_wp_e01de_mesh_refinement.py` | 6 planned mesh levels (2 families x 3 levels) for `DE-11` | NOT CREATED; hash TBD. Element assembly is offline Python but still FEM numerical execution; no safety classification granted. | NOT RUN; requires separate Owner GO. |

Collection rules: do not weaken `tests/conftest.py`; do not use a broad selector. The `conftest.py` Gmsh probe is restricted to its optional mesh-module set; none of the two registered material-point modules is in that set. The existing unregistered element modules are skipped/classified conservatively rather than implicitly trusted. Any new test module needs a reviewed call graph, exact source digest, bounded resource envelope, and explicit test-tier record before an exact command is proposed.

## 8. P0/P1/P2 findings and blockers

* **P0:** none found in the inspected paths.
* **P1:** The direct J2 evidence is material-point/affine-spring only. The production TET4/HEX8 J2 element tangents have not been compared against an independent assembled element residual derivative at fixed accepted integration-point state. Keep `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE` and do not use the current symmetrized J2 tangents as a production Armijo certificate.
* **P1:** Neo-Hookean is material-point only. Element integration would require protected route/material/result changes and Owner choice of energy/domain. No finite-strain J2 is supported by this package.
* **P1:** The existing geometric nonlinear route uses legacy route controls; it does not automatically enforce the E01-A frozen experimental controls or supply a production Armijo certificate for a new constitutive route.
* **P2:** Geometric StVK result fields are element-averaged for HEX8 and omit PK1; the separate E01-E point-field metadata contract needs Owner approval. Existing `det(F)` and geometry thresholds are guards, not physical admissibility approvals.
* **P2:** TET4 StVK direct and batch paths duplicate equations. Use the direct kernel as a comparator for the batch integration; do not create a third implementation.
* **P2:** Current TL unit tests are not hash-registered as safe offline execution. Their Python-only appearance is insufficient; do not run them under the current mandate.

## 9. Decision-ready package and next step

For Owner review, freeze separately: (1) whether the J2 material-point tangent gate may use the proposed `1e-8` three-step branch-preserving threshold and which mixed/weak directions are mandatory; (2) whether to authorize bounded Python TET4/HEX8 element-kernel V&V; (3) the exact Neo-Hookean energy/domain and case-level `J_min` policy before any integration; (4) route-specific E01-A control/certificate requirements; and (5) per-integration-point result fields and metadata. No threshold in §6 is frozen here.

Suggested sequence: first authorize and hash-register a Python-only element-algebra module, then compare TET4/HEX8 residual/tangent against independent element oracles without invoking `solve_model`; next separately authorize small synthetic incremental/rollback checkpoint studies; only after those pass should an Owner consider protected route changes or any native FEM GO. A passing element unit module would still not constitute native FEM V&V, qualification, or release evidence.

## 10. Required statuses

```text
J2_TANGENT_GATE: REVISE (bounded material-point result is useful; add mixed/weak directions and assembled element-level gate before freeze)
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
ELEMENT_RESIDUAL_TANGENT_CONTRACT: PREPARED
TET4_INTEGRATION: IMPLEMENTED_BY_SOURCE (small-strain J2 and TL/StVK only; Neo-Hookean integration absent)
HEX8_INTEGRATION: IMPLEMENTED_BY_SOURCE (small-strain J2 and TL/StVK only; Neo-Hookean integration absent)
FINITE_STRAIN_MATERIAL_POINT_VNV: VERIFIED_BOUNDED_PREVIOUS_EVIDENCE
ELEMENT_LEVEL_VNV: PREPARED_NOT_RUN
NATIVE_FEM_VNV: NOT_RUN
PRODUCTION_ARMIJO_CERTIFICATE: NOT_VERIFIED
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

## Appendix A — source and evidence hashes

The baseline HEAD is recorded above. Hashes below identify the audited source/test artifacts, not an implementation change in this report.

| File | SHA-256 |
|---|---|
| `qualification/0_2_12/owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md` | `C5140D75444905CB79E54FE995A0DCE7EF060FDC6473979AACA15136285C22F1` |
| `src/solveur/materials/finite_strain_elastic.py` | `757876588DC437F10614822883920A8A4FE27254EEA88C2FCB9794CE2CD8CE35` |
| `src/solveur/materials/solid.py` | `7D8223C81999D037900C26BF1A6A2ABC9F4B47C0CFF597F4BE0CF0163E8092AA` |
| `src/solveur/elements/solid/tet4.py` | `0517683946A0292E2224D77BA197229EBDBC91DCF935B57D9B75E728D9BE3D0B` |
| `src/solveur/elements/solid/hex8.py` | `4DD8BA606B7E8CAB9697FD26CE0BAF37FBAF046F9E95894AFB0AC8EAA0C85D7A` |
| `src/solveur/elements/solid/tet4_total_lagrangian.py` | `3CA06B5DA5BF8AF148603432DEA635D7507D32ECC24BC021FB563C52BBEDBF2C` |
| `src/solveur/elements/solid/tet4_total_lagrangian_batch.py` | `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `D6E524B2233A84702974518A1F2136C0BEF00BC744F120041150EAE78BBF1BF5` |
| `src/solveur/elements/solid/total_lagrangian_j2.py` | `1CD4B3FE91FBA43521DD17346AD9ACA8015862A7578C07FE9250582D218823CB` |
| `src/solveur/elements/solid/corotational_j2.py` | `11D121FD3D32CB5FEFE0D23802D36974EF683AC545ADB6B08661F3021849796C` |
| `src/solveur/core/assembly/nonlinear.py` | `C5C6E1953C3B08C30397F18F8DF07FB8D355216BF372C45CEE5695FCE7BC65E1` |
| `src/solveur/core/assembly/geometric.py` | `B81454F32F8A824725F3E0902871EB5394BB0A4D83BD4709D9DC626A3108A22C` |
| `src/solveur/core/analyses/geometric_nonlinear.py` | `57C65E438FF745CB2FE66A4216749412A5440758FE0E9E6F43674D1310CE89E9` |
| `src/solveur/core/nonlinear/iteration.py` | `5383A183FAE7F16D75E752FB402CC81B4931A1649655DA5180C1BE5A2E3AEBA2` |
| `src/solveur/core/nonlinear/material_state.py` | `6439F50398A8A914123ABD804752C018D879FAD909F437F075267373916B7DFA` |
| `src/solveur/core/nonlinear/contracts.py` | `FAEA669E31A85988071E64D930246769212F5745ED5E09E8ECC07B7200363809` |
| `src/solveur/post/solid_results.py` | `751DE6ADBDFFF1B508E0D46CB823EF4BE5315167D113189686037D5302225A87` |
| `src/solveur/core/results.py` | `83ED02B68C8DE953F50C2A4BAE42DDC8180069E10B52876AEE2E523E120B27FA` |
| `tests/unit/test_wp_e01b_b6_residual_jacobian.py` | `2BC4CB5EF8AC4FB08DC78868EEEB90641CDF6D7B2C9A75B3BCCB8490762C09FF` |
| `tests/unit/test_wp_e01c_finite_strain_material.py` | `F64A3F9B2E296A2366A977A782C27635AB2E6868F2C44D55A84560D9A59399F9` |
| `tests/unit/test_total_lagrangian_tet4.py` | `A90E765029B8D2A0F207ACD3093C187175D2AADA199A81CB34830A02AD03A6CB` |
| `tests/unit/test_total_lagrangian_hex8.py` | `7A3CB92DF6C7664536940D6AF8D30DB34C161291B700933ABD6CF7B95C05E542` |
| `tests/unit/test_corotational_j2.py` | `0B7FDA1D57BC949D6ED1DDB731D54CCFAB563ACC74EA269E50D7D195E849B218A` |
| `tests/unit/test_nonlinear_state_transaction_contract.py` | `252ACEC314F0949AC65BEEA18A1815A0A29C50C29D22272F49925571DD963985` |
| `tests/unit/test_nonlinear_assembly_plan.py` | `73645C7908ACC830732DA92D17E6E4DB021C38F859525E0E89CFAF0C882230C8` |
| `tests/conftest.py` | `E4A02602E82715362A2E934FD1296DB320C5CEB19CA5B7AB2C967CA5CD505677` |
