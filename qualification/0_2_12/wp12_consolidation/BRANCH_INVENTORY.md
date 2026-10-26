# WP12 branch/worktree inventory and rationalization proposal

**Point-in-time snapshot:** 2026-10-26. **Comparison ref:** `origin/emptiesvoids-cloud/0.2.12` at `98456355f0a85dff9edf7f37d53c7c6fff59bf37`. Ahead/behind counts and exclusive commits compare each ref with that ref. Changed paths are committed tree deltas, not local edits. Refs/worktrees advanced during this task; recheck live state before cleanup. No branch/worktree is deleted here.

The collaboration registry showed no active worker except this task and listed the other review workers as completed. That cannot rule out independent tasks. Multiple refs advanced and new worktrees appeared during the audit; clean status does not prove no agent/process depends on a branch.

| Branch/ref | HEAD | Merge-base | Ahead / behind | Exclusive changed paths | Worktree state | Agent/task signal | Assessment | Action |
|---|---|---|---:|---|---|---|---|---|
| `audit/wp12-advanced-physics` | `71461362e1a6f720aac6a9f854d67048f4d469b7` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | 2/1 | `qualification/0_2_12/wp12_c_advanced_physics_audit.md`<br>`qualification/0_2_12/wp12_c_j2_objectivity_research_protocol.md` | QFSolverAgents/wp12-advanced-physics: clean | attached checkout; live agent unknown | DOCUMENTARY_DONE | MERGE selected reports |
| `codex/hex8sri-controller-registration` | `616c9e2be7f020677bea5f67c92680bbe396aa3e` | `2aa994f34900f39bef8df9db5fb025157fb694bb` | 4/74 | `development_autonomous_policy.json`<br>`scripts/development_autonomous.py`<br>`tests/unit/test_development_autonomous_policy.py` | QFSolverAgents/hex8sri-controller: clean | attached checkout; live agent unknown | POLICY/CONTROLLER_VARIANT | REVIEW; concurrent edits |
| `codex/wp07-serialization-integration` | `bf8732c49b20cf74af65b0c7a358f997b5b28e1f` | `bf8732c49b20cf74af65b0c7a358f997b5b28e1f` | 0/8 | — | QFSolverAgents/wp07-integration: clean | attached checkout; live agent unknown | CONTENT_INTEGRATED | REVIEW; worktree attached |
| `codex/wp12-dynamic-harmonic-verification` | `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66` | `bf8732c49b20cf74af65b0c7a358f997b5b28e1f` | 5/8 | `qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_EXPERIMENT_PLAN.md`<br>`qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_RESULTS_REPORT.md`<br>`tests/unit/test_modal_newmark.py`<br>`tests/unit/test_reduced_harmonic.py`<br>`tests/unit/test_wp07_uniform_base_acceleration.py`<br>`tests/unit/test_wp12_observable_archive_synthetic.py` | QFSolverAgents/wp12-dynamics: clean | attached checkout; live agent unknown | SCIENTIFIC_BRANCH + report | KEEP; code/tests separate |
| `codex/wp12-policy-finalization` | `4bf52792f46988b84fecf11ebe3bd5fe078975ef` | `4bf52792f46988b84fecf11ebe3bd5fe078975ef` | 0/6 | — | QFSolverAgents/wp12-policy-final: DIRTY 1: development_autonomous_policy.json | local edits observed; owner/process unknown | LOCAL_POLICY_EDIT | KEEP; dirty |
| `codex/wp12-policy-reconciliation` | `aecddc6277a52789f2f3b34642393db344d87460` | `b0023628d7231629cc6bf124420e995fffa6c44c` | 2/5 | `development_autonomous_policy.json`<br>`scripts/development_autonomous.py`<br>`tests/unit/test_development_autonomous_policy.py` | QFSolverAgents/wp12-policy-reconciliation: clean | attached checkout; live agent unknown | POLICY_VARIANT | KEEP / REVIEW |
| `codex/wp12-policy-registration-consolidation` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | 0/1 | — | QFSolverAgents/wp12-policy-registration-consolidation: clean | attached checkout; live agent unknown | ANCESTOR_OF_CENTRAL | REVIEW; worktree attached |
| `codex/wp12-rotor-registration-preparation` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 0/0 | — | .codex/worktrees/wp12-rotor-config/qf_solver: DIRTY 1: qualification/0_2_12/wp12_preparation/wp12_d_rotor_owner_request.md | local edits observed; owner/process unknown | ANCESTOR + local request | KEEP; dirty |
| `codex/wp12b-elements-controller-extension` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 0/0 | — | QFSolverAgents/wp12b-elements-controller: clean | attached checkout; live agent unknown | NEW_CONTROLLER_WORKTREE | REVIEW; no unique commits yet |
| `docs/wp12-consolidation` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 0/0 | — | main checkout: DIRTY 19: docs/verification/wp12_b_elements_loads_audit.md, experiments/wp12_tet4_convergence/case_metrics.csv, experiments/wp12_tet4_convergence/figures/family_comparison.png, experiments/wp12_tet4_convergence/figures/resources.png … | local edits observed; owner/process unknown | DOCUMENTARY_IN_PROGRESS | KEEP |
| `docs/wp12-legacy-coverage-roadmap` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 0/0 | — | QFSolverAgents/wp12-roadmap-docs: clean | attached checkout; live agent unknown | FULLY_INTEGRATED | REVIEW; worktree attached |
| `emptiesvoids-cloud/0.2.12` | `2aa994f34900f39bef8df9db5fb025157fb694bb` | `2aa994f34900f39bef8df9db5fb025157fb694bb` | 0/74 | — | qf_solver: DIRTY 4: tests/unit/test_wp_e01m_hencky_material_point.py, tests/unit/test_wp_e01q_hencky_tangent.py, checkout-0.2.12/, wp12-science-00428ad/ | local edits observed; owner/process unknown | STALE_LOCAL_RELEASE_CHECKOUT | KEEP; dirty |
| `emptiesvoids-cloud/wp12-autonomous-policy-onboarding` | `e8ad947ddf86ee896d6c3335281b0e5f5a635ce0` | `6d8f140834db75ea9b968b055af23445261d0073` | 2/9 | `AGENTS.md`<br>`DEVELOPMENT_AUTONOMOUS.md`<br>`development_autonomous_policy.json`<br>`scripts/development_autonomous.py`<br>`tests/unit/test_development_autonomous_policy.py` | QFSolverAgents/wp12-policy-config: clean | attached checkout; live agent unknown | STALE_POLICY_VARIANT | REVIEW |
| `emptiesvoids-cloud/wp12-autonomous-policy-root-luna` | `f939f6ee3c4d5a90d68dbee9b70e563aedf88b9a` | `2aa994f34900f39bef8df9db5fb025157fb694bb` | 1/74 | `AGENTS.md`<br>`development_autonomous_policy.json`<br>`scripts/development_autonomous.py`<br>`tests/unit/test_development_autonomous_policy.py` | QFSolverAgents/wp12-policy-root-luna: clean | attached checkout; live agent unknown | STALE_POLICY_VARIANT | REVIEW |
| `emptiesvoids-cloud/wp12-dynamics-selective-integration` | `f843d9286894d938df8503028d9d553baa27e1ed` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 2/0 | `docs/verification/wp12_b_elements_loads_audit.md`<br>`experiments/wp12_tet4_convergence/case_metrics.csv`<br>`experiments/wp12_tet4_convergence/figures/family_comparison.png`<br>`experiments/wp12_tet4_convergence/figures/resources.png`<br>`experiments/wp12_tet4_convergence/figures/tet4_convergence.png`<br>`experiments/wp12_tet4_convergence/report_consolide.md`<br>`experiments/wp12_tet4_convergence/summary.json`<br>`qualification/0_2_12/vv_local/WP12_CONSOLIDATION_INDEX.md`<br>`qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_RESULTS_REPORT.md`<br>`qualification/0_2_12/vv_local/wp12_legacy_cross_route/COVERAGE_MATRIX.tsv`<br>`qualification/0_2_12/vv_local/wp12_legacy_cross_route/LEGACY_CROSS_ROUTE_REPORT.md`<br>`qualification/0_2_12/wp12_c_advanced_physics_audit.md`<br>`tests/unit/test_modal_newmark.py`<br>`tests/unit/test_reduced_harmonic.py`<br>`tests/unit/test_wp07_uniform_base_acceleration.py`<br>`tests/unit/test_wp12_observable_archive_synthetic.py` | QFSolverAgents/wp12-dynamics-integration: clean | attached checkout; live agent unknown | MIXED_DOCS_AND_SCIENTIFIC_TESTS | REVIEW; do not cherry-pick |
| `experiment/wp12-tet4-convergence` | `9c48bd5559b898db3bb76bef05b9566302c613c8` | `6d8f140834db75ea9b968b055af23445261d0073` | 5/9 | `experiments/wp12_tet4_convergence/case_metrics.csv`<br>`experiments/wp12_tet4_convergence/figures/family_comparison.png`<br>`experiments/wp12_tet4_convergence/figures/resources.png`<br>`experiments/wp12_tet4_convergence/figures/tet4_convergence.png`<br>`experiments/wp12_tet4_convergence/report_consolide.md`<br>`experiments/wp12_tet4_convergence/summary.json`<br>`scripts/wp12_dev/prepare_tet4_quality_sequence.py`<br>`scripts/wp12_dev/tet4_mechanical_oracles.py`<br>`tests/unit/test_tet4_wp12_preparation.py`<br>`tests/unit/test_wp12_tet4_prepared_fem.py` | QFSolverAgents/tet4: clean | attached checkout; live agent unknown | SCIENTIFIC_BRANCH + results | KEEP; code/tests separate |
| `fix/wp12-wp07-serialization` | `0a2e8135a9d4b6d80abf41dbdd9bf2aefa1cafd6` | `6d8f140834db75ea9b968b055af23445261d0073` | 1/9 | `src/solveur/core/results.py`<br>`tests/unit/test_result_serialization_contracts.py` | QFSolverAgents/wp07: clean | attached checkout; live agent unknown | PATCH_CONTENT_INTEGRATED | REVIEW; worktree attached |
| `research/hex8-sri-equilibrium` | `76d9161951fe8848af07aaf326376da8de259f9e` | `2aa994f34900f39bef8df9db5fb025157fb694bb` | 11/74 | `.gitattributes`<br>`experiments/hex8_sri_equilibrium/__init__.py`<br>`experiments/hex8_sri_equilibrium/campaign.py`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/build_campaign_drafts.py`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/common_problem.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/candidate_status.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/common_problem.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_hex8_standard_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_hex8_standard_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_sri_corrected_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_sri_corrected_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_sri_historical_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/manifest_sri_historical_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4/registration.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/candidate_status.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/common_problem.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_hex8_standard_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_hex8_standard_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_sri_corrected_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_sri_corrected_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_sri_historical_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/manifest_sri_historical_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_2896c0f0f5e5_protocol2/registration.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/candidate_status.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/common_problem.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_hex8_standard_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_hex8_standard_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_sri_corrected_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_sri_corrected_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_sri_historical_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/manifest_sri_historical_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_4950f4b6b556/registration.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/common_problem.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_hex8_standard_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_hex8_standard_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_sri_corrected_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_sri_corrected_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_sri_historical_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/manifest_sri_historical_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/registration.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_hex8_standard_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_hex8_standard_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_sri_corrected_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_sri_corrected_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_sri_historical_nu_0p3.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/manifest_sri_historical_nu_0p4999.json`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/owner_authorization_request.md`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/preparation_report.md`<br>`investigations/hex8_sri_equilibrium_20261026/campaign_preparation/registration_proposal.json`<br>`investigations/hex8_sri_equilibrium_20261026/compare_element_operators.py`<br>`investigations/hex8_sri_equilibrium_20261026/operator_comparison_results.json`<br>`investigations/hex8_sri_equilibrium_20261026/report.md`<br>`src/solveur/elements/solid/hex8_sri.py`<br>`tests/unit/test_hex8_sri_campaign_sidecar.py`<br>`tests/unit/test_hex8_sri_element.py`<br>`tests/verification/test_hex8_sri_structural_campaign.py` | QFSolverAgents/hex8-sri-research: clean | attached checkout; live agent unknown | SCIENTIFIC_ACTIVE | KEEP; dirty |
| `test/wp12-fem-regressions` | `fa889f480766506787941617fa0db4124381c63b` | `6d8f140834db75ea9b968b055af23445261d0073` | 4/9 | `qualification/0_2_12/vv_local/wp12_agent3/HEX8_SRI_PREEXECUTION_PLAN.md`<br>`qualification/0_2_12/vv_local/wp12_agent3/WORKING_COVERAGE_MATRIX.md`<br>`tests/verification/test_wp12_hex8_sri_diagnostics.py` | QFSolverAgents/vv-elements: clean | attached checkout; live agent unknown | SCIENTIFIC_TESTS + prep docs | KEEP; test separate |
| `verify/wp12-elements-loads` | `8818b1b4095bd7f5c1303d640375c2c577bdc4d8` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | 2/1 | `docs/verification/wp12_b_elements_loads_audit.md`<br>`docs/verification/wp12_b_elements_loads_authorization_request.md`<br>`tests/unit/test_wp12b_artifact_archive.py`<br>`tests/unit/test_wp12b_beam2_continuity.py`<br>`tests/unit/test_wp12b_hex20_affine_patch.py`<br>`tests/unit/test_wp12b_tet10_curved_load.py`<br>`tests/unit/wp12b_test_support.py` | .codex/worktrees/verify-wp12-elements-loads/qf_solver: clean | attached checkout; live agent unknown | DOCUMENTS + NEW TESTS | MERGE audit only |
| `verify/wp12-legacy-cross-route` | `e59298e2deef9df5dc612b7962ce12d823080217` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | 2/1 | `qualification/0_2_12/vv_local/wp12_legacy_cross_route/COVERAGE_MATRIX.tsv`<br>`qualification/0_2_12/vv_local/wp12_legacy_cross_route/LEGACY_CROSS_ROUTE_REPORT.md` | QFSolverAgents/wp12-legacy-cross-route: clean | attached checkout; live agent unknown | DOCUMENTARY_DONE | MERGE report/matrix |
| `verify/wp12-rotor-performance` | `4adc0c220369b7b8f257f604ca2bb9e89d12c1c3` | `cbdd54aadbb640a96c6b6b5b9726e1247da36012` | 2/1 | `qualification/0_2_12/vv_local/wp12_rotor_performance/ROTOR_PERFORMANCE_PLAN.md` | .codex/worktrees/wp12-rotor-performance/qf_solver: clean | attached checkout; live agent unknown | DOCUMENTARY_PLAN | MERGE plan |
| `origin/codex/wp12-dynamic-harmonic-verification` | `d9deddbd6b42467c5fdc9e278bd54e97605f5738` | `bf8732c49b20cf74af65b0c7a358f997b5b28e1f` | 4/8 | `qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_EXPERIMENT_PLAN.md`<br>`tests/unit/test_modal_newmark.py`<br>`tests/unit/test_reduced_harmonic.py`<br>`tests/unit/test_wp07_uniform_base_acceleration.py`<br>`tests/unit/test_wp12_observable_archive_synthetic.py` | no attached worktree: — | no attached worktree; external task unknown | REMOTE_BEHIND_LOCAL | KEEP; reconcile separately |
| `origin/emptiesvoids-cloud/0.2.12` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | `98456355f0a85dff9edf7f37d53c7c6fff59bf37` | 0/0 | — | no attached worktree: — | no attached worktree; external task unknown | CENTRAL_RELEASE_HEAD | KEEP |

