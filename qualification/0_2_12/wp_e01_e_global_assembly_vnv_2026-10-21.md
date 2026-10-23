# WP-E01-E — Global assembly V&V preparation (2026-10-21)

## 1. Executive disposition

This package prepares a bounded, in-memory global assembly suite for the existing TET4/HEX8 small-strain J2 and Total-Lagrangian StVK assembly paths. It adds no production source and does not execute pytest, collection, numerical fixtures, a nonlinear solve, native FEM, Gmsh, a worker, or a subprocess. The D4R run remains historical evidence: 65 PASS under `tests/unit/test_wp_e01d1_element_vnv.py` SHA-256 `FFA43CB053934C6DFF319955CB0857634C761662869D4B49B6BE4973F5FD6B6D` and registry SHA-256 `1E605BE8AA656B1B0FCD81D3AAA87FDAEF75AF5E3BAA4EBDF8FD5272A3BF47A3`; it was not rerun in this campaign.

| Status | Result |
|---|---|
| `D4R_ELEMENT_VNV` | `PREVIOUS_65_PASS_BOUNDED` |
| `GLOBAL_ASSEMBLY_FIXTURES` | `IMPLEMENTED_BY_SOURCE` |
| `GLOBAL_ASSEMBLY_TESTS` | `PREPARED_NOT_RUN` |
| `GLOBAL_RESIDUAL_JACOBIAN` | `PREPARED` |
| `J2_STATE_COMMIT_ROLLBACK` | `PREPARED`, helper-level only |
| `CHECKPOINT_RESTART` | `INCOMPLETE`; schema-v2 serialization round trip is prepared, no solver restart/recovery test |
| `GLOBAL_REACTION_BALANCE` | `PREPARED`, displacement-controlled synthetic patch only |
| `J2_TANGENT_GATE_REVIEW` | `INDEPENDENT_REVIEW_COMPLETE` |
| `J2_TANGENT_SCIENTIFIC_FREEZE` | `NOT_APPROVED` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED`; registry remains empty |
| `INTEGRATED_FEM_VNV` | `NOT_RUN` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

The repository identity was verified in the isolated worktree at root `C:\wpc01-frictionless-public-integration-wt\wp-e01`, remote `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch `codex/qf-wp-e01-a-implementation-20261020`, clean baseline HEAD `32e8743eb5558479e399d238541e1238f0c61f22`. No canonical roadmap or historical record was edited.

The historical D4R report also records bounded J2 state validation, all-direction tangent checks under candidate criteria, direct raw-tangent-skew measurements, and TET4/HEX8 J2 and TL/StVK element evidence. Those findings remain tied to the D4R test identity and do not establish global assembly, solver, checkpoint-restart or Newton/Armijo correctness.

## 2. Prepared executable inventory

The original 18-case candidate was extended by two negative cases, one for each element family, to exercise the global J2 assembly boundary with a surplus TET4 state and a truncated HEX8 state. The resulting static inventory is eight test functions and 20 parameter-expanded cases. This is a source-derived inventory; pytest collection was not run.

| Test function | Cases | Reference or behavior |
|---|---:|---|
| `test_j2_global_affine_elastic_patch_and_reaction_reference` | 2 | TET4/HEX8 elastic affine patch; closed-form stress, independent face traction, free-center residual, resultant and moment balance |
| `test_j2_global_monotone_path_matches_tensor_return` | 4 | TET4/HEX8 × perfect plasticity / linear isotropic hardening; virgin state then five monotonically increasing accepted synthetic states |
| `test_j2_global_residual_tangent_fixed_state_fd` | 4 | TET4/HEX8 × two hardening moduli; fixed nonzero accepted history, independent tensor-return force finite differences, four directions, branch margins and independently scattered production local outputs |
| `test_j2_global_accepted_state_trial_rollback_and_exactly_once_commit` | 2 | TET4/HEX8 `MaterialStateSession` helper rollback, commit once, and rejection of a second commit |
| `test_j2_global_accepted_state_wp10_v2_checkpoint_serialization_roundtrip` | 2 | TET4/HEX8 schema-v2 accepted-state save/load round trip through `tmp_path`; identity and material-state equality |
| `test_stvk_global_rigid_rotation_and_affine_patch` | 2 | TET4/HEX8 rigid rotation and homogeneous finite-deformation patch with independent `P N` face forces |
| `test_stvk_global_residual_tangent_and_material_geometric_split` | 2 | TET4/HEX8 nonuniform nodal field; independent quadrature force, full tangent, material/geometric split and four directional differences |
| `test_j2_global_assembly_rejects_wrong_integration_point_state_vector` | 2 | TET4 surplus state / HEX8 missing state refused without mutating input history |
| **Total** | **20** | **8 test functions** |

