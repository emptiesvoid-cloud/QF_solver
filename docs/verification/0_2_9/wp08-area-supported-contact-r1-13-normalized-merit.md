---
doc_id: DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-001
revision: 1.0
status: controlled_candidate_contract
applicable_version: 0.2.9-development
---

# WP08 area-supported contact R1.13 — normalized active-slip globalization

## Purpose and status

R1.13 prospectively rechecks the bounded area-supported frictional-contact
benchmark after the R1.13 correction to active-slip nonlinear globalization.
The campaign is diagnostic evidence for Owner review, not formal WP08 credit.
It awards no points and does not alter the historical ledger.

The R1.12 M4/slip attempt remains an immutable `FAIL_CLOSED_NUMERICAL`. Its
least-squares termination did not satisfy the frozen maximum per-contact
residual gate. R1.13 tests a specific candidate cause: R1.12 formed a
Newton direction/Jacobian from the physical residual while evaluating Armijo
decrease with a pressure-normalized residual. R1.13 pairs the normalized
residual, its pressure-scale-aware Jacobian, and the L2 Armijo merit. The
maximum per-contact acceptance gate remains unchanged.

## Frozen scope

- Cases: `stick_target` and `slip_target`.
- Mesh sequence: M1, then M2, then M3; each case runs serially in its own
  process.
- Progression: M2 only after both M1 cases pass; M3 only after both M2 cases
  pass; stop after any failed process or gate.
- Inputs: reuse the R1.11 geometry, mesh definitions, material, boundary
  conditions, load history, friction coefficient, surface stiffness density,
  contact search, solver backend, tolerances, active-set limits, enumeration
  guard, fallback policy, and diagnostic gates without modification.
- Source: bind the exact R1.13 execution commit, full source inventory, both
  runner hashes, contract/document hashes, and runtime before executing.
- Evidence: write only to a new R1.13 output root; never overwrite or retry an
  existing case. Preserve every failure and process log.

## R1.13 mechanics delta

Only active-slip globalization is changed relative to the R1.12 execution
source: the Newton system and line-search merit now describe the same
pressure-normalized residual. The L2 merit is used only for globalization;
the frozen maximum per-contact residual remains the convergence gate. The
coupled projection route uses the same consistent pairing. No physical input,
threshold, solver tolerance, iteration budget, contact definition, or fallback
policy is changed by this campaign.

## Required reporting

Record per case: mesh/case, execution SHA, contract and binding SHA-256,
source-bundle SHA-256, runner/test hashes, exact command, UTC start/end, child
PID and exit code, raw/result/telemetry/log hashes, accepted/rejected steps,
active contact states, solver convergence, equilibrium and all frozen gates.
Report observed mesh deltas descriptively; do not infer a new convergence
threshold from results.

Classify a fully passing six-case run as `PASS_CANDIDATE_DIAGNOSTIC_ONLY`.
Any failed gate remains `FAIL_CLOSED`; later cases are skipped according to
the frozen dependency rules. Neither outcome by itself awards WP08 points.

## Explicit limitations

This campaign does not execute an independent global FEM/Newton reference,
formal replay, external-solver correlation, or formal WP08 closure. The
existing independent observable recomputation/replay claims from other source
SHAs are not transferable to R1.13. A successful R1.13 run is therefore a
candidate for a separate Owner review, not a formal qualification.
