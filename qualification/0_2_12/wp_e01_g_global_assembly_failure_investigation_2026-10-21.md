# WP-E01-G — Global Assembly Failure Investigation

Date: 2026-10-21
Branch: `codex/qf-wp-e01-a-implementation-20261020`
Starting HEAD: `5bd79c3e764c89c8f5630a59d5ab66fe5d2cec2a`
Current executable identity: `4e274ec023d72d81967c2d078d825800001e9606`

## Executive result

The two TET4/HEX8 elastic patch failures are confirmed test-reference precision defects. I corrected only the expected-value literal; the material problem and the `2e-11` relative tolerance are unchanged. This correction has **not been executed**.

The four J2 fixed-history tangent cases still fail the proposed directional gate. The historical output identifies the failing direction and assertion class, but its failure dictionaries elide the data needed to identify the underlying scientific cause. No production defect is demonstrated, and it would be unsound to blame either the constitutive tangent or the proposed gate from the preserved output alone.

I prepared a test-only diagnostic update that prints complete per-direction records before assertions, compares the production assembly finite difference with the independent tensor/quadrature reference, checks that the accepted material history remains unchanged, and records production integration-point branch identities. All four directions now complete before the existing gates are evaluated together. The gate values are unchanged and remain **PROPOSED**. No tests were collected or run.

The production tree is unchanged. The next action requires a new exact-path Owner GO bound to the test, registry, supervisor and source hashes in [the execution manifest](wp_e01_g_execution_manifest_2026-10-21.json).

## Baseline, history and static checks

The authoritative worktree was `C:\wpc01-frictionless-public-integration-wt\wp-e01`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, on the requested branch. It was clean at the requested baseline HEAD. All 17 production-source hashes frozen in the F3 manifest still match. Prior D4R element V&V remains **65 PASS** historical evidence and was not rerun. The historical F3 report is unchanged and records 20 collected cases: 14 passed, 6 failed, and zero skipped, xfailed or xpassed. Its captured stdout hash is `C2CC8404829349EEC9ED41913A87B13421CFA380053630FE34553C2AA086EA2B`.

Source-only checks for this change:

* AST parsing succeeded and found the same eight test functions. No pytest collection was performed.
* `git diff --check` passed; Git emitted only its existing LF-to-CRLF working-copy warnings.
* The collection guard is byte-for-byte unchanged.
* The registry classification remains `NUMERICAL_UNIT`; only its descriptive text and exact test digest changed. No deny rule changed.
* The supervisor containment implementation is unchanged; only its expected test and registry hashes changed.
* No production source, public API, fixture, dependency, numerical threshold, material law or test-function count changed.
* No pytest, numerical fixture, solver, native backend, Gmsh or collection command was invoked during WP-E01-G.

## Original six failures

The original executable identity was test SHA-256 `F726B9FA059C3782ED1CE4C6915CE1DAAAA20EDA726D39DA7DDEFA0B4A243528`, registry `080B5527359F09CAB0F4F978AE429A593C7E4CBF8D526928D8DB680407B2973A`, and supervisor `7AEDC5FE3C654AB6C7A1576279A95394F6030F71A3B1A78BC91501A662F33F66`.

| Historical node | Failure location or gate | Source-supported finding |
|---|---|---|
| `test_j2_global_affine_elastic_patch_and_reaction_reference[TET4]` | Expected stress assertion, old line 667 | Failed before element assembly. The expected `sigma_yy` literal was truncated. |
| `test_j2_global_affine_elastic_patch_and_reaction_reference[HEX8]` | Same assertion | Same pre-assembly reference defect; no assembly/reaction evidence from this node. |
| `test_j2_global_residual_tangent_fixed_state_fd[TET4-0.0]` | Proposed `global_window_pass`, old line 819 | Failure occurred in the final `weak-near-translation` direction after three directions printed. The exact failed subcondition and full metrics were elided. |
| `test_j2_global_residual_tangent_fixed_state_fd[TET4-1500000000.0]` | Proposed `global_window_pass`, old line 819 | Same direction and reporting limitation. |
| `test_j2_global_residual_tangent_fixed_state_fd[HEX8-0.0]` | Eligible proposed `local_window_pass`, old line 821 | Failure occurred on the first `free-center-mixed` direction. The global window had passed; plateau was therefore true, and the local comparison was eligible. At least one final-window local error exceeded `1e-5`; exact values were elided. |
| `test_j2_global_residual_tangent_fixed_state_fd[HEX8-1500000000.0]` | Same local gate | Same direction and reporting limitation. |

