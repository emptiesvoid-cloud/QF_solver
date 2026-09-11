---
doc_id: DOC-029-005
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# Inherited limitations and 0.2.9 boundaries

The following 0.2.8 public boundaries remain in force while 0.2.9 is planned:

- Small-strain J2 is `QUALIFIED_BOUNDED` only in its recorded scope.
- Geometric nonlinear mechanics is `RESEARCH_ONLY`.
- Frictionless penalty node-to-triangle contact is `EXPERIMENTAL_BOUNDED`.
- Mixed distributed PETSc/MPI is `NOT_VALIDATED`; historical structured-TET4
  evidence does not validate the mixed runtime.
- No general finite-strain plasticity, nonlinear contact production, nonlinear
  HPC, finite sliding or surface-to-surface contact claim exists.

Provisional targets are deliberately narrower than implementation ambition:

- TET4/HEX8 geometric nonlinear: `QUALIFIED_BOUNDED` only after all frozen
  gates and Owner review.
- TET10/HEX20 geometric and arc-length/postbuckling: at most
  `EXPERIMENTAL_BOUNDED`.
- Frictional contact: at most `EXPERIMENTAL_BOUNDED`.
- J2 plus geometry: no target until [OD-029-01](owner-decisions.md) is
  resolved; defer remains the safe default.
- Triple material/geometric/contact coupling remains research/feasibility by
  default.
