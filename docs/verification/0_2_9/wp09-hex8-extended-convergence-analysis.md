# WP09 HEX8 extended convergence analysis

## Scope

This diagnostic extension keeps the HEX8-only bounded configuration unchanged:
25% total reference load, same J2 material, same four load increments, same
corotational strain bound `0.05`, and no threshold relaxation. It adds HEX8
levels 5, 6, 7 and 9 to the already archived isotropic levels 4 and 8.

The historical TET4 route is not executed or modified.

## Fine-mesh results

| Level | Nodes | Elements | DOFs | max displacement | energy | max von Mises | max local strain | force balance | moment balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H4 = 4×4×4 | 125 | 64 | 375 | 1.509184e-02 | 1.364766e-03 | 2.082318e-01 | 2.875461e-02 | 8.262e-11 | 5.838e-11 |
| H5 = 5×5×5 | 216 | 125 | 648 | 1.741178e-02 | 1.622461e-03 | 2.470424e-01 | 3.370675e-02 | 5.776e-11 | 4.083e-11 |
| H6 = 6×6×6 | 343 | 216 | 1029 | 1.909948e-02 | 1.821754e-03 | 2.748382e-01 | 3.734831e-02 | 5.150e-11 | 3.644e-11 |
| H7 = 7×7×7 | 512 | 343 | 1536 | 2.032819e-02 | 1.975004e-03 | 2.952287e-01 | 4.008183e-02 | 4.381e-11 | 3.098e-11 |
| H8 = 8×8×8 | 729 | 512 | 2187 | 2.123035e-02 | 2.093816e-03 | 3.105745e-01 | 4.219400e-02 | 1.490e-07 | 1.053e-07 |
| H9 = 9×9×9 | 1000 | 729 | 3000 | 2.189801e-02 | 2.187237e-03 | 3.224369e-01 | 4.385875e-02 | 1.932e-07 | 1.366e-07 |

All six meshes pass geometric quality. All six solve runs terminate with
`PASS`, four accepted increments and zero rejected increments. The local
strain envelope remains below `0.05`, including H9.

## Consecutive refinement deltas

| Transition | displacement | energy | von Mises | PEEQ |
|---|---:|---:|---:|---:|
| H4→H5 | 13.324% | 15.883% | 15.710% | 14.704% |
| H5→H6 | 8.836% | 10.940% | 10.114% | 9.759% |
| H6→H7 | 6.044% | 7.759% | 6.907% | 6.826% |
| H7→H8 | 4.249% | 5.674% | 4.941% | 5.010% |
| H8→H9 | 3.049% | 4.271% | 3.679% | 3.799% |

The H8→H9 transition satisfies the frozen mesh thresholds for displacement,
energy and von Mises stress. This is the first fine transition that closes
those three comparison gates simultaneously.

## Remaining formal blocker

H9 does not satisfy the frozen equilibrium thresholds:

```text
force balance  = 1.932e-07 > 1e-08
moment balance = 1.366e-07 > 1e-08
free residual  = 8.601e-08 < 1e-07
```

The equilibrium degradation appears at the larger systems (H8/H9), while the
local strain envelope remains valid. It must be diagnosed as a solver or
post-processing accuracy issue before formal requalification; thresholds must
not be loosened to accept it.

## Status

```text
HEX8_FINE_MESH_TREND = IMPROVING
HEX8_H8_H9_MESH_CLOSURE = PASS_FOR_DISPLACEMENT_ENERGY_STRESS
HEX8_H9_EQUILIBRIUM = FAIL_CLOSED
HEX8_FORMAL_REQUALIFICATION = NOT_READY
WP09_FORMAL_POINTS = 0/8
```

The next technical step is a read-only forensic decomposition of the H8/H9
force and moment residuals, followed—only if the source of the degradation is
identified—by a separately reviewed numerical-accuracy remediation. No
threshold change, production-mechanics change, merge, or push is justified by
this diagnostic series.

## Evidence

- H5/H6: `qualification/0_2_9/wp09_hex8_extended_refinement_r1/`
- H7: `qualification/0_2_9/wp09_hex8_extended_refinement_r2/`
- H9: `qualification/0_2_9/wp09_hex8_extended_refinement_r3/`
- Previous H4 evidence: `qualification/0_2_9/wp09_hex8_refinement_r1/`
