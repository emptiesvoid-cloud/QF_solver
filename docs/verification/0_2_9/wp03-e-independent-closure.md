---
doc_id: DOC-029-WP03-012
revision: 0.1
status: closed
applicable_version: 0.2.9-development
---

# WP03-E — independent robustness closure audit

**Decision:** `GO_WITH_LIMITATIONS` at audit SHA
`4ca71d549ea13460086f52670baa42c74d9ac1aa`.

WP03 closes at **7/7**, bringing the validated roadmap to **29/100**. This
audit changed no production source, formulation, element behavior, maturity
claim, checkpoint schema or historical evidence. The source and adversarial
test audit finds one authority each for stagnation, line search, adaptive step
policy and arc-radius policy. Those policies return decisions and diagnostics;
they cannot commit accepted nonlinear state.

## Frozen gate outcome

| Gate | Decision | Independent basis |
| --- | --- | --- |
| G03-01 | PASS_WITH_LIMITATIONS | One authority per bounded policy family; the arc correction kernel remains specialized by design. |
| G03-02 | PASS | Repeated failure classifications and deterministic diagnostics agree. |
| G03-03 | PASS | Stagnation sample, threshold, convergence-precedence and non-finite boundaries pass. |
| G03-04 | PASS | One alpha-reduction loop; rejected line-search trials do not leak state. |
| G03-05–G03-07 | PASS | Common cutback/radius, growth/shrink and terminal-boundary rules are exercised. |
| G03-08 | PASS_WITH_LIMITATIONS | Exact rollback is demonstrated for supported material/continuation paths. |
| G03-09 | PASS_WITH_LIMITATIONS | Easy pre/final paths are numerically identical; bounded geometric/contact regressions pass. |
| G03-10 | PASS | Same-model difficult-case improvement is independently reproduced. |

## G03-10 difficult-case proof

The audit defined one target-clipped arc-length challenge and ran it unchanged
at pre-WP03 `9a97025670f7fbb28cbe4c6e2e76eacbf9fc5714` and at the audit SHA.
The same model, mesh, material, loads, constraints, tolerance, target and
`MAX_ITERATIONS` injection reject an effective attempt radius at or above
`0.0035`.

Before WP03, the policy radius was reduced but the target-clipped effective
radius stayed `0.0035355339059327385` for five failed attempts. The final
policy made the next effective attempt `0.003125`: only one rejection was
needed. Both revisions then accepted the same effective radii, reached the
same load factors and produced the identical final displacement. This is a
material robustness improvement, not a source-count or policy-unit-test claim.

## Boundaries retained

This closure does not qualify frictional contact, adaptive penalty contact,
distributed nonlinear PETSc/MPI or nonlinear dynamics. Inherited mixin typing
debt remains documented. Geometric nonlinear and arc-length maturity remain
unchanged. OD-029-01 stays **OPEN** and blocks WP09 only; OD-029-02 stays
**CLOSED** as `READ_V1_WRITE_V2_BOUNDED`.

The machine-readable audit record is
`qualification/0_2_9/wp03_e_independent_closure.json`. The next permitted
action is **Owner review before WP04 authorization**; WP04 is not started by
this audit.
