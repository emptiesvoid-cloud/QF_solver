# WP14 G03 R4.7 — pre-merge public-surface requalification

**Result:** `PASS_BOUNDED_PUBLIC_SURFACES` and `PASS_CANDIDATE_PACKAGE_ONLY`
for the selected surfaces below. This record is prepared for Owner review. It
does not close WP14, waive the historical whole-repository findings, approve a
release, or authorize publication.

## Frozen source

- PR: [#7 — Prepare v0.2.9 source integration without release tag](https://github.com/emptiesvoid-cloud/QF_solver/pull/7)
- Audited source SHA: `5bdd6bec378b7c5cea75351e6a193553eaa075ec`
- Contract and execution commit: `8c5edcb16461927b5a184228dc0889f62040d344`
- Contract: [R4.7 frozen public-surface contract](../wp14_g03_bounded_public_surfaces_r4_7_contract.json)
- Contract SHA-256: `563c04f5653012ffd7c320541e9bd2f0d60fcf2cf2c0f9bca05b5bb70b786bad`

The source commit corrects the published `0.2.8` versus development-candidate
`0.2.9` wording in five selected public documentation files and adds a
documentation regression test. R4.6 remains valid only for its earlier source
SHA. The R4.7 contract was committed prospectively after the corrected source;
the selected source inputs remained unchanged during execution.

## Results

- Selected package-source scan: **551 files, 0 findings**.
- Strict scan of selected tracked documentation: **745 files, 0 findings**.
- The controlled `docs/verification/0_2_9/` archive remains tracked; **208
  files** are excluded from public MkDocs output and this bounded scan. G06
  review metadata remains an independent gate.
- Candidate wheel and sdist scans: **551** and **559** files, respectively,
  both with **0 findings**. Source-to-package mapping verified all selected
  package inputs.
- Installed-package probes passed both inside and outside the checkout:
  **473 installed QF source files** verified; `--version` and `--help` exited
  successfully and reported package version `0.2.9`.
- The installed `verify-all` probe returned the documented unsupported result
  for a developer-only command requiring a complete Git checkout. It is not
  interpreted as an installed-package failure.
- Wheel candidate: **1,510,095 bytes**, SHA-256
  `281ab23f4bd2e5fffb19eef081dab61da4417f5e9ed4fd65479e6eea935c2b88`.
- Sdist candidate: **1,138,360 bytes**, SHA-256
  `119eb65dd75da06bf2db3422eb1ce952c6b2eb47d47244c32a7da55657839311`.

## Governance and limits

- WP14 remains **HOLD, 0/1** and the consolidated validated total remains
  **95/100**. No ledger or maturity status was changed.
- Current-PR CI at the eventual evidence commit and the Owner's integrated
  review decision remain separate. This G03 result does not grant G08 or G09.
- No numerical solve, tag, merge, release, or publication was performed by
  this audit. The wheel and sdist were temporary candidate artifacts.
- The scan is limited to the frozen selected package sources and public
  documentation text/PDF suffixes. It does not inspect the entire repository,
  `scripts/`, `tests/`, the rest of `qualification/`, Git history, image
  pixels, binary meshes/data, or rendered layout.
- Raw build logs, transient binaries, virtual environments, and workstation
  paths are not committed. Probe paths below are normalized to
  `<local-temp>`; status and installed-source verification are preserved.
- The archived scan JSON has LF line endings for the byte-exact Git evidence;
  its structured findings and provenance are unchanged from the external run.

## Archived evidence

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| `public-scope-scan.json` | 387,121 | `f117633365f0e95eba3932acb9f373b51c7955044461634e45a6fbd758303d78` |
| `package_candidate/package_check.json` | 713 | `0c49a745aa8549368afb36d7942111aa97bf10ea44dfb0a57eed9e2f50ee1d74` |
| `package_candidate/source_mapping.json` | 136,105 | `8c3675dfa0eb5235b511f4f5ef0978562d8febb5257ee0b8296e2322d4949a0c` |
| `package_candidate/inside_checkout_probe.json` | 6,146 | `8cc3f4dc55d734cd18960cbcb94a6108f009d12f1020e2da26f292b54fcd6ea2` |
| `package_candidate/outside_checkout_probe.json` | 6,170 | `a108ea85d4b4080129a5db9541216be0537b369c9449b4bb9ddd0f555a7c2db2` |
