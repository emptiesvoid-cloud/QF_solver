---
doc_id: DOC-NL-025-015
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 planned known limitations

These are default release boundaries. They may be narrowed by evidence and may
be expanded only through an Owner-reviewed scope/gate revision.

- J2 remains the existing isotropic-hardening small-strain model until an
  explicit finite-kinematic coupling model is approved and verified.
- No general finite-strain plasticity, anisotropic/kinematic hardening, damage,
  fracture, creep, viscoplasticity or cyclic-material qualification is claimed.
- TET4 and HEX8 are the MUST geometric-nonlinear element scope. TET10 and HEX20
  remain SHOULD until their own evidence closes.
- Linear buckling is an idealized bifurcation analysis, not an imperfection-aware
  collapse prediction.
- Linear buckling is qualified only as a bounded first tangent-instability
  analysis: the Euler TET4 total-Lagrangian evidence uses four structured
  levels and the external Code_Aster probe uses a constrained five-TET4 block.
  TET10/HEX8/HEX20 external buckling, imperfection-sensitive collapse and
  post-buckling remain unqualified.
- Arc-length includes a reduced scalar shallow-arch branch-following check, but
  remains bounded to the verified benchmark/problem class; no FEM snap-through,
  post-buckling, arbitrary branch switching or general snap-back behavior is
  implied. The global solver's signed target and `max_steps` turning window
  are opt-in research controls and do not change the default target-load path.
- The finite-kinematic J2 arc-length path has bounded internal research evidence
  on homogeneous TET4, TET10, HEX8 and HEX20 paths up to signed load factor
  `0.5`, using an opt-in adaptive radius. It remains a monotone target-load
  continuation contract; it does not qualify FEM snap-through, snap-back,
  post-buckling, arbitrary branch switching or external response correlation.
- Frictionless contact is the mandatory contact scope. Friction remains optional
  and cannot be advertised unless G07 is promoted and closed.
- The common contact path supports a bounded slave-node patch against a
  triangulated master surface, updated facet search, current-configuration
  normals and penalty enforcement. The patch expands to independent
  node-to-faceted-surface contributions; it is not a mortar or segment-to-
  segment formulation. The internal three-facet traversal and facet-transition
  replay do not qualify general continuum surface-to-surface contact,
  unrestricted finite sliding or external recontact behavior.
- Self-contact, cohesive, thermal and advanced mortar contact are excluded.
- Triple J2+geometry+contact coupling is SHOULD, not a release prerequisite.
- External numerical correlation is not physical validation.
- The regular two-cell Code_Aster J2 campaign is convention-matched and reports
  `PASS_EXTERNAL_CORRELATION` for TET4/TET10/HEX8/HEX20 when the explicit QF
  TET10 `code_aster_5` nonlinear quadrature is selected. The legacy four-point
  Hammer rule remains the default for existing models and linear paths, so
  this bounded evidence does not by itself close G01/G10.
- The release is not an HPC expansion and makes no new million-DOF nonlinear
  claim. PETSc/SLEPc remain optional backends.
- Performance claims are limited to recorded hardware/software/mesh histories.
- Full Newton is the qualified global method. Modified Newton remains outside
  production scope unless separately gated.
- A capability with an OPEN gate remains experimental/research regardless of
  whether code or tests for it exist.

## Coverage provenance note

The apparent change from approximately `88.37 %` to `63.64 %` was a
measurement-environment discrepancy, not a numerical regression. The valid
candidate run used the unit/integration command with `--cov=solveur`,
`--cov-branch`, the configured exclusions (`not benchmark and not large and
not evidence`), and an explicit `PYTHONPATH=src`; it selected `1550` tests,
measured `17867` source statements and reported `88.341 %`. The invalid run
imported `solveur` from the neighbouring `QF_solver_public` checkout because
the source path was not explicit; it measured a different tree (`565` files
and `58861` statements) and reported `63.64 %`. Future release evidence must
record the resolved `solveur.__file__` and the candidate `source_sha`.
