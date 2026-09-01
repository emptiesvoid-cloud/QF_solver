---
doc_id: DOC-027-012
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Risk Register

| ID | Risk | Impact | Mitigation | STOP trigger | Owner |
| --- | --- | --- | --- | --- | --- |
| R027-01 | 0.2.6 historical evidence is mistaken for 0.2.7 execution | false release claim | separate SHA, version and evidence heads | active record has no provenance class | Owner |
| R027-02 | registry v2 infers maturity from source presence | overclaim | require evidence and Owner status per combination | orphan or duplicate public row | Quality |
| R027-03 | descriptor/preflight changes default behavior | numerical/API regression | additive path, negative tests and checkpoint replay | default result changes | Solver/Owner |
| R027-04 | V&V harness refactor loses old evidence | provenance loss | leave old 188-module corpus intact and compare manifests | missing historical artifact | Quality |
| R027-05 | C3D6/PENTA6 is not formulation-compatible | false external validation | preflight node order, kinematics and observables | ambiguous mapping | V&V |
| R027-06 | WEDGE6 scope grows into mixed meshes/new physics | schedule and validation risk | static vertical slice and explicit exclusions | unreviewed scope expansion | Solver |
| R027-07 | mesh quality reduced to aspect ratio | invalid domain claim | multidimensional diagnostics and Owner policy | universal cutoff proposed | V&V |
| R027-08 | low-order locking is treated as a bug fix target | unjustified formulation change | diagnostic comparison and separate formulation study | threshold weakened to pass | Solver/Owner |
| R027-09 | 1M benchmark becomes a marketing claim | misleading scaling | hardware/topology/resource verdicts | no resource context | Performance |
| R027-10 | stretch work blocks the bounded core | release drift | optional WP13 with independent decision | research route enters core claim | Owner |
| R027-11 | full regression runs too frequently or too late | wasted time or late regression | T0-T3 policy and declared checkpoints | no checkpoint after cross-cutting change | Quality |
| R027-12 | release metadata drifts from package/tag | unusable artifact | WP01 and WP14 exact version checks | version mismatch | Release |

## Level-Up risks

| ID | Risk | Impact | Mitigation | STOP trigger | Owner |
| --- | --- | --- | --- | --- | --- |
| R027-LU-01 | 1M or 3M size is reported without a real FEM solve | false scaling claim | WP16 true-DOF contract and WP18 Bronze/Silver/Gold separation | assembly-only result presented as solve | Performance |
| R027-LU-02 | matrix-free or preconditioned path changes numerical behavior | loss of trust | assembled subscale equivalence, residual and replay evidence | unexplained drift | Solver/Quality |
| R027-LU-03 | PETSc/MPI availability is mistaken for supported production capability | irreproducible release | pin environment and classify unavailable routes explicitly | missing runtime provenance | Performance |
| R027-LU-04 | HEX8 diagnostic becomes an unreviewed formulation project | scope and numerical risk | diagnostic-first WP19 and defer production HEX8R/SRI/B-bar | threshold weakening or kernel change | Solver/Owner |
| R027-LU-05 | portfolio weight/progress numbers are treated as evidence | governance confusion | keep accounting fields separate and require WP evidence | planned work marked PASS | Owner |
