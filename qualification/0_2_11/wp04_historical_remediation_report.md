# QF Solver 0.2.11 — WP04 selected historical remediation

**Status:** scoped retests and documentary corrections recorded; exact-candidate
CI is required before closing `QF0211-G03`.

**Base:** `33d83b2935a97ca7a74fef2c62d5e2310eb71ddc` on
`codex/v0.2.11-wp04-legacy-remediation`.

**Preservation:** `origin/main` remains at
`c37179dae53604126aa6aa0d834770dfa4d2db37`; immutable `v0.2.10` remains at
`e535ff63464ddd7d76c2898df25470350b5154f1`. No production numerical code,
formulation, tolerance, historical qualification record, result, or maturity
was changed. WP05 and gyro/QEP/Campbell work did not start.

## L01 — Current documentary authorities

The 0.2.10 V&V summary linked to the generic candidate contract, not the final
authorized e535ff selected-package contract. Its current-release text and
document-control label also still described a candidate. The summary now names
the immutable `v0.2.10` → `e535ff63464ddd7d76c2898df25470350b5154f1` package source,
links `qualification/0_2_10/authorized_selected_package_release_contract_e535ff.json`,
and distinguishes that governance record from the package source commit. It
retains the version DOI `10.5281/zenodo.23106744`, concept DOI
`10.5281/zenodo.22697897`, `G03 = FAIL_PRESERVED`, and
`WP14 = HOLD_NOT_PROMOTED`. No historical contract or historical claim was
rewritten.

## L02 — Current source-size rule

The developer guide said Python files “must” remain below 700 lines. Current
implementation/tests treat 700 lines as a maintainability objective: the audit
reports debt/warnings and does not fail the build solely on this count; the
Quality workflow has no 700-line hard gate. The guide now says so explicitly.
The 0.2.6/0.2.7 documents remain as historical descriptions of their then-current
guard. No numeric formulation or tolerance is involved in this policy.

## L03 — Short replays, not requalification

| Item | Historical status | Current replay | Root cause / bounded finding | Action | Promotion |
|---|---|---|---|---|---|
| MITC4 modal 10k QUAD4 | Historical QF timeout/no usable eigenpair; this does not fail every MITC4 modal route | `BLOCKED`: exact documented QF settings reached the unchanged 900 s limit; no usable eigenpair or `summary.json` | High-DOF `eigsh`/`spilu` route does not finish within the frozen time budget on this run. The historical record does not isolate a deeper solver defect. Code_Aster reference was not recomputed and its reference directory is absent from this clean checkout. | `RETEST_ONLY`; defer solver/preconditioner/formulation work and external correlation | None; historical scope remains open |
| Discrete Newmark | Owner gate `REJECTED`; route `EXPERIMENTAL` | `REPRODUCED`: owner-gate regression test passes while affirming coarse phase error `0.012895220110156203 rad > 0.012 rad`; fine grid is `0.0032254224099297346 rad` | Frozen coarse time grid crosses the frozen phase gate. The known record attributes no remedy and retains the gate/grid. | `RETEST_ONLY`; preserve record and exact gate | None; remains `EXPERIMENTAL` |
| Contact guards | Historical active-set cycle; targeted remediation was diagnostic, not general WP08 requalification | `PASS_TARGETED_GUARDS`: 24 selected unit tests pass | Frozen tangential mode could induce a normal active-set cycle; bounded coupled Coulomb projection recovers the selected case, while enumeration above eight operators fails closed. This says nothing about mesh sensitivity, finite sliding, dynamics, or general contact. | `RETEST_ONLY`; no broad campaign | None; WP07/WP08 dispositions unchanged |

The exact commands, test/policy file digests, environment and WP03 canonical
execution keys are in
[`wp04_retest_execution_records.json`](wp04_retest_execution_records.json).
The MITC4 mesh/deck generated during the bounded attempt is local-only and
content-hashed there; no result/eigenpair was fabricated from it.

## L04 — Evidence availability

[`wp04_evidence_inventory.json`](wp04_evidence_inventory.json) updates the
selected evidence inventory without moving or rewriting archived records. It
separates tracked historical summaries, reconstructed WP04-D bytes, raw data
that is missing from the clean checkout, optional Code_Aster/runtime payloads,
and CI-only evidence. A reproduced payload matching old size/hash expectations
is not relabeled as the original capture. Missing originals remain missing.

## Other historical open items retained

No blanket closure campaign was run. G03 remains `FAIL_PRESERVED`, the whole
repository archive is not cleared, WP14 remains on HOLD, WP06-D remains bounded
experimental with 0/2 formal points, WP06-E/F remain blocked on formal
dependencies, and WP08 R1.13 remains an experimental diagnostic with visible
mesh sensitivity. The bounded WP08 contact acceptance is not broadened.
WEDGE6 transient/harmonic, HEX8 SRI, HEX8 buckling experimental scope, MITC3
modal/dynamic promotion, WEDGE15, general HPC scaling, general checkpoint
compatibility, M2 moment limits, historical refinement failures, and full
archive cleanup remain unchanged/deferred. Details and authorities are listed
in `wp01_historical_open_items.md` and the evidence inventory.

## Candidate gate and checks

Local retest and documentary conditions are recorded in
[`wp04_historical_remediation_contract.json`](wp04_historical_remediation_contract.json).
Local architecture/source-size checks: `21 passed`, one advisory warning.
Newmark owner-gate replay: `1 passed, 4 deselected` (the test verifies the
historical rejection; it is not a numerical PASS). Contact guards: `24 passed`.
The MITC4 run was stopped at its frozen 900 s limit. Exact-WP04 Quality and
Documentation CI are still required; the WP03 comparison runs are Quality
`37269320218` and Documentation `37269320422`. No full campaign was relaunched
on `main`.

`QF0211-G03_SELECTED_HISTORICAL_FIXES_VERIFIED` is not closed until the exact
committed WP04 SHA passes its required CI with no new regression. A `BLOCKED`
or failing historical replay is compatible with this gate if recorded
accurately and not promoted.
