# WP-E01-B3 Scientific Gate and Newton/J2 Integration Readiness

- **Date:** 2026-10-20
- **Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-a-implementation-20261020`
- **Verified starting HEAD:** `d1a629f83c9303eded40ce181e3fd38706d21fc5` (clean)
- **Origin:** `https://github.com/emptiesvoid-cloud/QF_solver.git`
- **Canonical roadmap:** `qualification/0_2_12/ROADMAP.md`, SHA-256 `48021a7773895c354806446ab89e317b968cfee5f2618790f4487fbf11195a6d`
- **Scope:** E01-B small-strain J2 tangent evidence and a bounded synthetic Newton/J2 test plan
- **Campaign cycle:** 1 of 3; no production or test-source remediation was needed

## Outcome

The existing authorized J2 material-point oracle was rerun with its registered digest unchanged. It passed 28/28 and produced elastic and smooth-plastic directional derivative data. The data supports a candidate `1e-8` tangent gate for the exercised fixtures, provided the stiffness floor is revised to a mathematically derived scale. The gate is **not Owner-approved or source-enforced**. Evidence does not cover all requested branches or establish a production Newton/J2 route.

No new tests or source files were created. A bounded internal synthetic integration test specification is provided below; a new execution path still needs a separate Owner GO. No public solver, model assembly, native FEM, Gmsh, backend, worker, or child process ran.

## A — Candidate tangent gate for Owner decision

### Exact derivative and conventions

The target is the derivative of the **discrete stress update**, holding the incoming material state `z_n` fixed:

\[
D_h\sigma(\varepsilon;z_n,p)=
\frac{\sigma(\varepsilon+h p;z_n)-\sigma(\varepsilon-h p;z_n)}{2h}.
\]

The six-component API uses ordering `[xx, yy, zz, xy, yz, xz]`; the strain input has engineering shears, while stress output has tensorial shears. For this candidate gate, `p` is normalized by the Euclidean 2-norm of that fixed engineering-Voigt coordinate vector. The error is the Euclidean 2-norm on the corresponding returned stress-Voigt coordinates. These are explicit API-coordinate norms, not an assertion that the packed-vector norm is a tensor-invariant norm.

Report the absolute error

\[
E_{abs}(h,p)=\|C_{alg}p-D_h\sigma\|_2 \quad [\mathrm{stress}],
\]

and use this dimensionless normalized error:

\[
\eta_T(h,p)=\frac{E_{abs}(h,p)}
 {\max(\|C_{alg}p\|_2, C_{ref}\|p\|_2)}.
\]

`h` is a dimensionless engineering-strain perturbation amplitude. `C_ref` is positive and has stress units, so the denominator remains nonzero even when a perfect-plastic flow direction makes `C_alg p` small. No separate arbitrary absolute-error floor is required; keep `E_abs` in the record for review.

### Stiffness reference correction

The earlier B2 report used `C_ref=K+2μ`. That is positive, but it is not a general operator-norm reference for all allowed Poisson ratios. Recommend instead

\[
C_{ref}=\max(3K,2\mu),\quad K=\frac{E}{3(1-2\nu)},\quad \mu=\frac{E}{2(1+\nu)}.
\]

For isotropic elasticity represented in the stated six-component mapping, the normal block has eigenvalues `3K, 2μ, 2μ` and the engineering-shear columns have eigenvalue `μ`; `max(3K,2μ)` is therefore the elastic matrix's Euclidean operator norm. It is a scale, not a claim that the elastoplastic tangent is always bounded by it.

For the tested fixture (`E=210000 MPa`, `ν=0.3`), the old floor was `K+2μ=336538.5 MPa`; the revised floor is `3K=525000 MPa`. With the same coordinate norms, increasing this denominator floor cannot increase the reported normalized errors or adjacent-difference ratios. Thus the existing fixture evidence is conservative under the revised scale. That implication does not supply evidence for untested material parameters.

### Proposed acceptance rule — not frozen

Use the existing geometric sweep `h=1e-3, 1e-4, …, 1e-10`. For each material branch and independent direction, accept a smooth-branch derivative check only if a window of **three consecutive decade-spaced steps** exists such that:

1. `η_T(h,p) ≤ τ_T` at all three steps;
2. the two adjacent finite-difference changes
   \[
   \delta_i=\frac{\|D_{h_i}\sigma-D_{h_{i+1}}\sigma\|_2}
   {\max(\|D_{h_{i+1}}\sigma\|_2,C_{ref}\|p\|_2)}
   \]
   are each `≤ τ_T`;
