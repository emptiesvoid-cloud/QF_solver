# Local V&V runner — design and limits

**Status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`

## Architecture

The local runner is a small, standard-user CLI in `scripts/run_local_vv.py`, supported by:

- `scripts/local_vv/manifest.py` — JSON shape checks, exact Git identity, tracked-file SHA-256/Git blob checks, environment and import diagnostics, plus structural/binding checks for a separate Owner decision record.
- `scripts/local_vv/process.py` — fixed pytest argument builder, exact selection/JUnit parsing, direct-child timeout/log monitoring, unique file writes and hash inventory.
- `scripts/local_vv/execution.py` — read-only preflight and one-case execution/receipt flow.
- `scripts/local_vv/cli.py` — `validate` and `run` subcommands.
- `scripts/local_vv_pytest_plugin.py` — in-process exact node collection and `solveur.__file__` capture.
- `tests/unit/test_local_vv_runner.py` and `tests/fixtures/local_vv/fake_child.py` — synthetic-only tests. The separate characteristic-polynomial oracle test is scientific and is **not** part of the runner self-test suite.

The runner checkout is pinned independently from both the frozen science checkout and the tests checkout. `verify_runner_entrypoint` checks that the invoked CLI path is the path in the manifest-bound runner checkout. For this prepared campaign, tests are read from a separate tests worktree at its own commit/tree; they are not treated as though they belong to the frozen science tree.

## Control sequence

`VALIDATE` checks manifest shape, evidence-root placement, runner/science/test commit and tree, clean checkouts, exact tracked-file SHA-256 and Git blob IDs, interpreter/version, installed package versions/locations, and source import. The probe starts a distinct Python process with the named venv; it imports the frozen `solveur` package, NumPy, SciPy and threadpoolctl to report their origin/versions/native pools. It performs no analysis or matrix solve and creates no output directory.

`run` first binds the decision record to the raw manifest hash, case, exact nodeid, oracle/criteria, checkouts, Python, evidence root, one attempt and proposed budgets. It then checks identities, files and environment again, reserves a unique output directory and attempt, constructs one fixed argv without a shell, and supervises one Python child. The in-process pytest plugin records the collected nodeids and actual loaded solveur module path before test calls. The runner then checks selection, JUnit, exit status and post-run file identities; hashes outputs and writes a receipt.

No caller-provided shell text, command array, nodeid, suite path, wildcard or retry override is accepted. The `cases` array in the manifest is the only selectable scope. The supplemental Q3 oracle review is not in that array.

## Trust boundary

This runner is intentionally **non-attested**. It checks that a separate JSON decision matches the manifest, but it cannot prove who wrote or approved that JSON. It has no signature key, protected trust store, Owner account check, external approval-service query or independent archive anchor. A local decision file is not cryptographic Owner authentication. The future campaign must obtain explicit Owner review of the exact manifest hash and case outside the runner before a decision record is supplied.

The child test runs under the current user's ordinary Windows token. It can access any file that user can access. The runner does not use a restricted token, Job Object, VM, container or filesystem sandbox. It cannot guarantee descendant termination. It monitors the direct child and samples output file sizes; the wall timeout and log-size cap do not impose hard CPU, RAM or disk quotas. The process can forge its own JUnit/selection files or modify accessible evidence during execution. Pre/post hashes detect many accidental changes but do not defeat a same-user process or malicious test code.

Use only reviewed trusted source/test commits. Do not use this route where a campaign requires strong protection against child writes or resource exhaustion; move that campaign to a separately reviewed isolated environment. Accepted evidence must be copied to an Owner-controlled archive, and the copied hash must be checked.

## Results and receipts

The runner's positive execution label is `PYTEST_PASS_ONLY`, requiring one collected nodeid, one matching JUnit testcase and zero exit status. Assertion failures are `FAIL`; skips are `INCONCLUSIVE`; timeout, observed output-cap exhaustion, interruption, selection/JUnit errors and identity mutations are separately classified. A positive process label is not an oracle pass or qualification.

The receipt includes manifest and decision-file hashes, case/run/attempt IDs, the command argv and cwd, before/after Git/file identities, Python/dependency/native-thread observations, collection record, JUnit/process status, visible numeric marker status and output hashes. A missing structured `QF_VV_NUMERIC_RESULT=` payload is `NOT_EXPOSED`. Receipt files use exclusive creation. A logical attempt reservation prevents a second attempt for the same case/campaign in that evidence root, but local files remain editable by the same account.

## Synthetic validation only

The dedicated suite creates temporary JSON, logs, JUnit and fake Git/file data and starts only `fake_child.py` where process supervision is tested. It does not import QF Solver or run a QF test. Its status is runner implementation evidence only; it is not a scientific result. The exact synthetic test command is recorded in the final WP12-Q delivery report, not in the campaign manifest.
