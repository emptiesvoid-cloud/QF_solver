---
doc_id: DOC-STATE-002
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Capabilities and maturity

This page is an orientation to the cumulative 0.2.11 solver, not a new qualification
decision. Maturity applies only to a named
scope; implementation or execution alone does not promote it.

| Scope | Status | Boundary |
| --- | --- | --- |
| TET4/TET10/HEX8/HEX20 linear static | `QUALIFIED_BOUNDED` | Recorded combinations in the 0.2.8 registry. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | Exact element-analysis combinations in that registry. |
| Corotational J2 | `QUALIFIED_BOUNDED` within accepted scope | HEX8; large rotations, small local strain; not general finite-strain plasticity. |
| Total-Lagrangian StVK geometry | Audited `GO_WITH_LIMITATIONS`; maturity unchanged | Selected static serial TET4/HEX8 cases only. |
| Coupled nonlinear static | Owner-accepted bounded evidence | Selected TET4/HEX8/HEX20/TET10; no friction, dynamics, MPI/PETSc or external solver correlation. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Penalty node-to-triangle bounded scope. |
| Frictional contact | Owner-accepted bounded evidence; current-source formal requalification not established | Narrow serial route; mesh sensitivity and search limits remain. |
| Arc-length | Experimental bounded evidence | No general bifurcation/postbuckling claim. |
| PETSc/MPI | Owner-accepted bounded evidence | Two-rank linear static with replicated input/root-side assembly; no scaling claim. |
| Code_Aster | Owner-accepted bounded external correlation | Same-mesh linear-static observables for selected families; not physical validation. |
| Mixed PETSc/MPI general workflow | `NOT_VALIDATED` | Architecture evidence does not establish generic distributed execution. |
| Gyroscopic modal analysis | `EXPERIMENTAL` | Straight circular BEAM2 shafts with centered rigid axisymmetric disks; dense serial QEP, no distributed shaft gyro. |
| Campbell diagrams | `EXPERIMENTAL` | Explicit complex-mode tracking; the high-frequency pair at 100 rad/s remains ambiguous. GYRO-06 is internal mesh-convergence evidence, not independent physical validation. |

`QUALIFIED_BOUNDED`, `EXPERIMENTAL_BOUNDED`, Owner-accepted evidence, and an
audit result are distinct labels; this summary preserves the source decision
language. The 46-row historical registry remains unchanged: 32
`QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, and 0 `NOT_QUALIFIED` for its
specified 0.2.8 element-analysis combinations. It is not a current-version score.

Read the [capability matrix](../capabilities/index.md),
[analysis map](../analyses/index.md), [known limitations](limites.md), and
[0.2.11 V&V summary](../verification/0_2_11/README.md) and inherited
[0.2.10 evidence](../verification/0_2_10/README.md) together.
