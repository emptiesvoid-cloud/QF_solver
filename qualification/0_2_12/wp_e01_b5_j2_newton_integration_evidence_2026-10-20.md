# WP-E01-B5 J2 Tangent and Synthetic Newton/J2 Evidence

**Date:** 2026-10-20
**Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`
**Verified starting HEAD:** `d12c5826a610e90a3ee90f206db05aef552a3d8e` (clean)
**Origin:** `https://github.com/emptiesvoid-cloud/QF_solver.git`
**Canonical roadmap:** `qualification/0_2_12/ROADMAP.md` (read-only; SHA-256 `48021a7773895c354806446ab89e317b968cfee5f2618790f4487fbf11195a6d`)

## Scope and result

This B5 pass reviewed the bounded small-strain J2 tangent evidence, reran only the unchanged B4 test module already authorized at its exact path and digest, and prepared a richer synthetic Newton/J2 trace module. The new B5 test path is statically reviewed, intentionally unregistered, and **has not been executed**; the existing fail-closed classifier will keep it `UNKNOWN` until an exact-path Owner GO authorizes registry classification and execution. No production source, scientific threshold, WP10 v2 behavior, Armijo certificate registry, canonical roadmap, WP-D01/WP-D02 file, or qualification status was changed.

The 24 B4 branch-preserving directional sweeps support a **bounded candidate** for Owner review. They do not support a general tangent qualification. The proposed `tau_T = 1e-8` remains unapproved. The existing normalized metric is an elastic-stiffness-relative metric; it does not promise per-direction relative accuracy when `||C_alg p||` is small. That limitation is explicit below and must remain attached to any Owner freeze decision.

## Candidate tangent contract for Owner decision

For each differentiable branch, keep the incoming constitutive state `z_n` fixed for the base stress, both finite-difference probes, and the production tangent evaluation. Use component order `[xx, yy, zz, xy, yz, xz]`, engineering shear strain `[epsilon_xx, epsilon_yy, epsilon_zz, gamma_xy, gamma_yz, gamma_xz]`, and physical tensor shear stress. The current test directions are normalized in the ordinary Euclidean norm of this engineering-Voigt coordinate vector. That is reproducible for this API but is coordinate-based, not a rotation-invariant tensor norm.

For unit direction `p` and dimensionless strain step `h`, define the independent centered derivative

```text
D_h sigma = [sigma(epsilon + h p; z_n) - sigma(epsilon - h p; z_n)] / (2 h)
E_abs     = || C_alg p - D_h sigma ||_2                    [MPa]
C_ref     = max(3 K, 2 mu)                                 [MPa]
eta_T     = E_abs / max(||C_alg p||_2, C_ref ||p||_2)
delta_i   = ||D_hi sigma - D_hi+1 sigma||_2
            / max(||D_hi+1 sigma||_2, C_ref ||p||_2)
```

The proposed acceptance target is `tau_T = 1e-8` (**PROPOSED**, not frozen). A candidate plateau is three adjacent decade steps with branch signs unchanged for both probes; every `eta_T` and both adjacent `delta_i` values in that window must meet the proposed threshold. Yield-switch points are nonsmooth and are checked one-sided; no common centered derivative is asserted. Record `E_abs` in MPa, all derivative vectors, the trial-yield margins, and incoming-state digest alongside normalized metrics.

### Scale review and limitation

For the B4 material (`E = 210,000 MPa`, `nu = 0.3`), `K = 175,000 MPa`, `mu = 80,769.230769 MPa`, and therefore the proposed `C_ref` is `525,000 MPa`. The B4 retained report and output show 24 branch-preserving sweeps with a maximum selected-window `eta_T = 2.952233737e-9` and maximum adjacent `delta_i = 2.922153148e-9`. The B4 window covers two consecutive decades chosen from `h = 1e-3 ... 1e-10`; the most difficult selected plastic margin is reported as `1.59573088 MPa`. Perfect plasticity, isotropic hardening, small positive plastic multiplier, unloading, reverse re-yield, normal, engineering-shear, mixed directions, and a separate one-sided yield-switch study are included.

