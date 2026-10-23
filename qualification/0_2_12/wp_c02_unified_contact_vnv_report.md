# WP-C02-Z — Unified Frictionless Contact FEM Verification

**Current bounded status:** `WP_C02_STATUS=CLOSED_BOUNDED` for WP-C02-AR/N03 only (Owner decision N13). The broader/general WP-C02 contact route remains OPEN / EXPERIMENTAL_TARGET.
**Execution branch:** `codex/wp-c02-z-unified-contact-vnv-20261021`
**Test execution HEAD:** `1344321f61d09fc010389019d059b54346a88a28`
**General contact scientific qualification:** NOT_ACQUIRED. **WP-C02-AR/N03 bounded benchmark:** CLOSED_BOUNDED; no asymptotic or general-contact claim.
**WP-C01:** CLOSED_NEGATIVE / UNCHANGED.

## 1. Executive scientific conclusion

WP-C02-Z completed one guarded collection of the frozen 14-node module and one guarded run: **14 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed**. The run used the experimental mixed-contact solver with the repository’s actual `GlobalAssembler` and linear TET4 element stiffness for a small fixed triangular-prism model. It was a genuine bounded assembled mechanical reference against one frozen rigid triangular face, with one slave node and one scalar normal multiplier. It was not a public solver, native backend, general contact search, multi-contact, or large-scale FEM campaign.

The assembled stiffness matched an independently formed element-level BᵀCB scatter to a maximum relative error of 2.661e-16. Active KKT gaps were within 4.58e-20 m of zero; normalized free mechanical residuals were at most 1.674e-15. Reported force and moment imbalance maxima were 7.571e-13 N and 3.712e-13 N·m, respectively. These are excellent algebraic closure results for this tiny fixture. However, the support-force vector is reconstructed from constrained residual entries and then participates in the reported global balance; it is not an independent support-reaction oracle. Local contact action/reaction transfer has an independent geometric force/moment reference, but this does not make support reactions independently measured.

The mesh family holds prism geometry and volume constant over n=1,2,3, but the contact reaction is applied at one slave point. Its multiplier changed from 155.667 N to 34.9785 N to 13.9885 N while the top displacement at the selected observation point changed from -0.339333 mm to -0.335144 mm to -0.334021 mm. The large point-reaction change means **spatial mesh convergence of contact force was not acquired**. The three displacement values are approaching one another, but there is no analytical continuum reference, no demonstrated asymptotic regime, and no defensible convergence-order estimate. This is not evidence of successful contact-force convergence.

The “release” fixtures are independent static solves at a reduced 0.5 N downward load, not increments advanced from the previously active accepted state. Thus OPEN and ACTIVE states are verified for the defined cases and an independently solved low-load OPEN case is verified, but an OPEN → ACTIVE → RELEASE history is **not verified**. General contact qualification, updated-geometry consistency, edges/corners, friction, multiple simultaneous contacts and external correlation remain outside the evidence.

Recommendation: retain the current narrow experimental single-point, frozen-face scope. Before seeking a broader engineering maturity claim, obtain an independently balanced support-reaction oracle and a physically appropriate distributed/finite-area contact benchmark with mesh-refinement evidence. Keep WP-C01 CLOSED_NEGATIVE and do not merge or promote this work package automatically.

## 2. Exact source and execution provenance

### Frozen origin and continuation

The original WP-C02 checkout remained unchanged at:

- Worktree: `C:\Users\fari\Documents\projet\SAFRAN\.codex-worktrees\wp-c02`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Branch: `emptiesvoids-cloud/wp-c02`
- Frozen HEAD: `2bd0fb769edb05d090ef17023173380c8fc853d0`
- Frozen Git tree: `c6ac54863f82962e3f941965e82db1b8f501be86`
- Tracked state: clean; existing Q evidence directory preserved.

The 516-file scientific source aggregate reproduced as SHA-256 `816554de0ff4ef30c115c9e01038bf7ed56565f9bc60886ed78cd818eea4c745`. It is a content aggregate, not a Git tree object ID.

The isolated continuation is `C:\Users\fari\Documents\projet\SAFRAN\.codex-worktrees\wp-c02-z`, branch `codex/wp-c02-z-unified-contact-vnv-20261021`. The run used frozen HEAD `1344321f61d09fc010389019d059b54346a88a28`. Two preparation commits precede execution: `e5f6a7b1` (prepare bounded verification) and `1344321f61d09fc010389019d059b54346a88a28` (pin the supervisor to the fixed Z worker). This report/evidence commit follows the executed HEAD; no scientific executable source or test is changed after execution.

