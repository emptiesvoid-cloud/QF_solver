# WP12-V2-R1 — execution protocol revision

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

This prospective revision addresses result classification and exact command construction for the single H1 audit. It introduces no mechanical formulation, model, numerical threshold or new linear solve. A future execution still requires a separate complete Owner decision for the revised manifest.

**Disposition: WP12_V2_R1_READY_FOR_OWNER_EXECUTION_DECISION.** This is a preparation disposition, not case execution permission.

- [Frozen R1 manifest](V2_R1_MANIFEST.json), SHA-256 `fe19d40bd46c0d8c1fc0fc6f49cb37e978b8132d5c5077d15b4ab8d9f46db77d`.
- [Complete proposed Owner decision and exact command](OWNER_DECISION.md).
- [Prospective test source](../../../../../tests/unit/test_wp12_v2_tet4_operator_audit.py).
- [Pure result classifier](../../../../../scripts/local_vv/results.py) and [standalone synthetic checks](../../../../../tests/synthetic/test_wp12_v2_r1_result_profile.py).

## Preserved preparation and evidence

The [original V2 manifest](../V2_MANIFEST.json), SHA-256 `dd72bc80ff5dbae1d105bef5ad6f778eb9046335706697db0479b0764145d665`, remains unchanged and `PREPARED_NOT_AUTHORIZED`. Its pinned runner is commit `9b1465d79cb19985c823c1329af2540de665a556`; that runner omitted `-s`, while the manifest recorded it. The integration branch already contained a later runner with `-s`, but that branch file was not the frozen runner selected by the original manifest. R1 must bind the implementation actually used.

U1/U2 remain historical `PYTEST_PASS_ONLY`, U3 remains historical `FAIL`. The H1 HDF5 fixture, derived archived displacement fields, scientific commit `00428adf38e9397340ac136f6f503a268eb671da` and tree `df4ec667bf746b042c900fad1f86bf542e1a437b` are preserved. The original V2 test checkout and runner checkout remain available at their old identities.

## Scientific result protocol

The [original numerical criteria](../V2_NUMERICAL_CRITERIA.md) supply the unchanged values, normalizations, exact discrete identities and diagnostic observables. R1 replaces their provisional gamma interpretation with this explicit rule: Owner acceptance of local limitations cannot establish an unobserved arithmetic assumption.

| Field | Meaning |
|---|---|
| `rounding_assumptions_verified` | Whether all assumptions needed for the gamma interpretation have been demonstrated. |
| `gamma_bound_evaluated` | Whether the bound comparison was computed from available valid data. |
| `gamma_bound_satisfied` | The observed comparison, or null when unavailable; its Boolean value alone has no scientific acceptance authority. |
| `gamma_scientific_status` | `PASS` only with verified assumptions and a satisfied bound; `FAIL` only with verified assumptions and a violated bound; otherwise `INCONCLUSIVE` or `ERROR` for invalid data. |
| `pytest_execution_status` | Execution/assertion outcome, assessed separately from the gamma and overall scientific statuses. |
| `overall_scientific_status` | The bounded H1 assessment, including mandatory assertion failures and unresolved gamma assumptions. It grants no qualification disposition. |

Runtime rounding mode and all internal reduction intermediates remain unobserved in this candidate. Consequently gamma is expected to remain `INCONCLUSIVE`, even if the numerical bound comparisons are satisfied. No fallback tolerance is introduced. Conditional gamma assertions are not accepted as passed when their preconditions are unverified. The payload records acceptance checks actually reached; checks after a failure remain `NOT_REACHED`. A failure before a complete result payload is produced is an incomplete/error result, never a scientific pass.

The previously recorded exact archived energy/work identity is now explicitly included in the final mandatory assertion list. Its equation and acceptance rule are unchanged. The no-subnormal observation is an arithmetic assumption diagnostic, so it cannot independently establish a mechanical failure or verify all internal intermediates.

