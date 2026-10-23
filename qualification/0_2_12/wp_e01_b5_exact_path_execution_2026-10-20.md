# WP-E01-B5 Exact-Path Offline Execution

- **Date:** 2026-10-20
- **Owner authorization:** B5 Exact-Path Offline Execution GO
- **Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-a-implementation-20261020`
- **Pre-execution HEAD:** `91d1935f172c1d235cf50db62fabae6a2837d25f`
- **Origin:** `https://github.com/emptiesvoid-cloud/QF_solver.git`

This execution record updates the earlier B5 preparation status. The earlier statement that the module was unregistered and unexecuted describes the state before this exact-path Owner GO; it remains an accurate historical record.

## Preflight and scope

The authorized test source matched SHA-256 `795255e89b61782f647f74de480f48ff7f5ff2471c26f80a9967f548afed5c8d`. After the source-path audit, the exact digest was added to `REVIEWED_TEST_TIERS` in `tests/conftest.py` as `NUMERICAL_UNIT`. The post-registration `tests/conftest.py` SHA-256 is `e4a771b2777806595142766aefed7c9612b0c601380dfb3e66064d9178bff954`. The test file itself was not changed.

The module has two test functions and three parameter-expanded cases. It imports the J2 material-point API, nonlinear state transaction, WP10 v2 checkpoint, NumPy, JSON and pytest. File writes are restricted to pytest `tmp_path`. The test does not call model assembly, a public solve, `solve_model`, a nonlinear solver entry, or a worker/process launcher.

The collection hook calls `_gmsh_available()` only for the two paths in `OPTIONAL_MESH_TEST_MODULES` (`test_code_aster_tet10_dynamic.py` and `test_code_aster_tet4_dynamic.py`). B5 is not in that set, so its collection does not invoke Gmsh probing. The reviewed parent-package import chain includes broad I/O and element modules; optional PETSc/SLEPc/MPI and `ctypes` operations are confined to functions not called by the selected test paths. A subprocess helper is imported transitively by the manifest module, but neither the B5 calls nor the checkpoint save/load path invoke it. No Gmsh initialization, native FEM backend, external command, child process, or public solver route is reachable from the selected test bodies. NumPy operations (and package-level SciPy imports) remain within the authorized Python numerical-unit scope.

Preflight source anchors: B5 tests at lines 152 and 325 of `tests/unit/test_wp_e01b_b5_newton_j2_trace.py`; exact tier registration at `tests/conftest.py:231`; collection hook at `tests/conftest.py:264`; conditional Gmsh probe at `tests/conftest.py:294`; `_gmsh_available` definition at `tests/conftest.py:581`. The production E01-A derivative-certificate registry remains empty at `src/solveur/core/nonlinear/e01a.py:38`.

## Authorized command and result

```text
python -m pytest -q -s tests/unit/test_wp_e01b_b5_newton_j2_trace.py
```

Result: **3 passed, 0 failed, 0 skipped**; pytest-reported time `1.27 s`; command wall time `3.744 s`; exit code `0`. This was the only pytest command executed under this GO. No automatic retry or second execution occurred.

## Newton/J2 residual and state traces

Both synthetic material-point cases use the independent tensor-form radial-return oracle, fixed incoming state, engineering-strain/tensor-stress conversion, a predeclared force reference, `F_abs = 0 N`, and `tau_R = 1e-8`. The force residual is `target - internal`, in N. The production material tangent supplies the synthetic full-step Newton updates; this is not an independent solver Jacobian implementation or an Armijo certificate.

| Hardening `H` | Target force and `F_ref` (N) | Residual limit (N) | Residual history (N) | Corrections / evaluations | Final `epsilon_xx` | Final stress `(xx, yy, zz)` (MPa) | Final `alpha = Delta_gamma` | Accepted-state digest after commit |
|---:|---:|---:|---|---:|---:|---|---:|---|
| `0 MPa` | `1216.6666666666665` | `1.2166666666666665e-5` | `1216.6666666666665`, `296.825396825397`, `-2.2737367544323206e-13` | `2 / 3` | `0.006` | `(1216.6666666666667, 966.6666666666666, 966.6666666666666)` | `0.002968253968253968` | `1a6e864e65d50f584a879f9854f63aad11a5b7e33c6de891c7888267fbcc8af7` |
| `1500 MPa` | `1219.6166587789871` | `1.2196166587789871e-5` | `1219.6166587789871`, `296.11610365508284`, `0.0` | `2 / 3` | `0.006` | `(1219.6166587789871, 965.1916706105064, 965.1916706105064)` | `0.002949992112320555` | `1c94abfe53c61404686e24d3e316bc63dab3adacb1cc5885e64e6bce5a5e9bd8` |

In both cases, the accepted incoming material-state digest is `2c6fbdb6f9232ae7b17d05580ec4dc04755ae4a8ad2ef9a16191d354fe0508ed`, and the composite accepted-state digest before the trial is `aa70964da56c54120d4ec219bf5260a8c2c7f4a3112f5ea2a54bab87710e6323`. Each Newton trace has an initial residual evaluation followed by two correction updates and a residual check after the second correction. Each converged trace commits once. The perfect-plastic final yield residual is `-1.1368683772161603e-13 MPa`; the hardening-case final yield residual is `-1.4210854715202004e-13 MPa`.

