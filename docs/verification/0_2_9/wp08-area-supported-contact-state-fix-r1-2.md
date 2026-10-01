---
doc_id: "DOC-MARKDOWN-68AD7558750BA90A"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact: R1.2 zero-pressure state correction

## Purpose and classification

This is a bounded experimental diagnostic requalification, not a formal WP08 qualification. It preserves the R1 and R1.1 attempts and binds a fresh M1 prerequisite before one sequential M2/M3 diagnostic execution. No score is claimed or awarded.

## Root cause from the preserved R1.1 M2 failure

At M2 `slip_target`, load step 7, the normal active-set update included all nine candidate contact nodes even though nodes `[2, 5, 8]` had zero pressure. The active-slip root correctly formed its compressed frictional subset `[0, 1, 3, 4, 6, 7]` and excluded `[2, 5, 8]` from its 12-dimensional tangential unknown vector. The post-root validator nevertheless compared stale observed `slip` labels for all nine nodes against a root result that classified zero-capacity, zero-pressure nodes as frictionless. This raised `TANGENTIAL_STATE_CHANGED`. A later coupled projection then rejected the seed and reached the frozen contact-count guard. The latter is a secondary consequence and is not addressed by relaxing or increasing that guard.

## R1.2 correction

For frictional contacts that are absent from the compressed frictional root subset, including normal-weakly-active contacts with pressure at or below the existing pressure tolerance:

- classify the tangential state as `open`;
- require zero tangential force within the existing tolerance;
- preserve the prior slip reference exactly;
- exclude the contact from tangential root unknowns and state-transition comparisons for compressed stick/slip contacts.

Compressed contacts continue through the existing stick/slip state checks. The new unit regression covers a weakly normal-active, zero-pressure contact and checks the open state, zero tangential force, unchanged slip reference, and telemetry subset classification.

This is a production contact-mechanics correction for this benchmark, not merely an instrumentation change. It does not alter the frozen contact formulation or benchmark parameters.

## Frozen numerical scope and invariants

The base R1 contract remains the source of all model, mesh, load, constitutive, solver, and diagnostic-gate definitions. In particular, geometry, M1/M2/M3 meshes, material, boundary conditions, normal and tangential resultants, friction coefficient, surface stiffness density `2,666,700 N/m^3`, load-step sequence, active-set iteration cap, contact-count guard, tolerances, fallback policy, and diagnostic checks are unchanged. No numerical threshold has been introduced or relaxed. Refinement deltas remain descriptive; this contract does not classify mesh convergence as PASS or FAIL.

Fresh R1.2 M1 evidence was executed after the correction on source bundle `82e519769e5df019afadefacda5f65d6589107d54ac90bd0fe595f682ae7159d`. Both `stick_target` and `slip_target` returned `PASS_DIAGNOSTIC_GATES`, each with process exit code 0. Their raw results are immutable prerequisites for the following M2/M3 run.

## Execution authorization and fail-closed sequence

Owner authorization is limited to one diagnostic execution on the bound source and frozen base contract. Execute sequentially:

1. M2 / `stick_target`;
2. M2 / `slip_target`;
3. M3 / `stick_target`, only if both M2 cases pass;
4. M3 / `slip_target`, only if both M2 cases pass and the preceding M3 case passes.

Use a new output directory. Do not overwrite earlier evidence. If a case fails, stop the dependent sequence, preserve all artifacts, and report the observed failure. No retries, parameter changes, threshold changes, fallback-policy changes, or contact-limit changes are authorized by this amendment. No independent global FEM reference, formal replay, formal WP08 qualification, merge, push, or point award is implied.

## Provenance anchors

- Branch / HEAD: `codex/wp08-surface-stiffness-remediation` / `78d2c07eeeab32c13986eb4184537e83973534d5`.
- Base R1 M2/M3 contract SHA-256: `277993b1b1c270b8175d2def35d99d137c36670accef699b6c21ffc0bcbadee2`.
- Fresh R1.2 M1 contract SHA-256: `c5a071266918980ee5400875da1dff7ee6cbae16d7f3c60c35c6f3a2a3b3b4ec`.
- Fresh R1.2 M1 final SHA-256: `1ffe10941c41dcd63142a551261bd9bb8c584493a4ca0074d344933d2f0e6b28`.
- Fresh R1.2 M1 source-bundle SHA-256: `82e519769e5df019afadefacda5f65d6589107d54ac90bd0fe595f682ae7159d`.
- Policy digest is recorded as diagnostic context only: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`; governing policy enforcement is not claimed.

The machine-readable amendment and freeze binding enumerate and hash the M1 inputs and prior R1/R1.1 evidence. The execution runner must verify these hashes before freezing or launching any M2/M3 process.
