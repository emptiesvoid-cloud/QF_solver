---
doc_id: DOC-027-LU2-WP07-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# LU2-WP07 - Existing route maturity and targeted V&V

WP07 closes the maturity audit for existing public routes. The machine-readable
source is `qualification/0_2_7/lu2_wp07_maturity_matrix.json`; this document is
a generated-view-style summary of that record.

## Decision

`PASS_WITH_LIMITATIONS`. No promotion or demotion was made. The audit reused
the controlled WP06, WP19 and WP20 evidence and reran the focused validation
set. No new external campaign was needed because the remaining external
correlations are bounded and do not change a public maturity decision.

## Route boundary

| Route | Current maturity | Decision | Main boundary |
| --- | --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | KEEP | Element/material combinations remain separate claims. |
| Modal | `QUALIFIED_BOUNDED` | KEEP | Mass, element and first-mode evidence remain bounded. |
| Buckling | `QUALIFIED_BOUNDED` | KEEP | HEX8 buckling remains more-evidence-required/not qualified. |
| Harmonic | `QUALIFIED_BOUNDED` | KEEP | Family and external coverage remain bounded. |
| Newmark dynamics | `QUALIFIED_BOUNDED` | KEEP | Recovery and element coverage are limited to tested routes. |
| Nonlinear static | `EXPERIMENTAL` | KEEP | Broad nonlinear, finite-kinematic and coupled routes are not qualified. |
| Arc-Length | `EXPERIMENTAL` | KEEP | Continuation evidence is bounded; no general nonlinear claim. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | KEEP | TET4/TET10/HEX8/HEX20 only; no universal increment threshold. |
| Contact | `QUALIFIED_BOUNDED` | KEEP | Frictionless scope only; friction remains not qualified. |
| WEDGE6 | `EXPERIMENTAL` | KEEP | Static remains experimental; modal evidence is separate and bounded. |

## Existing evidence and adversarial boundary

WP19 contributes 24 predeclared adversarial cases, including 14 expected
failures, with fail-closed behavior, deterministic replay and no NaN/Inf.
WP20 contributes the four-family small-strain J2 closure, including return
mapping, unload/reload, increment characterization, rollback integrity and
finite-difference tangent evidence. WP06 defines the recovery boundary and
does not claim universal restart or fault tolerance.

The audit therefore keeps the following explicitly outside qualified claims:
finite-kinematic J2, coupled nonlinear routes, friction, mixed meshes, HEX8R /
SRI / B-bar, WEDGE15, PYRAMID5 and untested large-route recovery.

## Tests and provenance

The focused audit set is recorded in the machine-readable matrix. It includes
the WP19, WP20, WP06, checkpoint, preflight, registry and G14 coverage tests;
the result was `50 passed`. No new external run, heavy benchmark, full
regression or numerical source change was performed. WP04 remains
`USER_INTERRUPTED_INCONCLUSIVE` and its supervised retry remains independent.
