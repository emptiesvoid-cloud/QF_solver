# WP12-W directional TET4 development protocol

**Status:** `DEVELOPMENT_ONLY`  
**Formal qualification:** `NOT_AUTHORIZED`  
**WP12:** `OPEN`

## Fixed physical and numerical case

The development sequence reuses the frozen H3 cantilever model and adds two
directional meshes. All three cases use the same 4 m × 0.4 m × 0.4 m domain,
isotropic linear elasticity (`E=70 GPa`, `nu=0.3`), a total `-1 N` global-Z
load on the `x=L` face with tributary weights, and all three translations fixed
on `x=0`. Meshes use the existing six-TET4-per-brick decomposition.

| Case | Cells `(nx, ny, nz)` | TET4 | Nodes | Total DOF | Free DOF |
|---|---:|---:|---:|---:|---:|
| H3 comparison | `(8, 4, 4)` | 768 | 225 | 675 | 600 |
| W1 longitudinal | `(16, 4, 4)` | 1,536 | 425 | 1,275 | 1,200 |
| W2 transverse coupled | `(8, 8, 8)` | 3,072 | 729 | 2,187 | 1,944 |

The solve uses the existing matrix-free CG route, chunk size 8192, `rtol=1e-8`,
`atol=0`, maximum 10,000 iterations, and nodal block-Jacobi preconditioning.
Those are the H3 settings; this protocol adds no numerical acceptance
threshold. Each case is run once, sequentially, with a 300 s timeout and stop
on the first nonzero exit, timeout, or missing result. There is no automatic
retry, MPI, or heavy benchmark.

## Recorded quantities and definitions

The harness records element volume/quality, node/element/DOF counts, loaded
face mean `UZ`, load-conjugate displacement `F^T u / sum(Fz)`, maximum nodal
translation and its location, support reactions and moments about the origin,
force/moment imbalance, matrix-free solver residual and iteration count,
strain energy `U = 0.5 u^T K u`, and external work `W = F^T u`.

For residual comparisons it reports both the dimensional free residual
`||K u - F||_2` in newtons and the existing large-route normalization
`||r_free||_2 / max(||F_free||_2, 1 N)`. The unit-valued floor makes this
normalized quantity dependent on the SI numerical unit convention; it is not
an invariant relative error. Reactions are recovered from the constrained
entries of `K u - F`. A sparse assembly is performed after the matrix-free
solve to recover these quantities; it does not perform another linear solve.

The diagnostic reference remains the prior 1D Euler-Bernoulli plus Timoshenko
value `-1.4397142857142855e-7 m`. It is not a three-dimensional oracle. H3's
previous archived value `-4.795612893178559e-8 m` remains historical and is not
rewritten; a new H3 development run supplies the additional fields needed for
like-for-like observables.

## Interpretation limits

W1 changes longitudinal resolution while retaining the two transverse cell
counts. W2 doubles both transverse counts at once and cannot separate their
individual effects. Differences among H3, W1, and W2 are directional
sensitivity observations, not an asymptotic convergence sequence. A larger
deflection can be described as increased compliance under this discretization;
it does not alone demonstrate under-resolution, shear locking, or physical
accuracy. The matrix-free and sparse routes share the frozen element/material
formulation. An independent 3D reference, such as a same-model higher-order
solid comparison, remains future work.

## Execution and evidence handling

The one-purpose development harness is
[`run_tet4_directional_dev.py`](../../../../scripts/wp12_dev/run_tet4_directional_dev.py).
It verifies the scientific commit/tree, a clean checkout, the import origin,
the pinned Python/numerical package versions, and all six single-thread
variables before solving. It refuses an existing output destination and stores
the generated model, displacement vector, JSON metrics, process logs, and
hashes outside the repository. This is local development provenance; it is not
a sandbox, a hard resource quota, or a formal WP12 execution receipt.

The frozen source identity is commit
`00428adf38e9397340ac136f6f503a268eb671da`, tree
`df4ec667bf746b042c900fad1f86bf542e1a437b`. Any change to those sources
requires a new candidate identity and a new prospective plan. All measured
outputs are descriptive unless a future, separately approved formal manifest
defines acceptance criteria.
