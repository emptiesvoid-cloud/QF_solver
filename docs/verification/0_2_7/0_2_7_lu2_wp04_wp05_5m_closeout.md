---
doc_id: DOC-027-5M-CLOSEOUT
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# LU2 5M Bronze and Silver Closeout

This closeout records the corrected WP04 Bronze retry and the conditional LU2-WP05 Silver continuation from source SHA `04b07e00ddfe0b339b5790493a607ec902b1ed80`.

## Frozen scope

- Workload: structured TET4, linear static, 5,012,640 true DOF and 9,773,946 elements.
- Input digest: `ff73bc9debd0c8e1ae7355cb6b42e62734c619efa87423e484284878449a55ec`.
- Freeze: `LU2-WP02-FREEZE-bfd1975b012453a3`, digest `bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1`.
- Runtime: PETSc 3.25.1, MPICH 5.0.1, 8 ranks, contiguous partition, AIJ, CG/GAMG.

## Results

WP04 Bronze PASS: the exact workload reached 100% insertion, RHS completion, PC setup, global readiness, all-rank post-ready gather, `COMPLETED`, raw evidence, and clean finalization. The eight rank marker streams contain the complete expected sequence and no exception marker.

WP05 Silver PASS: the existing complete PETSc route was reused without source or configuration changes. Two independent runs converged with 1,243 iterations each. Run 1 total time was 4,427.657 s and Run 2 total time was 4,378.777 s. The configured acceptance checks passed for residual, equilibrium, energy, and finite results. Replay comparison passed with identical workload/configuration/source digests and compatible observables.

The reported performance is evidence for this exact workload and frozen single-host configuration only. It is not a universal 5M, multi-node, GPU, mixed-mesh, nonlinear, restart, or Gold claim.

## Evidence

- Bronze raw: `qualification/0_2_7/wp04_runtime/wp04_corrected_run_a_raw.json`
- Bronze telemetry: `qualification/0_2_7/wp04_runtime/wp04_corrected_run_a_progress.jsonl`
- Bronze rank telemetry: `qualification/0_2_7/wp04_runtime/wp04_corrected_run_a.wp04_5m_progress.rank*.jsonl`
- Silver run 1: `qualification/0_2_7/wp05_runtime/wp05_5m_silver_run1.json`
- Silver run 2: `qualification/0_2_7/wp05_runtime/wp05_5m_silver_run2.json`
- Silver replay: `qualification/0_2_7/wp05_runtime/wp05_5m_silver_replay.json`

Gold was not attempted because no pre-defined distinct 5M workload and additional Gold mechanisms were available in this run. No full regression, new formulation, or source modification occurred during qualification.
