# QF Solver execution policy

## `DEVELOPMENT_AUTONOMOUS`

- Routine local development tests run noninteractively. No per-command Owner prompt is required inside the registered scope.
- The generic `unit` and `integration` scopes require one explicit test-function nodeid at a time; directory/module/full-suite targets are refused so FEM tests are not enabled implicitly.
- The exact D01, C01, and E01 worktrees, branches, baseline ancestry, solver source roots, nodeids, and budgets are registered in `development_autonomous_policy.json`.
- For monitored FEM exploration, invoke only `scripts/development_autonomous.py` with an exact registered nodeid, its worktree ID, and a short diagnostic reason. The current D01 v2 envelope authorizes only the three exact M1/M2/M3 projected-damping/residual-flexibility nodeids, with limits of one M1 attempt, one M2 attempt, and three M3 attempts. C01 remains limited to the listed prospective legacy/dimensional and mechanics nodes. E01 is limited to the listed pointwise constitutive-math nodes; no E01 FEM node is authorized.
- The runner verifies the canonical Git root, expected branch, baseline ancestry, exact nodeid, source inventory, and in-child `solveur.__file__`. It serializes D01/C01 scenarios through a shared OS file lock. D01 v2 uses a separate attempt ledger linked by SHA-256 to the immutable v1 ledger; it never edits the old three failed M3 entries. Each command is one attempt; it never retries by itself. A further attempt needs a classified source/instrumentation/launcher change or a separately identified diagnostic hypothesis.
- The D01 development launcher removes only the `NATIVE_AUTH_REQUIRED` skip from one exact registered M1, M2, or M3 test at a time. It does not change D01 test sources, qualification settings, thresholds, or evidence status. This is a local workflow authorization, not a security boundary.
- E01 math-only scope must never be expanded to element assembly, FEM, or its qualification worker. Do not copy integration changes into scientific worktrees.
- Use the launcher for timeout/output/RSS/process/temp monitoring and durable per-attempt logs. RSS, process counts, temporary/archive sizes, and free-disk polling are observations/soft controls except for captured stdout/stderr byte caps and the procedural attempt ledger. This is not a sandbox or an OS memory/disk quota.
- Direct `pytest` remains available for ordinary development, but it does not inherit the launcher's budgets, attempt ledger, source-origin check, or archive guarantees. Use the launcher for the registered FEM exploratory nodes.

## WP12 development scopes

- The registered WP12 missions are `wp12_wp07`, `wp12_tet4`, and `wp12_elements`. Each has its own exact branch, checkout, external evidence directory, mandate ID, baseline `2aa994f34900f39bef8df9db5fb025157fb694bb`, source root, budget, and shared-resource class in `development_autonomous_policy.json`.
- New test functions are added only with `python scripts/development_autonomous.py register-nodeid --worktree <wp12_id> --target tests/unit/test_module.py::test_function --reason "..."`. This inspects the source with Python AST parsing; it does not import or run the test. Registration records are append-only, capped per mission, and bound to the current test-source fingerprint.
- The registration command updates the policy file in the scientific worktree. Commit the test/source and registrations, then leave the worktree clean before preparing or running an FEM node. The runner refuses a dirty WP12 source worktree and refuses any nodeid whose registered source fingerprint has changed.
- `prepare-manifest` writes a source/controller-bound template marked `PREPARED_NOT_AUTHORIZED`; it does not authorize or launch FEM. A separate explicit Owner authorization is required before changing the template decision to `OWNER_AUTHORIZED`. The approved manifest is specific to one worktree, nodeid, source fingerprint, controller, and budget. It may cover planned retries of that unchanged nodeid until the mission or per-node cap is exhausted; source/controller changes require a newly prepared and approved manifest.
- Actual WP12 FEM attempts must use `python scripts/development_autonomous.py test --scope fem_exploratory --worktree <wp12_id> --target <exact_registered_nodeid> --reason "..." --execution-manifest <approved_manifest.json>`. One invocation selects one exact pytest nodeid. The durable external ledger caps total attempts at 10 for WP07, 12 for TET4, and 20 for elements, with matching per-node caps. No automatic retry occurs.
- WP07 uses 300 seconds and at most two shared light-run slots. TET4 uses 900 seconds, a 50,000 DDL target, and exclusive FEM access. Elements uses 300 seconds by default, with a 900-second maximum only when the separately approved manifest includes a 20-to-300-character exception reason; its target is 30,000 DDL and FEM access is exclusive. Every attempt is configured for one FEM case. Timeout and captured-output caps are enforced by the launcher; RSS, process count, temporary/archive size, and free disk are soft observations. DDL and one-case-per-attempt limits are passed to the child as `QF_DEV_MAX_DOFS` and `QF_DEV_MAX_FEM_CASES`; the selected test must honor them, since the launcher cannot enforce solver allocations or count internal solver calls as an OS quota.
- All WP12 missions share `E:\QFSolverAgents\evidence\.wp12-coordination` for up to two light-run slots. Heavy TET4/elements runs take both slots. Each mission writes to its own evidence directory; benchmark execution is not enabled as a separate scope.
- This configuration-preparation mission does not itself launch FEM. A prepared template must remain unauthorized until a separate Owner decision is recorded. Synthetic configuration tests may validate both refusal and manifest parsing, but must never invoke a solver or FEM test.

Example setup for TET4 (repeat with the corresponding mission ID and registered test):

```powershell
python scripts/development_autonomous.py register-nodeid --worktree wp12_tet4 --target tests/unit/test_tet4_convergence.py::test_mesh_case --reason "Register one exact convergence case"
git add tests/unit/test_tet4_convergence.py development_autonomous_policy.json
git commit -m "Register WP12 TET4 development node"
python scripts/development_autonomous.py prepare-manifest --worktree wp12_tet4 --target tests/unit/test_tet4_convergence.py::test_mesh_case --authorization-id wp12-tet4-case-0001
# Record the separate Owner decision in the returned manifest, then use that exact path:
python scripts/development_autonomous.py test --scope fem_exploratory --worktree wp12_tet4 --target tests/unit/test_tet4_convergence.py::test_mesh_case --reason "Evaluate the registered mesh-convergence case" --execution-manifest E:\QFSolverAgents\evidence\tet4\authorizations\wp12_tet4\wp12-tet4-case-0001.json
```

## `QUALIFICATION_RELEASE`

- Development authorization never authorizes frozen scientific qualification, certificate evidence, acceptance-threshold changes, merge, or release.
- Preserve qualification runners, manifests, Owner gates, thresholds, evidence namespaces, and historical results. Never use a development record as a qualification PASS or certificate.
- A failed exploratory FEM test remains a development failure/diagnostic. It does not promote or rewrite D01, C01, E01, C4, WP05, or general qualification status.
- Codex, Windows, and OS-level prompts remain outside this repository policy; do not bypass them.
