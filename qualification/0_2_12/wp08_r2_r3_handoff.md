# WP08-R2 to R3 handoff

## R2 result and safe-use boundary

R2 provides an explicit corrected corotational J2 material-state and internal-force kernel with the R1 exact polar-adjoint map, bounded to `||U-I||_F <= 0.05`, `det(F)>1e-10`, and existing isotropic associative J2 with linear isotropic hardening. The legacy default remains intact.

**Corrected global Newton route: NOT READY.** The existing legacy tangent is not established as the derivative of the corrected force. The global assembly/solver boundary rejects corrected formulation selection before solving. Do not remove that guard or call the corrected force kernel a usable global analysis route until R3 supplies and verifies a compatible tangent.

**Production tangent validated: NO.** R2's independent finite-difference force/potential checks are verification oracles, not a production tangent. R2 makes no tangent qualification claim.

**Corrected public stress outputs/checkpoints: unavailable.** R2 intentionally blocks generic integration-point results and does not implement corrected checkpoint serialization, resume, migration, or historical output reinterpretation.

## Required R3 work

1. Derive and implement the raw algorithmic derivative of the corrected nominal stress, including the derivative of `R`, the polar adjoint with respect to `U`, and the existing J2 algorithmic tangent on elastic/plastic branches.
2. Handle repeated and near-repeated stretches through basis-invariant Frechet/divided-difference/Sylvester methods; do not differentiate arbitrary eigenvectors.
3. Define and test yield switching/generalized derivative behavior. Do not symmetrize the raw tangent before reporting or Newton use.
4. Compare tangent action to fixed-accepted-state central directional force differences at the preregistered local, origin-invariant steps; separately establish element/global tangent assembly and solver convergence.
5. Implement result measure/frame/semantic version, availability, aggregates, serialization, and fail-closed compatibility with legacy results.
6. Implement full physical/operator/formulation identities and corrected checkpoint provenance; reject legacy or insufficiently identified checkpoints for corrected resume.
7. Run integrated nonlinear tests and required regressions, then separately evaluate QF0212 gates. Numerical pass does not imply qualification or maturity promotion.

## Do not fold into R3 without authorization

General tangent robustness/origin-invariance work belonging to WP09, checkpoint/convergence policy overhaul belonging to WP10, multiplicative finite-strain plasticity, new constitutive laws, global Newton redesign, or general finite-strain validation are outside this R2 handoff. If any becomes necessary to derive a consistent corrected tangent inside the R1 scope, stop and request an explicit rescope.

## Statuses preserved

`WP08_STATUS=BLOCKED`; `QF0212_G03_NL=BLOCKED`; `QF0212_G04_NL=BLOCKED`; `HISTORICAL_G03=FAIL_PRESERVED`; `HISTORICAL_WP14=HOLD_NOT_PROMOTED`; `WHOLE_REPOSITORY_ARCHIVE_CLEARED=NO`; `RELEASE_PUBLICATION_AUTHORIZED=NO`. The corrected formulation remains experimental and not qualified. R2 completion is not R3 authorization.
