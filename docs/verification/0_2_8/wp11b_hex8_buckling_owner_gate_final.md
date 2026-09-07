# WP11B HEX8 buckling Owner gate

The Owner gate audits the separate WP11B experimental-readiness contract and
campaign. It does not rewrite WP06/WP06B, the Euler `FAIL`, the mesh-convergence
`FAIL`, or the absence of a comparable external oracle.

## Decision

`APPROVE_EXPERIMENTAL`

HEX8 linear buckling is exposed as `EXPERIMENTAL` only within this bounded scope:

- linear eigenvalue buckling from linear-elastic prestress;
- valid bounded HEX8 cantilever solid geometries;
- the explicitly tested clamped solid-block boundary condition;
- the first positive mode;
- exploratory/research use only.

The benchmark was frozen before execution: a clamped rectangular solid block
under uniform end-face dead compression. The campaign passes the declared
prestress/geometric-stiffness, eigenproblem, physical scaling, mode, robustness,
invalid-geometry and two-replay checks. The factors are positive and decrease
with refinement (`41.9397`, `21.5200`, `17.8649`), but that trend is only
characterized; it is not a general convergence claim.

## Limitations

`EXPERIMENTAL` means implemented, reproducible and physically coherent on this
narrow scope, but insufficiently validated for normal or production use. It is
not `QUALIFIED_BOUNDED`. No Euler prediction, general convergence, certification,
imperfection, nonlinear/post-buckling, plasticity, arbitrary-mesh, universal
accuracy, multi-mode, mixed-mesh, HEX8R, SRI, B-bar or hourglass claim is made.

No comparable current external oracle was available. Therefore no external
correlation claim is made and none is required for this experimental status.

## Registry and integrity

The 46 element-analysis records reconcile as follows:

| State | Before WP11B | After WP11B |
| --- | ---: | ---: |
| `QUALIFIED_BOUNDED` | 32 | 32 |
| `EXPERIMENTAL` | 13 | 14 |
| `NOT_QUALIFIED` | 1 | 0 |
| Total | 46 | 46 |

Only `COMB-HEX8-linear_buckling` transitions from `NOT_QUALIFIED` to
`EXPERIMENTAL`. WP06/WP06B evidence remains preserved, no numerical source was
changed, and no 0.2.7 evidence was modified. Any later promotion or scope
expansion requires another Owner gate.

Machine-readable records: [WP11B contract](../../../qualification/0_2_8/wp11b_hex8_buckling_experimental_contract.json),
[campaign evidence](../../../qualification/0_2_8/wp11b_hex8_buckling_experimental_vnv.json),
[updated matrix](../../../qualification/0_2_8/wp11b_hex8_buckling_experimental_matrix.json),
and [this Owner record](../../../qualification/0_2_8/wp11b_hex8_buckling_owner_gate_final.json).
