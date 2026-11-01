# GitHub Branch Consolidation and Cleanup Report

**Repository:** emptiesvoid-cloud/QF_solver
**Audit date:** 2026-11-01 (Europe/Paris)
**Remote:** https://github.com/emptiesvoid-cloud/QF_solver
**Consolidation checkout:** C:/Users/fari/.codex/worktrees/wp13-branch-consolidation-20261101/qf_solver
**Local branch:** codex/wp13-branch-consolidation-20261101

## Executive result

- GitHub showed 48 live branches before cleanup. Thirteen refs were conditionally deleted after the branch-head SHA, open-PR state, preservation references, and content equivalence were checked. A fresh remote-head query confirmed all thirteen absent and **35 live branches remaining**.
- Every removed PR head is still available at its GitHub pull ref, with the exact pre-delete SHA. For twelve deleted heads, the root tree exactly matches the corresponding retained merge result; the other head is already an ancestor of the release. No unique source tree was lost.
- PRs #114, #115, and #116 remain open and unchanged. No changes were pushed and no new PR was created.
- PR #115 and #116 were cherry-picked onto a local branch starting from the current #114 candidate. All five authorized non-scientific targeted tests passed.
- WP13 P0 remains PARTIAL_OR_BLOCKED. No scientific ledger, qualification result, threshold, manifest, or acceptance decision was edited. No local directory, environment, archive, calculation output, or worktree was removed.

## Snapshot and comparison method

The current remote refs were read with git ls-remote --heads origin after the deletions. Current protected heads are:

| Ref | HEAD | Root tree |
|---|---|---|
| main | e367fe58b2b9ebb4aef321424ca775e80e82d9ca | 0f10660178f005dc84da70771fb31362fe6c646a |
| emptiesvoids-cloud/0.2.12 | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 57b1c9c5f890559e94123656cda72937ca9cd7a1 |
| codex/wp13-release-engineering-20261031 | 67adffbe3d4292c55c6c66cb2e37f8f1a0563e4d | fead52cadad244df1d36c8dd4c9a83f0b321e26f |

The root tree IDs differ. Each retained branch's exact tree ID below can therefore be compared directly with main, release, and the WP13 candidate; every retained branch has a distinct root tree from those three except the corresponding protected ref itself. The root tree ID fingerprints the complete recursive tree and its blobs.

The existing detailed branch appendices are qualification artifacts and were not changed:

- qualification/0_2_12/vv_local/WP12_BRANCH_INVENTORY_20261031.csv
- qualification/0_2_12/vv_local/WP12_DIVERGENT_HEADS_20261031.csv

Those appendices were calculated against the earlier release baseline 24885ae7eec606c473328bece5be3310779e55a5. The current release advanced to ab137051d920d7fa9aae9a3012a48b2b26e2198b through PR #113. Their path lists and worktree associations remain useful for the 42 unchanged initial heads, but their path counts are historical and are not presented here as recomputed current-release counts. For every live ref, the comparison appendix below records the refreshed HEAD, exact root tree, current merge-base with release, and exact number of head commits not reachable from current release.

The old inventory records the detailed changed paths, patch commits, prior PR associations, and worktree associations. It also documents science and policy provenance that would not be visible from ahead/behind counts alone. A merged PR was never treated as proof of equivalent branch content without a tree or ancestry check.

## Initial 48 branch classifications

Each of the 48 initial live refs is represented exactly once across the two tables below: 35 retained refs and 13 deleted refs. A, B, C, and E use the owner's definitions.

### Retained live refs — 35

