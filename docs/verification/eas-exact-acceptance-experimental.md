# Experimental EAS exact residual acceptance

The boolean `experimental_eas_exact_residual_acceptance` defaults to false.
It selects direct SciPy linear statics on a supported homogeneous
`HEX8_EAS_EXPERIMENTAL` mesh. The diagnostic-only option is mutually
exclusive. Pre-guard direct refinement cannot be combined with this option.
The existing residual guard runs first at its existing tolerance.
The experiment only handles finite residual rejections at the binary64
threshold `1e-7`. Other failures retain the guard exception.

One supervised child receives a snapshot of the reduced CSR matrix, right-hand
side and initial candidate. The child checks their identity and evaluates the
exact squared criterion on their represented values. On an exact FAIL it may
factorize the same matrix once and apply at most three sparse LU corrections,
using an exactly accumulated residual rounded to binary64 for each correction.
The next candidate is stored in binary64 and checked exactly before any
acceptance. The archived initial vector fails exactly, so checking it alone
cannot resolve the archived case.

The input limits are 1,500 rows, 100,000 entries and 8 MiB of array data.
The worker is subject to a 10 s observation deadline and a 256 MiB sampled
RSS ceiling. Neither is an OS quota. Synchronous spawn and bounded cleanup
may extend elapsed time. Missing monitoring, malformed output, interruption,
zero denominator, numerical failure and exhausted corrections retain rejection.

The response binds the initial system, threshold and candidate to the tested
candidate and the refinement history. A fresh per-call integrity key detects
stale or altered replies. The parent recomputes the candidate identity on
the same system before it can return the corrected vector. The worker and
parent are trusted code within one process family. Exact acceptance remains
separate from the historical guard decision and certifies only the criterion
for the represented inputs.
