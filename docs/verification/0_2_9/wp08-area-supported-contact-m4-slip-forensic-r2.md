# WP08 area-supported contact — M4 slip forensic R2

This is a single, prospective forensic reproduction of the R1.10 M4
`slip_target` case. The earlier M4 result is preserved as a numerical
`FAIL_CLOSED`; this run uses a separate output directory and cannot overwrite
or reclassify it.

The runner reuses the frozen M4 mesh, material, loads, contact formulation,
friction data, tolerances, iteration limits, and fallback policy. It runs only
`M4/slip_target`, once, sequentially. It does not rerun stick, M1/M2/M3, a
reference, or a replay. No parameter tuning or formal WP08 claim is in scope.

The diagnostic change is limited to evidence capture: the runner serializes
the complete nested solver exception, its cause chain, optimizer termination
fields, and per-contact residual records. Dense global tangential-basis
vectors are encoded exactly by nonzero indices/values and a SHA-256 digest of
the original float64 vector. Other oversized numeric vectors are represented
by shape, finite counts, norm, extrema, and a SHA-256 digest. Non-finite
values remain explicit and cannot produce a PASS.

The resulting execution can diagnose a failure or record a successful
experimental reproduction; neither outcome alone qualifies WP08. A numerical
failure remains valid evidence, and no automatic retry is permitted.
