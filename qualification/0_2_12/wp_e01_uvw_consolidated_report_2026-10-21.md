# WP-E01-U/V/W — Experimental Hencky Global FEM and Newton Campaign

Date: 2026-10-21
Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-uvw`
Branch: `codex/wp-e01-uvw-hencky-global-newton-20261021`

## Executive result

The campaign extended the prior Hencky material, constitutive-tangent, and element-tangent work through bounded global TET4/HEX8 assembly and an isolated incremental Newton prototype. Stage U completed **31/31 PASS** under the fixed-target Windows Job Object supervisor. Stage V collected all **16 authorized nodes** and executed once; the run recorded **13 PASS / 3 FAIL**. No retry was made.

The TET4 and HEX8 affine equilibrium paths converged in three corrections at each of four load increments. The three failures are confined to two exact accepted-state identity assertions after the numerical displacement-equivalence assertions passed, and one initial-equilibrium test which evaluates a nonzero dead-load vector at the default zero load factor. A separate reviewer found no production Newton P0/P1 defect indicated by the execution evidence. The failures remain recorded and the Stage V test suite is not accepted as fully passing.

The isolated assembly and Newton path are not connected to public solver dispatch. This campaign does not verify native FEM, general multi-degree-of-freedom nonlinear convergence, physical line-search rejection, persistence/restart, crash durability, finite-strain plasticity, or production Newton/Armijo.

## Provenance and campaign history

The continuation branch started at the verified WP-E01-T commit `86a3de3a7d5020367796e5069432779f49881e71`, in the dedicated worktree. The origin was `https://github.com/emptiesvoid-cloud/QF_solver.git`. No changes were made to the authoritative integration branch.

| Stage | Commit | Result |
|---|---|---|
| U implementation | `b1ce4620a6dc0c2d4812a704b119fabab0bc227e` | Isolated total-Lagrangian Hencky global assembly and 31-case V&V suite |
| U evidence | `d9992d43bac411e647684539516b937928a9306d` | 31/31 PASS report and immutable run evidence |
| V implementation | `4a3b5323e49dc0276174a4dc40cb31e425a20cae` | Isolated bounded incremental Newton prototype and 16-node suite |
| W documentation/evidence | final commit recorded after this report is committed | This report and preserved V execution artifacts |

Historical evidence remains separate and unchanged: WP-E01-P3 material/local-force tests **41/41 PASS**; WP-E01-S constitutive tangent tests **35/35 PASS**; WP-E01-T element tangent tests **34/34 PASS**. They were not rerun here.

The local reference `codex/v0.2.12-integration` was observed at `cccf897f207c17ecad105948d231bf1240057184`. The merge base with this campaign branch is `1d7fef04094d2f4b920795b4b3c25f052fcf21c0`; the local graph reports 3 integration-only commits and 650 campaign-only commits. The branches are substantially diverged. No merge, rebase, cherry-pick, or integration-branch edit was performed. Remote freshness was not checked.

## Verified formulation and source architecture

The material response is the opt-in Hencky hyperelastic energy

`W = μ ||dev(E_H)||² + (κ/2)(tr(E_H))²`, with `E_H = 0.5 log(FᵀF)` and `F = I + Grad_X(u)`.

For the affine reference `F = diag(s,1,1)`, the principal logarithmic strain is `E_H = diag(log(s),0,0)`. Therefore `||dev(E_H)||² = (2/3)(log(s))²`, `W = 0.5(κ + 4μ/3)(log(s))²`, and the independently derived PK1 component is `P11 = dW/ds = (κ + 4μ/3)log(s)/s`. Its product with the element's integrated free-node area has units N and defines the dead nodal force used in both example fixtures.

The established material returns PK1 stress. In the total-Lagrangian adapter, the reference-gradient internal force is assembled as

`f_int[a,i] = Σ_q P[i,J] Grad_X(N_a)[J] dV0`.

