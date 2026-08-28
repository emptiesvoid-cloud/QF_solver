# Architecture Audit

The machine-readable authority is `qualification/0_2_6/architecture_audit.json`.
This audit is descriptive; G04 moves implementation ownership without changing numerical bodies or public entry points.

- Source SHA captured: `6b77fd7b318dab0fea4a371c3567dea3cdc19b47`
- Source dirty at capture: `False`
- Python modules inspected: 428
- Flat verification modules: 188
- Core implementation packages: analyses, assembly, nonlinear, solvers
- Core compatibility facades: 30

## Large Modules

| Module | Lines | Audit threshold |
| --- | ---: | --- |
| `src/solveur/verification/mitc4_modal_extended.py` | 697 | over_500 |
| `src/solveur/verification/maturity_promotion.py` | 694 | over_500 |
| `src/solveur/verification/release_vv.py` | 687 | over_500 |
| `src/solveur/core/audit.py` | 684 | over_500 |
| `src/solveur/core/analyses/modal.py` | 683 | over_500 |
| `src/solveur/core/analyses/dynamic.py` | 674 | over_500 |
| `src/solveur/mesh/validation.py` | 674 | over_500 |
| `src/solveur/verification/code_aster_contact_additional.py` | 662 | over_500 |
| `src/solveur/verification/nonlinear_failure_campaign.py` | 643 | over_500 |
| `src/solveur/verification/code_aster_tet10_dynamic.py` | 640 | over_500 |
| `src/solveur/verification/campaign.py` | 632 | over_500 |
| `src/solveur/verification/robustness_contact.py` | 618 | over_500 |
| `src/solveur/mesh/gmsh_importer.py` | 613 | over_500 |
| `src/solveur/verification/mitc4_campaign.py` | 605 | over_500 |
| `src/solveur/core/assembly/assembler.py` | 591 | over_500 |
| `src/solveur/verification/orthotropic_singularity_vnv.py` | 591 | over_500 |
| `src/solveur/verification/robustness_mesh.py` | 589 | over_500 |
| `src/solveur/api/public.py` | 565 | over_500 |
| `src/solveur/verification/j2_material.py` | 556 | over_500 |
| `src/solveur/verification/tet10_structural_convergence.py` | 552 | over_500 |
| `src/solveur/core/nonlinear/arc_length.py` | 529 | over_500 |
| `src/solveur/post/stress.py` | 528 | over_500 |
| `src/solveur/large/solver.py` | 525 | over_500 |
| `src/solveur/verification/code_aster_tl_structural.py` | 524 | over_500 |
| `src/solveur/verification/mitc4_harmonic_nafems.py` | 521 | over_500 |
| `src/solveur/verification/vnv_torsion_import.py` | 516 | over_500 |
| `src/solveur/verification/mitc4_newmark_operational.py` | 508 | over_500 |
| `src/solveur/verification/robustness_geometric.py` | 505 | over_500 |

## Large Historical Artifacts

These are retained for provenance. The 0.2.6 policy prevents new equivalents from entering normal source history.

| Artifact | Bytes |
| --- | ---: |
| `qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/4m_r2/displacements.bin` | 32823144 |
| `qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/4m_r4/displacements.bin` | 32823144 |
| `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/graph_2m_r2/displacements.bin` | 16355328 |
| `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/graph_2m_r4/displacements.bin` | 16355328 |
| `qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/2m_r2/displacements.bin` | 16355328 |
| `qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/2m_r4/displacements.bin` | 16355328 |
| `docs/generated/benchmarks/BM-SOL-TET4-TORSION-001/h1.json` | 5014189 |
| `docs/assets/reviews/revue_mecanique_tet10_lineaire.pdf` | 3598799 |
| `docs/assets/reviews/owner_review_mitc3_statique.pdf` | 3294734 |
| `docs/assets/reviews/owner_review_contraintes_singulieres.pdf` | 2499548 |

## Findings

- Verification contains many flat, solver-specific modules and duplicated campaign entrypoints.
- Core assembly, solver, analysis and nonlinear implementations are grouped under explicit subpackages; flat core imports remain compatibility facades.
- Historical large benchmark displacement blobs exceed the proposed normal artifact size policy and must be preserved, not rewritten.
