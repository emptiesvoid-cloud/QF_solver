---
doc_id: DOC-NL-025-011
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 performance plan

## Purpose

Characterize nonlinear cost and memory without turning 0.2.5 into an HPC rewrite.
Optimization begins only after a profile identifies a stable hotspot.

## Instrumentation

Measure per increment and total:

- constitutive update time and call count;
- quadrature and B/kinematic operator time;
- material, geometric and contact tangent assembly;
- contact search/projection and active-set changes;
- sparse assembly conversion, nnz and allocation count;
- linear solve/factorization and iterative diagnostics;
- state begin-trial, copy, commit and rollback;
- continuation constraint work;
- peak RSS where available and deterministic storage estimates.

The first reproducible implementation is
`scripts/benchmark_nonlinear_025.py`. It records raw samples for the regular
two-cell shared J2 TET4/TET10/HEX8/HEX20 benchmark, including DOF count, Newton
iterations, wall time, Python peak allocations, optional RSS and mean phase
timings. Repeated runs also retain median, minimum, maximum and sample standard
deviation for wall time, together with median phase timings where available;
these statistics describe repeatability and do not define release thresholds.
The experimental finite-kinematic branch can be selected explicitly;
it is not a release qualification claim. For example:

```text
python scripts/benchmark_nonlinear_025.py --families TET4 HEX8 --repeats 3 --output results/benchmark_0_2_5/nonlinear.json
python scripts/benchmark_nonlinear_025.py --families TET4 --kinematics total_lagrangian_j2 --repeats 1 --output results/benchmark_0_2_5/tl_j2.json
python scripts/benchmark_nonlinear_025.py --families TET4 --path arc_length --repeats 1 --output results/benchmark_0_2_5/arc_length.json
python scripts/benchmark_nonlinear_025.py --families TET4 TET10 HEX8 HEX20 --path arc_length_finite_kinematic --repeats 1 --output results/benchmark_0_2_5/arc_length_finite_kinematic.json
python scripts/benchmark_nonlinear_025.py --families TET4 --path coupled --repeats 1 --output results/benchmark_0_2_5/coupled.json
```

The benchmark now exposes explicit `load_control`, `arc_length`,
`arc_length_finite_kinematic`, `contact` and `coupled` paths. The load-control
path exposes non-invasive per-step timers for
`assembly_seconds`, `linear_solve_seconds` and `line_search_seconds`, plus
component timings for element setup, element kernel, local scatter, sparse
conversion and contact assembly, plus nonlinear element-plan and
Total-Lagrangian reference-geometry cache hit/miss counts. These are
observational phase timings, not
claims of a scaling law or a release performance target.

### Finite-kinematic arc-length replay (one repeat, working tree)

The latest explicit replay is archived at
`results/benchmark_0_2_5/arc_length_finite_kinematic_latest.json`. All four
families reached the signed target factor `0.5` with the common adaptive-radius
driver:

| Family | DOF | Newton | Wall s | Assembly s | Sparse solve s | Max relative residual |
|---|---:|---:|---:|---:|---:|---:|
| TET4 | 24 | 76 | 2.943 | 2.137 | 0.297 | `1.65e-08` |
| TET10 | 78 | 670 | 83.906 | 70.081 | 2.797 | `9.58e-08` |
| HEX8 | 24 | 120 | 6.546 | 4.961 | 0.478 | `6.57e-08` |
| HEX20 | 60 | 1479 | 235.151 | 197.523 | 6.060 | `9.90e-08` |

The benchmark uses `max_arc_steps=512` because the HEX20 path needs a longer
continuation budget; its successful run used 319 accepted steps. These are
single-run, dirty-worktree observations. They identify the current HEX20
element-kernel cost but do not establish scaling, a speedup, or close `025-G08`.

### Bounded path smoke (working tree)

One TET4 repeat was executed for each new path on the current working tree.
These values are characterization only, not frozen release thresholds:

| Path | Kinematics | DOF | Newton | Wall s | Assembly s | Linear solve s | Max relative residual |
|---|---|---:|---:|---:|---:|---:|---:|
| `load_control` | `total_lagrangian_j2` | 36 | 23 | 1.335 | 1.092 | 0.064 | `9.88e-09` |
| `arc_length` | `small_strain` | 12 | 14 | 0.177 | 0.027 | 0.057 | `8.73e-11` |
| `contact` | `small_strain` | 24 | 21 | 0.388 | 0.219 | 0.056 | `4.91e-09` |
| `coupled` | `total_lagrangian_j2` | 24 | 24 | 0.811 | 0.612 | 0.068 | `2.93e-08` |