The assembled tangent contains the constitutive/material action and the geometric contribution. Element DOFs use node-major UX/UY/UZ order and are scatter-added into a sparse global matrix. TET4 uses one positive-orientation centroid point; HEX8 uses the full 2×2×2 Gauss rule. The implementation remains experimental and separate from public material dispatch and public solver routes.

For the supported displacement-independent dead nodal loads:

* Canonical residual: `R(u, λ) = f_int(u) − λ f_dead`.
* Tangent: `K_t = dR/du`; the dead-load derivative is zero for this load model.
* Reduced system: `K_ff Δu_f = −R_f`, with `K_ff = P_fᵀ K_t P_f`.
* Prescribed displacement values are reapplied on each trial; embedded free increments have exactly zero prescribed components.
* Support-on-structure reactions are reconstructed from the full, unreduced residual. Force and moment closure were measured in the U and V fixtures.

These sign relations do not apply unchanged to follower or displacement-dependent external loads; those are unsupported.

## Stage U — global assembly evidence

U exercised **31 collected nodes: 31 PASS, 0 FAIL, 0 SKIP, 0 XFAIL, 0 XPASS**. The fixed-target supervisor recorded exact allowlist acceptance, one child per phase, process/job committed-memory limits of 268,435,456 bytes, a 120-second deadline, kill-on-close, no breakaway, and cleanup. Collection used PID 38144, ran for 1.568067 s, and peaked at 53,534,720 committed bytes. RUN used PID 40604, ran for 3.591137 s at the parent and 2.95 s in pytest, and peaked at 87,248,896 committed bytes. Both child PID sets were empty after exit.

The tests covered single and connected-element global force/tangent assembly, shared-DOF scatter, reduced residual/tangent behavior, synthetic force and moment closure, rigid translation and rotation checks, element ordering, and invalid states. The finite-difference steps were `2e-4, 1e-4, 5e-5, 2.5e-5, 1.25e-5`. For the tested free directions, successive centered-difference error ratios were approximately 4 for TET4 and HEX8, supporting a second-order region over those measured steps. A roundoff plateau was not established.

U numerical values and its independent review are preserved in [the U report](wp_e01_uvw_global_assembly_vnv_2026-10-21.md). Its principal limitations remain: the material block is obtained by subtracting the geometric block from the total; some metamorphic checks reuse the same constitutive implementation; synthetic reaction closure is not an independent structural reaction solution; and HEX8 positive determinant is checked at quadrature points only.

## Stage V — Newton prototype and execution

### Implementation

The isolated driver bounds the mesh and load sequence, reduces the free system, checks tangent conditioning, applies Newton updates, reassembles trials, and returns the last accepted state if an increment fails. The accepted state contains only the mesh fingerprint, load factor, and bytes-backed immutable displacement vector. On continuation, it reassembles and checks the accepted state's free residual using the current applied free dead-load norm; callers cannot supply or inflate that scale.

The convergence values remain proposed: absolute residual tolerance `1e-8 N` and relative factor `1e-9` times the current applied free dead-load norm. The driver also bounds load steps, Newton iterations, reduced DOFs, tangent condition estimate, and backtracking reductions. Optional backtracking tests the squared reduced-residual merit `φ = 0.5 ||R_f||²`. For an exact Newton direction under the fixed dead-load convention, `Dφ = −||R_f||²`. It is residual-merit globalization, not total-potential energy decrease and not a production Armijo certificate.

The only mechanical equilibrium fixtures have one free UX DOF. The backtracking rejection/acceptance helper tests use a synthetic scalar residual; the recorded physical load paths accepted full steps and did not exercise a physically rejected Newton trial.

### Collection and containment

Collection observed the exact **16-node** allowlist for `tests/unit/test_wp_e01uvw_newton.py`, with 14 test functions, `NUMERICAL_UNIT` classification, and an accepted collection receipt. Collection PID 33568 exited 0 in 1.546336 s and peaked at 52,555,776 committed bytes.

