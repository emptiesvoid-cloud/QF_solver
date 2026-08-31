---
doc_id: DOC-027-018
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Declarative V&V Harness v2

WP04 adds an additive declarative harness for new 0.2.7 campaigns. It is a
new evidence path; the historical verification modules and runners remain
usable and are not migrated wholesale.

## Case contract

Each case records a case and requirement identifier, capability/registry
references, element, analysis, material and route, model/deck input, declared
observables, tolerance, expected failure, execution tier and provenance. The
case schema is stored in
`qualification/0_2_7/vnv_v2/sample_cases.json` and validated before execution.

The oracle contract supports `ANALYTICAL`, `INTERNAL_INVARIANT`,
`CROSS_ELEMENT`, `EXTERNAL_SOLVER`, `REFERENCE_DATA` and
`FAILURE_EXPECTATION`. An oracle declares its source, observable, unit,
comparison rule, tolerance and provenance. A threshold is part of the case
contract and is never inferred from an observed result.

## Execution and evidence

`solveur.verification.v2.VnvRunner` validates a case, invokes a controlled
executor, collects observables, compares them to the declared oracle,
classifies the result and writes a machine-readable evidence record. Verdicts
are `PASS`, `FAIL`, `SKIPPED_EXTERNAL_UNAVAILABLE`, `RESOURCE_LIMITED`,
`EXPECTED_FAILURE_PASS` and `INVALID_EVIDENCE`. An external skip is never a
pass.

Evidence records contain source SHA, environment, canonical input digest,
observables, oracle and tolerance, verdict, failure reason, runtime, optional
peak memory, provenance and artifact classification. Canonical UTF-8 JSON with
sorted keys and LF termination is used for digests. Replay checks source SHA,
input digest and result digest separately and reports mismatches explicitly;
timestamps and runtime are not part of the scientific result digest.

## Representative migration boundary

Three existing routes are exercised through the new contract: a TET4 static
analytical fixture using the public solve API, a TET4 modal invariant fixture,
and an unknown-element preflight expected-failure fixture. These samples prove
the migration boundary without replacing the 188 historical V&V modules.

WEDGE6 remains unimplemented. The schema can describe future WEDGE6 patch,
orientation, face-load, refinement, distortion and external-oracle cases, but
no WEDGE6 capability or qualification is created by WP04.
