# WP09 handoff notes for a future WP10

**Status:** informational only. WP10 has not been started or authorized by this work.

## Preserved contracts

- Corrected formulation remains `corrected_corotational_biot_j2/v1`, explicit opt-in, `EXPERIMENTAL`.
- Accepted material state is fixed for base and all perturbation force evaluations; no trial result from tangent construction is committed.
- Corrected tangent remains raw central difference with `h=1e-5 V0^(1/3)`, `2*n_dof+1` force evaluations, and no symmetrization.
- Tangent strategy provenance is `origin_centered_scaled_geometry/v2` in solver results. Existing checkpoint format and corrected formulation identity are unchanged.
- Unresolvable reference coordinates or displacement stencil fail closed as `NUMERICALLY_AMBIGUOUS`; legacy route behavior is untouched.

## Restart and transaction boundary

WP09 did not alter checkpoint serialization, checkpoint identity, accepted-state schema, restart migration, or commit/rollback semantics. The corrected route remains formulation-bound as validated in WP08-R3. WP09 changes floating evaluation order through centering/scaling, so bit-for-bit identity of a pre-WP09 checkpoint's future trajectory across software revisions is not asserted. Same-version deterministic restart tests and the existing formulation/material/model compatibility checks remain the relevant evidence. Do not migrate legacy or unidentified checkpoints based on these results.

## Possible WP10 checks (not work performed here)

1. Re-run restart equivalence under the WP09 strategy version with interrupted and uninterrupted corrected load paths.
2. Decide whether tangent strategy version must participate in execution/checkpoint identity for exact replay; do not change identity semantics without the WP10 contract and review.
3. Exercise failure/cutback recovery when tangent diagnostics are `BRANCH_TRANSITION` or `NUMERICALLY_AMBIGUOUS`, ensuring no trial state was committed.
4. Keep the geometry and displacement precision refusals explicit in restart diagnostics; do not silently fall back to the legacy tangent.
5. Preserve the separation between corrected and legacy formulations, and retain fail-closed behavior for historical NL checkpoint migrations.

These suggestions do not close WP09-wide gates, authorize WP10, or imply a release decision.
