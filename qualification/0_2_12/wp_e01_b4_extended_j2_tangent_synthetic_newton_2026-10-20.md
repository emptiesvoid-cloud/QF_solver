# WP-E01-B4 Extended J2 Tangent V&V and Synthetic Newton/J2 Readiness

**Date:** 2026-10-20  
**Scope:** WP-E01-B J2 tangent evidence and a synthetic Newton/J2 preparation  
**Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`  
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`  
**Verified starting HEAD:** `25f20dd6030fa4a2c47af048872b847b33bec21f` (clean)  
**Origin:** `https://github.com/emptiesvoid-cloud/QF_solver.git`  
**Canonical roadmap:** `qualification/0_2_12/ROADMAP.md`, unchanged; SHA-256 `48021a7773895c354806446ab89e317b968cfee5f2618790f4487fbf11195a6d`.  
**Current working status:** the unchanged reviewed J2 oracle passed 28/28; the Owner-authorized B4 module passed 11/11 on the final run after a test-only exception expectation correction.

## Executive result

The unchanged, hash-registered material-point oracle passed **28/28**. It reproduced the earlier smooth-branch sweep for `H=0` and `H=1500 MPa`, starting from zero incoming plastic history. I recomputed the reported normalized errors with the proposed

\[
C_{ref}=\max(3K,2\mu),\qquad K=175{,}000\ \mathrm{MPa},\quad \mu=80{,}769.230769\ \mathrm{MPa},
\]

so `C_ref=525,000 MPa`. For the six exercised differentiable fixtures, a selected two-consecutive-decade window (`h=1e-6, 1e-7, 1e-8`) meets the **proposed** `tau_T=1e-8` candidate gate. This is evidence only for those initial-state cases; it does not close the requested history, small-multiplier, reverse-yield, or restart domains.

A separate test module covers the missing material-point domains, a synthetic scalar Newton/J2 case, state commit/rollback, a WP10 v2 temporary-file round-trip, typed retry evidence, and refusal of the still-empty production Armijo certificate registry. Under the subsequent exact-path Owner GO, the module passed **11/11** on the final run. The first run exposed only a test expectation mismatch: an unregistered route correctly raises `InputValidationError`, as existing E01-A policy tests specify. The test now asserts that exact fail-closed behavior; production code and frozen scientific criteria are unchanged.

`J2_TANGENT_CONSISTENCY` remains **BLOCKED**. The tangent threshold, norm, and plateau rule remain proposals; no production Armijo certificate, Full Newton J2 validation, native FEM result, or scientific qualification is claimed.

## Baseline and source review

The actual branch and HEAD matched the requested baseline; the initial worktree was clean. The canonical roadmap and WP-E01 A/B Owner records were read. The roadmap retains `WP-E01 = OPEN / EXPERIMENTAL_TARGET`. The Owner-approved D1-D4 principles and E01-A experimental profile are unchanged. No WP-D01/D02 or historical record was edited.

The existing constitutive path was inspected at `src/solveur/materials/solid.py`. It accepts a fixed prior state, evaluates the trial stress, applies the isotropic radial return, returns a trial state and forms a symmetrized algorithmic tangent. The J2 state contains the accumulated equivalent plastic strain, plastic strain, stress, strain, multiplier, and historical `plastic_dissipation`; this work does not change those fields or meanings. The tangent remains not independently qualified. `src/solveur/core/nonlinear/e01a.py` still has an empty `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` mapping and refuses an unregistered route.

No source contradiction was found in the inspected constitutive return map or E01-A certificate guard. No production correction was warranted.

## Independent reference and proposed gate

The independent reference works in symmetric 3-by-3 tensors, with engineering shear strain converted to tensorial shear by a factor of one half and stress shear kept tensorial. It forms

\[
\varepsilon_e^{tr}=\varepsilon-\varepsilon^p_n,\quad
\sigma^{tr}=\lambda\,\mathrm{tr}(\varepsilon_e^{tr})I+2\mu\varepsilon_e^{tr},\quad
q^{tr}=\sqrt{\tfrac32 s^{tr}:s^{tr}},
\]

then solves the scalar consistency equation

\[
q^{tr}-(3\mu+H)\Delta\gamma-(\sigma_{y0}+H\alpha_n)=0
\]

