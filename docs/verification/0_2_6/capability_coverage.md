# Capability Coverage Register

This generated view is derived from `qualification/capability_registry.json`, the controlled source of truth. Code presence is never interpreted as qualification.

## Baseline

- Registry: `QF-SOLVER-CAPABILITY-REGISTRY`
- Historical qualified source: `8047fb63c420609b510beaa1e30aa3ab31d9ad87`
- Capability count: 33; public mappings: 33
- Public element-analysis combinations: 44
- V&V distribution: L0=0, L1=3, L2=14, L3=16

## Maturity Meaning

- **L0**: code/inventory only. **L1**: executable smoke or route evidence. **L2**: quantitative verification. **L3**: bounded qualification backed by recorded evidence.
- `EXPERIMENTAL`, `RESEARCH`, and `NOT_IN_RELEASE_SCOPE` remain visible even when code and historical tests exist.

## Capability To Gate Matrix

| ID | Domain | Element | Analysis | Maturity | V&V | 0.2.6 gate/WP | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ELE-BEAM2` | ELEMENT | BEAM2 | static/modal/Newmark/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-MITC3` | ELEMENT | MITC3 | static/modal/Newmark/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-MITC4` | ELEMENT | MITC4 | static/modal/Newmark/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-TET4` | ELEMENT | TET4 | static/modal/Newmark/harmonic/buckling/nonlinear | QUALIFIED_BOUNDED | L3 | `026-G04/G05/G06/G07/G08` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-TET10` | ELEMENT | TET10 | static/modal/Newmark/harmonic/buckling/nonlinear | QUALIFIED_BOUNDED | L3 | `026-G04/G05/G06/G07/G08` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-HEX8` | ELEMENT | HEX8 | static/modal/Newmark/harmonic/buckling/nonlinear | QUALIFIED_BOUNDED | L3 | `026-G04/G05/G06/G07/G08` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-HEX20` | ELEMENT | HEX20 | static/modal/Newmark/harmonic/buckling/nonlinear | QUALIFIED_BOUNDED | L3 | `026-G04/G05/G06/G07/G08` | PRESENT_REQUALIFICATION_PENDING |
| `ELE-DISCRETE` | ELEMENT | discrete spring/mass | static/modal/Newmark/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_REQUALIFICATION_PENDING |
| `INF-RBE-CONSTRAINTS` | INFRASTRUCTURE | RBE2/RBE3 constraints | static/modal/dynamic where admissible | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_GAP_RECORDED |
| `ANA-STATIC` | ANALYSIS | multiple | linear_static | QUALIFIED_BOUNDED | L3 | `026-G04` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-MODAL` | ANALYSIS | multiple | modal | QUALIFIED_BOUNDED | L3 | `026-G05` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-NEWMARK` | ANALYSIS | multiple | transient_dynamic | QUALIFIED_BOUNDED | L3 | `026-G05` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-HARMONIC` | ANALYSIS | multiple | harmonic_response | QUALIFIED_BOUNDED | L3 | `026-G05` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-BUCKLING` | ANALYSIS | solid families | linear_buckling | QUALIFIED_BOUNDED | L3 | `026-G08` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-NONLINEAR-LOAD` | ANALYSIS | solid/contact-supported models | nonlinear_static | EXPERIMENTAL | L2 | `026-G06/G09` | PRESENT_DEFERRED |
| `ANA-GEOMETRIC-NONLINEAR` | ANALYSIS | solid families | geometric_nonlinear_static | EXPERIMENTAL | L2 | `026-G07` | PRESENT_REQUALIFICATION_PENDING |
| `ANA-ARC-LENGTH` | ANALYSIS | TET4 bounded benchmark | arc_length | EXPERIMENTAL | L2 | `026-G07` | EXPERIMENTAL_NOT_QUALIFIED |
| `MAT-ELASTIC` | MATERIAL | multiple | all linear analyses | QUALIFIED_BOUNDED | L3 | `026-G04` | PRESENT_REQUALIFICATION_PENDING |
| `MAT-ORTHOTROPIC-LAMINATE` | MATERIAL | MITC3/MITC4/solids where supported | static/modal/Newmark/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_DEFERRED |
| `MAT-J2-SMALL` | MATERIAL | TET4/TET10/HEX8/HEX20 | nonlinear_static | QUALIFIED_BOUNDED | L3 | `026-G06` | PRESENT_QUALIFIED_BOUNDED |
| `MAT-TL-ELASTIC` | MATERIAL | TET4/HEX8 bounded; high-order research | geometric_nonlinear_static | QUALIFIED_BOUNDED | L3 | `026-G07` | PRESENT_REQUALIFICATION_PENDING |
| `MAT-FINITE-J2` | MATERIAL | TET4/TET10/HEX8/HEX20 | geometric_nonlinear_static | RESEARCH | L1 | `026-G10` | RESEARCH_DEFERRED |
| `MAT-COUPLED-NL` | MATERIAL | bounded solid/contact workflows | coupled nonlinear | EXPERIMENTAL | L1 | `026-G10` | EXPERIMENTAL_DEFERRED |
| `CON-FRICTIONLESS` | CONTACT | bounded node-to-triangle/contact models | nonlinear/geometric nonlinear | QUALIFIED_BOUNDED | L3 | `026-G09` | PRESENT_REQUALIFICATION_PENDING |
| `CON-FRICTION` | CONTACT | bounded contact models | nonlinear contact | RESEARCH | L1 | `NOT_IN_RELEASE_SCOPE` | NOT_IN_RELEASE_SCOPE |
| `INF-MESH-GMSH` | INFRASTRUCTURE | multiple | model import | EXPERIMENTAL | L2 | `026-G04` | PRESENT_DEFERRED |
| `INF-LOADS-BC` | INFRASTRUCTURE | multiple | all supported analyses | EXPERIMENTAL | L2 | `026-G04` | PRESENT_DEFERRED |
| `INF-POST` | INFRASTRUCTURE | multiple | static/modal/dynamic/harmonic | EXPERIMENTAL | L2 | `026-G04/G05` | PRESENT_DEFERRED |
| `INF-SPARSE-SCIPY` | INFRASTRUCTURE | multiple | linear and eigen paths | QUALIFIED_BOUNDED | L3 | `026-G04/G12` | PRESENT_REQUALIFICATION_PENDING |
| `INF-PETSC-SLEPC` | INFRASTRUCTURE | large sparse/modal paths | PETSc/SLEPc optional backends | EXPERIMENTAL | L2 | `026-G05/G12` | PRESENT_DEFERRED |
| `INF-DIAGNOSTICS-FAILURES` | INFRASTRUCTURE | multiple | solver/failure paths | QUALIFIED_BOUNDED | L3 | `026-G11` | PRESENT_QUALIFIED_BOUNDED |
| `INF-PERF-SCALING` | INFRASTRUCTURE | large TET4 and bounded solid benchmarks | assembly/solve performance | QUALIFIED_BOUNDED | L3 | `026-G12` | PRESENT_REQUALIFICATION_PENDING |
| `INF-EXTERNAL-CORRELATION` | INFRASTRUCTURE | multiple | verification adapters | EXPERIMENTAL | L2 | `026-G13` | PRESENT_DEFERRED |

