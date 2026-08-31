---
doc_id: DOC-027-005
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 V&V Strategy

## Evidence vocabulary

The campaign uses the following non-transitive states:

| State | Meaning |
| --- | --- |
| `SUPPORTED` | An implementation route accepts the combination. |
| `TESTED` | At least one declared case was executed. |
| `VERIFIED` | An invariant, analytical oracle or independent reference was checked. |
| `QUALIFIED_BOUNDED` | An Owner decision accepts a declared scope and exclusions. |
| `EXPERIMENTAL` | The route has exploratory evidence but no qualified general claim. |
| `NOT_QUALIFIED` | The route is explicitly excluded from qualified claims. |
| `DEFERRED` | The decision or evidence is intentionally postponed. |

No state is inferred from code presence, test count or a neighboring element.

## Evidence layers

1. **Contract:** machine-readable requirement, capability row, oracle and
   policy exist before execution.
2. **Implementation:** route, element descriptor, loads, faces and post-
   processing behavior are tested in isolation.
3. **Verification:** analytical/invariant, mesh, distortion, replay and
   failure-mode evidence are recorded.
4. **External correlation:** a comparable independent deck is used when one
   exists; incompatible or unavailable tools are explicit skips.
5. **Owner decision:** the accepted maturity, bounded domain and limitations
   are recorded separately from raw results.

## Capability axes

The registry target is:

`element x analysis x material x route x mesh/load convention`

An element descriptor does not authorize every analysis. A WEDGE6 static
result cannot qualify WEDGE6 modal, Newmark, harmonic, J2 or geometric
nonlinearity without their own evidence. Existing TET, HEX, beam, shell and
discrete decisions remain independent.

## Required evidence families

- patch and constant-strain behavior where applicable;
- positive Jacobian, orientation, volume and mesh-quality checks;
- rigid-body and equilibrium invariants;
- analytical oracle with declared assumptions;
- mesh and, where relevant, time/increment/frequency refinement;
- cross-element comparison only on physically comparable models;
- failure and adversarial cases with fail-closed behavior;
- deterministic replay with source and artifact digests;
- external correlation with formulation/observable compatibility recorded;
- resource and performance measurements on declared hardware.

## Scope discipline

The 0.2.7 core proposal does not promote TL HEX8, refined Arc-Length,
finite-kinematic J2, friction/finite sliding/mortar, WEDGE15, PYRAMID5 or
HEX8R. Stretch results may be useful research evidence but remain outside the
bounded release claim unless a separate Owner decision says otherwise.
