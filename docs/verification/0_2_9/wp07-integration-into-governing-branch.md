---
doc_id: DOC-029-WP07-INTEGRATION-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 WP07 governing-branch integration audit

This record covers the controlled integration of the Owner-frozen WP07
candidate into `0.2.9-unified-nonlinear`. It promotes only the revalidated
WP07-A/B/C technical candidates to formal points. WP07-D structural execution
and WP07-E closure remain unrun and receive no points.

Machine-readable record:
[`wp07_integration_audit.json`](../../../qualification/0_2_9/wp07/wp07_integration_audit.json)

## Integration provenance

| Item | Value |
| --- | --- |
| Governing branch | `0.2.9-unified-nonlinear` |
| Governing start SHA | `fb1fc2d4d861397b4a3689bd64e7a727e1f33998` |
| Child branch | `0.2.9-wp07-prep` |
| Child head | `3bdcc84907a045e7815d6d5253bf4e2eed74970e` |
| Merge-base | `2c52bf8196a7d47d14ce1784290580160de26590` |
| Non-fast-forward merge | `b3cba87f811441edd657f0788ade29d2a904f430` |
| Merge conflicts | None |

The pinned heads and historical merge-base matched before the merge. The
integration used `git merge --no-ff`; child history was preserved. The WP06
child branch was not inspected, modified or merged.

## Source integration and protection

The child adds the bounded contact evaluation/restart layer and additive
contact diagnostics in:

* `src/solveur/contact/evaluation.py`;
* `src/solveur/contact/__init__.py`;
* `src/solveur/contact/solver.py`.

Targeted validation initially exposed a package-import cycle: the new package
exports eagerly imported `evaluation.py`, which imported runtime model types
while `solveur.core.model` was still initializing. The integration applies one
non-numerical hygiene correction: `DofManager` and `FiniteElementModel` are
type-only imports under `TYPE_CHECKING`. This leaves contact force, tangent,
activation, penalty, Newton and line-search behavior unchanged. A subprocess
model-first import regression is included in
`tests/integration/test_wp07_governing_integration.py`.

No governing WP04 mechanics, WP04 floor-aware termination, WP05 high-order
contract, WP15 telemetry route, or WP06 branch content changed. The
integration change is production source (`production_source_changed = true`)
because WP07 itself adds the contact API and the import-order correction, but
it is not a mechanics-formulation or numerical-policy change.

## WP07-A/B/C revalidation

### WP07-A — bounded formulation scope

WP07-A is revalidated as `PASS_BOUNDED_SCOPE_CONTRACT` (`1/1`). The contract
keeps these regimes separate:

* linear small-displacement active-set contact with initial/fixed search;
* nonlinear frictionless penalty contact with initial/fixed face and normal;
* updated-search/finite-sliding contact remains `RESEARCH_ONLY`.

Friction, dynamics, MPI contact, self-contact, mortar, augmented Lagrangian,
modal/buckling contact and general industrial-contact claims remain excluded.
No structural qualification is inferred from the scope contract.

### WP07-B — evaluation and restart semantics

WP07-B is revalidated as `PASS_BOUNDED_EVALUATION_AND_RESTART_SEMANTICS`
(`2/2`) by 18 focused tests. The tests cover same-trial determinism,
discarded-trial re-evaluation, configuration digest determinism and
sensitivity, contact-only versus full-restart distinction, required model and
accepted-state identities, fail-closed incompatible metadata, legacy
composition/diagnostics, and the explicit unsupported/unqualified restart
boundaries.

Penalty contact remains `PURE_STATELESS_FROM_TRIAL_U`; no independent contact
history is committed. Full restart compatibility requires the contact
configuration digest, restored model/checkpoint signature and restored
accepted-state digest. Active-set mid-solve restart remains unsupported.

### WP07-C — contact identities

WP07-C is revalidated as `PASS_BOUNDED_CONTACT_IDENTITIES` (`2/2`) by 11
focused tests and its raw candidate record. The frozen observations pass for
penalty open force, active force, energy gradient, tangent finite difference,
tangent symmetry, activation semantics, reopen/no-ghost-force behavior, and
active-set gap/pressure/complementarity, vector equilibrium and replay.