RUN used PID 37952 once. It exited 1 after 6.891231 s (pytest reported 6.25 s), with 86,376,448 peak committed bytes. Both collection and RUN read back the 256 MiB process and job caps, active-process limit 1, kill-on-close enabled, breakaway disabled, and the 120-second phase deadline. The active PID set was empty after each child exit; cleanup was `VERIFIED_WINDOWS_JOB_CLOSED`. Both stderr files are empty. There was no timeout, cap exceedance, unexpected child, or automatic retry.

### Actual results

| Outcome | Count |
|---|---:|
| PASS | 13 |
| FAIL | 3 |
| SKIP | 0 |
| XFAIL / XPASS | 0 / 0 |
| Collected | 16 |

The passing TET4/HEX8 affine increment tests each converged in 3 corrections at load factors 0.25, 0.5, 0.75, and 1.0. Every recorded physical step accepted `α = 1`; the physical trajectory had no line-search rejection.

| Family | Pre-correction free-residual norms by load factor (N), 3 iterations each | Final residual (N) | Final residual limit (N) | Error from analytic displacement (m) | Force closure (N) | Moment closure (N·m) |
|---|---|---:|---:|---:|---:|---:|
| TET4 | λ=.25: 277.123090511, 7.247400929, 0.005276116; λ=.5: 277.123090514, 7.556354291, 0.005997198; λ=.75: 277.123090515, 7.895096070, 0.006862057; λ=1: 277.123090516, 8.268315516, 0.007909541 | 7.254129741e-9 | 1.118492362e-6 | 5.893896482e-14 | 7.254129741e-9 | 0 |
| HEX8 | λ=.25: 271.536360938, 3.443724825, 0.000569957; λ=.5: 283.457893841, 3.849303979, 0.000731996; λ=.75: 294.860268858, 4.276885189, 0.000929935; λ=1: 305.765161752, 4.727724192, 0.001170814 | 7.162270776e-11 | 1.672738543e-6 | 5.342948306e-16 | 7.185125068e-11 | 1.063442990e-13 |

The listed iteration values are the residual before each correction. The accepted-step post-correction residual is the final residual column for the last increment. The trace also records relative residual, merit before/after, energy before/after, full-step acceptance, and empty rejected-alpha lists. Correction norms and 2-norm tangent condition estimates are stored in the in-memory result object but are not emitted into the persistent test report; those metrics are **NOT_RECORDED** for this RUN. The small-strain test passed its decreasing-error assertion at strains `1e-3` and `5e-4`; the individual error values were not printed, so they are **NOT_RECORDED**.

### Failed nodes and diagnosis

1. `test_final_equilibrium_is_independent_of_admissible_load_partition[tet4]` failed only at the final exact `accepted_state.identity` comparison. Both paths had status `CONVERGED`, each passed the analytic-target error assertion, and their componentwise displacement comparison passed with `rtol=0, atol=2e-10 m`.
2. `test_final_equilibrium_is_independent_of_admissible_load_partition[hex8]` failed at the same exact identity assertion after those same convergence and displacement comparisons passed.
3. `test_initial_state_must_be_in_free_space_equilibrium` did not raise. It sets one dead-load entry to 500 N, then calls `driver.initial_state()` with default `load_factor=0`. The global external load is scaled by that factor, so the test evaluates the zero-load, zero-displacement equilibrium. The source's no-error behavior is consistent with that actual setup.

Accepted-state identity is a SHA-256 over exact mesh fingerprint, load factor, and displacement bytes. Independently converged states can differ by roundoff while satisfying the stated displacement tolerance, so exact identity equality does not test partition-independent equilibrium. The actual displacement difference is **NOT_RECORDED**; only the passing `2e-10 m` componentwise tolerance is established. Exact identity remains appropriate for rollback assertions comparing the same accepted state before and after rejection.

