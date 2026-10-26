# QF Solver v0.2.12 — Integration roadmap overlay

**Original integration overlay date:** 2026-10-25
**Reviewed branch:** `emptiesvoids-cloud/0.2.12`
**HEAD at review start:** `8aa83f632643c389aed3b8c4e9223f8c422eee1a`

This file records the current integration decision that supplements the preserved Owner roadmap. The Owner-approved roadmap remains byte-preserved at [`owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md`](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md). The earlier integration snapshot is preserved verbatim at [`wp_e01_source_snapshot_ROADMAP.md`](wp_e01_source_snapshot_ROADMAP.md); its WP-E01 row reflects the status before Owner decision BC and is historical.

## Latest normative state — 2026-10-26

**Integration branch:** `emptiesvoids-cloud/0.2.12`<br>
**Integration HEAD assessed before this documentation update:** `557a4fda85d151aba57ed07671cdaedf15f47db7`<br>
**Frozen scientific candidate used by WP12-S:** commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.

This is the latest operational portfolio state as of 2026-10-26. It supersedes the dated 2026-10-25 snapshot below. Campaign execution records remain tied to their own manifests and source identities; their results must not be described as runs on the later integration HEAD unless the record says so.

### Normative portfolio disposition

| Work package | Current disposition |
|---|---|
| WP00 | `CLOSED` — positive historical closure |
| WP01 | `CLOSED` — positive historical closure |
| WP02 | `CLOSED` — positive historical closure |
| WP03 | `CLOSED` — positive historical closure |
| WP04 | `CLOSED` — positive historical closure |
| WP05 | `CLOSED` — positive historical closure; v0.2.12 reduced harmonic |
| WP06 | `CLOSED` — positive historical closure; v0.2.12 modal Newmark |
| WP07 | `CLOSED` — positive historical closure |
| WP08 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP09 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP10 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP-C01 | `CLOSED_NEGATIVE`; remediation remains `OPEN` |
| WP-C02 | `CLOSED_BOUNDED` — WP-C02-AR/N03 only |
| WP-D01 | `INCONCLUSIVE` — open |
| WP-D02 | `CLOSED_BOUNDED` — within its recorded scope |
| WP-E01 | `OPEN_WITH_BOUNDED_CERTIFICATES` — selected capabilities integrated; general qualification not acquired |
| WP11 | `CLOSED` — approved API/integration gate only |
| WP12 | `OPEN` — verification, validation, non-regression, and performance |
| WP13 | `OPEN` — packaging and publication |

Portfolio total: **19 work packages; 14 positive closures, 1 historical negative closure, and 4 open or inconclusive packages** (WP-D01, WP-E01, WP12, WP13). This is an administrative count, not a measure of scientific coverage, qualification, or release readiness. WP-C01's remediation remains part of that existing work package and is not an additional open package.

WP11 remains closed only for its accepted API, integration, traceability, result-contract, serialization, compatibility, and refusal scope. WP12 remains the scientific V&V and performance gate; WP13 remains the packaging/publication gate. No status below promotes maturity or grants publication approval. The [WP12 master plan](vv_master_plan/README.md) records these governance boundaries.

### WP12 progress — 2026-10-26

| Phase | State | Recorded outcome |
|---|---|---|
| WP12-P | Complete | Master V&V plan and inventory of 62 capabilities; planning artifact, not execution evidence. |
| WP12-Q | Complete | Local V&V policy and runner preparation; policy adoption did not authorize a scientific case. See the [Owner policy decision](vv_local/WP12_Q_OWNER_POLICY_DECISION.md). |
| WP12-R | Executed | 4/4 cases returned `PYTEST_PASS_ONLY`; numerical observables were `NOT_EXPOSED`. The later WP12-S extraction report preserves this distinction. |
| WP12-S | Executed | 8/8 authorized cases ran: seven receipts are `PYTEST_PASS_ONLY`, and one historical `FAIL` is preserved. `PYTEST_PASS_ONLY` is not an oracle verdict or qualification decision. |
| WP12-T | Complete | Scientific audit of modal 2-DOF and TET4 evidence; no new solver test, FEM run, benchmark, or mesh generation was performed. |
| WP12-U | Local execution report exists; branch records conflict | The local execution report records U1/U2 `PYTEST_PASS_ONLY` and U3 `FAIL`; a co-located summary and decision request still say `NOT_RUN`/`PENDING`. Those local files are untracked and were not changed or staged here. U3 remains `FAIL`; reconcile the records before integrating a normative U disposition. |
| WP12-V2-R3 | Development evidence complete; formal profile prepared | Three H1 development attempts are recorded; the successful pytest attempts remain scientifically `INCONCLUSIVE` for gamma assumptions. A new allowlist-compatible manifest is prepared but remains `PREPARED_NOT_AUTHORIZED`; no formal R3 run occurred. |
| WP12-W | Development study executed | H3/W1/W2 completed as bounded development observations; response and mesh-quality changes do not establish convergence or qualification. |
| WP04–WP07 regression sample | Partial | WP04–WP06 selected checks passed. WP07 has two passing nodeids and one `frequency_response` serialization failure; no status is promoted. |
| Representative element sample | Bounded | Selected BEAM2, TET10, HEX8, HEX20 and MITC4 tests passed; HEX8-SRI was not run because no suitable current numerical nodeid was selected. |

