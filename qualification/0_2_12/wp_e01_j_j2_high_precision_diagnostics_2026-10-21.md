# WP-E01-J — Supervised high-precision J2 tangent diagnostics

Date: 2026-10-21
Branch: `codex/qf-wp-e01-a-implementation-20261020`
Starting source HEAD: `a53d07b6b3154cd4f99a57d02a5aae52572c6c88`

## Executive result

The exact 12-case diagnostic module was collected and executed once under the frozen Windows Job Object supervisor. Collection matched all 12 authorized nodes. The run recorded **8 passed, 4 failed**, with no skips, xfails, or xpasses. All six fixed-history Decimal derivative diagnostics and both weak-vector characterization cases completed. The four failures are the four exact-translation controls; each stopped before evaluating force or tangent invariance because the test created a new `DofManager` while reusing an assembly plan bound to the original manager. They are test-harness failures, not numerical translation results.

The TET4 free-center mixed-direction derivative errors show the predicted centered-difference `O(h^2)` trend through `h=3e-7`; the high-precision sequence then reaches an absolute comparison floor of about `2.30e-5` to `3.35e-5 N`, less than `6.4e-17` under the declared global stiffness scale. This supports fixed-history tangent agreement for those two tested directions. It does not validate plastic history evolution or freeze a tangent gate.

For the four near-translation vectors, the Decimal force derivatives are stable over the full step sweep, but the production binary64 tangent action differs locally by 6.74–11.03%. These directions are almost rigid translations and are not admissible in the constrained Newton space. Since the exact rigid-translation controls did not reach their assertions, the local mismatch cannot be assigned uniquely to constitutive tangent error versus cancellation/conditioning in the assembled binary64 matrix. `J2_TANGENT_CONSISTENCY` remains blocked.

No production code, tests, acceptance thresholds, frozen executable identities, or scientific status were changed. The previous WP-E01-H 16/4 outcome and D4R 65-pass evidence remain historical and unchanged.

## Identity, safety, and execution evidence

The worktree was `C:\wpc01-frictionless-public-integration-wt\wp-e01`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch as above, and clean at the required starting HEAD. The frozen I manifest hash matched. All **29** manifest source identities and **32** effective supervisor pins matched the current files immediately before invocation; the archived preflight lists all 32 verified paths.

| Frozen item | SHA-256 |
|---|---|
| I execution manifest | `9884A3846B2D8929371DABC1E6A7D7E1BB489CCB094D62FDCADE3D193133141C` |
| Diagnostic module `tests/unit/test_wp_e01i_j2_precision_diagnostics.py` | `59DBAF1F84E518C2F10FC573ED973EE22187399671B7045F22C3F73B349F4C95` |
| Safety registry `tests/conftest.py` | `A3220FD8716FC86E316EF0577E7E3E8DB789C850B0201E63EEF1ED2CD28F0618` |
| Collection guard | `722D30D59C710D93DAD82150C40DBF6EB6FF2CCCBCF6BB27179A3D3F24F718B4` |
| Diagnostic supervisor | `74A6043726702CEF1AEC888FC40D5BE57B1487DE2DFF4B7FAC15193C56EB450C` |

The module remained hash-bound as `NUMERICAL_UNIT`. The approved parent command was invoked once:

```text
C:/Python313/python.exe -m experiments.wp_e01i_j2_diagnostic_supervisor
```

The supervisor launched one fixed pytest child (PID 2012), with no retry. Runtime evidence records one active process, process and job committed-memory caps of `268435456` bytes each, parent deadline 120 seconds, kill-on-close enabled, breakaway disabled, and cleanup `VERIFIED_WINDOWS_JOB_CLOSED`. Peak process and job committed memory were both `107085824` bytes (102.1 MiB). Supervisor elapsed time was 3.5821 s; pytest reported 2.87 s. Timeout was false. `stderr.log` was empty. The supervisor's `FAILED_CLOSED` status reflects pytest's nonzero exit after four assertion-path exceptions; it does not indicate a resource-limit failure.

The guard wrote and validated exactly 12 authorized nodes before entering the test loop. All test bodies then ran. There was no native FEM/Gmsh, public solver, worker, child test subprocess, or network path in the reviewed executable scope.

### Actual collected nodes and outcomes

Six derivative diagnostic nodes passed their branch/state assertions:

```text
test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-perfect-free-center-mixed]
test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-hardening-free-center-mixed]
test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-perfect-weak]
test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-hardening-weak]
test_j2_high_precision_fixed_history_tangent_diagnostic[hex8-perfect-weak]
test_j2_high_precision_fixed_history_tangent_diagnostic[hex8-hardening-weak]
```

