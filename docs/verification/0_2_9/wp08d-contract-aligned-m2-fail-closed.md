# WP08-D M2 contract-aligned requalification

The WP08-D Phase-1 runner now derives every load-history factor directly from
the frozen contract. In particular, step 1 is normal=1.0, tangential=0.0 as
required; no contract, threshold, mesh, load, tolerance, backend, or fallback
setting was modified.

The authorized M2 production route was rerun on that exact path and failed
closed at step 5. Steps 1-4 were accepted and their committed checkpoints were
preserved. At step 5 the normal set stabilized at [3, 7, 11]; the direct route
reached its fixed 25-iteration limit, then the bounded mixed active-slip root
route failed with a least-squares residual of 3.790e+00. Rollback was
performed.

The manifest hashes pass. This independently reproduces the frozen-contract
reference's step-5 failure and establishes that the earlier production pass
depended on the runner's incorrect first tangential factor.

M2 = FAIL_CLOSED
M2 replay = NOT_RUN
M3 = NOT_RUN
WP08-D points = 0/2

Further mechanics work requires a separate Owner-reviewed remediation scope.