| Ref | Current HEAD | HEAD committer time | PR status / base | Class | Evidence and reason to retain |
|---|---|---|---|---|---|
| audit/wp12-advanced-physics | 71461362e1a6f720aac6a9f854d67048f4d469b7 | 2026-10-26 22:17 +01:00 | — | E | Preserves the unique J2 objectivity protocol and scientific history. |
| codex/hex8sri-controller-registration | 43af3e8b3d17b3be1dfaa8fed3d390f29a5cc80f | 2026-10-27 07:52 +01:00 | #26 closed / main | E | Closed unmerged controller registration history; preserve the exact controller/provenance record. |
| codex/vv3d-family-remainder-optimized | f40ccf9facd0d0bc4583fc3a6aa868834e6395f5 | 2026-10-30 23:10 +01:00 | #104 closed / release | E | Contains unique prepared experiment and manifest material. It is not a safe deletion based on PR state alone. |
| codex/vv3d-tet4-l3-optimized | 096857b890353c8cf1c8e02007fe97c5455cb50a | 2026-10-30 19:41 +01:00 | — | A | Exact branch/worktree registration for the bounded TET4 L3 diagnostic. |
| codex/wp12-controller-designation-0d91fc5-20261028 | a813c7b592939a1f25635c48c37ce79efae40d03 | 2026-10-28 18:43 +01:00 | #70 closed / release | E | Historical controller designation and source lineage remain useful for auditability. |
| codex/wp12-dynamic-harmonic-verification | 7406e34efc28ed8f18c15440115595dfa3dd9ca5 | 2026-10-28 16:32 +01:00 | — | A | Registered dynamic/harmonic verification scope and active worktree dependency. |
| codex/wp12-rotor-scope | 8e62d3cd83da95ecaf02ca710fe55e8a2ee7162a | 2026-10-26 22:46 +01:00 | — | E | Preserves the unique bounded rotor-scope history and its provenance. |
| codex/wp12b-corrective-registration | e3debf15c57fdbc263355d579cb81600222814da | 2026-10-26 23:24 +01:00 | — | E | Preserves the corrective WP12-B campaign registration history. |
| codex/wp13-release-engineering-20261031 | 67adffbe3d4292c55c6c66cb2e37f8f1a0563e4d | 2026-11-01 10:10 +01:00 | #114 open / release | A | Current WP13 release candidate and open PR head. |
| codex/wp13-release-scan-optimization-20261031 | 368b3ef3e10b5df9e325f25bb62880a50ee24ac2 | 2026-10-31 23:07 +01:00 | #116 open / WP13 candidate | A | Open stacked PR; its two source commits were selectively replayed locally. |
| codex/wp13-test-contact-separation-20261031 | 00306cd4f6358947f329ded2f7450925225037ce | 2026-10-31 22:16 +01:00 | #115 open / release | A | Open PR head; its documentation-asset test change was selectively replayed locally. |
| diagnostic/vv3d-tet4-l3-performance | 59fdf0be1dd4896eb2c09b49127d02cedd2324ae | 2026-10-30 18:03 +01:00 | — | A | Registered diagnostic scope and existing worktree dependency. |
| docs/wp12-consolidation | 640dfa69bc483e01a315de63e7e25c82ffeae2c9 | 2026-10-26 22:37 +01:00 | — | E | Preserves the original WP12 consolidation report and provenance. |
| docs/wp12b-hex8sri-prospective-audit-20261029 | d57ee12029b27fb0c786e5decae84998a80fc726 | 2026-10-29 22:21 +01:00 | #89 merged / release | E | Its current branch head has a distinct tree and preserves prospective scientific audit evidence; merged status alone does not establish equivalence. |
| emptiesvoids-cloud/0.2.12 | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 2026-10-31 11:15 +01:00 | #113 merged / release | A | Protected release ref. |
| emptiesvoids-cloud/fix-wp12b-scope-identity-guard | 2db9c9b54283a6c78953fbcede427527101ec8cf | 2026-10-26 23:02 +01:00 | — | A | Exact scope-identity guard dependency; prior inventory records a dirty associated worktree, which was left untouched. |
| emptiesvoids-cloud/research-wp12-vv3d-adaptive | 34812fc7525859686f88ac7e56e1833ee558cb66 | 2026-10-29 23:08 +01:00 | #84 merged / release | E | Current head retains adaptive research drafts and prepared evidence beyond the merged PR head. |
| emptiesvoids-cloud/vv3d-controller-designation-0653 | bd0a6524023b10f77fc733055dee84f86e9f5cb1 | 2026-10-29 23:09 +01:00 | — | E | Preserves VV3D controller designation provenance. |
| emptiesvoids-cloud/wp12-autonomous-policy-onboarding | e8ad947ddf86ee896d6c3335281b0e5f5a635ce0 | 2026-10-26 19:05 +01:00 | — | E | Preserves original autonomous-policy onboarding history. |
| emptiesvoids-cloud/wp12-autonomous-policy-root-luna | f939f6ee3c4d5a90d68dbee9b70e563aedf88b9a | 2026-10-26 18:32 +01:00 | — | E | Preserves policy-root and worker provenance. |
| emptiesvoids-cloud/wp12b-hex20-r2-controller | 624a984908f5be0eea91f2efd7d980e5c04a8ac5 | 2026-10-29 08:02 +01:00 | #73 merged / release | E | Preserves the distinct prospective HEX20 R2 controller proposal and its review trail. |
| experiment/wp12-tet4-convergence | 9c48bd5559b898db3bb76bef05b9566302c613c8 | 2026-10-26 19:52 +01:00 | — | A | Registered TET4 convergence evidence/worktree dependency. |
| fix/wp12-wp07-serialization | 0a2e8135a9d4b6d80abf41dbdd9bf2aefa1cafd6 | 2026-10-26 18:05 +01:00 | — | A | Exact compatibility/serialization scope used by registered work. |
| fix/wp12a-base-motion-observability-20261028 | 7406e34efc28ed8f18c15440115595dfa3dd9ca5 | 2026-10-28 16:32 +01:00 | — | E | Same HEAD and tree as codex/wp12-dynamic-harmonic-verification, but the exact ref is cited as prospective source in docs/development/WP12A_BASE_MOTION_FINAL_OWNER_EXECUTION_DOSSIER.md:23. Retain the provenance alias. |
| fix/wp12a-harmonic-observability-20261028 | bf88803a8464a805e953013a2593fb06e6ea4659 | 2026-10-28 14:39 +01:00 | — | E | Preserves unique harmonic observability evidence and history. |
| fix/wp12a-p0-batch-preparation-20261029 | 8651e868089fb4aee5f9ceb1c2ee69c1d80c4fc1 | 2026-10-29 07:57 +01:00 | #74 merged / release | E | The exact branch name is cited in qualification/0_2_12/WP12A_P0_OWNER_BATCH_AUTHORIZATION_DOSSIER.md:9 as preparation provenance. |
| main | e367fe58b2b9ebb4aef321424ca775e80e82d9ca | 2026-10-07 21:18 +02:00 | — | A | Protected default branch. |
| research/hex8-sri-equilibrium | 5304e3f00e73a916d1af4c1d75375a9b051f0524 | 2026-10-28 18:29 +01:00 | — | E | Preserves unique HEX8-SRI experiment reports, results, and manifest history. |
| research/hex8sri-equilibrium-8x4x4-20261030 | e251883a0dd13e20628eb2ee229b630603af1efb | 2026-10-30 07:50 +01:00 | — | A | Registered exact source/manifest scope and associated worktree. |
| research/wp12-vv3d-recovery-r2 | ac0f1855a88cc66e48e629eadc4f0e681d1d719d | 2026-10-30 23:20 +01:00 | #105 merge target | A | Retained R2 recovery branch and merge target that preserves PR #105 content. |
| research/wp12b-hex20-r2-prospective | 9b998f42c1543f9d40b2f7a7ef88fd59153a65ee | 2026-10-29 08:01 +01:00 | — | A | Registered prospective R2 scope and associated worktree. |
| test/wp12-fem-regressions | fa889f480766506787941617fa0db4124381c63b | 2026-10-26 19:44 +01:00 | — | A | Registered regression suite and evidence binding; retained without running FEM tests. |
| verify/wp12-elements-loads | 8818b1b4095bd7f5c1303d640375c2c577bdc4d8 | 2026-10-26 22:27 +01:00 | — | A | Exact branch name is pinned by the verification registration. |
| verify/wp12-legacy-cross-route | e59298e2deef9df5dc612b7962ce12d823080217 | 2026-10-26 22:20 +01:00 | — | E | Preserves unique legacy cross-route verification plan/provenance. |
| verify/wp12-rotor-performance | 4adc0c220369b7b8f257f604ca2bb9e89d12c1c3 | 2026-10-26 22:21 +01:00 | — | A | Exact registered rotor-performance verification scope. |

