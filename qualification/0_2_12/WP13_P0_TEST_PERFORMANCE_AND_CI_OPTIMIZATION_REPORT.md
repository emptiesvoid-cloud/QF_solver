# WP13 P0 test performance and CI optimization

**Candidate PR:** #114
**Candidate HEAD audited:** `f00bbb9c23769f984a12c2dda37802382ffc5414`
**Release base:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`
**Status:** `WP13_P0_PARTIAL_OR_BLOCKED`
**Release decision:** not authorized; no tag, merge to `main`, package publication, site deployment or release artifact was created.

## 1. Controlled-execution status

At the beginning and end of triage, no local pytest, WP13 package-smoke
controller, qualification runner or solver process was active. The only
processes in the process inventory were the PowerShell/`gh` commands used for
the inventory itself. GitHub Actions runs `41210713065` and `41225195330` are
terminal; no quality workflow remains queued or running. The real package-FEM
attempt ledger remains absent. No historical qualification ledger was edited.

The 20-node profile below ran serially, one exact pytest function selector per
child process, on local Windows 10.0.19045 / CPython 3.13.1. It used no
coverage instrumentation and did not run a suite target. Process CPU and the
maximum observed process-tree RSS were sampled every 25 ms. `pytest --durations=1`
reported test-call time. Local totals include Python startup and pytest
collection; RSS may miss spikes shorter than the sampling interval.

**Scope deviation discovered during profiling:** the first selected node was
named as a documentation asset test, but source inspection after its execution
showed that it calls three contact campaigns, including two structural TET4
mesh-refinement campaigns. That one bounded node passed locally in 41.10 s,
but it was not covered by a frozen WP13 FEM contract or separate Owner
approval. It wrote under pytest's temporary directory and created no
qualification ledger or durable evidence. Its output is not qualification
evidence and the node will not be run again without an exact Owner-approved
scope. This deviation is recorded rather than hidden.

## 2. Top 20 from the bounded node profile

This is the ranking of the 20 deliberately selected exact nodeids, not a
global ranking of all 4,708 CI-selected tests. GitHub Actions ran pytest without
`--durations`; its logs do not contain per-node CPU, duration or memory, so a
full-suite top-20 ranking cannot be reconstructed. The Windows full-suite
timeout also did not print the exact in-flight nodeid.

| Rank | Exact nodeid | Local wall / CPU / peak RSS | Result and class | Finding / action |
|---:|---|---|---|---|
| 1 | `tests/unit/test_architecture_rules.py::test_python_source_size_debt_is_reported_without_a_hard_cap` | `>169.064 s` / `3.016 s` / `87.4 MiB` | `DIAGNOSTIC_STOP`; governance scan, no FEM | Python `Path.rglob` plus per-file reads made little I/O progress on the local `E:` worktree. Stop was issued after read counters stopped advancing. The same test appears in the Windows hosted CI log at the beginning of the suite; it is not the 3-hour stall. Treat this local measurement as filesystem-specific. |
| 2 | `tests/unit/test_contact_documentation_assets.py::test_contact_publisher_includes_the_structural_friction_evidence` | `43.446 s` / `39.438 s` / `476.4 MiB` | `PASS` (41.10 s pytest call); **unmarked FEM** | Re-runs 12 spring/contact analytical solves plus four frictional and four frictionless structural TET4 solves. Each structural campaign refines through `(4,2,2)`, `(8,4,4)`, `(12,6,6)`, `(16,8,8)`; the finest level has 6,144 TET4 elements and 1,377 structural nodes. Split documentation wiring/render checks from these controlled solves; retain the numerical campaigns under an explicit scientific scope. |
| 3 | `tests/unit/test_corotational_j2_corrected.py::test_corrected_polar_kinematics_and_fail_closed_guards` | `4.508 s` / `3.906 s` / `152.5 MiB` | `PASS` (2.13 s call); mechanics math, no global solve | Small fixed-size polar and guard operations; no material performance issue observed. |
| 4 | `tests/unit/test_development_autonomous_policy.py::test_source_inventory_binds_recursive_test_local_imports_and_pytest_conftests` | `3.427 s` / `2.828 s` / `92.6 MiB` | `PASS` (1.43 s call); synthetic governance | Synthetic tree only. No broad repository inventory or FEM. |
| 5 | `tests/unit/test_development_autonomous_policy.py::test_wp12_manifest_stays_unapproved_until_exact_owner_decision` | `2.905 s` / `2.453 s` / `86.1 MiB` | `PASS` (0.87 s call); synthetic governance | Individual Windows run is fast; it does not reproduce the full-suite Windows stall. |
| 6 | `tests/unit/test_development_autonomous_policy.py::test_source_inventory_rejects_unresolvable_dynamic_test_imports` | `2.826 s` / `2.359 s` / `86.2 MiB` | `PASS` (0.78 s call); synthetic governance | Bounded temporary fixture. |
| 7 | `tests/unit/test_development_autonomous_policy.py::test_d01_policy_rejects_budget_expansion_beyond_owner_envelope` | `2.793 s` / `2.438 s` / `85.9 MiB` | `PASS` (3 parameter cases, 0.81 s total call); synthetic governance | Exact policy-boundary assertions; no ledger outside temporary test data. |
| 8 | `tests/unit/test_development_autonomous_policy.py::test_each_wp12_worktree_resolves_its_registered_test_and_solver_root` | `2.778 s` / `2.359 s` / `86.1 MiB` | `PASS` (0.75 s call); synthetic governance | No runner launch. |
| 9 | `tests/unit/test_development_autonomous_policy.py::test_each_worktree_has_a_separate_output_namespace` | `2.762 s` / `2.359 s` / `88.3 MiB` | `PASS` (0.71 s call); synthetic governance | No external evidence write. |
| 10 | `tests/unit/test_development_autonomous_policy.py::test_wp12_registry_has_distinct_exact_worktree_envelopes` | `2.761 s` / `2.438 s` / `89.5 MiB` | `PASS` (0.76 s call); synthetic governance | Static registry assertion. |
| 11 | `tests/unit/test_development_autonomous_policy.py::test_wp12b_corrective_manifest_binds_campaign_and_remains_unapproved` | `2.758 s` / `2.234 s` / `86.0 MiB` | `PASS` (0.72 s call); synthetic governance | Temporary manifest only. |
| 12 | `tests/unit/test_development_autonomous_policy.py::test_hex8sri_source_identity_inventory_freezes_exact_raw_worktree_bytes` | `2.749 s` / `2.328 s` / `86.6 MiB` | `PASS` (0.75 s call); governance / hashes | Reads the pinned inventory; does not run its scientific nodes. |
| 13 | `tests/unit/test_development_autonomous_policy.py::test_wp12b_corrective_campaign_sets_canonical_scope_and_separate_evidence_root` | `2.715 s` / `2.312 s` / `86.8 MiB` | `PASS` (0.73 s call); synthetic governance | Temporary policy fixture. |
| 14 | `tests/unit/test_development_autonomous_policy.py::test_wp12_dynamics_policy_rejects_unsafe_ledger_binding[generic-path]` | `2.705 s` / `2.266 s` / `86.2 MiB` | `PASS` (0.73 s call); synthetic governance | Rejects a path mutation; does not open or edit a historical ledger. |
| 15 | `tests/unit/test_development_autonomous_policy.py::test_release_controller_designation_is_unambiguous_and_pinned` | `2.703 s` / `2.297 s` / `91.7 MiB` | `PASS` (0.76 s call); governance | Reads pinned declarations. |
| 16 | `tests/unit/test_development_autonomous_policy.py::test_policy_registers_only_owner_authorized_worktrees_and_keeps_qualification_separate` | `2.687 s` / `2.141 s` / `86.9 MiB` | `PASS` (0.71 s call); governance | Static policy assertion. |
| 17 | `tests/unit/test_development_autonomous_policy.py::test_source_inventory_rejects_dynamic_pytest_plugin_mutations` | `2.679 s` / `2.328 s` / `86.5 MiB` | `PASS` (2 parameter cases, 0.72 s total call); synthetic governance | Temporary source inputs. |
| 18 | `tests/unit/test_development_autonomous_policy.py::test_source_inventory_rejects_local_wildcard_imports` | `2.676 s` / `2.250 s` / `88.5 MiB` | `PASS` (0.73 s call); synthetic governance | Temporary source inputs. |
| 19 | `tests/unit/test_development_autonomous_policy.py::test_wp12_dirty_scientific_worktree_is_refused_before_registration_or_execution` | `2.669 s` / `2.312 s` / `89.5 MiB` | `PASS` (0.72 s call); synthetic governance | Refusal path only; no registration, reservation or FEM. |
| 20 | `tests/unit/test_development_autonomous_policy.py::test_dynamic_nodeids_are_allowlisted_only_for_the_dynamics_worktree` | `2.633 s` / `2.266 s` / `89.6 MiB` | `PASS` (0.72 s call); synthetic governance | Static allowlist assertion. |

Except for the first two rows, total wall is primarily interpreter startup and
pytest collection (about 1.9–2.7 s per fresh process); test-call times are
0.71–1.43 s for the governance cases. Those rows do not justify splitting the
policy file on timing grounds. The measured outliers are the documentation
node with embedded contact campaigns and the local `E:` filesystem scan.

## 3. Windows full-suite stall

Corrected official run
[41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330)
ran at the exact PR HEAD `f00bbb9c23769f984a12c2dda37802382ffc5414`.
The two Ubuntu jobs completed successfully; both Windows jobs reached the
180-minute job limit in the `Tests and branch coverage` step:

| Cell | Exact Python | Pytest outcome before job cancellation | Subsequent gates |
|---|---:|---|---|
| Ubuntu | 3.10.22 | 4,676 passed, 32 skipped, 150 deselected; 4 warnings; 7,537.95 s (2:05:37) | Global branch coverage 84.75%; P0 module gate, compileall, quick verification and artifact upload PASS. |
| Ubuntu | 3.13.17 | 4,676 passed, 32 skipped, 150 deselected; 4 warnings; 7,120.37 s (1:58:40) | Global branch coverage 84.75%; P0 module gate, compileall, quick verification and artifact upload PASS. |
| Windows | 3.10.11 | 602 passed, 5 skipped, 150 deselected; pytest interrupted after 10,681.97 s (2:58:01) | Job cancelled at 180 minutes. No coverage artifact, P0 gate, compileall or quick-verification result. |
| Windows | 3.13.16 | 602 passed, 5 skipped, 150 deselected; pytest interrupted after 10,724.65 s (2:58:44) | Job cancelled at 180 minutes. No coverage artifact, P0 gate, compileall or quick-verification result. |

Both Windows logs stop at the same progress point: the output names
`tests/unit/test_development_autonomous_policy.py` at 12%, then pytest is
interrupted in `pathlib` (`pathlib.py:1290` on Python 3.10 and
`pathlib._abc.py:38` on Python 3.13). The workflow does not use verbose node
reporting or `--full-trace`; therefore the exact in-flight nodeid is **not
recorded**. Do not attribute the stall to a guessed node. Individually timed
synthetic policy nodeids from that module complete in 0.71–0.87 s locally;
that does not prove which test or interaction is responsible in the hosted
runner.

The same 602-pass Windows stopping point recurred in run 2. This is a
repeatable Windows-runner/test-process stall, not a demonstrated product
assertion failure. There is no CPU or RSS evidence from GitHub Actions. The
next useful diagnostic is a separately bounded Windows-only exact-node
workflow with verbose output, `--full-trace`, per-test durations and a short
timeout after the exact node is recorded; another full four-cell run would
not add the missing node identity.

## 4. Classification of the 17 failures in run 2

The 17 failures in run
[41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065)
were test, policy or selection failures, not numerical solver failures:

| Count | Failure family and exact nodes | Classification | Corrected-run disposition |
|---:|---|---|---|
| 14 | `tests/unit/test_wp12_process_attestation.py`: `test_valid_ephemeral_owner_decision_attests_only_fixed_fake_child`; four cases of `test_scientific_nodeid_refused_and_synthetic_reports_classified` (`test_no_junit`, `test_contradictory_junit`, `test_junit_substitution`, `test_nonzero`); `test_existing_archive_destination_is_never_overwritten`; `test_receipt_tampering_is_detected_and_attempt_collision_is_refused`; `test_declared_interpreter_mismatch_is_denied_before_process_creation`; `test_system_identity_observation_is_rejected_before_child_resume`; `test_input_change_after_prelaunch_check_is_recorded_as_infrastructure_error`; `test_process_launch_error_is_archived_as_infrastructure_error`; `test_supervisor_interruption_is_not_reclassified_as_pass`; `test_job_assignment_failure_terminates_the_suspended_process_handle`; `test_timeout_and_descendant_scenarios_are_not_reported_as_pass` | Platform policy / test expectation. The Linux implementation correctly returned `DENY_EXECUTION` because suspended-child attestation requires the Windows backend. | Tests now assert that exact fail-closed refusal on non-Windows; no permissive attestation fallback was added. Linux run 3 passed. Windows run 3 did not progress far enough to reacquire the Windows child-classification results. |
| 1 | `tests/unit/test_wp12_qualification_runner.py::test_pilot_v4_manifest_binds_separate_checkouts_and_stays_blocked` | Test fixture portability: literal Windows separator construction disagreed with the host-native expected argv. | Fixture now builds `junit.xml` with `Path`; Linux run 3 passed. |
| 1 | `tests/unit/test_wp12_qualification_runner.py::test_provenance_plugin_accepts_pinned_inventory_superset_with_only_fake_module` | Test isolation / import-origin fixture: the suite had already imported the real `solveur` package. | The test removes cached `solveur` modules within its monkeypatch scope before installing the fake module; Linux run 3 passed. |
| 1 | `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual` | Controlled-scope policy. A controller-gated scientific node escaped the old exact-name exclusion and correctly refused because `QF_DEVELOPMENT_AUTONOMOUS` was absent. No solve ran. | The exact node is now deselected from the generic matrix. This is `NOT_RUN` in standard CI, not a PASS and not a changed scientific gate. |

No threshold or oracle was changed. The HEX20 case remains outside this
generic workflow until its registered scientific scope is authorized.

## 5. Unmarked numerical work and delay sources

The CI command selects `tests/unit` and `tests/integration` by path and only
excludes five marker classes plus exact `-k` names. A static scan of solver
calls found many small model solves in those paths. Confirmed examples include
`tests/integration/test_packaging.py::test_solver_cli_module_check_mesh_and_solve_run`,
`tests/unit/test_beam2_element.py` static/modal tests,
`tests/unit/test_frictional_contact.py`,
`tests/unit/test_frictionless_contact.py`,
`tests/unit/test_contact_surface_tangential_stiffness.py`, and the corrected
global Newton routes in `tests/unit/test_corotational_j2_corrected.py`.
They should be classified individually; the presence of `.solve()` alone does
not make every backend-algebra or small deterministic mechanics unit a
scientific qualification. The contact documentation node is confirmed to
execute structural FEM and has no `scientific_vv` marker.

The governance supervisor tests intentionally create fake children with
`sleep(20)` payloads, but enforce 0.2–0.3 s monitored timeouts and assert child
termination. This is bounded adversarial testing, not a 20-second sleep per
test and not the three-hour stall. Test bodies include many CLI/subprocess
launches; those are a reasonable repeated startup cost but are not by
themselves evidence of an unbounded wait.

No source change is made in this triage. In particular, the 169-second local
source-scan stop is not treated as a product defect because its hosted-run
counterpart completes near the start of Windows CI. The contact campaign is a
real standard-suite cost and a scope-classification problem; the remedy must
separate its scientific runs from documentation wiring without weakening
either the contact oracles or the asset assertions.

## 6. Proposed P0 CI organization

This proposal changes no current gate and has **not** been adopted as a
release criterion.

| Role | Proposed environment | Gates |
|---|---|---|
| Reference | Ubuntu / Python 3.13 | Complete permitted standard suite; branch coverage >=80%; declared P0 module gates >=90%; Ruff, mypy, compileall, CLI/API and quick verification. Current observed full duration: 1:58:40. |
| Compatibility | Ubuntu / Python 3.10 | Targeted version-compatibility tests for Python 3.10, serialization, APIs, CLI, filesystem paths and clean wheel/sdist install. |
| Compatibility | Windows / Python 3.10 and 3.13 | Targeted Windows subprocess/provenance and path tests, serialization, public API/CLI, clean wheel/sdist install and non-solving check-mesh. Keep distinct result rows per Python version. |

The targeted cells must identify exact selected nodeids and exclusions; they
must not be described as equivalent to the full suite. The current release
obligation for the complete Ubuntu/Windows x Python 3.10/3.13 suite remains
`NOT_ACQUIRED` until an explicit Owner decision changes it. The current run
already demonstrates that the complete Linux reference suite can be acquired;
it does not complete Windows compatibility or Windows full-suite gates.

For future diagnostic runs, attach pytest's `--durations=20` to the reference
job and use `-vv --full-trace` only on an exact bounded Windows diagnostic.
Persist JUnit and job logs with hashes. Do not run the entire four-cell suite
again solely to collect per-test timings.

## 7. Duration estimate and before/after

Run 3 began at 17:34:33Z and terminated at 20:34:48Z: about 3:00:15 wall time.
Its observed job/test durations were 7,537.95 s on Ubuntu/Python 3.10,
7,120.37 s on Ubuntu/Python 3.13, 10,681.97 s on Windows/Python 3.10 before
timeout, and 10,724.65 s on Windows/Python 3.13 before timeout. The summed
runner occupancy is about 10.0 compute-hours; this is measured, though the
Windows rows are incomplete.

Under the proposed layout, one reference run is about 1:59 based on the actual
Ubuntu/Python 3.13 result. The three targeted compatibility jobs have not been
measured. A provisional 10–20 minutes each would put total occupancy near
2.5–3.0 compute-hours and matrix wall time near 2 hours, assuming those
selected tests stay below the reference-job duration and no install/network
retry occurs. This is a planning estimate, not a result. There is no measured
before/after comparison yet.

## 8. Gate result, unresolved actions and next Owner decision

| Gate | Result after run 3 |
|---|---|
| Linux/Python 3.10 complete standard suite | PASS: 4,676 passed, 32 skipped, 150 deselected. |
| Linux/Python 3.13 complete standard suite | PASS: 4,676 passed, 32 skipped, 150 deselected. |
| Global branch coverage >=80% | PASS on both Linux cells: 84.75%. |
| P0 module branch coverage >=90% | PASS on both Linux cells: `solveur/core/errors.py` 100.00%; `solveur/verification/traceability.py` 92.16%. |
| Ruff, privacy diff, mypy, compileall, official quick verification | PASS in all four jobs before timeout (the Windows jobs timed out only in the test step, so their downstream steps did not run). |
| Windows/Python 3.10 and 3.13 complete standard suite | BLOCKED at 180 minutes; each stopped after 602 passed. Exact in-flight nodeid and Windows coverage are unavailable. |
| Installed-artifact solve smoke (STATIC/MODAL/DYNAMIC x wheel/sdist) | BLOCKED / NOT_RUN pending exact Owner FEM authorization; only persisted and synthetic no-FEM preflights pass. |
| Old full four-cell suite obligation | `NOT_ACQUIRED`; not replaced by this report's proposal. |
| Overall P0 | `WP13_P0_PARTIAL_OR_BLOCKED`; do not claim `WP13_P0_VALIDATED`. |

The next Owner decision is whether to formally amend the P0 acceptance matrix
to the reference-full plus targeted-compatibility design, while retaining the
old four-cell full-suite obligation as `NOT_ACQUIRED` in the record. The same
decision pack should authorize (or decline) a short, exact Windows diagnostic
of the recorded governance stall and the separate package-smoke cases; neither
is covered by a generic test-suite dispatch.

## 9. Evidence references

- Corrected official run 3: [workflow 41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330), exact HEAD `f00bbb9c23769f984a12c2dda37802382ffc5414`.
- Prior 17-failure run 2: [workflow 41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065), exact HEAD `2865587a44f9e461a0b4e4286c912c17e4f04be5`.
- Run 3 Linux Python 3.10 log SHA-256: `3a5aee5b5ed90be43db789e89aa1cc3b873d065d2ddc0e02f3156a81796b236f`.
- Run 3 Linux Python 3.13 log SHA-256: `073034c7caaeae536c219eac18cad5a4a43602625643bd5e9091fc411c62057ef`.
- Run 3 Windows Python 3.10 log SHA-256: `a77fa49d45e59f9a5c4b163166bf817f916388326bcd2504d42e7f40bae4b549`.
- Run 3 Windows Python 3.13 log SHA-256: `8f808a13543708e5ea2b4539dd38ffef5413256fb4e46ba4e548426eb4c62187`.
- Linux branch coverage artifact hashes and module values are in the execution baseline and the CI artifacts; Windows produced no coverage artifact.
- Package FEM case identities, limits, oracles and no-FEM preflight hashes remain in [`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md). No actual package smoke attempt ledger exists.
- Historical v2/v3/v4 candidate reports, scientific evidence, and qualification ledgers were not rewritten.