The error tuples printed by pytest are truncated with ellipses. The following are only their preserved leading absolute-error values, in step order beginning at `h=1e-4`, `3e-5`, `1e-5`, `3e-6`, `1e-6`; the sixth entry and all other omitted tuple contents are `NOT_RECORDED`.

| Case | Preserved absolute-error prefix (N) |
|---|---|
| TET4, `H=0` | `(119039996.61010249, 10689916.722354252, 1187535.8155966953, 106875.83911880669, 11875.043403491…)` |
| TET4, `H=1.5e9 Pa` | `(118293324.18423387, 10622869.795971941, 1180087.6674513833, 106205.51298461636, 11800.560493479…)` |
| HEX8, `H=0` | `(0.0003894176193790447, 0.0021337968559002217, 0.004133532508228219, 0.02213135174712171, 0.0440…)` |
| HEX8, `H=1.5e9 Pa` | `(0.0004074683951646025, 0.0023151472148876515, 0.004219787764411436, 0.02419095413399678, 0.0487…)` |

These prefixes are diagnostics, not sufficient tangent-accuracy evidence. In particular, the increasing HEX8 absolute-error prefix as `h` decreases is compatible with cancellation or a derivative mismatch; the absent normalized errors and vectors prevent distinguishing them.

## Elastic reference correction

The patch uses isotropic linear elasticity with `E=210e9 Pa`, `nu=0.30`, and infinitesimal strain `epsilon=diag(1e-4, 0, 0)`. The independently derived constitutive equation is

```text
sigma = 2 mu epsilon + lambda_Lame tr(epsilon) I
mu = E / (2(1+nu))
lambda_Lame = E nu / ((1+nu)(1-2nu))
```

Thus `sigma_yy=lambda_Lame*1e-4 = 12,115,384.615384615 Pa` at the stored literal precision. The old literal, `12.115384615e6 Pa`, differs from the expression used by the test by approximately `3.846e-4 Pa`; the unchanged relative tolerance allows approximately `2.423e-4 Pa`. This is why both cases failed before calling assembly. The source correction is:

```diff
- assert stress[1, 1] == pytest.approx(12.115384615e6, rel=2.0e-11)
+ assert stress[1, 1] == pytest.approx(12.115384615384615e6, rel=2.0e-11)
```

No assertion, tolerance, constitutive formula, load, mesh or expected physical stress changed. The corrected expected value is an analytical reference; its runtime patch/reaction behavior remains `PREVIOUS_FAIL / NOT_RERUN` until new authorization and execution.

## J2 fixture and case-specific diagnostics

The fixed-history cases use `E=210e9 Pa`, `nu=0.30`, `sigma_y0=250e6 Pa`, and hardening `H=0` or `1.5e9 Pa`. The unit-cube TET4 mesh has 12 elements and 12 centroid material points; the HEX8 mesh has 8 elements and 64 Gauss points. The accepted state is formed by a production preload to `epsilon_x=0.0016`, compared with the independent tensor-return history, then deep-copied and held fixed. The trial field has `epsilon_x=0.003` plus a center-node offset `[2e-5,-1e-5,1.5e-5] m`; its nominal affine axial increment over the preload is `0.0014`, but it is not advanced as a load step. This is a fixed-history derivative fixture, not a multi-increment nonlinear loading test.