## Element x Analysis Coverage

| Family | Static | Modal | Newmark | Harmonic | Buckling | Load-control | Geometric | 0.2.6 gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BEAM2 | code/tests | G05-B verified | G05-B verified | G05-B verified | n/a | n/a | n/a | G05 bounded; other scopes separate |
| MITC3 | READY corpus | G05-B verified | G05-B verified | G05-B verified | n/a | n/a | n/a | external deck pending |
| MITC4 | READY corpus | G05-B verified | G05-B verified | G05-B verified | n/a | n/a | n/a | external deck pending |
| TET4 | READY corpus | G05-B verified | G05-B verified | G05-B verified | READY/planned | READY | bounded evidence | external coverage bounded |
| TET10 | READY/planned | G05-B verified | G05-B verified | G05-B verified | planned | READY/planned | research route | external deck pending |
| HEX8 | READY/planned | G05-B verified | G05-B verified | G05-B verified | planned | READY/planned | bounded evidence | external deck pending |
| HEX20 | READY/planned | G05-B verified | G05-B verified | G05-B verified | planned | READY/planned | research route | external deck pending |
| Discrete | READY/planned | G05-B verified | G05-B verified | G05-B verified | n/a | n/a | n/a | G05 bounded; other scopes separate |

## G05-B Integration And Open Gaps

- `G05-B` is supplemented by an all-family campaign with MOD 14, DYN 32 and HAR 12 controlled cases. The Owner closed `026-G05` as `PASS_WITH_LIMITATIONS`.
- The family campaign executes MOD 14, DYN 32 time-level cases and HAR 12 across all eight requested family rows. See `0_2_6_g05_family_coverage.md`; external correlation remains bounded.
- The G05-B family campaign covers TET4, TET10, HEX8, HEX20, BEAM2, MITC3/MITC3+, MITC4 and discrete; refinement policies are OWNER_APPROVED_BOUNDED and the Owner closed G05 as PASS_WITH_LIMITATIONS.
- The modal mesh, Newmark time-refinement, and harmonic frequency-refinement policies are `OWNER_APPROVED_BOUNDED`; their closeout is recorded in `owner_decisions.json`.

