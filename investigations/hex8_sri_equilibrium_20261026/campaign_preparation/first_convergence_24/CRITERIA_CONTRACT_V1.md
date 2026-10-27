# HEX8-SRI first-six criteria contract

Status: prepared for Owner review. No FEM calculation, assembly, or eigensolve was run while preparing this contract.

## Case-level gates

The first six `4×2×2` cases use the already reviewed thresholds without alteration:

| Criterion | Classification | Frozen condition |
|---|---|---|
| Required observables finite | `CASE_GATE` | Every required array and scalar is finite |
| Sampled Jacobian | `CASE_GATE` | `det(J) > 0` at the center and the eight evaluated Gauss points |
| Free residual | `CASE_GATE` | Relative residual `≤ 1e-7` |
| Energy identity | `CASE_GATE` | Relative defect `≤ 1e-8` |
| Force closure | `CASE_GATE` | Relative closure `≤ 1e-6` |
| Moment closure | `CASE_GATE` | Relative closure `≤ 1e-6` |
| Mean loaded-face `UZ` | `CASE_GATE` | Negative under the applied negative-Z traction |

The four numeric limits are passed to the element-case evaluator. The three boolean checks are emitted as case verdicts. These conditions do not change the mechanical formulation.

## Case diagnostics

The matrix symmetry defect, affine Jacobian reproduction, positive internal energy, formulation comparison, condition estimate, time, RSS, and Timoshenko difference are `CASE_DIAGNOSTIC` measurements. They are retained as descriptive observables and do not decide a case verdict in this tranche.

## Deferred campaign gates

Paired-mesh changes in displacement and energy, and errors against a qualified independent 3-D reference, are `CAMPAIGN_GATE_DEFERRED` with status `NOT_ASSESSED`. The single `4×2×2` level cannot evaluate them. Timoshenko remains a scale/sign/trend comparison and is not a precision oracle.

The existing four mesh/reference thresholds remain recorded in `proposed_criteria`; they are not passed to the case evaluator as gates. A deferred criterion must remain `NOT_ASSESSED`; it cannot be reported as `PASS` from these single-level tests.

## Owner decision and revision boundary

The case manifest carries the proposed classification and keeps `frozen_criteria` unset. The execution Owner decision must carry the exact disposition map, the four case-gate thresholds, and the registration digests for all six cases. The controller rejects a changed class, threshold, revision, or manifest digest. An approved decision is bound to the exact controller and scientific source identities.

Changing any classification requires a documented scientific revision, a new contract revision, and a new Owner decision. The previous decision and receipts remain historical and cannot authorize the new manifest identities.

## Implementation dependency

The controller change is prepared on `codex/hex8sri-criteria-contract-fix`; the science-test and instrumentation change is prepared separately on `research/hex8sri-first6-criteria-contract`. The science branch advances the test contract marker, evaluates the approved `UZ < 0` gate, and records the Owner dispositions in its sidecars. Both changes must be reviewed together. After integration, source-bound manifests and collect-only preflights must be regenerated; none is regenerated here.
