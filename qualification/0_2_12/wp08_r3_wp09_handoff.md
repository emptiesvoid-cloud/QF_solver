# WP08-R3 handoff to WP09 / WP10

**This is a handoff record only. WP09 and WP10 are not started or authorized here.**

## R3 boundaries now present

- Corrected force and tangent are selected together via `corrected_corotational_biot_j2/v1`; absent selector means legacy.
- Production R3 tangent is a raw central difference of corrected force with fixed accepted state, `h=1e-5 V0^(1/3)`, and `2*n_dof+1` force evaluations. It is not symmetrized.
- The local step does not use `max(abs(coordinates))`; an origin-shift fixture passes the frozen R1 tolerance. General conditioning, scale extremes and broader finite-difference robustness remain unclaimed.
- Nonsmooth yield branch changes are explicitly counted; the matrix is not described as a classical derivative when a sampled branch changes. No general semismooth Newton proof is claimed.
- Corrected output and checkpoint identifiers are in place; legacy output/default and historical checkpoint schemas are not rewritten.

## WP09 observations, not authorization

WP09 may assess whether to replace or improve the finite-difference production tangent with an algorithmic/Frechet derivative, characterize conditioning and cancellation over broader scales, stress repeated/near-repeated stretches and origin shifts, and reduce cost without losing raw-tangent evidence. It must continue to compare against fixed-accepted-state independent directional differences and must not symmetrize. Any change to R1 equations or constitutive history requires Owner rescope. R3 already uses a geometry-local characteristic length for the corrected finite difference; the legacy branch retains its old step and is deliberately untouched.

## WP10 observations, not authorization

Corrected fixed/adaptive load-control checkpoint restart is versioned and formulation/material/model bound on the tested path. General historical checkpoint migration, broader accepted-state recovery, migration of incomplete NL v1/v2 states, and expanded failure/convergence policy remain separate work. No old checkpoint is migrated into the corrected formulation. Preserve fail-closed behavior unless an explicit compatibility proof and Owner approval exist.

## Status

R3 does not modify global QF0212 gates or authorize release. Preserve `HISTORICAL_G03=FAIL_PRESERVED`, `HISTORICAL_WP14=HOLD_NOT_PROMOTED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED=NO`, and corrected J2 maturity `EXPERIMENTAL`. Owner authorization is required before WP09 or WP10 starts.
