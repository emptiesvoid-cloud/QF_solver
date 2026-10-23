# WP-E01-M — 3D logarithmic strain and experimental Hencky elasticity

**Disposition:** source implementation and analytical test preparation complete; numerical tests were not collected or run. This is an isolated experimental capability, not solver or material-route qualification.

## Scope and compatibility

The implementation is confined to `src/solveur/materials/finite_strain_hencky.py`. It is not exported from `solveur.materials`, registered in a material factory, wired to `NonlinearAssemblyPlan`, or passed to the nonlinear solver. Existing small-strain J2, total-Lagrangian StVK, Neo-Hookean and public API behavior are unchanged. The new material does not satisfy the existing `SolidMaterial` or `ConstitutiveModel` interfaces because its finite-strain algorithmic tangent is not implemented.

Existing total-Lagrangian routes use reference gradients, (F=I+\nabla_Xu), Green–Lagrange strain, PK2 stress, PK1 virtual work, and a consistent tangent. StVK provides these data in the existing TET4/HEX8 routes. The material-point Neo-Hookean implementation also returns PK2/PK1/Cauchy stress and exact tangents. The new Hencky law therefore shares the stress-measure boundary but deliberately does not enter dispatch until its derivative is implemented and independently checked.

## Kinematics and admissibility

For a real finite (3\times3) deformation gradient,

\[
C=F^TF=Q\,\mathrm{diag}(c_i)Q^T,\qquad
E_H=\tfrac12\log C=Q\,\mathrm{diag}(\tfrac12\log c_i)Q^T.
\]

The implementation uses `numpy.linalg.eigh` on the symmetrized (C). Principal stretches are (\sqrt{c_i}), and principal logarithmic strains are (\tfrac12\log c_i=\log\lambda_i), ordered from smallest to largest. No complex matrix logarithm or eigenvalue clipping is used. Output tensors are symmetric and returned arrays are read-only.

The input is refused unless it is finite, real, orientation-preserving, has representable (J=\det F>0), and produces finite (C). A computed (C) must have positive eigenvalues satisfying

\[
c_{\min}>64\,\epsilon_{64}\,c_{\max}.
\]

This relative float64 spectral-resolution limit is a proposed numerical refusal condition, not a physical minimum stretch or (J_{\min}). It fails closed when the logarithm cannot be resolved at the working precision. The law also rejects nonfinite response fields rather than clipping or returning them.

For element helper geometry, TET4 checks positive orientation and dimensionless scaled signed volume above (64\epsilon_{64}); HEX8 checks positive dimensionless reference Jacobian determinants above that value at each of the existing eight quadrature points. These checks are local to the new helpers. HEX8 sampling does not prove positivity between quadrature points.

## Hencky energy and stress conjugacy

The experimental law uses positive shear modulus \(\mu\) and bulk modulus \(\kappa\), both in Pa:

\[
W=\mu\,\mathrm{dev}(E_H):\mathrm{dev}(E_H)
 +\frac{\kappa}{2}\,[\mathrm{tr}(E_H)]^2.
\]

Energy density is Pa (equivalently J/m³). Its stress conjugate to (E_H) is

\[
M_H=\frac{\partial W}{\partial E_H}
 =2\mu\,\mathrm{dev}(E_H)+\kappa\,\mathrm{tr}(E_H)I.
\]

This tensor is **not** passed directly as PK2. Since (E_H=\tfrac12\log C),

\[
dW=\tfrac12 M_H:D\log_C[dC]
 =\tfrac12 D\log_C[M_H]:dC
 =D\log_C[M_H]:dE_G,
\]

where the Fréchet derivative of log on SPD tensors is self-adjoint and (dC=2dE_G). Thus the stress conjugate to Green–Lagrange strain is

\[
S=D\log_C[M_H].
\]

In the eigenbasis of (C), this uses the Loewner factors

\[
L_{ii}=1/c_i,\qquad
L_{ij}=\frac{\log c_i-\log c_j}{c_i-c_j},
\]

