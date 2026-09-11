---
doc_id: DOC-STATE-003
revision: 1.0
status: controlled
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# Known limitations

Every result is bounded by the element family, formulation, mesh quality,
loading, boundary conditions, material model and solver route used to produce
it.

- WEDGE6 static is qualified only within its approved bounded linear-elastic
  scope. WEDGE15 is not supported; PYRAMID5 remains internal/research-only.
- Mixed TET4/WEDGE6/HEX8 static, modal, translational-MPC and multi-material
  workflows have separate bounded qualification records. Mixed Newmark and
  harmonic are experimental bounded. Arbitrary mixed workflows are not
  qualified.
- HEX8-SRI is a separate experimental-bounded locking-sensitive capability;
  it is not locking-free or universally robust. HEX8R, B-bar and general
  hourglass-control production paths remain deferred or research-only.
- Finite-kinematic J2 remains experimental and is not a production claim.
- General nonlinear, contact-with-friction and finite-sliding routes remain
  experimental, bounded or outside the qualified scope.
- 5M Gold and deeper 10M scaling analysis are deferred. The 10M result is a
  bounded C3 capacity/solve observation, not a universal scaling claim.
- Optional PETSc/MPI and SLEPc routes require their external runtimes. Their
  absence must be reported explicitly and does not invalidate core import.
- Mixed PETSc/MPI has architecture evidence only and is `NOT_VALIDATED`: its
  physical force-balance and three-rank runtime gates remain failed.
- The `.inp` reader is a provisional bounded Abaqus/CalculiX subset, not full
  format compatibility. The mixed HDF5 writer/reader is opt-in, requires
  `h5py`, and makes no restart, parallel-HDF5 or general scalability claim.
- Bounded contact is frictionless penalty node-to-triangle small-sliding only;
  it does not cover friction, general finite sliding, impact or self-contact.
- Code_Aster comparisons are limited to comparable recorded cases. CalculiX
  results are `NOT_COMPARABLE` where conventions, integration or observables
  do not match strictly.
- macOS and some declared Python versions are not directly verified locally;
  they are not claimed as tested without CI or reproducible evidence.
- No certification, universal physical validation, industrial equivalence or
  hardware-independent performance claim is made.

For exact element-analysis boundaries, use the
[0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
and the [0.2.8 evidence summary](../verification/0_2_8/README.md). The 0.2.7
records remain available as immutable historical evidence.

For the current cross-registry status, use the [central capability index](../capabilities/index.md).