The source lives at `tests/unit/test_wp_e01e_global_assembly_vnv.py`. It calls the existing `assemble_internal_tangent` and `build_total_lagrangian_assembly` kernels directly. It does not call a nonlinear driver or solver. The constraint map is read from `GlobalAssembler.fixed_indices`; no constrained solve is run.

The module is long because its small mesh constructors, independent tensor/quadrature oracles and parametrized cases form one execution package. It remains a single hash-bound identity so those executable references are not split into an additional unbound helper. A future split would require a fresh dependency-hash and execution-safety review.

## 3. Independent mechanical references

### Meshes and units

Both fixtures occupy the reference unit cube `[0,1]^3` in metres. The TET4 mesh has eight cube-corner nodes and a center node, split into 12 positively oriented tetrahedra; each TET4 uses its one constant-gradient point. The HEX8 mesh is a regular `2×2×2` partition with 27 nodes and eight elements; each HEX8 reference independently evaluates the trilinear shape gradients at the `2×2×2` Gauss points. TET4 has 36 global displacement DOFs and HEX8 has 81. Every exterior node is prescribed and the center node is free, leaving three free DOFs.

Material inputs are `E=210 GPa`, `nu=0.30`, `sigma_y0=250 MPa`, and `H∈{0,1.5 GPa}`. Coordinates and displacements are metres; strain is dimensionless; stress and tangent moduli are Pa; internal forces and reactions are N; global stiffness is N/m; moment is N·m. The unit cube has `V=1 m³`, reference face area `A=1 m²`, and characteristic length `L=1 m`. The TET4 mesh has 27 global displacement DOFs and HEX8 has 81; each leaves exactly three center-node DOFs free.

### Small-strain J2

The independent material oracle uses tensorial strain and stress, isotropic elasticity, associated J2 flow and the approved radial return:

\[
q=\sqrt{\tfrac32\,s:s},\qquad
f=q-(\sigma_{y0}+H\alpha),\qquad
\Delta\gamma=\frac{f_{\rm trial}}{3\mu+H},\qquad
\Delta\alpha=\Delta\gamma.
\]

The engineering-Voigt material state is converted to a tensor plastic strain before the reference return. Reference gradients are independently reconstructed from affine interpolation for TET4 and from explicit trilinear derivatives/Jacobians for HEX8. For every perturbed displacement, the oracle recomputes stress at each integration point from the same fixed accepted state and separately scatters

\[
f^{\rm int}_{ai}=\sum_g w_g\,\sigma_{ij}^{(g)}N_{a,j}^{(g)}
\]

to the global DOF map. The finite-difference force field does not call the production J2 material update, production element kernel, or production global force scatter. At the base displacement, the independently assembled force is also compared against production global force. The history used in the tangent check is first checked against the tensor-return preload reference.

The elastic patch uses `epsilon=diag(1e-4,0,0)`. The analytical stress is `sigma_xx=28.269230769 MPa`, `sigma_yy=sigma_zz=12.115384615 MPa`, zero shear, and zero accumulated plastic strain. The monotone path uses load fractions `(0.25,0.50,0.75,0.80,1.0)` of `epsilon_x=0.002`; it transfers each returned trial state to the next synthetic state. This is a material-state progression fixture, not a nonlinear equilibrium/load-control path. It does not establish unloading, reverse re-yielding or production increment rollback.

For the J2 tangent case, the accepted history is generated at `epsilon_x=0.0016` and compared with the independent reference before use. The trial field has `epsilon_x=0.003` plus a center-node offset to break homogeneity. The FD perturbations hold the accepted state fixed. Every direction must stay on the smooth plastic branch for both signs of every tested step; crossing a yield switch is a failure of fixture eligibility, not an invitation to use a centered derivative across the switch.

