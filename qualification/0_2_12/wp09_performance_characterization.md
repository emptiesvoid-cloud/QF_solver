# WP09 performance characterization

**Record type:** small-fixture measurements; not industrial scaling evidence.

## Method

The WP08-R3 and WP09 implementations were loaded from source revisions into the same Python process and run on the same corrected elements. Each case was warmed and measured in four repetitions; medians are reported. Python allocation peaks were measured with `tracemalloc`; native-library allocations may not be included. A separate paired nonlinear-static TET4 case used three repeated wall-clock runs per implementation. This is a bounded comparison, not a broad benchmark campaign.

## Element force plus tangent

| Family | DOFs | Integration points | Force evaluations | R3 median (s) | WP09 median (s) | Ratio | Traced peak R3 / WP09 (bytes) |
|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 12 | 1 | 25 | 0.0147374 | 0.0149828 | 1.01665 | 41,843 / 42,615 |
| TET10 | 30 | 4 | 61 | 0.1437606 | 0.1448563 | 1.00762 | 156,106 / 157,487 |
| HEX8 | 24 | 8 | 49 | 0.2310198 | 0.2323869 | 1.00592 | 289,752 / 292,947 |
| HEX20 | 60 | 27 | 121 | 1.9639448 | 1.9688649 | 1.00251 | 1,015,962 / 1,018,650 |

The observed overhead is approximately 0.25–1.67%, small relative to measurement variability. No speedup is claimed. The force-evaluation count is unchanged at `2*n_dof+1`; the instance cache avoids repeating reference quadrature preparation, but the finite-difference force calls dominate these fixtures.

## Global nonlinear solve

Paired three-run medians: WP08-R3 `2.5312119 s`; WP09 `2.5417024 s`; ratio `1.00414`. Both solved the same four-step, 20-iteration corrected TET4 case, with no cutbacks or line-search reductions and matching final residuals to reported precision. The sample is too small to distinguish a performance change from runtime noise.

## Bounded stage microtimings

On the same Python process and one corrected TET4 integration-point fixture, `time.perf_counter` medians over five repeats were: polar kinematics/SVD `83.41 µs` (3000 calls per repeat), polar directional derivative/Sylvester solve `47.57 µs` (3000), constitutive update `18.91 µs` (1000), corrected element internal force `579.96 µs` (200), and corrected element force+tangent `14.849 ms` (8). The force/tangent value is consistent with the paired four-family measurements; the tangent dominates because it performs 25 full force evaluations. These microtimings are interpreter/hardware-sensitive, not additive, and are included only to identify likely cost centers.

The present campaign does not isolate sparse factorization or line-search overhead from the global solver. The geometry cache and normalization add small preprocessing/storage work, while per-column corrected-force evaluation remains the dominant asymptotic expense. No large-mesh memory, concurrency, or industrial scaling claim is made. No optimization was accepted based on timing alone; force, state, directional-derivative, origin, and scale-covariance checks were also required.
