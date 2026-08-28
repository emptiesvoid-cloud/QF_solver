---
doc_id: DOC-NL-025-004
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 work packages

## Dependency graph

```text
WP0 -> WP1 -> WP2 -> WP3
              |      |
              |      `-> WP4
              `-> WP5 -> WP6 -> WP7 (optional Owner GO)

WP1..WP6 -> WP8 profiling
WP1..WP7 -> WP9 adversarial
WP1..WP7 -> WP10 external correlation
WP8..WP10 -> WP11 full regression -> WP12 Owner pack
```

WP3 and WP4 may proceed independently after WP2. WP5 requires WP2 because
finite-sliding contact must use the approved geometric state and common Newton.

## WP0 - Audit, provenance and baseline freeze

**Objective:** freeze the published 0.2.4 behavior and final architecture map.

**Likely files:** planning/evidence documents, benchmark runners, no numerical
source unless a later approved WP begins.

**Steps:** reconcile stale 0.2.4 gate provenance; record start SHA; archive test,
coverage, V&V, convergence and performance baselines; inventory every public and
internal nonlinear path; freeze API and numerical snapshots.

**Tests/evidence:** complete 0.2.4 release suite, exact artifact digests, benchmark
environment and repeated timing protocol.

**Acceptance:** reproducible baseline tied to one SHA; no unexplained failing
gate; architecture and qualification states reviewed.

**Gate:** `025-G00`. **STOP:** any unreconciled release provenance or baseline
failure. **GO:** Owner approves the frozen audit.

## WP1 - Close 0.2.4 nonlinear V&V debt

**Objective:** prove the existing J2 engine beyond affine one-element evidence.

**Likely files:** nonlinear verification tests, benchmark registry/runners,
evidence builders and documentation; constitutive code only for a verified bug.

**Steps:** multi-element common mesh; coarse-to-refined study; cyclic paths;
energy balance; adversarial rollback/cutback; tangent FD sensitivity; complete
external response curves; PEEQ and HEX20 cost investigation.

**Tests/V&V:** TET4/TET10/HEX8/HEX20 displacement, reactions, von Mises, PEEQ,
energy, iterations and state histories. Correlate Code_Aster and/or CalculiX.

**Acceptance:** all debt requirements in the V&V matrix pass without changing
0.2.4 tolerances; limitations of isotropic hardening remain explicit.

**Gate:** `025-G01`. **STOP:** energy/state corruption, mesh divergence without
explanation, or external mismatch. **GO:** debt pack is reproducible.

## WP2 - Unified geometric nonlinear core

**Objective:** bring geometric nonlinearity into the common residual, tangent,
state, convergence and increment infrastructure.

**Likely files:** `core/nonlinear.py`, `core/geometric_nonlinear.py`, nonlinear
contracts, TL element kernels, assemblers, result/diagnostic types.

**Prerequisite:** G00 and G01.

**Steps:** approve kinematic/stress measures; freeze current TET4 TL behavior;
extract element contribution contract; add material and geometric sparse tangent;
integrate TET4 then HEX8; consider TET10/HEX20 only after low-order gates.

**Tests/V&V:** rigid rotation, zero spurious stress, large traction, large-rotation
cantilever, distorted elements, element tangent FD, energy, mesh convergence and
external correlation.

**Acceptance:** objectivity and tangent requirements pass; same Full Newton and
transaction infrastructure is used; no separate production driver remains.

**Gate:** `025-G02`. **STOP:** unapproved measure pair, spurious rigid-body stress
or non-consistent tangent. **GO:** TET4 and HEX8 core evidence passes.

## WP3 - Linear buckling

**Objective:** provide a bounded sparse stability analysis using the verified
geometric stiffness.

**Likely files:** analysis/router contracts, modal/eigen backend adapters,
geometric stiffness assembly, benchmark/evidence files.

**Prerequisite:** G02.

**Steps:** define preload state and eigenproblem; reuse SciPy/SLEPc; expose factor,
mode and diagnostics; avoid inverse formation and dense matrices.

