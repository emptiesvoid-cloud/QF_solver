---
doc_id: DOC-027-017
revision: 0.2
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: OWNER_APPROVED_BOUNDED
source_sha: 9d79dc8b306e6cc65f2f4ae2e77e00f676182b84
evidence_artifact: qualification/0_2_7/vnv_v2/wp10_final_evidence.json
---

# WP10 WEDGE6 Modal Qualification Evidence

WP10-FINAL is `PASS` within the declared bounded scope. The gate remains
`PASS_WITH_LIMITATIONS` because the qualification is limited to the tested
consistent-mass WEDGE6 modal route and does not make a general dynamics claim.
The active Owner decision is `OWNER_APPROVED_BOUNDED`.

## Scope and policy

The tested route is the common modal assembler with a six-node, 18-DOF
WEDGE6, homogeneous isotropic small-strain elasticity, positive density and
the consistent translational mass matrix
`M = rho * integral(N^T N det(J)) tensor I3`. Production integration is
`TRI3_X_GAUSS2` (6 points). `DUFFY_GAUSS5_X_GAUSS4` (100 points) is a
verification reference only. No lumped-mass or reduced-integration route is
qualified.

The final policy was fixed in the declarative catalog before replay: mass
symmetry relative error `<= 1e-14`, rigid-translation mass conservation
absolute error `<= 1e-10` in the declared model units, modal eigenpair residual
`<= 1e-7`, mass orthogonality error `<= 1e-12`, and finite positive requested
frequencies. Same-mesh external frequency comparison uses relative tolerance
`1e-2`, MAC uses `>= 0.99`, and a relative frequency gap `<= 1e-5` uses
subspace MAC. The refinement criterion is `<= 1e-2` between the final levels
for the first three modes. These tolerances are approved only for this bounded
scope; post-result retuning is forbidden and monotonicity is not required.

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

The final replay used 4, 8, 16 and 32 prism segments. The first three final
adjacent relative changes were `0.779170%`, `0.125485%` and `0.030112%`, all
within the `1%` rule. Modes four to six remain diagnostic because their fourth
final adjacent change is `1.075439%`. The maximum normalized eigenpair
residual was `2.3993260594985674e-11`, all requested frequencies were finite
and positive, and deterministic replay passed.

| Segments | Mode 1 (Hz) | Mode 2 (Hz) | Mode 3 (Hz) |
| ---: | ---: | ---: | ---: |
| 4 | 81.556398 | 151.870479 | 269.886494 |
| 8 | 73.511829 | 148.992958 | 268.591238 |
| 16 | 71.335789 | 148.253799 | 268.267970 |
| 32 | 70.779961 | 148.067764 | 268.187189 |

Refinement status is `PASS_QUALIFIED` for the first-three-mode observable;
higher modes are not silently counted as converged.

## Code_Aster correlation

The reproducible headless reference is Code_Aster 18.1.0/PENTA6 in the
pinned image
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`.
Four same-mesh cases were executed: axial single prism, bending multi-prism,
distorted valid prism and multi-WEDGE mesh. They use the same geometry, node
order, material, fixed condition, mass convention and six-mode request. The
maximum frequency relative error was `1.927e-13`, the minimum MAC was
`0.9999999999999991`, and all `24/24` mode pairs passed the predeclared
frequency and MAC rules. The deck extracts physical `DX`, `DY` and `DZ`
components and excludes Lagrange multiplier components before comparison.
This is bounded cross-solver evidence, not universal modal validation.

The canonical deck and compact result are recorded at:

- `qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP10-A-penta6-modal.comm`
- `qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP10-A-penta6-modal.mail`
- `qualification/0_2_7/external_oracles/wedge6/results/wp10_code_aster_modal.json`

## Limitations and next gate

- WEDGE6 modal maturity is `QUALIFIED_BOUNDED` only for the scope declared
  above; the gate remains `PASS_WITH_LIMITATIONS`.
- Modes four to six are externally matched but remain diagnostic for mesh
  convergence.
- No lumped-mass route is qualified.
- No qualification transfers to Newmark, harmonic, nonlinear, J2, TL, contact
  or general dynamic routes.
- Newmark, harmonic, nonlinear, J2, TL and contact WEDGE6 routes are outside
  WP10.
- Full regression was not run under the WP10 T0/T1/T2 targeted policy; no
  existing-element numerical formulation was changed.

Machine-readable records are the source for the final case-level evidence:
`qualification/0_2_7/vnv_v2/wp10_final_cases.json`,
`qualification/0_2_7/vnv_v2/wp10_final_evidence.json` and
`qualification/0_2_7/wp10_final_state.json`. The original 16-case records
`qualification/0_2_7/vnv_v2/wp10_cases.json` and
`qualification/0_2_7/vnv_v2/wp10_evidence.json` remain preserved as historical
evidence and are not used to dilute the final policy.
