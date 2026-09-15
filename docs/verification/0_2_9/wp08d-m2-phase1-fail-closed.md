# WP08-D M2 Phase-1 — fail-closed evidence

The authorised M2 production run was executed once on commit `d47287944906610eaac751871796de34df4b7d44`. It ended fail-closed with `NumericalConvergenceError`: the frictional contact active set did not converge with direct or active-slip root iterations.

The run reached mesh construction, assembly completion, and the contact active-set linear-solve entry point. It accepted no load increment. The preserved M2 evidence consists of lifecycle telemetry, progress, console logs, and a hash-complete manifest. A final `result.json` and `raw.npz` do not exist because no converged terminal state was produced.

No independent reference or replay was run: both depend on a completed production M2 result. M3 was not run. No production mechanics, thresholds, solver parameters, or fallbacks were changed.

This evidence does not award WP08-D points. WP08-D remains `FAIL_CLOSED_PHASE1_M2`, with `0/2` formal points; WP08 remains `0/8`. Owner review is required before any remediation or further execution.
