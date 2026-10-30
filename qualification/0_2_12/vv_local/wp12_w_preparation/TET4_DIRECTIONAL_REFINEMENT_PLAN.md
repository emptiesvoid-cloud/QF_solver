# TET4 directional refinement plan

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

## Question and baseline

After V2 has been reviewed, determine whether the observed H3 cantilever stiffness changes more under longitudinal refinement or under a uniform transverse cross-section refinement, with the H3 model as the common baseline.

Keep the historical baseline `H3: nx=8, ny=4, nz=4`, length `L=4 m`, square section `0.4×0.4 m`, isotropic `E=70 GPa`, `nu=0.3`, and terminal `Fz=-1 N`. Preserve the exact element ordering, support/load mapping, material, units, solver backend/method, numerical tolerances, thread settings and postprocessing definitions used by the H3 case. The prior WP12-T report states that charges, moments, supports, volumes and meshes were checked; these checks should be recorded in the future manifest rather than inferred from the mesh dimensions alone.

## Requested candidates

| Case | Grid | TET4 count | Nodes | Total DOFs | Change from H3 |
|---|---|---:|---:|---:|---|
| H3 baseline | 8×4×4 | 768 | 225 | 675 | reference |
| W1 longitudinal | 16×4×4 | 1,536 | 425 | 1,275 | double `nx` only |
| W2 transverse-uniform | 8×8×8 | 3,072 | 729 | 2,187 | double both `ny` and `nz` under one isotropic transverse-refinement rule |

W1 changes only the longitudinal count. W2 is one *design factor* if `ny=nz` is treated as a coupled transverse rule, but it changes two coordinate-axis counts. It cannot distinguish y- from z-direction sensitivity. If individual transverse-axis attribution is necessary, ask the Owner later whether to add `W2-Y: 8×8×4` and/or `W2-Z: 8×4×8`; neither is authorized or included in the current W proposal.

## Minimal sequence and stopping rule

1. Review the V2 payload and its exact matrix-free/direct comparison, map checks, archived residuals, and limitations. Stop and resolve any unexplained V2 FAIL/INCONCLUSIVE before W planning is converted into execution.
2. Freeze H3 provenance and exact output definitions. Do not regenerate or overwrite the historical baseline.
3. If the Owner authorizes W, run W1 and W2 sequentially, one case per isolated evidence directory. Keep all mechanics, loading, solver route, thread settings and acceptance definitions fixed. Stop at the first unexplained anomaly.
4. Compare each signed mean-tip and load-conjugate response with H3. Use the direction-of-change and mesh-normalized spatial resolution as observed diagnostics; do not declare convergence from two directional candidates.
5. Decide from the results whether a y-only/z-only experiment, a controlled mesh sequence, TET10 comparison or independent 3D reference is warranted. Defer them unless results demonstrate a need.

No exact W pytest nodeid, wrapper or execution manifest is created here. A future W authorization must bind those artifacts after their source, direct/indirect residual method and exact candidate models are reviewed.

## Interpretation

The intended comparison is discriminating but bounded: W1 estimates sensitivity to longitudinal refinement; W2 estimates sensitivity to coupled, uniform transverse refinement. Because W2 has four times as many elements as H3 and W1 has twice as many, the difference in response is not a cost-normalized convergence rate. A response moving toward the beam estimate is not by itself proof of FEM convergence or 3D physical accuracy. Do not label the current 66.69% H3-to-beam discrepancy as shear locking without formulation-specific evidence.