### Executables and policy

| Item | SHA-256 |
|---|---|
| Test module `tests/unit/test_wpc02_z_mesh_contact.py` | `d78d80773533d14c4f5cb271152045727915ebd0ab9410b31e6c1284fe5819b4` |
| Fixed Python worker `qualification/0_2_12/wpc02_z_guarded_pytest_runner.py` | `6f85105518f7408a514972653690493560985e2c54ca39645d30804785f7808f` |
| PowerShell launcher `qualification/0_2_12/wpc02_z_guarded_pytest_launcher.ps1` | `a505f6a89d85eb75e03cc0e112c816fef844b93c58c39e711f7e6aadbc267894` |
| Windows supervisor bridge `qualification/0_2_12/wpc02_z_windows_supervisor.cs` | `5f18906a6132cde3b5afe093b0f2ab2ed8ac7468b524222bb3ab878ed4945031` |
| Source aggregate (`src/solveur/**/*.py`, 516 files) | `816554de0ff4ef30c115c9e01038bf7ed56565f9bc60886ed78cd818eea4c745` |
| Test policy `docs/verification/0_2_7/0_2_7_test_policy.md` | `a9e75c982b369b0937533fa64ecdf3b129bc7fb942fd379066cf74c1c0ada37a` |
| `conftest.py` | `d8c1cb0bfc88e7e35ba0868489a47401a69632c88ed2ce0b0802cca5c18504e0` |
| `pyproject.toml` | `15019a3f786920b886756a763a837415c4f8b059e122aa7a7372481db37ef834` |

The collection and run each used the one fixed test module, in-process `pytest.main`, one supervised Python child, preserved conftest safety, and no automatic retry. The worker’s Gmsh sentinel and plugin restrictions remained active. Static and independent source review confirmed no test path to public `solve_model`, native FEM, Gmsh initialization, external solver, worker creation, or subprocess. Runtime observed exactly one job process; no unexpected process association or process-limit event occurred.

### Exact commands

Collection (one invocation):

~~~powershell
pwsh.exe -NoProfile -File qualification/0_2_12/wpc02_z_guarded_pytest_launcher.ps1 collect wp-c02-z-mesh-20261021-01 1344321f61d09fc010389019d059b54346a88a28 -ExpectedLauncherSha256 a505f6a89d85eb75e03cc0e112c816fef844b93c58c39e711f7e6aadbc267894
~~~

Run (one invocation, conditional on the accepted collection receipt):

~~~powershell
pwsh.exe -NoProfile -File qualification/0_2_12/wpc02_z_guarded_pytest_launcher.ps1 run wp-c02-z-mesh-20261021-01 1344321f61d09fc010389019d059b54346a88a28 -ExpectedLauncherSha256 a505f6a89d85eb75e03cc0e112c816fef844b93c58c39e711f7e6aadbc267894
~~~

The actual case inventory is 14 nodes: three assembly cases, three active cases, three open/separating cases, three independent reduced-load OPEN cases, one mesh-family check and one local frame-invariance check. The complete list is in the immutable run receipt and manifest.

## 3. Historical WP-C02 evidence audit

Historical reports A through P and preserved execution receipts were reviewed. The old cases overlap in implementation and mathematical coverage; cumulative counts are not independent replications.

