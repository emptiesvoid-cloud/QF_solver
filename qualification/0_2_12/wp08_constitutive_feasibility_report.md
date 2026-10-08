# WP08 constitutive feasibility audit

**Nature:** read-only scientific and technical feasibility study; not qualification, implementation, or gate closure.
**Audit branch:** `codex/v0.2.12-wp08-constitutive-feasibility-audit`
**Audit base:** `c1769ccaa9670fb98950c555c9ac29d66cd96ee4`
**WP08 source baseline:** `f85b6ad589a67e40782ff65b2e69e0e9e937e00a`
**WP08 status retained:** `BLOCKED`

## Executive conclusion

The reported noncoaxial-plastic defect is reproducible, and this audit identifies two implementation-level causes that reinforce one another:

1. The code feeds the symmetric local J2 response directly into `P = R T_local`. For a constitutive stress conjugate to the Biot stretch strain `U - I`, that is not the exact derivative of the internal energy with respect to `F` unless `T_local` commutes with `U`. The omitted polar-rotation/stretch derivative produces a force that is not the gradient of the bounded local incremental potential. Its angular-momentum residual is present in the assembled internal force, not just in exported stress fields.
2. The committed plastic tensors are stored in the element-corotated/material-like coordinates used by `U - I`, but `_transport_state` rotates them by `R_current.T @ R_old`. A rigid spatial spin after plastic preload leaves `U` unchanged yet changes equivalent plastic strain and local stress. This is a separate path-objectivity defect.

The evidence does **not** show that all J2 plasticity, every deformation in the declared strain bound, or the separate Total-Lagrangian route is invalid. Virgin elastic/coaxial tests behave as expected, and a fixed superposed rotation of an entire history remains covariant. Those are narrower properties than incremental objectivity or noncoaxial constitutive consistency.

### Proposed Owner decision

**Proposed decision: `RESCOPE_MINIMAL_CORRECTION`.** A bounded, mechanically coherent route appears feasible without introducing a new plasticity law: define the current local tensor as a Biot-strain-conjugate stress for `E_B = U - I`; keep plastic internal variables in the same material/reference frame (or define and integrate a mathematically equivalent objective transport); derive the nominal stress from the polar kinematic derivative; and rederive/verify the tangent from that force. This is more than relabeling or changing one output formula, but it is materially narrower than a general finite-strain plasticity redesign.

The proposal is conditional, not an implementation approval. The derivation and bounded numerical probes support feasibility; only an authorized implementation plus independent V&V can establish the corrected route. If Owner does not authorize force/state/tangent changes in v0.2.12, the defensible fallback is to defer this correction and explicitly exclude or limit the affected corotational J2 route in the release scope. The existing `WP08_STATUS = BLOCKED`, `QF0212_G03_NL = BLOCKED`, and `QF0212_G04_NL = BLOCKED` remain unchanged.

## Audit boundaries and baseline

The audit branch was created from the exact WP08 diagnostic commit. `f85b6ad...` and `c1769cc...` are in its ancestry; `origin/main` remains `e367fe58b2b9ebb4aef321424ca775e80e82d9ca`; the published `v0.2.11` tag still targets `afd2efa469a18e66581720ff4801f50de7d29eb4`. WP00/WP01 contracts are present. No source or test changes were present between the WP07 base and the WP08 diagnostic commit. The previous WP08 report and contract were read and left unchanged.

The read-only diagnostic campaign used Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, a unit linear TET4, and the production `VonMisesElastoplasticMaterial` / corotational element only as the object under examination. Tensor transformations, the polar derivative, and the radial-return incremental-potential oracle were separately evaluated with NumPy formulas. No persistent diagnostic script was added; fixtures, equations, preregistered metrics, commands, and outputs are recorded in `wp08_constitutive_feasibility_evidence.json`.

The already-frozen WP08 diagnostics were retained: transformation residual `<= 1e-12 * max(||reference||_F, 1 Pa)`, relative skew `||A-A.T||_F / max(||A||_F, 1 Pa)`, and a symmetry diagnostic threshold `1e-10`. These are diagnostics, not qualification tolerances. They were not changed after results were seen.

## Implemented chain versus intended interpretation

