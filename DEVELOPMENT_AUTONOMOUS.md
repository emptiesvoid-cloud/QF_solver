# Local autonomous development policy

`DEVELOPMENT_AUTONOMOUS` is a local development workflow, separate from `QUALIFICATION_RELEASE`. Its finite FEM scope is configured in `development_autonomous_policy.json` and is limited to the registered worktrees below:

- D01: exact M1/M2/M3 native exploratory nodes for projected damping/residual flexibility, with per-node limits of one M1, one M2 and three M3 attempts.
- C01: exact prospective A/B legacy and `dimensional_v1` benchmark/mechanics-diagnostic nodes.
- E01: exact pointwise constitutive mathematics only; element assembly and FEM remain excluded.
- WP12 WP07: reduced-harmonic serialization and small calculations, on `fix/wp12-wp07-serialization`.
- WP12 TET4: bounded convergence and formulation comparisons, on `experiment/wp12-tet4-convergence`.
- WP12 elements: HEX8-SRI and element regressions, on `test/wp12-fem-regressions`.
- WP12 dynamics: exact WP04–WP07 modal, harmonic, Newmark, and base-acceleration nodes, on `codex/wp12-dynamic-harmonic-verification`.

Each worktree entry binds a canonical checkout path, Git root, branch, baseline commit ancestry, `src/solveur` package location, exact pytest nodeids, and resource policy. The launcher refuses a different root/branch, an unrelated history, a test outside the allowlist, or a `solveur` import from another checkout. It records HEAD/tree/status and a source fingerprint per attempt. Do not copy integration files into D01 or C01.

## Monitored invocation

From the shared controller checkout (`E:\QFSolverAgents\wp12-policy-final`), an approved exact target is started without an interactive prompt, for example:

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

Use the shared controller checkout `E:\QFSolverAgents\wp12-policy-final`; do not pull its branch into or commit policy files from a scientific worktree. Inspect and commit the exact scientific test in its own clean branch. Registration parses the test module with Python's AST without importing or running it, checks the clean worktree identity and baseline, and fingerprints the solver/test sources. It normally accepts `tests/unit/...` nodeids; `wp12_elements` has a narrowly scoped exception for only the two registered HEX8-SRI diagnostics in `tests/verification/test_wp12_hex8_sri_diagnostics.py`. It refuses TET4 selections above 50,000 DDL and elements selections above 30,000 DDL before any attempt is reserved. WP07 also records its selected DDL count but has no additional DDL ceiling in this mandate. If a source file changes, register a new revision; prior registration and attempt records remain preserved. Register all intended nodeids before preparing manifests: the manifest binds the common controller policy hash, so a later policy registration invalidates manifests prepared earlier.

Example for one TET4 node (replace the nodeid, count and basis with the reviewed case):

```powershell
$controller = 'E:\QFSolverAgents\wp12-policy-final'
$python = 'C:\Python313\python.exe'
$target = 'tests/unit/test_wp12_tet4.py::test_one_case'
& $python -B "$controller\scripts\development_autonomous.py" register-nodeid `
  --worktree wp12_tet4 `
  --target $target `
  --reason 'Review one bounded convergence case' `
  --selected-dofs 48000 `
  --selection-basis 'TET4 mesh level L3; planned assembled system has 48,000 DDL'

& $python -B "$controller\scripts\development_autonomous.py" prepare-manifest `
  --worktree wp12_tet4 `
  --target $target `
  --authorization-id 'wp12-tet4-case-0001'

# The Owner fills the exact case decision in the returned JSON file.
& $python -B "$controller\scripts\development_autonomous.py" test `
  --scope fem_exploratory --worktree wp12_tet4 `
  --target $target `
  --execution-manifest 'E:\QFSolverAgents\evidence\tet4\authorizations\wp12_tet4\wp12-tet4-case-0001.json' `
  --reason 'Record the result for the inspected L3 convergence case'
```

