# NAFEMS 13H harmonic mesh study — prepared site assets

Status: prepared for review; **not published**. These files summarize the J16
MITC4 6×6, 8×8 and 10×10 runs. Every frequency row retains the QF route status.
Near-resonance amplitudes and deformed shapes are raw diagnostic outputs where
the unchanged residual guard rejected the point; they are not accepted QF
results or a formal correlation.

## Contents

- `mesh_comparison_summary.json` and `mesh_comparison_frequency_response.csv`:
  aggregate results, including all three meshes and per-frequency statuses.
- `mesh_comparison_amplitude_phase.png`: amplitude and phase with rejected
  points identified.
- `mesh_06/`, `mesh_08/`, `mesh_10/`: per-mesh response CSV and JSON, setup
  figure, and peak-shape figure. Each deformed plot states its amplification
  factor and diagnostic status.
- `artifact_manifest.json`: byte size and SHA-256 for all generated data and
  image files in this bundle (excluding this README).

## Provenance and reproduction

- Frozen mesh-study contract: `research/j16/contracts/nafems_13h_mesh_study_003.json`.
- FEM source commit: `82c361e750b3a0d7bd26b22743d0a5fc240a41e3`.
- Asset aggregation contract: `research/j16/contracts/nafems_13h_mesh_site_assets_004.json`.
- Asset aggregation source commit: `cc584c4b8c016a1e4a5d89e339a87893b0264b09`.
- Mesh outputs were made by the registered development-autonomous runner, one
  exact test node per mesh, with one attempt each. The frozen contract and
  repository test/helper sources define inputs, frequency grid, observables,
  limits and output checks. The archived runner receipts remain in the local
  ignored execution area because they contain workstation paths.
- The assets were assembled from the archived per-frequency checkpoints and
  runner receipts. Aggregation did not rerun the FEM solver.

The official NAFEMS 13H / Abaqus 2024 benchmark page and S4R input deck are
listed in `docs/planning/0.3.0-j16-resultats.md`. Abaqus was not run locally;
its published peak values are a comparison reference, not a locally reproduced
independent solve.

## Interpretation limits

The results document one plate geometry, one material/thickness, one pressure,
one support configuration, one damping model and three MITC4 meshes. All
near-peak QF response points are guard-rejected on 8×8 and 10×10; only the
low-frequency portion of 6×6 is accepted. The raw mesh trend is descriptive
and does not establish convergence or general qualification. The Navier
reference is a thin Kirchhoff–Love solution, while QF uses MITC4/
Reissner–Mindlin. No phase is published for the Abaqus direct-solution table.