Four translation controls failed before the physical invariance comparisons:

```text
test_j2_exact_translation_control_on_raw_internal_operator[tet4-perfect]
test_j2_exact_translation_control_on_raw_internal_operator[tet4-hardening]
test_j2_exact_translation_control_on_raw_internal_operator[hex8-perfect]
test_j2_exact_translation_control_on_raw_internal_operator[hex8-hardening]
```

The two weak-vector characterization nodes passed:

```text
test_historical_weak_direction_is_approximate_and_not_constraint_admissible[TET4]
test_historical_weak_direction_is_approximate_and_not_constraint_admissible[HEX8]
```

Pytest result: `8 passed, 4 failed in 2.87s`; child exit code `1`. The full node list, pytest output, phase record, preflight and supervisor summary are preserved under `qualification/0_2_12/wp_e01_j_execution_2026-10-21/`.

## High-precision oracle assessment

The fixed-history oracle runs at 80-digit Decimal precision. It reconstructs each stored binary64 model, material, direction, and accepted-state input using `Decimal.from_float`; computes the shape gradients, TET4/HEX8 quadrature, strain, isotropic J2 return mapping, stress integration, and global force scatter in Decimal; and holds the accepted incoming plastic history fixed for every `u ± h p` evaluation. Its force path does not call the production constitutive stress routine, element force routine, quadrature routine, or global scatter routine. It does share the model's parsed geometry/connectivity, material parameters, and production-generated accepted state. The production tangent under comparison is the assembled binary64 matrix.

At base state, all points were plastic and production/Decimal branch identities matched: 12 points for the 12-element TET4 mesh and 64 points for the 8-element HEX8 mesh. All tested perturbations preserved those branches, with minimum positive yield margin across the sweep about 208.822 MPa for the two TET4 mixed cases and at least 219.647 MPa for weak cases. Accepted-state digests were unchanged. Production/Decimal base-force norm differences were `5.66e-8` and `9.25e-8 N` for TET4, and `2.33e-7` and `2.46e-7 N` for HEX8.

This is strong independent evidence for the derivative conditional on the supplied accepted history. It does not validate how that history was produced, nor does it establish a production FEM solve or Armijo certificate.

### TET4 free-center mixed directions

For a smooth force map and fixed branch,

\[
D_h=\frac{F(u+hp)-F(u-hp)}{2h}
=J(u)p+\frac{h^2}{6}D^3F(u)[p,p,p]+O(h^4).
\]

The measured global errors were:

| Hardening (Pa) | `h=3e-6` | `h=1e-6` | `h=3e-7` | Ratios on refinement |
|---:|---:|---:|---:|---|
| 0 | `2.03573028e-7` | `2.26191810e-8` | `2.03572582e-9` | `9.0000`, `11.1111` |
| `1.5e9` | `2.02296232e-7` | `2.24773151e-8` | `2.02295791e-9` | `9.0000`, `11.1111` |

These ratios match the squared step ratios and support an `O(h^2)` truncation-dominated range. At `h=1e-10`, the global comparisons are `2.20e-16` and `2.36e-16`; by `h=1e-12`, they settle at `6.37e-17` and `4.37e-17`. Corresponding absolute errors plateau at `3.3457e-5 N` and `2.2952e-5 N`. This floor is against the rounded binary64 assembled tangent, not a Decimal subtraction-noise floor. The binary64 tangent entries themselves have finite precision; the globally scaled action is about `3.96e11`–`3.97e11 N`.

Richardson extrapolation was derived from adjacent Decimal force-difference vectors using

\[
D_R(h,r)=\frac{r^2D_{h/r}-D_h}{r^2-1},\qquad r=h/(h/r).
\]

For pairs `(3e-6,1e-6)`, Richardson errors fell to `4.2758e-2 N` (`8.1444e-14` globally) and `4.2463e-2 N` (`8.0881e-14`); for `(1e-6,3e-7)` they were `4.5663e-4 N` (`8.6977e-16`) and `4.3552e-4 N` (`8.2956e-16`). At finer pairs, estimates reach the same ~`1e-17` binary64-matrix comparison floor. Full 12-step results for both hardening values are in `tet4_free_center_richardson.csv`; all six cases and all 12 step values are in `j2_fixed_history_derivative_sweep.csv`.

