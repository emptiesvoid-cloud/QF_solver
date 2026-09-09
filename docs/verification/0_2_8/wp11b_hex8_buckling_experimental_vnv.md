---
doc_id: DOC-028-WP11B-VNV-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP11B HEX8 buckling experimental-readiness campaign

WP11B is a separate experimental-readiness record. It does not rewrite WP06 or
WP06B and does not change the 46-combination registry.

## Scope and benchmark

The tested capability is HEX8 linear eigenvalue buckling from a linear-elastic
prestress state, for valid bounded geometries and the first positive mode only.
The frozen benchmark is a rectangular solid cantilever block (`L=4.0`, `b=1.2`,
`h=1.0`) with all DOFs fixed on `x=0` and uniform nodal dead compression on the
`x=L` face (`P=1.0`). The material is homogeneous isotropic linear elasticity
with `E=1000`, `nu=0.3`.

The levels `(2,2,2)`, `(4,4,4)` and `(6,6,6)` are used to characterize the
route. This is a solid-block physical-consistency benchmark, not a pinned Euler
column oracle. The first mode is expected to be lateral and UZ-dominant for the
declared weak-axis geometry.

## Results

| Mesh | Critical factor | Solver residual | Recomputed eigen residual | Mode |
| --- | ---: | ---: | ---: | --- |
| 2×2×2 | 41.9396858064 | 2.15e-13 | 7.64e-14 | UZ |
| 4×4×4 | 21.5199859692 | 3.35e-13 | 5.45e-13 | UZ |
| 6×6×6 | 17.8648777257 | 3.38e-13 | 1.50e-12 | UZ |

All factors are finite and positive; preload residuals are below `1e-8`,
geometric-stiffness symmetry is below `1e-12`, and the lateral mode fraction is
about `0.984`. The refinement trend is positive and decreasing, but adjacent
changes remain about `94.9%` and `20.5%`. It is therefore recorded as
`CHARACTERIZED_ONLY`, not as convergence and not as convergence to Euler.

Physical scaling passes the frozen contract: doubling `E` gives a factor ratio
of `2.00086`, doubling preload gives `0.49957`, doubling length gives a lower
positive factor (`10.03819`), and the moderate perturbation changes the level-4
factor by only `0.0046%`. Invalid orientation is rejected explicitly. No NaN or
infinite eigenvalue was observed.

Two complete reference replays have identical critical factor, mode, residual
and evidence digest. No comparable current Code_Aster or CalculiX result was
available, so `EXTERNAL_ORACLE = NOT_AVAILABLE`; no external correlation is
claimed.

## Decision and limitations

The technical decision is `EXPERIMENTAL_CANDIDATE`, with proposed public status
`EXPERIMENTAL` subject to a separate Owner gate. It is not
`QUALIFIED_BOUNDED`.

The proposed exposure is exploratory/research use only for the declared HEX8
linear eigenvalue buckling route, linear-elastic prestress, valid bounded
cantilever solid blocks, explicitly tested constraints, and first positive mode.
It excludes general Euler prediction, general convergence, certification,
production use, imperfections, nonlinear/post-buckling, plasticity, arbitrary
meshes, universal accuracy, multi-mode/mixed-mesh buckling, HEX8R, SRI, B-bar
and hourglass formulations.

The historical WP06 Euler `FAIL`, WP06 mesh-convergence `FAIL`, and absence of a
comparable external oracle remain unchanged and visible. No numerical source or
0.2.7 evidence was modified.

Machine-readable records: [contract](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp11b_hex8_buckling_experimental_contract.json),
[evidence](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp11b_hex8_buckling_experimental_vnv.json),
and [matrix](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp11b_hex8_buckling_experimental_matrix.json).
