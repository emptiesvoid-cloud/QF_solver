# Capability Inventory

| Capability | 0.2.5 maturity | 0.2.6 intent | Claim boundary |
| --- | --- | --- | --- |
| `small_strain_j2` | QUALIFIED_BOUNDED | maturity_extension | No finite-strain J2 claim. |
| `total_lagrangian_elasticity` | QUALIFIED_BOUNDED | bounded_refinement | TET4/HEX8 bounded domain. |
| `linear_buckling` | QUALIFIED_BOUNDED | maturity_extension | No nonlinear collapse claim. |
| `frictionless_contact` | QUALIFIED_BOUNDED | maturity_extension | No general mortar or arbitrary large sliding claim. |
| `arc_length` | EXPERIMENTAL | review_only | Promotion requires independent reproducible reference. |
| `coupled_nonlinear` | EXPERIMENTAL | review_only | Finite-kinematic J2 remains deferred. |
| `friction` | NOT_IN_SCOPE | not_in_scope | No implementation in 0.2.6 foundation. |
