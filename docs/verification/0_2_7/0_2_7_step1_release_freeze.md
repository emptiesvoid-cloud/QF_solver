---
doc_id: DOC-027-STEP1
revision: 1.0
status: controlled_release
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Historical 0.2.7 Step 1 release-freeze record

This page records the pre-stable freeze procedure. It is retained for
traceability; the active public release summary is in [the verification index](README.md).

Step 1 converts the owner-approved `0.2.7a0` candidate into the stable
`0.2.7` release identity. The release commit and annotated tag are the single
source for the Step 2 GitHub checks. PyPI publication is deliberately outside
this step.

## Frozen scope

- TET4, TET10, HEX8 and HEX20 retain their documented bounded routes.
- WEDGE6 static remains `EXPERIMENTAL`; WEDGE6 modal remains
  `QUALIFIED_BOUNDED` only for its declared first-three-mode scope.
- 1M, 3M and 5M evidence remains bounded to the recorded structured
  TET4/PETSc/MPI configurations. 5M is Silver; 5M Gold is deferred.
- The 10M C3 result remains bounded `PASS_WITH_LIMITATIONS`; no universal
  scaling, hardware, GPU, nonlinear or mixed-mesh claim is made.
- MPI collective synchronization and structured MPIAIJ preallocation fixes,
  with their guards and provenance, are included.
- Code_Aster remains bounded `PASS_WITH_LIMITATIONS`; CalculiX remains
  `NOT_COMPARABLE` where the formulation and observables are not equivalent.

## Preserved limitations

Mixed meshes, WEDGE15, PYRAMID5, production HEX8R/SRI/B-bar, finite-kinematic
J2, general dynamics/contact, experimental nonlinear and finite-sliding routes,
deeper 10M scaling, 5M Gold, optional HPC routes and directly unverified
macOS/Python combinations are not promoted by this freeze. Historical
`0.2.7a0` audit records and legacy `96/100` views remain available as
provenance and are not treated as the current release state.

## Integrity

The machine-readable record is
[`qualification/0_2_7/step1_release_freeze.json`](../../../qualification/0_2_7/step1_release_freeze.json).
The foreign 0.2.1 documentation change remains isolated in the preserved
targeted stash and is not part of the release candidate. No numerical source,
baseline, maturity decision or historical evidence was changed for the freeze.