3. the base point and both perturbations at all three steps remain on the same **strict** active branch, with signed `f_trial` values recorded; and
4. the incoming state digest is unchanged by every perturbation.

Recommend `τ_T=1e-8` for Owner approval. This is 2000 times tighter than the older proposed `2e-5`, and is about 12.6 times above the largest measured smooth-plastic error in the current local window under the prior, smaller denominator. It is evidence-informed rather than selected only to pass, but remains limited to the tested fixtures. If no stable window exists, report `INCONCLUSIVE` rather than treating cancellation or branch crossing as proof of an incorrect tangent.

If `f_trial` is zero or any perturbation changes strict branch, exclude that centered derivative from the smooth gate. Record it as a yield-transition case and compare one-sided derivatives on their respective branches. Do not average across the active-set switch. No numeric yield-margin cutoff is proposed: strict branch membership and the measured signed margins are recorded, and unresolved floating-point branch classification is reported as `TRANSITION_UNRESOLVED`.

Apply the smooth gate separately to elastic, smooth plastic with `H=0`, and smooth plastic with `H>0` states. Add nonzero incoming plastic history, unloading/reload and near-yield cases before treating this as a general material gate. Symmetry of the returned tangent is diagnostic only; the code symmetrizes the tangent and symmetry alone cannot establish derivative consistency.

## B — Numerical evidence and transition findings

The exact J2 module run reported `C_ref=336538.5 MPa` (B2 scale), used fixed zero incoming plastic state for the derivative fixtures, and tested three normalized directions: normal-mixed, engineering-xy shear, and six-component mixed. Both perturbations remained smooth-plastic for `H=0` and `H=1500 MPa`. Minimum reported trial-yield margins were approximately `561.274 MPa`, `751.115 MPa`, and `708.109 MPa` for those directions, respectively.

| Branch / quantity | Perturbation | Maximum observed across the tested directions | Interpretation |
|---|---:|---:|---|
| Elastic derivative error | `h=1e-6` | `1.618e-16` relative; `5.445e-11 MPa` absolute | Resolved |
| Elastic derivative error | `h=1e-8` | `9.174e-15` relative; `3.087e-9 MPa` absolute | Resolved |
| Elastic derivative error | `h=1e-10` | `1.022e-12` relative; `3.4397e-7 MPa` absolute | Cancellation starts to dominate |
| Smooth plastic `η_T` | `h=1e-6` | `7.930e-10` | Local stability window |
| Smooth plastic `η_T` | `h=1e-7` | `1.028e-11` | Local stability window |
| Smooth plastic `η_T` | `h=1e-8` | `7.138e-11` | Local stability window |
| Smooth plastic `η_T` | `h=1e-9` | `8.845e-10` | Cancellation growth |
| Smooth plastic `η_T` | `h=1e-10` | `4.817e-9` | Cancellation growth |
| Adjacent smooth-plastic FD change | `1e-6 → 1e-7` | `7.901e-10` | First stable decade transition |
| Adjacent smooth-plastic FD change | `1e-7 → 1e-8` | `6.686e-11` | Second stable decade transition |

At large steps, centered-difference error decreases with refinement, consistent with truncation error. At the smallest steps it increases, consistent with floating-point cancellation; that behavior is not evidence of a constitutive defect. The revised `C_ref` only increases the normalized denominators for this fixture, so the figures above upper-bound those normalized values under the proposed reference scale.

The yield-switch fixture reports one-sided engineering-shear slopes of `400 MPa` on the elastic side and `30.76923077 MPa` on the plastic side. The branch change is nonsmooth and must not be treated as a smooth centered-tangent failure.

The perfect-plastic stress test verifies a deviatoric stress plateau at the yield stress as strain increases and accumulated plastic strain grows. It does **not** differentiate the plateau tangent. Existing loading/unloading/reloading/reverse-loading tests compare stress and state to the tensor oracle, but current tangent sweeps do not start from a nonzero accepted plastic state. Small plastic multipliers and a controlled approach to the yield switch are not yet numerically characterized. These are P2 coverage gaps, not observed failures.

## C — Extremal input and state robustness

The existing authorized material-point tests cover finite-but-unrepresentable elastic stiffness, finite strain whose trial stress overflows, and a nonfinite tangent injected at the tangent seam. All three refuse the trial before returning a constitutive state. Source review also confirms checks after trial equivalent-stress/yield calculations and after corrected scalar, array, work-diagnostic and tangent calculations (`solid.py:143-256`).

