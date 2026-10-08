# Proposed Owner decision: WP08 constitutive rescope

**Status:** proposal only. No official roadmap or gate has been changed.
**Requested Owner decision:** choose whether to authorize a bounded correction, defer it with an explicit scope exclusion, or require a broader reformulation.

## Proposed decision

```ini
PROPOSED_DECISION = RESCOPE_MINIMAL_CORRECTION
RECOMMENDED_RELEASE_SCENARIO = SCENARIO_1_IF_OWNER_ACCEPTS_HIGH_TARGETED_VNV_COST
FALLBACK_RELEASE_SCENARIO = SCENARIO_2_WITH_EXPLICIT_COROTATIONAL_J2_SCOPE_EXCLUSION
```

The current local update can plausibly be retained as additive isotropic J2 in the bounded Biot stretch strain `E_B=U-I`. The evidence does not require a new multiplicative finite-strain plasticity law to repair the observed defects. It does require changes to the constitutive-state frame contract and to the force map. Therefore this is a mechanics rescope, not WP08's original semantic-only task.

## Proposed authorized work boundary (not started)

If approved, define a separately tracked bounded correction with all of these mandatory outputs:

1. **Kinematic/model declaration:** `F=RU`, `E_B=U-I`, `||E_B||_F <= 0.05` (or an Owner-approved unchanged limit), reference/material frame for plastic internal variables, and explicit model limitations.
2. **Local constitutive contract:** additive associative J2 radial return and isotropic hardening in `E_B`; show the local incremental potential/flow and dissipation assumptions; identify which state fields are material-frame quantities.
3. **State invariance:** pure spatial spin after nonzero plastic preload leaves `U`, material state, equivalent plastic strain, and local stress unchanged; superposed rigid rotation of an entire history gives covariant spatial stress and force.
4. **Force contract:** derive `P=∂ψ_incremental/∂F` by the polar chain rule, including all terms implied by state evolution. Do not replace the skew stress by a symmetric projection. Demonstrate virtual-work residual and angular-momentum balance independently.
5. **Tangent:** derive a consistent algorithmic tangent or evaluate a preregistered raw finite-difference tangent of the corrected force. Report raw skew and step sensitivity before any symmetrization. Origin-invariant differencing belongs in the dependent tangent work.
6. **Results:** preserve historical output fields as legacy semantics; version new stress measure/frame metadata. Only emit `second_piola_stress` and `cauchy_stress` when the relevant transform is mathematically and constitutively justified. Existing stored results remain unchanged and are not requalified.
7. **Restart:** do not resume a historical checkpoint if the state frame or physical identity cannot be proven. Add a new semantic/state version only after a separate compatibility decision.

No item above is authorized by this proposal. In particular, neither force code nor tangent code may be changed until Owner approval.

## Required acceptance evidence if authorized

Freeze the numerical metrics before implementation results are examined. At minimum:

- local stress equals the derivative of the stated incremental potential within a scale-aware finite-difference tolerance;
- exact force variation agrees with independent nodal potential differences across the tested strain range;
- `F^-1P` and `P F.T/J` are symmetric to the preregistered numerical threshold for the no-couple model;
- pure rigid-spin increment after plastic preload creates no plastic update;
- superposed rotation covariance holds for multi-step noncoaxial histories;
- internal resultant moment is consistent with angular-momentum balance;
- force/tangent directional derivative agrees at multiple step sizes and is invariant under coordinate-origin translation;
- proportional and nonproportional elastic/plastic load-unload paths, element family/quadrature, mesh sensitivity, Newton convergence and failure/restart behavior are characterized;
- compare against an independent analytical/material-point implementation or an independently authored reference, not only a second QF code path;
- preserve non-corotational routes, TL route, Newton controls, historical results and qualification statuses.

The existing `1e-10` symmetry diagnostic and `1e-12` transform residual remain unchanged unless Owner explicitly approves a pre-result scientific review and contract revision. Numerical PASS does not imply qualification or maturity promotion.

## WP09 / WP10 sequencing proposal

```text
Owner rescope decision
        |
        v
bounded state-frame + force-map formulation (WP08 rescope)
        |
        v
raw/consistent tangent and origin-invariant numerical differentiation (WP09)
        |
        +------> WP10 checkpoint/restart implementation using frozen state semantics
        |
        v
targeted nonlinear V&V and evidence integration
```

WP10 parser/integrity and generic trial/commit/rollback tests can be split out after explicit authorization. Corotational replay results and state migration cannot be finalized before the state-frame contract. WP09 may characterize the old tangent for diagnosis, but its final correctness target must follow the corrected force law.

## Release choice requested

### Scenario 1: bounded correction within v0.2.12

Select only if the Owner wants the corotational J2 route in the release's claimed NL scope and accepts additional force/tangent work plus high targeted V&V. WP08 reopens under a new scope; WP09 becomes dependent and WP10 checkpoint versioning follows. Keep G03_NL and G04_NL blocked until all criteria and evidence pass.

### Scenario 2: defer correction and reduce NL scope

This is the schedule-preserving fallback. Explicitly exclude or label the affected corotational J2 path as not assessed/physically unverified for noncoaxial plastic histories; do not imply it is fixed by its existing tests. Update the official scope and gates only after Owner approval. Other v0.2.12 dynamic work and independently supported nonlinear routes remain separately assessable. The global NL gate cannot be passed while the excluded route remains in its required scope.

### Scenario 3: delay for broad finite-strain redesign

Use only if required product claims exceed the bounded Biot-strain model or Option A fails independent V&V. This is not required by the current evidence alone.

## Explicitly unchanged pending Owner decision

```ini
WP08_STATUS = BLOCKED
WP09_READY = NO
WP10_READY = NO
QF0212_G03_NL = BLOCKED
QF0212_G04_NL = BLOCKED
HISTORICAL_G03 = FAIL_PRESERVED
HISTORICAL_WP14 = HOLD_NOT_PROMOTED
WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO
RELEASE_PUBLICATION_AUTHORIZED = NO
MATURITY_PROMOTION = NONE
```

No branch beyond the documentary audit branch, code change, test change, historical-result edit, qualification change, tag, push, merge, or publication is authorized by this proposal.
