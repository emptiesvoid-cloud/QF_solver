# WP06-D local axial mesh audit (no solve)

## Proposal

The current M1 `64×4×4` mesh is retained. Refinement is added only in the crown/load window and at both finite end-bearing zones. One-cell transition bands keep the axial size jump at 2:1. The y/z section remains `4×4`; this is therefore a local axial diagnostic, not a complete 3-D convergence hierarchy.

## Results

| level | x cells | nodes | TET4 | DDL | min quality | max cond(J) | volume error | patch triangles | force error | moment error | RB rank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | 64 | 1625 | 6144 | 4875 | 0.35072 | 14.8333 | 1.735e-16 | 64 | 2.220e-16 | 1.970e-18 | 6/6 |
| M2 | 104 | 2625 | 9984 | 7875 | 0.356829 | 14.584 | 3.469e-16 | 128 | 4.441e-16 | 1.358e-18 | 6/6 |
| M3 | 188 | 4725 | 18048 | 14175 | 0.305426 | 14.5571 | 1.735e-16 | 256 | 8.882e-16 | 1.790e-18 | 6/6 |

## DDL comparison

| level | local DDL | uniform 3-D reference | uniform DDL | reduction |
|---|---:|---|---:|---:|
| M1 | 4875 | M1_current_64x4x4 | 4875 | 0.00% |
| M2 | 7875 | M2_uniform_128x8x8 | 31347 | 74.88% |
| M3 | 14175 | M3_uniform_256x16x16 | 222819 | 93.64% |

## Conclusion

The local meshes are topologically valid, positive-volume, manifold, remove all six rigid modes, preserve the reference load resultant/moment, and are nested. They reduce the proposed M2/M3 DDL substantially. They do not yet prove nonlinear path accuracy: only a formal production/reference/replay campaign can establish that, and the unchanged 4×4 cross-section must be explicitly accepted as a scope limitation or refined locally in a later mesh family.