See the [WP12-R numerical extraction status](vv_local/wp12_s/Q1_Q4_NUMERICAL_EXTRACTION.md), [WP12-S execution report](vv_local/wp12_s/WP12_S_EXECUTION_REPORT.md), [WP12-T audit synthesis](vv_local/wp12_t_audit/SCIENTIFIC_AUDIT_SUMMARY.md), and [prospective experiment plan](vv_local/wp12_t_audit/PROSPECTIVE_TEST_PLAN.md). The new [accelerated V&V report](vv_local/wp12_accelerated/WP12_ACCELERATED_VV_REPORT.md) contains quantitative H3/W1/W2 development results, current selected-test receipts, and their limits. WP12-P/Q/T are preparation or audit milestones; they are not scientific test passes.

### WP12-S observations and limits

- **Modal 2-DOF:** the independent polynomial roots agree with the recorded computed eigenvalues to a maximum relative difference of about `1.89e-16`. The historical `MODAL-2DOF-POLY-001` test remains `FAIL`: its projected-stiffness assertion uses `atol=0` against theoretically zero off-diagonal entries, where roundoff of about `4.44e-16` fails. WP12-T classifies this as `TEST_CRITERION_DEFECT`; no solver defect is demonstrated by this failure, and the historical result is not erased. The prospective replacement has not been run. See the [modal root-cause audit](vv_local/wp12_t_audit/MODAL_2DOF_ROOT_CAUSE.md).
- **BEAM2:** two one-element bending-plane cases agreed with their Timoshenko expressions at roughly `5–6e-16` relative error. This is a bounded single-element comparison, not spatial convergence, 3-D validation, or general BEAM2 qualification.
- **Newmark:** the single recorded discretization has a final displacement error of about `5.95e-11 m`. One time step size was used; temporal convergence is not established.
- **TET4:** the recorded meshes contain 12, 96, and 768 TET4 elements with 36, 135, and 675 total DOFs. The finest-level tip result differs from the 1-D beam diagnostic by `66.69%`; the helper's `WARNING` remains. The audit checked archived volume, load/resultant and moment, support, topology, and mesh identities, but the cause of the deficit remains `INCONCLUSIVE`. The beam expression is not an exact 3-D oracle; no 3-D validation or asymptotic convergence is claimed. See the [TET4 reference audit](vv_local/wp12_t_audit/TET4_REFERENCE_AUDIT.md).

The [WP12-S report](vv_local/wp12_s/WP12_S_EXECUTION_REPORT.md) retains raw case statuses and recorded values. These bounded observations do not close WP12, establish general validation, or promote any capability's maturity.

### WP12-U local record reconciliation boundary

The Owner subsequently authorized the three WP12-U cases in conversation, and the local `WP12_U_EXECUTION_REPORT.md` records U1/U2 `PYTEST_PASS_ONLY` and U3 `FAIL`. The same untracked local directory contains a `SCIENTIFIC_RESULTS_SUMMARY.md` that says all three were `NOT_RUN` and an `OWNER_EXECUTION_DECISION.md` that remains `PENDING`. This disagreement is not silently resolved by this roadmap update: the local artifacts are not part of the Git branch, were not modified or staged, and must be reconciled before those outcomes are integrated as branch evidence. Preserve U3 `FAIL` in every record. The earlier proposal is superseded by the Owner authorization but remains represented by its separate preparation artifacts.

### WP12 accelerated development evidence — 2026-10-26

All results below remain development observations tied to their frozen science/test/runner identities, not to the integration HEAD. They do not change WP statuses or capability maturity.