### Deleted refs — 13

All PRs shown as merged were merged before the ref deletion. Before deleting each ref, its GitHub HEAD still matched the recorded SHA. After deletion, all 13 were absent from live heads, and refs/pull/<n>/head continued to resolve to the exact recorded source SHA. Tree equality below was checked against the indicated retained merge result; where source commit ancestry was not retained by the merge strategy, the exact tree match proves content equivalence. Branch-only commit counts are against the current release HEAD, not a proxy for useful change.

| Deleted ref | Pre-delete HEAD | HEAD committer time | PR / base | Class | HEAD tree | Current-release head-only commits | Preserved content proof |
|---|---|---|---|---|---|---:|---|
| codex/vv3d-family-runner-fix-20261031 | 421e45b01951f72ed0cdb1698db2cce1b41464fa | 2026-10-31 08:33 +01:00 | #108 merged / release | B | 9f96ab5fb7c622eb86914f15919ca69879b2b3a3 | 0 | Source head is an ancestor of retained release. |
| codex/wp13-windows-diagnostic-20261031 | 1ef0ec97351971d65e79d45ad9ff234103676b36 | 2026-11-01 09:34 +01:00 | #117 merged / WP13 candidate | C | a9c72b178887b1eee725531e9c833ffa5c80865b | 30 | Exact tree match to merge commit bf30a27a4525981b38c5440f0a3f0c50ba890865; candidate retains that result. |
| docs/wp12-global-closeout-wp13-handoff-20261031 | 19b68e4a05eb83dfbdac23f5747e526ad469d610 | 2026-10-31 11:15 +01:00 | #113 merged / release | C | 57b1c9c5f890559e94123656cda72937ca9cd7a1 | 5 | Exact tree match to current release HEAD ab137051d920d7fa9aae9a3012a48b2b26e2198b. |
| fix/wp12a-p0-9ed-controller-designation-20261029 | e73f9104c27bf0eb843be730d848b1c1b98a6758 | 2026-10-29 09:39 +01:00 | #79 merged / release | C | 46397d6514c01ff05408ea5318626a5418dbb0a8 | 1 | Exact tree match to merge commit 098382938df641751271acb62b7c8e666cfa8e09. |
| fix/wp12a-p0-c47-controller-designation-20261029 | 0afb189335b5667f90d5b1de3d955c2bb5c04613 | 2026-10-29 08:40 +01:00 | #77 merged / release | C | a32ccae8b3441af138c54995a5ef401282152638 | 2 | Exact tree match to merge commit 6c920ea31daa95addbce668aac26e337aaad7443. |
| docs/wp12a-owner-bounded-closure-record-20261029 | aaf6912c63011e2b413d5636f774ae80c9b54113 | 2026-10-29 10:15 +01:00 | #81 merged / release | C | a1d032eaf824f81f20a34d6ecbdbbcde7f0a73bf | 1 | Exact tree match to merge commit f0ec9566a8596abc92c2eec0ce2b49f8c98ac98d. |
| docs/wp12f-final-consolidation-20261031 | a05d621d2b9c1b41fedd584502bd36727cd92633 | 2026-10-31 10:25 +01:00 | #112 merged / release | C | 32f669b36d9647f6c4c27072870e6282929aa107 | 1 | Exact tree match to merge commit 24885ae7eec606c473328bece5be3310779e55a5. |
| fix/wp12a-p0-controller-designation-20261029 | d32a6254ff63ff9b193a80b2a70322ea51660d19 | 2026-10-29 08:14 +01:00 | #75 merged / release | C | 1a9199e0187de516dee43ddd7611ae6c1d0b3515 | 1 | Exact tree match to merge commit ae52f5598819877af1423452f01e684d88e8bb77. |
| fix/wp12a-p0-runtime-freeze-20261029 | 14efaa444cdd6d432e04d8e79d74855b2feea0cf | 2026-10-29 08:44 +01:00 | #78 merged / release | C | 3935f0c78c14e4d85e64f0a8d951a025cabb4695 | 1 | Exact tree match to merge commit 9ed7a375b25ac195740cbca8db00b0265e036dbb. |
| codex/hex8sri-guard-registration-20261028 | b0e82c2817365f17602671ed2713acea217e6bcc | 2026-10-28 18:34 +01:00 | #68 merged / release | C | 3d57c36c948c9cc3fbc8a5d399fc465245c54a11 | 1 | Exact tree match to merge commit 0d91fc5a9bc09875526af6f17cf42c3ac666c5b7. |
| docs/wp12a-p0-bounded-closure-20261029 | bb10b7da7d27782c4f6a37cb9eb4fc28d53ced23 | 2026-10-29 10:03 +01:00 | #80 merged / release | C | be9047fdec03014fb96be27e47edeee7f83f3970 | 1 | Exact tree match to merge commit de660d6fbeb28044f537cdb6e85235a4e918f417. |
| emptiesvoids-cloud/wp12-vv3d-controller-designation | bb3b45cec5ffa21f1a36486023b02758d6b1a156 | 2026-10-29 20:15 +01:00 | #86 merged / release | C | e8c97535b48ca82a53a19f8af90ef9050d6034a8 | 2 | Exact tree match to merge commit e463195aaa044579e3395e5216dfa845bfdfd230. |
| codex/vv3d-family-remainder-source-r2 | ad6e980b75325c3a9c92518ee75794df239ec3be | 2026-10-30 23:13 +01:00 | #105 merged / research/wp12-vv3d-recovery-r2 | C | 39bf88bef3d72e6c970a3928d577239074f7b9fb | 20 | Exact tree match to retained merge target at ac0f1855a88cc66e48e629eadc4f0e681d1d719d; the source PR ref remains available. |

