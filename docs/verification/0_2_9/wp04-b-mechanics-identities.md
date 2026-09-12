---
doc_id: DOC-029-WP04-B-001
revision: 0.1
status: executed-targeted-evidence
applicable_version: 0.2.9-development
---

# WP04-B — geometric nonlinear mechanics identities

WP04-B exercises the existing Total-Lagrangian Saint-Venant–Kirchhoff
assemblies for **TET4** and **HEX8**. It adds qualification infrastructure
only. The production element kernels, assembly equations, tolerances and
public maturity records were not changed. WP04 remains at **0/12** until the
later family qualification phases and independent WP04-F closure.

## Frozen scope and independent oracle

The campaign uses `SolidMaterial(E=1000.0, nu=0.30)` and one positively
oriented reference element per family. Affine states are generated from a
known deformation gradient and evaluated independently as

\[
 C=F^T F,\quad E=\tfrac12(C-I),\quad
 S=\lambda\operatorname{tr}(E)I+2\mu E,\quad P=FS,
\]

\[
 \sigma=J^{-1}FSF^T,\qquad
 \psi=\tfrac12\lambda\operatorname{tr}(E)^2+\mu(E:E).
\]

The patch campaign checks every TET4 point and all eight HEX8 Gauss points.
The tested states satisfy `det(F) >= 0.20`, principal stretches in
`[0.75, 1.30]` and `||E||_F <= 0.30`.

## Audited production equations

Writing `G_aJ = dN_a/dX_J` for a reference shape-function gradient and
`C_IJKL = lambda*d_IJ*d_KL + mu*(d_IK*d_JL + d_IL*d_JK)`, the inspected
TET4/HEX8 kernels implement, at each reference integration point,

\[
 f_{int,a i}=\int_{V_0} P_{iJ}G_{aJ}\,dV_0,
\]

\[
 K_{T,a i b k}=\int_{V_0}G_{aJ}
 \left(F_{iI}C_{IJKL}F_{kK}+d_{ik}S_{LJ}\right)G_{bL}\,dV_0.
\]

The first term is the material/constitutive contribution and the second is
the initial-stress geometric contribution. TET4 uses its constant reference
measure and one point; HEX8 uses the eight-point reference Gauss rule. The
same inspected state fields are `F`, `E`, `S`, `sigma = F S F^T/J` and
`psi = 0.5*lambda*tr(E)^2 + mu*(E:E)`. The independent campaign below
recomputes these quantities from `F` rather than calling the production
constitutive routines as an oracle.

## Identity results

| Family | Objectivity max scaled energy | Objectivity max scaled force | Patch max point `F` error | Patch max state error |
| --- | ---: | ---: | ---: | ---: |
| TET4 | `5.926e-32` | `7.145e-16` | `0.000e+00` | `2.132e-14` |
| HEX8 | `5.612e-32` | `2.751e-16` | `1.110e-16` | `2.842e-14` |

Both families pass the four rigid-motion cases: translation, finite rotation,
translation plus rotation, and a nontrivial multi-axis rotation. Strain,
stress and energy are zero at the frozen scaled/absolute limits.

The centered energy-gradient study uses the frozen selected step `h=1e-6`
and records the candidates `1e-4, 3e-5, 1e-5, 3e-6, 1e-6`. The largest
selected-step errors were:

| Family | Max relative `dU/du` error | Max component absolute error |
| --- | ---: | ---: |
| TET4 | `3.730e-09` | `2.267e-09` |
| HEX8 | `6.226e-10` | `8.010e-09` |

The consistent tangent study uses centered internal-force differences at
near-zero, moderate, stretch/shear and structural-loaded states:

| Family | Max Frobenius relative error | Max column relative error | Max symmetry defect |
| --- | ---: | ---: | ---: |
| TET4 | `6.078e-11` | `1.176e-10` | `0.000e+00` |
| HEX8 | `1.171e-10` | `1.506e-10` | `0.000e+00` |

All values are below the frozen WP04-A limits (`1e-6`, `5e-6` and `1e-12`).

## Accepted-state work path

The work observer consumes detached states only from the existing accepted-state
callback, after global commit. The structural demonstrations use a
proportional dead load and trapezoidal integration over accepted states at
12/24/48/96 intervals. Coarse values are retained as refinement evidence; the
frozen gate is applied to the finest path and the 96-vs-48 change.

| Family | 12 error | 24 error | 48 error | 96 error | 96-vs-48 work change |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | `1.546e-06` | `3.866e-07` | `9.664e-08` | `2.416e-08` | `7.248e-08` |
| HEX8 | `3.222e-06` | `8.054e-07` | `2.014e-07` | `5.034e-08` | `1.510e-07` |

The finest error is below `1e-6` and the 96-vs-48 change is below `2e-7` for
both families. The historical WP13-11 value
`1.3963468382007748e-05` remains unchanged in its immutable 0.2.8 record.

Observer checks recorded six accepted snapshots, no rejected-trial snapshot,
and detached snapshot copies. Replaying the TET4 accepted path produced exact
displacement, energy and accepted-state digest equality.

Raw reproducible evidence is stored in:

- `qualification/0_2_9/wp04_b_mechanics_identities.json`
- `qualification/0_2_9/wp04_b_raw.npz`

The JSON records the exact source SHA, environment, thresholds, per-family
metrics, gate decisions and scope limitations. The NPZ contains paths, force
vectors, energies, work histories and analytical/finite-difference tangent
matrices without object arrays.

## Gate status

- G04-01: `PASS_BOUNDED`
- G04-02: `PASS` — TET4 and HEX8 objectivity
- G04-03: `PASS` — independent finite-deformation patch
- G04-04: `PASS` — internal force equals energy gradient
- G04-05: `PASS` — tangent, per-column agreement and symmetry
- G04-08: `PASS` — accepted-path work refinement for both families
- G04-06, G04-07, G04-09: pending WP04-C/D
- G04-10: pending WP04-C
- G04-11: pending WP04-D
- G04-12: pending WP04-E

These results do not qualify mesh convergence, global reaction campaigns,
cross-family convergence, contact, arc-length, J2+geometry or any excluded
formulation. TET4 and HEX8 therefore remain `RESEARCH_ONLY`.

## Validation boundary

The focused WP04-B matrix reports `43 passed`. Existing targeted TET4/HEX8
kernel and geometric-route regressions remain green. Qualification JSON
validation, Ruff, compileall and MkDocs strict are run separately. The full
repository numerical suite is intentionally not run (`FULL_TEST_SUITE_RUN =
NO`).

The next permitted action is Owner review before WP04-C; WP04-B does not start
WP04-C/D/E or WP05.
