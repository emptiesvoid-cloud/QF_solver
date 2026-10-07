---
doc_id: DOC-ANALYSIS-000
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Analyses

This page maps the cumulative QF Solver 0.2.11 analysis surface. The
experimental rotating routes have their own evidence and are not part of
the immutable 0.2.10 tag or distribution. The
[consolidated 0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
remains authoritative for its 46 element-analysis decisions. Development-cycle
evidence is linked separately and does not rewrite that registry.

| Analysis | Maturity / evidence status | Scope boundary |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Only recorded element/material/load/mesh combinations. |
| Modal | Route-dependent; see registry | Controlled linear eigenvalue cases; mass and family scope vary. |
| Newmark transient | Route-dependent; mixed route `EXPERIMENTAL_BOUNDED` | Linear dynamics only; recorded time-step, mass and damping assumptions apply. |
| Harmonic | Route-dependent; mixed route `EXPERIMENTAL_BOUNDED` | Recorded linear frequency-domain cases only. |
| Linear buckling | Route-dependent | Bounded first-factor cases; not postbuckling or bifurcation analysis. |
| Rotating modal | `EXPERIMENTAL` | One signed speed per solve; serial dense QEP; straight circular-isotropic BEAM2 shaft with centered rigid axisymmetric disks, undamped and unprestressed. See [scope and limitations](../mechanics/rotating-modal.md). |
| Campbell sweep / modal tracking | `EXPERIMENTAL` | Orchestrates explicit ordered speeds through the bounded `rotating_modal` route; complex MAC, global assignment, subspace-aware degeneracy and visible ambiguity. No forced-response or general rotordynamics claim; see [Campbell limits](../mechanics/campbell.md). |
| Small-strain J2 | `QUALIFIED_BOUNDED` | The exact element-analysis combinations in the registry. |
| Corotational J2 | `QUALIFIED_BOUNDED` within accepted scope | HEX8 only; large rotations with small local strains, not general finite-strain plasticity. |
| Total-Lagrangian geometric nonlinear | Audited `GO_WITH_LIMITATIONS`; maturity not promoted | Selected StVK static serial TET4/HEX8 cases. |
| Coupled material/geometric nonlinear | Owner-accepted bounded evidence | Selected static cases across TET4/TET10/HEX8/HEX20; no friction, dynamics, MPI/PETSc or external correlation. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Penalty node-to-triangle bounded route. |
| Frictional contact | Prior Owner-accepted bounded evidence; current-source formal requalification not established | Narrow serial stick/slip route; mesh sensitivity and search limitations remain. |
| Arc-length continuation | Experimental bounded evidence | No general limit-point, bifurcation, or postbuckling claim. |
| PETSc/MPI static | Owner-accepted bounded evidence | Two-rank linear-static one-element cases with replicated input/root-side assembly. |

For element-family boundaries use the [elements map](../elements/index.md).
For nonlinear mechanics see the [mechanics overview](../mechanics/nonlinear-overview.md)
and [capability matrix](../capabilities/index.md). The current
[0.2.11 V&V summary](../verification/0_2_11/README.md) and separate
[0.2.10 evidence](../verification/0_2_10/README.md) distinguish implementation,
verification, bounded acceptance, and physical validation.
