# Proposed WP12 execution waves

**Status:** PREPARATION_ONLY — no wave authorized.
**Numerical execution:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

The sequence prioritizes scientific risk and reuse of independent oracles. A wave may be split into exact per-node units. Any proposal to execute a broad campaign must be independently scoped and approved; do not launch a whole directory.

| Wave | Scope and objective | Entry gate | Representative test/case families | Cost | Exit evidence |
|---|---|---|---|---|---|
| 0 — Plan/criteria approval | Approve matrix, statuses, case identities, local policy, criteria and storage plan | Owner accepts `LOCAL_VV_POLICY_PROPOSAL.md` and `OWNER_PLAN_DECISION.md`; resolve any conflict with AGENTS.md | No solver tests | None | Signed/recorded policy decision; exact sequence and criteria freeze |
| 1 — Theory and components | Establish low-cost algebraic identities and bounded small-system checks | Exact nodeid and test side effects inspected; science tree and venv recorded | ALG-PROJ-001 (algebraic); discrete spring-mass modal; coupled modal 2DOF (same-backend unless independently derived scalar oracle is added); undamped SDOF modal Newmark; affine element patches; excitation phasor | Low | Per-case raw values; oracle-independence label; all assertions understood; failures preserved |
| 2 — Linear FEM | Test representative static/modal response, reactions, stress and at least one spatial study | Wave 1 identities understood; mesh/load/reference contract frozen | Beam cantilever; TET4/TET10/HEX8/HEX20; beam and shell bounded cases; mesh convergence | Low to medium | Independent analytic/reference comparison plus documented mesh trends; no unexplained balance error |
| 3 — Dynamics and reductions | Check direct/modal Newmark, direct/reduced harmonic, base input, checkpoints and D02 | Wave 1; route dependencies and projection change reviewed; exact assumptions match | WP04 five projection nodes + modal 2DOF; WP05 impedance; WP06 oscillator/time refinement/checkpoint; WP07 base acceleration; D02 | Low to medium | Contract-level assertions and independent oscillator oracle; direct/reduced comparisons labeled internal |
| 4 — Advanced physics | Address bounded J2, nonlinear state, contact, shells/composites and D01/D02 boundaries | Separate Owner scope per package; preserved negative/inconclusive records; fixture identity/quality checked | WP08–10; C01 prospective repair; C02 AR/N03 only; E01 point/element/global distinctions; D01 | Medium to high | Scoped PASS/FAIL/INCONCLUSIVE by criterion; no cross-scope promotion |
| 5 — Inherited rotor and selected backends/performance | Demonstrate selected rotor/API continuity and bounded resource behavior | Rotor plan and performance protocol approved; low-cost sentinels first | GYRO identity tests; Campbell ambiguity/refusal sentinel; SciPy/PETSc small comparison; bounded scaling | Medium to high | Exact source-run identity; complex mode/subspace handling; performance conditions and limits |
| 6 — External correlation | Compare selected compatible cases with Code_Aster/CalculiX | Correlation mapping complete; exact external version/container/input identities; external execution separately approved | TET4/TET10 static/dynamic; BEAM2; selected shell/composite, contact, J2, RBE2 | High / environment-dependent | Same-observable, same-convention reports; classification as correlation, not physical validation |
| 7 — Consolidation | Resolve matrix status per approved criterion and recommend WP12 disposition | Prior waves’ evidence archived and independently reviewed | No new solver call by default | Low | Complete traceability, residual gaps, fail/inconclusive inventory, Owner decision request |

## Work-package crosswalk

The numbers in the old WP12-A/B/C manifests refer to that earlier plan and must not be repurposed. The current scientific waves are a crosswalk only:

- WP12-1 (previous preparation): modal projection/contract checks; proposed here in Wave 1 and the WP04 slice of Wave 3.
- WP12-2: dynamic/prepared system checks; Wave 1 then Wave 3.
- WP12-3: nonlinear and contact; Wave 4.
- WP12-4: inherited/transversal regression; Waves 2, 3 and 5 by dependency.
- WP12-5: performance; Wave 5.
- WP12-6: consolidation; Wave 7.

This crosswalk creates no new work package, manifest approval, or campaign run. WP12 remains OPEN.

The proposed first local sequence is projection identity, discrete spring-mass modal frequency, coupled 2-DOF modal case, undamped SDOF modal Newmark, then the parameterized BEAM2 case and bounded TET4 multi-mesh utility. Only the first is algebraic-only; the next three invoke solver/analysis paths. The existing 2-DOF test is not an independent eigenvalue oracle because it uses SciPy `eigh` for the expected result and the production route uses SciPy `eigh` as well. The beam parameter suffix and TET4 plan/output/acceptance need resolution and Owner approval before they are launch-ready.

## MUST / SHOULD / DEFERRED

### MUST before a bounded WP12 closure recommendation

- Current science candidate identity and clean source state are recorded.
- Contractual WP12 routes are represented in the matrix and each has a current candidate evidence disposition.
- The projection change has the narrow downstream regressions required by WP04–WP07 claims.
- At least one finite-observable FEM case has a defensible analytic or convergence strategy if the approved WP12 scope claims FEM accuracy.
- Every FAIL, INCONCLUSIVE, NOT_ACQUIRED, and NOT_RUN is preserved and dispositioned.
- No acceptance rule was changed after results were observed.
- Runner/local execution governance is Owner-approved and followed.

### SHOULD

- Add cross-family TET/HEX/BEAM or shell representative checks where users rely on those routes.
- Run a small backend comparison with the optional backend actually installed.
- Independently review complex stress/phase conventions and nonlinear state identity.
- Add performance baselines for the most used routes with repeatable machine metadata.

### DEFERRED unless claimed or separately contracted

- Full GYRO-05/GYRO-06 historic mesh-speed sweeps; 100 rad/s ambiguity remains recorded.
- Large MPI and multi-million DOF benchmarks.
- General Code_Aster/CalculiX matrix across every family.
- General finite sliding, arbitrary contact meshes, global Hencky/Newton, generic rotor-machine qualification, and broad experimental material qualification.