### Total-Lagrangian StVK

The independent reference constructs `F=I+Grad_X(u)`, `E_GL=0.5(FᵀF-I)`, `S=λ tr(E_GL)I+2μE_GL`, `P=F S`, and

\[
f^{\rm int}_{ai}=\int_{V_0}P_{iJ}N_{a,J}\,dV_0.
\]

Its material tangent is the `F C F` contraction and its geometric tangent is `delta_ik ∫ N_{a,J} S_{LJ} N_{b,L} dV_0`. The reference code independently builds shape gradients/quadrature and assembles both pieces. Production force, full tangent and geometric tangent are compared separately. The rigid-rotation fixture uses a proper rotation about `z` by `0.73` radians; it tests zero energy/force and does not require individual tensor components to remain unchanged under rotation. A second homogeneous deformation checks the `P N` surface-force reference. The nonuniform center-offset fixture compares the discrete production assembly and tangent with the independently coded quadrature oracle; its HEX8 reference uses the same mathematical `2×2×2` rule as production, so it verifies the discrete formulation and linearization, not exact continuum integration of a nonuniform field.

### Residual, tangent and reactions

This fixture package explicitly chooses

\[
R(u)=F_{\rm int}(u)-F_{\rm ext}(u),\qquad
J_R=\frac{\partial R}{\partial u}=K_{\rm int}
\]

for dead external force. The current displacement-controlled fixtures set the explicit nodal vector `F_ext` to zero, so the derivative checked is the internal-force derivative and equals the derivative of this residual. The analytical face traction vector (`sigma n` for small-strain J2, `P N` for TL/StVK) is an independent comparison/balance reference; it is not inserted as an external load or sent through a solver load assembler. Fixed-DOF residual entries are compared with that face reference, the free center residual is checked, and support residual resultant/moment closure is checked. This is synthetic reaction-balance evidence only.

The earlier D4R candidate described a dead-load derivative using the opposite residual sign. That historical text is not edited. This suite and the chosen reaction residual use `F_int-F_ext`, hence `+K_int`. There is also a route-level sign distinction to resolve before solver integration: the frozen E01-A residual is `target_force - internal_force`, while `src/solveur/core/nonlinear/solver.py` and `src/solveur/core/audit.py` use `internal - external` for final residual/reactions; `src/solveur/core/nonlinear/driver.py` forms `load_factor*external - internal`. The current suite verifies assembly force/tangent only and does not certify any Newton route's residual/Jacobian sign mapping.

## 4. Candidate numerical checks (not Owner-frozen)

| Check | Candidate definition / threshold | Units and role |
|---|---|---|
| Patch force / balance | `||f_int-f_surface|| / max(||f_surface||, F_ref) ≤ 1e-10`; free residual and total force/moment use the same physical scales | Dimensionless mandatory fixture assertion; `F_ref` N, moment scale N·m |
| J2 material stress/state | stress error `≤ 3e-12 max(||sigma_ref||,0.02 Pa)+0.02 Pa` | Pa absolute floor plus dimensionless relative term |
| Global tangent scale | `K_ref=max(3K,2mu) V/L²` | N/m; `K` is bulk modulus, `mu` shear modulus |
| J2 tangent error | `rho_g=||K p-D_h f_ref[p]|| / max(||D_h f_ref[p]||,K_ref||p||) ≤ 1e-7` | Dimensionless; proposed global criterion |
| J2 direction-local error | `rho_p=e_p/max(||D_h f_ref[p]||,64 eps K_ref||p||) ≤ 1e-5` | Dimensionless; applies only when response exceeds the declared near-null floor; otherwise `NOT_EVALUABLE`, while global criterion still applies |
| StVK tangent error | Same global normalization, candidate `≤ 1e-7` | Dimensionless |
| Force/tangent decomposition | Independently reconstructed force, full tangent and material/geometric pieces: each relative error `≤1e-10` with its physical reference scale | Force N; tangent N/m |
| Rotation check | Roundoff bound `512 eps E A` for force and that bound times `L` for energy | N and N·m; proposed fixture guard |
| FD sweep / plateau | Step multipliers `(1e-4,3e-5,1e-5,3e-6,1e-6,3e-7)` on directions with `||p||=L`; the final three derivative estimates must share a plateau whose two adjacent normalized changes are each `≤1e-6` | Step multipliers dimensionless; `h p` has units m. Every global error in that same three-point window must meet its proposed gate. Every eligible local error in that same window must meet its local gate. |