with the repeated-eigenvalue limit (1/c_i). The implementation evaluates the off-diagonal quotient using `log1p((c_i-c_j)/c_j)/(c_i-c_j)` for stability. It then returns (P=FS) and (\sigma=PF^T/J). At (F=I), (S=M_H). Proper left rotations leave (C,E_H,W,M_H,S) unchanged and rotate (P,\sigma) as their spatial measures require. A pure proper rotation has zero strain, stress, and energy up to floating-point roundoff.

For (\mu>0,\kappa>0) and admissible (F), the stored energy is nonnegative and vanishes at proper rotations. This does not establish global rank-one convexity, strong ellipticity, or physical suitability for arbitrary large distortions. No tangent is returned: `tangent_status` is `NOT_IMPLEMENTED`.

## TET4/HEX8 experimental boundary

`tet4_deformation_gradients` returns one (F), shape `(1, 3, 3)`, from the existing TET4 shape-gradient node order. `hex8_deformation_gradients` returns eight (F) tensors, shape `(8, 3, 3)`, at the existing 2×2×2 Gauss points and node order. Both use (F=I+\sum_a u_a\otimes\nabla_XN_a) and reject invalid reference geometry or inadmissible (F).

The isolated force-only adapters integrate

\[
f_{ai}^{\mathrm{int}}=\int_{\Omega_0}P_{iJ}N_{a,J}\,dV_0.
\]

TET4 has constant gradients and one material point; HEX8 uses the existing eight-point quadrature. Forces are in N when moduli are Pa and coordinates are m. They do not form a tangent, scatter into a global operator, apply external forces/constraints, commit material state, or enter production routes. No integrated FEM V&V is claimed.

## Prepared analytical verification

`tests/unit/test_wp_e01m_hencky_material_point.py` is prepared and hash-bound as `NUMERICAL_UNIT`; it is **not collected or executed**. Static inventory is **23 test functions and 36 parametrized cases**:

| Coverage | Cases | Independent reference or observable |
|---|---:|---|
| Identity and proper rigid rotations | 3 | (C=I), zero energy/stress, roundoff-scale objectivity |
| Uniaxial, volumetric, isochoric, and simple shear | 4 | Closed-form principal logarithmic strains, energy, and uniaxial PK2 |
| Combined left rotation and stretch | 1 | Invariant reference measures and rotated spatial stresses |
| Infinitesimal-strain limit | 3 | (E_H=\epsilon\,\mathrm{sym}(H)+O(\epsilon^2)) across three amplitudes |
| Repeated and nearly repeated stretches | 2 | Repeated-eigenvalue limit and finite response |
| Invalid (F) and invalid moduli | 9 | Singular, inverted, unresolved positive spectrum, nonfinite/complex (F), nonpositive/nonfinite moduli |
| Principal reconstruction and energy definition | 2 | (\exp(2E_H)=C) and direct evaluation of the stated (W) |
| PK1 energy directional derivative | 3 | Independent chain-rule identity (dW=P:dF), centered material-point difference |
| Stress transformations and tangent refusal | 2 | (P=FS), (\sigma=PF^T/J), symmetric Cauchy stress, explicit unsupported tangent |
| TET4/HEX8 affine kinematics | 2 | Exact constant (F) for affine nodal displacement |
| TET4/HEX8 force-only adapters | 2 | Uniform PK1 TET4 reference and exact unit-cube integral (\int\nabla N_a,dV_0=\mathrm{signs}_a/4) |
| Invalid reference element geometry | 3 | Inverted/degenerate TET4 and inverted HEX8 refusal |

The finite-difference stress-energy tolerance (`2e-7` relative in the prepared source), rigid-motion roundoff allowances, and geometric/spectral `64 eps` refusals are candidate software-test values only. None is an Owner-approved scientific acceptance gate. No material tangent test is included because no tangent exists.

## Safety and static verification

