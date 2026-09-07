---
doc_id: DOC-028-WP05-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP05 — WEDGE6 static V&V

WP05 audits the `COMB-WEDGE6-linear_static` record identified by WP01 as
`NEEDS_MAJOR_VNV`. The campaign is additive: it does not rewrite any 0.2.7
record, change the numerical source or apply a public maturity relabel.

The frozen contract is
[`wp05_wedge6_contract.json`](../../../qualification/0_2_8/wp05_wedge6_contract.json).
The machine-readable campaign record is
[`wp05_wedge6_vnv.json`](../../../qualification/0_2_8/wp05_wedge6_vnv.json),
and its maturity delta is
[`wp05_maturity_matrix.json`](../../../qualification/0_2_8/wp05_maturity_matrix.json).
The executable campaign is
[`run_wp05_wedge6.py`](../../../scripts/run_wp05_wedge6.py), with focused
checks in
[`test_028_wedge6_static_campaign.py`](../../../tests/verification/test_028_wedge6_static_campaign.py).

## Frozen scope and tolerances

The candidate scope is the existing six-node Gmsh Prism 6 route for linear
static homogeneous isotropic small-strain elasticity. It includes the current
nodal, body/gravity, uniform TRI3 pressure, uniform QUAD4 pressure and
constant surface-traction contracts; conforming prism assembly; reactions,
force/moment equilibrium; displacement, Gauss-point strain/stress and strain
energy recovery.

The production `TRI3_X_GAUSS2` rule is compared with the independent
verification-only Duffy rule. Valid affine, skewed, aspect-ratio and
near-degenerate-warning cases are bounded explicitly. Flat, inverted,
nonfinite, coincident and wrong-order cases remain fail-closed; no automatic
orientation repair is claimed.

The contract freezes the identity, rank, residual, patch, energy and load
resultant limits before execution. External comparison classes retain the
predeclared `1e-6` affine same-mesh and `1e-5` distorted/refinement limits;
their approval state remains `OWNER_REVIEW_REQUIRED`. No threshold was tuned
after observing a result.

## Executed evidence

At baseline `0ad191a41b45283cff53bb461996b08c8dc2739a`, the current replay
lots were deterministic:

- WP07: 8 cases, 7 `PASS`, 1 `EXPECTED_FAILURE_PASS`;
- WP08: 15 cases, 14 `PASS`, 1 `EXPECTED_FAILURE_PASS`;
- WP09 internal: 22 cases, 18 `PASS`, 4 `EXPECTED_FAILURE_PASS`.

Each lot was executed twice and its result digests matched. The elemental
checks passed for partition of unity, derivatives, affine mapping, positive
Jacobian, stiffness symmetry, rank 12, six rigid-body modes, affine strain,
constitutive stress, energy and production/reference quadrature. All five
canonical faces were checked: both TRI3 faces and all three QUAD4 faces.

The multi-element refinement ladder contains one, two and four conforming
prisms. Reactions, free residuals, force balance and moment balance remain
finite and below the frozen internal limits. Post-processing contains six
finite production Gauss-point records with strain and stress values.

## Independent correlation boundary

The controlled 0.2.7 Code_Aster 18.1 PENTA6 artifact is audited by reference,
not rewritten or falsely presented as a new 0.2.8 execution. It contains 12
comparable bounded cases covering affine loads, TRI3/QUAD4 pressure,
prescribed displacement, a conforming multi-element case, one declared
distortion and refinement levels 1, 2 and 4. All 12 primary comparisons pass.
The maximum recorded relative errors are `2.93e-15` for displacement,
`3.60e-15` for total reaction and `2.48e-15` for strain energy against the
predeclared classes. Its external final replay and QF replay both pass.

The inherited CalculiX C3D6 path remains `NOT_COMPARABLE` because its
integration convention differs from QF `TRI3_X_GAUSS2`. No stress
qualification is inferred from either external artifact.

## Technical decision and boundary

The WP05 technical decision is `QUALIFIED_BOUNDED` for the exact static scope
above. The public state remains `EXPERIMENTAL` until a separate Owner gate.
This result does not promote WEDGE6 modal, Newmark or harmonic routes and does
not change the sole 0.2.8 `NOT_QUALIFIED` combination,
`COMB-HEX8-linear_buckling`.

No numerical bug was found or fixed. No file under `src/` or
`qualification/0_2_7/` was changed.
