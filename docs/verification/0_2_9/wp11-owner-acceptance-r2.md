# WP11 Owner acceptance — R2 multi-family bounded scope

## Decision

The Owner accepts WP11-R2 for the bounded multi-family scope and awards the
full six WP11 points:

```text
OWNER_ACCEPTS_WP11 = YES
OWNER_AWARDS_WP11_POINTS = 6/6
WP11_OFFICIAL_POINTS = 6/6
GLOBAL_OFFICIAL_TOTAL_BEFORE = 84/100
GLOBAL_OFFICIAL_TOTAL_AFTER = 90/100
FINAL_STATUS = APPROVED_WITH_LIMITATIONS
```

Accepted families are TET4, HEX8, TET10 and HEX20. M1 serial SciPy, M2
PETSc/MPI two-rank execution, M3 fresh-process replay and the independent
file-backed observable recomputation passed for each family.

## Accepted limitations

- bounded linear-static, one-element homogeneous cases;
- root-side assembly with replicated input;
- no strong- or weak-scaling claim;
- no dynamics, contact or friction qualification;
- no general mesh-convergence claim;
- the reference is an independent observable recomputation, not an
  independent global FEM/Newton solve;
- no Code_Aster or other external-solver correlation;
- no cross-family physical equivalence claim.

The historical TET4 R1 evidence and the earlier R2 candidate package remain
preserved. No governing push or merge is authorized by this decision.

Evidence: [WP11 provenance Owner review](wp11-multifamily-provenance-owner-review.md)
and [machine-readable acceptance](../../../qualification/0_2_9/wp11_owner_acceptance_r2.json).
