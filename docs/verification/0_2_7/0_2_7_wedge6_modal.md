---
doc_id: DOC-027-017
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
source_sha: 7d494eaa638ffa88a04ed3e5c51f6036ad1804a1
---

# WP10 WEDGE6 Modal Evidence

WP10 is `PASS_WITH_LIMITATIONS` for the declared technical modal evidence.
The WEDGE6 modal route remains `EXPERIMENTAL`, and public qualification is
`DEFERRED`. This record is independent from the WP07-WP09 static evidence;
static maturity is not transferred to dynamics.

## Scope and policy

The tested route is the common modal assembler with a six-node, 18-DOF
WEDGE6, homogeneous isotropic small-strain elasticity, positive density and
the consistent translational mass matrix
`M = rho * integral(N^T N det(J)) tensor I3`. Production integration is
`TRI3_X_GAUSS2` (6 points). `DUFFY_GAUSS5_X_GAUSS4` (100 points) is a
verification reference only. No lumped-mass or reduced-integration route is
qualified.

The acceptance policy was fixed before execution: mass symmetry relative
error `<= 1e-14`, rigid-translation mass conservation absolute error
`<= 1e-10` in the declared model units, modal eigenpair residual `<= 1e-7`,
mass orthogonality error `<= 1e-12`, and finite positive requested
frequencies. The external frequency candidate is a relative tolerance of
`1e-2`, marked `OWNER_REVIEW_REQUIRED`; it is not a universal accuracy claim.

## Evidence summary

The catalog contains 16 cases: 15 `PASS`, one controlled
`EXPECTED_FAILURE_PASS` for zero density, and no unexpected failure.

| Check | Result |
| --- | --- |
| Mass symmetry | relative error `0.0`; PASS |
| Mass positivity | minimum eigenvalue `324.9999999999996`; PASS |
| Total mass | expected `23399.999999999993`; maximum translation error `7.28e-12`; PASS |
| Production/reference mass | relative difference `3.32e-16`; PASS |
| Density and geometry scaling | PASS; geometry ratio `7.9999999999999964` |
| Single-element modal solve | six finite positive frequencies; residual `1.08e-13`; PASS |
| Three-element modal solve | residual `6.31e-13`; mass orthogonality `5.14e-16`; PASS |
| Distorted valid prism | finite modal solve; residual `4.30e-13`; PASS |
| Deterministic replay | frequencies and mode vectors identical; PASS |
| Zero-density input | fail-closed expected failure; PASS |

The first frequency over the four declared mesh levels (1, 2, 3 and 4
prism segments) is `156.4464`, `106.6541`, `88.9941` and `81.5564` Hz.
The final relative change is `9.12%`. This is reported as a bounded trend;
no monotonicity or universal modal convergence threshold is claimed.

## Code_Aster correlation

The reproducible headless reference is Code_Aster 18.1.0/PENTA6 in the
pinned image
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`.
It uses the same affine single-prism geometry, node order, bottom-node fixed
condition, material and six-frequency request. The primary observable is
frequency, not a mode-shape comparison. The maximum relative difference is
`4.03e-14`, below the predeclared `1e-2` candidate, so the result is
`PASS_EXTERNAL_CORRELATION_BOUNDED`. This external result is not a public
qualification by itself.

The canonical deck and compact result are recorded at:

- `qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP10-A-penta6-modal.comm`
- `qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP10-A-penta6-modal.mail`
- `qualification/0_2_7/external_oracles/wedge6/results/wp10_code_aster_modal.json`

## Limitations and next gate

- WEDGE6 modal maturity remains `EXPERIMENTAL`; WP10 does not promote the
  public combination to `QUALIFIED_BOUNDED`.
- The refinement sequence is diagnostic and does not establish a general
  mesh-convergence claim.
- MAC is not claimed because no independently mapped external displacement
  mode field was required for the frequency-only bounded check.
- Newmark, harmonic, nonlinear, J2, TL and contact WEDGE6 routes are outside
  WP10.
- Full regression was not run under the WP10 T0/T1/T2 targeted policy; no
  existing-element numerical formulation was changed.

Machine-readable records are the source for the case-level evidence:
`qualification/0_2_7/vnv_v2/wp10_cases.json`,
`qualification/0_2_7/vnv_v2/wp10_evidence.json` and
`qualification/0_2_7/wp10_state.json`.
