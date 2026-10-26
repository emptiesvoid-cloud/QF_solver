# FEM-TET4-H-001 — bounded refinement characterization

**Status:** `EXECUTION_RECORDED`<br>
**Numerical execution:** `PERFORMED_AS_BOUNDED_CHARACTERIZATION`<br>
**WP12:** `OPEN`

## Corrected mesh inventory

The fixed study uses base cells `(2,1,1)`, refinement factors `(1,2,4)`, six TET4 per cell, and tributary load distribution. The source formula is `6 * nx * ny * nz`. Therefore the mesh counts are **12 / 96 / 768** elements. The earlier table in [`FIRST_CAMPAIGN_EXECUTION_PLAN.md`](../FIRST_CAMPAIGN_EXECUTION_PLAN.md) listed 24 / 192 / 1536 for those same factors; that is inconsistent with the generator and is not reused here. This new plan does not rewrite the historical page.

| Level | Factor | Cells `(nx,ny,nz)` | TET4 | Nodes | Translational DOF |
|---|---:|---:|---:|---:|---:|
| H1 | 1 | `(2,1,1)` | 12 | 12 | 36 |
| H2 | 2 | `(4,2,2)` | 96 | 45 | 135 |
| H3 | 4 | `(8,4,4)` | 768 | 225 | 675 |

## Model and output

The fixed wrapper calls `solveur.verification.tet4_structured_convergence.run_structured_tet4_study` with `length=4.0`, `width=height=0.4`, `E=70e9`, `nu=0.3`, total global-Z load `-1.0`, matrix-free backend, chunk size 8192, and maximum 10,000 CG iterations. It uses no default larger mesh and no PETSc/MPI path. The generator fixes all three translational DOFs on `x=0` and distributes the load over the `x=L` face using tributary weights. The observable is mean tip-face `UZ`.

The Owner-approved run produced three model HDF5 files plus the utility's `summary.json`/`report.md`, the wrapper's `results.csv`, and a numeric marker in the runner receipt; raw artifacts remain in the external evidence archive. The [execution report](WP12_S_EXECUTION_REPORT.md) records measured values and receipt hash. Time and operator memory are captured as reported by the utility; `operator_memory_bytes` is an estimate, not a measured process peak.

## Reference and criteria

The built-in reference is Euler–Bernoulli bending plus Timoshenko shear using `A=width*height`, `I=width*height^3/12`, `G=E/[2(1+nu)]`, and `kappa=5/6`. It is a one-dimensional beam diagnostic, not an exact solution of this three-dimensional continuum model. A deviation from this reference, a mesh-to-mesh change, and an error against independent 3-D elasticity data are distinct quantities.

The utility defaults `relative_limit=0.01` and `residual_limit=1e-8` are passed explicitly to preserve its configured execution behavior, but they are **not** WP12-S scientific acceptance thresholds. The wrapper does not assert the helper's `PASS` status. For the proposed characterization-only scope, the data-completeness checks are: all three expected mesh sizes are present; displacement and residual values are finite; per-level solver values and timings are retained. No monotonicity, asymptotic order, beam-reference error limit, or 3-D validation pass is claimed. Any stricter convergence criterion needs a separate Owner-approved reference and threshold before execution.

The utility calculates observed orders from error relative to the beam formula and requires positive errors to do so. Such values, if returned, are descriptive only; they are not called formal h-convergence order without evidence of the asymptotic regime and a suitable reference. The utility's unconditional `stable_candidate` maturity metadata is not adopted as a WP12-S verdict.

## Cost and risk

The 675-DOF top level is the bounded local candidate, but actual runtime and memory are unknown until executed. Local resource handling provides only direct-child timeout and soft log-size polling: no hard CPU/RAM/disk quota, filesystem sandbox, or guaranteed process-tree termination. The proposed 1,800-second timeout and 16-MiB per-stream cap require Owner acceptance. Stop on any unexpected mesh inventory, backend substitution, incomplete output, non-finite value, timeout, or provenance mismatch and preserve the partial attempt.

The three levels recorded finite outputs, but the helper diagnostic returned `WARNING` because the provisional 1% beam-reference difference was not met. This is not an approved WP12 acceptance threshold. The levels do not demonstrate an asymptotic regime and provide no independent 3-D reference or external solver correlation. Historical large TET4 campaigns in [`docs/verification/tet4_structured_convergence_campaign.md`](../../../../docs/verification/tet4_structured_convergence_campaign.md) are contextual evidence only and do not supply results for this bounded study.