The `C_ref` floor makes this a global stiffness-relative error, not a local relative error in every direction. For example, the retained B4 shear-direction sample has `E_abs = 1.1583e-3 MPa`, a tangent response about `3.6991e4 MPa`, and a `C_ref`-normalized error about `2.2063e-9`; the corresponding local ratio is about `3.1e-8`. Thus the reported candidate target can pass while a coarse-step local ratio is several times larger. The absolute discrepancy is small on this fixture, and the finer plateau points decrease it further, but the normalization alone cannot guarantee a local relative bound near a weak or nearly-null direction.

**Recommendation:** retain the exact tested stiffness-relative metric only if the Owner intends that limited claim. Preserve absolute errors and local directional ratios as mandatory reported diagnostics. Before a broader tangent claim, add near-null/weak-response directions and decide whether a separately scaled local-relative or case-declared absolute-error gate is required. Do not change `tau_T` to make the current evidence pass. The existing sweeps do not test general rotation covariance or all six independent tangent columns.

The smaller earlier scale `K + 2 mu = 336,538.461538 MPa` would increase normalized errors by about `1.56` when the floor is active. The reported maximum would still be below `1e-8`, but this scale sensitivity reinforces that the normalization definition must be part of the Owner-approved claim, not an implementation detail.

## Source and contract review

| Area | Source evidence | Finding |
|---|---|---|
| J2 return map and component convention | `src/solveur/materials/solid.py`, `VonMisesElastoplasticMaterial` and `stress_tangent_state` (lines 103–255) | Small-strain isotropic elasticity, fixed incoming plastic state, radial return, plastic strain and accumulated equivalent strain are directly inspectable. Existing output `plastic_dissipation` is computed by endpoint trapezoidal stress work at lines 220–225; this review leaves its historical name and values unchanged and does not call it proven thermodynamic dissipation. |
| Algorithmic tangent | `src/solveur/materials/solid.py`, `_algorithmic_tangent` (around lines 269–333) | The returned tangent is symmetrized in engineering-Voigt form. B4 compares the API-returned tangent to an independently implemented tensor-form, scalar-bisection stress oracle. This supports only the exercised directions and branches; it does not qualify Full Newton. |
| State transaction | `src/solveur/core/nonlinear/state.py`, `begin_trial`, `commit`, `rollback`, and `deterministic_state_digest` (lines 190–262) | Trial construction is detached; commit checks accepted-state integrity and publishes a detached composite; rollback discards trial after integrity checking. The B4 tests exercise these direct state-object behaviors, not all production material/contact contributors. |
| WP10 v2 checkpoint | `src/solveur/core/nonlinear/checkpoint.py`, `NonlinearCheckpointV2.from_state`; `src/solveur/io/nonlinear_checkpoint.py`, `save`/`load` | B4 performs a `tmp_path` accepted-state round-trip and checks digest/material equality. This is ordinary synthetic restart evidence, not crash durability or filesystem atomicity. The new trace test uses the existing v2 accepted-state form and introduces no checkpoint fields. |
| E01-A rejection metadata | `src/solveur/core/nonlinear/e01a.py` and `load_control.py` | E01-A uses its existing versioned metadata/ledger helpers over accepted WP10 state. B5 did not execute the E01-A ledger suites, did not add a typed-evidence subrecord, and did not claim global-rejection persistence from the B4 J2 checkpoint round-trip. |
| Armijo route registry | `src/solveur/core/nonlinear/e01a.py`, `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` and `derivative_certificate` (lines 38, 455–462) | Registry remains empty; B4’s fail-closed check passes. No synthetic tangent observation registers a production certificate. |

No source/contract contradiction was found in these inspected paths. A symmetrized matrix can satisfy symmetry by construction; symmetry alone is not independent tangent evidence. The directional derivative comparisons, not symmetry, carry the bounded evidence.

## Executed evidence (carried-forward results are separated)