Boundaries: these tests do not exhaust every overflow route (for example overflow in hardening/yield products or accumulated work) or prove cross-field coherence of arbitrary externally supplied accepted states. The source checks finite shape/scalar validity but does not verify every algebraic relation among an externally supplied state's stress, strain, plastic strain and energy fields. No defect was observed in exercised cases; these remain P2 coverage risks.

## D — Newton/J2 interface and bounded synthetic suite plan

Source trace:

- The J2 material returns trial stress, tangent and a copied state from the incoming material state (`src/solveur/materials/solid.py:143-274`). Solid element paths collect trial integration-point states; the corotational route also returns a tangent through the element assembly path (`src/solveur/elements/solid/corotational_j2.py:408-465, 657-795`).
- E01-A evaluates the free-DOF residual and assembles internal tangent from a trial state through the internal nonlinear driver; transaction state is detached and commits or rolls back through `NonlinearStateTransaction` (`src/solveur/core/nonlinear/load_control.py`, `src/solveur/core/nonlinear/driver.py`, `src/solveur/core/nonlinear/state.py:149-256`).
- `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` is empty. `derivative_certificate(route_id)` fails closed for an uncertified route (`src/solveur/core/nonlinear/e01a.py:36-38, 450-467`). Thus the positive production E01-A/J2 Armijo route cannot be exercised without a separate certificate decision.
- The typed admissibility helper creates a versioned evidence object with component, criterion ID and maximum admissible increment (`e01a.py:57-138`). The checkpoint ledger stores attempt/state identities, interval, classification and rollback flag but not that full evidence payload (`load_control.py:578-593, 754-770`; validator `e01a.py:634-856`).

### Proposed bounded offline test inventory (not authored or run)

Use one test-local generalized material point, no mesh or element assembly: one scalar displacement `u`, a fixed kinematic map `ε(u)=B u`, and scalar weight `w`. The synthetic internal force and tangent are:

\[
f_{int}(u,z_n)=w B^T\sigma(Bu;z_n),\quad K(u,z_n)=w B^T C_{alg}(Bu;z_n)B,
\]
\[
R(u,\lambda,z_n)=\lambda F-f_{int},\quad J_R=-K.
\]

An independent one-dimensional elastic / linear-hardening reference supplies the solution and residual derivative. Keep `z_n` immutable for all derivative probes. Separate cases should cover:

1. elastic response and smooth linear-hardening response with a unique reference equilibrium;
2. perfect-plastic plateau as a constitutive response, without demanding a unique force-controlled post-yield displacement;
3. plastic loading followed by unloading/reload from a nonzero accepted state;
4. trial-state creation, forced rejection, rollback digest equality, half-step retry, and exactly-once accepted commit;
5. accepted-state checkpoint serialize/reconstruct and rejection-ledger persistence, with corrupted/mismatched identity refusal;
6. retryable typed admissibility versus unknown/invalid terminal failure; and
7. E01-A certificate lookup with the production registry empty, which must refuse before any positive Armijo solve is claimed.

For the positive synthetic Newton oracle, use an internal test harness or generic internal Newton driver with no public model/solver facade, and compare every accepted state against the independent scalar reference. Do not label it as an E01-A Armijo-route PASS. Until a separate Owner-approved route certificate exists, the E01-A/J2 integration portion is a negative refusal test only. This plan is ready for an Owner-authorized bounded offline test, but no new execution module was created in this campaign.

## E — Checkpoint typed-evidence proposal

Recommend an additive, versioned retry-evidence object under the E01-A metadata subrecord. Each retryable admissibility rejection should persist the original typed evidence, including:

```text
schema = "qf-wp-e01-a-increment-admissibility/v1"
classification = "INCREMENT_DEPENDENT_FINITE"
attempted_increment
state_finite = true
unclassified_components = []
components = [{component, criterion_id, maximum_admissible_increment}, ...]
```

Bind the evidence to the ledger entry's attempt ID, accepted-state identity, failure reason and attempted increment, and store a digest over canonical serialization of that evidence. On validation, require every maximum admissible increment to be strictly below the attempted increment; reject duplicate/unknown components, inconsistent digest, mismatched base state or absent typed evidence for a new retryable admissibility failure.

Keep the outer WP10 v2 record and identity semantics unchanged. Do not invent evidence for historical records. Owner decisions still needed: exact subrecord versioning, canonical serialization/digest recipe, and whether a legacy v2 retry checkpoint without typed evidence is readable as historical-but-unverifiable or must fail closed for resume. Do not rewrite archives or silently reset the 25-rejection ledger.

