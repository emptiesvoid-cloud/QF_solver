---
doc_id: DOC-NL-025-006
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 formula inventory

This inventory defines formulas to audit and verify. It does not select a new
constitutive model or authorize implementation.

| ID | Capability | Governing relation | Existing basis | Required decision/proof |
|---|---|---|---|---|
| F-01 | Global equilibrium | `R(u, q, lambda) = Fint - lambda Fext + Fc = 0` | separate nonlinear/contact residuals | sign convention and one common residual contract |
| F-02 | Full Newton | `K_T delta_u = -R`, `u_{i+1}=u_i+delta_u` | small-strain and geometric loops | one convergence policy and tangent composition |
| F-03 | Small strain | `epsilon = sym(grad u)` | common J2 element contract | preserve 0.2.4 behavior |
| F-04 | J2 yield | `f = sigma_eq - (sigma_y + H alpha)` | `VonMisesElastoplasticMaterial` | re-derive convention and cyclic limitations |
| F-05 | J2 flow/return | associative deviatoric radial return | existing material | analytical path and state verification |
| F-06 | J2 tangent | `C_alg = d sigma_{n+1}/d epsilon_{n+1}` | existing algorithmic tangent | FD sensitivity near elastic/plastic transition |
| F-07 | Finite kinematics | `F = I + Grad_X u` | TET4 TL kernel | approve reference/current configuration conventions |
| F-08 | Green-Lagrange strain | `E = 0.5 (F^T F - I)` | TET4 TL kernel | objectivity and element FD proof |
| F-09 | TL stress/work conjugacy | `S` conjugate to `E`, `P = F S` | StVK TET4 | approve material measure for each model |
| F-10 | Internal virtual work | `delta Wint = integral(delta E : S dV0)` | TL assembly | internal force and energy derivative FD |
| F-11 | Tangent decomposition | `K_T = K_material + K_geometric + K_contact` | separate paths exist | sparse common assembly and FD consistency |
| F-12 | Linear buckling | `(K + lambda K_G) phi = 0` or sign-equivalent form | bounded sparse TET4/HEX8 route | preload/sign/normalization convention |
| F-13 | Arc length | `g(delta u, delta lambda, ds) = 0` | sparse augmented correction helper | choose one Crisfield/Riks constraint and sign rule |
| F-14 | Normal gap | `g_n = (x_s - x_m) dot n_m` | contact package | orientation, projection and finite-sliding update |
| F-15 | Normal contact | complementarity or approved regularization | active-set contact exists | choose multiplier/penalty/augmented formulation |
| F-16 | Coulomb friction | `||t_t|| <= mu t_n`, stick/slip complementarity | regularized experimental path | optional objective frame/state formulation |
| F-17 | External work | incrementally consistent `Wext` | partial nonlinear work diagnostics | load-path integration convention |
| F-18 | Energy balance | `Wext - Ue - Dp - residual_terms = 0` | not fully qualified | define treatment of contact/friction work |
| F-19 | Plastic dissipation | `Dp >= 0` for the retained associative J2 model | material states | per-increment and accumulated proof |
| F-20 | Transaction | `state_committed` unchanged until accepted increment | `MaterialStateSession` | extend to contact/continuation and adversarial proof |

## Formula review checklist

For each formula before coding:

1. cite the reference or existing controlled derivation;
2. declare tensor ordering, signs, configuration and units;
3. identify work-conjugate measures;
4. derive residual and consistent tangent together;
5. define analytical and finite-difference checks;
6. record singular/degenerate cases;
7. obtain Owner approval for any scope-changing constitutive assumption.
