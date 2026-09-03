---
doc_id: DOC-027-F4-TEST-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 F4 Unit-Test Quality Audit

F4 audits whether the test suite can detect realistic regressions before
publication. It is a quality audit, not a new numerical qualification and not
a replacement for the bounded evidence records in the release pack.

## Source of truth and scope

The audit follows the evidence hierarchy recorded by F3: executed results,
machine-readable qualification records, frozen V&V evidence, tests,
qualification documentation, user documentation and package metadata. At the
clean F4 start SHA `6ddb581851754a5e701c35e97be565cc0f95ef60`, the inventory
contained 471 Python test files, 464 files with test definitions, 1,993 test
definitions and 2,324 collected tests. The AST inventory found 1,654 unit,
143 integration, 41 documentation and 155 verification test definitions.

The review covered assertions, invalid-input behavior, regression guards,
determinism, isolation, skips/xfails and behavior against the current
combination-level maturity claims. It did not treat the number of passing tests
or code coverage as sufficient evidence by itself.

## Findings

| Priority | Finding | Disposition |
| --- | --- | --- |
| P0 | None found. | No release-critical test-quality failure identified. |
| P1 | None found. | Critical supported routes have behavioral assertions and negative guards. |
| P2 | 17 critical `pytest.raises(Exception)` catches were too broad. | Fixed with concrete error categories. Optional live PETSc/MPI, Gmsh and external environments remain explicitly gated. |
| P2 | The full suite retains three pre-existing failures in experimental or stale nonlinear test paths. | Deferred without skip/xfail or expectation weakening; outside the bounded public release matrix. |
| P3 | One cache assertion was opaque; two validator success tests rely on no exception; no mutation framework is installed. | Cache assertion fixed. The two API-contract cases and the absence of a global mutation campaign remain non-blocking limitations. |

The negative-test audit covered dimensions and shapes, degenerate/inverted
geometry, non-finite values, material properties, incompatible BC/load
definitions, unsupported routes/backends, corrupt checkpoints/evidence and
wrong types or sizes. No critical domain was found to be completely
unguarded. The concrete exception guard is now also enforced by
`tests/unit/test_f4_unit_test_quality.py`.

## Behavioral confidence matrix

| Surface | Test quality | Current boundary | Remaining gap |
| --- | --- | --- | --- |
| TET4, TET10, HEX8, HEX20 | Element, matrix, result and adversarial checks | Existing bounded registry scope | Optional live backends remain environment-gated |
| WEDGE6 static | Fail-closed kernel/workflow/robustness checks | `EXPERIMENTAL` | Static maturity is not promoted by modal evidence |
| WEDGE6 modal | Frequency, mode-shape and bounded evidence checks | `QUALIFIED_BOUNDED`, first three modes | No transfer to static or general dynamics |
| Static/modal/buckling | Route-specific numerical and failure checks | Combination-level and bounded | No universal element-independent claim |
| Dynamics/Newmark/harmonic/contact | Targeted route and checkpoint checks | `SUPPORTED_WITH_LIMITATIONS` | No transitive qualification from static evidence |
| Small-strain J2 | Constitutive, state-integrity and failure checks | `QUALIFIED_BOUNDED` for four solid families | Finite-kinematic J2 remains experimental |
| BCs, loads, reactions, energy and materials | Analytical, equilibrium, finite-result and negative assertions | Route/element evidence scope | External comparisons remain comparable-only |
| API/CLI, packaging, registry and preflight | Contract, import and release guard tests | Implemented/tested surfaces | Live optional environments are separate jobs |

The full machine-readable matrix, mutation-style analysis and evidence links
are in [`f4_unit_test_quality_audit.json`](../../../qualification/0_2_7/f4_unit_test_quality_audit.json).

## Mutation-style checks

The audit challenged six plausible regressions: changing an element-stiffness
sign, dropping an assembly contribution, skipping a BC, selecting the wrong
backend, removing residual validation and corrupting reactions or
post-processing. Existing tests provide a meaningful detector for each through
symmetry/rank or analytical checks, assembly contracts, exact DOF and
equilibrium assertions, explicit backend selection, non-convergence guards and
reaction/energy/finiteness checks.

## Skips, determinism and isolation

Twenty-six significant skip sites were reviewed; there are no xfail markers.
External tools, optional Gmsh/PETSc/MPI environments, heavy evidence and
generated artifacts are skipped only behind explicit prerequisites. A skip is
not converted to PASS and does not widen a public claim. Inspected random
generators use explicit seeds; no unbounded sleeps or network-dependent test
paths were found. Temporary paths and environment changes are fixture-scoped.

## Full-suite outcome

The complete local suite finished in 1,577.06 seconds with `2142 passed,
3 failed, 184 skipped, 2 warnings`. The three failures are preserved and
visible: two finite-sliding expectations exercise an experimental or
unsupported discrete/nonlinear path, and the geometric-nonlinear negative
test expects an older message after a deliberately invalid object load is
rejected earlier by the current fail-closed preflight. They were not skipped,
xfail-ed or reclassified as PASS. They are deferred test-contract work for a
future experimental-route decision and do not affect the bounded supported
route claims audited by F4.

The F4 targeted battery finished with `379 passed, 4 skipped, 2 warnings`.
Ruff and `compileall` passed. The warnings came from the existing adversarial
HEX8 determinant probe and do not alter its fail-closed verdict.

## Conclusion

`F4_STATUS = PASS_WITH_LIMITATIONS`. For officially supported and bounded
0.2.7 routes, the suite gives reasonable confidence that a realistic
regression will be detected before publication: critical results and
invariants, dispatch, invalid inputs, fail-closed behavior and release guards
are asserted. The full-suite audit still exposes three experimental/stale
nonlinear failures, so those paths are not release-ready; this does not
weaken the bounded supported-route conclusion. F5 has not started, and no
numerical source, historical evidence or maturity was changed by F4.

The controlled state is recorded in the JSON artifact and the release manifest;
the active release progress remains unchanged.