No open PR depended on these 13 branch refs. The original PR head refs still match their recorded pre-delete SHA. No local branches, worktrees, or directories were deleted.

## Current-release graph and tree comparison for the 35 live refs

For the columns below, “head-only” is the exact count from git rev-list release...HEAD: commits reachable from that branch HEAD but not from the current release HEAD. Merge-base is against current release ab137051d920d7fa9aae9a3012a48b2b26e2198b. Full tree IDs are shown. A root tree equal to the protected refs is marked in the final column; all other rows have distinct roots from main, release, and the WP13 candidate.

| Ref | Root tree SHA | Merge-base with release | Head-only commits | Tree relation |
|---|---|---|---:|---|
| audit/wp12-advanced-physics | d5feecbd69b9a41eb3c3b4c9b6f08b1c56c814d6 | cbdd54aadbb640a96c6b6b5b9726e1247da36012 | 2 | distinct |
| codex/hex8sri-controller-registration | 5dec04f24c86c46de200e3c0b64ee78f39450aff | 2aa994f34900f39bef8df9db5fb025157fb694bb | 11 | distinct |
| codex/vv3d-family-remainder-optimized | 0c0a636f72fada91f53edc9a065985b946e41b83 | fe5254cfeb8be12e4f315aa11362bf94233af968 | 26 | distinct |
| codex/vv3d-tet4-l3-optimized | ca84f375e4aaf91bee3fd42bfa87406c796681bd | 8e594c3a331d5a9a1d081b5911dc3e7c8b56e567 | 24 | distinct |
| codex/wp12-controller-designation-0d91fc5-20261028 | fa524a4a5dd98810922c82f2b397a2a332ea87d9 | 0d91fc5a9bc09875526af6f17cf42c3ac666c5b7 | 1 | distinct |
| codex/wp12-dynamic-harmonic-verification | a618d0d1790ab8642f408a78b2d2856debcc60c0 | bf8732c49b20cf74af65b0c7a358f997b5b28e1f | 11 | distinct |
| codex/wp12-rotor-scope | 1261f00d334bc637e5aedf956429617aad33fed5 | 98456355f0a85dff9edf7f37d53c7c6fff59bf37 | 1 | distinct |
| codex/wp12b-corrective-registration | e25a71bdc8d2c852dfa6b7e436628debfab5fa1c | 7d429164d705d62b8c0c8ce64b936a6b2d9e8580 | 1 | distinct |
| codex/wp13-release-engineering-20261031 | fead52cadad244df1d36c8dd4c9a83f0b321e26f | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 30 | candidate |
| codex/wp13-release-scan-optimization-20261031 | 124b6d01874ab3a0b68eed1584f24db53498665b | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 25 | distinct |
| codex/wp13-test-contact-separation-20261031 | 87c67d33876c63c30a58c263e453010bebbf5658 | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 1 | distinct |
| diagnostic/vv3d-tet4-l3-performance | 80587b0c38d72dab4695af6f159e7700c41145f9 | 8e594c3a331d5a9a1d081b5911dc3e7c8b56e567 | 22 | distinct |
| docs/wp12-consolidation | 15837e6c759b09fbd4fd3169df0ff8094426d7a6 | 98456355f0a85dff9edf7f37d53c7c6fff59bf37 | 1 | distinct |
| docs/wp12b-hex8sri-prospective-audit-20261029 | e2153d153493234029ed3c0b321d646fba936a21 | 8e594c3a331d5a9a1d081b5911dc3e7c8b56e567 | 1 | distinct |
| emptiesvoids-cloud/0.2.12 | 57b1c9c5f890559e94123656cda72937ca9cd7a1 | ab137051d920d7fa9aae9a3012a48b2b26e2198b | 0 | release |
| emptiesvoids-cloud/fix-wp12b-scope-identity-guard | d3db20b272aea032199efe43299cec212850d350 | cbdd54aadbb640a96c6b6b5b9726e1247da36012 | 3 | distinct |
| emptiesvoids-cloud/research-wp12-vv3d-adaptive | d4d7220a45e68e04504bef79321a2c28a690d2c6 | 8e594c3a331d5a9a1d081b5911dc3e7c8b56e567 | 16 | distinct |
| emptiesvoids-cloud/vv3d-controller-designation-0653 | 5b4cb9e7d8bfea7a5c938b73849490467c7d68c6 | 0653dde292f2090374ebfa490001b9e07c7aba17 | 1 | distinct |
| emptiesvoids-cloud/wp12-autonomous-policy-onboarding | d2f83c12cff2357b17f7dcd669ce3b31ece81b81 | 6d8f140834db75ea9b968b055af23445261d0073 | 2 | distinct |
| emptiesvoids-cloud/wp12-autonomous-policy-root-luna | e8505b8a9700ae7171ef5d2412b7674b69ebb53c | 2aa994f34900f39bef8df9db5fb025157fb694bb | 1 | distinct |
| emptiesvoids-cloud/wp12b-hex20-r2-controller | 04556891ce5b028ce4a69d10281f279b2d8a134e | aea4ce54d383efdf948021c36c80c9fe9c858cb5 | 2 | distinct |
| experiment/wp12-tet4-convergence | 633d365bf75b16157ff97d5021d5e4184c1a4dfd | 6d8f140834db75ea9b968b055af23445261d0073 | 5 | distinct |
| fix/wp12-wp07-serialization | 76ac5a92953613ba5c3b87f1cbfa2ce69b612717 | 6d8f140834db75ea9b968b055af23445261d0073 | 1 | distinct |
| fix/wp12a-base-motion-observability-20261028 | a618d0d1790ab8642f408a78b2d2856debcc60c0 | bf8732c49b20cf74af65b0c7a358f997b5b28e1f | 11 | distinct |
| fix/wp12a-harmonic-observability-20261028 | cd75a62d68a95adbbb398ee312fbc8e1fc5fb7cd | bf8732c49b20cf74af65b0c7a358f997b5b28e1f | 9 | distinct |
| fix/wp12a-p0-batch-preparation-20261029 | 78d7d1e763ae1eb3ce6c042aa1af86ac3412480f | aea4ce54d383efdf948021c36c80c9fe9c858cb5 | 5 | distinct |
| main | 0f10660178f005dc84da70771fb31362fe6c646a | e367fe58b2b9ebb4aef321424ca775e80e82d9ca | 0 | main |
| research/hex8-sri-equilibrium | 5d995ab972e8627d266e1cd2b86d2b858b93f84a | 2aa994f34900f39bef8df9db5fb025157fb694bb | 37 | distinct |
| research/hex8sri-equilibrium-8x4x4-20261030 | fdf9e76cff3293be3705cf29a3226fb480a928ad | 326b357fe752b33bb034c46ed546973abb1d2cb0 | 42 | distinct |
| research/wp12-vv3d-recovery-r2 | 39bf88bef3d72e6c970a3928d577239074f7b9fb | 8e594c3a331d5a9a1d081b5911dc3e7c8b56e567 | 21 | distinct |
| research/wp12b-hex20-r2-prospective | 76c9809690efffe9e585024db7561caca5230187 | aea4ce54d383efdf948021c36c80c9fe9c858cb5 | 3 | distinct |
| test/wp12-fem-regressions | b95972b9fc18e981af931358c2a13e1b90941794 | 6d8f140834db75ea9b968b055af23445261d0073 | 4 | distinct |
| verify/wp12-elements-loads | 0e89dab8d7edcada9de5607744a582ee2058ccbd | cbdd54aadbb640a96c6b6b5b9726e1247da36012 | 2 | distinct |
| verify/wp12-legacy-cross-route | b720340c2716681092a0ba8efae4f16ee137c968 | cbdd54aadbb640a96c6b6b5b9726e1247da36012 | 2 | distinct |
| verify/wp12-rotor-performance | d4cff12db4050e356daf2a268eee41ff72cedefa | cbdd54aadbb640a96c6b6b5b9726e1247da36012 | 2 | distinct |