Key raw values remain unchanged from the candidate evidence:

| Observation | Value | Frozen limit |
| --- | ---: | ---: |
| Penalty energy-gradient relative error | `1.5192447540399686e-10` | `1e-7` |
| Penalty tangent Frobenius error | `1.5743360213643872e-11` | `1e-6` |
| Penalty maximum-column error | `3.274180926489745e-11` | `5e-6` |
| Penalty tangent symmetry error | `0.0` | `1e-12` |
| Active-set force equilibrium | `1.4210854715202004e-16` | `1e-8` |
| Active-set moment equilibrium | `2.8421709430404003e-16` | `1e-8` |

## WP07-D and WP07-E boundaries

WP07-D is `PASS_CONTRACT_ONLY_STRUCTURAL_UNRUN` at `0/3`. Its corrected
consistent quadratic/triangular load, M1/M2/M3 preparation, observables,
equilibrium limits, replay policy and fail-closed guards remain frozen. No
contact structural solve and no external solver run was performed.

WP07-E is `PASS_FAIL_CLOSED_CONTRACT_ONLY_CLOSURE_UNRUN` at `0/2`. The
raw-evidence closure builder and anti-downgrade tests pass, but no runtime
structural evidence map exists. No WP07-E closure or bounded contact maturity
claim is made.

## Governing-policy binding

Future WP07-D execution is bound to the current governing branch and the
following deterministic digests:

* C2R6 nonlinear policy digest:
  `sha256:93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`;
* WP07 contract digest:
  `sha256:93c7741ecafd72cfa20e29e323b92ea9356fb93dacaff09a8347789bad9c9ed2`;
* accepted-state/rollback digest:
  `sha256:98baa056465502bf8ea8fb701b9bf9d33d95f9c9ff6baf7a5afc38c0450b6b03`;
* contact formulation/evaluation digest:
  `sha256:efa3a42d56eb5a80cea62ca3e8ae20b7dd22d2e27b585fd9b82a0e670f2b21a8`.

The state authority remains `NonlinearStateTransaction` plus
`UnifiedContinuationController` where continuation applies. The contact
evaluation layer returns detached semantic views and metadata; it does not
create a second accepted-state authority.

## Targeted validation

The WP07-specific candidate selection passed 60 tests: 18 WP07-B, 11 WP07-C,
15 WP07-D contract and 16 WP07-E fail-closed tests. The governing protection
selection passed 217 tests, including contact routes, WP04-F/C2R6, WP05
contract preparation, WP15 telemetry and assembly telemetry. The integration
guard adds 4 tests for contract scope, preparation-only boundaries, raw
identity thresholds and safe import order. The targeted run emitted only the
three expected NumPy warnings from intentional nonfinite/preflight failure
tests.

No full repository suite was run. No contact structural campaign, H2/H3 solve,
external solver, PETSc run or WP06 integration was run.

## Formal result and next step

| Package | Result | Points |
| --- | --- | ---: |
| WP07-A | Formal PASS — bounded scope contract revalidated | `1/1` |
| WP07-B | Formal PASS — evaluation/restart semantics revalidated | `2/2` |
| WP07-C | Formal PASS — contact identities revalidated | `2/2` |
| WP07-D | Contract only; structural execution not run | `0/3` |
| WP07-E | Contract only; closure not run | `0/2` |
| **WP07** | **Partial integrated candidate** | **`5/10`** |

The governing roadmap advances from `45/100` to `50/100`. WP04 remains closed
at `12/12`, WP05 remains partial at `2/5`, and WP15 remains closed at `2/2`.
WP07 remains bounded to the declared initial-search contact regimes and is
not a public maturity promotion. Owner review is required before preparing
the sequential WP07-D structural qualification campaign. Do not merge WP06.

## Post-validation branch retirement

The audit and retirement evidence commits were pushed to
`origin/0.2.9-unified-nonlinear`; the final verified governing head for this
integration record is `226b9e2020501aa2e97db3c7719585638ae1999e`. The child
head is an ancestor of that governing head. No local
`0.2.9-wp07-prep` branch existed in the integration checkout; the remote
`0.2.9-wp07-prep` ref was deleted with the non-forcing remote delete command
and verified absent. The WP06 remote ref remained untouched.