The B4 file and its registry entry were unchanged at the time of this one rerun. Their digests were:

| Item | SHA-256 at execution |
|---|---|
| `tests/unit/test_wp_e01b_b4_j2_extended_tangent.py` | `3dba88c9d726e9bef8881c7134915e646510b734435536372140d700e7b56ed3` |
| `tests/conftest.py` | `69ea1c51d8484a621107c32e51e9b03109bb8c9efaa9c478acad1eebd666944c` |

Command:

```text
python -m pytest -q -s tests/unit/test_wp_e01b_b4_j2_extended_tangent.py
```

Result: **11 passed, 0 failed, 0 skipped**; pytest reported `1.32 s`; command wall time was `3.738 s`; exit code `0`. It re-exercised the 24 branch-preserving tangent sweeps, one-sided switch diagnostic, synthetic scalar Newton assertion, transaction rollback, WP10 v2 accepted-state round-trip, and empty Armijo-certificate refusal. The module's scalar Newton test checks its manufactured endpoint, convergence threshold, bounded corrections and exactly-once commit, but still does not emit per-correction residual history. This rerun did not execute any public solver, FEM, Gmsh, backend, or subprocess path.

These previous results are **carried forward, not rerun in B5**: 39 E01-A integrated tests; 25 policy/collection-safety tests; and 28 J2 constitutive-oracle tests. They are not counted as B5 test execution. The prior B4 test log remains the complete retained vector-level sweep output at SHA-256 `73f27ada340d004d2d4e745cbeda70d208f0ef8ad3d17a39db25998b947ba8ac`.

## Prepared B5 trace test — NOT RUN

`tests/unit/test_wp_e01b_b5_newton_j2_trace.py` is a new exact-path test candidate. It has three parameter-expanded items: two material hardening cases for the synthetic Newton/J2 trace and one synthetic rollback/retry/WP10 v2 accepted-state round-trip. Each JSON trace includes the test fixture's load/increment/attempt identity, correction count and residual evaluation, signed and normed residual with units and predeclared scale, tangent/Jacobian status, step length and explicit `NOT_ARMIJO` label, stress and active branch/yield margins, plastic strain, accumulated equivalent plastic strain, plastic multiplier, incoming/accepted/trial/material digests, commit or rollback count, termination, and restart identity where applicable. The historical `plastic_dissipation` field is neither reinterpreted nor used as a V&V pass quantity.

The first test uses a one-point uniaxial constitutive coupling with `A = 1e-6 m^2` and `L = 1e-3 m`, so `F_int = sigma_xx * 1e6 Pa/MPa * A` is in N and `K_t = C_xx * 1e6 * A/L` is in N/m. The residual is `F_target - F_int`, `F_ref = abs(F_target)` is fixed before iteration, and `F_abs = 0 N`. Its independent test-local reference uses tensor stress/strain conversion and fixed-count scalar bisection. The production material tangent is used only for synthetic full-step Newton corrections and is explicitly marked unqualified; a centered derivative discrepancy is recorded only when both probes remain on the same branch. This is not a public E01-A force-route test or an Armijo certificate.

The second test creates one synthetic rejected trial, verifies rollback to the accepted digest, starts a second synthetic trial, commits once, then checks accepted-state digest and material state after the existing WP10 v2 temporary-file round-trip. It explicitly does **not** claim E01-A ledger persistence, actual process interruption, crash durability, or production retry coverage. No new WP10/E01-A checkpoint field or historical `plastic_dissipation` interpretation is introduced.

The new module is deliberately **not** registered in `tests/conftest.py`. Its SHA-256 is supplied below so a future exact-path Owner GO can explicitly authorize its `NUMERICAL_UNIT` classification and execution. Until then, the existing fail-closed classifier treats this unlisted local solver import as `UNKNOWN`; the B5 test module and `conftest.py` were not used for a pytest run.

## Separate read-only review and findings

I performed a separate read-only pass as the same primary agent; no separate independent reviewer was available. Findings:

