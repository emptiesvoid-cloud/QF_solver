# Performance and Scaling Plan

Record model generation, assembly, constraints, factorization, solve,
post-processing, wall time, peak RSS, DOF, NNZ and iterations. Every profile
records Python, dependency, backend and hardware metadata.

Use repeated medians, warm-up policy and profile bands rather than noisy
per-PR absolute runtime gates. CI is limited to SMOKE. STANDARD, EXTENDED and
LARGE runs are controlled evidence and do not become release claims without
their own gate review.