Directions are ordered `free-center-mixed`, `full-shared-node-mixed`, `boundary-shared-node`, `weak-near-translation`; each has norm `1 m`. Perturbation parameter `h` is dimensionless, so `delta_u=h p` has displacement units. The steps are `(1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7)`. The proposed reference is `K_ref=max(3K,2mu)*V/L^2` in N/m. The global normalized error is `||Kp-D_h|| / max(||D_h||, K_ref||p||)`; the local error divides by `max(||D_h||, 64 eps K_ref||p||)` and is `NOT_EVALUABLE` when the response is below that floor. The candidate final-three-step window is `(3e-6,1e-6,3e-7)`, with both adjacent normalized changes at most `1e-6` and every in-window global/local error at most `1e-7`/`1e-5`, respectively. All these gates remain **PROPOSED**.

| Element / `H` | Points | Branch/history | Failing direction / observed gate | Exact quantities unavailable in F3 |
|---|---:|---|---|---|
| TET4 / `0 Pa` | 12 | Smooth plastic independent-reference branch; accepted preload `0.0016` frozen; perfect plasticity | Weak near-translation; global window false. Whether plateau failed or an in-window global error exceeded `1e-7` is `NOT_RECORDED`. | `||F_ref||`, failing `Kp`, finite-difference vector, all six normalized errors, plateau changes, local eligibility/error, exact branch-margin minimum, production branch identities. |
| TET4 / `1.5e9 Pa` | 12 | Smooth plastic independent-reference branch; accepted preload frozen; linear isotropic hardening | Same weak direction and global gate. Exact failed subcondition `NOT_RECORDED`. | Same fields as above, including the accumulated accepted `alpha` range. |
| HEX8 / `0 Pa` | 64 | Smooth plastic independent-reference branch; accepted preload frozen; perfect plasticity | First free-center-mixed direction; global window passed, local comparison eligible, local window failed (`>1e-5` for at least one final-three step). | `||F_ref||`, `Kp`, derivative vector, each local/global error, plateau changes and exact minimum branch margin; production branch identities. |
| HEX8 / `1.5e9 Pa` | 64 | Smooth plastic independent-reference branch; accepted preload frozen; linear isotropic hardening | Same first direction and local gate. | Same unavailable fields as HEX8 `H=0`, including accepted `alpha` range. |

The independent-reference branch margins were positive for all perturbations in the failing cases: the old code would otherwise have failed the explicit branch-margin assertion before reaching the tangent gates. Their numerical minimum values were not printed. Production branch identities were not measured in F3. Failure reports do not record analytical Jacobian-vector values, independent derivative vectors, force reference norms or the complete error series; each is explicitly `NOT_RECORDED`, not reconstructed from the abbreviated assertion.

### Immediate failure mechanism versus scientific root cause

| Case | Immediate failure mechanism | Strongest scientific root-cause classification | Confidence |
|---|---|---|---|
| TET4 `H=0` | Candidate global-window composite false on the weak direction. | `INSUFFICIENT_EVIDENCE` | High confidence in this classification; no confidence assignment to competing underlying hypotheses. |
| TET4 `H=1.5e9` | Same. | `INSUFFICIENT_EVIDENCE` | Same. |
| HEX8 `H=0` | Candidate local-window false while global window passed and local gate was eligible. | `INSUFFICIENT_EVIDENCE` | High confidence in this classification; cause may be a local tangent discrepancy, normalization sensitivity or finite-difference resolution. |
| HEX8 `H=1.5e9` | Same. | `INSUFFICIENT_EVIDENCE` | Same. |

The leading TET4 possibilities are weak-mode global scaling, final-window plateau failure, or finite-difference resolution; the old trace does not separate them. The HEX8 local gate excludes the exact null-response exception, but its growing small absolute errors as `h` shrinks make cancellation a plausible hypothesis. A constitutive/assembly tangent defect and an overly restrictive candidate gate remain possible. None is demonstrated. Do not label any of these four as a production defect or a gate defect yet.

## Mathematical and source-level review

