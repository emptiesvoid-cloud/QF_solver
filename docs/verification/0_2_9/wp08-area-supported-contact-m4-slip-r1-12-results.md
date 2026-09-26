# WP08 area-supported contact — R1.12 M4 slip results

## Verdict

`FAIL_CLOSED_NUMERICAL`. The single prospective M4 `slip_target` execution
reached load step 7, accepted six steps, rejected step 7, and exited with code
1 after a `NumericalConvergenceError`. No retry was made. The R1.11 optimizer
stop-tolerance change did not bring the physical active-slip residual within
the frozen gate.

## Frozen execution

- Branch / execution source: `codex/wp08-area-contact-r1-12-m4` /
  `0f9e31e61987e9a8f1ccd154f242dc4071f536cb`.
- Runner commit: `0f9e31e61987e9a8f1ccd154f242dc4071f536cb`.
- R1.12 contract SHA-256:
  `0c6ce875472fde1fee797da59ab6dbf54d6849834ff477c28230de95bc0e6b76`.
- Execution-binding SHA-256:
  `7688c50fbe03f23d19b1cb45326368d8f8e2db2ad8bc692417585e20787757b8`.
- Source bundle SHA-256:
  `87eef7eda23b27577f4683502b104c40c72e8ffd1db02a4c321b91248c9b8e75`.
- R1.11 M1 contract: `95146b015cc4a76ee413593e1dc40a9cc0d4de2c7f01f1c7fc15cbc6ff4a6ca9`.
- R1.11 M2/M3 contract: `55c7d48b35f3fdaabad1e3460182de8b67a9c85fd777780f7efce5eae21803bf`.
- R1.11 M2/M3 binding: `4b900be6c08178eb53ef721f161b045cb7ecacb0b011049d11ea96b7fb62b5b0`.
- One M4 slip process only; no M1/M2/M3 or stick rerun, reference, replay,
  tuning, or fallback-policy change.

The historical M4 failure remained read-only and hash-verified. R1.11 M1,
M2, and M3 stick/slip cases were also read-only; all six retained
`PASS_DIAGNOSTIC_GATES`. Their refinement classification remains
`NOT_CLASSIFIED_NO_FROZEN_THRESHOLD`.

## Numerical result

| Measure | R1.12 observation | Frozen criterion | Outcome |
|---|---:|---:|---|
| Failure step | 7; 6 accepted, 1 rejected | 8 steps required | Fail closed |
| Direct active-set iteration | 25; 10 active sets visited | cap 25 | Cap reached |
| Active-slip contacts / unknowns | 45 / 90 | unchanged | Candidate rejected |
| Maximum scaled contact residual | `1.0519097154830292e-8` | `<= 1e-9` | Fail, 10.52× gate |
| Physical residual norm | `1.5037868322441332e-7` | `<= 1e-9` per frozen normalized gate | Fail |
| Least-squares termination | status 3, `xtol`; optimizer reports success | optimizer success alone is insufficient | Rejected by physical residual gate |
| Optimizer evaluations | 8 | internal `xtol=ftol=gtol=1e-12` | Stop tolerance did not resolve plateau |
| Optimizer optimality / gradient infinity norm | `3.929119915511927e-9` | `gtol=1e-12` | Stationarity criterion not reached |
| Semismooth refinement | line search failed; 0 accepted refinements | existing budget retained | Fail closed |
| Coupled projection seed | 45 frictional contacts; seed rejected at residual `2.056e-8` | physical gate `1e-9` | Fail closed |
| Exhaustive enumeration | 81 contacts; deterministic limit 8; 1 candidate attempted | guard unchanged | Search stopped by guard |

The previous forensic R2 record had the same maximum scaled residual
(`1.0519097154830292e-8`) and physical residual norm
(`1.5037868322441332e-7`), with three optimizer evaluations and unspecified
optimizer tolerances. R1.12 used eight evaluations and explicit `1e-12`
optimizer tolerances, but the accepted physical residual did not change. This
points to a residual/line-search or nonsmooth-root stagnation, not merely an
optimizer stopping tolerance that was too loose. This is an interpretation of
the recorded outcomes, not proof of a unique root cause.

The failure is numerical, not an infrastructure crash: the child process
completed, serialized the nested exception and telemetry, and exited 1. The
81-contact exhaustive search was not expanded. No final M4 displacement/raw
solution was emitted because the increment failed.

## Integrity and governance

- Contract and binding re-verification: PASS after execution.
- R1.11 parent campaign verification: six cases PASS; hashes rechecked.
- M4 process PID `41756`, exit code `1`, elapsed `69.5211 s`.
- Failure JSON SHA-256:
  `482b1529e0cd6670716170c10e1e6e3d31dbc83d133274950d0c0315c08a906f`.
- Telemetry JSONL SHA-256:
  `5236f986a2125ca7d5618b63a1bc65130941bc17d522f2369dd804ad6b892c48`.
- Process manifest SHA-256:
  `6168aaa4a60a398b69e299363a8c2762a4130d823fa543e8ef1ffca1f89a35c8`.
- M4 final summary SHA-256:
  `2f38fb375cb5c6ec95313f20391522a5c3f575ce07b16707fc0930b2a8a37e53`.
- No solver process remains. Source tree is clean apart from the preserved,
  untracked R1.11 and R1.12 qualification evidence directories.
- R1.12 changed no production mechanics; the executed source includes the
  previously committed R1.11 optimizer correction. Physical residual gate,
  meshes, loads, material, contact parameters, iteration limits, and
  enumeration/fallback policy were not changed.
- Targeted tests before freeze: 28 passed. Ruff was unavailable; no full test
  suite was run. No replay or independent global FEM reference was run.
- No WP08 points, ledger update, merge, or push.

## Status

```text
R1_11_M1_M2_M3 = PASS_DIAGNOSTIC_GATES (refinement unclassified)
R1_12_M4_SLIP = FAIL_CLOSED_NUMERICAL, step 7
R1_12_CAMPAIGN = EXPERIMENTAL_DIAGNOSTIC_ONLY
WP08_FORMAL_QUALIFICATION = NOT_ESTABLISHED
WP08_POINTS_AWARDED = NO
RETRY = NO
MERGE_OR_PUSH = NO
```

Next technical work should inspect the active-slip residual/Jacobian scaling
and the failed semismooth line-search direction at step 7. Do not raise the
iteration cap, relax the physical residual gate, or expand enumeration merely
to turn this execution into a pass. Any new solve needs another prospective
contract, unique output directory, and explicit authorization.
