# WP-C01-R13 — Experimental small-rotation contact transfer

**Status:** `SMALL_ROTATION_TRANSFER_INCONCLUSIVE` for the requested FEM
campaign. The bounded transfer formula, implementation path, and algebraic
contract tests are ready for an exploratory FEM confirmation; no FEM was run.

## Scope and source identity

This work is based on R10 branch `emptiesvoids-cloud/wp-c01-r10-telemetry`,
HEAD `b547601ad7d6558f32d93cec37e1cc90e805eab1`, tree
`552f8e6a00f8f1de89d2627a7c5c297dbe34da06`. Changes are isolated on
`emptiesvoids-cloud/wp-c01-r13-transfer`.

The experiment is deliberately limited to one frozen slave node, one reference
master triangle, initial projection, friction, linear static active-set
contact, and infinitesimal rotations. The default `legacy` transfer remains
the default and retains its numerical behavior and diagnostic shape.

## Formulation and implementation

For reference gap `g0 = n·(X_s - Σβ_j X_j)`, triangle shape gradients
`a_j = ∇_sN_j`, and a frozen tangent `t_a`, the implementation forms

```text
δn = -Σ_j a_j (n·δu_j)
B*_a δu = t_a·(δu_s - Σ_j β_jδu_j - g0δn)
```

It assembles the conjugate generalized force `B*ᵀ F_t`, giving
`q_s = F_t` and `q_j = -β_j F_t + g0(a_j·F_t)n`. The generalized forces have
zero resultant and zero reference moment for a planar linear triangle. The
stick matrix remains the exact derivative `k_t B*ᵀB*`; slip uses the existing
Coulomb return map and transition policy with the new `B*ᵀF_t` mapping. No new
global consistent slip tangent was added. The post-processing moment correction
is bypassed only for this experimental mode; the raw check and 0.002 N·m limit
are unchanged.

The mode is bound into non-legacy restart configuration identity and is
rejected by both model validation and the active-set operator builder when the
input leaves the stated domain. It also rejects a displaced operator reference.
Equation, sign, units, and kinematic limits are documented in
[`contact_small_rotation_work_conjugate_transfer.md`](../../docs/contact_small_rotation_work_conjugate_transfer.md).

No contact law, legacy tolerance, Coulomb yield rule, active-set transition,
load path, material, or normal-force assembly was changed. The experimental
mode adds real master-node force contributions, so a FEM confirmation must
inspect master support reactions.

## Non-FEM evidence

The versioned test file
[`test_wpc01_r13_small_rotation_transfer.py`](../../tests/unit/test_wpc01_r13_small_rotation_transfer.py)
contains 11 tests for legacy identity, the independent `B*` and force formulas,
virtual-work duality, force/moment resultants, rigid virtual motions, zero-gap
reduction, stick tangent finite differences, slip/open/zero-capacity mapping,
active-state transitions, raw moment preservation, restart identity, route
guards, and fail-closed rejection of the M2 patch.

`python -m pytest -q tests/unit/test_wpc01_r13_small_rotation_transfer.py`:
**11 passed**, no global solve and no FEM. The final measured run is archived in
[`wp_c01_r13_non_fem_test_run_05.json`](wp_c01_r13_non_fem_test_run_05.json):
3.45 s wall time, 126,533,632 bytes peak sampled process-tree RSS, exit code 0.
Pytest collection found the same 11 nodeids. Output/temp byte counts were not
measured because this was a non-FEM test run and it created no campaign output.

The independent read-only review is archived in
[`wp_c01_r13_independent_review.md`](wp_c01_r13_independent_review.md). It found
no remaining P0/P1 issue in the bounded contract and confirmed the
operator/force duality, stick tangent, raw moment handling, and route guards.
The slip branch remains an explicit limitation for later qualification, not a
claimed new tangent validation.

## FEM scenarios A–F

The minimum usable sequence is:

| Scenario | Intended check | R13 result |
|---|---|---|
| A | One slave node, one reference master triangle, nonzero initial gap, free master translations; compare legacy and `B*` assembly and master reactions. | Prepared in scope; not run. |
| B | On the same pair, load normal contact first, then tangential stick, then slip; archive branch transitions and master reactions. | Prepared in scope; not run. |
| C | Common infinitesimal rigid translation/rotation. | Covered algebraically; no FEM needed. |
| D | Centered differences of virtual work and stick tangent. | Covered by the versioned algebraic tests. |
| E | Independent raw force/moment balance with no artificial correction and the unchanged 0.002 N·m limit. | Requires FEM result archive; not run. |
| F | Prospective M2 non-regression and master-reaction inspection. | The R10 M2 input has nine slave nodes and two master faces. It is outside the strict one-pair `B*` contract and is rejected when the mode is enabled. A legacy-only M2 regression can check default non-regression, but cannot validate `B*` or its master reaction transfer. |

## Run gate and verdict

No FEM command was issued. `DEVELOPMENT_AUTONOMOUS` Level 3 requires a frozen
source identity, explicit numerical/time/resource limits, and an execution
manifest. R13 specified the physics and cases but supplied no limits or
manifest. These cannot be inherited from R9/R10, and their manifests remain
untouched. Thus the test and implementation result is favorable, but the FEM
campaign verdict is **`SMALL_ROTATION_TRANSFER_INCONCLUSIVE`**.

For the next step, freeze this branch after the final test/review, create a new
R13-only inactive execution manifest, and obtain one consolidated owner limit
set for wall time, peak RSS, output/temp bytes, thread/process count, attempts,
and stop-on-failure behavior. Then run A and B sequentially, inspect E from
their raw outputs, and run F only as a legacy/default M2 regression. Do not use
F to claim that `B*` was validated on M2. Expanding `B*` to the nine-slave/two-
face M2 patch would require a separate contract and review.

No merge, release, qualification promotion, or historical archive change was
made. Preserve `WP_C01_HISTORICAL=CLOSED_NEGATIVE`,
`CANONICAL_M2_NOT_RECOVERED`, `WP_C01_REMEDIATION=OPEN`, and
`WP_C02=CLOSED_BOUNDED`.