by fixed-count scalar bisection, rather than calling the production return-map or tangent code. It updates `eps_p` in tensor form and reconstructs stress from the elastic law. Every directional perturbation uses the same immutable incoming state. The API coordinate order is `[xx, yy, zz, xy, yz, xz]`; strain shear entries are engineering shear and stress shear entries are tensor stress.

For a unit Euclidean engineering-Voigt direction `p`, the candidate metrics are

\[
D_h\sigma=\frac{\sigma(\varepsilon+h p;z_n)-\sigma(\varepsilon-h p;z_n)}{2h},\qquad
E_{abs}=\|C_{alg}p-D_h\sigma\|_2\;[\mathrm{MPa}],
\]

\[
\eta_T=\frac{E_{abs}}{\max(\|C_{alg}p\|_2,C_{ref}\|p\|_2)},\qquad
\delta_i=\frac{\|D_{h_i}\sigma-D_{h_{i+1}}\sigma\|_2}
{\max(\|D_{h_{i+1}}\sigma\|_2,C_{ref}\|p\|_2)}.
\]

The candidate two-decade rule requires a three-point decade window, all three `eta_T <= tau_T`, both adjacent `delta_i <= tau_T`, and unchanged active-branch signs for both perturbations. The proposed `tau_T=1e-8` remains **PROPOSED**. A yield switch has no required common centered derivative; one-sided branch behavior is recorded separately.

## Recomputed evidence under the proposed scale

The unchanged reviewed module ran with the old reference `C_old=K+2mu=336,538.461538 MPa`. For the existing trace-free normal, pure engineering-shear, and six-component directions, the old normalization floor is active in the selected local window. Replacing that floor with `C_ref=525,000 MPa` therefore recomputes the normalized error and adjacent-change entries by the factor `C_old/C_ref = 0.6410256410`. Values below are rounded from the emitted test data; absolute error is the norm in MPa. All selected cases have `alpha_n=0` and zero incoming stress. The active margins shown are the minimum positive `f_trial` over the full branch-preserving sweep emitted by the test.

| `H` (MPa) | Direction | `min f_trial` (MPa) | `E_abs` at `h=1e-6 / 1e-7 / 1e-8` (MPa) | Recomputed `eta_T` at `h=1e-6 / 1e-7 / 1e-8` | Recomputed `delta` for `1e-6→1e-7 / 1e-7→1e-8` | Candidate window |
|---:|---|---:|---|---|---|---|
| 0 | normal-mixed | 561.2744 | `1.479e-4 / 2.327e-6 / 7.416e-6` | `2.8179e-10 / 4.4321e-12 / 1.4128e-11` | `2.7840e-10 / 1.7090e-11` | PASS, proposed gate |
| 0 | engineering-xy | 751.1150 | `2.001e-4 / 2.190e-6 / 1.048e-5` | `3.8115e-10 / 4.1712e-12 / 1.9955e-11` | `3.7756e-10 / 1.8442e-11` | PASS, proposed gate |
| 0 | six-component | 708.1092 | `2.669e-4 / 2.907e-6 / 2.315e-5` | `5.0833e-10 / 5.5365e-12 / 4.4096e-11` | `5.0647e-10 / 3.9282e-11` | PASS, proposed gate |
| 1500 | normal-mixed | 561.2744 | `1.470e-4 / 2.155e-6 / 5.517e-6` | `2.8000e-10 / 4.1045e-12 / 1.0506e-11` | `2.7737e-10 / 1.2679e-11` | PASS, proposed gate |
| 1500 | engineering-xy | 751.1150 | `1.988e-4 / 2.371e-6 / 1.798e-5` | `3.7872e-10 / 4.5167e-12 / 3.4237e-11` | `3.7436e-10 / 3.5814e-11` | PASS, proposed gate |
| 1500 | six-component | 708.1092 | `2.650e-4 / 3.461e-6 / 2.402e-5` | `5.0474e-10 / 6.5897e-12 / 4.5756e-11` | `5.0006e-10 / 4.2859e-11` | PASS, proposed gate |

Each original sweep covered `h=1e-3, 1e-4, …, 1e-10`; this table reports the declared three-point two-decade window. The largest recomputed error in that window is `5.0833e-10`, and the largest selected adjacent change is `5.0647e-10`. The sweep begins at zero incoming plastic strain and stress. The old test logs error norms and margins but not the full tangent-prediction and finite-difference vectors; the new prepared module now emits those vectors for its selected window.