- **H3/W1/W2 TET4:** mean loaded-face `UZ` was `-4.7956128932e-8 m`, `-8.6910285513e-8 m`, and `-5.0011257613e-8 m`. W1 increased the absolute response by 81.23% and reduced the difference to the 1D beam diagnostic from 66.69% to 39.63%; its element quality also improved substantially, so the mesh change is confounded. W2 changed response by 4.29%, but all 3,072 elements were below the existing quality threshold. Neither result establishes directional or asymptotic convergence. Peak memory was `NOT_MEASURED` for these runs.
- **WP04–WP06:** 6/6 WP04 projection checks (reconciled from exact JUnit), 3/3 WP05 reduced-harmonic checks, and 4/4 WP06 modal-Newmark checks passed. Their JUnit outputs do not contain measured error magnitudes, so the report records the existing oracle types rather than inventing errors.
- **WP07:** transient SDOF and TET4 full-mass-before-reduction checks passed. The harmonic SDOF assertions passed through the response/frame checks, then `ReducedHarmonicResult.from_dict(result.to_dict())` failed on inconsistent `frequency_response` metadata. The failure is preserved and requires a result-contract investigation; the group is not a pass.
- **Elements:** selected BEAM2 discrete V&V, TET10 affine patch, HEX8 rigid-mode/affine checks, HEX20 affine/face-load checks, and MITC4 zero-frequency consistency passed. HEX8-SRI remains unexecuted in the current sample.
- **R3 compatibility:** the campaign allowlist change is in commit `8b78db0aa169e787f5f36d6f8a2fa909bdd61489`; the revised manifest and Owner package remain `PREPARED_NOT_AUTHORIZED`.

See [WP12_ACCELERATED_VV_REPORT.md](vv_local/wp12_accelerated/WP12_ACCELERATED_VV_REPORT.md), which lists exact nodeids, manifest and JUnit hashes, the 62-row capability accounting, numerical limits, and the location of raw external evidence by receipt identity. See [V2_R3_MANIFEST_R2.json](vv_local/wp12_v2/r3/V2_R3_MANIFEST_R2.json) and [R3_OWNER_DECISION_PACKAGE_R2.md](vv_local/wp12_v2/r3/R3_OWNER_DECISION_PACKAGE_R2.md) for the unapproved formal R3 profile.

### WP-E01 disposition and publication boundary

`WP-E01=OPEN_WITH_BOUNDED_CERTIFICATES`. The selected E01 capabilities are integrated into the v0.2.12 candidate, but WP-E01 is **not officially CLOSED** and general qualification is not acquired.

