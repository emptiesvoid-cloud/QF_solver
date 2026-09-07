# WP11 mixed large-scale evidence contract

This contract is frozen before the WP11 measurements. It covers performance and
reproducibility evidence for the already bounded mixed `linear_static` workflow,
not a new numerical qualification.

## Declared scope

The campaign uses repeated conforming TET4/WEDGE6/HEX8 chains. Each chain has
one TET4, one WEDGE6 and one HEX8, with shared triangular and quadrilateral
interfaces respectively. The mandatory model has 9,091 independent chains,
100,001 nodes, 300,003 translational DOFs, and 27,273 elements (9,091 of each
family). The disconnected repetition is intentional scale evidence and limits
the claim: it is not a claim for an arbitrary connected industrial mesh.

The model is small-strain linear isotropic elasticity (`E=210e9`, `nu=0.3`,
`rho=7800`, SI units), with all `x=0` DOFs fixed and a unit total Z load per
chain distributed on free top nodes. Only conforming nodal interfaces are in
scope. PYRAMID5, HEX8-SRI, nonconforming interfaces, modal/dynamic/nonlinear
analyses and precision qualification are excluded.

The 66-DOF two-chain model is the baseline. A 999,999-DOF target and a
2,999,997-DOF stretch target are recorded as optional non-blockers; they are not
reported as measured unless executed in the declared environment.

## Gates

Before the large run, the baseline must solve successfully. The mandatory run
must have at least 300,000 DOFs, nonzero and balanced contributions from all
three element families, finite displacements, relative solver residual,
global-force closure, global-moment closure and energy identity no greater than
`1e-8`, and two exact physics replays. Runtime, peak memory, sparse `nnz`,
solver iterations and environment are recorded as evidence, not as universal
thresholds.

The exact replay digest covers the generated input, displacement vector,
iterations, residual, equilibrium and energy. Timing and memory are excluded
from that digest because they are environment-dependent.

The iterative backend is SciPy CG with `assume_spd=true`. This is an explicit
solver-policy assumption, justified here by homogeneous small-strain isotropic
elasticity and complete per-chain Dirichlet constraints; it is not a new
formulation or an accuracy claim.

## Claim boundary

The only permitted public wording is: “Recorded large-scale mixed
TET4/WEDGE6/HEX8 evidence for this specific linear-static route and
environment.” No general scalability, accuracy, production, or connected-mesh
performance claim is created.
