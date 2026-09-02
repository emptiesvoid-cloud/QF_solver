---
doc_id: DOC-027-LU2-WP04-FORENSIC-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
source_sha: c4c62bdd42d99b8252130f0d5de6a1a9c54def8b
reviewer: ""
approver: ""
---

# LU2-WP04 - 5M Bronze forensic audit

## Conclusion

The previous terminal session returned, but the Docker container was still
running when this audit inspected it. The eight MPI Python ranks were in a
runnable state (`Rsl`) and each reported approximately 99.9% CPU. The
container was then stopped explicitly by the audit. This is evidence of an
owner interruption whose first stop did not propagate, not evidence that the
calculation failed by itself.

The active classification is therefore `USER_INTERRUPTED_INCONCLUSIVE`, not
`RESOURCE_LIMITED`. The older guard record remains retained as historical
evidence of a 2x reference-time overrun, but its causal interpretation is
superseded by this audit.

## Reconstructed timeline

1. Two deterministic 5M TET4 model constructions passed. They produced
   `5,012,640` DOF, `9,773,946` elements and the identical input digest
   `ff73bc9debd0c8e1ae7355cb6b42e62734c619efa87423e484284878449a55ec`.
2. The eight-rank MPI command started under the unchanged WP02 freeze.
3. The runner loaded and audited the distributed model, computed the
   partition digest, created a PETSc AIJ matrix and called `matrix.setUp()`.
4. The last confirmed phase was the per-element AIJ insertion loop in
   `PetscTET4Assembler`. The final `matrix.assemble()`, RHS setup, KSP setup
   and GAMG readiness were not reached.
5. No raw JSON result was written because the runner writes it only after the
   Bronze path completes.

## Resource and scaling findings

No OOM, MPI error or silent fallback was observed. The last container RSS
sample was approximately `4.02 GiB`, below the `50,458,099,712` byte Docker
limit, but no persisted peak or swap time series exists. Swap pressure and
percentage of assembly completed are therefore `NOT_MEASURED` and
`NOT_ESTIMABLE`, respectively.

The 5M workload is about `1.67x` the 3M workload in DOF and elements. The
observed multi-hour AIJ insertion phase is substantially longer than that
simple ratio would predict, but the 3M reference total includes solve and
post-processing and the 5M run did not reach readiness. The discrepancy is a
diagnostic signal for sparse insertion/communication overhead, not proof of a
hard memory or capacity limit.

## Decision

`RESOURCE_LIMITED_PROVEN = NO` and `C1_TRIGGER_CONFIRMED = NO`.
`WP04` remains incomplete and `WP05` is not unlocked. A supervised longer
retry is recommended, with a five-hour hard ceiling, progress counters,
per-rank CPU/RSS, cgroup memory/swap telemetry and explicit phase markers.
The existing 2x reference point must be treated as a progress audit
checkpoint before the retry policy is run; the WP02 backend, ranks,
partitioning, KSP, PC and tolerances remain frozen.

The machine-readable report is
[`wp04_forensic_audit.json`](../../../qualification/0_2_7/wp04_runtime/wp04_forensic_audit.json).