## Detached worktrees

None were registered at this snapshot.

## Exact exclusive commits relative to the central ref

Every commit listed is reachable from its branch/ref and not reachable from the central ref. “None” means no exclusive commits by ancestry; it does not establish clean files, no task dependency, or absence of equivalent content elsewhere.

### `audit/wp12-advanced-physics`
- `71461362e1a6f720aac6a9f854d67048f4d469b7` — docs(wp12-c): archive J2 objectivity protocol
- `e8ace46aa64c98d7c3650b2b449ab3951f8e5d6d` — docs(wp12-c): finalize advanced physics audit

### `codex/hex8sri-controller-registration`
- `616c9e2be7f020677bea5f67c92680bbe396aa3e` — policy: register bounded HEX8-SRI preparation scope
- `fb89bb98759280871dd38393ea802cc2db9488da` — dev(controller): keep HEX8-SRI preparation-only until Owner go
- `67816c8de2b7954149d94ae7303e4653ba6d9f4b` — dev(controller): pin HEX8-SRI single-thread budget
- `780e0d8ce901e54b844a916ecb1ebbd10a2be894` — dev(controller): add isolated HEX8-SRI research preflight

### `codex/wp07-serialization-integration`
- None.

### `codex/wp12-dynamic-harmonic-verification`
- `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66` — docs(wp12): record bounded dynamics results
- `d9deddbd6b42467c5fdc9e278bd54e97605f5738` — fix(wp12): distinguish ledger and series attempt identities
- `1f609e52fe7838a8e2c61684a2658429fac00a5e` — fix(wp12): archive observables before assertions
- `ed24d6b00d95e339b288a8ec8fa0edf16149be5a` — Preserve WP12 Newmark scientific observables
- `e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d` — test: prepare WP12 dynamic and harmonic checks