The J2 material update in `src/solveur/materials/solid.py:143-256` uses the small-strain associated radial return. The local algorithmic tangent is formed in `_algorithmic_tangent` at lines 276-307 and symmetrized. TET4/HEX8 local force and tangent responses are integrated by `src/solveur/core/assembly/nonlinear.py:232-427`; local forces are accumulated by global DOF index at lines 378-395. The test's assembly oracle reconstructs a separate element-to-global DOF map and scatter-adds local results, while its independent J2 force reference uses tensor-form return mapping and independently constructed quadrature gradients. That reference still shares the production material parameters and the constitutive assumptions; it does not reuse production global assembly scatter.

For the test's fixed dead forces,

```text
R_test(u) = F_int(u) - F_ext
J_test = dR_test/du = dF_int/du = K_int
K_ff delta_u_f = -R_f = F_ext,f - F_int,f
```

The E01-A driver at `src/solveur/core/nonlinear/driver.py:825,980,1090` uses target-minus-internal as its correction right-hand side, solves with the reduced tangent, and adds the returned correction to displacement. This is sign-consistent for fixed external loads. If external force depends on displacement, the complete derivative is `J_R = K_int - dF_ext/du`; the fixed-load evidence does not cover follower-load linearization. E01-A's route certificate mapping in `src/solveur/core/nonlinear/e01a.py:38` remains empty. Its Armijo residual derivative uses the opposite sign of `Kp` for target-minus-internal residual. No production certificate, integrated Newton claim or Newton qualification is established here.

F3's J2 finite differences held the incoming accepted state fixed for the *independent reference* and checked its digest around the base production assembly. F3 did not evaluate production force at every perturbation or record production branch identities. The updated diagnostic now (1) checks the accepted-state digest around each production perturbation, (2) compares `(element, integration point, elastic/plastic branch)` with the base trial branch, (3) reports the production tangent action against both production and independent force finite differences, and (4) reports each direction's vector, norms, stepwise errors, reference margins, history summary and metadata before gate evaluation. It gathers all four directions before asserting the unchanged gates. The branch identity is a discrete elastic/plastic status, not a continuous distance-to-yield margin; the independent reference's margin remains the continuous branch-distance diagnostic.

### Why the existing finite-difference gate cannot yet be accepted or rejected

The centered difference has second-order truncation error on a smooth, fixed branch, while subtraction roundoff and material/assembly accumulation can dominate at small `h`. A final-three plateau can therefore be absent even for a correct tangent, or a stable but biased interval can appear plateaued. The global denominator uses `K_ref||p||`, protecting weak directions; the local denominator deliberately evaluates a stricter response-relative criterion except below its null floor. These are reasonable diagnostics, but their appropriateness depends on the measured response, branch margin and finite-difference plateau. F3 did not preserve the vectors, production derivative, exact in-window errors or production branch state needed to evaluate those conditions.

The revised test keeps the original step sweep and candidate limits. It does not relax or freeze them. The next run is intended to discriminate: production tangent versus production force derivative; production force versus independent reference force; branch switch versus branch-preserved derivative; and numerical resolution versus stable mismatch. A further gate revision should follow those measurements and an independent scientific review, not precede them.

## Independent review and findings

A separate read-only scientific reviewer examined the analytical elastic reference, the revised diagnostics, branch-identity checks, the F3 failure evidence and the competing J2 hypotheses. This was an independent review of the source and preserved evidence, not an independent numerical execution. The reviewer agreed that the elastic literal correction is justified, the production boolean branch identity is useful but is not a yield-margin measure, and F3's truncated output does not support assigning a unique J2 tangent root cause. No J2 threshold was endorsed or frozen.

* **P0:** None found in the reviewed source-only change.
* **P1:** Four J2 tangent cases remain unresolved under candidate gates. Preserve them as failures. Do not claim `J2_TANGENT_CONSISTENCY` or activate an Armijo route certificate.
* **P2:** The elastic expected-value precision defect is corrected in source but not rerun. Diagnostic additions have not been executed; only AST and hash checks are available.

