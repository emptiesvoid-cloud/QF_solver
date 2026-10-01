# WP14 G03 R4.6 — current-source bounded audit

**Result:** `PASS_BOUNDED_PUBLIC_SURFACES` and `PASS_CANDIDATE_PACKAGE_ONLY` for the scoped checks below. This is a bounded G03 result prepared for Owner review; it is **not** a WP14 closeout, whole-repository G03 pass, release approval, or publication authorization.

## Frozen source and execution

- PR: [#7 — Prepare v0.2.9 source integration without release tag](https://github.com/emptiesvoid-cloud/QF_solver/pull/7)
- Audited source SHA: `1d41202accf0a1645c4c6527ad2ed779aa51f264`
- Contract/execution commit: `3719f2dcf752308a3e30d2e579b3c848f9605baf`
- Contract: [`wp14_g03_bounded_public_surfaces_r4_6_contract.json`](../wp14_g03_bounded_public_surfaces_r4_6_contract.json)
- Contract SHA-256: `b4f7fad0739786287bc9f5f4bea6068e36d3a1b99abbe8ddede3b60a0eaffe8e`

The scan is bound to the PR source SHA. Its frozen package and documentation inputs matched that source; no input was missing and no threshold was changed.

## Results

- Selected package-source scan: 551 files, 0 findings.
- Strict scan of selected tracked documentation: 745 files, 0 findings.
- The controlled `docs/verification/0_2_9/` archive (208 files) remains in Git and is excluded from public documentation output and this bounded public-doc scan. The separate G06 gate is unchanged.
- Candidate wheel scan: 551 files, 0 findings. Candidate sdist scan: 559 files, 0 findings.
- Both installed-package probes passed; 473 installed QF source files were verified. `--version` and `--help` both returned exit code 0 and reported version `0.2.9`.
- The installed-package `verify-all` invocation returned its documented “developer/CI only” unsupported result because it requires a complete Git checkout. It is not treated as a package scan or install-probe failure.
- Wheel candidate: 1,510,095 bytes, SHA-256 `ea8faa4d2570300492d849fd83acdd0661289ca881b36f7382e422fba993cbdf`.
- Sdist candidate: 1,138,306 bytes, SHA-256 `db6d286763f2b7687b53fa0aa9435fb0f7cca773c00e5c598bd20c0915048a08`.

## Governance and limits

- WP14 remains `HOLD`, 0/1 validated points; official total remains 95/100. This record awards no points and does not edit the ledger.
- Historical whole-repository findings are retained; this bounded scan does not waive or reclassify them.
- No numerical solve, tag, release, or publication was performed or authorized by this audit. G06 review metadata and G08 CI evidence remain independent gates.
- The scan covers only the frozen selected package sources and tracked documentation text/PDF suffixes. It does not inspect `scripts/`, `tests/`, the rest of `qualification/`, repository history, image pixels, binary meshes/datasets, or rendered layout.
- The wheel and sdist were temporary audit candidates only. Their binaries, build environment, and raw command logs are not committed. Probe paths were normalized to `<local-temp>` to avoid publishing workstation-specific paths; status, installed-source verification, CLI results, and limitations are preserved.

## Archived evidence and hashes

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| `public-scope-scan.json` | 387,089 | `2e7f7fd73b30064d155e52ea4959fdba5b24c44a57be70bfd94e3ce113edc71c` |
| `package_candidate/package_check.json` | 713 | `a5fd33b4c355a20ba94235ad4e750c6ef66cbf6afed53e2bc3b476bf19b012c0` |
| `package_candidate/source_mapping.json` | 136,105 | `8c3675dfa0eb5235b511f4f5ef0978562d8febb5257ee0b8296e2322d4949a0c` |
| `package_candidate/inside_checkout_probe.json` (paths normalized) | 6,235 | `86b98571ce9d10aa2b84691f0dcff78555a29b9f2391032c6661c16d6efe9136` |
| `package_candidate/outside_checkout_probe.json` (paths normalized) | 6,260 | `20ed51e74e3ccf68d7a50aea5e4fee469dacf1280cd1bbaf9af7ade357ac1808` |