The source path in `src/solveur/elements/solid/corotational_j2.py` is:

| Stage | Implemented operation | Actual interpretation / audit note |
|---|---|---|
| Nodal displacement to kinematics | `F = I + u.T @ gradN` (`:158-160`) | Deformation gradient from reference gradients. |
| Polar split | SVD gives `F = R U` (`:76-88`) | Right stretch `U` acts in reference/material coordinates. |
| Local strain | `E_local = sym(U-I)` and engineering-Voigt conversion (`:163-169`) | Biot stretch strain; the bound is `||U-I||_F <= 0.05`. |
| Material update | `evaluate_constitutive(material, E_local, transported_state)` (`:171-172`) | Additive small-strain isotropic J2 radial return. Its symmetric tensor response is locally conjugate to the infinitesimal tensor `E_local` in the return map. It is not automatically Cauchy stress. |
| State transport | `R_current.T @ R_old`, applied to local plastic strain, stress and strain (`:91-127`) | Treats stored local tensor components as if they were fixed spatial components between frames. The pure-spin test below disproves invariance for this update. |
| Nominal stress for force | `P = R @ T_local` (`:174`) | Approximate pull/rotation map. It omits the exact derivative of `U(F)` for general noncoaxial `T_local,U`. |
| Internal force | `∫ P gradN dV0` (`:175`) | Therefore inherits the omitted polar derivative and the moment imbalance. |
| Tangent | Central difference of this force; step scales with `max(abs(displacement), abs(coords))`; returned matrix is symmetrized (`:203-230`) | Differentiates the current force approximately, then hides its raw skew. It is not a consistent tangent to a corrected force map. This remains WP09 work. |
| Export | `second_piola_stress = T_local`; `cauchy_stress = P F.T/J` (`:194-196`) | The former is not `F^-1 P`; the latter is nonsymmetric on the failing history and cannot be claimed as classical Cauchy stress there. |

The intended public meanings of first Piola, second Piola, and Cauchy stress are configuration-dependent stress measures, not labels for an arbitrary local tensor. The existing WP01 rule requires new results to carry measure, frame, and semantic version; it forbids silent reinterpretation of historical bytes.

## Reproduction and independent mechanics checks

### Previously reported noncoaxial history

The prior WP08 report's two-step TET4 history was re-read. It uses `F1 = diag(1+a, 1-a/2, 1-a/2)`, followed by a rotated principal-stretch state `F2`, carrying the committed material state. Across `a = 0.0015 ... 0.02`, all tested states remain inside the code's `0.05` local-strain bound. The reported relative skew rises from approximately `5.99e-4` to `2.44e-2`; at the largest case, the nodal resultant torque matches the volume-scaled skew part of `P F.T` to `9.50e-15` relative error. This confirms that the measured moment is represented in the production internal force; it is not a post-processing-only artifact.

The independent audit reran the same family at `a=0.016`: `||U-I||_F=0.0166661`, equivalent plastic strain `0.0240241`, normalized commutator `||TU-UT||/(||T|| ||U||)=0.0112640`, relative skew of `F^-1P=0.0194382`, and relative Cauchy skew `0.0194567`. The fixed threshold remains `1e-10`.

### Pure spin after plastic preload

After plastic preload at `F1=diag(1.016,0.992,0.992)`, apply `F2=Q_z(0.71)F1`. The independent SVD gives relative `U2-U1` error `6.41e-17`: stretch and local strain are unchanged to roundoff. Yet the implementation changes equivalent plastic strain from `0.0149067` to `0.0312165`, local stress by `73.4%` relative, and violates the expected nominal-stress covariance `P2=Q_z P1` by `91.6%` relative.

For a state stored in the material/right-stretch frame, a rigid spatial spin must not create a new plastic increment. `U` is invariant under `F -> QF`; the current state rotation therefore changes the material input while the strain input stays fixed. The old virgin rigid-rotation test passes because zero state is unchanged by any rotation. The old superposed-frame test also passes because rotating every state and every `F` by the same `Q` cancels out in `R_current.T R_old`. Neither test exercises a spin increment after a nonzero plastic state.

### Local work conjugacy and force discrepancy