### `codex/wp12-policy-finalization`
- None.

### `codex/wp12-policy-reconciliation`
- `aecddc6277a52789f2f3b34642393db344d87460` — chore: register exact WP12 HEX8-SRI diagnostics
- `71ca96dcc7302b08d332bd667e54948f10f3191f` — fix: allow exact WP12 element verification nodes

### `codex/wp12-policy-registration-consolidation`
- None.

### `codex/wp12-rotor-registration-preparation`
- None.

### `codex/wp12b-elements-controller-extension`
- None.

### `docs/wp12-consolidation`
- None.

### `docs/wp12-legacy-coverage-roadmap`
- None.

### `emptiesvoids-cloud/0.2.12`
- None.

### `emptiesvoids-cloud/wp12-autonomous-policy-onboarding`
- `e8ad947ddf86ee896d6c3335281b0e5f5a635ce0` — feat(dev): add bounded WP12 dynamics scope
- `49069df1f8fbfc15670bb31cca8d8a4de02de504` — feat(dev): register bounded WP12 worktrees

### `emptiesvoids-cloud/wp12-autonomous-policy-root-luna`
- `f939f6ee3c4d5a90d68dbee9b70e563aedf88b9a` — feat: register bounded WP12 development scopes

### `emptiesvoids-cloud/wp12-dynamics-selective-integration`
- `f843d9286894d938df8503028d9d553baa27e1ed` — docs: record WP12-B cases as prepared not authorized
- `8b90eb70141dad71f15425570ae04bf001fd9ba0` — docs: selectively consolidate WP12 dynamic evidence

