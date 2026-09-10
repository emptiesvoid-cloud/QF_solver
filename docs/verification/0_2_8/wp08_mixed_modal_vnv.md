---
doc_id: DOC-028-WP08-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP08 mixed modal V&V

WP08 audits one bounded mixed modal workflow using `TET4 + WEDGE6 + HEX8`,
starting from `65c816fee4a1497dd320358565a297c01bfcaff5`. It does not rewrite
0.2.7 evidence, the WP07 static decision, or the element-analysis registry.
The frozen campaign contract is the
[`WP08 contract`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08_mixed_modal_contract.json);
the executable machine-readable result is the
[`WP08 evidence`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08_mixed_modal_vnv.json);
and the decision matrix is the
[`WP08 matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08_mixed_modal_matrix.json).

## Scope and architecture audit

The existing global assembly already provides family-generic stiffness and
consistent translational mass assembly through the shared-node DOF map. The
modal route solves the reduced generalized eigenproblem with the consistent
mass formulation. Lumped finite-element mass is not a supported qualification
route for this campaign. The WEDGE6 modal route remains outside the existing
publicly qualified element-analysis states; WP08 therefore audits the mixed
workflow separately and does not relabel any historical combination.

The only demonstrated implementation gap was that the existing mixed
conforming-interface validation contract was invoked for `linear_static` but
not for `modal`. WP08 adds that validation dispatch and its regression/failure
coverage. No element matrix, mass formulation, modal solver or numerical
kernel was changed.

## Candidate scope

The tested scope is `modal`, fixed-base small-strain linear isotropic
elasticity, homogeneous positive-density material, consistent translational
finite-element mass, and conforming shared-node triangular and quadrilateral
interfaces between TET4, WEDGE6 and HEX8. It covers the first six positive
modes in the explicitly tested pairwise and three-family cases.

The campaign excludes lumped or concentrated mass qualification, Newmark,
harmonic, nonlinear, contact, nonconforming interfaces, hanging nodes,
MPC/RBE transitions, TET10/HEX20 mixed meshes, PYRAMID5, large mixed-model
performance and any universal all-frequency claim. No modal stress claim is
made.

## Campaign gates

The tolerances were frozen in the contract before the campaign and were not
retuned after observing results. The campaign records:

- symmetric positive consistent mass, density/volume conservation, directional
  mass conservation and unique shared-node DOFs;
- TET4-WEDGE6, WEDGE6-HEX8 and TET4-WEDGE6-HEX8 modal cases;
- residuals, mass orthogonality, unit generalized-mass normalization, sorted
  frequencies, family labels and JSON output;
- an independent dense oracle that reassembles local K/M arrays separately and
  solves with `scipy.linalg.eigh`, without calling the production modal solver
  or production global matrix path;
- pure-family versus mixed diagnostics without an equality claim between
  different discretizations, including subspace MAC handling for numerically
  degenerate eigenvalue clusters;
- explicit rejection of invalid connectivity, invalid geometry, disconnected
  families and nonconforming duplicate-node interfaces;
- two deterministic replays with eigenvector sign canonicalization only.

All of those gates pass for the tested mixed cases. No external industrial
solver result was available; no external correlation is claimed. The bounded
dense oracle is sufficient to verify the local-matrix scatter and generalized
eigenpair contract, but it does not establish external solver correlation.

## Refinement result and technical decision

The three tested refinement levels have first frequencies of approximately
`779.297`, `665.952` and `587.201` Hz. The adjacent relative changes pass the
predeclared frequency-step bound. However, shared-node matching of the first
six modes gives minimum MAC values of approximately `0.1028` and `0.7312` for
the two transitions, so the predeclared `0.5` mode-matching gate fails at the
first transition.

This is not hidden by changing the tolerance or by reordering modes. The
technical result is therefore **`SUPPORTED_WITH_LIMITATIONS`**, not
`QUALIFIED_BOUNDED_CANDIDATE`; no public promotion and no Owner gate are
applied. The result is not a general modal convergence claim. A future
campaign would need a new predeclared refinement/mode-matching design and
evidence before reconsidering qualification.

The independent pairwise and three-family modal checks remain reproducible and
bounded, but they do not override the failed refinement gate. WP08 does not
start WP09 or any other work package.