The current J2 return map was compared against an independently coded tensor radial-return calculation and its incremental potential. For the tested active-plastic local update, production and independent local stress differed by `2.99e-15` relative; a central difference of the independent incremental potential with respect to symmetric local strain reproduced the local stress to `1.55e-10` relative. This supports a narrow interpretation of `T_local` as the stress conjugate to `U-I` for that local small-strain update. It does **not** establish finite-strain constitutive validity.

For a fixed committed plastic state and the same admissible TET4, the derivative of the incremental potential with respect to nodal displacements was evaluated independently. The production internal force differed by `0.8515%` when the state was held in its material frame; including the code's state-transport rule changed this only to `0.8467%`. The discrepancy remained approximately constant as the finite-difference step was reduced from `1e-5` to `1e-7`. Thus it is not truncation noise. This numerical check agrees with the exact polar derivative below.

### Polar derivative and angular momentum

Let `F=RU`, `A=R.T δF`, and take a basis in which `U=diag(λ_i)`. Differentiating the polar decomposition gives, for `i != j`,

```text
δU_ij = (λ_i A_ij + λ_j A_ji)/(λ_i + λ_j).
```

If a local potential has symmetric conjugate tensor `T = ∂ψ/∂U`, its exact first-Piola derivative is `P=R Pbar`, where in the principal-stretch basis `Pbar_ii=T_ii` and `Pbar_ij=2 T_ij λ_i/(λ_i+λ_j)` for `i != j`. This is a chain-rule result, not a symmetrization. It satisfies `Pbar U = U Pbar.T`, hence both `F^-1P` and `P F.T/J` are symmetric. It reduces to `P=RT` only when `TU=UT` (or in limiting small-stretch approximations).

On the tested plastic state, the production `RT_local` differs from this energy-conjugate map by `0.7854%`; the independently transformed exact-map PK2 and Cauchy skew are `9.67e-17` and `1.92e-16`. These are algebraic results for the stated local potential and state; they do not show that the production force is currently corrected.

