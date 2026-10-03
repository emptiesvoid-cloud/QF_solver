---
doc_id: DOC-CAPABILITY-028-001
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# QF Solver capability index — 0.2.10

**Current release:** `0.2.10` / `v0.2.10`

This index describes evidence available for QF Solver 0.2.10 without changing
previous maturity decisions. In particular, source implementation and a
successful test do not by themselves establish qualification.

## How to read the statuses

`QUALIFIED_BOUNDED` refers only to a recorded element/analysis/material scope.
`EXPERIMENTAL_BOUNDED` means the route has limited evidence but is not a
general qualified capability. “Owner-accepted bounded evidence” is reported
as such and is not silently relabeled `QUALIFIED_BOUNDED`. “Audited; maturity
not promoted” means a technical audit exists but no maturity promotion was
recorded. The 46-case registry remains the authority for its original 0.2.8
scope and counts; this 0.2.10 index does not rewrite it.

## Capability matrix

| Domain | Capability | Maturity / evidence status | Scope and limitation |
| --- | --- | --- | --- |
| Linear | TET4, TET10, HEX8, HEX20 | `QUALIFIED_BOUNDED` — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Recorded elastic element/analysis combinations only; read the registry row and route boundary. |
| Linear | WEDGE6 static | `QUALIFIED_BOUNDED` — [WP05 Owner record](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/wp05_owner_gate_final.json) | Gmsh Prism 6, bounded isotropic small-strain static scope. |
| Dynamics | Modal | Route-dependent — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Controlled linear eigenvalue cases; mass formulation and family coverage vary by route. |
| Dynamics | WEDGE6 modal | `QUALIFIED_BOUNDED` — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Homogeneous isotropic consistent-mass route; first three modes in the declared refinement scope. |
| Dynamics | Newmark | Route-dependent / mixed route experimental — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Linear transient scope only; timestep, damping and mass assumptions apply. |
| Dynamics | Harmonic | Route-dependent / mixed route experimental — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Recorded linear frequency-domain cases; no general nonlinear transient claim. |
| Material NL | Small-strain J2 | `QUALIFIED_BOUNDED` — [registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json) | Recorded homogeneous constitutive cases and element combinations only. |
| Geometric NL | Total-Lagrangian StVK | Audited `GO_WITH_LIMITATIONS`; maturity not promoted — [audit](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/wp04f/wp04_final_closure_audit.json) | Selected static serial TET4/HEX8 cases within explicit deformation/formulation bounds; excludes contact, dynamics, MPI/PETSc and high-order routes. |
| Coupled NL | Material + geometry | Owner-accepted bounded evidence — [WP10 decision](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/wp10_owner_acceptance.json) | Selected static cases across recorded families; not frictional contact, dynamics, Code_Aster correlation or MPI. |
| J2 rotations | Corotational J2 | `QUALIFIED_BOUNDED` within accepted scope — [Owner decision](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/owner_decisions.json) | HEX8 route; large rotations with small local strains. Not general multiplicative finite-strain plasticity. |
| Contact | Frictionless penalty | `EXPERIMENTAL_BOUNDED` — [capability record](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/wp13_07d_contact_capability_record.json) | Node-to-triangle, penalty, bounded small-sliding cases; not self-contact or impact dynamics. |
| Contact | Frictional stick/slip | Owner-accepted bounded evidence; current-source formal requalification not established — [progress and limitations](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/progress.json) | Narrow serial route; mesh sensitivity remains; no general updated search or finite sliding. |
| Continuation | Adaptive increments / cutback | Bounded route evidence — [WP03 records](https://github.com/emptiesvoid-cloud/QF_solver/tree/main/qualification/0_2_9) | Full Newton, line search, stagnation and retry mechanisms are not a guarantee of convergence for arbitrary models. |
| Continuation | Arc-length | Experimental bounded evidence — [WP06 decision](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/wp06d_owner_bounded_experimental_decision.json) | No general bifurcation or postbuckling capability claim. |
| HPC | PETSc/MPI | Owner-accepted bounded evidence — [WP11 decision](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/wp11_owner_acceptance_r2.json) | Two-rank linear-static cases with replicated input and root-side assembly; no scaling or nonlinear distributed claim. |
| HPC | Distributed mixed PETSc/MPI runtime | `NOT_VALIDATED` — [historical runtime limits](../verification/0_2_8/README.md) | Development-cycle bounded linear evidence does not close generic mixed distributed gates. |
| Large model | Structured TET4 PETSc route | Route-dependent historical evidence — [limitations](../etat/limites.md) | Exact workload/environment only; not general scaling or hardware-independent performance. |
| External correlation | Code_Aster 18.1 | Owner-accepted bounded correlation — [WP12 decision](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_9/wp12_owner_acceptance_r2.json) | Same-mesh, linear-static and comparable observables; not physical validation or general nonlinear correlation. |

For the nonlinear architecture see the [mechanics overview](../mechanics/nonlinear-overview.md).
For concrete route restrictions see [known limitations](../etat/limites.md).
For test and evidence interpretation see the [0.2.10 V&V summary](../verification/0_2_10/README.md).

## Registry boundary

The consolidated 0.2.8 registry contains 46 element-analysis combinations:
32 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, and 0 `NOT_QUALIFIED`. These are
historical, scoped counts—not a 0.2.10 score and not a count of every separate
workflow above. Mixed workflows, mechanics evidence, and external correlation
remain separate records. WP14 is on HOLD while the whole-repository G03 scan
is failed; the selected-package audit does not waive or clear that gate.
