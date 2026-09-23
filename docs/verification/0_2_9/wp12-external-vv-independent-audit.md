---
doc_id: DOC-029-WP12-EXTERNAL-VV-INDEPENDENT-AUDIT
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.9-development
---

# WP12 external V&V — independent plan and evidence audit

## Verdict

`READY_FOR_OWNER_REVIEW_WITH_LIMITATIONS`

The frozen R2 package supports four candidate Code_Aster correlations for the
exact WP11-R2 M1, one-element, small-strain linear-static cases. The frozen
raw-evidence auditor independently recomputed every comparison from the QF and
Code_Aster arrays: all four families pass, with no audit errors. This does not
award points or establish broader solver or physical validation.

This was a read-only audit of completed evidence plus a rerun of the targeted
WP12 unit tests. No Code_Aster or QF structural solve, merge, push, or ledger
update was performed. The full repository suite was not run.

## Provenance and repository state

| Item | Independently checked value |
|---|---|
| Evidence branch | `codex/wp12-external-vv` |
| Evidence HEAD at audit start | `1adc4b40ca5c4b1feffbe0e98f859ad6be37c5dc` |
| Authorized WP12 base / merge base | `48eadcbde3cfcf8b15f6cd2335afa3df17d8de37` |
| Current governing local and remote ref | `754664836c0e30232d38b31e21c3d98e4b3092bd` |
| WP12 contract-freeze / execution commit | `e3231fa386d2542841084e3be9843e7eca75acf4` |
| Runner commit | `c4a772cd14921ca0b243c71b99a0f94f0ca210e8` |
| Independent raw auditor commit | `c6626976d72a77fcf1233ea6c41b1f998be0e5bb` |
| R2 contract SHA-256 | `f6154660635670c026354429894c9c7a6f7fa6d8bd6849edf44717a4bd43824a` |
| R2 evidence manifest SHA-256 | `7a912a795bd57db6505ae100dd77a8480d3bf41a1229fd39644c298b294c4e8c` |
| R2 runner summary SHA-256 | `a7f7222d03ef04662828ed1e1207a312487c958b5d948bd36f513102dacae138` |
| Independent audit output SHA-256 | `0be63ce3f98e7e785f0cdff8fda94b4495d4d95f5ae0ee50c5809ad181acbdcf` |
| Pre-audit worktree | Clean |
| Active Code_Aster containers after run | None found |

The R2 contract-freeze commit time is `2026-09-23T10:35:10+02:00`. The first
family process began at `10:35:34+02:00`, after the contract was committed.
The runner and auditor commits are ancestors of that freeze/execution commit;
the evidence commit is a descendant. The WP12 branch has not been pushed or
merged. The governing branch has advanced two commits from the common base
since WP12 branched; their diff contains no `src/` changes. Reconcile that
administrative lineage during any later integration, without rebinding or
rewriting R2 evidence.

From the authorized base through the WP12 evidence HEAD, no production
`src/` path changed. The branch adds the WP12 runner, independent auditor,
targeted tests, contract, reports, and evidence. This statement is limited to
the audited base-to-branch diff; it is not a claim that the entire project has
never changed production mechanics.

## Plan audit

The prospective plan and frozen R2 contract agree on the bounded scope:

- one homogeneous, one-element, 3D, small-strain linear-static model per
  family: TET4, HEX8, TET10, HEX20;
- read-only reuse of the accepted WP11 M1 inputs; no QF M1/M2/M3 rerun;
- identical coordinates, connectivity mapping, material (`E=210 GPa`,
  `nu=0.30`), fixed DOFs and frozen nodal load vectors;
- all translations fixed at the `x=0` nodes and a `-1000 N` vertical resultant;
- tetrahedral loading at the one `x=1` vertex (not represented as a face
  traction), with the frozen explicit HEX20 local-node permutation;
- pinned Code_Aster 18.1.0 image, fresh container for each family, one CPU,
  MPI disabled, sequential order TET4 → HEX8 → TET10 → HEX20;
- displacement and reaction L2/L-infinity comparisons, energy/work identity,
  force/moment equilibrium in both solvers, fixed-DOF displacement and
  finite-value/model-fingerprint checks;
- comparison limits fixed prospectively at `1e-8` and fixed displacement at
  `1e-12`; no post-result threshold adjustment or output overwrite.