The exact duplicate SHA/tree between codex/wp12-dynamic-harmonic-verification and fix/wp12a-base-motion-observability-20261028 was retained because the dossier cites the second name. It is not a duplicate of main, release, or the WP13 candidate.

## WP13 integration performed locally

The consolidation branch started at the exact current candidate HEAD 67adffbe3d4292c55c6c66cb2e37f8f1a0563e4d. Three source commits were replayed with -x and no conflicts:

| Source | Original commit | Local replay |
|---|---|---|
| PR #115 documentation-asset wiring test | 00306cd4f6358947f329ded2f7450925225037ce | f5f112a7a0286b89d714ba608d6710f38d648a8a |
| PR #116 scan test optimization, commit 1 | 3475813131d069f6f6d60adb8f59efe9495349ab | e3b86980f24212b81f6a1ccfbc112833985aa23c |
| PR #116 scan test optimization, commit 2 | 368b3ef3e10b5df9e325f25bb62880a50ee24ac2 | 1d8522f24e40c8afd3e776038d87ae89c633b7c8 |

The resulting branch is local only. Its HEAD is 1d8522f24e40c8afd3e776038d87ae89c633b7c8; its root tree is b73c0b63150572e698b637c64762ea3dd2a74df0. It contains the candidate plus those three replay commits. It was not pushed, and no PR was created.

