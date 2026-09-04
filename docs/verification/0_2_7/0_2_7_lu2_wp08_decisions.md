---
doc_id: DOC-027-LU2-WP08-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# LU2-WP08: Mixed, WEDGE15, PYRAMID5 and HEX8 decisions

This is a governance decision record, not an implementation or qualification
record. It is based on the repository state at
`8ef34e345f970879548a4dfdce4ac5ba32c11bda`. The machine-readable source is
[`lu2_wp08_decision_matrix.json`](../../../qualification/0_2_7/lu2_wp08_decision_matrix.json),
and the state record is
[`lu2_wp08_state.json`](../../../qualification/0_2_7/lu2_wp08_state.json).

## Decision summary

| Axis | Observed state | LU2 decision | Priority | Public boundary |
| --- | --- | --- | --- | --- |
| Mixed TET/WEDGE/HEX | `PARTIAL` technical paths, no end-to-end qualification | `DEFER` | P1 | Not a qualified mixed route |
| WEDGE15 | `NOT_SUPPORTED` | `DEFER` | P2 | No active capability |
| PYRAMID5 | `NOT_SUPPORTED` | `DEFER` | P3 | Negative fixtures are not implementation |
| Existing HEX8 | `SUPPORTED_WITH_LIMITATIONS` | `KEEP_EXISTING_ROUTE` | P1 | Bounded route and WP19 diagnostic only |
| HEX8R | `NOT_EVALUATED` | `RESEARCH_ONLY` | P2 | No production claim |
| SRI | `NOT_EVALUATED` | `RESEARCH_ONLY` | P2 | No production claim |
| B-bar | `NOT_EVALUATED` | `RESEARCH_ONLY` | P2 | No production claim |
| Hourglass control | Not applicable to current full integration | `DEFER` | P3 | No reduced-integration claim |

## Mixed meshes

The Gmsh importer recognizes a bounded set of same-dimensional solid families,
and individual element routes exist. That is not an end-to-end mixed-mesh
qualification. Interface assembly, shared material and DOF contracts,
boundary-face selection, load transfer, post-processing and cross-family
equilibrium need a dedicated contract and V&V corpus. The LU2 decision is
therefore `DEFER`, rather than `IMPLEMENT_NOW` or `TARGETED_RESEARCH`.

## Candidate new solids

WEDGE15 has a plausible industrial value for quadratic prismatic meshes, but
would require a new kernel, high-order face/load mapping, quadrature, quality,
mass/modal and independent external evidence. PYRAMID5 is useful mainly when
transition meshes demonstrate a concrete need; its apex quality and
interpolation risks make it a larger V&V commitment than its current evidence
justifies. Neither family has an active descriptor, importer path or registry
capability here. Both are deferred beyond LU2.

Future evidence must include shape-function identities, Jacobian/orientation,
rigid-body modes, affine/patch tests, rank and energy checks, distortion,
loads/faces, deterministic replay and formulation-compatible external results.

## HEX8 next generation

WP19 remains authoritative for the existing bounded HEX8 route. Its compatible
C3D8 displacement study is a diagnostic and does not prove locking, universal
accuracy, or a replacement formulation. No production HEX8R, SRI or B-bar
route was evaluated. Those alternatives are `RESEARCH_ONLY`; a future
prototype must keep a separate route, prove its formulation and compare
locking benefit against distortion, rank, energy, patch and backward-compatibility
risks. Hourglass control is subordinate to a reduced-integration decision and
is deferred with it.

## Scope and next steps

No element, formulation, mixed-mesh framework or large benchmark was added in
this WP. Existing public maturity is unchanged. The best future element
investment is WEDGE15 after interoperability and V&V foundations are funded;
the lowest-ROI standalone LU2 item is PYRAMID5. These are prioritization
decisions, not implementation commitments.

The gate closes as `PASS_WITH_LIMITATIONS`: the required decisions and future
V&V boundaries are explicit, while deferred and research routes remain absent
from the active qualified registry. WP04's independent supervised retry
remains the next operational action; it is not reclassified by this document.
