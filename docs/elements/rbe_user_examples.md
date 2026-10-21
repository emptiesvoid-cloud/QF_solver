# RBE2/RBE3 bounded linear-static examples

These examples are reproducible input decks for the Owner-approved bounded
linear-static scope. They are analytical examples, not external solver
correlations. The example files have not been run through the public CLI in
this integration campaign. The seven targeted test modules passed on the
integrated source revision; see `qualification/0_2_12/wp13_rbe_integration_report.md`.

## RBE2 rigid offset with a combined wrench

Input: [`examples/rbe2_rigid_offset_combined_wrench.json`](../../examples/rbe2_rigid_offset_combined_wrench.json).

The master is at `(0,0,0)` and the slave at `(2,1,0) m`. The master has a
`1000 N/m` `UX` spring, a `1000 N m/rad` `RZ` spring, and fixed `UY`, `UZ`,
`RX`, and `RY`. The slave receives `(FX,FY)=(10,20) N`; the master receives
`MZ=5 N m`. The kinematic law is
`u_slave = u_master + theta_master x (x_slave - x_master)`.

The force at the slave contributes `Mz = 2*20 - 1*10 = 30 N m` about the
master. Including the applied master moment gives `35 N m`. Therefore the
expected response is:

| Quantity | Expected value |
| --- | ---: |
| Master `UX` | `0.010 m` |
| Master `RZ` | `0.035 rad` |
| Slave `UX` | `-0.025 m` |
| Slave `UY` | `0.070 m` |
| Master `UY` support reaction | `-20 N` |
| Master `UX` spring reaction | `-10 N` |
| Master `RZ` spring reaction | `-35 N m` |

Equilibrium checks: applied resultant force `(10,20,0) N` is balanced by
support reactions `(-10,-20,0) N`; applied moment about the master is
`35 N m`, balanced by the `RZ` spring reaction `-35 N m`. These values follow
from the exact rigid-arm equation and the two scalar spring equilibrium
equations; they are not a Code_Aster result.

Scope: one rigid arm, small displacement, linear statics and the declared
spring/support set. The example does not demonstrate arbitrary element-family
combinations or `tie_rotations` behavior.

## RBE3 unequal positive weights on distributed supports

Input: [`examples/rbe3_unequal_weight_projection.json`](../../examples/rbe3_unequal_weight_projection.json).

The reference is at the origin. Six independent translation-only support
nodes are placed at `+/-1 m` on X, `+/-2 m` on Y and `+/-3 m` on Z. Their
positive weights are respectively `1`, `2` and `3` on each opposite pair.
Each independent translation has a `1000 N/m` spring. The reference is loaded
with `F=(120,-60,90) N` and `M=(70,112,-36) N m`. The pair symmetry makes the
weighted translation/rotation blocks uncoupled. Direct evaluation of the
weighted rigid-body least-squares projection gives

`sum(w)=12`, `J=diag(70,56,18) m^2`, and
`J2=diag(194,164,34) m^2`, where `J=sum(w)(|r|^2 I-r r^T)` and
`J2=sum(w^2)(|r|^2 I-r r^T)`.

The independent nodal load reference is
`f_i = w_i [F/12 + beta x r_i]`, with
`beta=J^-1 M=(1,2,-2) N/m`. This produces:

| Node | Position | Weight | Expected force `(Fx,Fy,Fz)` N | Expected displacement `(ux,uy,uz)` m |
| --- | --- | ---: | ---: | ---: |
| 1 | `(1,0,0)` | 1 | `(10,-7,5.5)` | `(0.010,-0.007,0.0055)` |
| 2 | `(-1,0,0)` | 1 | `(10,-3,9.5)` | `(0.010,-0.003,0.0095)` |
| 3 | `(0,2,0)` | 2 | `(28,-10,19)` | `(0.028,-0.010,0.019)` |
| 4 | `(0,-2,0)` | 2 | `(12,-10,11)` | `(0.012,-0.010,0.011)` |
| 5 | `(0,0,3)` | 3 | `(48,-24,22.5)` | `(0.048,-0.024,0.0225)` |
| 6 | `(0,0,-3)` | 3 | `(12,-6,22.5)` | `(0.012,-0.006,0.0225)` |

The expected reference translation is
`(0.0233333333,-0.0116666667,0.0175) m`. The expected reference rotation,
computed as `J^-1 J2 J^-1 M / 1000`, is approximately
`(0.00277142857,0.00585714286,-0.00377777778) rad`.

Equilibrium checks: nodal forces sum to `(120,-60,90) N`; their moments about
the origin sum to `(70,112,-36) N m`. The spring reactions are the opposite
nodal forces, so total force and moment close to zero. The values use the
weighted least-squares map and virtual-work transpose `H^T`; they are not an
external-solver result.

Scope: `rigid_body_projection`, six positive weights, full-rank 3D support
geometry, fixed geometry and linear springs. This is not a general Nastran
RBE3 card implementation and does not establish nonlinear, dynamic, contact,
or arbitrary multi-MPC compatibility.