The audit script imports NumPy and standard-library modules only. It does not
import the QF solver or WP12 runner. It verifies the generated ASTER mesh,
command and export text against the contract, validates process/runtime records
and manifest hashes, then recomputes metrics from raw arrays. Therefore the
reference is a separate Code_Aster finite-element solve plus an independent
observable recomputation—not merely a QF post-processing pass. It is still
correlation on the same frozen mathematical model, not experimental
validation.

Plan limitations are explicit and correctly fail closed: no mesh-convergence,
stress-field equivalence, cross-family equivalence, nonlinear/contact/dynamic
qualification, or general solver-equivalence claim.

## Raw evidence and execution audit

- R2 manifest: all **74/74** entries independently rehashed; no missing or
  mismatched entry.
- Accepted WP11 source, contract, Owner acceptance, M1 inputs and Owner
  manifest hashes: verified by the independent auditor.
- R1: all **66** manifest entries and the failure record were revalidated.
  R1 remains `FAIL_CLOSED_LAUNCHER_RUNTIME_IMPORT_FAILURE` (`mpi4py` missing
  during startup, before numerical output); it is preserved, not relabeled or
  reused as passing evidence. R1 and R2 have distinct output roots.
- Each R2 process record binds its family, host PID, distinct container ID,
  pinned image ID, runtime version, start/end, CPU limit, MPI-disabled flag,
  command, telemetry count and exit code `0`.
- The four runs are strictly sequential; each begins after the prior process
  exits. All four `.mess` logs report normal Code_Aster termination, and no
  fatal marker was found. The targeted run-time import smoke is recorded PASS.
- No active Code_Aster container remained during this audit.
- `tests/unit/test_wp12_code_aster_multifamily.py`: **16 passed** on
  `2026-09-23`; no full repository suite was run.

### Recomputed R2 gates

All comparison/equilibrium limits are `1e-8`; fixed displacement is absolute
`1e-12`. Relative metrics are dimensionless.

| Family | DOFs | Displacement L2 / Linf | Reaction L2 / Linf | Energy/work | QF force / moment | Aster force / moment | Fixed `|u|max` | Audit |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| TET4 | 12 | `1.782e-16 / 1.782e-16` | `2.625e-16 / 2.274e-16` | `1.824e-16` | `0 / 0` | `0 / 0` | `0` | PASS_CANDIDATE |
| HEX8 | 24 | `7.501e-16 / 1.240e-15` | `1.046e-15 / 1.364e-15` | `7.938e-16` | `4.348e-16 / 2.558e-16` | `8.789e-17 / 9.846e-17` | `4.463e-25` | PASS_CANDIDATE |
| TET10 | 30 | `4.734e-15 / 4.152e-15` | `6.043e-15 / 6.489e-15` | `4.252e-15` | `6.765e-15 / 3.794e-15` | `5.210e-16 / 2.558e-16` | `7.533e-24` | PASS_CANDIDATE |
| HEX20 | 60 | `1.210e-14 / 1.619e-14` | `1.358e-14 / 1.294e-14` | `1.110e-14` | `3.600e-15 / 4.433e-15` | `2.405e-16 / 1.241e-16` | `1.566e-24` | PASS_CANDIDATE |

Independent auditor outcome: `PASS_CANDIDATE`, candidate `4/4`, official
`0/4`, zero errors. These values establish agreement for the declared
discrete cases; the small deltas are not evidence of universal accuracy.

## External comparison gap matrix

WP12 closes only the narrow external-correlation gap for the four WP11 M1
linear-static cases. The following remain outside its evidence and are
non-blocking for this WP12 Owner decision, but block any broader external
validation claim:

| Work package / claim | External evidence still missing | Minimum separately frozen comparison |
|---|---|---|
| WP04 geometric nonlinear response | No external correlation for its bounded finite-rotation/geometric path | Same geometry, kinematic measure, constitutive law, loading path and observables; compare full displacement/reactions, equilibrium and deformation envelope. |
| WP05 high-order geometric nonlinear TET10/HEX20 | WP12 checks only linear elasticity; no external nonlinear or representative-stress correlation | Separate TET10 and HEX20 nonlinear cases; freeze traction/quadrature, stress region and volume weighting; compare path observables and stress metrics without claiming full-field equivalence unless directly tested. |
| WP06 continuation / postbuckling | No independent nonlinear path solve; current accepted status is bounded experimental continuation and no limit point was established | First freeze a benchmark with a detectable limit point or explicitly bounded-path objective; compare load factor versus control displacement, branch/turning-point detection, equilibrium and post-limit states. Do not call it postbuckling validation before a limit point is observed. |
| WP07 frictionless contact | No external contact-path correlation | Match the bounded active-set and penalty routes separately; compare displacement, reactions, contact resultant/active region, penetration, contact energy, equilibrium and replayed state transitions. |
| WP08 frictional contact | No external frictional-path correlation | Freeze Coulomb/friction parameters, initial search and supported route; compare stick/slip states, tangential forces, slip, dissipation, penetration and equilibrium. Differences in contact algorithms must be treated as model-form limitations, not hidden by tuning. |
| WP09 bounded corotational J2 | No external J2/material-state correlation | Match the exact bounded kinematics and hardening law first; compare load-path displacement, reactions, stress, plastic strain/internal variables and energy on the accepted HEX8 scope. Do not substitute a different finite-strain law without declaring non-equivalence. |
| WP10 bounded coupled multi-family response | No external correlation for its coupled nonlinear family cases | Select representative accepted families and match coupling, material state evolution, contact/kinematics and load path; compare both global responses and required internal variables. Keep each family and limitation explicit. |
| WP11 PETSc/MPI route | WP12 validates the serial linear-static physics cases, not distributed assembly or scalability | No added external physics claim is needed for the accepted WP11 scope. If distributed correctness is claimed independently, compare serial/MPI decomposition-invariant raw results and ownership/assembly invariants; do not infer scaling from this campaign. |

Recommended sequence for future, separately authorized V&V: (1) bounded
WP09 J2, after constitutive/kinematic equivalence is demonstrated; (2) WP10
coupled multi-family cases; (3) WP04/WP05 geometric and high-order cases;
(4) WP07/WP08 contact routes, each formulation separately; (5) WP06 only
after its benchmark and limit-point criterion are frozen. This is a planning
recommendation, not execution authorization or a new scoring scheme.

Code_Aster's official documentation describes distinct options for nonlinear
behavior and large-deformation plasticity, contact-friction in nonlinear
analyses, and load-control/continuation methods. Those references establish
that future study paths exist; they do **not** establish equivalence to QF's
specific implementations or settings. The cited manuals span versions 14–17,
whereas R2 used 18.1.0; exact command/behavior availability must be checked in
the pinned 18.1.0 runtime before freezing any future comparison:

- [Code_Aster U4.51.11 — nonlinear behaviors](https://code-aster.org/V2/doc/default/en/man_u/u4/u4.51.11.pdf)
- [Code_Aster R5.03.21 — large-deformation elastoplasticity](https://code-aster.org/doc/v14/man_r/r5/r5.03.21.pdf)
- [Code_Aster R5.03.22 — large rotations and small strains](https://code-aster.org/doc/v14/man_r/r5/r5.03.22.pdf)
- [Code_Aster U2.04.04 — contact-friction use](https://code-aster.org/doc/v17/manuals/man_u/u2/u2.04.04/index.html)
- [Code_Aster R5.03.50 — discrete contact-friction formulation](https://code-aster.org/doc/v14/man_r/r5/r5.03.50.pdf)
- [Code_Aster R5.03.80 — load-control methods](https://code-aster.org/doc/v14/man_r/r5/r5.03.80.pdf)

## Governance and next gate

```text
WP12_CANDIDATE_POINTS = 4/4
WP12_OFFICIAL_POINTS = 0/4
WP12_OWNER_REVIEW = READY
CURRENT_MACHINE_LEDGER = 90/100; WP12 remains NOT_STARTED / 0 of 4
PRODUCTION_SRC_CHANGED_IN_WP12_BRANCH = NO
THRESHOLDS_CHANGED = NO
HISTORICAL_R1_FAILURE_PRESERVED = YES
SOLVE_RERUN_DURING_THIS_AUDIT = NO
FULL_REPOSITORY_TEST_SUITE = NOT_RUN
MERGE = NOT_PERFORMED
PUSH = NOT_PERFORMED
LEDGER_UPDATE = NOT_PERFORMED
```

The Owner may now decide whether to accept each of the four family-specific
correlations, accept the limitations, award up to `4/4`, and separately
authorize any governing merge/push or ledger change. A later integration must
first reconcile the two newer governing documentation commits with this
candidate branch; do not rerun or rewrite the frozen R2 evidence for that
administrative step.