- **P0:** None found in inspected source or the exact B4 test path.
- **P1:** The global `C_ref` normalization supports a stiffness-relative bound, not a local relative guarantee for weak directions. Owner approval must preserve this limited interpretation or add a separate directional/absolute criterion before broader use. The production J2 tangent remains blocked for route certification.
- **P1:** The new Newton trace test has not been executed; it is prepared for exact-path Owner review. Existing E01-A retry-ledger and full load-control tests were not rerun in B5.
- **P2:** Existing WP10 v2 round-trip evidence is not crash-durability evidence. The B4 Newton assertion lacks per-iteration diagnostics; the new trace candidate addresses the reporting gap but cannot be evidence until separately authorized and run.

## Status

```text
J2_TANGENT_GATE: READY_FOR_OWNER_FREEZE
J2_TANGENT_CONSISTENCY: VERIFIED_BOUNDED_CANDIDATE
NEWTON_J2_RESIDUAL_TRACE: PREPARED
NEWTON_J2_SYNTHETIC: INCOMPLETE
J2_TRANSACTIONAL_STATE: VERIFIED_BOUNDED (direct synthetic state-object behavior only)
CHECKPOINT_RESTART: PASS_SYNTHETIC (accepted WP10 v2 state round-trip only)
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED (registry empty)
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

`READY_FOR_OWNER_FREEZE` means the bounded candidate criteria are packaged for an Owner decision; it does not mean the threshold or criterion has been approved. `VERIFIED_BOUNDED_CANDIDATE` describes the executed synthetic material-point branches only and must not be read as general tangent consistency or scientific qualification.

## Remaining Owner decisions and next authorization

1. Decide whether `tau_T = 1e-8`, the Euclidean engineering-Voigt direction norm, `C_ref = max(3K,2mu)`, and the three-point/two-decade plateau are acceptable as a **global stiffness-relative** candidate gate.
2. Decide whether weak-direction local relative accuracy needs an additional gate or remains a reported diagnostic with explicit scope limitation.
3. If desired, issue an exact-path test GO for the prepared module using the digest below. No B5 test execution is authorized by this report.
4. Keep `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; no Armijo certificate or Full Newton validation claim is authorized.

## Post-GO execution addendum (2026-10-20)

After this preparation record was written, the Owner issued a separate exact-path B5 execution GO. The hash-bound B5 module was reviewed, registered as `NUMERICAL_UNIT`, and run once: 3 passed, 0 failed, 0 skipped. The full residual, constitutive, transaction, and WP10 v2 round-trip traces are recorded in [the exact-path execution report](wp_e01_b5_exact_path_execution_2026-10-20.md) and its three JSON evidence files. This later bounded test does not alter the limitations recorded above: the synthetic route is not FEM or production-load-control evidence; tangent acceptance criteria remain unapproved; no production Armijo certificate was activated; `J2_TANGENT_CONSISTENCY` is not promoted; and WP-E01 remains open.

## Files and hashes

| File | SHA-256 / status |
|---|---|
| `tests/unit/test_wp_e01b_b5_newton_j2_trace.py` | `795255e89b61782f647f74de480f48ff7f5ff2471c26f80a9967f548afed5c8d` — prepared, **NOT RUN** |
| `tests/conftest.py` | `69ea1c51d8484a621107c32e51e9b03109bb8c9efaa9c478acad1eebd666944c` — unchanged; new path remains unregistered |
| `tests/unit/test_wp_e01b_b4_j2_extended_tangent.py` | `3dba88c9d726e9bef8881c7134915e646510b734435536372140d700e7b56ed3` — unchanged; 11/11 B5 rerun |
| `qualification/0_2_12/wp_e01_b4_extended_tangent_execution_2026-10-20.log` | `73f27ada340d004d2d4e745cbeda70d208f0ef8ad3d17a39db25998b947ba8ac` — retained prior full diagnostic output |
| `qualification/0_2_12/ROADMAP.md` | `48021a7773895c354806446ab89e317b968cfee5f2618790f4487fbf11195a6d` — unchanged |
