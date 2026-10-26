# Local autonomous development policy

`DEVELOPMENT_AUTONOMOUS` is a local development workflow, separate from `QUALIFICATION_RELEASE`. Its finite FEM scope is configured in `development_autonomous_policy.json` and is limited to the registered worktrees below:

- D01: exact M1/M2/M3 native exploratory nodes for projected damping/residual flexibility, with per-node limits of one M1, one M2 and three M3 attempts.
- C01: exact prospective A/B legacy and `dimensional_v1` benchmark/mechanics-diagnostic nodes.
- E01: exact pointwise constitutive mathematics only; element assembly and FEM remain excluded.
- WP12 WP07: reduced-harmonic serialization and small calculations, on `fix/wp12-wp07-serialization`.
- WP12 TET4: bounded convergence and formulation comparisons, on `experiment/wp12-tet4-convergence`.
- WP12 elements: HEX8-SRI and element regressions, on `test/wp12-fem-regressions`.

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

## WP12 registration and execution

After retrieving the common configuration commit into the scientific branch, inspect the exact test function and declare its planned DDL count and selection basis. Registration parses the test module with Python's AST without importing or running it, checks the clean worktree identity and baseline, and fingerprints the solver/test sources. It refuses TET4 selections above 50,000 DDL, elements selections above 30,000 DDL, and dynamics selections above 12 DDL before any attempt is reserved. WP07 also records its selected DDL count but has no additional DDL ceiling in this mandate. Dynamics is capped at 9 total attempts, at most 3 per nodeid, and 300 seconds per attempt. If a source file changes, register a new revision; prior registration and attempt records remain preserved. Commit the source and registration before preparing the execution manifest so the exact worktree is frozen. The dynamic preparation currently proposes these exact candidates. They remain refused until each is registered against its current clean source fingerprint:

```text
tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables
tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation
tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization
```

Example for one TET4 node (replace the nodeid, count and basis with the reviewed case):

```powershell
& 'C:\Python313\python.exe' -B scripts\development_autonomous.py register-nodeid `
  --worktree wp12_tet4 `
  --target 'tests/unit/test_wp12_tet4.py::test_one_case' `
  --reason 'Review one bounded convergence case' `
  --selected-dofs 48000 `
  --selection-basis 'TET4 mesh level L3; planned assembled system has 48,000 DDL'

git add tests/unit/test_wp12_tet4.py development_autonomous_policy.json
git commit -m 'test: register bounded WP12 TET4 case'

& 'C:\Python313\python.exe' -B scripts\development_autonomous.py prepare-manifest `
  --worktree wp12_tet4 `
  --target 'tests/unit/test_wp12_tet4.py::test_one_case' `
  --authorization-id 'wp12-tet4-case-0001'

# The Owner fills the exact case decision in the returned JSON file.
& 'C:\Python313\python.exe' -B scripts\development_autonomous.py test `
  --scope fem_exploratory --worktree wp12_tet4 `
  --target 'tests/unit/test_wp12_tet4.py::test_one_case' `
  --execution-manifest 'E:\QFSolverAgents\evidence\tet4\authorizations\wp12_tet4\wp12-tet4-case-0001.json' `
  --reason 'Record the result for the inspected L3 convergence case'
```

The policy runs one exact nodeid per attempt. WP07 has a 10-total-attempt mission cap at 300 seconds per attempt. TET4 has a 12-total-case/attempt cap at 900 seconds per attempt. Elements has a 20-total-case/attempt cap at 300 seconds by default; a registration may request 900 seconds only with a case-specific reason. Example: add `--timeout-seconds 900 --timeout-reason '...'` to the elements registration command. Repeated attempts consume the same mission cap. A per-case execution manifest must bind the exact source, registration, controller, nodeid and budget; the template stays refused until an Owner decision marks that case authorized. Authorization IDs are single-use.

Each WP12 worktree has a separate evidence and attempt-ledger directory under `E:\QFSolverAgents\evidence`. A shared nonblocking lock in `.wp12-coordination` allows at most two WP07 or dynamics `parallel` runs; TET4 and elements reserve both slots, excluding every other WP12 FEM run until they finish. A busy slot is refused before an attempt is reserved. These records track development cases and never imply formal qualification.

## Budgets and their meaning

| Scope | Wall time | RSS | Captured output | Temp files | Attempts/node |
|---|---:|---:|---:|---:|---:|
| D01 M3 | 180 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 256 MiB sampled monitor | 3 |
| C01 exact nodes | 1200 s | 2 GiB soft monitor | 256 MiB aggregate, 128 MiB/stream | 512 MiB sampled monitor | 3 |
| E01 math-only | 900 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 128 MiB sampled monitor | 3 |
| WP12 WP07 | 300 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 10 |
| WP12 TET4 | 900 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 12; selected DDL ≤50,000 |
| WP12 elements | 300 s default, 900 s exceptional | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 20; selected DDL ≤30,000 |
| WP12 dynamics | 300 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 9 total; ≤3/node; selected DDL ≤12 |

The captured stdout/stderr byte caps are enforced by the launcher (excess output is discarded and the run is stopped). Timeout, RSS, process count, temporary/archive size, and free-disk checks are sampled by a watchdog and are not equivalent to a Windows Job Object, hard memory/commit limit, NTFS quota, or sandbox. Process-tree termination is best-effort. The test process is not prevented from writing outside its pytest temp directory. Use no unrelated concurrent FEM workload; D01/C01 calls serialize with each other, and WP12 calls coordinate through their separate two-slot lock.

The standard `unit` and `integration` scopes accept one explicit test-function nodeid at a time; a directory, module, or whole-suite request is refused so it cannot implicitly activate unregistered FEM tests. Direct `python -m pytest` is permitted for routine development but does not receive this launcher's source-origin check, run archive, attempt accounting, or monitored budgets.

## Qualification remains separate

This mode may diagnose failures, support in-scope fixes, run development regressions, and archive exploratory output. It cannot consume or rebind a frozen qualification manifest, change acceptance criteria, create a certificate, mark C4/WP05 qualified, close D01/C01/E01/WP12/WP13, merge, or release. Qualification results and historical evidence are unchanged. No E01 FEM run is authorized here. Codex/Windows/platform approvals, if any, cannot be suppressed by this project-level workflow.