## Historical Continuity

All capabilities tracked from 0.2.5a0 remain represented. No historical capability is silently retired. Historical tests that have not yet been mapped into a 0.2.6 READY case are recorded as explicit gaps, rather than treated as lost evidence or a current qualification claim.

| Capability | Historical reference | Current maturity | Continuity assessment |
| --- | --- | --- | --- |
| `ELE-BEAM2` | 0.2.6 supplemental/current | EXPERIMENTAL | present; no silent maturity downgrade |
| `ELE-MITC3` | 0.2.6 supplemental/current | EXPERIMENTAL | present; no silent maturity downgrade |
| `ELE-MITC4` | 0.2.6 supplemental/current | EXPERIMENTAL | present; no silent maturity downgrade |
| `ELE-TET4` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ELE-TET10` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ELE-HEX8` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ELE-HEX20` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ELE-DISCRETE` | 0.2.6 supplemental/current | EXPERIMENTAL | present; no silent maturity downgrade |
| `INF-RBE-CONSTRAINTS` | 0.2.5 recorded | EXPERIMENTAL | explicit 0.2.6 mapping gap |
| `ANA-STATIC` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ANA-MODAL` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ANA-NEWMARK` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ANA-HARMONIC` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ANA-BUCKLING` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `ANA-NONLINEAR-LOAD` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `ANA-GEOMETRIC-NONLINEAR` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `ANA-ARC-LENGTH` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `MAT-ELASTIC` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `MAT-ORTHOTROPIC-LAMINATE` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `MAT-J2-SMALL` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `MAT-TL-ELASTIC` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `MAT-FINITE-J2` | 0.2.6 supplemental/current | RESEARCH | present; no silent maturity downgrade |
| `MAT-COUPLED-NL` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `CON-FRICTIONLESS` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `CON-FRICTION` | 0.2.5 recorded | RESEARCH | present; no silent maturity downgrade |
| `INF-MESH-GMSH` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `INF-LOADS-BC` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `INF-POST` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `INF-SPARSE-SCIPY` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `INF-PETSC-SLEPC` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |
| `INF-DIAGNOSTICS-FAILURES` | 0.2.6 supplemental/current | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `INF-PERF-SCALING` | 0.2.5 recorded | QUALIFIED_BOUNDED | present; no silent maturity downgrade |
| `INF-EXTERNAL-CORRELATION` | 0.2.5 recorded | EXPERIMENTAL | present; no silent maturity downgrade |

No capability is removed, renamed, or retired in this foundation registry. Any future removal must enter `retired_capabilities` with a rationale and retained evidence reference; the audit otherwise fails.

| Release | SHA | Element inventory | Analysis routes |
| --- | --- | --- | --- |
| `v0.2.0-alpha` | `1804a03aee0c4e4bc6ac2c56e9461bedd9aac6d4` | BEAM2, MITC3, MITC4, TET4, TET10 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, transient_dynamic, harmonic_response |
| `v0.2.1-alpha` | `ccaef9c7572f47a80998d5bcb119393e4d05dd8f` | BEAM2, MITC3, MITC4, TET4, TET10 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, transient_dynamic, harmonic_response |
| `v0.2.2a0` | `0b0a9d4437d78406aa7737cf5bd1f7dd00c6ffe9` | BEAM2, MITC3, MITC4, TET4, TET10 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, transient_dynamic, harmonic_response |
| `v0.2.3a0` | `d401b80635105d9df47c57d9bdd30020a71683a2` | BEAM2, MITC3, MITC4, TET4, TET10, HEX8, HEX20 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, transient_dynamic, harmonic_response |
| `v0.2.4a0` | `e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` | BEAM2, MITC3, MITC4, TET4, TET10, HEX8, HEX20 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, transient_dynamic, harmonic_response |
| `v0.2.5a0` | `1e6c3e96d1e1366c4cc790546e82769cd9227902` | BEAM2, MITC3, MITC4, TET4, TET10, HEX8, HEX20 | linear_static, modal, nonlinear_static, geometric_nonlinear_static, linear_buckling, transient_dynamic, harmonic_response |

The audit reads these release sources directly from Git. It fails if the recorded historical inventory changes, if a released family or route disappears without a retirement record, or if the current source adds an element family or analysis route without a registry entry.

## Anti-Forgetting Contract

`scripts/audit_capability_registry.py --check` fails on duplicate IDs, missing required fields, orphan public claims, unregistered source sentinels, silent historical removal, or an implemented capability lacking a test, gate, or limitation justification. It intentionally does not require L3 for every capability.
