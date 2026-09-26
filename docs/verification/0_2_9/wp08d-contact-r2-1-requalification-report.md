# WP08-D contact requalification R2.1 — execution report

## Verdict

`HOLD_FAIL_CLOSED_REFINEMENT_DEFINITION_AND_EVIDENCE_LIMITATIONS`

The frozen campaign completed all authorized production cases, independent observable recomputations, and the required M1 replay. The solver cases converged and the independent references agree closely. However, the observed M2→M3 contact-resultant and dissipation deltas exceed the recorded limits when normalized by the larger observed magnitude. The parent contract does not specify the `scale_floor` value in its delta formula, nor numerical definitions for the two contact-region measures. The campaign runner's `PASS_CANDIDATE` is therefore not a WP08-D qualification verdict: its final predicate did not evaluate the parent refinement gates.

No WP08-D points are awarded; WP08-E, ledger changes, merge, and push remain unauthorized and were not performed.

## Provenance

| Item | Value |
|---|---|
| Branch | `codex/wp08d-contact-r2-requalification` |
| Execution / frozen source SHA | `dda753f5cc61925f776e3a9486a84dc448aac7be` |
| Parent governing baseline | `cd69958909aabcd74649b92fde768a1a0422ed52` |
| Contact change commit | `23de731e51e87a61831a23f97fea119f52846352` |
| R2.1 contract SHA-256 | `a9b82f19f1fc0dc27ac2ed97320a06e958c4adb4f96b4510bbf35c494316519d` |
| Parent WP08-D contract digest | `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a` |
| Policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Owner decision SHA-256 | `33f84096335b4badaf3a813e9041f3f3356b32973ed80d12a92a1f1afb547a7e` |
| Exact-source authorization SHA-256 | `9a656d25ca3cdf131a3aa2c082f323cca147a83df5fc70b3271f157f51de315a` |
| Run summary SHA-256 | `dc86efcbd9e7dd105af0082e98e89206e4d6a3f5ab4ef81dec6946200b96ecec` |
| Raw output directory | `qualification/0_2_9/wp08d_contact_requalification_r2_runs/raw_r2_attempt_02/` (local, Git-ignored) |

The earlier R2 attempt remains intact under `raw_r2/`; all three children exited 2 before solver import, with no `result.json` or `raw.npz`. R2.1 used a distinct empty output directory and the exact authorization above. No production source changed after the execution SHA. No campaign process remains active.

The authorized contact source change is present in the execution lineage at `23de731e…`; it modifies `src/solveur/contact/slip_root.py`. R2.1 adds no further production-mechanics change; its delta is runner/authorization/evidence isolation only. Do not describe the full governing-base diff as mechanics-unchanged.

## Campaign results

Each mesh completed 7/7 load increments. No fallback event was found in telemetry. Production results and independent references are `PASS`; the required M1 replay is `PASS`. I separately compared every replay-required observable: full displacement, reaction vector and moment, normal/tangential contact resultants, active count and qualitative state, dissipation, terminal status, load history, and exact `raw.npz` load-factor/state-digest arrays; all compared fields match. The independent implementation is a NumPy/KKT reference/recomputation, not a second global FEM/Newton solve.

| Mesh | Nodes / elements / DOFs | Contact states at final increment | Selected displacement | Normal contact resultant norm | Tangential contact resultant | Dissipation | Force / moment balance |
|---|---:|---|---:|---:|---|---:|---:|
| M1 | 16 / 12 / 48 | 4 open, 0 stick, 0 slip | 0.01703907169 | 0 | `[0, 0, 0]` | 0 | `4.81e-15 / 7.81e-15` |
| M2 | 49 / 96 / 147 | 9 open, 0 stick, 3 slip | 0.02038785849 | 159.2685802 | `[-45.45507612, 14.52017484, 0]` | 0.1380965064 | `2.57e-14 / 4.50e-14` |
| M3 | 229 / 768 / 687 | 35 open, 0 stick, 5 slip | 0.02074871057 | 236.3681471 | `[-70.52941901, 7.34007721, 0]` | 0.1219224730 | `1.49e-13 / 2.15e-13` |