The initial-state test should arrange a genuinely non-equilibrated state under a nonzero load factor; `initial_state(load_factor=1.0)` with the fixture's zero free-node displacement is the narrow candidate, subject to a future fresh collection/run authorization. No source, test, tolerance, or manifest was changed after the failed run. No numerical retry occurred.

### Failure-reporting note

The child executed and the persisted `run_results.json` records 13 PASS and 3 FAIL, but supervisor `summary.json` says `test_execution: NOT_RUN` and overall `EXECUTION_BLOCKED_OR_FAILED`. That status is inaccurate because the supervisor exits its success-validation branch on the nonzero child return code before parsing the child result artifact. The raw run log, run phase result, and `run_results.json` independently show the actual completed run. This is a P2 supervisor reporting defect; no execution evidence was rewritten to hide it.

## Reproducible small-model examples

These two example cards reproduce the passing affine Newton cases in the frozen V test module. They are evidence-backed examples for the current source identity. Reproduction uses the fixed-target supervisor and requires a new Owner execution GO; the old one-run authorization has been consumed.

### TET4 affine uniaxial equilibrium

* Reference coordinates: `(0,0,0)`, `(0.1,0,0)`, `(0,0.1,0)`, `(0,0,0.1)` metres; one TET4 with node order `(0,1,2,3)` and centroid quadrature.
* Material: μ=`2.5e6 Pa`, κ=`6.0e6 Pa`; path-independent Hencky energy as stated above.
* Target: `F = diag(1.08,1,1)`, with all target affine displacements prescribed except node 1 UX. Thus the reference free displacement is `0.008 m`.
* Load: dead UX nodal force at node 1, `F_x = P11 (L²/6)`, with `P11 = (κ + 4μ/3) log(1.08)/1.08`; load factors `.25,.5,.75,1.0`.
* Observed: 3 Newton corrections per increment, final residual `7.254129741e-9 N` against `1.118492362e-6 N`, displacement error `5.893896482e-14 m`, force closure `7.254129741e-9 N`, moment closure zero. The individual support reaction components were not printed.
* Test node: `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[tet4]`.

### HEX8 affine uniaxial equilibrium

* Reference coordinates: the eight corners of `[0,0.1]^3 m` in the sign order recorded in the test fixture; one HEX8 with full 2×2×2 quadrature.
* Material and target deformation: same as TET4; all affine target displacements are prescribed except node 1 UX, whose reference value is `0.008 m`.
* Load: dead UX nodal force at node 1, `F_x = P11 (L²/4)` with the same independently derived `P11`; load factors `.25,.5,.75,1.0`.
* Observed: 3 Newton corrections per increment, final residual `7.162270776e-11 N` against `1.672738543e-6 N`, displacement error `5.342948306e-16 m`, force closure `7.185125068e-11 N`, moment closure `1.063442990e-13 N·m`. The individual support reaction components were not printed.
* Test node: `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[hex8]`.

The reference normal stress is an independent diagonal Hencky expression and the element areas are hand-integrated. Iterative residual and tangent evaluations use the experimental global assembler. Thus the final displacement/force comparison has a genuinely separate affine reference; the Newton Jacobian iteration is still coupled to the same tested assembly/tangent implementation.

## Independent review and findings

A separate read-only reviewer checked the V algorithm/source and the frozen execution results. The reviewer did not run tests or calculations. It found no P0/P1 issue in the fixed-dead-load residual signs, free-DOF reduction, prescribed-value reimposition, accepted-state validation, immutable state data, failure rollback, Job Object containment, or the bounded one-free-DOF affine cases.

Findings retained:

* **P2 — test assertions/setup:** two partition tests equate exact state hashes after asserting tolerant displacement equality; one initial-equilibrium test omits a nonzero load factor.
* **P2 — supervisor status:** summary labels an executed failed run as `NOT_RUN`; the `run_results.json` and raw stdout preserve the actual outcome.
* **P2 — scope:** no physical Newton line-search rejection; no multi-DOF complex loading; no continuation persistence, checkpoint/restart, or crash durability; no follower loads/contact/instability; HEX8 positive determinant only at quadrature points.
* **P2 — measured-output gaps:** correction norms, tangent condition estimates, small-strain errors, and componentwise reactions were not persisted by the test report.
* **P2 — maintainability:** the fixed-target supervisor is a large dedicated campaign module (896 lines). It was kept frozen for this campaign; splitting it should happen only with separately pinned source identities and safety review.