PR #116's declared base is the WP13 candidate, but its current head is based at f00bbb9c23769f984a12c2dda37802382ffc5414. Compared with that head, the current candidate contains seven commits absent from PR #116, while PR #116 contains two source commits absent from the candidate. The two PR commits were cherry-picked onto current candidate to preserve both changes without rewriting either PR. PR #115 is one commit ahead of current release. PR #114 candidate is 30 commits ahead of current release with release as its merge-base.

The replayed changes affect tests and shared test setup only. They do not alter scanner implementation, qualification thresholds, manifests, scientific calculations, or ledgers. PR #117 is already represented by the candidate's merge result and was not replayed again.

## Deletion controls and preservation

The 13 deletions used an exact-HEAD compare-and-delete check for each ref, followed by remote verification. The GitHub PR head refs were then queried individually and all matched their recorded pre-delete SHA. Current live branch count was independently counted from the refreshed remote head list: **35**.

The initial count reconciles exactly: 48 = 35 retained + 13 deleted. Protected main and release remain at their recorded heads. The open PR heads remain at their recorded SHAs and bases.

No local checkout, branch worktree, repository folder, Python environment, archive, FEM output, or qualification artifact was deleted. The original C:/Users/fari/Documents/qf_solver checkout still has its prior modified scientific unit tests and untracked checkout-0.2.12/ and wp12-science-00428ad/ folders; they were not changed or removed. The new consolidation worktree is also retained for review.