These are test-candidate thresholds, not approved defaults and not measured results. The shared final-three plateau fixes the prior acceptance loophole: the minimum error and plateau may not be taken from unrelated parts of the sweep. Weak near-translation directions still have a mandatory global check. A direction-local metric is `NOT_EVALUABLE` only when its response falls below `64 eps K_ref||p||`; no local relative error is manufactured in that case.

## 5. State and restart limits

The suite distinguishes:

* **Virgin initialization:** `initial_material_states` supplies initial per-point state.
* **Accepted history:** monotone and preload references carry detached states to later synthetic evaluations.
* **Trial evaluation:** the production assembly returns a new candidate state; the accepted input digest is checked unchanged.
* **Helper rollback/commit:** `MaterialStateSession` is tested for isolation, rollback and exactly-once commit; this does not exercise a production increment driver.
* **Checkpoint:** the prepared test serializes one accepted state as schema-v2 NPZ and verifies save/load identity and material-state equality in `tmp_path`. It does not recover an interrupted attempt, persist a rejection ledger, resume Newton, or demonstrate filesystem/crash durability.

The checkpoint test preserves WP10 v2 behavior and uses no new schema. `NpzNonlinearCheckpointStore.save/load` imports a checkpoint-signature helper whose module also defines an unused Git-status subprocess helper. Static call-path review found the fixture's schema-v2 signing path calls only content hashing; it does not call the Git helper. No claim about actual runtime call reachability or crash behavior is made before the exact-path GO.

## 6. Source compatibility and V&V boundaries

| Route / layer | Current use in this package | Boundary |
|---|---|---|
| TET4/HEX8 small-strain J2 | Existing nonlinear global internal-force/tangent assembly and actual element kernels | No production material or assembly changes; no finite-strain plasticity |
| TET4/HEX8 TL/StVK | Existing geometric assembly and its tangent APIs | No public solver or default dispatch changes |
| Constraint map | `GlobalAssembler.fixed_indices` for free/fixed DOF identification | No global equation solve or nonlinear convergence claim |
| Contact | Assembly module imports conditional contact helpers; models contain no contacts and the fixture does not invoke contact assembly | No WP-C02/contact changes or contact integration claim |
| Checkpoint | Existing WP10 v2 save/load path on temporary files | Round-trip only; no new checkpoint semantics |
| Newton / Armijo | Not invoked | `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` remains empty; production Armijo unavailable |
| Neo-Hookean | Not invoked | No production dispatch/integration change |

Static source review confirms `assemble_internal_tangent` performs additive element scatter and returns the internal-force tangent; `solver.py`/`audit.py` use the `internal-external` final residual for reaction reporting. The test independently constructs its own DOF scatter for the J2 force reference and StVK quadrature reference. The J2 tangent FD is now independently driven by the tensor-return global force oracle at each perturbation, not by repeated production assembly. Direct element D4R evidence remains evidence for its D4R executable identity only.

## 7. Safety and exact-path execution proposal

The module is registered in `tests/conftest.py` as `NUMERICAL_UNIT`, hash-bound to its exact source. No registry classification or mandatory test guard was weakened. Static hook review shows Gmsh capability probing is lazy and limited to two unrelated optional Code_Aster modules; this module is not in that set. The production assembly module imports contact helper modules, but the models have no contacts and the tested function call does not enter their assembly. The checkpoint dependency imports `subprocess` in `manifest.py`, but the selected save/load call path does not invoke `_git_output`. The test source does not call `solve_model`, a public solver, a worker or a process API. These are source-level findings; pytest collection/runtime has not been observed.

