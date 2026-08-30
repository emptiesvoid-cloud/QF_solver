# 0.2.6 G10 Owner Closeout

Status: `PASS_WITH_LIMITATIONS`

Execution source SHA: `9b4a44d61132a28fe9161f4aa8f04e838afc5f32`
Worktree at review: `dirty=false`

This closeout audits the existing nonlinear and research routes. It does not
add physics, elements or solver behavior, and it does not close or promote
G07. The selected external evidence is bounded evidence only.

## Owner route classifications

| Route | Owner classification | Boundary |
| --- | --- | --- |
| Nonlinear static small-strain | `OWNER_APPROVED_BOUNDED` | Existing G06 bounded scope only. |
| Transaction/checkpoint/retry | `OWNER_APPROVED_BOUNDED` | Existing G09/G11 evidence and stated coverage. |
| Structured failure diagnostics | `OWNER_APPROVED_BOUNDED` | Existing G11 bounded failure contract. |
| Arc-Length continuation | `OWNER_DEFERRED` | Bounded external evidence is useful to G07; G07 remains unchanged. |
| Total-Lagrangian elasticity | `OWNER_DEFERRED` | TET4/HEX8 evidence is bounded and routed to G07. |
| Finite-kinematic J2 | `OWNER_NOT_QUALIFIED` | No formulation-compatible external constitutive qualification. |
| J2 plus geometry | `OWNER_DEFERRED` | No external evidence isolating constitutive and kinematic effects. |
| Geometry plus frictionless contact | `OWNER_EXPERIMENTAL_ONLY` | Existing contact law/surface limits remain. |
| J2 plus geometry plus contact | `OWNER_NOT_QUALIFIED` | Coupled external qualification is absent. |
| Modified Newton finite-kinematic | `OWNER_NOT_QUALIFIED` | Existing finite-route restriction remains. |

No route is classified `OWNER_FAILED`. The deferred and unqualified routes do
not block this audit closeout because they are excluded from any qualified
claim and remain visible as limitations.

## External evidence decision

The selected campaigns are formulation-compatible within their declared
domains and are recorded as `PASS_WITH_LIMITATIONS`:

- Arc-Length: 75 common interpolated points, one branch turn on each solver,
  relative turning-point differences of `1.33e-4` in load factor and `6.62e-3`
  in control displacement.
- Total-Lagrangian TET4: stress relative error `8.54e-5` and column maximum
  relative difference `1.69e-9` over four points to 80% of the same-mesh
  critical load.
- Total-Lagrangian HEX8: matched-point displacement difference `2.34e-9`,
  sign-aligned reaction difference `1.32e-11`, and QF residual `2.29e-13`.

The HEX8 full QF instrumented path was not completed within the bounded
campaign budget. External stress, energy and `det(F)` outputs were not mixed
with incompatible QF measures. These limitations prevent a general claim;
they do not create a numerical defect.

## Requirements and regression policy

All nine G10 requirements are addressed at full or bounded level. The
external-correlation requirement is satisfied as a recorded, bounded audit:
available comparable evidence is attached and missing formulation-compatible
routes remain explicit. No blocking requirement remains for the G10 audit
scope.

No functional source changed and no numerical regression was detected. Full
regression is therefore `SKIPPED_BY_POLICY`; the 73 targeted tests, registry,
anti-forgetting, Ruff, compileall and diff checks are the applicable closeout
controls.

## Final boundary

`026-G10 = PASS_WITH_LIMITATIONS`.

G07 remains unchanged. Arc-Length and Total-Lagrangian promotion decisions
remain G07-owned and deferred. Finite-kinematic J2 and coupled nonlinear
workflows remain experimental, not qualified, or deferred as listed above.
No general physical validation, industrial-solver equivalence or exhaustive
route-combination claim is made.
