# W resource estimates — static only

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

No timing, memory probe, mesh construction, solver, benchmark or FEM campaign was run for this estimate.

## Counts and scaling

Each structured hexahedral cell contributes six TET4 elements. Therefore W1 has `16×4×4×6 = 1,536` elements; W2 has `8×8×8×6 = 3,072`. The corresponding node grids are `17×5×5 = 425` and `9×9×9 = 729`, with 1,275 and 2,187 total translational DOFs. Against H3's 768 elements/225 nodes/675 DOFs, W1 is 2× the elements and 1.89× the nodes; W2 is 4× the elements and 3.24× the nodes.

For the current SciPy assembler, a 12×12 float64 element matrix carries 1,152 bytes per TET4. The emitted value/row/column arrays carry a further nominal 2,304 bytes per TET4 if each index is int64. A single full-chunk transient for those three arrays is therefore approximately 5.1 MiB for W1 and 10.1 MiB for W2. This is only the element matrix plus COO-style input arrays; it excludes temporary kernel arrays, CSR storage, accumulator fusion, solver factorization, Python/NumPy overhead and logs.

The current matrix-free `memory_bytes` property sums template, element-node, flattened-DOF, diagonal, block-inverse, free-map and workspace arrays. Applying that source formula with six TET4 templates and total-DOF upper bounds gives approximately 269 KiB for W1 and 528 KiB for W2. Actual free-map length depends on the exact support set; this estimate excludes the `LargeModel`, Python/NumPy/SciPy internals, CG vectors and solver/runtime overhead. It is not a measured RSS or a hard memory bound.

## Qualitative execution cost

W1 requires about twice H3's element kernels and global assembly, while W2 requires about four times. Sparse direct-factorization cost and peak memory may grow faster than element count and cannot be estimated reliably from these counts alone. Matrix-free CG avoids storing the full global stiffness but iteration count and preconditioner cost depend on conditioning; its small operator-array estimate is not total solve memory. Time and memory must be measured only under a future Owner-approved protocol.

The proposed W execution should use a timeout and output cap reviewed against prior evidence, but no new values are represented as approved here. Existing local V&V caps are software-polled and do not impose hard CPU/RAM/disk quotas. If the Owner requires a hard resource ceiling or protected historical archive, the current local environment is insufficient without separate isolation.
