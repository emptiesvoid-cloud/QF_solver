# WP09 isotropic 3-D remesh study — diagnostic analysis

## Scope

This is a diagnostic study on branch `codex/wp09-remesh-study`. It does not
rebind the frozen WP09 formal contract, does not alter production mechanics,
and does not award qualification points. The load scale is 25% of the formal
unit reference load, with the same J2 material and corotational local-strain
limit of `0.05`.

Execution SHA: `1bc884e927fb2a7d554da53bc3953d5719bd4914`

The study uses an isotropic 3-D hierarchy for both families:

| Level | Subdivision | TET4 elements | HEX8 elements |
|---|---:|---:|---:|
| H1 | 1×1×1 | 5 | 1 |
| H2 | 2×2×2 | 40 | 8 |
| H3 | 4×4×4 | 320 | 64 |

All six meshes pass the mesh-quality preflight with zero quality errors and
zero quality warnings.

## Mesh size and solve status

| Family | Level | Nodes | Elements | DOFs | Mesh quality | Solve |
|---|---:|---:|---:|---:|---|---|
| TET4 | H1 | 8 | 5 | 24 | PASS | PASS |
| TET4 | H2 | 27 | 40 | 81 | PASS | FAIL_CLOSED |
| TET4 | H3 | 125 | 320 | 375 | PASS | FAIL_CLOSED |
| HEX8 | H1 | 8 | 1 | 24 | PASS | PASS |
| HEX8 | H2 | 27 | 8 | 81 | PASS | PASS |
| HEX8 | H3 | 125 | 64 | 375 | PASS | PASS |

The TET4 failures are numerical-contract failures, not mesh-quality failures:

- H2: `||U-I||F = 0.06063282 > 0.05`;
- H3: `||U-I||F = 0.06522889 > 0.05`.

## Successful results

| Family | Level | max displacement | reaction norm | energy | max von Mises | max local strain | min detF |
|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 | H1 | 2.338608e-02 | 2.500000e-01 | 1.567577e-03 | 3.009993e-01 | 3.472800e-02 | 9.995516e-01 |
| HEX8 | H1 | 1.065944e-03 | 2.500000e-01 | 1.412232e-04 | 2.909757e-02 | 1.401096e-03 | 9.998201e-01 |
| HEX8 | H2 | 7.400543e-03 | 2.500000e-01 | 6.530805e-04 | 8.347733e-02 | 1.223946e-02 | 9.987323e-01 |
| HEX8 | H3 | 1.509184e-02 | 2.500000e-01 | 1.364766e-03 | 2.082318e-01 | 2.875461e-02 | 9.979918e-01 |

HEX8 H2→H3 relative changes are:

- displacement: `50.9633%`;
- reaction norm: effectively zero (`3.73e-10` under the report's relative
  normalization);
- energy: `52.1471%`;
- maximum von Mises: `59.9114%`;
- maximum equivalent plastic strain: `57.4644%`.

Equilibrium and residual diagnostics remain small for the successful HEX8
runs. At H3, the free relative residual is `1.971e-09`, force balance is
`8.262e-11`, and moment balance is `5.838e-11`.

## Interpretation

The isotropic remesh does not establish formal WP09 qualification:

1. TET4 cannot traverse H2/H3 under the frozen local-strain bound at this
   load scale.
2. HEX8 is numerically admissible through H3, but its displacement, energy,
   and stress observables are not mesh-converged at H2→H3.
3. The reaction resultant is stable because the applied resultant is fixed;
   this alone is not evidence of field or energy convergence.
4. No M2/M3, independent nonlinear FEM solve, or formal replay is inferred
   from this diagnostic run.

The result supports retaining the current WP09 scope as experimental/bounded
while treating isotropic HEX8 refinement as the more viable numerical route
for a future, separately frozen formal contract. It does not justify changing
the strain threshold, relabeling the TET4 failures, or awarding points.

## Evidence

- Raw and machine-readable results: `qualification/0_2_9/wp09_remesh_study_r3/`
- Manifest: `qualification/0_2_9/wp09_remesh_study_r3/manifest.json`
- Summary: `qualification/0_2_9/wp09_remesh_study_r3/summary.json`
- The partial `r1` and `r2` directories are preserved as superseded tooling
  attempts. They are not used as numerical evidence; `r3` is the complete
  diagnostic run after the runner's serialization and comparison fixes.
- This analysis is diagnostic only; historical WP09 formal `FAIL_CLOSED`
  evidence remains authoritative and unchanged.
