# WP-E01-AF — Isolated runtime remediation report

Date: 2026-10-22
Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
Branch: `codex/wp-e01-x-newton-test-remediation-20261021`

## Result

AF prepared a source-pinned Windows Sandbox layout and an offline Python runtime. The worker and supervisor derive paths from the authorized guest root, and the collection guard now validates the external control manifest and frozen source/runtime inventories. Newton configuration remains at the AB reference: **30 Newton iterations, 15 line-search trials, 14 reductions**.

Static source and manifest checks passed, and a separate read-only reviewer confirmed the snapshot identity and reviewed the path and collection-guard changes. Runtime properties remain unverified. In particular, host ACLs still grant `Authenticated Users` `Modify` on the source snapshot, runtime, control and output directories; guest read-only mounts do not prevent a host-side mutation. The profile stays **PREPARED_NOT_EXECUTABLE** pending a separately authorized non-scientific isolation check and resolution of this host-side mutation path.

No pytest, scientific FEM calculation, worker, supervisor, VM or Windows Sandbox was launched. COLLECT, RUN and native FEM remain NOT_RUN.

## Baseline and preserved evidence

The implementation started at `fce6b93969d94a8e963a432eec130a34de80883d` (tree `0893d08036471e286e26af9afa0a7feb5f4ee9a1`). The source/profile implementation was committed as `c2c77374a6e8237a1123d34606b6ea171568603c`, tree `6917fa2a6279338490dd12daa442b762c58640b2`.

Historical AB/AC/AD/AE reports and evidence were preserved. AB remains 16 PASS / 1 FAIL at the no-FEM execution guard, and AC/AD/AE remain static or simulated preparation evidence. The AA synthetic Newton result remains historical evidence only. This report does not promote or rerun any of those results.

The source snapshot is frozen to the implementation commit above. This report is a documentation-only commit after that freeze, so the final repository HEAD/tree will differ from the guest source snapshot identity by the report artifact only.

## Changes in the implementation commit

Eight tracked files changed:

* `experiments/wp_e01ad_collection_guard.py`
* `experiments/wp_e01ad_execution_contract.py`
* `experiments/wp_e01ad_physical_fem_supervisor.py`
* `experiments/wp_e01ad_physical_fem_worker.py`
* `qualification/0_2_12/wp_e01_ad_profile.json`
* `qualification/0_2_12/wp_e01_ad_runtime_manifest.template.json`
* `qualification/0_2_12/wp_e01_ae_isolation_profile.json`
* `qualification/0_2_12/wp_e01_ae_windows_sandbox.wsb`

No constitutive/mechanical formulation, scientific test, tolerance, Armijo criterion or Newton route was changed. The collection guard’s stale host-path/manifest assumptions were replaced with the guest mount layout, external control-manifest validation, source/runtime inventory verification, exact NUMERICAL_UNIT registry validation and the fixed node allowlist. Worker/supervisor paths are derived from their location under the guest source root rather than from a developer-specific absolute path. The worker verifies authorization and pinned identities before importing scientific modules.

The template is deliberately `runnable: false`, with no active Owner GO or operation manifest. The execution contract’s isolation provider remains unavailable by default. Its policy self-check enables a simulated provider only within the in-memory test path and restores the default afterward; this does not establish OS isolation.

## Host and guest layout

| Host path | Guest path | Access configured in `.wsb` |
|---|---|---|
| `C:\wpc01-frictionless-public-integration-wt\wp-e01-ae-source-snapshot` | `C:\e01\source` | Read-only |
| `C:\wpc01-frictionless-public-integration-wt\wp-e01-ae-runtime` | `C:\e01\runtime` | Read-only |
| `C:\wpc01-frictionless-public-integration-wt\wp-e01-ae-control` | `C:\e01\control` | Read-only |
| `C:\wpc01-frictionless-public-integration-wt\wp-e01-ae-output` | `C:\e01\output` | Read/write; worker policy allows only `output/wp_e01_ad_execution` |
| Windows system directory | `C:\Windows\System32` | Read-only system dependency root |

The guest profile uses these roots; no development-machine absolute path is required by the scientific worker. The Sandbox configuration disables networking, clipboard, audio/video input, printer redirection and vGPU, enables Protected Client, and does not configure an automatic logon command. The 2 GiB Sandbox VM allocation is a separate host from the guest Job Object caps; it is not a claim that the guest process receives 2 GiB.

### Effective ACL observation and limitation