### `experiment/wp12-tet4-convergence`
- `9c48bd5559b898db3bb76bef05b9566302c613c8` — docs: consolidate WP12 TET4 FEM findings
- `619fddd97d56936ca3333cbeca9e7ae46dbd6a8e` — test: add WP12 TET4 FEM convergence targets
- `11efa11c78609a18e0ee8d615b230e9b79ac8705` — Correct TET4 quality quantile reporting
- `8b85edc7b3136be6749fef48d034bf247ec66d51` — Make TET4 preparation script self-contained
- `200f589dd13da08b3b7c1cd7e49801073c7698e0` — Prepare controlled WP12 TET4 convergence models

### `fix/wp12-wp07-serialization`
- `0a2e8135a9d4b6d80abf41dbdd9bf2aefa1cafd6` — fix: preserve signed zero in reduced harmonic results

### `research/hex8-sri-equilibrium`
- `76d9161951fe8848af07aaf326376da8de259f9e` — docs(hex8-sri): record bounded campaign authorization request
- `528a87b18ca18196ee82f31339e9990d32044131` — research(hex8-sri): freeze six execution manifests
- `b547cf0e1c8057ef7f58ba780967d1b19c891ac4` — research(hex8-sri): prepare gated structural campaign harness
- `98c109ba09a6c094419636397a68b98ff261418c` — chore(hex8-sri): preserve manifest bytes on checkout
- `6766eb9a5544e955382684acab814390f825aca0` — docs(hex8-sri): prepare six structural case manifests
- `0351bc3bfa0edee6552739549b7ae447bbd5851b` — docs(hex8-sri): add structural campaign draft builder
- `344bb385b905544e8d94df496c312d5904edb55f` — test(hex8-sri): embed frozen historical operator
- `a306007b4af25971bb460ed99f0dec058e5e9658` — test(hex8-sri): reserve pending structural campaign nodes
- `b05ddb53350302201ee05a4e61e37016979a4631` — docs(hex8-sri): refine bounded FEM proposal
- `971a091f98924343a1f51104b53641c247755459` — docs(hex8-sri): document quadrature verification
- `125702e0a7bede798a615a635c3e579e49daa19f` — fix(hex8-sri): apply central volumetric quadrature weight