**Tests/V&V:** Euler column, one solid/plate-relevant case, mesh convergence,
mode normalization/invariance and Code_Aster/CalculiX correlation.

**Acceptance:** critical factor and mode satisfy justified analytical/external
criteria; sparse backend fallback is verified.

**Gate:** `025-G03`. **STOP:** inconsistent preload/geometric stiffness or mode
ordering. **GO:** bounded buckling envelope is documented.

## WP4 - Sparse arc-length/path following

**Objective:** qualify one continuation algorithm for limit-point response.

**Likely files:** nonlinear driver/controls/results, sparse solver interfaces,
checkpoint schema and arc-length benchmarks.

**Prerequisite:** G02; G03 is recommended for post-buckling work.

**Steps:** choose Crisfield spherical or Owner-approved equivalent; remove dense
correction; define sign/direction, adaptive radius, retry, rollback and restart;
record load factor and constraint residual.

**Tests/V&V:** shallow arch snap-through, limit point, bounded post-buckling,
branch-direction tests, step sensitivity and external response curve.

**Acceptance:** correct branch followed reproducibly; sparse path; no silent
switch to load control; restart reproduces the continuation history.

**Gate:** `025-G04`. **STOP:** wrong branch, dense global allocation or state
contamination. **GO:** defined problem class passes.

## WP5 - Unified frictionless contact

**Objective:** integrate normal contact into common residual/tangent/Newton/state.

**Likely files:** contact entities/search/solver, nonlinear assembler, state
transaction, controls and diagnostics.

**Prerequisite:** G02.

**Steps:** freeze current bounded contact evidence; approve enforcement method;
separate geometric search from contribution assembly; support opening, closure,
recontact and finite sliding; add contact rollback and penetration diagnostics.

**Tests/V&V:** single-node/patch contact, block/plane, curved contact,
open-close-recontact cycle, large sliding, penalty sensitivity if applicable,
mesh/load-step convergence and external correlation.

**Acceptance:** one common Full Newton loop; bounded penetration; exact rollback;
active-set changes are diagnosable; no element-family special driver.

**Gate:** `025-G05`. **STOP:** penetration/state depends unboundedly on penalty or
failed steps contaminate active state. **GO:** frictionless envelope passes.

## WP6 - Coupled nonlinear core

**Objective:** prove pairwise and, conditionally, triple nonlinear coupling.

**Likely files:** common assembler/contracts, coupled benchmark/evidence modules.

**Prerequisite:** G01, G02 and G05; approved J2 finite-kinematics model.

**Steps:** J2+geometry; geometry+contact; optional J2+geometry+contact; verify each
contribution in total residual/tangent and one shared transaction.

**Tests/V&V:** isolated-to-coupled limit recovery, tangent FD, energy, mesh/load
step sensitivity, rollback and external curves.

**Acceptance:** pairwise MUST cases pass and reduce correctly when one effect is
disabled. Triple coupling is SHOULD and cannot weaken pairwise evidence.

**Gate:** `025-G06`. **STOP:** no approved stress/strain model, inconsistent energy
or non-reproducible convergence. **GO:** pairwise evidence complete.

## WP7 - Frictional contact (conditional)

**Objective:** qualify Coulomb stick/slip only after normal contact is closed.

**Likely files:** contact friction state/tangent, transaction, diagnostics and
friction benchmarks.

**Prerequisite:** G05, G06 and explicit Owner GO.

**Steps:** approve local frame and enforcement; implement/verify stick, slip,
transition and tangential state; prove rollback and frictional dissipation.

**Tests/V&V:** block on plane, tangential traction, stick-to-slip, cyclic sliding,
large-displacement contact and external correlation.

**Acceptance:** objective direction update, non-negative physical dissipation,
state-safe retry and bounded external agreement.

**Gate:** `025-G07`. **STOP:** any prerequisite open. **GO:** optional claim only.