## Command and evidence protocol

The new profile binds a fixed pytest argument vector with `-s`, `--noconftest`, disabled automatic plugins/cache, one provenance plugin, the pinned configuration and one exact nodeid. The runner compares the recorded template to that fixed profile before launch. An extra option, missing option, changed nodeid or divergent template denies the launch. No shell command or suite selector is accepted.

The structured marker is emitted to stdout. A missing, malformed, duplicated or inconsistent payload cannot establish scientific `PASS`. JUnit, actual selection evidence, assertion execution and scientific control statuses remain separate evidence. Existing v1 profiles retain their historical interpretation.

The receipt and the durable attempt summary record the pytest, gamma and overall scientific statuses separately. The CLI returns 1 when the overall scientific status is not `PASS`, including the expected `INCONCLUSIVE` outcome; that exit code must not trigger a retry. A future reviewer must interpret the recorded statuses and raw evidence together.

## Frozen identities and checks

| Checkout | Commit | Tree |
|---|---|---|
| Science | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` |
| Tests R1 | `67813b4a36a057bbaa9e5fba32bcdea66ddf4df3` | `ffee889f0cd70b089ec8e1719b84a667babfa1be` |
| Runner R1 | `a9dcd5ac2b13e02db7e1fe2bc6fb940fbb490a09` | `fd4ea17d7a25452f72faa58a62704daa51b62fab` |

The three dedicated checkouts are clean. The manifest inventories 34 files with SHA-256 and Git blob OID. AST comparison confirms that all module-level constant values, including thresholds, fixture hashes and the exact nodeid, match the original V2 test. The H1 fixture SHA-256 remains `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`; the derived archived-field SHA-256 remains `a862bd016bb408566459491b3c726694e2cd408e084031b4f693223883429ba8`.

Validation on 2026-10-26 used only syntax/AST, Ruff, JSON, file/Git identities, static command comparison, documentation links and the direct stdlib harness:

```text
E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe -B E:\QFSolverWP12B\runner-local-vv-v2r1\tests\synthetic\test_wp12_v2_r1_result_profile.py -v
Ran 11 tests in 0.016s — OK
```

The harness uses fake JUnit/JSON files, forbids subprocess launch, and checks that pytest, solveur, NumPy and SciPy were not imported. It covers successful pytest with gamma PASS/INCONCLUSIVE, failed pytest with gamma PASS, missing/malformed/duplicate JSON, inconsistent evaluation fields, wrong nodeid, divergent command/options and full argv equality. No pytest invocation, test collection, solver import, stiffness assembly, matrix-free product or scientific calculation occurred. The Manager reviewed the changes and requested consistency corrections; this review is not an independent scientific audit. No operating-system isolation guarantee was added or tested.

The Python/native-library observations in the manifest come from the prior 2026-10-26 preflight. R1 did not repeat the import probe because this mission permits only static/synthetic checks. They must be revalidated under the future complete Owner decision before scientific launch.

## Owner gate and local limitations

The revised manifest remains `PREPARED_NOT_AUTHORIZED`, with `execution_authorized=false`, one case, one attempt, a proposed 300-second timeout and a 16 MiB software-polled limit per log stream. Its new namespace is distinct from the original V2 namespace. No attempt has been reserved.

The local runner uses the interactive account and its permissions. It provides no filesystem sandbox, restricted token, Windows Job Object, hard CPU/RAM/disk quota or guaranteed descendant containment. The account can modify the source checkouts and local historical archives that its ACLs permit; hash checks do not make those files immutable. Timeout supervision applies to the direct child; log limits are soft and can overshoot between polls. Local decision records and receipt hashes provide no cryptographic authorship or external archival attestation. The Owner must accept or refuse these limitations for this exact case.

The current task authorizes preparation and synthetic checks only. W1/W2 remain `PREPARED_NOT_AUTHORIZED`. WP12 and WP13 remain `OPEN`.
