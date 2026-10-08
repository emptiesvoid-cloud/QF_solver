# WP08 constitutive correction options

This comparison is a feasibility assessment, not authorization or a maturity/qualification decision. The evidence scope is the bounded `||U-I||_F <= 0.05` corotational J2 route and the diagnostic fixtures in `wp08_constitutive_feasibility_evidence.json`.

## Fact / estimate separation

**Observed facts:** `P=R T_local` is used in internal forces; `T_local` is the additive J2 update on `U-I`; the local variables are rotated by `R_current.T @ R_old`; the reported PK2 field is `T_local`; and tested noncoaxial plastic paths violate the prescribed symmetry diagnostic. An exact polar derivative exists for a symmetric stress conjugate to `U-I`; a rigid spin after plastic preload also changes the current state due to the current transport rule.

**Estimates:** effort, regression risk, migration cost and roadmap impact below are relative engineering estimates. They are not measured project durations. `LOW < MEDIUM < HIGH < CRITICAL` denotes relative burden/risk, not scientific quality.

## Strategy matrix

| Criterion | A. Bounded correction of current Biot-strain model | B. Broader coherent corotational reformulation | C. Reuse existing Total-Lagrangian J2 route | D. General finite-strain plasticity redesign |
|---|---|---|---|---|
| Mechanical consistency achievable | MEDIUM risk after derivation; HIGH confidence feasible within scope | LOW-MEDIUM risk if fully derived and tested | MEDIUM; separate bounded model already has compatible `E_G/S` kinematics | LOW after full formulation, but highest implementation burden |
| Objectivity | Must correct state frame; HIGH until tested | LOW-MEDIUM if objective rate/transport is explicit | MEDIUM; objective `E_G` response but plastic finite-strain scope remains bounded | LOW if multiplicative formulation and integration are correct |
| Angular-momentum balance | LOW risk with exact polar derivative; must verify force residual | LOW-MEDIUM | LOW for symmetric S and `P=FS`, subject to route tests | LOW-MEDIUM with consistent stresses and return map |
| Energy conjugacy | LOW-MEDIUM after proving local potential plus exact adjoint derivative | LOW-MEDIUM after re-derivation | MEDIUM; Green-Lagrange/PK2 pairing is explicit | LOW-MEDIUM with hyperelastic framework |
| Noncoaxial plastic histories | MEDIUM; current counterexample directly targets corrections | LOW-MEDIUM | MEDIUM; requires its own noncoaxial history study | LOW-MEDIUM after finite-strain V&V |
| Preserve current J2 radial return | HIGH (best of these options) | MEDIUM-HIGH | MEDIUM; can reuse material routine but strain measure changes | LOW; state/evolution law changes substantially |
| Internal force impact | HIGH/required | HIGH/required | HIGH for rerouted model | CRITICAL |
| Tangent impact | HIGH/required and depends on force | HIGH/required | HIGH for affected route | CRITICAL |
| Newton compatibility | MEDIUM; force and raw tangent must be tested together | MEDIUM-HIGH | MEDIUM; separate assembly route helps isolate | HIGH implementation burden |
| Checkpoint / state impact | MEDIUM-HIGH; state-frame schema and restart gate | HIGH | MEDIUM-HIGH; route-specific states/checkpoints | CRITICAL |
| Historical result migration risk | HIGH if relabeled; LOW if old bytes remain legacy and new semantics versioned | HIGH | MEDIUM-HIGH when users switch route | CRITICAL |
| Development effort estimate | HIGH, roughly 2–4 WP08-sized units including force/state/tangent review | HIGH–CRITICAL, roughly 4–7 units | MEDIUM, roughly 2–4 units for a separate bounded route and comparative V&V | CRITICAL, roughly 8+ units; new material-state and migration work |
| V&V effort estimate | HIGH: energy, objectivity, angular momentum, plastic path, mesh/element, Newton | CRITICAL: broad formulation matrix | HIGH: prove actual TL scope and prevent route substitution drift | CRITICAL: broad constitutive, integration, tangent, path, and migration campaign |
| Regression risk | HIGH locally; low outside the corotational path if isolated | HIGH | MEDIUM-HIGH due route selection and duplicated semantics | CRITICAL across all NL state/results/checkpoints |
| v0.2.12 roadmap impact | HIGH but bounded; WP08 must expand and WP09 follow | CRITICAL for planned release | MEDIUM; alternative NL path, not a fix of existing corotational route | CRITICAL; likely release reschedule |
| Future maintainability | MEDIUM-HIGH; explicit Biot contract and exact map can be maintained | MEDIUM; clearer theory, larger specialized code | MEDIUM-LOW if duplicate NL kernels proliferate | MEDIUM-HIGH if finite-strain plasticity is an actual long-term product need |

