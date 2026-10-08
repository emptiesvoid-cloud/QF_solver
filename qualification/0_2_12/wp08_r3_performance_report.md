# WP08-R3 — Bounded performance and memory observations

**Record type:** local microbenchmark, not scaling or industrial-performance evidence.

## Element microbenchmarks

One warmed observation per operation after two warm-up calls; affine elastic displacement, same material and fixture for both formulation IDs. Timings are wall-clock milliseconds and are environment-sensitive.

| Family | DOFs | Integration points | Legacy force only | Corrected force only | Legacy force+tangent | Corrected force+tangent | Corrected tangent force calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 12 | 1 | 0.234 | 0.607 | 5.483 | 14.971 | 25 |
| TET10 | 30 | 4 | 0.844 | 2.478 | 50.533 | 140.301 | 61 |
| HEX8 | 24 | 8 | 1.836 | 4.496 | 79.028 | 224.077 | 49 |
| HEX20 | 60 | 27 | 5.461 | 15.413 | 661.948 | 1862.561 | 121 |

For corrected force-only, the observed corrected/legacy ratios were approximately 2.45–2.94 on this run. The corrected force+tangent call took roughly 2.7–2.8x the corresponding legacy force+tangent call. The variation from the R2 median ratios is retained, not reconciled by changing code or selecting a favorable result; benchmark protocols and timing noise differ. The dominant R3 cost is the `2*n_dof+1` full corrected force evaluations per element tangent. For HEX20 that means 121 force evaluations, each traversing 27 integration points.

## Global Newton fixture

Same TET4 refinement fixture, load scale `0.25`, four fixed increments, two warm-up solves and one timed solve per formulation:

| Route | Solve time | Steps | Iterations | Final residual | Cutbacks |
|---|---:|---:|---:|---:|---:|
| Legacy | 1417.164 ms | 4 | 22 | `7.9823e-11` | 0 |
| Corrected | 2516.043 ms | 4 | 20 | `8.7886e-11` | 0 |

The corrected run was about `1.78x` slower in this single fixture while using two fewer Newton iterations. This does not establish a speedup or general relative efficiency. Line-search and adaptive-cutback cases are verified separately; their extra candidate/retry work is not folded into this timing comparison.

## Memory and serialized state

- Element tangents are dense local `n_dof x n_dof` NumPy arrays before sparse global scatter. Exact local storage is 1,152 bytes (TET4), 7,200 bytes (TET10), 4,608 bytes (HEX8), and 28,800 bytes (HEX20), excluding temporary arrays and Python overhead.
- A TET4 corrected tangent call under `tracemalloc` took 53.335 ms with a measured Python allocation peak of 59,531 bytes; the tangent's dense payload was 1,152 bytes. `tracemalloc` does not account for every native NumPy/SciPy allocation; its timing was instrumented and is not comparable to the uninstrumented table.
- One TET4 corrected material-state JSON encoding was 489 bytes in the sampled virgin-state fixture.
- A small corrected four-step checkpoint fixture wrote five checkpoint files; the largest was 3,953 bytes and their total was 18,930 bytes. This is a small fixture only; compression and per-point state scale with mesh/integration-point count.
- Corrected postprocessing and checkpoint metadata add small per-result/per-checkpoint identifiers; exact process RSS and large-mesh memory were not measured.

## Interpretation

`KERNEL_PERFORMANCE`, `ELEMENT_TANGENT_PERFORMANCE`, and `GLOBAL_NEWTON_PERFORMANCE` are distinct. R2's approximately 1.82–1.84 corrected force-kernel ratio was measured under its own median/tracemalloc protocol; the R3 table reports a different one-sample warmed protocol. No result is a benchmark campaign. The full cost of numerical tangent is not suitable for claiming large-model performance. WP09 may later address broader robustness/performance only under separate authorization; R3 does not reduce mathematical checks to obtain speed.
