---
doc_id: DOC-VV-000
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Verification and evidence

The active 0.2.7 public evidence summary is the canonical entry point:
[verification/0_2_7/README.md](0_2_7/README.md).

Detailed work-package, gate and audit records are retained as traceability
records, not as user-facing product status.

## Acceptance rules for a calculation

A calculation is acceptable within its declared scope when:

1. the input follows the schema and units are explicit;
2. the mesh and boundary conditions are mechanically coherent;
3. the solver converges with a finite residual under the configured threshold;
4. equilibrium, energy and other invariants are compatible;
5. the capability is covered by evidence and an appropriate maturity boundary.

PASS means the programmed criteria pass. WARNING requires a documented
decision. FAIL prevents acceptance. The qualification profile additionally
rejects experimental routes and orphaned evidence.

The active release evidence is bounded by the declared element, analysis,
material, mesh, loading and solver scope. Historical campaign counts remain in
their original records and are not current release metrics.

--8<-- "docs/generated/qualification_status.md"
