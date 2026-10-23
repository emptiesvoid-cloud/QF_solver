# QF Solver execution policy

## `DEVELOPMENT_AUTONOMOUS`

- Routine local development tests run noninteractively. No per-command Owner prompt is required inside the registered scope.
- The generic `unit` and `integration` scopes require one explicit test-function nodeid at a time; directory/module/full-suite targets are refused so FEM tests are not enabled implicitly.
- The exact D01, C01, and E01 worktrees, branches, baseline ancestry, solver source roots, nodeids, and budgets are registered in `development_autonomous_policy.json`.
- For monitored FEM exploration, invoke only `scripts/development_autonomous.py` with an exact registered nodeid, its worktree ID, and a short diagnostic reason. D01 is limited to the M3 projected-damping/residual-flexibility node; C01 is limited to the listed prospective legacy/dimensional and mechanics nodes. E01 is limited to the listed pointwise constitutive-math nodes; no E01 FEM node is authorized.
- The runner verifies the canonical Git root, expected branch, baseline ancestry, exact nodeid, source inventory, and in-child `solveur.__file__`. It serializes D01/C01 scenarios through a shared OS file lock and persists a three-attempt-per-nodeid ledger for this Owner mandate. Each command is one attempt; it never retries by itself. A repeated attempt needs changed source or a new documented hypothesis.
- The D01 development launcher removes only the `NATIVE_AUTH_REQUIRED` skip from its one exact approved M3 test. It does not change D01 test sources, qualification settings, thresholds, or evidence status. This is a local workflow authorization, not a security boundary.
- E01 math-only scope must never be expanded to element assembly, FEM, or its qualification worker. Do not copy integration changes into scientific worktrees.
- Use the launcher for timeout/output/RSS/process/temp monitoring and durable per-attempt logs. RSS, process counts, temporary/archive sizes, and free-disk polling are observations/soft controls except for captured stdout/stderr byte caps and the procedural attempt ledger. This is not a sandbox or an OS memory/disk quota.
- Direct `pytest` remains available for ordinary development, but it does not inherit the launcher's budgets, attempt ledger, source-origin check, or archive guarantees. Use the launcher for the registered FEM exploratory nodes.

## `QUALIFICATION_RELEASE`

- Development authorization never authorizes frozen scientific qualification, certificate evidence, acceptance-threshold changes, merge, or release.
- Preserve qualification runners, manifests, Owner gates, thresholds, evidence namespaces, and historical results. Never use a development record as a qualification PASS or certificate.
- A failed exploratory FEM test remains a development failure/diagnostic. It does not promote or rewrite D01, C01, E01, C4, WP05, or general qualification status.
- Codex, Windows, and OS-level prompts remain outside this repository policy; do not bypass them.