### `test/wp12-fem-regressions`
- `fa889f480766506787941617fa0db4124381c63b` — fix: bind HEX8-SRI archives to WP12 attempt evidence
- `444e3cd7c5cba64327bf562dd61274f9fbe4439d` — test: add bounded WP12 HEX8-SRI diagnostics
- `5153ab510f0a234c3a647b1c537598cbc8c83e09` — docs: prepare WP12 HEX8-SRI diagnostics
- `a873d6345d7435a932087abb3e799d3d342b9417` — docs: record WP12 Agent 3 coverage review

### `verify/wp12-elements-loads`
- `8818b1b4095bd7f5c1303d640375c2c577bdc4d8` — tests: prepare WP12-B element continuity cases
- `06c147a98b4e70e7b5fe365f2e48eb16a3a9fd6f` — docs: finalize WP12-B element load audit

### `verify/wp12-legacy-cross-route`
- `e59298e2deef9df5dc612b7962ce12d823080217` — docs(wp12): document dynamic node reconciliation plan
- `37a8ae22f1531fc8ab00ec91c6e4ff0fe04585ac` — docs(wp12): finalize legacy cross-route audit

### `verify/wp12-rotor-performance`
- `4adc0c220369b7b8f257f604ca2bb9e89d12c1c3` — docs: refresh WP12 rotor controller identity
- `582ca479713b94ab08764be8f79657b9b4d446fa` — docs: prepare WP12 rotor regression and performance plan