The policy runs one exact nodeid per attempt. WP07 has a 10-attempt mission cap at 300 seconds per attempt. TET4 has a 12-attempt/case cap at 900 seconds per attempt. Elements has a 20-attempt/case cap, 300 seconds by default; a registration may request 900 seconds only with a case-specific reason. Dynamics has a 10-attempt-per-nodeid cap, 130 total attempts, and a 300-second timeout. Example: add `--timeout-seconds 900 --timeout-reason '...'` to the elements registration command. Repeated attempts consume the same mission cap. A per-attempt execution manifest must bind the exact source, registration, controller, nodeid and budget; the template stays refused until an Owner decision marks that attempt authorized. Authorization IDs are single-use. The Owner's written development authorization may be referenced for each allowed attempt; the policy does not create additional authority.

Each WP12 worktree has a separate evidence and attempt-ledger directory under `E:\QFSolverAgents\evidence`. The child receives its registered `QF_DEV_EVIDENCE_ROOT`; tests must keep evidence beneath that root. A shared nonblocking lock in `.wp12-coordination` allows up to three `parallel` runs, so the TET4, elements, and dynamics agents can run one exact registered case each at the same time. A fourth simultaneous case is refused before an attempt is reserved. All four scopes use sampled 4096 MiB RSS soft limits; these are per-process observations and do not provide a hard aggregate memory guarantee. These records track development cases and never imply formal qualification.

The `wp12_dynamics` profile is bound to `E:\QFSolverAgents\wp12-dynamics` on `codex/wp12-dynamic-harmonic-verification`. Its 13 exact WP04–WP07 nodeids from `qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_EXPERIMENT_PLAN.md` are registered with source fingerprints. Each nodeid has a 300-second timeout and at most 10 attempts; one invocation runs only one exact nodeid. The checked-in allowlist does not claim a pytest PASS or authorize any change to scientific thresholds.

## Budgets and their meaning

| Scope | Wall time | RSS | Captured output | Temp files | Attempts/node |
|---|---:|---:|---:|---:|---:|
| D01 M3 | 180 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 256 MiB sampled monitor | 3 |
| C01 exact nodes | 1200 s | 2 GiB soft monitor | 256 MiB aggregate, 128 MiB/stream | 512 MiB sampled monitor | 3 |
| E01 math-only | 900 s | 2 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 128 MiB sampled monitor | 3 |
| WP12 WP07 | 300 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 10 |
| WP12 TET4 | 900 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 12; selected DDL ≤50,000 |
| WP12 elements | 300 s default, 900 s exceptional | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 20; selected DDL ≤30,000 |
| WP12 dynamics | 300 s | 4 GiB soft monitor | 64 MiB aggregate, 32 MiB/stream | 512 MiB sampled monitor | 10/nodeid; 130 total |

The captured stdout/stderr byte caps are enforced by the launcher (excess output is discarded and the run is stopped). Timeout, RSS, process count, temporary/archive size, and free-disk checks are sampled by a watchdog and are not equivalent to a Windows Job Object, hard memory/commit limit, NTFS quota, or sandbox. Process-tree termination is best-effort. The test process is not prevented from writing outside its pytest temp directory. Use no unrelated concurrent FEM workload; D01/C01 calls serialize with each other, and WP12 calls coordinate through their separate three-slot lock.

The standard `unit` and `integration` scopes accept one explicit test-function nodeid at a time; a directory, module, or whole-suite request is refused so it cannot implicitly activate unregistered FEM tests. Direct `python -m pytest` is permitted for routine development but does not receive this launcher's source-origin check, run archive, attempt accounting, or monitored budgets.

## Qualification remains separate

This mode may diagnose failures, support in-scope fixes, run development regressions, and archive exploratory output. It cannot consume or rebind a frozen qualification manifest, change acceptance criteria, create a certificate, mark C4/WP05 qualified, close D01/C01/E01/WP12/WP13, merge, or release. Qualification results and historical evidence are unchanged. No E01 FEM run is authorized here. Codex/Windows/platform approvals, if any, cannot be suppressed by this project-level workflow.
