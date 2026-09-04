---
doc_id: DOC-STATE-003
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Known limitations

Every result is bounded by the element family, formulation, mesh quality,
loading, boundary conditions, material model and solver route used to produce
it.

- WEDGE6 static is experimental. WEDGE15 and PYRAMID5 are not supported.
- Mixed TET/WEDGE/HEX end-to-end workflows are not qualified.
- HEX8R, SRI, B-bar and hourglass-control production paths are deferred or
  research-only.
- Finite-kinematic J2 remains experimental and is not a production claim.
- General nonlinear, contact-with-friction and finite-sliding routes remain
  experimental, bounded or outside the qualified scope.
- 5M Gold and deeper 10M scaling analysis are deferred. The 10M result is a
  bounded C3 capacity/solve observation, not a universal scaling claim.
- Optional PETSc/MPI and SLEPc routes require their external runtimes. Their
  absence must be reported explicitly and does not invalidate core import.
- Code_Aster comparisons are limited to comparable recorded cases. CalculiX
  results are `NOT_COMPARABLE` where conventions, integration or observables
  do not match strictly.
- macOS and some declared Python versions are not directly verified locally;
  they are not claimed as tested without CI or reproducible evidence.
- No certification, universal physical validation, industrial equivalence or
  hardware-independent performance claim is made.

For exact boundaries, use the [active capability matrix](../verification/0_2_7/0_2_7_capability_matrix.md)
and the [0.2.7 evidence summary](../verification/0_2_7/README.md).