The complete emitted smooth-plastic norm arrays are preserved below. `E_abs` is directly emitted in MPa. `eta_new` and `delta_new` are the same emitted values renormalized by `C_old/C_ref=0.6410256410`; their display precision is limited by the original test's formatted output. For each array, `h` is ordered `1e-3` through `1e-10`; `delta` is ordered `1e-3→1e-4` through `1e-9→1e-10`.

| `H` (MPa) / direction | `E_abs` (MPa), `h=1e-3…1e-10` | `eta_new`, `h=1e-3…1e-10` | `delta_new`, adjacent decade pairs |
|---|---|---|---|
| 0 / normal-mixed | `1.538e2, 1.480e0, 1.479e-2, 1.479e-4, 2.327e-6, 7.416e-6, 1.110e-4, 1.005e-3` | `2.9295e-4, 2.8192e-6, 2.8179e-8, 2.8179e-10, 4.4321e-12, 1.4128e-11, 2.1141e-10, 1.9154e-9` | `2.9013e-4, 2.7910e-6, 2.7897e-8, 2.7840e-10, 1.7090e-11, 2.1609e-10, 1.7782e-9` |
| 0 / engineering-xy | `1.971e2, 2.000e0, 2.001e-2, 2.001e-4, 2.190e-6, 1.048e-5, 1.280e-4, 1.314e-3` | `3.7551e-4, 3.8103e-6, 3.8109e-8, 3.8115e-10, 4.1712e-12, 1.9955e-11, 2.4378e-10, 2.5019e-9` | `3.7173e-4, 3.7724e-6, 3.7724e-8, 3.7756e-10, 1.8442e-11, 2.2673e-10, 2.3250e-9` |
| 0 / six-component | `2.632e2, 2.667e0, 2.668e-2, 2.669e-4, 2.907e-6, 2.315e-5, 2.977e-4, 1.365e-3` | `5.0128e-4, 5.0808e-6, 5.0814e-8, 5.0833e-10, 5.5365e-12, 4.4096e-11, 5.6699e-10, 2.6000e-9` | `4.9622e-4, 5.0295e-6, 5.0301e-8, 5.0647e-10, 3.9282e-11, 5.2436e-10, 2.0596e-9` |
| 1500 / normal-mixed | `1.528e2, 1.471e0, 1.470e-2, 1.470e-4, 2.155e-6, 5.517e-6, 2.652e-4, 9.559e-4` | `2.9115e-4, 2.8013e-6, 2.8006e-8, 2.8000e-10, 4.1045e-12, 1.0506e-11, 5.0519e-10, 1.8205e-9` | `2.8833e-4, 2.7737e-6, 2.7724e-8, 2.7737e-10, 1.2679e-11, 4.9923e-10, 1.4615e-9` |
| 1500 / engineering-xy | `1.959e2, 1.988e0, 1.988e-2, 1.988e-4, 2.371e-6, 1.798e-5, 1.438e-4, 5.469e-4` | `3.7321e-4, 3.7865e-6, 3.7872e-8, 3.7872e-10, 4.5167e-12, 3.4237e-11, 2.7397e-10, 1.0417e-9` | `3.6942e-4, 3.7487e-6, 3.7494e-8, 3.7436e-10, 3.5814e-11, 2.4936e-10, 1.3090e-9` |
| 1500 / six-component | `2.616e2, 2.651e0, 2.651e-2, 2.650e-4, 3.461e-6, 2.402e-5, 2.233e-4, 1.621e-3` | `4.9821e-4, 5.0494e-6, 5.0500e-8, 5.0474e-10, 6.5897e-12, 4.5756e-11, 4.2532e-10, 3.0878e-9` | `4.9314e-4, 4.9987e-6, 4.9994e-8, 5.0006e-10, 4.2859e-11, 3.8269e-10, 2.9147e-9` |

At each row the candidate criterion is reached on `1e-6,1e-7,1e-8`; coarse steps are above the candidate threshold and the smallest steps show cancellation growth. No tolerance was tuned during this campaign.

The existing one-sided zero-history yield-switch fixture measured engineering-shear slope magnitudes of `400 MPa` on the elastic side and `30.76923077 MPa` on the plastic side. This is a branch switch, not a centered smooth-tangent test. The existing H=0 stress plateau test confirms deviatoric stress remains at yield while plastic strain accumulates, but its previous version did not differentiate that plateau tangent.