The independent centered finite-difference diagnostic uses strain step `h = 1e-8` in the axial direction. All reported probes remained on the same elastic or plastic branch. At the initial elastic point, the production tangent and independent derivative are both `282692.3076923077 MPa` in both cases (absolute error `0 MPa`). On the plastic branch:

| `H` | Production `C_xx` (MPa) | Independent `D_h sigma_xx` (MPa) | Absolute discrepancy (MPa) |
|---:|---:|---:|---:|
| `0 MPa`, after correction 1 | `175000.0` | `175000.00001291482` | `1.2914824765175581e-5` |
| `0 MPa`, final evaluation | `175000.0` | `174999.99999017746` | `9.822542779147625e-6` |
| `1500 MPa`, after correction 1 and final evaluation | `175662.56507335542` | `175662.56506142963` | `1.19257892947644e-5` |

These are one-direction diagnostics at one step size, not a plateau study, not a frozen `tau_T` acceptance gate, and not a general tangent validation. The finite-difference code differentiates stress, not the force residual directly. Given the recorded relation `R = F_target - A sigma(u/L)`, the implied residual derivative is `dR/du = -(A/L) d sigma/d epsilon`; the synthetic correction uses the equivalent positive-stiffness solve. That sign relation is visible from the equations but is not separately asserted by a finite-difference residual/Jacobian test. The test does not exercise the production Newton driver or production Armijo path.

## Transaction and WP10 v2 restart trace

The synthetic transaction starts with accepted composite digest `aa70964da56c54120d4ec219bf5260a8c2c7f4a3112f5ea2a54bab87710e6323`. A deliberately rejected trial has digest `50114b41780bf9b53cebf12a524b8cc3b03997ae65d63ddecd651801f6e6fcdb`; rollback returns the accepted digest to the original value and leaves the commit count at `0`. A new synthetic trial has digest `ea31a0e9a44d851fd0ffc1495e6415385bb1aba65deaac8249327cbf86c35d1e`; it commits exactly once. The accepted-state digest after commit and after the WP10 v2 temporary-file round trip is `531143ffb97dc83d578823f70a74322e1eb3d20aab9dfad0bab9e8aa704b9455`; the restored material-state digest is `8483838af754e318498fc260171d5ec5948b3f5b1d7899bb16d77e4957097f9b`.

This is a direct transaction-object and ordinary WP10 v2 accepted-state round-trip check. It does not exercise the E01-A global rejection ledger, actual interruption/restart through the load controller, production typed retry contributors, abrupt process termination, crash durability, or filesystem atomicity.

## Evidence and review findings

The complete emitted JSON traces, including every residual evaluation, stress/plastic state, branch, finite-difference diagnostic, and state digest, are retained in:

* `wp_e01_b5_trace_j2_perfect_plastic_2026-10-20.json`
* `wp_e01_b5_trace_j2_hardening_2026-10-20.json`
* `wp_e01_b5_trace_transaction_restart_2026-10-20.json`

Read-only post-execution review findings:

* The synthetic equilibrium history reaches the independently referenced target with two corrections in both material cases and meets the test's stated force residual inequality.
* Residual values and sign are traced, and the stress tangent is compared to an independent axial centered difference. A direct force-residual/Jacobian finite-difference assertion is absent, so that specific check remains incomplete.
* The incoming accepted material state remains unchanged during Newton trial evaluations. The direct transaction regression confirms rollback identity and one subsequent commit; the WP10 v2 round trip preserves the accepted composite and material-state digests.
* The Newton loop is a test-local scalar update, not the production E01-A driver. The transaction test labels its rejection and retry synthetically; it is not evidence of E01-A cutback or rejection-ledger persistence.
* The finite-difference values provide bounded axial derivative evidence only. B4's prior sweep evidence was not independently rerun in this B5 execution. This result does not freeze `tau_T = 1e-8`, qualify the J2 tangent, establish a production Armijo derivative certificate, or validate Full Newton J2 FEM.
* No separate reviewer was available; the post-execution review was performed read-only by the primary agent.

## Status

```text
B5_TEST_EXECUTION: PASS (3/3)
NEWTON_J2_RESIDUAL_TRACE: VERIFIED_OFFLINE (synthetic trace; production driver not exercised)
NEWTON_J2_SYNTHETIC: VERIFIED_BOUNDED
RESIDUAL_JACOBIAN_ORACLE: INCOMPLETE (sign relation derived from the recorded force definition; no direct residual FD assertion)
J2_TRANSACTIONAL_STATE: VERIFIED_BOUNDED (direct transaction object only)
CHECKPOINT_RESTART: PASS_SYNTHETIC (ordinary WP10 v2 round trip only)
J2_TANGENT_GATE: READY_FOR_OWNER_FREEZE (bounded candidate only; not approved/frozen here)
J2_TANGENT_CANDIDATE_EVIDENCE: VERIFIED_BOUNDED_CANDIDATE (limited axial evidence)
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE (formal gate not promoted)
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED (registry remains empty)
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

The candidate tangent evidence is limited to the reviewed synthetic material-point evidence and prior recorded B4 candidate evidence; it is not a general constitutive or FEM qualification verdict. The formal tangent consistency gate remains blocked. The Owner must separately approve any tangent threshold or broader acceptance criterion.