| Evidence family | Historical result | What it supports | Bounds / missing evidence |
|---|---:|---|---|
| Regular-face scalar and solver regression (G/I) | 39 PASS on the reviewed source identity | Scalar Signorini, regular-face projection, active-set and Fischer–Burmeister behavior in tiny algebraic cases | Not global FEM; no edge/corner contact; true cycling not verified. Historical residual maxima not re-derived here. |
| H1 boundary/history/force oracle | 23 PASS | Boundary-tolerance behavior, multi-transition helper case, local barycentric force/moment oracle | Active-set true cycling not verified; route-level master equilibrium unavailable. |
| K local transfer adapter | 29 PASS | Local transfer and frozen-geometry tangent on the isolated adapter | Does not establish updated-geometry tangent or public assembly. |
| L reduced mixed KKT references | 6 PASS | Small independently specified mixed equations and separate load configurations | Not global FEM. No accepted incremental path. |
| M mixed-system prototype | 10 PASS | Bounded mixed blocks and one-contact prototype behavior | Not full FEM or global nonlinear contact. |
| N direct one-contact solver | 22 PASS | One affine frozen-gap contact pair, direct open/active classification and helper-level state semantics | Not general nonlinear active-set Newton; history remains partial. |
| O original TET4/contact attempt | 4 PASS / 7 FAIL | Preserved original negative evidence: six active-branch `UnboundLocalError` failures and one floating-point gradient-oracle failure | Never overwrite this outcome with corrected results. |
| P corrected TET4 tests | Not run at P | Source correction and test-oracle diagnosis only | The later Y campaign is the actual corrected-source execution evidence. |
| Y corrected TET4/global adapter | 22 PASS, 0 failures | Bounded corrected TET4 contact reference and adapter modules, exact receipts retained in original checkout | Do not rerun or infer broader qualification. Collection/run receipts: `c3f8dab597c89be43dd30dc68a54027c99b94adb29b344ea0493f132916463a7`, `4c83534eb556cda855b29427f75ba81448494c92b71cc5459801cfcd05805da4`. |
| Z authentic small-mesh campaign | 14 PASS, 0 failures | Results detailed below | One small fixed-face contact point and three discrete mesh levels; no continuum qualification. |

The historic “129 successful cases” count combines overlapping suites and source revisions. It must not be read as 129 independent physical verifications. WP-C01’s negative status and its distinct frictional/contact qualification limitations remain untouched.

## 4. Local contact formulation and conventions

The tested mechanical convention is frictionless Signorini contact with a frozen planar master face and one slave point. Unit normal `n` points from the rigid master toward the admissible slave side. Signed gap `g` is positive when separated and zero at contact; penetration corresponds to `g < 0`. The scalar multiplier `λ` is a compressive reaction magnitude with `λ ≥ 0`. In the test’s chosen generalized coordinate, the mixed KKT mechanical correction uses the approved one-contact experimental solver; the global sign convention is encoded by the contact gradient and slave/master transfer vectors. The tests check nonnegative multiplier, gap feasibility, `g λ = 0`, and equilibrium for each state.

For the fixed face, projection is the orthogonal projection onto its plane, followed by regular triangular-face barycentric eligibility. The normal gap is affine in the slave displacement. Its gradient is the oriented unit normal; the local frame test obtains finite-difference derivative `1.0000000000000073` against exact `1.0`. No moving normal, finite sliding, projection sensitivity for an updated face, or `λ Hessian(g)` term is exercised. A positive planar gap does not alone make an out-of-patch projection admissible; the regular-face feature contract remains in force.

The local geometry fixture reports `n=(0,0,1)`, gap `1e-5 m`, barycentric weights `(0.16666666666666674, 0.39999999999999997, 0.43333333333333335)`. Translation changes the reported gap by about `6.55e-17 m`; a proper rotation retains `1e-5 m`; cyclic vertex ordering permutes weights consistently; a 1e-3 geometry scale gives gap `1e-8 m`. These are bounded transformations on one regular face, not broad projection qualification.

## 5. Local and assembled numerical results

### Mesh geometry and assembly

The physical body is a unit-height triangular prism with triangular cross-section vertices `(0,0)`, `(1,0)`, `(0,1)`, volume `0.5 m³`. Material is linear small-strain isotropic elasticity, `E=3 MPa`, `ν=0`. The mesh generator creates n=1,2,3 comparable subdivisions. The top triangular surface has area `0.5 m²`; a uniform `1000 Pa` pressure gives a `500 N` resultant. One bottom slave node interacts with a fixed rigid triangular face placed at a `1e-5 m` reference gap. The mechanical mesh is TET4; one scalar normal contact constraint is used. Full assembled systems have 27, 63 and 129 DOFs, with 4, 13 and 31 free vertical DOFs after supported Dirichlet conditions.

An independently formed constant-strain TET4 stiffness and explicit scatter were compared with `GlobalAssembler` output. Element stiffness values, mesh volumes and connectivity are preserved in the source/test and logs; the independent oracle does not call the production element stiffness helper.

| Level n | Nodes | TET4 | Total DOFs | Free DOFs | `h_max` (m) | Volume (m³) | Relative stiffness error |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 3 | 27 | 4 | 1.4142135624 | 0.5000000000 | 0 |
| 2 | 18 | 24 | 63 | 13 | 1.1180339887 | 0.5000000000 (roundoff) | 2.6609e-16 |
| 3 | 40 | 81 | 129 | 31 | 1.0000000000 | 0.5000000000 | 1.9957e-16 |