## PR state and dependencies after cleanup

| PR | State | Head ref / SHA | Base | Result |
|---:|---|---|---|---|
| #114 | Open | codex/wp13-release-engineering-20261031 / 67adffbe3d4292c55c6c66cb2e37f8f1a0563e4d | emptiesvoids-cloud/0.2.12 | Unchanged. Candidate remains available for review. |
| #115 | Open | codex/wp13-test-contact-separation-20261031 / 00306cd4f6358947f329ded2f7450925225037ce | emptiesvoids-cloud/0.2.12 | Unchanged; source change replayed only on the local consolidation branch. |
| #116 | Open | codex/wp13-release-scan-optimization-20261031 / 368b3ef3e10b5df9e325f25bb62880a50ee24ac2 | codex/wp13-release-engineering-20261031 | Unchanged; two source commits replayed only on the local consolidation branch. |

## Targeted tests

All tests below were run individually and passed. No FEM or scientific qualification test was run.

| Test node | Result |
|---|---|
| tests/unit/test_contact_documentation_assets.py::test_contact_publisher_copies_campaign_assets_without_running_fem | PASS, 1 passed, 8.74 s |
| tests/unit/test_release_readiness.py::test_release_readiness_composes_current_scanner_and_history_statuses | PASS, 1 passed, 3.73 s |
| tests/unit/test_release_readiness.py::test_readiness_report_lists_only_machine_checkable_blocking_gate_ids | PASS, 1 passed, 1.95 s |
| tests/integration/test_release_readiness_pipeline.py::test_release_readiness_remains_dry_run_and_reports_worktree_state | PASS, 1 passed, 2.28 s |
| tests/unit/test_public_document_audit.py::test_whole_repository_document_audit_keeps_the_unresolved_public_hygiene_gate_visible | PASS, 1 passed, 181.96 s |