## Option A: bounded correction, not output-only repair

The current strain input `E_B=U-I` is the Biot stretch strain. A symmetric tensor conjugate to this strain may be retained as the local return-map output if that is the explicitly selected model. For a local potential/incremental potential `ψ(E_B, internal state)`, the global nominal stress must be the adjoint derivative `∂ψ/∂F`, not generally `R T_local`. In an eigenbasis of `U`, the off-diagonal chain-rule terms are stated in the main report and evidence record. They restore the exact virtual-work mapping for a fixed admissible state and satisfy the no-couple angular-momentum identity without symmetrizing any stress.

The state is the other necessary correction: if the plastic strain/stress are defined in the reference/right-stretch frame used by `U-I`, a pure spatial spin must leave those local components unchanged. If an alternative rotating frame is intended, the objective transport law must be stated and integrated consistently; `R_current.T @ R_old` is disproven for the current state meaning by the pure-spin counterexample.

The evidence supports feasibility **in principle**, not a ready-made patch. The exact map changes internal nodal forces; state evolution and checkpoint identity change; the numerical tangent must be recomputed from the new force and its raw symmetry diagnosed. A stress-only relabel, output symmetrization, or replacement of `P` by `sym(PF.T)` would not be acceptable.

## Option B: coherent corotational re-derivation

Choose one corotational frame/spin and one work-conjugate strain/stress pair, then derive the incremental state update, element internal force, and tangent from that choice. For instance, a rate-based Green–Naghdi style route and a right-stretch/Biot route are not interchangeable implementation details; each gives different finite-rotation evolution and must name its stress rate and objective update. The literature on small-strain corotational elements emphasizes deriving force/tangent from internal-energy variation and explicitly evaluating self-equilibrium, invariance, and consistency rather than assuming that local-force rotation suffices ([Felippa & Haugen](https://doi.org/10.1016/j.cma.2004.07.035); [Pai, Palazotto & Greer](https://doi.org/10.1016/S0045-7949(98)00004-2)).

This is feasible but broader than the current evidence requires. It is the fallback if the bounded Biot model cannot satisfy the user's required behavior or if a clean theory cannot be maintained with the present radial-return state.

## Option C: Total-Lagrangian route

The repository already has a distinct Green–Lagrange J2 route: `E_G=(F.T F-I)/2`, local J2 response used as `S`, `P=F S`, and `σ=F S F.T/J`. For a symmetric `S`, this mapping is work-conjugate and produces symmetric transformed Cauchy stress. The geometric nonlinear route uses this separate kernel. That makes TL a plausible restricted alternative if its own element, tangent, plastic-history, convergence and external-reference evidence meets the desired scope.

It does **not** repair corotational J2 in place. The strain measure and force response change. It is additive plasticity driven by Green–Lagrange strain, not a demonstrated multiplicative finite-strain law. Its current tests and stress verification cover a bounded route and do not establish general noncoaxial finite-strain plasticity. Routing a user model from one formulation to another must therefore be an explicit method selection with separate identity, results and qualification, never an implicit fallback.

## Option D: finite-strain redesign

A multiplicative formulation `F=F_e F_p`, with elastic response from a free energy in elastic configuration and a finite-strain plastic flow/update, is a substantially different material model. It needs new internal variables, return mapping and algorithmic tangent, state/checkpoint schema, and broad independent V&V. Simo–Ortiz is a primary example of a hyperelastic-based finite-deformation approach with return mapping; it is cited as a comparison class, not as an implementation recipe ([Simo & Ortiz 1985](https://doi.org/10.1016/0045-7825(85)90061-1)).

This option is unwarranted solely to fix a bounded small-local-strain corotational route. It becomes appropriate only if Owner requires general finite-strain plasticity or Option A cannot meet the actual product requirements.

## Recommendation and decision boundary

The best evidence-weighted next scope is **Option A under `RESCOPE_MINIMAL_CORRECTION`**, with a strict cap at the present small-corotational-strain domain and no claim of general finite-strain plasticity. The work package must explicitly include local-state frame semantics, exact force mapping, tangent revalidation, semantic versioning, and noncoaxial path V&V. If any of those conditions cannot be met, stop and return to Owner; do not soften the symmetry or energy criteria.

Option C may be evaluated separately as an already existing bounded route, but cannot be counted as correction of the corotational route. Option B and D should remain deferred unless the bounded model cannot be made coherent or broader product claims require them.