This confirms the H finding: the previous final-three-point rule included a truncation-dominated `3e-6` point just above its proposed `1e-7` limit, while the finer points were below it and continued converging. That rule can reject a converging sequence because it requires every point in the window to pass. The numerical threshold itself is not changed or approved here.

### Weak near-translation directions

The weak vectors are normalized uniform x-translation plus `1e-15` times a mixed perturbation. Their measured distance from exact translation is about `1.00e-15 m`; their prescribed-DOF component norms are 0.9428 (TET4) and 0.9813 (HEX8). They are approximate full-space translations, not admissible reduced Newton directions.

| Family / hardening | Decimal derivative norm (N) | Exact dot of stored binary64 K (N) | Absolute difference (N) | Local relative error | Global error |
|---|---:|---:|---:|---:|---:|
| TET4 / 0 | `1.7855600e-4` | `1.8299495e-4` | `1.2034803e-5` | `6.7401e-2` | `2.2923e-17` |
| TET4 / `1.5e9` | `1.7895984e-4` | `1.7751999e-4` | `1.2316378e-5` | `6.8822e-2` | `2.3460e-17` |
| HEX8 / 0 | `6.8663611e-5` | `6.7472956e-5` | `6.2674089e-6` | `9.1277e-2` | `1.1938e-17` |
| HEX8 / `1.5e9` | `6.8759115e-5` | `6.9173896e-5` | `7.5841202e-6` | `1.1030e-1` | `1.4446e-17` |

Across all 12 Decimal step values per case, these error and action norms remain constant to the shown digits; every perturbation preserves branch identity. Therefore the observed local discrepancy is not a centered-difference truncation trend or binary64 force-subtraction noise in the Decimal oracle. However, the direction is nearly null, and the assembled K entries are binary64. Cancellation of large stiffness contributions can magnify entry-rounding error in `Kp`; a global `K_ref ||p||` denominator hides the local mismatch. This evidence does not distinguish matrix-entry/assembly cancellation from a mathematical tangent discrepancy for the full-space near-null vector. No exact-translation control result is available to help isolate it.

The global normalization is dimensionally correct but insufficient alone for weak actions. A future gate should make reduced-space eligibility explicit, use a step-dependent resolution floor, report local error only when the response is resolved, and classify the near-null case `NOT_EVALUABLE` when it is not. Exact uniform translation belongs in a separate raw-operator invariance control. These are recommendations only; no threshold or gate is frozen.

## Translation-control failures: confirmed test defect

The source trace shows:

1. `_prepared_state` creates `dofs`, builds the plan from that exact object, then returns `model`, `center`, `plan`, and state—but not `dofs` (`tests/unit/test_wp_e01i_j2_precision_diagnostics.py:165-183`).
2. The translation test creates a new manager with `model.dof_manager()` (`:466`).
3. `NonlinearAssemblyPlan.matches` requires `self.dofs_token == id(dofs)` (`src/solveur/core/assembly/nonlinear.py:112-127`).
4. The assembly call raises `InputValidationError` at `nonlinear.py:249`, before the translated force/tangent assertions or Decimal translation oracle.

The minimum test-only correction for a future separately authorized identity is to preserve and reuse the original `DofManager` returned alongside the plan (or rebuild the plan from the newly created manager). Prefer returning the original manager so the check tests the intended cached-plan path. Do not add an exception alias or alter production plan validation. This correction was not made under this GO.

The weak-vector characterization did run: distance from exact translation was `9.9989e-16 m` for TET4 and `1.0067e-15 m` for HEX8; prescribed components were respectively `0.942809` and `0.981307`. No external or contact force enters those characterization calculations. These measurements confirm non-admissibility under the fixture constraints, not internal-force translation invariance.

## Failure classification and scientific conclusion

| Historical H condition | J evidence | Strongest supported classification | Limitation |
|---|---|---|---|
| TET4 free-center mixed, H=0 | Smooth all-plastic branch; `O(h^2)` raw error reduction; high-precision/Richardson agreement reaches binary64 K comparison floor | `TANGENT_CONSISTENT_WITH_ORACLE` for this fixed-history direction; H failure caused by `PROPOSED_GATE_DEFECT` (window selection) | One mesh/state/direction; not a general tangent qualification |
| TET4 free-center mixed, H=`1.5e9 Pa` | Same trend and sub-`1e-16` fine/Richardson comparison | `TANGENT_CONSISTENT_WITH_ORACLE` for this bounded case; `PROPOSED_GATE_DEFECT` | Same scope limitation |
| TET4 weak, H=0 and `1.5e9 Pa` | Stable Decimal derivative; 6.74%/6.88% local mismatch; near-translation and prescribed components nonzero | `INADMISSIBLE_REDUCED_DIRECTION` plus `INSUFFICIENT_EVIDENCE` for raw full-space tangent cause; cancellation is plausible | Exact translation control did not run; cannot call this a production tangent defect or PASS |
| HEX8 weak, H=0 and `1.5e9 Pa` | Stable Decimal derivative; 9.13%/11.03% local mismatch; near-translation and prescribed components nonzero | `INADMISSIBLE_REDUCED_DIRECTION` plus `INSUFFICIENT_EVIDENCE`; cancellation is plausible | Same missing raw translation control |
| Four J translation nodes in J | Plan/manager identity mismatch before calculations | Test-harness defect (`NonlinearAssemblyPlan` identity mismatch) | No numerical translation result was recorded |