The values are one local repeat and are not a release threshold or a scaling
claim. RSS and Python allocation counters are retained in the raw JSON output.

### Two-repeat all-family load-control characterization

The same regular two-cell J2 path was repeated twice for each supported solid
family on the current Windows worktree. The latest raw report is
`results/benchmark_0_2_5/nonlinear_load_control_all_families_repeats2_latest.json`.
All eight runs converged with the same Newton iteration count per family. The
coefficient of variation (CV) is descriptive only:

| Family | DOF | Newton | Mean wall s | CV | Mean assembly s | Mean sparse solve s | Max Python peak bytes | Max RSS bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 36 | 22 | 0.607 | 2.46% | 0.392 | 0.0614 | 1,343,608 | 112,435,200 |
| TET10 | 129 | 21 | 2.318 | 0.19% | 1.648 | 0.0646 | 1,426,913 | 114,286,592 |
| HEX8 | 36 | 17 | 1.028 | 2.31% | 0.747 | 0.0473 | 582,095 | 114,790,400 |
| HEX20 | 96 | 22 | 16.453 | 0.16% | 11.160 | 0.0654 | 1,112,348 | 114,573,312 |

This is a reproducibility and hotspot characterization, not a scaling or
release-acceptance result. The report records provenance as commit
`e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` with a dirty worktree; it must be
replayed on a clean candidate SHA before G08 can close.

### Component-level replay (one repeat, working tree)

The latest raw report is
`results/benchmark_0_2_5/nonlinear_load_control_component_profile_latest.json`.
All four runs converged. The decomposition is:

| Family | DOF | Wall s | Assembly s | Element kernel s | Scatter s | Sparse conversion s | Sparse solve s | Tangent nnz |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 36 | 0.619 | 0.404 | 0.205 | 0.120 | 0.017 | 0.058 | 684 |
| TET10 | 129 | 2.390 | 1.719 | 0.918 | 0.565 | 0.060 | 0.066 | 5,967 |
| HEX8 | 36 | 1.029 | 0.744 | 0.626 | 0.062 | 0.014 | 0.045 | 1,008 |
| HEX20 | 96 | 16.622 | 11.336 | 10.677 | 0.438 | 0.050 | 0.065 | 6,624 |

The result confirms that the current engineering-medium HEX20 cost is
dominated by the element kernel, not the sparse linear solve. It is still a
dirty-worktree, single-repeat characterization; no optimization or scaling
claim is inferred and G08 remains open until clean-SHA repeatability and
numerical before/after evidence exist.

## Exploratory result: reusable nonlinear assembly plan

The nonlinear driver now prepares a per-solve assembly plan containing the
material objects, element kernels, local coordinates and global DDL maps. It
does not retain integration-point history: trial and committed material states
remain supplied by the Newton transaction on every assembly. This removes the
repeated construction of those objects from the Newton loop while preserving
the existing sparse COO-to-CSR assembly path.

The one-repeat replay is stored in
`results/benchmark_0_2_5/nonlinear_load_control_cache_latest.json` on the same
dirty working tree. All four families converged and reported zero cache
misses during assembly. The observed setup-time comparison against the prior
component profile was:

| Family | Previous setup s | Cached setup s | Cache hits | Cache misses | Newton | Final displacement norm |
|---|---:|---:|---:|---:|---:|---:|
| TET4 | 0.00543 | 0.00040 | 260 | 0 | 22 | 0.1728238257 |
| TET10 | 0.00960 | 0.00059 | 250 | 0 | 21 | 0.5240095385 |
| HEX8 | 0.00106 | 0.00009 | 42 | 0 | 17 | 0.0382647740 |
| HEX20 | 0.00185 | 0.00014 | 52 | 0 | 22 | 0.4306610359 |

The assembly and total wall times remain within the variability of a single
local run, while the numerical outputs and iteration counts match the prior
profile. This is a bounded implementation result, not a release speedup or
scaling claim. A clean-SHA replay, repeated samples and the relevant
before/after numerical comparison remain required before G08 can close.

## Exploratory result: reference-geometry reuse

