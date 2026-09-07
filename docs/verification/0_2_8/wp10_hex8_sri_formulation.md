---
title: "WP10 HEX8 selective reduced integration formulation"
status: "PREDECLARED_RESEARCH_GATE"
---

# WP10 HEX8 selective reduced integration formulation

WP10 studies a separate research element. The qualified HEX8 implementation
and all existing analysis routes remain unchanged.

## Selected formulation

The reference interpolation is the existing trilinear HEX8 interpolation and
the existing Jacobian/strain-displacement operator. For isotropic linear
elasticity, the constitutive matrix is split as

\[
 C = C_{dev} + C_{vol},\qquad
 C_{vol}=K\,m m^T,\qquad m=(1,1,1,0,0,0)^T,
\]

where `K = E/(3(1-2ν))` and `C_dev = C-C_vol` in the engineering-Voigt
convention used by QF Solver. The SRI stiffness is

\[
 K_{SRI}=\sum_{2\times2\times2} w_q\det J_q B_q^T C_{dev}B_q
       +w_0\det J_0 B_0^T C_{vol}B_0.
\]

The deviatoric contribution uses the eight standard Gauss points. The
volumetric contribution uses the element centre only. This choice targets
volumetric locking while retaining full deviatoric/shear integration; no
hourglass control or production reduced-integration HEX8 variant is added.

## Risks and boundaries

The centre-only volumetric term can alter stiffness and must not be treated as
a general accuracy improvement. The gate therefore checks symmetry, six rigid
body modes, numerical rank, affine and constant-strain reproduction, energy,
distortion and invalid geometry. A rank loss, zero-energy mode, or materially
unstable distorted response rejects the candidate.

The candidate is internal and isotropic linear-static only. It is not added to
the public element registry, compatibility descriptor, standard HEX8 class,
modal/dynamic routes, nonlinear routes or release maturity records.