The independent assembly reference is strong bounded evidence for this material, element geometry and DOF ordering. It does not independently verify a continuum solution or all possible prescribed displacement patterns.

### Active compressed contact

The applied top pressure is `+1000 Pa` downward (resultant `−500 N` in z). Values below are actual test output; moment and force imbalances are the emitted algebraic balance metrics. Support resultants are reconstructed from fixed-DOF residuals and therefore are not independent reaction measurements.

| n | λ (N) | gap (m) | observed top `u_z` (m) | strain energy (J) | normalized free residual | force imbalance (N) | moment imbalance (N·m) | KKT error |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 155.6666667 | −4.5740e-20 | −3.3933333e-4 | 8.3388333e-2 | 4.0594e-16 | 5.6843e-14 | 8.6043e-14 | 5.6844e-17 |
| 2 | 34.9784981 | 1.3553e-20 | −3.3514416e-4 | 8.3366774e-2 | 1.2094e-15 | 9.9856e-14 | 7.1695e-14 | 8.5266e-17 |
| 3 | 13.9884627 | −1.6941e-21 | −3.3402140e-4 | 8.3355984e-2 | 1.5494e-15 | 6.4543e-13 | 4.6299e-13 | 2.1323e-17 |

Across all state cases, maximum normalized free residual was `1.67325e-15`; active gap absolute error was at most `4.574e-20 m`. The contact force transfer error was at most `3.015e-14 N`. The discrete KKT reference error was at most `5.685e-17` in its normalized measure. The test reports no penalty formulation; this is a mixed one-multiplier formulation.

## 6. TET4 stiffness and FEM assembly

The test constructs physical node coordinates, tetrahedral connectivity, isotropic material parameters and a `FiniteElementModel`, then invokes `GlobalAssembler`. It checks positive element volumes and compares the assembled stiffness with explicit element-level constant-strain matrices and scatter. Mesh DOF counts and top-facet load resultant are emitted in structured JSON. This is authentic small-model FEM assembly, not a hand-entered global stiffness matrix.

The independent stiffness formula uses the TET4 shape-function gradients derived from the inverse edge matrix, builds the engineering-strain `B` matrix, forms `V Bᵀ C B`, then scatters by the test’s explicit element DOF map. Maximum relative discrepancy is `2.661e-16`; maximum absolute discrepancy is `9.313e-10` in stiffness units. Global dimensions remain tiny. No native mesh generator, native solver or public solve route is involved.

The available comparison does not independently certify every elasticity boundary-value solution, material parameter convention, arbitrary element orientation, nonzero prescribed motion, or large-model sparse assembly. The fixtures use supported simple Dirichlet conditions and linear small-strain elasticity only.

## 7. Contact KKT and residual verification

The experiment creates one frozen regular-face constraint and one multiplier degree of freedom, with the free displacement subsystem assembled from TET4 mechanics. It solves the open mechanical system and, when required, the active KKT branch. The active branch imposes zero normal gap; the open branch uses zero multiplier and checks positive gap. The test compares against a separately assembled reduced KKT reference, checks multiplier sign, complementarity and normalized residual.

No penalty parameter is present, so penalty sensitivity is NOT_APPLICABLE. The active constraint rank is one in each case. Redundant/multiple contact constraint rank and singular multi-pair systems are not covered by this mesh family. The configuration is a one-slave/one-face fixed geometry experiment; it does not validate general multiplier indexing, multiple-face search, or contact-state transactions.

## 8. Open, active and reduced-load response

| Case | Load resultant in z (N) | λ (N), n=1/2/3 | Gap (m), n=1/2/3 | Finding |
|---|---:|---|---|---|
| Active compression, 1000 Pa | −500 | 155.667 / 34.9785 / 13.9885 | −4.574e-20 / 1.355e-20 / −1.694e-21 | Active KKT state, λ≥0, gap≈0 |
| Separating load, −1000 Pa | +500 | 0 / 0 / 0 | 1.61515e-4 / 7.22991e-5 / 5.08792e-5 | Open state with positive gap and zero contact force |
| Reduced compression, +1 Pa | −0.5 | 0 / 0 / 0 | 9.84848e-6 / 9.93770e-6 / 9.95912e-6 | Separately solved open state |