The material J2 stress is symmetric locally. Classical balance of angular momentum for a nonpolar continuum requires symmetric Cauchy stress. The observed skew is therefore a mechanics violation for those tested states, not numerical roundoff. The TET4 torque identity independently links it to the force assembly. A corotational finite-element derivation should obtain internal force and tangent by variation of internal energy and check self-equilibrium and invariance; see [Felippa and Haugen, *A unified formulation of small-strain corotational finite elements: I. Theory*](https://doi.org/10.1016/j.cma.2004.07.035). For stress/strain work conjugacy and the distinction between Green-strain/PK2 and spatial pairs, see the [stress-measure reference](https://abaqus.uclouvain.be/English/SIMACAETHERefMap/simathe-c-stressmeas.htm).

### Elastic controls, load reversal, path and increment sensitivity

The independent bounded controls (zero state, `E=210 GPa`, `nu=0.3`, high yield threshold) gave zero skew for zero deformation, virgin rigid rotation, uniaxial tension/compression, coaxial stretch, simple shear, and a rotated anisotropic stretch. For isotropic elasticity, `T` is a function of `U-I` and commutes with `U`; consequently these controls do not exercise the missing noncoaxial derivative.

Unloading the plastic prestrain to zero total stretch triggers reverse plastic flow in this model (`eqp: 0.0149067 -> 0.0286634`). This is not classified as a defect: the reverse elastic trial stress can reach the opposite yield surface. Two different paths to the same final `F` also produce different internal variables and stress, as expected of path-dependent plasticity; this observation is not used as a pass/fail oracle.

For one smooth rotating-principal-stretch path, one increment versus 32 increments changes equivalent plastic strain from `0.0139108` to `0.0161234`; the 16-to-32 increment change is about `0.316%`. This is a bounded discretization-sensitivity result for that sampled path, not a universal convergence rate or physical error bound.

## Cause assessment

| Candidate cause | Assessment | Contribution to observed defect |
|---|---|---|
| 1. Local stress has the wrong intrinsic definition | **Partly ruled out / semantics incomplete.** The local J2 response is symmetric and locally conjugate to `U-I` for the tested radial-return update. It is not thereby Cauchy stress. A precise Biot-strain interpretation is viable within the bounded model. | Not the primary cause if correctly treated as a local Biot-conjugate stress. |
| 2. Stress-measure transformation is wrong | **Confirmed.** The `second_piola_stress` payload is literally `T_local`, not `F^-1P`. The calculated Cauchy transformation is algebraically `PF.T/J`, but its input `P` is not a valid exact force-conjugate map for noncoaxial `T,U`. | Direct semantic defect plus visible nonsymmetry. |
| 3. Energetic conjugacy is absent | **Confirmed for current global force map.** Local return is conjugate to `U-I`; the global force map omits the adjoint derivative of `U(F)`. | Primary force/work inconsistency. |
| 4. First Piola construction `P=RT_local` | **Confirmed outside coaxial/small-stretch limiting cases.** Exact derivative differs by `0.7854%` on the audited state. | Primary angular-momentum/force contribution. |
| 5. Rotation treatment | **Confirmed for internal-state transport.** A pure rigid spin after plastic preload changes local state and stress with `U` invariant. | Independent, high-likelihood contributor to plastic-history errors. |
| 6. Small-strain J2 with finite rotations is inherently incompatible | **Not established.** A bounded objective small-local-strain model is possible; the current implementation's frame/force maps are inconsistent. This route must not be represented as general finite-strain plasticity. | Incompatibility is not necessary to explain this defect. |
| 7. A force term is missing | **Confirmed in the variational mapping.** The missing terms are the polar-kinematic chain-rule contributions; exact formula given above. | Primary mechanism. |
| 8. Force and tangent are inconsistent | **Confirmed as a corrective-work dependency; current numerical tangent differentiates current force but symmetrizes it.** Raw tangent skew in the tested state is about `1.51e-3`; origin shift 0 to 1000 changes FD step `1e-7` to `1.001e-4`, and the tangent matrix changes `4.14e-5` relative. | Tangent is not the root of the stress skew, but must be revalidated after force correction; blind symmetrization obscures diagnostics. |
| 9. Defect is specific to noncoaxial plastic paths | **Confirmed for the reproduced skew, not a universal scope statement.** Elastic isotropic and coaxial cases commute and pass these symmetry diagnostics. | Activating condition, not a separate root cause. |
| 10. Multiple causes | **Most likely.** Incorrect nominal force map plus internal-variable frame transport; mislabeled PK2 field is an additional semantic fault. | Best explanation of the full set of observations. |

## Producers, consumers, and route boundaries

| Producer / route | Current measure and frame | Affected consumer / output | Audit disposition |
|---|---|---|---|
| Corotational J2 element, `corotational_j2.py:148-198` | `stress/local_stress`: local additive J2 response to `U-I`; `first_piola_stress`: current `RT_local`; `second_piola_stress`: same local tensor under a false name; `cauchy_stress`: `PF.T/J`, nonsymmetric on failing states. | `StressPostProcessor._total_lagrangian_j2_result()` at `post/stress.py:193-305` uses raw `stress` for generic principal/von-Mises/averages and copies the named PK2/Cauchy fields. JSON result pass-through is in `core/results.py:65-80`; CSV writer is `io/csv_writer.py`; VTU writer is `io/vtu_writer.py`. | Directly affected. Averages of local stress components also lack explicit common-frame transport when quadrature frames differ. No silent relabel or migration. |
| Total-Lagrangian J2 element, `total_lagrangian_j2.py:99-175` | `E_G=0.5(F.TF-I)`; local J2 response used as `S`; `P=F S`; `Cauchy=F S F.T/J`. | TL stress processor/geometric route and dedicated TL tests. | Separate route. This audit does not infer the corotational failure there. It is a bounded Green-Lagrange/additive-J2 model, not proof of general multiplicative finite-strain plasticity. |
| Geometric nonlinear assembly | Uses its TL kernels and `S` for geometric contributions. | `core/assembly/geometric.py`, `core/analyses/geometric_nonlinear.py`. | No evidence that it consumes the corotational producer's false PK2 field. Do not generalize the defect. |

The old JSON/CSV/VTU values lack semantic version and reliable frame/measure metadata. Under WP01, `OLD_SEMANTICS != NEW_SEMANTICS` and `READABLE != SCIENTIFICALLY_REQUALIFIED`: historical result bytes stay as they are; a future adapter should mark ambiguous legacy fields `LEGACY_UNKNOWN`, not rewrite them as modern PK2.

## Corrective options and release implications

The detailed multicriteria matrix is in `wp08_constitutive_options_comparison.md`; the proposed decision record is in `wp08_constitutive_rescope_proposal.md`.

### Options in brief

- **A, bounded correction:** retain additive isotropic J2 on `U-I`, assign the local response a Biot-conjugate meaning, store internal variables in that material/right-stretch frame (or define an equivalent objective update), derive `P` by the exact polar derivative, then derive/check its tangent. Feasible in principle; internal force and tangent must change. High V&V, but no new constitutive law is inherently required inside the existing small-strain bound.
- **B, broader corotational reformulation:** define a chosen objective rate/local frame and derive state evolution, force, and tangent as one formulation. Feasible, but higher scope and risk than A.
- **C, existing Total-Lagrangian path:** a possible explicitly separate fallback for its tested scope, not a drop-in patch. It uses Green-Lagrange strain/PK2 and its own additive J2 update; it is not thereby a general finite-strain plasticity model.
- **D, finite-strain redesign:** multiplicative `F=F_e F_p`, elastic energy in elastic configuration, flow/hardening evolution, consistent algorithmic tangent and state migration. Scientifically broader and costliest; useful only if the product requires general finite-strain plasticity. See [Simo and Ortiz (1985)](https://doi.org/10.1016/0045-7825(85)90061-1) for a primary example of a hyperelastic-based finite-deformation framework, not as a drop-in prescription.

### WP09 and WP10 ordering

WP09's finite-difference step origin dependence, raw-versus-symmetrized tangent diagnostics, and evaluation-cost accounting can be characterized independently. A tangent acceptance campaign against the old force is provisional: force-map changes invalidate its final numerical targets. Recommended order: settle the corrected force/state contract first, then derive or independently difference that force, check raw symmetry, and remove any unverified symmetrization only under an authorized WP09 scope.

WP10 state transaction tests (trial/commit/rollback), checkpoint integrity, schema parsing, fail-closed migration tests, and method-specific convergence reporting are partly separable. Checkpoint compatibility and replay baselines for corotational J2 are not separable from internal-variable frame semantics; historical checkpoint restart must remain refused where identity/frame cannot be proven. Do not validate converged trajectories against a force law that is about to change.

### Release scenarios

1. **Bounded correction in v0.2.12:** preserve the dynamic WP02–WP07 work and complete A plus dependent WP09 validation. Best route if the bounded corotational J2 feature is a required release deliverable; schedule and V&V cost are high. The nonlinear gates remain open until complete.
2. **Defer correction and narrow NL scope:** keep the affected route explicitly limited/not qualified and remove it from v0.2.12 NL claims, with Owner-approved gate/scope/documentation changes. Dynamic capabilities remain independently assessable. This has lower release cost, but is unacceptable if the published NL scope still claims this route as mechanically verified.
3. **Delay release for a broader constitutive redesign:** required only if future evidence shows A cannot define the needed product behavior or if general finite-strain plasticity is required. Highest cost and risk; affects force, tangent, state/checkpoint and result semantics broadly.

## Limits and preserved decisions

The diagnosis is specific to the corotational J2 kernel and tested histories within its current `||U-I||_F <= 0.05` limit. It does not prove every history fails. The independent energy checks use a bounded associative isotropic J2 incremental potential; they are not external code-to-code validation or full-model qualification. The audit did not run the full unit suite, documentation suite, lint, format, or typing because no implementation was authorized; only the focused existing regression command was rerun.

Preserved exactly: `WP08_STATUS = BLOCKED`, `WP09_READY = NO`, `WP10_READY = NO`, `QF0212_G03_NL = BLOCKED`, `QF0212_G04_NL = BLOCKED`, `HISTORICAL_G03 = FAIL_PRESERVED`, `HISTORICAL_WP14 = HOLD_NOT_PROMOTED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`, and `RELEASE_PUBLICATION_AUTHORIZED = NO`. This study is not qualification and changes no maturity.