## F — Historical `plastic_dissipation` semantics

| Route | Existing formula | Source-supported meaning | Decision |
|---|---|---|---|
| Direct material point | `D_n + 0.5*(sigma_n+sigma_{n+1}) : Delta_eps_p` | Endpoint-trapezoidal stress work using tensorial stress shears and engineering plastic-strain shears; energy density | Preserve field name and values; not proven equal to exact plastic work integral or thermodynamic dissipation |
| Corrected corotational state | `sigma_y0 * alpha_{n+1}`; separately `hardening_energy = 0.5*H*alpha_{n+1}^2` | Distinct route-specific yield-work-like cumulative term plus stored hardening energy | Preserve existing values; do not harmonize or reclassify |

Generic solid serializers filter `plastic_dissipation`, and the public solid subset omits both it and `hardening_energy` (`post/solid_results.py:512-539`, `post/solid_recovery.py:167-194`). New public energy fields remain deferred by the Owner freeze. No historical result or API behavior changed.

## Findings and Owner decisions

- **P0:** none found.
- **P1:** none found in the inspected material-point and internal policy paths.
- **P2:** (1) revise the tangent reference from `K+2μ` to `max(3K,2μ)` before freezing the gate; (2) add nonzero-history, small-plastic-multiplier and branch-approach derivative cases before generalizing evidence; (3) persist typed retry evidence in a reviewed additive schema if retry auditability is required; (4) keep direct and corotational energy semantics explicitly distinct.

Owner approval is still needed for `τ_T=1e-8` and the plateau rule, typed-evidence checkpoint version/legacy resume policy, and any executable Newton/J2 integration campaign. A production Armijo certificate is a separate decision. No scientific acceptance threshold or contract was frozen here.

## Test chronology and safety

This B3 campaign reran only the previously authorized, unchanged J2 numerical-unit module:

```text
python -m pytest -q -s tests/unit/test_wp_e01b_j2_constitutive_oracles.py
28 passed in 0.83 s
```

Preflight verified the module digest and the `NUMERICAL_UNIT` registry entry. A top-level import-closure AST pass including package initializers examined 12 project modules; it found no eager Gmsh, ctypes, subprocess or multiprocessing imports. The Gmsh probe in `tests/conftest.py` is conditional on the two Code_Aster optional mesh modules, not this test. The test source calls only Python/NumPy material-point references and the direct constitutive API. No test files or classifications changed.

The E01-A results (39 integrated and 25 policy/collection tests passing) are carried forward from B2 and were **not rerun** in B3. No numerical thresholds were added to assertions. The production Armijo registry remains empty.

## Evidence and repository state

| Artifact | SHA-256 |
|---|---|
| `src/solveur/materials/solid.py` | `7d8223c81999d037900c26bf1a6a2abc9f4b47c0cff597f4be0cf0163e8092aa` |
| `src/solveur/core/nonlinear/e01a.py` | `c0dc0ebfb56fc2da52afca89550adc922e2a52ed04c0b53a2f4a9022cc7bc139` |
| `tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | `e7327058ddb5d107b7788dd69d1727794a2f4c22598c03426bb01253257703be` |
| `tests/conftest.py` | `5f90d53935a25bbfab31818d6988d30c3fdecfb74a573273e270311d468111b8` |
| B2 campaign evidence | `23df95497abe4283b81b3d6a5728f39dc97f3a8d97a979c8420b143fe7ecdd99` |

No source, test, canonical roadmap, historical archive, WP-D01 or WP-D02 file was changed in B3. The only planned change is this report. The final documentation commit and report hash are recorded in the delivery message.

## Final statuses

```text
J2_TANGENT_GATE: PROPOSED_FOR_OWNER_FREEZE / INCOMPLETE
J2_TANGENT_EVIDENCE: VERIFIED_BOUNDED / FINDINGS
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
J2_YIELD_TRANSITIONS: CHARACTERIZED / INCOMPLETE
NEWTON_J2_INTEGRATION: READY_FOR_BOUNDED_OFFLINE_TEST
CHECKPOINT_TYPED_EVIDENCE: SCHEMA_PROPOSED / BLOCKED
PLASTIC_DISSIPATION: HISTORICAL_SEMANTICS_PRESERVED
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

`READY_FOR_BOUNDED_OFFLINE_TEST` means the synthetic test specification is ready for a separate Owner GO. No new test module was authored or executed; the positive E01-A/J2 Armijo path remains blocked by the empty production certificate registry.