### Coverage still absent from executed evidence

The above run does **not** verify any of the requested derivatives from a nonzero incoming plastic state or stress. It does not numerically characterize a small positive plastic multiplier, unloading/reverse-yield tangent, a nonzero-history yield switch, or checkpoint restoration carrying a J2 history. Existing loading/unloading/reloading/reverse material-point tests compare stress/state to the independent reference only; that is not tangent derivative evidence. These items remain `INCOMPLETE`, not inferred from the zero-history sweep.

## Prepared extended test campaign (not run)

New module: `tests/unit/test_wp_e01b_b4_j2_extended_tangent.py`.

| Prepared case | Planned check | Status |
|---|---|---|
| `H=0` and `H>0` smooth plasticity from nonzero history | Fixed incoming `alpha_n>0` and stress; normal, engineering-xy, and mixed direction sweeps; proposed `C_ref` and two-decade gate | Prepared, not run |
| Small positive multiplier | Prior plastic state followed by an increment fixture requiring `0 < Delta_gamma < 1e-4`; verify only branch-preserving perturbation windows | Prepared, not run |
| Perfect plasticity | From nonzero history, increasing `alpha` with unchanged equivalent stress at the plateau, plus tangent sweep | Prepared, not run |
| Unloading and reverse re-yield | Fixed nonzero incoming state; elastic unloading and smooth reverse plastic branch for `H=0` and `H>0` | Prepared, not run |
| Near-yield transition | Nonzero-history elastic-side and plastic-side one-sided derivatives, signed margins, and branch tangent discrepancies; no centered common derivative | Prepared, not run |
| Synthetic scalar Newton/J2 | One generalized material point `epsilon(u)=u e_x`, `R=F-sigma_xx`, `dR/du=-C_xx`; load target manufactured from independent tensor oracle; bounded 25-correction local Newton loop | Prepared, not run |
| Transaction | Production `NonlinearStateTransaction` seam for detached trial, rollback without history accumulation, and one accepted commit | Prepared, not run |
| Checkpoint | Temporary-path-only schema-v2 accepted-state NPZ round-trip with J2 material state and accepted-step metadata | Prepared, not run |
| Retry classification | Typed finite increment evidence accepted by the policy helper; unclassified material failure remains terminal | Prepared, not run |
| Armijo boundary | Assert production certificate registry remains empty and an uncertified synthetic J2 route is refused | Prepared, not run |

The synthetic Newton harness is test-local. It is not `solve_model`, FEM assembly, the E01-A production nonlinear driver, or a positive Armijo route. The manufactured solution is `u*=0.006`; the target force comes from the independent tensor reference at that point. The material state is held fixed during Newton residual/tangent evaluations and is published only after the synthetic residual gate passes. A separate test discards a trial through rollback. The typed-evidence test exercises only the explicit policy helper and does not label an arbitrary J2 failure retryable.

The WP10 v2 test exercises normal `save`/`load` persistence in pytest `tmp_path`; it cannot demonstrate abrupt-crash durability, filesystem atomicity under power loss, or a full production load-path restart. No test activates a route certificate. No executable test path was run from this new module.

## Test safety and chronology

### Newly executed existing path

Before execution, the unchanged module SHA matched its existing `NUMERICAL_UNIT` registry entry. The focused import-time AST closure contained 12 project source files and no Gmsh, `ctypes`, native solver, backend, worker, or child-process path. `tests/conftest.py` calls its Gmsh availability probe only for two unrelated optional Code_Aster mesh modules; this J2 module is not among them. The reviewed test imports only NumPy, pytest, and the direct material-point class; its oracle performs 3-by-3 tensor algebra and fixed-count scalar bisection.