This establishes three classes of static solution for the tested model. The third class is not a transition from the preceding active solve. No accepted state is carried, and no state history or rollback was executed. Thus `OPEN_ACTIVE_RELEASE_CASES` is bounded-partial; `INCREMENTAL_CONTACT_HISTORY` is NOT_VERIFIED.

## 9. Incremental active-set evidence

There are no complete load-step active-set histories for this Z module. The direct solver performs bounded one-pair open/active classification for each static case, but the “reduced compression” test creates a fresh solve at the lower load. It does not use the active result as an initial accepted state. No claim is made for incremental path dependence, trial acceptance/rejection, rollback, hysteresis or multi-contact switching.

## 10. Mesh family and spatial convergence

| Level | `h_max` (m) | λ (N) | top observation `u_z` (m) | energy (J) | volume (m³) |
|---:|---:|---:|---:|---:|---:|
| Coarse n=1 | 1.4142135624 | 155.6666667 | −3.3933333e-4 | 8.3388333e-2 | 0.5 |
| Intermediate n=2 | 1.1180339887 | 34.9784981 | −3.3514416e-4 | 8.3366774e-2 | 0.5000000000000001 |
| Fine n=3 | 1.0000000000 | 13.9884627 | −3.3402140e-4 | 8.3355984e-2 | 0.5 |

Physical prism, material, pressure, gap, frozen face and solver controls are fixed; only mesh subdivision changes. This makes the trend informative, but not sufficient for a convergence claim. The point multiplier changes by about 77.5% coarse-to-intermediate and 60.0% intermediate-to-fine. The displacement and energy changes are much smaller, but no independent continuum reference exists, and the mesh refinement ratio is nonuniform. A single slave point force can be strongly mesh dependent even when global displacement/energy stabilize. There is no basis to assign a reliable observed order to λ or to declare asymptotic convergence from these three levels.

**Conclusion:** `SPATIAL_MESH_CONVERGENCE: NOT_ACQUIRED`. The test does provide negative evidence against treating point reaction magnitude as a mesh-independent physical observable in this setup. A next study should use a finite contact patch or distributed contact traction and an independently known continuum or carefully controlled reference, with a defined physical observable and enough refinement levels to show an asymptotic trend.

## 11. Force, moment and reaction equilibrium

The local transfer oracle checks equal-and-opposite force and moment transfer for the one slave/rigid-face pair. Pair-force imbalance is zero as emitted in every case; pair-moment imbalance is zero for open states and at most `5.550e-14 N·m` for active states. Master-force transfer error is at most `3.015e-14 N`.

The global active and open fixtures report load, contact and support resultants plus moment imbalance. Across all emitted state records the maximum force imbalance is `7.571e-13 N`; maximum moment imbalance is `3.712e-13 N·m`. These small residuals show algebraic closure to floating-point precision for the prescribed fixture. However, support reactions are reconstructed from the constrained mechanical residual entries by the same implementation and then included in the balance. The global force/moment result is therefore a self-consistency check, not an independent support-reaction validation. The contact pair transfer remains independently referenced locally, but is not equivalent to a separate assembled master-side deformable force-scatter test.

## 12. Independent references and review

- **Implementer self-check:** completed against the independent element scatter, explicit KKT reference and geometry calculations in the test.
- **Independent source/result review:** completed by a separate permitted read-only reviewer after execution. The reviewer inspected the test/source and saved run receipts/logs; they did not execute or reproduce a second numerical run.
- **Independent numerical oracle:** bounded pass for TET4 stiffness construction/scatter, local projection derivative and one-contact KKT reference. Support reaction provenance is not independent; no independent continuum solution exists.
- **External solver correlation:** NOT_RUN in this campaign. Any earlier correlation remains historical and is not comparable evidence for this mesh family.

Review findings: no P0 or P1 issues. P2 limitations: (1) strong mesh sensitivity in the single-point multiplier; (2) support reactions are residual-reconstructed and re-used in global balance; (3) reduced-load release is a separate static solve, not history. These are retained as evidence limits, not fixed or masked.

## 13. Numerical failures and reproducibility limits

