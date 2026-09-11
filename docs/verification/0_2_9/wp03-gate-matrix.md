---
doc_id: DOC-029-WP03-005
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03-A — prospective robustness gate matrix

> All gates below are frozen for later implementation. WP03-A has no
> implementation evidence, so every gate is
> PROSPECTIVE_NOT_DEMONSTRATED and WP03 remains 0/7.

The machine-readable contract and statuses are in
qualification/0_2_9/wp03_robustness_contract.json.

| Gate | Requirement | Required evidence | WP03-A status |
| --- | --- | --- | --- |
| G03-01 | One authoritative robustness/policy authority for public lifecycles | Static call graph and runtime delegation show no competing public policy owner | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-02 | Deterministic failure classification | Repeated injected failures produce identical reason/class/action metadata | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-03 | Correct stagnation detection | Plateau and near-convergent cases do not false-converge and report explicit stagnation | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-04 | One line-search contract | Difficult case records deterministic alpha/reductions; compatibility wrappers delegate | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-05 | Cutback preserves accepted state | Rejected adaptive trials leave the accepted composite digest exact | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-06 | Growth/shrink policy is explicit | Easy, expensive and rejected increments produce deterministic policy history | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-07 | Terminal behavior is explicit | Minimum increment, maximum cutbacks and non-retryable cases terminate canonically | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-08 | Rollback remains exact under retry | Failure injection across material, line-search and continuation paths preserves all digests | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-09 | Easy-case numerical preservation | Baseline cases remain within relative 1e-9 / absolute 1e-12 or stricter existing bounds | PROSPECTIVE_NOT_DEMONSTRATED |
| G03-10 | Difficult-case improvement is evidence-based | Same model/tolerances show a justified convergence/robustness improvement without changing the physical result | PROSPECTIVE_NOT_DEMONSTRATED |

## Interpretation rules

G03-01 does not require the same algebraic correction equation for
arc-length. It requires common accepted-state, failure/retry and diagnostic
ownership. G03-09 and G03-10 must never be achieved by changing a
formulation, relaxing a tolerance or promoting maturity.

No gate can be closed from the existence of a class or contract alone.
Targeted evidence and the later independent WP03-E review are required.
