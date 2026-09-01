---
doc_id: DOC-027-WP14-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
---

# WP14 - Large-Scale Execution Contract

WP14 is a contract gate, not a large benchmark. It freezes the physical
model, execution profile, acceptance metrics, resource rules and evidence
format before WP15-WP18 runs. The authoritative machine-readable record is
[`qualification/0_2_7/wp14_execution_contract.json`](../../../qualification/0_2_7/wp14_execution_contract.json).

## Reference model

The G01 reference is the public structured TET4 linear-static route generated
by `generate-large-tet4-block`:

* `69 x 69 x 69` bricks with the historical six-TET decomposition;
* 343,000 nodes, 1,971,054 TET4 elements and 1,029,000 true displacement
  degrees of freedom;
* unit SI cube, homogeneous isotropic material (`E=210 GPa`, `nu=0.3`);
* all translations fixed on `x=0` and a real uniform nodal dead load of
  `1,000,000 N` on `x=1` in the x direction;
* 4,900 loaded nodes and a load resultant invariant. The generated HDF5
  input is hashed byte-for-byte at execution.

The four subscale cases (`81`, `375`, `2,187` and `14,739` true DOF) use the
same geometry, material, boundary conditions and loading rules. They are the
declared comparison ladder for assembled versus matrix-free execution; they
are not 1M evidence.

## Frozen execution profile

The captured profile is Windows x86_64, AMD64 Family 25 Model 80, 12 logical
CPUs, 102,963,109,888 bytes of physical memory, Python 3.13.1, NumPy 2.2.6,
SciPy 1.15.2 and scipy-openblas 0.3.29. Numerical threads are fixed to one.
An execution on another machine must record a separate environment and is not
equivalent evidence.

The 1M reference route is explicit matrix-free CG with the nodal block-Jacobi
preconditioner. The assembled subscale route is explicit SciPy CG with the
Jacobi preconditioner. There is no silent backend fallback. The contract
freezes `rtol=1e-8`, `atol=0`, a maximum of 10,000 iterations and the
declared seed `0`, one numerical thread and the predeclared residual,
equilibrium and energy checks.

CG is conditional, not universal: the constrained operator must be symmetric
and positive definite for this homogeneous linear-elastic scope. A rigid mode,
non-positive direction, singular preconditioner block or unsupported backend
is an explicit fail-closed outcome.

## 1M and 3M rules

`1M_PASS` requires at least 1,000,000 real FEM DOF, a complete iterative solve,
finite outputs, residual, reaction/equilibrium and energy evidence, a
matrix-free/assembled subscale comparison, two independent replays and full
resource/provenance capture. Timeout, OOM or a resource-limited verdict never
creates a solve claim.

The 3M ladder is deliberately separate:

* **Bronze:** real 3M FEM model plus topology and resource preflight; no solve
  claim;
* **Silver:** complete reproducible iterative solve with residual, equilibrium,
  energy and resource evidence; principal target;
* **Gold:** PETSc/MPI distributed solve, restart and a second case or scaling
  point; stretch target.

Preflight estimates memory and disk before generation. The fixed safety rule is
`ceil(1.25 * declared peak estimate)`. Timeouts are 7,200 s for 1M, 14,400 s
for 3M Silver and 28,800 s for 3M Gold. Partial runs retain configuration,
input digest and resource/status metadata.

## Evidence and dependencies

Every future run records source/configuration/input digests, hardware and
software versions, backend, solver, preconditioner, topology, true DOF,
nonzero/operator memory, wall time, peak RSS, iterations, residual,
equilibrium, energy, UTC timestamp and a controlled verdict. Text configuration uses canonical
UTF-8/LF SHA-256; HDF5 and other binary artifacts use byte-for-byte SHA-256.

WP14 is PASS because these contracts are frozen and validated. It does not
claim a 1M or 3M solve. WP15 adds matrix-free numerical evidence, WP16 is the
release-blocking 1M qualification, WP17 covers PETSc/MPI, and WP18 executes
the Bronze/Silver/Gold ladder.