The Z run had no failed tests. Historical negative evidence remains: WP-C02-O had 4 PASS / 7 FAIL on the pre-correction code. Six failures were active-contact `UnboundLocalError`; one was an exact floating-point barycentric-gradient test mismatch. The active-branch assignment and four-ULP test-oracle comparison were subsequently corrected; the corrected-source 22-node Y run passed. Do not erase the original O failure.

The Z supervisor path itself was corrected before execution to target the Z fixed worker rather than Q. It was statically reviewed and then used for the single successful collection/run. Collection and run have complete receipts and log hashes. No retries occurred. Missing continuum and incremental metrics are not inferred from PASS outcomes.

## 14. Performance and memory

| Stage | pytest / worker | Parent wall | Peak committed memory | Limits |
|---|---:|---:|---:|---|
| Collection | pytest collection 0.87 s; worker 1.746359 s | 3.072754 s | 56,479,744 bytes | 1 GiB process/job, 60 s CPU where supported, 60 s parent wall, one active process |
| Run | pytest 1.01 s; worker 1.805513 s | 3.076043 s | 89,407,488 bytes | same |

The process-count limit and memory/time configuration were read back from the Job Object. Both collection and run had one primary Python worker, natural completion, no process-limit event, and confirmed cleanup. Runtime environment: Python 3.13.1, pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2. OpenBLAS pools were one thread before and after execution. Measured memory is far below the configured ceiling; it does not imply scalability beyond these models.

## 15. Unsupported feature matrix

| Feature | WP-C02-Z evidence/status |
|---|---|
| One frozen planar regular face, one slave node, frictionless normal | Bounded experimental fixture executed |
| Small-strain linear TET4 elasticity | Bounded authentic assembly executed |
| Open and active one-pair static states | Verified for defined cases |
| Local projection/frame invariance | Bounded single-face checks |
| Single point force/moment transfer | Bounded local oracle |
| Finite-area/distributed contact traction | NOT_SUPPORTED by this evidence |
| Mesh-independent point reaction | Not established; strong sensitivity observed |
| Accepted incremental OPEN→ACTIVE→RELEASE state | NOT_VERIFIED |
| General active-set cycling | NOT_VERIFIED |
| Updated normal/projection tangent and λ Hessian(g) | NOT_VERIFIED |
| Edge/corner or multiple normal contact | NOT_IMPLEMENTED |
| Multiple simultaneous contact constraints | NOT_VERIFIED |
| Nonconvex geometry, finite sliding or self-contact | NOT_SUPPORTED |
| Coulomb friction | OUT OF SCOPE |
| Plasticity, finite strain, impact/transient, follower loads | OUT OF SCOPE |
| Public FEM contact integration / native backend | NOT_RUN |
| Historical M4 failure resolution | PARTIAL only; not replayed |

## 16. Scientific maturity recommendation

The evidence supports **VERIFIED_BOUNDED experimental capability** for a tiny linear TET4 body against one fixed affine regular triangular face, using one slave point and one normal multiplier, with static open/active classification and the explicitly tested Dirichlet/load cases. It supports the local regular-face geometry, the one-contact KKT branch, and one independent element stiffness/scatter reference for those fixtures.

It does not support QUALIFIED_BOUNDED status for general FEM contact. The mesh-dependent multiplier and lack of independent support reaction oracle are material gaps for engineering force reporting. The route remains opt-in and experimental. Scientific promotion, public capability labels, production integration, release and closure require separate Owner decisions.

## 17. Remaining gaps

1. Define a physically representative distributed/finite-area contact problem whose force observable should converge with mesh.
2. Add an independent support reaction and moment oracle, not reconstructed from the same constrained residual used in the reported balance.
3. Demonstrate an accepted-state OPEN → ACTIVE → RELEASE incremental sequence with full transition and rollback records.
4. Expand mesh refinement only after items 1–2 define meaningful observables and an independent continuum/reference solution.
5. Review updated geometry terms before any moving-normal/foundation claim; specifically include gap-gradient sensitivity and the multiplier-weighted geometric Hessian where applicable.
6. Keep multi-contact, boundary features and nonconvex geometries refused until a separate mechanical formulation and verification campaign.
7. Keep historical M4 root cause PARTIAL until frozen comparable cases are independently exercised under a separately authorized campaign.

## 18. Integration preparation and next Owner decision

The continuation branch is isolated from `codex/v0.2.12-integration`; no merge or public solver change was made. The known authoritative integration baseline `cccf897f207c17ecad105948d231bf1240057184` was not modified. Proposed path: first decide whether to pursue a finite-area contact formulation and independent continuum benchmark or retain a single-point experimental demonstration. Only after the scientific scope is selected should an isolated adapter be proposed for the integration branch; do not infer that existing single-point results justify replacing public contact routes.