## WP8 - Performance characterization

**Objective:** measure and optimize only demonstrated nonlinear hotspots.

**Likely files:** profiling/benchmark utilities and narrowly scoped kernels.

**Prerequisite:** relevant functional gate closed.

**Steps:** baseline constitutive, Gauss, B matrices, geometric/contact tangents,
assembly, solves, copies and state memory; profile HEX20; optimize one hotspot at
a time and repeat numerical evidence.

**Acceptance:** environment, repeat count and uncertainty recorded; every change
has measured gain and non-regression.

**Gate:** `025-G08`. **STOP:** noisy or incomparable benchmark. **GO:** costs and
remaining limits are characterized even if no optimization is justified.

## WP9 - Failure and adversarial qualification

**Objective:** prove every important failure is explicit and state-safe.

**Likely files:** failure taxonomy, nonlinear/contact/continuation diagnostics,
adversarial tests and evidence.

**Prerequisite:** each tested subsystem's functional gate.

**Steps:** force max iteration, min increment, singular tangent, invalid element,
NaN/Inf, material/contact/linear-solver/arc-length failures; verify classification,
rollback and non-convergence.

**Acceptance:** no false PASS, committed state preserved, structured reason and
history returned for every planned mode.

**Gate:** `025-G09`. **STOP:** silent failure or contaminated state. **GO:** matrix
of failure contracts passes.

## WP10 - External correlation matrix

**Objective:** correlate complete response histories for every mandatory new
capability using comparable external formulations.

**Likely files:** external models, import/parsers, controlled references, evidence.

**Prerequisite:** corresponding internal verification gate.

**Steps:** lock geometry/mesh/material/BC/history/post-processing; run Code_Aster,
CalculiX and Abaqus if available; document incompatibilities; compare curves,
not selected scalar endpoints.

**Acceptance:** mandatory matrix cells pass or the associated release scope is
removed. Correlation is not called physical validation.

**Gate:** `025-G10`. **STOP:** irreproducible tool/version/model. **GO:** bounded
correlation pack tied to SHA.

## WP11 - Full non-regression

**Objective:** prove all 0.2.4 and accepted 0.2.5 scopes together.

**Likely files:** CI/readiness scripts and evidence only, except verified fixes.

**Prerequisite:** all mandatory functional, performance, failure and correlation
gates.

**Tests:** static, modal, harmonic, Newmark, BEAM, MITC, TET, HEX, composite,
sparse/PETSc/SLEPc where available, J2, geometric, buckling, arc-length, contact
and coupled paths. Build, docs and package smoke tests are mandatory.

**Acceptance:** complete campaign passes on the exact candidate SHA without
lowered tolerances, deselection drift or unexplained skips.

**Gate:** `025-G11`. **STOP:** any mandatory regression. **GO:** freeze candidate.

## WP12 - Documentation, traceability and Owner Review

**Objective:** produce a truthful release pack tied to the frozen SHA.

**Likely files:** README, changelog, qualification matrices, gate status, evidence
manifests, Owner Review and package metadata.

**Prerequisite:** G11.

**Steps:** regenerate SHA-dependent evidence; reconcile qualification vocabulary;
list limitations; verify wheel/sdist/smoke; ask every Owner question; do not tag or
publish automatically. The reproducible local chain is
`scripts/release_readiness_pipeline_025.py`: targeted mode runs the focused
tests, documentation build, gate check, SHA check, packaging and smoke import;
full mode additionally schedules coverage and the Docker external correlation.
An open `gate_check` keeps the verdict `NOT_READY` but does not prevent the
non-publishing SHA, packaging and smoke checks from running; other failures
stop the chain. The chain contains no tag, push or upload action.

**Acceptance:** requirements-to-evidence traceability complete, no stale SHA or
OPEN mandatory gate, explicit Owner decision.

**Gate:** `025-G12`. **STOP:** stale provenance, unsupported claim or missing
decision. **GO:** Owner-controlled release only.
