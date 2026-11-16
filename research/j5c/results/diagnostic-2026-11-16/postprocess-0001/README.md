# J5C — independent modal post-processing

Status: **DIAGNOSTIC_ONLY**. This post-processing does not change the J5B
campaign or any modal validation verdict.

## Provenance

The inputs are byte-exact copies from J5B attempt `j5b-6bb4e32988af`
at source commit `dc1315693715eb7322bd7e4647c2e36e635d4b0d`. Hashes are recorded
in `independent_check.json` and `artifact_manifest.json`. The J5B campaign status
remains `INCONCLUSIVE`; all five modal candidates
remain `INCONCLUSIVE` with their archived reasons.

## Independent checks

- Recomputed `sqrt(eigenvalue)/(2π)` against the five archived frequency/vector
  checkpoints.
- Checked the structured square meshes, positive CCW quad areas, mid-surface,
  and total represented area.
- Reproduced the J5B **unweighted nodal UZ MAC** and repeated-pair subspace MAC.
- Compared QF UZ interpolated bilinearly inside each element to independent
  Reissner–Mindlin soft-support continuum Ritz modes using an area-weighted L2
  MAC. The repeated pair is compared by the minimum squared principal-angle
  cosine in that weighted space. This is not a mass MAC.
- Evaluated the Kirchhoff/Navier formula independently and built a separate
  soft-support Reissner–Mindlin Galerkin/Rayleigh–Ritz frequency sequence.

The first four frequencies from the largest Ritz basis are `48.197906, 120.605970, 120.605970, 192.606408 Hz`.
The basis uses `w=0` on all edges and free rotations (natural moment conditions),
translation mass `rho*h`, and rotary inertia `rho*h^3/12`. Rotation polynomials
and transverse sine harmonics were expanded in nested spaces; the maximum
problem dimension was 931 at a fixed
48-point Gauss rule per axis. This is a numerical reference estimate, not an
exact closed-form result. No formal acceptance threshold was set.

## Archived J5B candidates

| Mesh | QF candidate frequencies (11,12,21,22), Hz | Relative errors to thin Kirchhoff/Navier | Historical status / reason |
|---:|---|---|---|
| 4×4 | 51.88552, 159.66283, 159.66283, 259.94242 | 7.187%, 31.934%, 31.934%, 34.249% | INCONCLUSIVE / aggregate_work_budget |
| 6×6 | 49.88731, 135.73039, 135.73039, 219.23895 | 3.059%, 12.158%, 12.158%, 13.228% | INCONCLUSIVE / dimension_budget |
| 8×8 | 49.21227, 128.83899, 128.83899, 207.25411 | 1.664%, 6.464%, 6.464%, 7.038% | INCONCLUSIVE / dimension_budget |
| 12×12 | 48.73258, 124.28642, 124.28642, 199.26567 | 0.673%, 2.702%, 2.702%, 2.912% | INCONCLUSIVE / dimension_budget |
| 16×16 | 48.56050, 122.75220, 122.75220, 196.55556 | 0.318%, 1.434%, 1.434%, 1.513% | INCONCLUSIVE / dimension_budget |

`modal_comparison.csv` adds differences to the Mindlin Ritz frequencies and
quadrature-weighted mode-shape metrics. `ritz_convergence.csv` contains the
predeclared basis sweeps. The PNG files are normalized comparison figures;
mode amplitudes are not physical forced-response displacements.

## Limits

The archived payload does not contain the assembled stiffness or mass matrix.
Therefore this work did **not** recompute eigenpair residuals or mass
orthogonality. The literature table found during J5C uses hard simple-support
conditions; it is context only, because J5B uses soft support. The Ritz
quadrature order was fixed and not separately converged. The study does not
qualify the MITC4 modal route or the solver as a whole.

## Reproduction

From the J5C clean worktree, run the single predeclared node:

```powershell
python -m pytest tests/unit/test_j5c_modal_postprocess.py::test_j5c_archive_postprocess_and_ritz_reference -q
```

The test writes the artifacts listed in `artifact_manifest.json` below
`research/j5c/results/diagnostic-2026-11-16/postprocess-0001/`. Input hashes,
contract and source commit are frozen in `research/j5c/contracts/`.
