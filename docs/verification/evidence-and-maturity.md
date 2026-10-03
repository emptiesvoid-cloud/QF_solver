---
doc_id: DOC-VV-MATURITY-028-001
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# Verification, validation, evidence and maturity

**Latest published release:** QF Solver `0.2.8` / `v0.2.8`<br>
**Current source candidate:** `0.2.10`, not yet published

The 0.2.10 candidate accumulates development made since the published 0.2.8
baseline, including the development-only 0.2.9 cycle. The
[candidate V&V summary](0_2_10/README.md) describes the bounded records; the
[capability index](../capabilities/index.md) is the public navigation to
current scopes. The 46-combination
[0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
is historical authority for those published element-analysis decisions and
is not silently rewritten here.

## Four distinct claims

1. **Implementation:** a code path exists.
2. **Verification:** a declared test, invariant, or numerical comparison was
   executed and met its stated checks.
3. **Bounded acceptance / qualification:** a decision explicitly accepts a
   named scope and limitations.
4. **Physical validation:** a model is compared with physical observations.

Passing software tests or comparing against another FEM solver is not, by
itself, physical validation. An Owner-accepted experimental record remains
experimental if that is what the decision says. Maturity labels must not be
upgraded merely because an implementation or evidence pack exists.

## Evidence chain

A bounded campaign records a prospective scope and gates, a frozen execution,
results and source/environment provenance, independent checks and their
limitations, replay where applicable, fail-closed behavior, and a final
decision record. Historical failures and superseded dispositions remain
preserved; they are not rewritten to match a later desired outcome.

## Maturity vocabulary

| Label | Meaning |
| --- | --- |
| `QUALIFIED_BOUNDED` | The declared combination passed its frozen qualification gates within the recorded scope; it is not universal. |
| `EXPERIMENTAL_BOUNDED` | A usable route with limited evidence and explicit restrictions, not a general qualified capability. |
| `EXPERIMENTAL` | Exploratory or partially verified evidence is insufficient for bounded qualification. |
| `RESEARCH_ONLY` | Discovery or feasibility work; no public supported-use claim. |
| `NOT_VALIDATED` | The implementation or architecture may exist, but required validation gates did not pass or were not run. |
| `INTERNAL` | Retained for development and traceability, not a public supported route. |
| `GO_WITH_LIMITATIONS` | An audit disposition for its declared campaign; it is not automatically a maturity promotion. |

The 0.2.8 registry counts remain 32 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`,
and 0 `NOT_QUALIFIED` across 46 specified combinations. These counts are not a
0.2.10 quality score and exclude separate mixed workflows and capability
records.

## Candidate boundaries

- Small-strain J2 and the 0.2.8 linear registry retain their original bounded
  scopes.
- Corotational J2 has an Owner-accepted bounded HEX8 scope with large rotations
  and small local strain; no general finite-strain claim follows.
- The Total-Lagrangian StVK audit covers selected serial static TET4/HEX8 cases
  and states `GO_WITH_LIMITATIONS` without maturity promotion.
- Coupled nonlinear Owner acceptance is limited to selected static TET4,
  TET10, HEX8, and HEX20 evidence. It excludes friction, dynamics, MPI/PETSc,
  external solver correlation, and independent global FEM/Newton solution.
- Frictionless contact remains experimental. Frictional contact evidence is
  narrow, mesh-sensitive, and not formally requalified against the current
  source.
- PETSc/MPI acceptance is limited to two-rank linear-static cases with
  replicated input/root-side assembly. No general nonlinear distributed or
  scaling claim follows.
- Code_Aster evidence is bounded same-mesh linear-static numerical correlation
  for recorded observables, not physical validation.
- WP14 remains HOLD while the whole-repository G03 archive scan is failed.
  Package-scoped checks do not waive that gate.

The detailed development-cycle records remain in
[`qualification/0_2_9`](https://github.com/emptiesvoid-cloud/QF_solver/tree/main/qualification/0_2_9).
They are engineering evidence, not user-level replacements for the concise
scope statements above.
