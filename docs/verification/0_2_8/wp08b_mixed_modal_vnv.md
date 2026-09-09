---
doc_id: DOC-028-WP08B-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP08B mixed modal follow-up

WP08B starts from `59a438bc0d58ee32d35e084dd091eefe78418bb6`. It preserves the
WP08 decision, `SUPPORTED_WITH_LIMITATIONS`, and does not rewrite WP08 or
0.2.7 evidence. The diagnostic is recorded in the
[`root-cause audit`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_root_cause_audit.json),
followed by the separate predeclared
[`WP08B contract`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_mixed_modal_contract.json),
executable [`WP08B evidence`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_mixed_modal_vnv.json)
and [`WP08B matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_mixed_modal_matrix.json).

## Root cause

The WP08 runner selected fixed element rows `0`, `1` and `2` for every
refinement level. At levels above one, that retained only the first WEDGE6 and
HEX8 segment: the model stayed at 33 DDL while its total volume changed from
approximately `1.667` to `0.917`, `0.542` and `0.354`. These are different
mechanical domains, not a mesh-refinement sequence. The shared-node MAC was
therefore not a valid convergence comparison.

The root cause is `MESH_TO_MESH_MAPPING_PROBLEM`, with a secondary
`GEOMETRIC_DISCRETIZATION_EFFECT`. It is not evidence of modal-solver
nonconvergence, an eigenvector-normalization defect, a mixed-mode crossing, or
a MAC implementation defect. The original WP08 threshold and failed result
remain intact.

## Predeclared follow-up method

Each WP08B level retains one TET4 and every generated WEDGE6 and HEX8 segment.
The physical volume and coordinate bounds are invariant; node/DDL counts grow
from `11/33` at level one to `46/138` at level eight. Coarse modal fields are
prolonged to every fine-mesh node through the containing coarse element's
linear shape functions. The full MAC matrix is then evaluated with the fine
global consistent mass matrix, and the maximum-total-MAC assignment is
recorded. No extrapolation is allowed.

The new contract predeclares `MAC ≥ 0.85` and an adjacent matched-frequency
change of at most `10%`; it does not alter the WP08 `0.5` gate. Numerically
degenerate pure-family control modes are compared as mass-orthonormal
subspaces. The mixed candidate modes are individually matched because no
near-degenerate group is found in the first six modes.

## Results

All mixed gates pass. The minimum assigned mapped MAC values for levels
`1→2`, `2→4` and `4→8` are `0.9751`, `0.9037` and `0.9979`; every assignment
is mode `i → i`. The largest adjacent matched-frequency change is about
`5.86%`, below the predeclared bound. Mass conservation, independent dense
assembly/eigensolve correlation, eigenpair residuals, mass orthogonality,
interface/failure contracts, output and two deterministic replays also pass.

Pure TET4, WEDGE6 and HEX8 refinements are retained as protocol controls only.
They show expected coarse/high-mode sensitivity and, for HEX8, near-degenerate
subspaces; they do not alter any individual-family modal maturity state.

## Technical candidate and limitations

WP08B yields **`QUALIFIED_BOUNDED_CANDIDATE`** for the exact fixed-base
conforming TET4/WEDGE6/HEX8 chain, small-strain homogeneous linear isotropic
elasticity, consistent translational mass and the first six positive modes at
the declared levels. A separate Owner gate is required before any public
promotion.

The independent oracle is a separately scattered dense generalized eigensolve,
not an external industrial-solver correlation. There is no modal-stress,
Newmark, harmonic, nonlinear, contact, nonconforming-interface, higher-order
family, large-model performance or universal modal claim. WP09 is not started
by this record.