Total-Lagrangian J2 kernels now cache the reference quadrature measures and
gradients for the immutable reference coordinates of one solve. The cache key
contains the coordinate shape, dtype and bytes; a changed reference mesh
invalidates it. Hit/miss counters are exported in each nonlinear step and in
the benchmark samples, making the optimization auditable. This removes
repeated reference Jacobian/inverse work from Newton iterations without
changing the material state or tangent formulas. A before/after speedup is not
claimed until the same clean-SHA multi-repeat benchmark is available.

The first post-change observation is archived at
`results/benchmark_0_2_5/nonlinear_load_control_reference_cache_latest.json`.
The four finite-kinematic family runs converged and reported reference-cache
misses only on their first element evaluation: TET4 `260/10`, TET10 `270/10`,
HEX8 `40/2` and HEX20 `52/2` hits/misses. This confirms reuse across Newton
iterations; it is a dirty-worktree single-repeat observation and does not close
`025-G08`.

## Exploratory result: finite-kinematic TET4 assembly

After vectorizing the finite-kinematic TET4 tangent contraction, the same dirty
working-tree run (10 elements, 36 DOF, one repeat, Python 3.13.1 on Windows)
changed as follows:

| Metric | Before | After | Interpretation |
|---|---:|---:|---|
| Total elapsed time | 43.207 s | 1.341 s | exploratory characterization |
| Assembly time | 41.445 s | 1.096 s | measured hotspot reduction |
| Linear solve time | 0.0663 s | 0.0654 s | unchanged within this sample |
| Newton iterations | 23 | 23 | same convergence regime |
| Maximum relative residual | 4.26e-9 | 9.88e-9 | same configured criterion |
| Final displacement norm | 0.1453241371 | 0.1453241370 | numerical agreement in this sample |
| Final PEEQ | 0.1018066229 | 0.1018066229 | numerical agreement in this sample |

Raw files are local exploratory artifacts under `tmp/` and are not release
evidence. The comparison is a single small case on a dirty worktree; it does
not close 025-G08, prove scaling, or justify a general performance claim.

The corresponding one-repeat HEX8 run completed in **1.552 s**, with **1.271 s**
in assembly, **17 Newton iterations** and a final relative residual of
`5.85e-10`. The earlier **27.77 s** value was an intermediate vectorization
step and is retained only in local raw artifacts; it is not the final after
measurement.

## Exploratory result: HEX20 validation reuse

The first all-family profile exposed a redundant full geometry validation inside
each HEX20 Gauss-point B-matrix build. The public `b_matrix()` contract still
validates geometry for direct callers, while the element integration loop now
validates once and reuses the validated local kernel. On the same two-cell,
96-DOF, one-repeat small-strain J2 case, the dirty working-tree comparison was:

| Metric | Before | After | Interpretation |
|---|---:|---:|---|
| Total elapsed time | 114.288 s | 17.321 s | 84.8% lower in this sample |
| Assembly time | 96.639 s | 11.573 s | 88.0% lower in this sample |
| Linear solve time | 0.0656 s | 0.0669 s | unchanged at this scale |
| Newton iterations | 22 | 22 | same convergence regime |
| Maximum relative residual | not retained in baseline summary | `5.49e-08` | configured criterion remained satisfied |
| Final displacement norm | not retained in baseline summary | `0.4306610359` | recorded for replay |
| Final PEEQ | not retained in baseline summary | `0.1716514432` | recorded for replay |

The before value is the all-family baseline captured before the local kernel
change; the after value is stored in
`results/benchmark_0_2_5/nonlinear_load_control_hex20_optimized.json`.
This is an optimization characterization only: it uses one local Windows
repeat, a dirty worktree and an engineering-medium mesh. It does not close
025-G08, establish a scaling law, or qualify HEX20 for large models. A clean
SHA replay, repeated measurements and numerical comparison against the frozen
baseline remain required.

## Targeted studies

| Study | Variants | Question |
|---|---|---|
| Element family | TET4/TET10/HEX8/HEX20 | cost per Gauss point, element and converged DOF |
| State storage | element/Gauss count and state width | deep-copy memory/time scaling |
| Newton | iterations and tangent reuse | where total solve time is spent |
| Geometry | material vs geometric tangent | incremental cost of large deformation |
| Contact | candidates/active pairs/sliding distance | search vs projection vs tangent cost |
| Arc-length | load control vs continuation | augmented solve and retry overhead |
| HEX20 | integration/constitutive/assembly/copies | explain and measure the known high cost before/after the local optimization |

## Benchmark hygiene