The H failures remain historical failures under the unchanged proposed gate. J supplies bounded evidence that the two TET4 mixed-direction failures were truncation/window-selection effects, but the four weak-direction observations remain unresolved for a raw full-space operator and are ineligible for the constrained Newton derivative gate. No production J2 tangent defect is demonstrated; none is ruled out generally.

## Independent read-only review

An authorized independent reviewer examined the persisted J logs and source without editing or executing code. The reviewer agreed the four translation failures are test-harness plan identity mismatches and that no translation invariant was measured. They agreed the six derivative cases pass only branch/state assertions; TET4 mixed directions support fixed-history derivative agreement, while weak-direction local differences remain unresolved and should not be promoted. The independent reviewer identified no basis to freeze a revised gate. This was a read-only interpretation, not a second numerical execution.

## Evidence files and hashes

| Artifact | SHA-256 |
|---|---|
| `preflight.json` | `49580E5CE7FD1EB865FE2559E45091263A8A738516FFA4A7087121D35117D26A` |
| `summary.json` | `431A73F2AEDF22124A6D33B12E3C5D34F0A99BF63FE9111629394F826774FC19` |
| `execution/collection_nodes.json` | `D5ED0E79A92C64C436C219A55635E144448CE6EA29C3C47EEB41A5A470FA151B` |
| `execution/phase_result.json` | `A61AF12280329154B98A5B304908DCD02043273987CEC1CCA125766595243C3D` |
| `execution/stdout.log` | `0C456A49A17AD5198E1F34564A678F4B31D9B7C02F443C92A48C844465807BAF` |
| `execution/stderr.log` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |
| `j2_fixed_history_derivative_sweep.csv` (72 step rows) | `449617EE1BCFC626F86643A4B2A333276C5824647395CBD9207A2D07E0B65F00` |
| `tet4_free_center_richardson.csv` (22 adjacent-step estimates) | `D37312B188ADB7530F6E5206C67F2C2E8EA7508770238F2E9CACCBCD653C7518` |

## Verdicts

| Status | Result |
|---|---|
| `J2_DIAGNOSTIC_COLLECTION` | `12_OBSERVED` |
| `J2_HIGH_PRECISION_ORACLE` | `VERIFIED_BOUNDED` for fixed-history derivative comparison |
| `RIGID_TRANSLATION_VNV` | `BLOCKED` — all four controls stopped at plan validation |
| `TET4_DERIVATIVE_WINDOW` | `CHARACTERIZED` |
| `WEAK_DIRECTION_RESOLUTION` | `CHARACTERIZED`; reduced-space local gate is ineligible, raw cause unresolved |
| `J2_TANGENT_ROOT_CAUSE` | `PARTIAL` |
| `REVISED_TANGENT_GATE` | `PROPOSED_NOT_APPROVED` |
| `ELASTIC_PATCH_VNV` | `PREVIOUS_PASS_BOUNDED` |
| `STVK_GLOBAL_TANGENT` | `PREVIOUS_PASS_BOUNDED` |
| `GLOBAL_ASSEMBLY_VNV` | `PARTIAL` |
| `INCREMENTAL_NEWTON_FEM` | `NOT_RUN` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Exact next Owner decision

Authorize a **new exact test identity** with the test-only `DofManager`/plan correction, updated NUMERICAL_UNIT hash binding, and a fresh safety review. Then authorize one supervised execution limited to the four rigid-translation controls. Keep all tangent thresholds and the J2 scientific gate unchanged. The next run should report raw internal-force invariance, `K t`, Decimal invariance, branch identity, accepted-state immutability, and resource evidence. The weak-vector mismatch remains a separate follow-up question; do not use an exact-translation result to claim that every near-null direction is tangent-qualified.