The M1/M2/M3 engineering `run_verdict` is `WARNING` because frictional contact maturity is classified `experimental`. The terminal classification remains `PASS`; the warning is preserved, not relabeled.

## Frozen M2→M3 refinement gates

The ratios below use `abs(M3-M2)/max(abs(M3),abs(M2))` (Euclidean norms for vectors), i.e. the recorded definition without an additional floor. The parent contract names `scale_floor` but does not freeze its value, so these are transparent observed deltas, not a fully specified normalized-gate evaluation. The large contact/dissipation differences are not relabeled as PASS; a future contract must freeze the normalization before another qualification run.

| Observable | Observed delta | Frozen maximum | Result |
|---|---:|---:|---|
| Selected displacement | 1.73915% | 3% | PASS |
| Reaction resultant | 1.26e-11% | 2% | PASS |
| Reaction moment | 0.04955% | 3% | PASS |
| Normal contact resultant | 32.61843% | 3% | **FAIL** |
| Tangential contact resultant | 36.78182% | 3% | **FAIL** |
| Cumulative dissipation | 11.71212% | 5% | **FAIL** |
| Active contact region measure | Not emitted / no frozen measure formula | 10% | **FAIL_CLOSED — missing** |
| Stick/slip region measure | Not emitted / no frozen measure formula | 10% | **FAIL_CLOSED — missing** |

As descriptive counts only, the active fraction changes from 3/12 (25%) in M2 to 5/40 (12.5%) in M3; all active contacts are classified slip and none stick. These count fractions are **not** substituted for the contracted physical region measures. The large contact-force and dissipation deltas indicate that contact response is not mesh-converged under the frozen limits, despite close displacement/reaction convergence and excellent equilibrium.

## Evidence integrity and tooling findings

The campaign process audit records seven sequential processes, each with exit code 0: primary M1/M2/M3, independent references M1/M2/M3, then replay M1. The outer process manifests' stdout/stderr hashes match their final logs. The runner's `replay_comparison()` checks only a subset of the parent-required fields; the complete replay comparison above was independently performed for this audit, so the runner's PASS alone would not establish the full replay gate.

All 89 file entries in the seven case manifests were rechecked. 86 match their recorded size and SHA-256. Three discrepancies are confined to `runner.stdout.log` in the M1/M2/M3 independent-reference manifests: each inner manifest recorded the empty log before the parent process wrapper appended its one-line PASS output. In every case, the final log's size/hash matches the separate execution `process.json` stdout digest. The raw logs and manifests were left unchanged. This is a manifest-timing defect, not a numerical-result mismatch, but it remains an evidence-tooling limitation and the old manifests must not be represented as fully hash-clean.

The source patch adds a bounded seed-first coupled contact-projection recovery route. The present M2/M3 telemetry records `active_slip_root`; no `coupled_contact_candidate_*` event appears. Thus these runs do not demonstrate that the newly added recovery branch was exercised. M1 has only the open-contact/direct path.

The runner summary says `PASS_CANDIDATE` because it checks per-case terminal/reference/replay status but omits the parent M2→M3 gates. Its raw summary is preserved unchanged; this report supplies the separate gate adjudication.

## Verification and disposition

- Targeted WP08 tests: `90 passed`.
- Ruff: PASS; targeted mypy: PASS; compileall: PASS; JSON validation: PASS; `git diff --check`: PASS.
- Full repository suite: not run.
- Thresholds, loads, mesh, material, tolerances, backend, and fallback policy: unchanged.
- WP08-E: not run. Official WP08-D points: unchanged at `0/2`; WP08 total unchanged.
- No ledger update, merge, push, or release.

Next step: preserve this run as evidence of converged bounded solves with unresolved/over-limit contact refinement. Before any new structural execution, freeze the scale floor and physical active/stick/slip region measures prospectively, fix the reference-manifest log timing and incomplete replay comparator in tooling, and prepare a new frozen execution contract if the contact method or mesh is to change. Do not relax the current thresholds or overwrite this run.