Only the schema-v2 serialization fixture writes files, all beneath pytest's `tmp_path`. The largest dense global tangent is 81×81 `float64`; expected working memory is well below 256 MiB. Estimated runtime is under 120 s, unmeasured. A separately authorized run should cap numerical-library threading to one and execute only:

```powershell
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
python -m pytest -q -s tests/unit/test_wp_e01e_global_assembly_vnv.py
```

The future Owner GO must bind the then-current branch, clean HEAD, exact module hash and registry hash; authorize this exact module only; and require a fresh import/collection safety review. Do not use broad pytest or treat historical D4R authorization as applicable to this new identity.

## 8. Independent review and findings

A separate read-only reviewer inspected the current test and registry hashes without editing files, collecting tests, running numerical calculations or executing tests. The reviewer confirmed the corrected shared tangent plateau/error window, independent fixed-history J2 global force reference, dimensional scales, and bounded checkpoint/reaction claims. This is independent source review, not independent runtime evidence or Owner approval.

* **P0:** none found in the reviewed test source.
* **P1:** residual sign differs by route as recorded above; route-specific Jacobian mapping and Armijo proof remain unverified. It does not block this assembly-only package but blocks a Newton certificate claim.
* **P2:** StVK nonuniform HEX8 reference uses production-equivalent quadrature independently coded; it verifies the discrete assembly, not continuum-exact integration. Checkpoint test is a serialization round trip, not restart correctness. Material-state lifecycle tests use a state helper, not production increment orchestration.

## 9. Next Owner decision

Authorize one exact-path offline run of `tests/unit/test_wp_e01e_global_assembly_vnv.py` after verifying its current SHA-256 and the corresponding `tests/conftest.py` SHA-256 on a clean branch/HEAD. The run should be limited to this 20-case NUMERICAL_UNIT module under the reviewed synthetic in-memory paths and bounded resources above. It should authorize no solver, `solve_model`, FEM assembly driver, Gmsh, worker, child process, Armijo certificate, merge, qualification or release. A later integrated nonlinear FEM/Newton execution requires a separate Owner decision after this bounded assembly evidence is reviewed.

## 10. Source identity and hashes

The following exact hashes bind this prepared snapshot; they must be rechecked before any later GO.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01e_global_assembly_vnv.py` | `A6F6F104E331F1E9E09B384CF65B9FD49B783392C5B3C6002D67FE81A9ECEE45` |
| `tests/conftest.py` | `2A448E4070A8A441BFC0E3CE5B506E66CD104FB45A85DB7EDDF00D7A46A2FBAC` |
| `src/solveur/core/assembly/nonlinear.py` | `C5C6E1953C3B08C30397F18F8DF07FB8D355216BF372C45CEE5695FCE7BC65E1` |
| `src/solveur/core/assembly/assembler.py` | `23E0702165A65AFB2108670B2F140B8173F4857134A4E1461C5D75E8333B30CB` |
| `src/solveur/core/assembly/geometric.py` | `B81454F32F8A824725F3E0902871EB5394BB0A4D83BD4709D9DC626A3108A22C` |
| `src/solveur/elements/solid/tet4.py` | `5DAA0CDECE28F0C352649607872EED2A49900ACF7BE76BCC11EB98A8C9181B59` |
| `src/solveur/elements/solid/hex8.py` | `E4D37B19268BD7FCE81F270E17BA314CE8390667B19685CC982F514802E13A3F` |
| `src/solveur/elements/solid/j2_state.py` | `1DD85418DF2026D3A9E3DE4F8DA5FCA30021E85882F0606290F083C0D23C26A4` |
| `src/solveur/elements/solid/tet4_total_lagrangian_batch.py` | `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `95DF9E1895BB631D598FA52FD22986E153C865F77C91557E904FF0AF766451A6` |
| `src/solveur/core/nonlinear/checkpoint.py` | `EB2B320537D45B3AFD012E143B248237175D7528F7628FDA84E9D64E95885C81` |
| `src/solveur/io/nonlinear_checkpoint.py` | `69983B613DF6A4ECC16183D45AD67EC55BAFA2857043278CFA4B77026DC19709` |

No production file in this table was modified by this campaign. This report records prepared source and source review only; no execution result or qualification claim is inferred.
