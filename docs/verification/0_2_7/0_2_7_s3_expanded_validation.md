# S3 Expanded Validation Matrix

S3 is a zero-weight release pre-gate at the 0.2.7 HEAD. Its purpose is to consolidate high-value validation coverage before WP09 and expose gaps without changing numerical formulations or promoting maturity.

The controlled source of truth is `qualification/0_2_7/s3_validation_matrix.json`. The 24 S3-added records distinguish reused controlled evidence, targeted replay evidence, expected-failure evidence, planned coverage and non-comparable external observations. Reused evidence is not presented as a new solver execution.

The matrix covers element families TET4, TET10, HEX8, HEX20 and WEDGE6, plus linear static, modal, buckling, dynamics, nonlinear/J2, contact and fail-closed preflight routes. It records displacement, reaction/equilibrium, energy, residual, frequency/MAC and finite-output invariants where applicable.

No capability is promoted. HEX8 next-generation formulations, mixed meshes, WEDGE15, PYRAMID5, finite-kinematic J2 and broad dynamics claims remain deferred or bounded. Code_Aster evidence is used only within its documented WEDGE6 comparability boundary; CalculiX observations remain `NOT_COMPARABLE` where reactions or energy do not share an equivalent contract.

The C3 10M result remains a configuration- and hardware-bound engineering observation. Exact timing or speedup is not a universal public qualification claim.