## Exact run commands and scope

The parent invocation was run once from the fixed worktree root:

`C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor`

The supervisor executed collection first, accepted exactly the 16 allowlisted nodes, and then performed one RUN. Its child commands were frozen to the exact module. No direct pytest command, broad discovery, worker, subprocess test helper, public solver, Gmsh, native backend, network access, or production Newton route was used.

## Hash and evidence inventory

### V source identities

| Artifact | SHA-256 |
|---|---|
| V Newton driver | `1a24046913a4544aadba8dbec715f796ef56069f3cdbe813fd871a630950ffb0` |
| V target tests | `c58cfde4aea001d155c1c0d2e5cc42bc99e781b66ca5509c9d90b3635aa16e4f` |
| Safety registry | `e83a839aaad16fbe14b2b169ec1465445a01ed0a92e89e1b565e979d88b114c5` |
| V collection guard | `4595be6f29589bbb1be6c542b32398617abdd827128cc6b08577b8da316d0283` |
| V supervisor | `25d5a503d1e508e002183d8ee2808674434ad836ee953110d8d6b9da7b829c66` |
| U global adapter | `e02baaf346c3b8f853049990c8ac053b5e76ffab92f0a138f167f997cd2503b9` |
| Hencky material | `b87706cecfb036d3a4b31461c83da1b8af0b7aeb7098037e2cf7e65cdf466f50` |
| Hencky tangent | `8ca5dde952eb820a462eb3ebacd329f010d22e5f246fac95863ebee6c467b8b1` |
| WP-E01 job helper | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |
| Static execution manifest | `787b58fe3b9ad0c047aab6aa17264cdcfa67c494a1c0ec9ade55d9b181d76f6a` |
| Runtime execution manifest | `10de21c66d41fc47c70129efa16d7c91bb4d57886bfd3f908cc3a9b162ba233d` |

The runtime manifest contains 34 source pins and was checked by the supervisor against the committed source head `4a3b5323e49dc0276174a4dc40cb31e425a20cae`. The static map contains the exact 14-function/16-node allowlist and the registry binds the target as `NUMERICAL_UNIT`.

### V execution artifacts

All files are under `qualification/0_2_12/wp_e01_uvw_newton_execution_2026-10-21/20261021T172321Z/`.

