---
doc_id: DOC-029-WP04-C2-M3-ABORT-001
revision: 1.0
status: evidence
applicable_version: 0.2.9-development
---

# WP04-C2 M3 — owner-aborted linear-solver remediation record

The C2-M3 nonlinear process (PID `25932`) was deliberately stopped by the
Owner for linear-solver remediation. Its pre-stop snapshot recorded
`29,775.578 s` CPU, `21,584.007 s` wall time, `10.46 GiB` RSS, `14.58 GiB`
private memory, and 24 threads. py-spy attributed approximately 98–100% of
sampled main-thread time to `scipy.sparse.linalg.spsolve` / SuperLU.

The authoritative classification is
`ABORTED_BY_OWNER_FOR_LINEAR_SOLVER_REMEDIATION`. The external runner's stale
`RUNNING` status is an interrupted status-write artifact, not a terminal solver
classification. This record neither changes the historical WP04-C failure nor
claims a resource, numerical, or timeout failure.

WP04 remains HOLD, G04-10 remains unresolved, and the validated total remains
29/100. Machine-readable evidence:
`qualification/0_2_9/wp04_c2_m3_owner_abort.json`.