## Updated executable identity and next-run safety manifest

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01e_global_assembly_vnv.py` | `8FA46D1D2FF402C72E0D85851EB57307173FBA3D37A39567E3678608FE818296` |
| `tests/conftest.py` | `CC54ADD4E7521762ECAD97E7CF0B19579AB898FE79CFF25319D889BEC2F081A2` |
| `experiments/wp_e01f_global_assembly_supervisor.py` | `06FE16E642CA8FEFE850B92DD41F30128C84A96712E1CBA954272AE23EFAE79B` |
| `experiments/wp_e01f_collection_guard.py` (unchanged) | `324D49F2542FAF2FBDD9B31DA2188EAB6FDEA5F512CC85A15FE26A7D42B36E24` |

The module remains the same 8 test functions and statically parameterizes to 20 cases. The new identity was **not collected**. The manifest records all 20 node IDs from the previous guarded collection only as expected inventory, not as a claim that they were observed for the new hash. The unchanged guard checks exact module prefix, count, functions, fixtures, markers and the collected node record before pytest enters its test loop.

For a future separate Owner GO, the fixed parent invocation is:

```text
C:\Python313\python.exe -m experiments.wp_e01f_global_assembly_supervisor
```

It accepts no arguments and internally launches only the fixed test module as one `shell=False` child using `C:\Python313\python.exe -S -m pytest`, the hash-bound collection guard, one BLAS thread, one active process, 256 MiB job and process committed-memory limits, a 120-second phase deadline, kill-on-close, no breakaway and no automatic retry. Collection occurs inside this supervised child and aborts before test bodies if the inventory differs. Do not invoke the child command directly or bypass the supervisor. The supervisor and all unchanged production-source hashes are bound in the manifest. These resource settings have not been exercised for this new identity.

Manifest SHA-256: `0F609B4B51AE81A8FD2F2BD4233510D9002AD0A46404279D6532D19AE8E31E91`.

The executable/test identity is preserved by commits `9e7f7f1025f446c50b53ca1697c09b2dd24e8496` (diagnostic and hash binding update) and `4e274ec023d72d81967c2d078d825800001e9606` (collect all direction diagnostics before gate evaluation). The report and manifest are committed together as documentation-only artifacts; their hashes are reported in the final delivery.

## Final status

| Required status | Result |
|---|---|
| `ELASTIC_PATCH_REFERENCE` | `CORRECTED_BY_SOURCE` |
| `ELASTIC_PATCH_RUNTIME_VNV` | `PREVIOUS_FAIL / NOT_RERUN` |
| `J2_TET4_GLOBAL_TANGENT` | `FAIL_UNDER_PROPOSED_GATE / UNDERLYING_ROOT_CAUSE=INSUFFICIENT_EVIDENCE` |
| `J2_HEX8_LOCAL_TANGENT` | `FAIL_UNDER_PROPOSED_GATE / UNDERLYING_ROOT_CAUSE=INSUFFICIENT_EVIDENCE` |
| `J2_TANGENT_SCIENTIFIC_GATE` | `NOT_APPROVED` |
| `STVK_GLOBAL_TANGENT` | `PREVIOUS_PASS_BOUNDED` |
| `WP10_SCHEMA_V2_ROUNDTRIP` | `PREVIOUS_PASS_BOUNDED` |
| `GLOBAL_ASSEMBLY_VNV` | `PARTIAL` — historical 14 pass, 6 fail; corrected identity not run |
| `INCREMENTAL_NEWTON_FEM` | `NOT_RUN` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Exact next Owner decision

Authorize one supervised collection-and-execution of `tests/unit/test_wp_e01e_global_assembly_vnv.py` using only the parent supervisor command above and the exact current test, registry, supervisor, collection-guard and unchanged production-source hashes recorded in the manifest. The guarded run will recheck the full 20-case inventory before entering tests, then emit complete per-direction production/reference/Jacobian diagnostics. It is an offline global assembly numerical test only; it is not a production nonlinear solve, native FEM V&V, J2 tangent scientific freeze or qualification.

The corrected expected stress and the four J2 cases must retain all observed outcomes. Any future scientific acceptance-gate change requires separate Owner review after the full diagnostic record and independent analysis are available.