| Evidence | SHA-256 |
|---|---|
| Collection nodes | `48f6558fff10a99cf6647372e576afe0c8e25f453a8a66ca92cbb9595b55e9fd` |
| Accepted collection receipt | `febd921e4ebb58fc1e5061bdaf1a3f13da52bd37d77d9f16f1a92423b1cb2130` |
| Preflight | `0aca5eb60eacb35400fbf00895da7958a4079ddd9fc89c3f83cc96772fd55b52` |
| Collection phase result | `f71bfa188f6381d581dcbf252d295ae606e5217559a393160cb9cf5da90685bc` |
| Collection stdout | `176b9e179cecf172adb5da42c711b7dd93c3ee0a4ecc721ccce39b36fb301060` |
| Collection stderr (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| RUN phase result | `93e57980e86bf2b4c5561d31d4d112c0638c43d5871a2bd8c9df2afb5a58c9da` |
| RUN stdout | `d4bb64bce9ae5f4ee2e42b0ef8517bc84b718c07bb9613834d97853147bb1e82` |
| RUN stderr (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Structured test results | `e2b4b4a08f20cae9ca0ee1e145def1f8e8e00a96e25c339b0731a4d6e917190b` |
| Evidence hash index | `7e196ade2a61a5b7019e1b04cc0acf0d5fb31546a56ca06b4f28e8419d32990e` |
| Supervisor summary | `eda797bd0cd1b165b189ce430a74b7b0e1f9811f06409a2821c4927512e08214` |

The independent reviewer recomputed all 10 evidence-index entries and found no mismatch. `summary.json` is hashed separately because the evidence index excludes itself and the summary to avoid recursive hashing; its bytes contain the evidence-index digest. The supervisor summary's `test_execution` field is inaccurate as described above; use `run_results.json` and RUN stdout for counts.

## Integration readiness plan

1. Keep this code in `solveur.verification.experimental_hencky_*` until the Owner approves a capability/API design. Do not add material-factory dispatch or route it through public `solve_model`.
2. Obtain a new exact-path GO for the test-only V correction: replace the partition test's exact cross-run identity equality with physical equilibrium/displacement comparisons under the existing frozen tolerance; make the initial-state rejection case use a genuinely nonzero load factor and non-equilibrium free state. Preserve exact identity equality in rollback tests.
3. Correct the supervisor result schema so a completed nonzero pytest run is recorded as an actual failed RUN with its node counts, rather than `NOT_RUN`. Freeze new test, registry, guard, supervisor, and manifest hashes; perform fresh safety review and one new supervised execution only under that GO.
4. Before any integration proposal, extend bounded experimental V&V to more than one free DOF, multiple connected elements, nonuniform loading, support reaction components, free-space tangent directions, and a physical case that actually rejects a Newton full step. Record correction norms and conditioning, rather than leaving those metrics implicit in objects.
5. Assess HEX8 Jacobian admissibility between Gauss points or document a justified element validity policy. Add checkpoint/restart only with a defined persistence contract and independent corruption/recovery tests.
6. Reconcile the branch divergence from the current integration ref. Port only reviewed experimental artifacts to a fresh Owner-approved integration branch after scientific/test review; do not merge the 650-commit campaign history wholesale.
7. Any production route, Armijo certificate, qualification, merge, or release requires separate Owner authorization.

## Final statuses

| Gate | Status |
|---|---|
| HENCKY_MATERIAL_POINT_VNV | PREVIOUS_41_PASS_BOUNDED |
| HENCKY_CONSTITUTIVE_TANGENT_VNV | PREVIOUS_35_PASS_BOUNDED |
| HENCKY_ELEMENT_TANGENT_VNV | PREVIOUS_34_PASS_BOUNDED |
| HENCKY_GLOBAL_ASSEMBLY | VERIFIED_BOUNDED (Stage U, 31/31) |
| HENCKY_CONSTRAINTS_AND_REACTIONS | VERIFIED_BOUNDED for tested supported single-element fixtures |
| HENCKY_REDUCED_TANGENT | VERIFIED_BOUNDED for the tested free-space directions; general Newton behavior remains partial |
| HENCKY_INCREMENTAL_NEWTON | PARTIAL (Stage V, 13/16; three test failures) |
| HENCKY_SMALL_MODEL_EQUILIBRIUM | PARTIAL (two affine cases converged; test suite not fully passing) |
| INDEPENDENT_SCIENTIFIC_VNV | PARTIAL (separate read-only review; not an independent new numerical run) |
| PRODUCTION_NEWTON_ACTIVATION | NOT_AUTHORIZED |
| FINITE_STRAIN_J2 | NOT_IMPLEMENTED |
| GENERAL_SCIENTIFIC_QUALIFICATION | NOT_ACQUIRED |
| AUTHORITATIVE_INTEGRATION | PENDING |
| WP_E01_STATUS | OPEN / EXPERIMENTAL_TARGET / OWNER_REVIEW_REQUIRED |

The exact next Owner decision is a targeted test-harness correction GO, with permission to freeze new hashes and perform one supervised collection plus one conditional RUN of the corrected 16-node V module. No production implementation change is indicated by the current evidence.
