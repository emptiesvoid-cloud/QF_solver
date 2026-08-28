---
doc_id: DOC-NL-025-018
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 objective-mode execution plan

## Objective for the future execution process

Implement and qualify the 0.2.5a0 bounded unified nonlinear structural mechanics
scope in strict gate order, preserving the complete 0.2.4 baseline and producing
reproducible evidence for each work package before starting dependent work.

## Mandatory operating loop

```text
AUDIT -> IMPLEMENT ONE WP -> VERIFY -> BENCHMARK -> CORRELATE -> GATE
      -> GO to a dependent WP, or STOP/document if the gate remains OPEN
```

The execution process must never convert missing evidence, unavailable software or elapsed
time into a PASS.

## Exact execution order

1. WP0: freeze `v0.2.4a0` baseline and close `025-G00`.
2. WP1: close every inherited 0.2.4 V&V debt and `025-G01`.
3. WP2: unify and verify TET4/HEX8 geometric nonlinear core; close `025-G02`.
4. WP3: verify sparse linear buckling; close `025-G03`.
5. WP4: verify one sparse arc-length method; close `025-G04`.
6. WP5: unify frictionless finite-sliding contact; close `025-G05`.
7. WP6: verify mandatory pairwise couplings; close `025-G06`.
8. Ask Owner whether WP7 friction is promoted; otherwise record `NOT_IN_SCOPE`.
9. WP8: characterize performance on every completed mandatory capability.
10. WP9: execute adversarial/failure matrix.
11. WP10: complete bounded external-correlation matrix.
12. WP11: run full regression, docs, packaging and smoke installation.
13. WP12: regenerate final-SHA evidence and request Owner release decision.

WP3 and WP4 may run in parallel after G02. Profiling and adversarial tests may be
prepared earlier, but their gates cannot close before the corresponding function
gate.

## Per-WP execution checklist

1. Read authoritative requirements, formulas, risks and gate rows.
2. Record baseline tests and numerical outputs before editing.
3. Make the smallest architecture-compatible change.
4. Run focused unit and element tests.
5. Run global benchmark and sensitivity study.
6. Run external correlation when the gate requires it.
7. Update evidence, limitation and traceability records.
8. Close the gate only when every acceptance item has an artifact.
9. Run prerequisite non-regression before moving on.

## STOP rules

Stop the dependent branch and leave the gate `OPEN` when any of these occurs:

- stress/strain measures are not approved for a coupled formulation;
- tangent FD or objectivity fails;
- a failed step corrupts committed state;
- sparse paths require an unbounded dense allocation;
- mesh/load-step studies do not converge without a documented explanation;
- external formulations are not comparable;
- a mandatory 0.2.4 regression appears;
- evidence cannot be tied to the exact tested SHA.

Independent work may continue only when its dependency path does not include the
open gate.

## GO rules

GO requires the gate row to contain: exact SHA, environment, commands, results,
artifacts, limits, reviewer and explicit status. A green test process alone is
not a closed gate.

## Release boundary

The future execution process may prepare commits and release artifacts when instructed, but
must not tag, create a GitHub Release or publish to PyPI without a separate Owner
instruction after `025-G12`.