- pin process/thread counts where supported;
- record warm-up and at least enough repetitions to estimate variability;
- separate CPU time, wall time and external solver time;
- use identical mesh/history/options for before/after;
- archive raw samples, not only averages;
- do not assert tight wall-time limits on shared CI runners.

## Optimization acceptance

An optimization is accepted only when the target metric improves outside the
measured noise band, all relevant numerical outputs remain within frozen
tolerances, focused and full regression pass, and readability/maintenance cost
is documented. Otherwise retain the profile as characterization evidence.

## Gate 025-G08 closure

G08 can close without a speedup when all mandatory paths have a reproducible cost
model, hotspots and remaining limits. It cannot close with unmeasured claims such
as “faster”, “scalable” or “memory efficient”.

## Exploratory result: bounded nonlinear tangent assembly

The common nonlinear assembly no longer retains all global tangent triplets in
unbounded Python lists. Local tangent contributions are converted to CSR chunks
and merged by `SparseCsrAccumulator`; `nonlinear_assembly_chunk_size` controls
the peak chunk (default `256` elements). Each nonlinear step now records
`sparse_chunk_count`, `sparse_peak_chunk_entries`,
`sparse_peak_chunk_bytes_estimate` and `sparse_accumulator_levels` alongside the
existing timing counters. The byte value is a conservative estimate of the
temporary row/column/value staging buffers; it is not a process RSS measurement
and excludes the final CSR accumulator. This keeps the default sparse path and
the numerical formulas unchanged while making the temporary assembly footprint
observable and bounded by the configured chunk.

The same bounded CSR accumulation is now used by the high-order
Total-Lagrangian geometric assembly (`TET10`/`HEX20`) used by the geometric and
buckling paths. Its latest assembly metrics are exposed through
`assembly_diagnostics()` and included in geometric-static solver diagnostics;
the finite-kinematic kernels and their constitutive response are unchanged.

The change is an implementation/performance observation only. It does not claim
a speedup or close `025-G08` until a clean-SHA repeated benchmark compares the
old and new paths with numerical non-regression evidence.

The first post-change run is archived at
`results/benchmark_0_2_5/nonlinear_load_control_sparse_chunks_latest.json`.
It converged on all four finite-kinematic families. The maximum observed chunk
counts were TET4 `5`, TET10 `10`, HEX8 `2` and HEX20 `2`; the corresponding
peak local-entry counts were `288`, `900`, `576` and `3600`; the corresponding
staging-buffer estimates were `13,824`, `43,200`, `27,648` and `172,800`
bytes. These counters make the bounded temporary assembly policy auditable,
while the dirty one-repeat run remains only exploratory evidence.

The bounded geometric path replay is archived at
`results/benchmark_0_2_5/geometric_static_all_families_latest.json`. TET4,
TET10, HEX8 and HEX20 all converged on the recorded regular meshes with 18
Full-Newton iterations; the maximum relative residuals were respectively
`4.86e-12`, `2.81e-11`, `1.31e-12` and `2.37e-11`. The run records elapsed time
and RSS samples, plus shared-driver assembly and linear-solve timers. The
high-order rows also expose the CSR staging estimates. This is bounded
characterization only and does not close `025-G08` or qualify the high-order
geometric path.

### Targeted contact and coupled-path replay

The same benchmark harness was also replayed once for the existing TET4 contact
and coupled paths. The raw reports are
`results/benchmark_0_2_5/contact_tet4_latest.json` and
`results/benchmark_0_2_5/coupled_tet4_latest.json`. Both runs are `PASS` on the
current dirty worktree:

| Path | Kinematics | DOF | Newton | Wall s | Assembly s | Linear solve s | Contact assembly s | Max relative residual |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `contact` | `small_strain` | 24 | 18 | 0.374 | 0.195 | 0.053 | 0.028 | `1.64e-08` |
| `coupled` | `total_lagrangian_j2` | 24 | 24 | 0.870 | 0.639 | 0.078 | 0.037 | `2.93e-08` |

The contact run records `PEEQ=0.1205`, plastic dissipation `0.0748` and
`contact_tangent_nnz=388`; the coupled run records `PEEQ=0.1045`, plastic
dissipation `0.0564` and `contact_tangent_nnz=396`. These measurements are
diagnostic evidence for the common driver only. They do not establish general
surface contact, external coupled correlation, scaling, or close `025-G05`,
`025-G06` or `025-G08`. Both reports carry the provenance
`e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` with `worktree_dirty=true`.