The test is registered as `NUMERICAL_UNIT`. The import closure includes pytest and NumPy, the `solveur` and `solveur.materials` package initializers, and the Python material modules imported by `solveur.materials.__init__` (beam, composite, failure, laminate, and orthotropic). The TET4/HEX8 adapters lazily import the existing element classes; those modules import the constitutive contract, geometry helpers, and J2 state validator. The selected test path calls only material response, shape-gradient/quadrature, and local force algebra. Static inspection found no Gmsh/native library initialization, material factory dispatch, global assembly, public solve, nonlinear Newton, worker, test-side subprocess, network, or intentional file-write path. The root pytest guard and `tests/conftest.py` remain active. No pytest collection was performed.

Static checks performed: `python -m py_compile src/solveur/materials/finite_strain_hencky.py tests/unit/test_wp_e01m_hencky_material_point.py`; `python -m ruff check` on those files and `tests/conftest.py`; and `git diff --check`. All passed. A source-AST inventory gives 23 test functions and 36 parametrized cases; this is not an observed pytest collection count or node inventory. Numerical tests, pytest collection, FEM, solver, and backend were not run.

The prepared execution manifest is `qualification/0_2_12/wp_e01_m_hencky_execution_manifest_2026-10-21.json`. It pins the target, registry, reviewed source/import files, static inventory, and child commands. It explicitly records that execution and collection are unauthorized, and that the existing WP-E01-F supervisor is hard-bound to another worktree and test and cannot be reused unchanged. A future Owner GO must bind a fixed-target Windows Job Object supervisor to this exact identity and verify its resource enforcement before collection. The manifest's proposed environment is Python 3.13.1, pytest 8.4.1, one BLAS thread, one child, and candidate 256 MiB process/job commitment and 120-second wall limits; these limits were not enforced or measured in this source-only mandate.

### Independent read-only review

A separate reviewer inspected the formulation, implementation, and proposed references at the source baseline. No P0/P1 blocker was found. The reviewer agreed that the (M_H\to S\to P\to\sigma) transformations, repeated-eigenvalue Loewner limit, and element force conventions are mathematically consistent. It confirmed that the thresholds are described as proposed numerical refusal/test values, not physical admissibility criteria. The reviewer identified one P2 limitation: the PK1 energy directional-derivative test uses a single centered-difference step and is a derivative self-consistency check, not a fully independent oracle. Its step and error normalization remain proposed and have not been validated. This limitation is retained; no test threshold was changed and no numerical evidence is claimed.

### Exact preparation identities

| File | SHA-256 |
|---|---|
| `src/solveur/materials/finite_strain_hencky.py` | `B318DAD553073F848B96528C61589AB2015C1EB1DD8FA52CB0BD52D13B09EAB2` |
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `55E8CB65C77F724799B40415451759DC8A99F980194E95C4CCB2EACFADEC6E83` |
| `tests/conftest.py` | `8B90D1556F7F611759378FE051BCA716905832ECB2731E38D111D001A2500261` |
| `qualification/0_2_12/wp_e01_m_hencky_execution_manifest_2026-10-21.json` | `42CA471BA4AE6379EFA819573ED1C19F743754F48B4D21213BBC2673FDDE75ED` |

## Finite-strain plasticity boundary

Small-strain J2 remains unchanged. A future finite-strain J2 design must separately define a multiplicative split (F=F_eF_p), plastic evolution on a specified intermediate configuration, an elastic logarithmic strain and its work-conjugate stress, yield function and flow rule, hardening/internal variables, plastic dissipation, objective stress update, a consistent algorithmic tangent in the element’s PK1/PK2 convention, and transactional commit/rollback. It also needs branch-aware point and element verification. None of that is implemented or qualified here.

## Next Owner decision

Authorize one exact-path collection and bounded execution of `tests/unit/test_wp_e01m_hencky_material_point.py` only after reviewing the final test, registry, source and manifest hashes. Any force-only element tests remain isolated algebraic checks and do not authorize global assembly, Newton, native FEM, production registration, tangent claims, finite-strain J2, or scientific promotion.