| Execution | Command | Result | Pytest-reported duration |
|---|---|---:|---:|
| Existing J2 material-point/tangent oracle | `python -m pytest -q -s tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | **28 passed, 0 failed, 0 skipped** | `0.74 s` |

The test-runner command took `2.83 s` wall time in the command tool. This run included the eight-step `h=1e-3…1e-10` smooth sweeps, finite-output refusals, fixed-state input checks, one-sided switch slopes, and historical work accumulator comparison. No failure occurred.

The E01-A 39 integrated and 25 policy/collection-safety passes are carried forward from B2/B3 and were **not rerun** here. B4 execution chronology is recorded below.

### New module static safety review

The new module remains explicitly hash-bound as `NUMERICAL_UNIT`; after the test-only correction and diagnostics expansion, its AST parsed successfully and the registry digest was updated without changing the tier. A Ruff executable was unavailable during the final static pass. The test source has no `solve_model`, Gmsh, `ctypes`, subprocess, worker, public solver, or native-backend call. Its only persistent test output is confined by `tmp_path`.

The transitive package/conftest AST closure contained 176 project files because package initializers eagerly import exports. It includes `subprocess` in `solveur.io.manifest` and the `_git_output` helper, but static import-time review found no helper invocation; the selected checkpoint calls do not invoke `git_source_state`. `shutil.which("git")` is used to locate Git at import time, without launching a process. The test calls only `NonlinearCheckpointV2.from_state`, `NpzNonlinearCheckpointStore.save/load`, canonical state encoding, NumPy NPZ I/O, digest validation, and temporary-path file operations. Other package modules contain function-local optional imports for Gmsh, `ctypes`, PETSc, or MPI, but those functions are not reached. `pytest_collection_modifyitems` probes Gmsh only for two unrelated optional mesh modules; this B4 module is not in that set. No backend dispatch, element assembly, worker, subprocess, or native-library initialization was reachable from collection/setup/test/teardown for the selected module.

Owner-authorized execution command:

```text
python -m pytest -q -s tests/unit/test_wp_e01b_b4_j2_extended_tangent.py
```

The module contains 10 test functions and 11 pytest items after hardening parameterization. Work is bounded to eight perturbation sizes, six-component vectors and 3-by-3 tensors, at most 96 scalar bisection iterations per reference call, a 26-evaluation Newton check, one small temporary NPZ round-trip, and no child process. Final pytest duration was 1.45 s (command wall time about 4.1 s).

### Owner-authorized B4 execution and correction

| Cycle | Test-source state | Result | Pytest duration |
|---|---|---:|---:|
| 1 | Original B4 module | 10 passed, 1 failed | 1.55 s |
| 2 | Corrected certificate-refusal assertion | 11 passed, 0 failed, 0 skipped | 1.36 s |
| 3 | Added complete per-case diagnostic emission; no criteria/assertions changed | 11 passed, 0 failed, 0 skipped | 1.45 s |

The sole initial failure was `test_production_j2_armijo_route_remains_uncertified_and_fails_closed`: the test expected `NumericalConvergenceError`, while `derivative_certificate` correctly raises `InputValidationError` for an unregistered/unsupported route. This is consistent with the fail-closed input-validation policy and the existing E01-A integrated test. The correction changed only the test expectation/import and exact SHA-bound registry value; no production source changed. The final raw pytest output, including component vectors, branch margins, and finite-difference diagnostics, is preserved in `wp_e01_b4_extended_tangent_execution_2026-10-20.log`.

Across the final run, 24 branch-preserving tangent sweeps passed the **proposed** `tau_T=1e-8`, `C_ref=max(3K,2mu)=525,000 MPa` gate using the existing coordinate 2-norm and two-consecutive-decade window rule. Maximum selected-window normalized error was `2.952233737e-9`; maximum adjacent finite-difference change was `2.922153148e-9`. The smallest positive selected plastic-branch margin was `1.59573088 MPa` in the small-multiplier case. All 24 detailed state, direction, derivative-vector, perturbation, margin, and error records are in the raw output log. The four yield-switch steps were treated one-sided; no common centered derivative was asserted.

The synthetic Newton/J2 test passed its manufactured target, residual, correction bound, exactly-once commit, and incoming-state isolation assertions. It does not record a per-iteration residual history or exact digest values in its output; therefore a full residual-history/checkpoint-identity report remains incomplete. The checkpoint unit test did assert equality of accepted-state digest before/after WP10 v2 save/load and material-state equality. This is normal temporary-file restart evidence only, not crash durability. No production retry path or Armijo route certificate was exercised.

## Independent read-only review and findings

This review was performed as a second read-only pass by the same primary agent; no separate reviewer was available. It is not described as a blind audit.

- **P0:** none identified in the inspected return map, direct E01-A certificate guard, or prepared test path.
- **P1:** bounded history-dependent, small-multiplier, perfect-plastic, unload/reverse, one-sided transition, and checkpoint cases now pass synthetically. The proposed gate is still limited to these material-point fixtures and does not qualify the tangent for general paths. No production tangent certificate exists.
- **P2:** the candidate reference and plateau rule remain Owner decisions. The Newton/J2 test does not retain a per-iteration residual history or print exact digest values. Checkpoint round-trip is not crash-durability evidence. Direct and corotational historical energy semantics remain route-specific and unchanged.

## Owner decisions and next bounded action

1. Review whether `tau_T=1e-8`, the coordinate 2-norm, `C_ref=max(3K,2mu)`, and a three-point/two-consecutive-decade plateau rule are acceptable candidate criteria. They are **not frozen** by this report; the bounded synthetic evidence makes the proposal ready for Owner review.
2. Keep `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE` until an independent review accepts the criterion and additional authorized evidence supports the intended scope.
3. Any future production E01-A/J2 Armijo certificate is a distinct route-level decision after route-specific derivative evidence; this report does not authorize one.

## Files, hashes, and repository state

| File | SHA-256 / disposition |
|---|---|
| `src/solveur/materials/solid.py` | `7d8223c81999d037900c26bf1a6a2abc9f4b47c0cff597f4be0cf0163e8092aa` — unchanged from B3 |
| `src/solveur/core/nonlinear/e01a.py` | `c0dc0ebfb56fc2da52afca89550adc922e2a52ed04c0b53a2f4a9022cc7bc139` — unchanged from B3; certificate registry remains empty |
| `src/solveur/core/nonlinear/state.py` | `977330c88438174ba29e826825b120a1135a8a04d6046e2b134dca08ab3e3bf2` — read-only inspected transaction path |
| `src/solveur/core/nonlinear/checkpoint.py` | `eb2b320537d45b3afd012e143b248237175d7528f7628fda84e9d64e95885c81` — read-only inspected schema-v2 contract |
| `src/solveur/io/nonlinear_checkpoint.py` | `69983b613df6a4ecc16183d45ad67ec55bafa2857043278cfa4b77026dc19709` — read-only inspected temporary-file store |
| `src/solveur/io/manifest.py` | `eb1d72751fe03e17804c18e9c7bdfa3fe20a9d2e3a11fd6cc88a415e5def5eee` — imported helper defines Git subprocess, not called by the selected checkpoint path |
| `tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | `e7327058ddb5d107b7788dd69d1727794a2f4c22598c03426bb01253257703be` — unchanged and executed |
| `tests/unit/test_wp_e01b_b4_j2_extended_tangent.py` | `3dba88c9d726e9bef8881c7134915e646510b734435536372140d700e7b56ed3` — `NUMERICAL_UNIT`; test-only exception expectation and diagnostic emission updated; final 11/11 |
| `tests/conftest.py` | `69ea1c51d8484a621107c32e51e9b03109bb8c9efaa9c478acad1eebd666944c` — exact test digest updated; tier unchanged |
| `qualification/0_2_12/wp_e01_b4_extended_tangent_execution_2026-10-20.log` | `73f27ada340d004d2d4e745cbeda70d208f0ef8ad3d17a39db25998b947ba8ac` — final run raw output and full component diagnostics |
| `qualification/0_2_12/ROADMAP.md` | Unchanged |

No production source, canonical roadmap, WP-D01/WP-D02 file, historical archive, scientific threshold, or Armijo certificate registry was modified. Final documentation commit and clean HEAD are reported in the delivery message.

## Final status

```text
J2_TANGENT_HISTORY: VERIFIED_BOUNDED (synthetic material-point scope)
J2_SMALL_PLASTIC_MULTIPLIER: VERIFIED_BOUNDED (synthetic material-point scope)
J2_UNLOADING_REVERSE: VERIFIED_BOUNDED (synthetic material-point scope)
J2_TANGENT_GATE: CANDIDATE_FOR_OWNER_FREEZE (all 24 branch-preserving synthetic sweeps pass; tau_T remains proposed)
J2_TANGENT_CONSISTENCY: BLOCKED
NEWTON_J2_SYNTHETIC: INCOMPLETE (assertions pass; no residual history or exact digest values recorded)
CHECKPOINT_SYNTHETIC: PASS (WP10 v2 tmp_path round-trip; crash durability not verified)
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED (registry remains empty)
E01_A_REGRESSION: NOT_RERUN (B2/B3 results carried forward)
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```
