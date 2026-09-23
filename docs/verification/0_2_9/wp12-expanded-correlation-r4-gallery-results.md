# WP12 R4 — extended model-gallery Code_Aster correlation

Status: **PASS_WITH_LIMITATIONS**

Independent raw-evidence audit: **PASS_WITH_LIMITATIONS** — 864/864 cases.

## Coverage

The campaign adds 864 fresh solver-correlation cases to the 144 verified R3.6 cases, for 1008 cumulative case comparisons.

| Dimension | Coverage |
|---|---:|
| New cross-section topologies | 6 |
| Material parameter sets | 3 |
| Element families | 4 |
| Mesh levels per topology | 3, longitudinal-only H1/H2/H3 |
| Load cases per model/mesh | 4 |
| Fresh Code_Aster comparisons | 864/864 |

### Cases by topology

| Topology | Cases | PASS | FAIL/HOLD |
|---|---:|---:|---:|
| box_tube_beam | 144 | 144 | 0 |
| channel_section_beam | 144 | 144 | 0 |
| cruciform_beam | 144 | 144 | 0 |
| i_section_beam | 144 | 144 | 0 |
| tee_section_beam | 144 | 144 | 0 |
| triangular_prism | 144 | 144 | 0 |

### Cases by material

| Material | Cases | PASS | FAIL/HOLD |
|---|---:|---:|---:|
| aluminum | 288 | 288 | 0 |
| polymer | 288 | 288 | 0 |
| steel | 288 | 288 | 0 |

### Largest independently recomputed metrics

| Metric | Maximum | Frozen gate |
|---|---:|---:|
| displacement_relative_l2 | `6.200221e-12` | `1e-08` |
| displacement_relative_linf | `7.434304e-12` | `1e-08` |
| reaction_relative_l2 | `6.916131e-12` | `1e-08` |
| reaction_relative_linf | `8.002877e-12` | `1e-08` |
| strain_energy_from_external_work_relative | `6.048079e-12` | `1e-08` |
| qf_free_residual_relative_l2 | `8.548752e-13` | `1e-08` |
| qf_force_equilibrium_relative | `2.931393e-12` | `1e-08` |
| aster_force_equilibrium_relative | `4.583792e-15` | `1e-08` |
| qf_moment_equilibrium_relative | `2.458750e-12` | `1e-08` |
| aster_moment_equilibrium_relative | `2.764222e-15` | `1e-08` |
| fixed_displacement_abs_max | `1.566992e-20` | `1e-12` |

## Execution and provenance

- Branch: `codex/wp12-expanded-correlation-r4`
- Execution SHA: `c3c52449eb41e9b5a79e98f35b4bdb5591ba6980`
- Contract SHA-256: `7588d0962776e02fe4ffba83ccc1611afbb5d606bd502c51d8f544954bc48ef2`
- Manifest SHA-256: `02b4c6a799835dd6908a2ea297d11ad86d27e22947fdb778ab44af7403a9980d` (14692 raw files)
- Independent audit SHA-256: `50ba73ec784452931b000ca750f4885c1eb63acb3510ffb4d8296b7e0db0a8c5`
- Code_Aster: 18.1.0 in the pinned image; fresh container per case; sequential, one CPU, MPI disabled.
- Execution window: 2026-09-23T17:25:33.486112+00:00 to 2026-09-23T19:48:34.959936+00:00.
- The first audit attempt failed closed because the inherited checker expected `wp12_expanded_summary.json`, while the R4 runner emitted `wp12_gallery_r4_raw_summary.json`. A byte-identical compatibility alias was added (same SHA-256: `a4bfc5df...898562a`), and the manifest was regenerated. All 14,691 pre-existing manifest entries retained identical hashes; only the alias was added. The initial failed audit is preserved separately with SHA-256 `fb37db9f...da9a3`.
- Final audit: `PASS_WITH_LIMITATIONS`, 864/864, zero errors; its SHA-256 is recorded above and at the contract-designated audit path.
- The 243 MB raw case directory remains local and is excluded by a specific `.gitignore` rule. The generated manifest, audit records, compact summary and report are not yet committed; no push or merge was made.

## Interpretation and limitations

This is same-discrete-mesh solver correlation: both solvers receive the same coordinates, connectivity, material, fixed root plane and equivalent nodal loads. It is not experimental validation, an independent physical benchmark, or a mesh-convergence proof. The three mesh levels refine only the longitudinal direction. No stress-field, nonlinear, contact, dynamics, buckling, or MPI/scaling claim is made. The campaign is supplemental and does not change WP12 official points or the global ledger.

## Validation

- Targeted tests: 196 passed
- Compileall: PASS
- Ruff: PASS
- Mypy: PASS
- Full repository test suite: not run.

`OFFICIAL_POINTS_CHANGED = NO`

`GLOBAL_LEDGER_CHANGED = NO`

`PUSH = NO`

`MERGE = NO`