- The isolated Hencky material-point kernel and directional material tangent have bounded evidence for their recorded scopes; both remain experimental, and the tangent evidence does not establish a robust convergence plateau.
- The historical Newton–Armijo GF4 certificate applies only to its identified TET4 deformable slave subsystem and its recorded source, manifest, and image identity. It is not evidence for global master assembly or for the current integration runtime.
- Global master-assembly equilibrium remains `NOT_VERIFIED`; the historical raw global BA verdict remains `FAIL`; the global J2 tangent remains unresolved; `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.
- Under the current Owner roadmap decision, WP-E01 is not a standalone mandatory publication gate. Do not add general WP-E01 closure as an extra condition for v0.2.12 publication. This does not waive the actual WP12/WP13 gates or alter any recorded Owner decision.

The [WP-E01 integration report](wp_e01_bc_integration_report.md) and [global scientific audit](wp_e01_bb_global_scientific_audit_and_closure_readiness.md) define the certificate boundaries and preserve the negative global result. The [Owner roadmap](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md) remains byte-preserved; this current disposition follows its recorded BC decision and the integration evidence.

### Publication and status interpretation

`WP11=CLOSED` is limited to its operational API/integration scope. `WP12=OPEN` and `WP13=OPEN`. `WP-C01=CLOSED_NEGATIVE` with remediation open; `WP-C02=CLOSED_BOUNDED` only for AR/N03; `WP-D01=INCONCLUSIVE`; `WP-D02=CLOSED_BOUNDED`; and `WP-E01=OPEN_WITH_BOUNDED_CERTIFICATES`. Administrative closure, implementation maturity, scientific evidence, and publication authorization are distinct. This update does not authorize further WP12 execution, close WP12/WP13, promote maturity, or publish v0.2.12.

## Historical snapshot — normative portfolio state as of 2026-10-25 (superseded)

This dated section preserves the operational state after the WP11 closure decision as recorded on 2026-10-25. It is superseded by the 2026-10-26 state above; its contents are retained as a historical snapshot without changing the underlying decisions.

| Work package | Current disposition |
|---|---|
| WP00 | `CLOSED` — positive historical closure |
| WP01 | `CLOSED` — positive historical closure |
| WP02 | `CLOSED` — positive historical closure |
| WP03 | `CLOSED` — positive historical closure |
| WP04 | `CLOSED` — positive historical closure |
| WP05 | `CLOSED` — positive historical closure; v0.2.12 reduced harmonic |
| WP06 | `CLOSED` — positive historical closure; v0.2.12 modal Newmark |
| WP07 | `CLOSED` — positive historical closure |
| WP08 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP09 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP10 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP-C01 | `CLOSED_NEGATIVE`; remediation remains `OPEN` — [R19 status register](wp_c01_r19_status_register.json) |
| WP-C02 | `CLOSED_BOUNDED` — WP-C02-AR/N03 only — [Owner N13 decision](wp_c02_n13_owner_bounded_closure_decision.md) |
| WP-D01 | `INCONCLUSIVE` — open — [integration report](wp_d01_stable_projection_integration_report.md) |
| WP-D02 | `CLOSED_BOUNDED` — within its recorded scope — [closure report](wp_d02_bounded_closure_report.md) |
| WP-E01 | `OPEN_WITH_BOUNDED_CERTIFICATES` — [integration report](wp_e01_bc_integration_report.md) |
| WP11 | `CLOSED` — operational API/integration gate only — [closure assessment](wp11_final/closure_gate_assessment.md) |
| WP12 | `OPEN` |
| WP13 | `OPEN` |

Portfolio total: **19 work packages; 14 positive closures, 1 historical negative closure, and 4 open**. This is an administrative count, not a measure of scientific qualification, coverage, or release readiness. WP00–WP10's historical scopes and statuses are preserved in the [Owner-approved roadmap](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md); WP08–WP10 are positive but bounded closures. WP-C01's open remediation is tracked against its negative historical closure and is not a twentieth work package. WP-D01 is included among the four open packages because its disposition is `INCONCLUSIVE`.

WP11 closed only for its approved API, integration, traceability, result-contract, serialization, documented-compatibility, and refusal scope. The [closure assessment](wp11_final/closure_gate_assessment.md) and [capability traceability matrix](wp11_final/capability_traceability_matrix.tsv) preserve the accepted boundary. Its closure does not require or imply rotor numerical non-regression. Rotor numerical V&V belongs to WP12; WP12 remains open. No WP12 solver checks or WP13 activities are executed by this roadmap update.

The WP12-0 preparation package is indexed at [qualification/0_2_12/wp12_preparation/README.md](wp12_preparation/README.md). It is preparation-only; its manifests do not authorize campaigns, and WP12 remains `OPEN`.

## Capacités héritées de v0.2.11 — Rotordynamique

These are already implemented v0.2.11 capabilities carried in the current source tree. They are inherited experimental routes, not newly created v0.2.12 work packages and not part of the v0.2.12 WP05/WP06 feature names.

### Rotating modal — `rotating_modal`

- Experimental small-perturbation model for a straight, connected, unbranched and collinear BEAM2 shaft, circular isotropic beam sections, and centered rigid axisymmetric disks attached at shaft nodes.
- Assembles structural `M` and `K` plus the disk unit-speed gyroscopic matrix `G`. Uses the signed-speed convention `M q̈ + ΩG q̇ + Kq = 0` with the frozen global axis and right-hand rule; speed is applied once.
- Solves the quadratic eigenvalue problem with a serial dense SciPy QEP and returns complex eigenvalues, frequencies, and complex modes.
- Historical WP05 verification GYRO-01 through GYRO-04 is recorded as PASS for the frozen contract and source identity. The route remains `EXPERIMENTAL` and has no general rotating-machinery qualification.

### Campbell — `campbell`

- Runs only over a finite, explicitly supplied, strictly increasing list of signed spin speeds; it does not generate or adaptively refine a speed grid.
- Tracks complex modes using the frozen complex MAC/global assignment policy, records branch lineage, handles degenerate subspaces, and preserves missing samples and unresolved associations as gaps or ambiguities.
- Historical WP06 verification GYRO-05 and GYRO-06 is recorded as PASS within their contracts. The high-frequency pair's ambiguity at 100 rad/s remains explicit; no branch is forced through it. GYRO-06 is internal mesh-convergence evidence, not independent physical validation.
- Maturity remains `EXPERIMENTAL`. A Campbell crossing is not a forced-response amplitude, unbalance-response prediction, operating-danger assessment, or instability verdict.

### Shared exclusions and maturity boundary

The source contracts reject distributed shaft gyroscopic terms, forced unbalance response, speed-dependent bearings or other speed-varying `M/K/G` inputs, general rotor damping (the accepted WP05 model is undamped), centrifugal prestress/stress-stiffening, contact/rubbing and nonlinear rotor response, and sparse/PETSc/SLEPc/MPI QEP backends. These routes do not qualify general rotating machinery. The exact model validators and refusal rules remain those in the frozen v0.2.11 contracts; this summary does not extend them.

The [v0.2.12 WP00 baseline](wp00_baseline_scope.md) and [frozen baseline contract](wp00_baseline_scope_contract.json) assign reduced harmonic response to WP05 and modal Newmark transient response to WP06. They mark prepared Campbell as optional and not selected, and place rotors outside the newly selected dynamic scope. Those statements define the new v0.2.12 work scope; they do not remove the separately released v0.2.11 rotating_modal and campbell capabilities from the inherited codebase.

| Release/work-package identity | Capability | Relationship |
|---|---|---|
| v0.2.11 WP05 | Gyroscopic model / rotating_modal | Inherited capability; GYRO-01–04 |
| v0.2.11 WP06 | Campbell / complex modal tracking | Inherited capability; GYRO-05–06 |
| v0.2.12 WP05 | Reduced harmonic response | Current-release feature; distinct numbering |
| v0.2.12 WP06 | Modal Newmark transient response | Current-release feature; distinct numbering |

WP numbering is release-specific; identical WP numbers across releases do not denote the same capability. See the [v0.2.11 WP05 contract](../0_2_11/wp05_gyroscopic_contract.json), [WP05 report](../0_2_11/wp05_gyroscopic_report.md), [v0.2.11 WP06 contract](../0_2_11/wp06_campbell_contract.json), [WP06 report](../0_2_11/wp06_campbell_report.md), [capability index](../../docs/capabilities/index.md), [rotating-modal guide](../../docs/mechanics/rotating-modal.md), and [Campbell guide](../../docs/mechanics/campbell.md).

The prospective WP12 checks are documented in [wp12_rotating_inherited_regression_plan.md](wp12_rotating_inherited_regression_plan.md). They are all NOT_RUN on the reviewed HEAD; the historical v0.2.11 records are not current-HEAD test results.

## Historical integration decisions and dated snapshots

### Snapshot — WP-E01 Owner BC, 2026-10-23
`WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`.

WP-E01 is included in v0.2.12 as an experimental capability set with strictly scoped evidence. It remains open and is not a standalone publication gate. WP11, WP12, and WP13 retain their own open validation criteria and are not closed by this decision.

- `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` applies only to the archived GF4 TET4 deformable slave subsystem and its exact historical source, manifest, and image identity.
- `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`.
- The raw global BA verdict remains `FAIL`.
- The global J2 tangent remains unresolved.
- Hencky material-point and directional-tangent evidence is bounded to its recorded tests; the tangent convergence plateau is not established.
- `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.

