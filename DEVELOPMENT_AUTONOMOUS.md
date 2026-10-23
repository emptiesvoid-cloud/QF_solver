# Local autonomous development policy

`DEVELOPMENT_AUTONOMOUS` is a local development workflow, separate from `QUALIFICATION_RELEASE`. Its finite FEM scope is configured in `development_autonomous_policy.json` and is limited to three registered worktrees:

- D01: one M3 native exploratory node for projected damping/residual flexibility.
- C01: exact prospective A/B legacy and `dimensional_v1` benchmark/mechanics-diagnostic nodes.
- E01: exact pointwise constitutive mathematics only; element assembly and FEM remain excluded.

Each worktree entry binds a canonical checkout path, Git root, branch, baseline commit ancestry, `src/solveur` package location, exact pytest nodeids, and resource policy. The launcher refuses a different root/branch, an unrelated history, a test outside the allowlist, or a `solveur` import from another checkout. It records HEAD/tree/status and a source fingerprint per attempt. Do not copy integration files into D01 or C01.

## Monitored invocation

From the integration worktree, an approved exact target is started without an interactive prompt, for example:

```powershell
& 'C:\Python313\python.exe' -B scripts/development_autonomous.py test `
  --scope fem_exploratory --worktree d01 `
  --target 'tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]' `
  --reason 'Investigate projected damping skew after reviewing the last diagnostic'
```

C01 uses `--scope fem_exploratory --worktree c01` with one exact nodeid from the policy. E01 uses `--scope math_non_fem --worktree e01` with one listed pointwise-material/tangent nodeid. Every command runs exactly one target and records stdout/stderr, hashes, Git identity, runtime observations, and a JSON outcome below `.codex/development-runs/worktrees/<id>/`. Standard scopes are separately stored under `.codex/development-runs/standard/<scope>/`. Controller, policy, and plugin hashes are recorded alongside the scientific worktree identity.

The D01/C01 exploratory nodes share a nonblocking OS file lock, so only one scenario launched through this runner can be active. A persistent procedural ledger limits each registered nodeid to three attempts for mandate `DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1`. It refuses a repeat when both the relevant source fingerprint and the documented reason are unchanged. No attempt is retried automatically. The ledger and logs are local development records, not cryptographic authorization.

The D01 pytest module is normally skipped as `NATIVE_AUTH_REQUIRED`. For only the exact registered M3 node, the development pytest plugin removes that one skip marker after collection; it refuses any other node or a missing/changed marker. No test source, scientific equation, threshold, C4 gate, official runner, or qualification manifest is altered. D01's existing `QF_WP_D01_BJ_SOURCE_SHA` input is set to the actual development worktree HEAD for traceability; this does not create qualification provenance.

## Budgets and their meaning

| Scope | Wall time | RSS | Captured output | Temp files | Attempts/node |
|---|---:|---:|---:|---:|---:|
| D01 M3 | 180 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 256 MiB sampled monitor | 3 |
| C01 exact nodes | 1200 s | 2 GiB soft monitor | 256 MiB aggregate, 128 MiB/stream | 512 MiB sampled monitor | 3 |
| E01 math-only | 900 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 128 MiB sampled monitor | 3 |

The captured stdout/stderr byte caps are enforced by the launcher (excess output is discarded and the run is stopped). Timeout, RSS, process count, temporary/archive size, and free-disk checks are sampled by a watchdog and are not equivalent to a Windows Job Object, hard memory/commit limit, NTFS quota, or sandbox. Process-tree termination is best-effort. The test process is not prevented from writing outside its pytest temp directory. Use no unrelated concurrent FEM workload; D01/C01 launcher calls are serialized with each other.

The standard `unit` and `integration` scopes accept one explicit test-function nodeid at a time; a directory, module, or whole-suite request is refused so it cannot implicitly activate unregistered FEM tests. Direct `python -m pytest` is permitted for routine development but does not receive this launcher's source-origin check, run archive, attempt accounting, or monitored budgets.

## Qualification remains separate

This mode may diagnose failures, support in-scope fixes, run development regressions, and archive exploratory output. It cannot consume or rebind a frozen qualification manifest, change acceptance criteria, create a certificate, mark C4/WP05 qualified, close D01/C01/E01, merge, or release. Qualification results and historical evidence are unchanged. No E01 FEM run is authorized here. Codex/Windows/platform approvals, if any, cannot be suppressed by this project-level workflow.
