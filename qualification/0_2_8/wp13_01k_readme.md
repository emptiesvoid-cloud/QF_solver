# WP13-01K connected MVP campaign

The contract is `WP13-01K-CONNECTED-MVP-001`, frozen before any model solve
at commit `1b21d695b236e6835cf5a952b2e41db7f17c8e1b`.
The earlier design commit was adjusted before all model computations to add
a WEDGE6 buffer: TET4 and HEX8 must not even share an edge or corner.

The compact elbow uses shared lattice nodes and isotropic refinement.
Only the HEX8 face at y=-1 is supported. Only the TET4 face at z=3 is loaded.
WEDGE6 is the sole connection between these regions. The two interfaces
are verified by matching faces, unique DOFs and independently summed family
internal forces, including resultant transfer. The execution record contains
all pre-solve geometry/stiffness checks, physical checks and saved solutions.

## Reproduction

Use the recorded Docker image and set OPENBLAS_NUM_THREADS=1 and
OMP_NUM_THREADS=1. Mount the checkout at /work and use /work as working directory.
The runtime requires PETSc/petsc4py 3.25.1 and MPI as recorded in the execution JSON.

```text
python scripts/run_wp13_01k_mvp.py --case small --backend serial --label new_small_serial
mpiexec -n 2 python scripts/run_wp13_01k_mvp.py --case small --label new_small_mpi2
```

After the small control passes, use `--case stage_a` (9768 DOF), then
`--case stage_b` (50844 DOF). Apply the contract's stop rules. Use new labels
to preserve captured results. Run the comparison script on saved labels:

```text
python scripts/check_wp13_01k_comparison.py label1 label2 --output new_partition
python scripts/check_wp13_01k_comparison.py label1 replay1 replay2 --replay --output new_replay
```

## Evaluator correction retained for review

`small_mpi2.json` preserves the first evaluator FAIL. All physical gates passed;
the evaluator erroneously required **both** family interface pairs to cross ranks.
The frozen contract requires nonzero cross-rank faces and ghosts overall.
The correction implements that requirement without changing the model, partition
or threshold. `small_mpi2_contract.json` records the subsequent run.
Both pairs have real cross-rank faces at Stage A and Stage B.
The final Owner should review this correction explicitly.

## Interpretation limits

The stiffness entry max/min statistic includes nearly zero coefficients and is
not a condition-number estimate. Geometry/Jacobian checks and the positive
assembled diagonal ratio are the predeclared acceptance measures.
Comparison with the old slender model is a correlation, not proof of causality.

PETSc matrix/connectivity are not gathered globally via MPI, but the runner
replicates its input model and partition metadata and scatters the full solution
for reaction reconstruction. Timing covers assembly/solve, excluding geometry
inspection and independent interface postprocessing. Memory is the maximum
rank ru_maxrss sampled at that point, in MiB. One reported iteration denotes a
direct factorization solve, with two additional fixed residual corrections.

No general industrial-model, iterative scalability, 1M connected, release or
maturity claim follows. Prior FAIL records, contracts and 0.2.7 evidence remain
unchanged. Final Owner approval remains separate from this technical campaign.
