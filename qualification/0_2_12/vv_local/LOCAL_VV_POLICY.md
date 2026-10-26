# QUALIFICATION_LOCAL_VV policy

**Status:** `POLICY_PRINCIPLE_ADOPTED; CASE_EXECUTION_NOT_AUTHORIZED`<br>
**Document status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`<br>
**Effective scope:** QF Solver v0.2.12 local verification planning; this policy does not authorize a case.

## 1. Purpose and relationship to existing policy

`QUALIFICATION_LOCAL_VV` is an ordinary, non-attested local workflow for measured verification and validation on the Owner's Windows workstation. The Owner approved the policy principle, the use of a dedicated Python environment and exact bounded cases, and the separation between local evidence and cryptographically attested qualification.

The policy is independent of `DEVELOPMENT_AUTONOMOUS` and `QUALIFICATION_RELEASE`. A development-runner authorization is not a qualification authorization. This route does not modify or reactivate the WP12-A/B/C runner, its trust model, manifests, denials or evidence. Earlier WP12-P proposal documents retain their historical `PROPOSED_NOT_EFFECTIVE` state; this page records the later policy decision without rewriting that history.

This route does not require Ed25519, an HKLM trust store, a SYSTEM broker, a dedicated Windows account, a VM, Docker, process attestation or a particular Windows build. It must not claim those protections. Windows and numerical library versions are recorded as environment diagnostics.

## 2. Approval boundary

Policy adoption is not permission to execute. Every scientific case requires a separate, explicit Owner decision in a later campaign mission. That decision must identify and bind:

- the exact manifest SHA-256 and case ID;
- the frozen science commit/tree, runner commit/tree and test/fixture identity;
- one exact nodeid or one reviewed fixed benchmark entry point;
- the Python executable, environment, import origin and controlled numerical thread variables;
- the command, working directory, output root and attempt limit;
- the oracle, contract source, acceptance criteria and stop conditions;
- timeout/output budgets and the reviewer or disposition path.

The decision record is a structured operational record. Its presence is not cryptographic proof that the named Owner authored it. The Owner must approve the exact manifest and case outside the local runner before an operator creates or uses that record. Silence, policy approval, document commit or a green synthetic runner test is not case approval.

## 3. Roles

- **Owner:** approves policy revisions, exact cases, immutable identities, criteria, environment, budgets, evidence destination and attempt count. The Owner also decides whether a result may support a qualification disposition or public communication.
- **Operator:** verifies the prepared manifest and environment, uses only the runner's exact-case interface, preserves all outputs and stops on any mismatch. The operator does not change criteria or retry silently.
- **Reviewer:** checks the raw command, identities, source/import provenance, JUnit, logs, oracle, observed values, failure classification, hashes and archive copy. The reviewer does not infer physical validation from test success.

One person may fill more than one role only when the future Owner decision says so; role overlap does not create independent review.

## 4. Case and command rules

1. Use the named clean science checkout and separately identified runner checkout. A documentation/runner commit does not replace the frozen science identity.
2. Review the selected test and all declared fixtures/configuration for hidden parameterization, solver calls, file writes, external dependencies and side effects.
3. Run one exact pytest nodeid per process. Parameterized cases require their exact bracketed IDs. Fixed benchmarks require a reviewed checked-in entry point and literal frozen arguments.
4. The local CLI constructs an argument vector without a shell. It accepts no arbitrary command, directory, wildcard, suite or caller-supplied nodeid.
5. Verify exact Git commit/tree and clean status, file SHA-256 and Git blob IDs, Python and package versions, actual `solveur.__file__`, NumPy/SciPy versions and observed native thread pools.
6. Disable pytest plugin autoload and conftest loading for the first four cases. Load only the local exact-selection plugin. Any future test requiring conftest fixtures needs a separate review and manifest revision.
7. Do not change a test assertion, tolerance, reference, input or model to obtain a pass. Any such change requires a new source/test identity and review.

## 5. Evidence and outcomes

Each attempt uses a new `campaign/case/run-id` directory outside source checkouts and historical evidence. A pre-existing attempt reservation or destination denies reuse. Preserve stdout, stderr, JUnit, actual collection selection, environment/import report, command, process status, structured observables when explicitly emitted, file hashes, warnings, failures and a receipt. Partial outputs remain; they are not overwritten or relabeled.

Outcome categories include `PYTEST_PASS_ONLY`, `FAIL`, `INCONCLUSIVE`, `TIMEOUT`, `RESOURCE_LIMIT`, `INTERRUPTED`, `INFRA_ERROR` and `DENY_EXECUTION`. A zero process exit code alone cannot establish `PYTEST_PASS_ONLY`: the exact collection record and one matching JUnit testcase must also be present. `PYTEST_PASS_ONLY` does not establish an oracle pass, physical validation, qualification, maturity promotion or WP closure.

If the test emits no structured values, record `NOT_EXPOSED`. Do not reconstruct unpublished values from an assertion or draw a publication plot from a Boolean result. Preserve every failure and inconclusive result. A retry is a new Owner-reviewed attempt with a new run ID and a reason; never overwrite the prior attempt.

Hashes and append-only file naming help detect accidental changes but are not physically immutable or tamper-proof. Copy accepted records to an Owner-controlled archive and retain/check its hash. Do not write to frozen historical archives.

## 6. Resource and filesystem limitations

The runner enforces a wall-clock timeout on its direct child and monitors log-file sizes. The output cap is polled and is a soft control, not a hard kernel-enforced quota. It has no hard CPU/RAM/disk limits, no guaranteed process-tree termination, no Windows Job Object, no restricted token and no filesystem sandbox. A process running as the Owner can access any file that Owner can access.

For these four small deterministic cases, the Owner may accept those limits after review. If a campaign needs a hard resource quota, descendant containment or protection against writes by a compromised test process, use a separately reviewed OS isolation design; do not imply this local runner supplies it.

## 7. Stop conditions

Stop before launching a case if any identity/hash, import, package, thread configuration, command, nodeid, selection, environment, output path or Owner decision differs from the frozen record. Stop after a timeout, output limit, interruption, missing/contradictory JUnit, source mutation, missing observable required by the oracle, or scientific failure. Preserve the evidence and classify the cause; do not retry automatically.

## 8. Scientific interpretation

Keep these claims separate:

- test source exists;
- pytest executed and passed its assertions;
- an algebraic or analytical oracle agrees;
- a mesh/time convergence study is adequate;
- independent solver correlation agrees;
- an experiment validates a physical model;
- an Owner grants a bounded qualification disposition.

The first four cases supply different evidence types; none alone qualifies the general analysis route. WP12 remains open until its approved gate and Owner disposition.
