# Mechanics and formulation index

**Scope:** formulation orientation for code navigation.
**Revision:** 2026-10-25.
Exact equations, signs, units, tolerances and exclusions are controlled by each route’s release-specific scientific contract.

## Linear structural system

For a supported linear static route, the assembled constrained system is represented as K u = f. K is the structural stiffness operator, u the displacement vector in the model’s DOF convention, and f the assembled load vector. Boundary conditions and MPC/RBE treatment alter the solved system. See [assembly](../../src/solveur/core/assembly/assembler.py), [constraints](../../src/solveur/core/constraints.py), and the applicable analysis contract.

Classical undamped modal analysis solves the generalized eigenproblem K φ = ω² M φ for the selected system. Frequency conversion, normalization, eigensolver policy, and handling of constrained or massless directions must be checked in [modal.py](../../src/solveur/core/analyses/modal.py) and its contract.

## Dynamic operators and modal reduction

The prepared dynamic route binds physical stiffness, mass, and applicable damping operators to model identity. [Excitation channels](../../src/solveur/core/analyses/excitation_channels.py) bind applied loads and phases to that system. A modal basis is a projection space, not a new physical model. In an ordinary real basis representation, reduced operators have the form K_r = Φᵀ K Φ and M_r = Φᵀ M Φ; exact normalization and any symmetrization/fallback behavior are defined by the [WP04 contract](../../qualification/0_2_12/wp04_modal_basis_damping_contract.json) and [basis source](../../src/solveur/core/analyses/modal_basis.py).

Reduced harmonic response and modal Newmark explicitly consume this prepared/reduced representation. They are distinct from direct harmonic response and direct Newmark. Truncation diagnostics, damping, excitation convention, residual flexibility, stress recovery, and checkpoints have route-specific contracts. WP-D01 remains INCONCLUSIVE; WP-D02 remains CLOSED_BOUNDED.

## Harmonic response

The direct harmonic solver assembles real K, M, and Rayleigh damping C, then forms a complex dynamic stiffness for each frequency and solves for complex response. In the current implementation, the algebra is constructed as K + iωC - ω²M; frequency is converted from Hz to angular frequency. Load phase and sign conventions remain governed by the applicable API and scientific contract. Do not transfer direct-route details to modal superposition without checking its contract. See [harmonic solver](../../src/solveur/core/analyses/harmonic.py).

## Transient response

The repository contains a [direct transient Newmark route](../../src/solveur/core/analyses/dynamic.py) and an explicit [modal-Newmark route](../../src/solveur/core/analyses/modal_newmark.py). Both use time histories, but their state spaces differ: full physical DOFs for the direct route, modal coordinates for the reduced route. Time step, Newmark parameters, initial conditions, energy diagnostics, history storage and checkpoint behavior are controlled by route-specific settings and contracts.

Uniform base acceleration is currently accepted by the [router](../../src/solveur/core/router.py) only for harmonic modal-superposition and transient modal-Newmark. This is a routing restriction, not a claim that every excitation configuration is physically equivalent. See the [WP07 contract](../../qualification/0_2_12/wp07_uniform_base_acceleration_contract.json).

## Stress and strain

Element routines and post-processors compute formulation-specific strains and stresses. Coordinate systems, shell section conventions, stress measures, extrapolation/recovery and material axes vary by element and route. Use the relevant element/material source and contract. Do not treat one recovered stress field as a universal stress definition.

## Nonlinear material and geometry

J2 plasticity, total-Lagrangian kinematics, and corotational formulations represent different modeling choices. Internal variables and constitutive tangents interact with the global Newton residual and tangent; a point-material test checks only that material-level path. Global equilibrium, state commit/rollback, line search, adaptive steps, and checkpoint restore require their own evidence.

Finite-strain and Hencky foundations under WP-E01 are experimental with bounded certificates. The current records do not establish a general large-deformation plasticity workflow. Consult [nonlinear overview](../mechanics/nonlinear-overview.md) and the WP08–WP10/WP-E01 contracts and reports.

## Contact

Contact routes define a gap/penetration measure, normal and optionally tangential contributions, search strategy, and equilibrium coupling. Penalty, stick/slip, and finite-sliding behavior must be distinguished. WP-C01 retains a negative historical closure with remediation open; WP-C02’s bounded closure is only AR/N03. Do not infer general updated search, arbitrary sliding, or mesh-independent frictional results.

## Rotating modal and Campbell

The inherited rotating model uses the signed-speed equation M q̈ + Ω G q̇ + K q = 0, with its frozen global axis and sign convention, and solves the associated dense quadratic eigenvalue problem (λ²M + λΩG + K)φ = 0. G is built from the accepted centered rigid disks, not distributed shaft gyroscopy. Modes are complex. See [gyro disk assembly](../../src/solveur/core/assembly/rotating_disk_gyro.py), [rotating modal](../../src/solveur/core/analyses/rotating_modal.py), and the [WP05 contract](../../qualification/0_2_11/wp05_gyroscopic_contract.json).

Campbell analysis evaluates a strictly increasing explicit list of signed speeds and associates complex modes using the contracted complex MAC and assignment rules. Degenerate subspaces, missing branches, lineage and ambiguity are represented. The historical ambiguity at 100 rad/s is retained; it must not be converted to a forced-response or operational safety conclusion. See [Campbell implementation](../../src/solveur/core/analyses/campbell.py) and the [WP06 contract](../../qualification/0_2_11/wp06_campbell_contract.json).

For exact hypotheses, geometry restrictions, dimensions, normalization, tolerances and refusals, use [rotating-modal](../mechanics/rotating-modal.md), [Campbell](../mechanics/campbell.md), and qualification/0_2_11/wp05_gyroscopic_contract.json / wp06_campbell_contract.json.

## Units and frames

The code does not provide a universal unit conversion layer. A model’s values must be internally consistent with the units expected by its inputs and contracts. Vector directions, material axes, shell local frames, global rotating axes, and sign rules are route-dependent. When the repository contract does not resolve a convention, do not infer one from a field name; inspect source or record the ambiguity.
