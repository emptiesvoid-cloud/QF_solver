# Proposal: proportionate local scientific V&V policy

**Status:** PROPOSED_NOT_EFFECTIVE — Owner approval required.
**Execution:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

## 1. Why a separate local route is proposed

The WP12-A/B/C signed runner and process-attestation path was designed for tightly controlled scientific qualification. The current WP12-C review still records limitations/refusals. The requested WP12-P direction is to consider ordinary local scientific verification on the Owner’s Windows PC without requiring a dedicated service account, SYSTEM broker, HKLM trust store, Ed25519 key, VM, or process attestation. This remains a proposal pending an explicit Owner decision and governance amendment.

This proposal is a proportionate local workflow, not a security sandbox. It must not remove, weaken, bypass, or reactivate the historical runner. It does not turn ordinary local runs into cryptographically attested or independently reviewed evidence.

## 2. Proposed policy status

No new policy is effective until the Owner explicitly approves the scope and the repository’s governing policy is updated through its ordinary review process. The current [AGENTS.md](../../../AGENTS.md) and [development_autonomous_policy.json](../../../development_autonomous_policy.json) remain in force. In particular, development-run authorization is not qualification authorization, and historical release gates remain separate.

Proposed policy key: **QUALIFICATION_LOCAL_VV — PROPOSED_NOT_EFFECTIVE**.

## 3. Minimum local controls

For each exact case:

1. Use the named frozen science commit/tree; record the separate docs/runner/test commit and tree.
2. Require a clean checkout or a complete patch/source inventory approved for the case.
3. Use a dedicated Python venv where available; record absolute interpreter, environment identity, package versions and actual import origin. Refuse accidental import from global qf-solver 0.2.10.
4. For tests, use one exact pytest nodeid per invocation. For a benchmark, use one reviewed checked-in entry point with literal frozen arguments, one case ID, a new output root, and a source hash recorded in the decision. No directory, wildcard, entire suite, unbounded benchmark sweep, or user-supplied shell command.
5. Inspect the selected test and fixtures for solver calls, parameterization, external dependencies, file writes and mesh loops before approval.
6. Freeze inputs, source hashes, nodeid, command, criteria, output directory, and retry policy before the first run.
7. Write to a new case/run directory. Refuse overwrite. Preserve stdout/stderr, structured results, environment report, and SHA-256 inventory.
8. Keep FAIL, timeout, interruption, and infrastructure errors as separate outcomes. A retry gets a new run identity and written reason.
9. Copy the completed evidence directory to an Owner-controlled archive with a read-only or backup copy. Local hashes improve traceability but do not prove immutability or authorship.
10. An Owner or reviewer inspects every result before using it in a qualification disposition.

## 4. Responsibilities and limits

- **Owner:** approve policy revision, target science identity, exact nodeids/cases, criteria, outputs, attempt limits and any external tool.
- **Operator:** execute only approved exact commands in the specified venv/checkout; preserve logs and outcomes.
- **Reviewer:** verify identities, command scope, raw results, oracle/criterion, failures, archive hash and interpretation.

Running locally under the Owner’s account means the test process can access files that account can access. This procedure is not a filesystem sandbox. Do not run untrusted test code. Job Objects or process monitoring may record/limit some process/resource behavior but do not by themselves protect files from a same-user process.

## 5. Command and recording template

An exact test command may use this form after Owner approval:

    python -m pytest -q tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form

Before use, replace `python` with the verified absolute venv interpreter and set the approved working directory and environment. A benchmark API invocation must likewise be frozen as a complete literal command, reviewed for side effects, bound to its checked-in entrypoint hash and given a new output directory. The proposed TET4 call in [BENCHMARK_CATALOG.md](BENCHMARK_CATALOG.md) is not approved. This document authorizes nothing.

Record at minimum:

    case_id, run_id, utc_start, science_commit, science_tree, integration_commit,
    runner_commit, clean_status, nodeid, command, interpreter, venv, import_origin,
    packages, native_libraries_if_observed, thread_variables, fixtures_and_hashes,
    inputs_and_units, oracle, criterion_source, outputs, exit_code, verdict,
    failure_or_deviation, artifact_hashes, reviewer, archive_location

Unknown fields must say NOT_OBSERVED; do not infer them.

## 6. Security and qualification separation

This local policy governs a measured V&V run and evidence handling. It makes no claim of cryptographic identity, protected process launch, OS-enforced memory quota, or tamper-proof storage. The old WP12 runner retains its current denial behavior and may be used only under its own verified authority. No local approval silently counts as an Ed25519 decision or satisfies the prior runner's trust chain.

The policy does not authorize a release, a maturity promotion, WP12 closure, or use of the development runner as qualification evidence.

## 7. Owner decision required

Approve or reject the policy as written; approve a precise amendment to AGENTS.md / qualification governance; select an initial case list; approve exact criteria and environment recording; decide retention/archive location and permitted retries. Until then, this proposal is not effective and all proposed campaign commands remain unexecuted.
