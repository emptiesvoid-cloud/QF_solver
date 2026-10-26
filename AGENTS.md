# QF Solver execution policy

## `DEVELOPMENT_AUTONOMOUS`

- Routine local development tests run noninteractively. No per-command Owner prompt is required inside the registered scope.
- The generic `unit` and `integration` scopes require one explicit test-function nodeid at a time; directory/module/full-suite targets are refused so FEM tests are not enabled implicitly.
- The exact D01, C01, and E01 worktrees, branches, baseline ancestry, solver source roots, nodeids, and budgets are registered in `development_autonomous_policy.json`. The WP12 WP07, TET4, elements, and dynamics scopes are also registered there with separate mandates, evidence roots, case/attempt caps, and resource envelopes.
- For monitored FEM exploration, invoke only `scripts/development_autonomous.py` with an exact registered nodeid, its worktree ID, and a short diagnostic reason. The current D01 v2 envelope authorizes only the three exact M1/M2/M3 projected-damping/residual-flexibility nodeids, with limits of one M1 attempt, one M2 attempt, and three M3 attempts. C01 remains limited to the listed prospective legacy/dimensional and mechanics nodes. E01 is limited to the listed pointwise constitutive-math nodes; no E01 FEM node is authorized.
- The runner verifies the canonical Git root, expected branch, baseline ancestry, exact nodeid, source inventory, and in-child `solveur.__file__`. It serializes D01/C01 scenarios through a shared OS file lock. D01 v2 uses a separate attempt ledger linked by SHA-256 to the immutable v1 ledger; it never edits the old three failed M3 entries. Each command is one attempt; it never retries by itself. A further attempt needs a classified source/instrumentation/launcher change or a separately identified diagnostic hypothesis.
- The D01 development launcher removes only the `NATIVE_AUTH_REQUIRED` skip from one exact registered M1, M2, or M3 test at a time. It does not change D01 test sources, qualification settings, thresholds, or evidence status. This is a local workflow authorization, not a security boundary.
- E01 math-only scope must never be expanded to element assembly, FEM, or its qualification worker. Do not copy integration changes into scientific worktrees.
- WP12 scopes use `scripts/development_autonomous.py register-nodeid` to add one exact `tests/unit/...::test_function` after checking its clean worktree branch, baseline ancestry, path, and Python AST without importing or running the test. Registration records the rationale, source fingerprint, selected DDL count, and selection basis. TET4 selections above 50,000 DDL, elements selections above 30,000 DDL, and dynamics selections above 12 DDL are refused before an attempt is reserved or a test starts. A source change requires an inspected registration revision; earlier registration records remain in history.
- Before a WP12 FEM attempt, use `prepare-manifest` to create a source-bound `PREPARED_NOT_AUTHORIZED` record; an exact Owner decision must approve that case before `test --execution-manifest` can run. The manifest is a development execution gate, not qualification evidence. The launcher also requires the scientific worktree to be clean and records the manifest ID as single-use in the attempt ledger.
- WP12 limits are mission-wide: WP07 allows 10 total attempts at up to 300 seconds each; TET4 allows 12 total cases/attempts at up to 900 seconds each; elements allows 20 total cases/attempts at 300 seconds by default, with 900 seconds only for a registered case carrying an explicit reason; dynamics allows 9 total attempts, at most 3 per nodeid, at 300 seconds each. Each attempt runs one exact registered nodeid. The selected DDL count and timeout are checked before launch and written to the durable attempt record; the child also receives `QF_DEV_SELECTED_DOFS`, `QF_DEV_MAX_FEM_CASES`, and, where set, `QF_DEV_MAX_DOFS` so the test can assert the declared selection before assembly.
- WP12 execution records and attempt ledgers use each mission's separate `E:\QFSolverAgents\evidence\...` directory. A shared slot lock under `E:\QFSolverAgents\evidence\.wp12-coordination` allows at most two `parallel` cases, while `exclusive` cases reserve both slots. TET4 and elements use the exclusive class; dynamics shares the bounded parallel slots with WP07. A busy slot is refused before an attempt is reserved. These procedural records and sampled resource limits do not constitute OS quotas or formal qualification.
- Use the launcher for timeout/output/RSS/process/temp monitoring and durable per-attempt logs. RSS, process counts, temporary/archive sizes, and free-disk polling are observations/soft controls except for captured stdout/stderr byte caps and the procedural attempt ledger. This is not a sandbox or an OS memory/disk quota.
- Direct `pytest` remains available for ordinary development, but it does not inherit the launcher's budgets, attempt ledger, source-origin check, or archive guarantees. Use the launcher for the registered FEM exploratory nodes.