Pre-N13 recommendation: authorize a new bounded scientific work package for a distributed/finite-area regular-face contact benchmark, with an independent support reaction/moment oracle and a genuine accepted-state load sequence. Freeze its geometry, physical observables, mesh family, independent reference and acceptance criteria before numerical execution. The broader contact qualification remained open pending that review; N13 subsequently closed only the separately scoped AR/N03 benchmark.

### N13 Owner decision addendum — 2026-10-23

The preceding roadmap recommendation and status table record the pre-N13 state. The Owner has now approved `WP_C02_STATUS=CLOSED_BOUNDED` **solely for the WP-C02-AR manufactured TET4 fixed planar-face benchmark and prospective criteria N03**. The decision and exact evidence identities are recorded in `wp_c02_n13_owner_bounded_closure_decision.md`. This bounded closure does not close the broader contact qualification or integration work. The general-qualification gaps listed in §17 remain open; no Docker equivalence, asymptotic convergence, public capability, integration or release claim is made. Historical N06/N08 FAIL and Docker FAIL_CLOSED verdicts remain unchanged.

## Evidence files and hashes

The immutable stage directory is `qualification/0_2_12/wpc02_z_evidence/wp-c02-z-mesh-20261021-01/`. Its evidence manifest SHA-256 is `6648901f8351ac3d03641279a206efcf5df9de13f9a1db60f603cd1c660b123f` and its mesh table SHA-256 is `84e49ae6872203846a55810fc5bf7c85d87aecf49bfdddcd37b4e134a4d8db56`. The manifest records receipt and log digests, the 14 exact nodes, source identities, runtime versions, process accounting and scope.

| Evidence artifact | SHA-256 |
|---|---|
| Collection receipt | `d50792642d9ace04bd19c3070d2cccd7265e68b202ad81b48402edfc2d28fea2` |
| Collection stdout | `4807840460090c24a4fde0fed58f02669c46ffb0e7fd379c1810a405c80935f5` |
| Collection stderr | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Collection runner result | `ea370485adb65423c0caa605a5bc3e14ea66496ef20c8483669d774bdff5009b` |
| Run receipt | `90ab1aae36a79377e9af376fff9b4f374796cd760cfc69c3b410a24c315c6bf7` |
| Run stdout | `9afcf16613ba6721e500e8bf30808eb27b539bc6dab1e78fdbf3cbed9396c72c` |
| Run stderr | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Run runner result | `72c1ec514e67b0ddeea4c783910c8290c33a63083d3007cf91c33264d5dd522a` |
| Mesh observables CSV | `84e49ae6872203846a55810fc5bf7c85d87aecf49bfdddcd37b4e134a4d8db56` |
| Evidence manifest | `6648901f8351ac3d03641279a206efcf5df9de13f9a1db60f603cd1c660b123f` |

The two `.incomplete.*.bak` files are retained exactly as supervisor failure evidence from receipt publication attempts; the final collection and run receipts were subsequently published successfully. They are included in the stage evidence directory and must not be discarded.

## Final statuses

| Status | Result |
|---|---|
| `LOCAL_CONTACT_KINEMATICS` | VERIFIED_BOUNDED |
| `CONTACT_PROJECTION_AND_TANGENT` | PARTIAL |
| `TET4_REFERENCE_ASSEMBLY` | VERIFIED_BOUNDED |
| `AUTHENTIC_GLOBAL_CONTACT_FEM` | VERIFIED_BOUNDED for the stated tiny one-pair reference only |
| `CONTACT_EQUILIBRIUM` | VERIFIED_BOUNDED algebraically; support reaction oracle is not independent |
| `OPEN_ACTIVE_RELEASE_CASES` | PARTIAL |
| `INCREMENTAL_CONTACT_HISTORY` | NOT_VERIFIED |
| `SPATIAL_MESH_CONVERGENCE` | PASS_BOUNDED for WP-C02-AR/N03 M1–M5 only; asymptotic convergence not demonstrated |
| `ACTIVE_FRONT_M2_M5` | PASS_BOUNDED for the approved one-cell empirical criterion |
| `INDEPENDENT_SOURCE_REVIEW` | COMPLETED |
| `INDEPENDENT_NUMERICAL_ORACLES` | PASS_BOUNDED, limited to stiffness/scatter, projection derivative and KKT reference |
| `EXTERNAL_CORRELATION` | HISTORICAL_ONLY / NOT_RUN |
| `GENERAL_CONTACT_QUALIFICATION` | NOT_ACQUIRED |
| `DOCKER_EQUIVALENCE` | NOT_ACQUIRED; historical Docker campaigns remain FAIL_CLOSED |
| `WP_C01_STATUS` | CLOSED_NEGATIVE_UNCHANGED |
| `WP_C02_STATUS` | CLOSED_BOUNDED for WP-C02-AR/N03 benchmark only (Owner decision N13) |
| `AUTHORITATIVE_INTEGRATION` | PENDING |
| `PUBLIC_RELEASE` | NOT_AUTHORIZED |

