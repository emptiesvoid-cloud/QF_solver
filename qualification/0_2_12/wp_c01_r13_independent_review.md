# WP-C01-R13 — Independent read-only review

**Disposition:** favorable within the stated frozen-pair, small-rotation
contract. No remaining P0 or P1 issue was identified. This review does not
validate finite sliding, solve convergence, or physical qualification.

## Reviewed scope

- Substitution of the specified `δn` into `B*` and the conjugate force map.
- Stick tangent and the actual assembled contact-force mapping.
- Existing slip return map, slip transition behavior, and the absence of a new
  consistent global slip tangent.
- Force/moment resultants and the mode-specific bypass of post-processing
  moment correction.
- Single-pair, initial-reference, small-rotation restrictions.
- Direct operator-builder guards and legacy diagnostic compatibility.

## Findings

1. **Operator and forces:** the master-node addition in each tangent row is
   `g0 (t_a·a_j)n`, matching the stated formula. The assembled mapping is
   `B*ᵀF_t`, giving the specified slave and master contributions. The
   identities `Σa_j=0` and `ΣX_j⊗a_j=P` give zero resultant and moment for a
   tangential pair on a planar linear triangle.
2. **Stick tangent:** the existing rank-one assembly uses each updated row,
   `k_t b_aᵀb_a`, so it is the derivative of the corresponding
   work-conjugate stick force. The versioned tests compare it to centered
   differences.
3. **Slip:** the current Coulomb force and branch transitions are unchanged;
   their generalized mapping uses `B*ᵀF_t`. The option does not add a new
   consistent global slip tangent, and no such validation is claimed.
4. **Moment audit:** B* is assembled in the solve path. The experimental mode
   leaves the raw global moment visible and records a zero post-processing
   correction. The legacy correction remains separate.
5. **Scope guards:** public validation and `_contact_operators` restrict the
   option to one frictional slave node, one reference triangle, linear-static
   active-set contact, initial search, and an undisplaced operator reference.
   The R10 M2 multi-slave/multi-face input is rejected by this mode.

The first review pass noted that direct private calls could bypass some
model-level restrictions. Checks were added at `_contact_operators`, including
rejection of a non-null displaced reference. A follow-up review found these
guards consistent with the normal route and confirmed that legacy diagnostic
keys remain unchanged.

## Limits

This was a code/formulation review only. The reviewer made no file changes and
ran no test, global solve, or FEM calculation. The conclusions apply to the
linearized frozen reference pair and do not imply finite-slip objectivity,
face changes, or physical superiority over legacy.
