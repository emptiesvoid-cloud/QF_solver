# WP08 area-supported contact — R1.12 M4 slip diagnostic

This prospective, one-attempt campaign tests the R1.11 optimizer stopping
correction on the previously failing M4 `slip_target` case. It reuses the
frozen R1.10 M4 geometry, mesh, material, boundary conditions, loads, friction
and contact stiffness. The physical per-contact root tolerance remains
`1e-9`; the R1.11 optimizer stopping tolerance is `1e-12` for that physical
tolerance. Optimizer success alone is not acceptance.

The runner freezes its source inventory, this document, the R1.11 M1/M2/M3
evidence hashes, and the historical M4 slip failure before starting. The only
authorized execution is one serial M4 `slip_target` solve in a new output
directory. There is no retry, parameter tuning, M1/M2/M3 rerun, stick rerun,
independent reference, replay, score award, or formal WP08 qualification.
The historical failures remain immutable.

Diagnostic gates are the frozen runner gates: finite serialized observables,
converged solver, eight load steps, rank-2 active support, and terminal active
tangential state `slip`. No mesh-refinement threshold is frozen; any M3/M4
comparison is descriptive only. The result is experimental evidence and does
not by itself establish mesh convergence or Owner acceptance.