Read-only `Get-Acl` inspection found inherited entries on all four mapped host folders: Administrators and SYSTEM Full Control; Builtin Users Read/Execute; and `NT AUTHORITY\Authenticated Users` Modify (plus an inherited system entry). No ACL was changed in AF. This is a material host-side mutation/TOCTOU concern for the source, runtime and control inputs and an evidence-integrity concern for output. A guest read-only mapping constrains writes from the guest but does not constrain a host process that has Modify permission. Resolve this before a runtime-isolation GO by applying and verifying appropriately narrow host ACLs or an equivalent immutable staging mechanism. The actual guest-visible ACL behavior is unverified.

The sandbox template has no personal-folder mapping. This is a configured mount policy, not a demonstrated system-wide denial of host resources. Network isolation, account identity, share behavior, host/guest access boundaries and cleanup require runtime verification.

## Runtime closure

The staged offline runtime lock identifies CPython **3.13.1**, NumPy **2.2.6**, SciPy **1.15.2**, Matplotlib **3.10.3**, pytest **8.4.1**, and 12 additional pinned transitive distributions (17 total). It records **8,937 files / 330,288,739 bytes**. Its `python313._pth` disables site initialization, user-site and `.pth` processing, and uses only the staged runtime and explicitly listed guest source paths. No package installation or download occurred in AF; the isolated runtime interpreter itself was not launched. Exact binary/import compatibility is therefore not runtime verified.

The frozen source snapshot is an offline archive of the implementation commit, with no `.git` metadata and no manifest self-inclusion. It contains **7,997 files / 939,311,651 bytes**. Its control manifest binds origin, branch, HEAD and tree and hashes every file. Static verification matched all 204 profile source pins. The full archive is broader than the minimal import closure; it remains guest read-only. The reviewer found no executable/library/credential-like extensions in the snapshot and noted the additional review surface and hash/read cost.

The full source snapshot is checked by both supervisor and worker. That duplicated hashing may exceed the 120-second phase deadline on some storage; no runtime timing is claimed. Keep the existing limit until measured under a non-scientific, separately authorized isolation check.

## Supervisor resource contract

The source profile keeps the AD values unchanged:

* 256 MiB per-process committed-memory cap.
* 256 MiB Job committed-memory cap.
* 120-second parent wall deadline.
* 100 seconds cumulative user CPU time for the Job; this is a cumulative cap, not a CPU-rate quota.
* One active process, no breakaway, kill-on-close, assignment while suspended before resume, and no retries.

These are statically inspected settings and readback requirements, not observed enforcement. The supervisor is not run in AF, so Job Object assignment, limit readback, timeout termination, accounting and cleanup remain unverified. The Python process policy is not a substitute for network or filesystem isolation.

## Newton parity

The frozen profile retains 30 Newton iterations, 15 line-search trials and 14 maximum reductions. The AB physical input, material, boundary conditions, load and solver tolerances remain represented by the unchanged pinned scenario fields. No Newton or Armijo method, test or tolerance changed in AF. Static comparison confirms the requested iteration/backtracking counts; runtime behavior is not revalidated.

## Static checks performed

* Parsed and compiled the four changed Python modules with the host Python built-in AST/compiler APIs, without importing solver modules: PASS.
* Parsed three JSON configuration files and the `.wsb` XML: PASS.
* Checked the profile’s 204 SHA-256 source pins against the checkout: 204 match, 0 mismatch.
* Validated the staged runtime lock and closed inventory: PASS, 8,937 files / 330,288,739 bytes.
* Generated and validated the source snapshot inventory against the 204 pinned sources: PASS, 7,997 files / 939,311,651 bytes.
* Ran the pure in-memory policy self-check: 53 simulated decisions (5 accepted-path cases and 48 rejection cases); PASS. It did not launch any process, solver or test runner.
* `git diff --check`: PASS before the implementation commit; it will be repeated for this report commit.
* Ruff: 9 findings remain, each confirmed in the corresponding baseline file at HEAD before the AF changes; one previously present unused-name finding was removed. No new Ruff finding was introduced. No unrelated cleanup was included.

These are static and simulated checks. They do not establish Sandbox runtime behavior, ACL enforcement, resource enforcement or scientific FEM behavior.

## Independent read-only review

The separate reviewer confirmed the source snapshot manifest hash, repository HEAD/tree, file count and byte count; confirmed no `.git` metadata or self-included manifest; and reviewed the current guard/path changes. Findings:

* **P0:** none.
* **P1:** runtime readiness remains blocked on verified host/guest ACL and mount behavior, restricted account/network isolation, Job Object readback and cleanup. Guest read-only mapping alone does not prevent host-side mutation/TOCTOU. This is retained as a runtime blocker, not declared resolved.
* **P2:** the 7,997-file snapshot is broader than needed, and verification is repeated in supervisor and worker. Runtime time under the 120-second cap remains unmeasured.
* The prior path mapping discrepancy and Newton iteration-count mismatch are resolved in the static configuration reviewed. The reviewer did not run any code, test, supervisor, worker, FEM or Sandbox.

## Hashes

All digests are SHA-256 of the file bytes.

| Artifact | SHA-256 |
|---|---|
| `experiments/wp_e01ad_collection_guard.py` | `3d45ac4116ae70578bee9a945fed818d367befd23ca0361f12f1e6efc3ed5d37` |
| `experiments/wp_e01ad_execution_contract.py` | `6cd0310938628405d9efb4d9eba4b4f08d5415ec9559f2f23574e801699214c1` |
| `experiments/wp_e01ad_physical_fem_supervisor.py` | `1bd0f41503d0fb66f502861b801093dbcf510cc8ae24987577aabe09142f4c73` |
| `experiments/wp_e01ad_physical_fem_worker.py` | `1a3a6f07e75e160f797e499a6794b9ac6e233cf6464e1fe0c13f9566e40d5138` |
| `qualification/0_2_12/wp_e01_ad_profile.json` | `7682bcd4d23263350210737ca76b2f17372d398ecd41c452060034af6952db2f` |
| `qualification/0_2_12/wp_e01_ad_runtime_manifest.template.json` | `d93cf698df9f71451329b8201a27931d28a1a1c9959d70aa66098fe34f2386bb` |
| `qualification/0_2_12/wp_e01_ae_isolation_profile.json` | `cff08878dcfd72d9d82bd59491509c1b8f0496ee4fa740bcb4eac789edaed690` |
| `qualification/0_2_12/wp_e01_ae_windows_sandbox.wsb` | `0f79b581a33425e734ea44b121d729c0bd2aa684d082ab63e1cfcd9264840f36` |
| External `runtime-lock.json` | `aeaa17d26632929a608c30f252c5d32654acece5ecefe2bcd1f9f472ee8bf700` |
| External `source_snapshot_manifest.json` | `a44a070b412887b2a6569ceb1bb585bb47b05ce4a355ed4c50c8e06fc9a3ef0f` |

## Future validation sequence

The next authorization should be a **non-scientific isolation-runtime validation**, not COLLECT or RUN. Before it:

1. Resolve host-side ACL/immutability and evidence-write permissions; record the intended account and verify read-only input mounts and the dedicated output mount from inside Sandbox.
2. Create a trusted host-side preflight that verifies the frozen source HEAD/tree, the manifest and all source/runtime hashes before Sandbox starts; close the host-mutation window for the duration of validation.
3. Verify network denial, no personal-folder mappings, guest account identity, process creation limits, Job Object assignment/readback, commit/CPU/wall limits, timeout termination, kill-on-close and cleanup using a non-scientific sentinel only.
4. Measure the repeated 939 MB snapshot verification cost against the existing 120-second wall limit; do not raise limits without a separate justification and Owner authorization.
5. Only after those checks and a favorable independent review, prepare a fresh inactive operation manifest. A later Owner GO-COLLECT must bind exact HEAD/tree, profile, runtime lock, source snapshot, registry, test node and a new collection receipt. GO-RUN remains separate and must require the accepted receipt and its own authorization.

No active operation manifest was generated by AF. No GO-COLLECT or GO-RUN is implied.

## Final classifications

* `WP_E01_PHYSICAL_EXECUTION_INFRASTRUCTURE=STATICALLY_REVIEWED`
* `WP_E01_ISOLATION_RUNTIME=NOT_VERIFIED`
* `WP_E01_PHYSICAL_EXECUTION_PROFILE=PREPARED_NOT_EXECUTABLE`
* `COLLECT=NOT_RUN`
* `RUN=NOT_RUN`
* `NATIVE_FEM_VNV=NOT_RUN`
* `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`
* `INCREMENTAL_NEWTON=VERIFIED_BOUNDED` (historical synthetic evidence only)
* `SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`
* `AUTHORITATIVE_INTEGRATION=PENDING`
* `PUBLIC_RELEASE=NOT_AUTHORIZED`
