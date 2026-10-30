# W observables and reference hierarchy

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

## Required observables for each future mesh

- Complete nodal displacement field with node/DOF mapping and units.
- Mean terminal-face UZ and signed load-conjugate displacement `W/ΣFz`.
- Support reactions by component, total external/support force and moment about a fixed declared origin.
- An independently formed free-DOF residual and its explicit denominator; report absolute and relative 2-norms and the largest component.
- Exact/consistent discrete strain energy `U`, external work `W`, and the residual term in `2U-W=u_freeᵀr_free`.
- Element/node counts, volumes, mesh metrics, material identity, applied force sum and applied moment.
- Actual wall time and process/memory observations, clearly distinguished from static estimates; record solver/backend/thread identities.
- Ratios and signed changes relative to H3, and ratios to the beam diagnostic. Keep the reference definition and sign visible.

Before Owner approval, specify how the residual is independent of the solve result. Prefer an explicitly documented alternate application/assembly route or a reviewed element-force reconstruction; recomputing `K u-f` from the same stored matrix is useful diagnostics but not independent implementation evidence. A residual cannot establish discretization accuracy.

## Reference hierarchy

1. **Discrete algebraic checks:** equilibrium, residuals, and energy/work identities for the exact tested model. These verify consistency of the discrete computation, not continuum correctness.
2. **Historical H3 result:** same model identity and output definition as WP12-S. Preserve its original receipt and use the recorded UZ `-4.795612893178559e-8 m` only after confirming identity and extraction.
3. **Beam diagnostic:** Euler-Bernoulli/Timoshenko result `-1.4397142857142855e-7 m`. It is a 1D comparator and not an exact 3D solution; its 66.69% difference from H3 is context, not a tolerance or validation oracle.
4. **Potential future physical reference:** an independent 3D analytical benchmark or separately reviewed external solver, selected only if the W results require one and its model assumptions can be matched.

No W acceptance tolerance, convergence order, or “dominant direction” threshold is approved in this preparation. A future Owner decision should define whether direction comparison is descriptive or gated and how numerical solution uncertainty is propagated. Do not retrofit such a threshold after observing W results.

## Energy decomposition caution

Do not report a bending/shear energy split merely by selecting strain components unless the decomposition is invariant, mechanically meaningful for this 3D solid formulation, and independently checked. A proposed split would need a written definition, coordinate/frame convention, and a demonstration that component contributions are not artifacts of the selected element basis or local axes. Defer the decomposition if those conditions are not met.
