# WP05-D stress-window remediation candidate

## Status

`CANDIDATE_REQUIRES_OWNER_APPROVAL_NO_QUALIFICATION_EXECUTION`

This package prepares a prospective WP05-D observable-contract revision. It
does not modify the frozen WP05-C/D contract, any raw result, the historical
`WP05D_FORMAL_STATUS = FAIL_CLOSED`, or WP05 points.

## Problem isolated

The frozen observable averages Cauchy `sigma_xx` only at existing element
integration points that fall inside the fixed reference box:

`0.40 <= X/L <= 0.60`, `0.70 <= Y/H <= 0.95`, and
`0.20 <= Z/D <= 0.80`.

For HEX20, this point-membership rule selects different effective regions on
the formal meshes:

| Mesh | selected points | sampled reference volume | expected physical volume |
|---|---:|---:|---:|
| H2 | 96 | 0.028838734567901255 | 0.030000000000000000 |
| H3 | 840 | 0.030647183641975325 | 0.030000000000000000 |

The resulting H2-to-H3 stress delta is `10.4273435571%`, above the frozen
`8%` limit. Displacement, force/moment equilibrium, reaction, energy and the
deformation envelope pass. This identifies a mesh-dependent sampling
observable, not a demonstrated nonlinear-solver failure.

## Candidate measurement

The candidate keeps the exact same physical box, reference-coordinate frame,
reference-volume weighting, material, mesh sequence, load, boundary
conditions and `8%` gate. It changes only how the box is integrated:

1. Intersect each straight-sided HEX20 cell with the physical reference box.
2. Transform the intersection to the element natural coordinates.
3. Integrate Cauchy `sigma_xx` with deterministic tensor 5x5x5
   Gauss-Legendre quadrature on the clipped subcell.
4. Reject non-affine/curved HEX20 geometry instead of approximating it.

This gives exactly the same reference region on every structured mesh. The
candidate unit tests establish exact reference volume `0.03` for H1/H2/H3 and
partition invariance for a uniform affine deformation.

## Governance and next gate

Owner approval is required before this candidate becomes a new WP05-D
contract. If approved, a new digest must be frozen, then H1/H2/H3,
an independent reference and replay must be executed. Only that later
requalification may decide whether the unchanged `8%` threshold is met.

No existing PASS/FAIL evidence may be overwritten or reclassified.
