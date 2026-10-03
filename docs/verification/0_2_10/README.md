---
title: QF Solver 0.2.10 candidate verification summary
doc_id: DOC-VV-CANDIDATE-0210-001
revision: 1.0
applicable_version: 0.2.10
status: controlled_candidate
reviewer: ""
approver: ""
---

# QF Solver 0.2.10 candidate verification summary

**Status:** candidate documentation; no final source freeze, tag, package,
GitHub Release, or version DOI is asserted here. The package candidate audit
is tied to source SHA
[`aa45694f02bcc7607f5aef4b770ddb07269e42fe`](https://github.com/emptiesvoid-cloud/QF_solver/commit/aa45694f02bcc7607f5aef4b770ddb07269e42fe),
not to this later documentation tree. The whole-repository G03 archive scan
remains failed. A package-scoped scan does not waive that failure.

This summary separates four kinds of statement:

- **Implementation:** code paths exist.
- **Verification:** specified checks were run and produced recorded results.
- **Bounded acceptance/qualification:** an explicit decision accepts only a
  named scope and its limitations.
- **Physical validation:** comparison with physical measurements; the evidence
  summarized here does not establish universal physical validation.

### Three numerical evidence sources

- **Internal independent recomputation** recalculates selected observables
  independently of the solver path. It is not a second global FEM/Newton
  solution.
- **External solver correlation** compares frozen, comparable cases with
  Code_Aster 18.1. The accepted scope is same-mesh linear-static observables
  for recorded element families; it does not cover nonlinear correlation.
- **Physical validation** compares predictions with measurements. Solver-to-
  solver agreement and internal recomputation do not provide that evidence;
  no universal physical-validation claim is made here.

## Evidence overview

| Area | Current evidence and public interpretation |
| --- | --- |
| Nonlinear core and state | Common residual/tangent and Newton infrastructure, trial/accepted-state transactions, rollback/retry, and selected schema-v2 restart routes have recorded closures. These do not qualify every composed route. |
| Small-strain J2 | Existing bounded element-analysis decisions remain authoritative; see the 0.2.8 registry. |
| Corotational J2 | Owner-accepted bounded HEX8 scope with large rotations and small local strain. This is not general finite-strain plasticity. |
| J2 family extensions | TET10/HEX20 extension evidence is bounded and accepted with limitations, but does not itself promote formal maturity. |
| Coupled nonlinear cases | Owner-accepted bounded static evidence across selected TET4/TET10/HEX8/HEX20 cases; contact, dynamics, and distributed extensions are outside that acceptance. |
| Total-Lagrangian geometry | Selected StVK TET4/HEX8 static serial campaign audited `GO_WITH_LIMITATIONS`; the final audit explicitly leaves maturity unchanged. |
| Frictionless contact | Experimental bounded penalty node-to-triangle route. |
| Frictional contact | Prior narrow serial evidence is Owner-accepted with limitations; current-source formal requalification is not established. Mesh sensitivity remains visible. |
| Continuation | Full Newton, line search, adaptive cutback/retry, and arc-length evidence is route-bounded; no general postbuckling or bifurcation claim. |
| PETSc/MPI | Bounded two-rank linear-static cases with replicated input/root-side assembly; no scaling or general nonlinear distributed claim. |
| Code_Aster | Same-mesh 18.1 linear-static numerical correlation for bounded cases across TET4/HEX8/TET10/HEX20. This is not physical validation or general nonlinear correlation. |
| Release gate | WP14 remains on HOLD while the whole-repository G03 scan is failed; no implicit waiver is applied. |

## Provenance and interpretation

The development-cycle records are retained under
[`qualification/0_2_9`](https://github.com/emptiesvoid-cloud/QF_solver/tree/main/qualification/0_2_9)
and the 0.2.10 package candidate records under
[`qualification/0_2_10`](https://github.com/emptiesvoid-cloud/QF_solver/tree/main/qualification/0_2_10).
They are detailed engineering evidence, not a substitute for the scope
summaries above. Historical failures and previous source-bound audits remain
unchanged.

The package-scoped candidate scan and package checks were run against their
recorded source SHA; they do not clear a later source tree or full repository
archive. A final release requires a clean, exact-SHA freeze and renewed source-
bound audits. The candidate Zenodo identifier `10.5281/zenodo.23106744` is
reserved but not published; it must not be cited as the version DOI.

For the latest public release and citation, see
[`CITATION.cff`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CITATION.cff).
