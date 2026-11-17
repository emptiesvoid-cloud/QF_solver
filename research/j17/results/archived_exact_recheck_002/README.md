# J17 archived residual recheck

Offline post-processing of five archived 8x8 reduced systems and three stored vectors per frequency. No FEM assembly or solve was run.

The primary decision compares exact rational squared L2 values with the squared binary64 limit. Decimal norms are display-only. The current QF guard was recomputed from stored matrices, RHS vectors, and solutions. No route result was promoted.

The current J16 manifest SHA differs from the SHA recorded in the J16 high-precision contract. The five NPZ files used here match their current source-manifest entries; five per-frequency JSON files and the old guard summary do not. Those text records are comparison-only; guard metrics were recalculated.