See [`wp_e01_bc_integration_report.md`](wp_e01_bc_integration_report.md) for the integrated file inventory, maturity matrix, tests, exact hashes, exclusions, and risks. The original Owner roadmap and historical reports remain unchanged.

### Snapshot — WP11 preliminary open position, 2026-10-23, before final closure

This section preserves the earlier open assessment. It is superseded by the
dated post-verification decision at the end of this overlay.

`WP11=OPEN`. The WP11-A audit and WP11-B traceability package cover the
capabilities present on this integration branch. The API surface and selected
serialization/refusal contracts have targeted non-qualifying regression
coverage; this does not close the complete WP11 integration gate by itself.
The ordinary result DTOs do not all have a shared versioned schema or generic
deserializer. WP11-B records this contract boundary for an Owner decision.

WP-D02 remains `CLOSED_BOUNDED` at its documented recovery scope. WP-E01
remains `OPEN_WITH_BOUNDED_CERTIFICATES`: the GF4 certificate is historical to
its exact TET4 slave-subsystem identity, master assembly equilibrium remains
`NOT_VERIFIED`, and the global J2 tangent remains unresolved. WP-C02 is now
`CLOSED_BOUNDED` only for the WP-C02-AR manufactured TET4 fixed planar-face
benchmark and prospective criteria N03. `GENERAL_CONTACT_QUALIFICATION` and
`DOCKER_EQUIVALENCE` remain `NOT_ACQUIRED`; no asymptotic convergence claim is
made. The N06/N08 and Docker `FAIL`/`FAIL_CLOSED` verdicts remain unchanged.
This does not close the broader contact route or alter the WP11, WP12, or WP13
criteria. D01 remains separate from the bounded C02 decision.