## `QUALIFICATION_RELEASE`

- Development authorization never authorizes frozen scientific qualification, certificate evidence, acceptance-threshold changes, merge, or release.
- Preserve qualification runners, manifests, Owner gates, thresholds, evidence namespaces, and historical results. Never use a development record as a qualification PASS or certificate.
- A failed exploratory FEM test remains a development failure/diagnostic. It does not promote or rewrite D01, C01, E01, C4, WP05, or general qualification status.
- Codex, Windows, and OS-level prompts remain outside this repository policy; do not bypass them.

## `QUALIFICATION_LOCAL_VV`

- The Owner has approved the principle of ordinary local scientific verification on the Owner's Windows workstation. This is a separate, non-attested V&V route; it is not a security sandbox, a qualification certificate, or release approval.
- A policy-level approval does not authorize a campaign. Every scientific run requires a frozen case manifest and a separate explicit Owner decision binding the exact manifest hash, science/test/runner identities, case ID, exact nodeid or fixed benchmark entry point, environment, output location, attempt limit, oracle, and acceptance criteria.
- Run one exact nodeid or one reviewed fixed benchmark entry point per process. Do not accept arbitrary shell commands, directories, wildcards, full suites, implicit retries, or mutable criteria. The local runner must construct the argument vector without a shell.
- Before execution, verify the clean frozen science checkout, separately identified runner and tests, exact file hashes, Python environment, `solveur.__file__`, package versions, and controlled numerical thread variables. A mismatch denies the run.
- Write every attempt to a new case/run directory outside source and historical evidence trees. Refuse overwrite. Preserve command, environment, stdout/stderr, JUnit, structured results when exposed, exit status, hashes, warnings, failures, and an immutable-per-attempt receipt. A retry is a new Owner-reviewed attempt; never replace or delete a failed result.
- Distinguish `PYTEST_PASS_ONLY` from an oracle result and from any qualification decision. Classify test assertion failures, infrastructure errors, timeouts, interruptions, and inconclusive outcomes separately. Missing numerical observables remain `NOT_EXPOSED`; do not infer them from a green test.
- An Owner, operator, and reviewer retain separate responsibilities. Local files and hashes are not cryptographic proof of authorship or tamper-proof storage; archive accepted records in an Owner-controlled location. Do not claim hard CPU, memory, process-tree, or filesystem isolation unless the selected OS mechanism demonstrably enforces it.
- This route does not modify or bypass the WP12-A/B/C signed runner, its trust requirements, refusal behavior, manifests, or evidence. It does not expand `DEVELOPMENT_AUTONOMOUS`; development runs remain governed by their registered policy and cannot be relabeled as V&V.
- WP12 remains OPEN until its own approved gate and Owner disposition. No local run authorizes a maturity promotion, release, publication, tag, or merge.

## Technical knowledge base

- Use [docs/ai/INDEX.md](docs/ai/INDEX.md) to orient yourself in the technical documentation.
- Consult specialized knowledge-base pages according to the task.
- Verify applicable contracts, current source, and recorded evidence before technical changes or claims.
- This knowledge base does not replace or override the safety and execution rules in this file.
