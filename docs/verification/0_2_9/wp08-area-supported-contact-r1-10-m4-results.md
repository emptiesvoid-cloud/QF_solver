---
doc_id: "DOC-MARKDOWN-252DCAD9FF732B00"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact R1.10 — M4 diagnostic results

## Verdict

`EXPERIMENTAL_EXECUTION_PARTIAL_FAIL_CLOSED`. The frozen M4 stick case passed its diagnostic gates. The frozen M4 slip case failed closed at load step 7, so the two-case M4 campaign is incomplete. This does not qualify WP08, establish mesh convergence, or award points.

| Case | Process | Observed result | Interpretation |
|---|---:|---|---|
| M4 stick target | exit 0 | `PASS_DIAGNOSTIC_GATES`; 8/8 accepted steps; 81/81 slave contacts active; 0.5 m² active area; affine support rank 2; terminal state stick | Diagnostic case pass. The general audit still reports `run_verdict=WARNING` because contact maturity is experimental; that warning is retained. |
| M4 slip target | exit 1 | `FAIL_CLOSED` at step 7 after 6 accepted steps and 1 rejected step; active-slip residual `1.5037868322441332e-7` versus frozen `1e-9` tolerance | Numerical robustness limitation at the refined slip case. No retry, alternate parameter, or continuation was attempted. |

The stick equilibrium audit reports relative force and moment errors of `6.349816556317474e-15` and `2.4092289071644135e-14`. The fallback count is unavailable in the result schema and is not claimed to be zero.

## Provenance and frozen scope

- Branch: `codex/wp08-area-contact-r1-10-candidate`
- Source HEAD bound for the M4 runner: `5aeab8733164fb26bbb167f1000212388392bb5d`
- Freeze/evidence metadata HEAD: `36d1d379e4a22d8d420da55dc0410a1fcac24304`
- Runner SHA-256: `dce70eb021344d42c420d693a25f835681ea5b13c8da08b917d34bc82bc80541`
- Contract SHA-256: `79073a5199a2832a3c546f77c5e3a98d48d7fd38b6f69c1fb3a237a40fffa0dd`
- Execution-binding SHA-256: `1a28e12326d321457975529d5861d15045e947b1b5aa9507a238cb791b49ee14`
- Source-bundle SHA-256: `b740589aea985fb1768e5676963d68138dcc898ba8f21dcc45e0bc7946c85fb7`
- Freeze UTC: `2026-09-26T20:42:42.610982Z`
- Execution window: `2026-09-26T20:43:45.206498Z` to `2026-09-26T20:45:52.109695Z`

The run used the authorized 16×8×8 TET4 level, fixed R1.10 contact and material inputs, eight load steps, and the prescribed stick-then-slip sequence. The parent M1/M2/M3 cases were reused read-only. No thresholds, loads, mesh, material, contact parameters, solver mechanics, fallback policy, or parent evidence were changed. There was no retry. No M1/M2/M3 rerun, formal replay, independent global FEM solve, or external solver run occurred. No active M4 process remains.

The contract froze no M3→M4 convergence threshold. Therefore the following stick-only comparison is descriptive, not a convergence pass:

| M3 stick → M4 stick | Relative L2 difference | Absolute L2 difference |
|---|---:|---:|
| Common-node displacement, 225 common body nodes | 0.644622% | `2.955170973160418e-5 m` |
| Normal contact resultant | 0.103880% | `0.9061684032752737 N` |
| Tangential contact resultant | 0.152071% | `0.222029869552818 N` |

Active-area fractions are 1.0 at both levels. No M3→M4 slip comparison exists because M4 slip did not complete.

## Slip failure detail

At step 7 the active-slip globalized least-squares route terminated on `xtol`, but the residual remained `1.5037868322441332e-7`, above the frozen `1e-9` root tolerance (`GLOBALIZED_SLIP_RESIDUAL_NOT_CONVERGED`). The coupled-projection seed was then rejected. Its exhaustive candidate search was stopped by the deterministic guard: 81 contact operators exceed the frozen maximum enumeration size of 8 (`COUPLED_SEARCH_CONTACT_LIMIT_EXCEEDED`). This is a controlled fail-closed robustness outcome, not an infrastructure crash and not evidence that exhaustive enumeration should be enabled.

## Integrity and validation

The runner’s `M4/final.json` remains unchanged; its SHA-256 is `d63d0cf49dfe542495890d814642e775e5f47ed7ca10ef90aa6cc8d4e2f71f16`. The machine-readable post-run audit is `qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_m4_20260926/m4_final_audit.json`.

Compact process manifests and logs are committed with this report. A path-specific `.gitattributes` rule stores these Windows process logs as byte-exact binary evidence, preserving their CRLF bytes and SHA-256. Large per-case outputs (`raw.npz`, case telemetry, and the case result/failure records) remain local and ignored by Git; their SHA-256 values are recorded in the audit JSON. They have not been deleted or rewritten.

Before execution, the runner’s targeted tests passed (`3 passed`), `py_compile` passed, and `git diff --check` passed. Ruff was unavailable in the environment and is not claimed as passed. No full repository suite was run. The run itself introduced no production mechanics or threshold change.

## Status

```text
M4_STICK = PASS_DIAGNOSTIC_GATES (general audit WARNING retained)
M4_SLIP = FAIL_CLOSED at step 7
M4_CAMPAIGN = EXPERIMENTAL_EXECUTION_PARTIAL_FAIL_CLOSED
M3_TO_M4_STICK = DESCRIPTIVE_ONLY
M3_TO_M4_SLIP = NOT_AVAILABLE
FORMAL_WP08_QUALIFICATION = NO
WP08_POINTS_AWARDED = NO
PRODUCTION_MECHANICS_CHANGED_BY_M4 = NO
THRESHOLDS_CHANGED = NO
FULL_TEST_SUITE = NOT_RUN
PUSH_OR_MERGE = NOT_PERFORMED
```

Next step: analyze the frozen step-7 slip telemetry and formulate a prospective remediation/experiment. Any changed mechanics or rerun requires a new source/contract binding and separate authorization; do not reinterpret this failed case as a pass.