### Snapshot — WP11 review state during verification, 2026-10-25

The official state remained `WP11=OPEN` throughout verification. The Owner
decision accepts the operational API/integration scope and the heterogeneous
documented result contracts; no universal result schema or generic
`load_result()` is required. The exact
acceptance matrix, compatibility reserve, test results and exclusions are in
[`wp11_final/closure_gate_assessment.md`](wp11_final/closure_gate_assessment.md)
and [`wp11_final/owner_decision_followup_manifest.json`](wp11_final/owner_decision_followup_manifest.json).

This operational closure does not promote D01 (`INCONCLUSIVE`), expand C02
`CLOSED_BOUNDED` beyond AR/N03, or close E01 (`OPEN_WITH_BOUNDED_CERTIFICATES`).
Numerical V&V and performance remain WP12 work. No WP12 or WP13 execution,
merge to `main`, tag, package publication, or site publication is included.

See [`wp11_b_closure_gate_assessment.md`](wp11_b_closure_gate_assessment.md)
for the current gate assessment and recommended decision.

### Snapshot — WP11 Owner policy review before the final gate result, 2026-10-25

The Owner decision recorded for the operational API/integration WP11 resolves
the earlier questions above. The official status remains `WP11=OPEN` while the
current contract verification is completed. The acceptance scope is API
integration, traceability, result contracts, serialization, documented
compatibility, and refusals. Numerical V&V campaigns and performance
measurements belong to WP12. Any additional FEM execution requires its own
frozen manifest and separate authorization.

The heterogeneous documented result DTOs are accepted for v0.2.12; no
universal result schema or `load_result()` is required. Existing versioned
schemas, refusal rules, and stated limits remain in force. D01 remains
`INCONCLUSIVE`; C02 remains `CLOSED_BOUNDED` only for AR/N03; E01 remains
`OPEN_WITH_BOUNDED_CERTIFICATES`. None is promoted by WP11 API evidence. The
dated acceptance matrix and exact proof references are in
[`wp11_final/wp11_acceptance_matrix.tsv`](wp11_final/wp11_acceptance_matrix.tsv)
and [`wp11_final/owner_decision_record.md`](wp11_final/owner_decision_record.md).
This policy review did not alter historical ledgers or approve WP12, WP13,
merge, tag, or publication.

### Snapshot — WP-C02 integration and portfolio count before WP11 closure, Owner N13 / M-ERGE, 2026-10-23

`WP_C02_STATUS=CLOSED_BOUNDED` applies solely to WP-C02-AR/N03. The selected
integration is recorded in
[`wp_c02_integration_merge_report.md`](wp_c02_integration_merge_report.md);
it does not change the scientific scope or claim Docker equivalence. N10
execution results and their archive remain external and are linked by their
own manifest and integrity hashes.

The integration portfolio count recorded at that earlier point was
**19 work packages: 13 positive closures, 1 negative closure, and 5 open**. It is a
historical count from before the WP11 closure and is superseded by the
2026-10-25 normative count above. Neither count measures scientific maturity
or release readiness. The Owner roadmap remains preserved verbatim, and
`main`/public release are unchanged.

### WP11 CLOSE evidence — 2026-10-25

`WP11=CLOSED` for the operational API/integration gate (interfaces,
traceability, result contracts, serialization, documented compatibility and
refusals), following the acceptance criteria approved by the Owner. The
closure dossier records `CLOSE`, the `save_result` migration reserve, the
verification limits and exact proof references in
[`wp11_final/closure_gate_assessment.md`](wp11_final/closure_gate_assessment.md)
and [`wp11_final/owner_decision_followup_manifest.json`](wp11_final/owner_decision_followup_manifest.json).

This operational closure does not promote D01 (`INCONCLUSIVE`), expand C02
`CLOSED_BOUNDED` beyond AR/N03, or close E01 (`OPEN_WITH_BOUNDED_CERTIFICATES`).
Numerical V&V and performance remain WP12 work. No WP12 or WP13 execution,
merge to `main`, tag, package publication, or site publication is included.