### `origin/codex/wp12-dynamic-harmonic-verification`
- `d9deddbd6b42467c5fdc9e278bd54e97605f5738` — fix(wp12): distinguish ledger and series attempt identities
- `1f609e52fe7838a8e2c61684a2658429fac00a5e` — fix(wp12): archive observables before assertions
- `ed24d6b00d95e339b288a8ec8fa0edf16149be5a` — Preserve WP12 Newmark scientific observables
- `e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d` — test: prepare WP12 dynamic and harmonic checks

### `origin/emptiesvoids-cloud/0.2.12`
- None.

## Cleanup proposal

No ref qualifies for immediate `DELETE_CANDIDATE`: worktrees remain attached to the integrated/done refs and concurrent workspace activity is visible. Later review candidates include `codex/wp07-serialization-integration`, `codex/wp12-policy-registration-consolidation`, `docs/wp12-legacy-coverage-roadmap`, and possibly `fix/wp12-wp07-serialization` (equivalent file trees, distinct ancestry). Before any candidate deletion, release its worktree, prove no task/process or manifest/receipt depends on it, compare tree/blob identity and patch history, and retain a recoverable archive ref. No deletion is authorized.

The main checkout is at `2aa994f34900` (74 commits behind the remote) with two modified E01 tests and two untracked directories; it was not switched or cleaned. Dirty HEX8 research, policy-finalization, and rotor-registration changes remain untouched.