## Remaining review and risk

- The 17 A refs remain active/protected or satisfy exact policy, controller, verification, or open-PR dependencies.
- The 18 E refs preserve scientific results, negative/diagnostic evidence, controller history, policy history, or exact provenance references. In particular, closed PRs #26 and #104 do not justify deleting their current branches because unique source material remains.
- No remaining branch was classified F or G: there was enough evidence to preserve all 35 remaining refs, and no additional deletion met every owner condition. Historical E refs may be reconsidered only after their exact manifests, dossier citations, controller registrations, and worktree dependencies are deliberately retired.
- The main regression risk is limited validation coverage: five targeted non-scientific tests passed, but no full suite, FEM run, or qualification run was performed. This does not change WP13 P0's PARTIAL_OR_BLOCKED status or create qualification evidence.
- The #116 PR branch is behind its current base as described above; the local replay is reviewable, but the open PR itself was intentionally left unchanged.
- No merge into main or release, publication, release, tag, or scientific-ledger change was performed.

## Final count

**Initial GitHub live branches:** 48
**Deleted after proof and exact-SHA recheck:** 13
**Final GitHub live branches:** **35**
**Open WP13 PRs preserved:** #114, #115, #116
**Local unpushed consolidation branch:** codex/wp13-branch-consolidation-20261101