### Exact collected and executed node inventory

These 14 nodes were observed at collection and are the complete RUN allowlist:

1. `tests/unit/test_wpc02_z_mesh_contact.py::test_uniform_tet4_mesh_assembly_matches_independent_element_scatter[coarse]`
2. `tests/unit/test_wpc02_z_mesh_contact.py::test_uniform_tet4_mesh_assembly_matches_independent_element_scatter[intermediate]`
3. `tests/unit/test_wpc02_z_mesh_contact.py::test_uniform_tet4_mesh_assembly_matches_independent_element_scatter[fine]`
4. `tests/unit/test_wpc02_z_mesh_contact.py::test_active_contact_mesh_family_equilibrium_and_kkt[coarse]`
5. `tests/unit/test_wpc02_z_mesh_contact.py::test_active_contact_mesh_family_equilibrium_and_kkt[intermediate]`
6. `tests/unit/test_wpc02_z_mesh_contact.py::test_active_contact_mesh_family_equilibrium_and_kkt[fine]`
7. `tests/unit/test_wpc02_z_mesh_contact.py::test_open_contact_under_separating_load_has_positive_gap_and_zero_reaction[coarse]`
8. `tests/unit/test_wpc02_z_mesh_contact.py::test_open_contact_under_separating_load_has_positive_gap_and_zero_reaction[intermediate]`
9. `tests/unit/test_wpc02_z_mesh_contact.py::test_open_contact_under_separating_load_has_positive_gap_and_zero_reaction[fine]`
10. `tests/unit/test_wpc02_z_mesh_contact.py::test_reduced_compression_releases_contact[coarse]`
11. `tests/unit/test_wpc02_z_mesh_contact.py::test_reduced_compression_releases_contact[intermediate]`
12. `tests/unit/test_wpc02_z_mesh_contact.py::test_reduced_compression_releases_contact[fine]`
13. `tests/unit/test_wpc02_z_mesh_contact.py::test_mesh_sizes_are_comparable_and_refine_in_all_prism_directions`
14. `tests/unit/test_wpc02_z_mesh_contact.py::test_regular_face_projection_and_gap_gradient_are_frame_invariant`

### Relevant experimental source identities

| Source | SHA-256 |
|---|---|
| `src/solveur/contact/experimental_complementarity.py` | `f9c40ddff876c1cb508a576da21ce5098e413e7ca23adc56403f409cb09c36c6` |
| `src/solveur/contact/experimental_fem_transfer.py` | `7cdc087591f347b44c5fa9f03a5377631332ebb0f07033c4a62653a737cbf9fc` |
| `src/solveur/contact/experimental_mixed_solver.py` | `c8ca8d945ef317dba316c7414b1d4b306e2d7c8861a0e4c8af1aa23a6da16b6b` |
| `src/solveur/contact/experimental_mixed_system.py` | `6665b501f1cb8ce280b76bc7b21c2ff44f141c5197915c285b277277b08dbf53` |
| `src/solveur/contact/experimental_regular_face.py` | `c808ae823e3a290a778f0fd030f12be12daf3a656a5765767db211b418fdb138` |
| `src/solveur/contact/experimental_tet4_assembly.py` | `45bd4095642ca2508b79040759a83231d30c39e640a98ee968fbe2929312b341` |

The stage directory’s `SHA256SUMS.txt` hashes every retained file, including the two incomplete receipt backups, and has SHA-256 `57a0e105d106d0645323b5701ee4cee59ae6647694f1808eb4d1d6bec7c529dd`.
