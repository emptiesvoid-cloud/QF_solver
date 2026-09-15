---
doc_id: DOC-029-WP08E-001
revision: 0.2
status: candidate_pending_owner_review
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-E — bounded closure, replay and accepted-state restart

## Executive summary

WP08-E is technically complete within the deliberately bounded
`linear_static` frictional-contact route. The implementation now persists a
signed accepted contact state, rejects stale or tampered checkpoints before a
resume, and demonstrates that a stop after an accepted increment can be
continued to the same terminal result as an uninterrupted run.

The A→D audit closes the existing WP08 evidence chain. The resulting
technical candidate is `8/8`, but this is not an official score: all formal
points remain `0/8` until the Owner explicitly reviews and attributes them.

## Scope

This record implements and verifies the bounded WP08-E closure machinery for
the already-qualified frictional-contact route. It adds signed persistence of
an accepted friction state and fail-closed validation before a resumed solve.
It does not claim mid-Newton restart, updated-search friction, finite sliding,
or a general nonlinear checkpoint capability.

No M2 or M3 structural solve was relaunched by this task. The previously
authorized M2/M3 production, independent-reference and replay artifacts were
consumed read-only and their manifests were re-hashed.

## Provenance and source identity

```text
AUTHORIZED_BASE_SHA = 7b93e71bab06a0e58108bd2479cd46808d533b67
REMEDIATION_SHA = 794de436c13364c16aa85b2ae2c9e7bb09957829
EXECUTION_SHA = 3c386b87bd60f3ed20d979f67c8b42da8f41b8c1
EVIDENCE_COMMIT_SHA = bba9f7bc54ccd804824b58cb3e8684dc185fe8a7
FINAL_SHA = bba9f7bc54ccd804824b58cb3e8684dc185fe8a7
REMOTE_HEAD = 7916d37a32af405fb5d710f56693c572f43aa298
BRANCH = 0.2.9-wp08d-m1-phase1
```

`REMEDIATION_SHA` identifies the local implementation commit. `EXECUTION_SHA`
is the exact source revision used for the final WP08-E and A→D audit runs.
`EVIDENCE_COMMIT_SHA` and `FINAL_SHA` identify the local evidence snapshot
containing the generated JSON and checkpoints. `REMOTE_HEAD` is unchanged
because no push was requested. The older M1/M2/M3 structural artifacts retain
their own execution and authorization SHAs and are not relabeled as if they
had been rerun by this task.

## Implementation delivered

The accepted-state restart contract is implemented in:

- `src/solveur/contact/restart.py`: schema versioning, physical-model/load
  path signature, atomic JSON writes, shape/finite/state validation, and
  fail-closed checkpoint loading;
- `src/solveur/contact/solver.py`: checkpoint after each accepted increment,
  restart from the last accepted step, restoration of slip references and
  cumulative local dissipation, and restart metadata in result details;
- `tests/unit/test_frictional_contact.py`: uninterrupted-vs-resumed equality,
  tamper rejection, missing-checkpoint rejection, invalid-friction rejection,
  and updated-search rejection;
- `scripts/run_wp08e_closure.py`: bounded executable E closure pack;
- `scripts/run_wp08abcd_closure.py`: read-only A→D evidence and manifest audit.

The checkpoint records the model/load-path digest, completed accepted step,
slip references, tangential forces, displacement, normal state, multipliers,
gaps, pressures, tangential states, active contacts and cumulative
dissipation. Volatile output paths are excluded from the physical signature;
all physical inputs remain bound to the digest.

## WP08-E evidence

The controlled seven-step local history was solved once without interruption.
A second run was stopped after accepted step 4, using an injected test
interruption. The accepted state was written atomically, then loaded into a
fresh solver and continued through steps 5–7.

| Check | Result |
| --- | --- |
| accepted checkpoint after step 4 | `PASS` |
| resumed steps | `3` |
| resumed terminal state vs uninterrupted state | `PASS` |
| maximum displacement absolute delta | `0.0` |
| cumulative dissipation delta | `0.0` |
| M2 replay evidence revalidated | `PASS` |
| M3 replay evidence revalidated | `PASS` |
| manifests and raw hashes | `PASS` |

Negative controls all fail closed:

- negative or non-finite friction coefficient: `PASS_FAIL_CLOSED`;
- frictional updated-search request: `PASS_FAIL_CLOSED`;
- missing restart checkpoint: `PASS_FAIL_CLOSED`;
- tampered physical-model checkpoint signature: `PASS_FAIL_CLOSED`.

The machine-readable result is
`qualification/0_2_9/wp08e_closure/wp08e_closure_final.json`.

### E execution sequence

The closure runner performed the following bounded sequence:

1. Solve the seven-step frozen local history without interruption.
2. Repeat it with a controlled stop at step 5, after the checkpoint for
   accepted step 4 had been flushed.
3. Load and validate that checkpoint in a fresh solver instance.
4. Continue steps 5–7 and compare the terminal state with the uninterrupted
   run.
5. Execute negative controls and verify typed fail-closed behavior.
6. Re-hash the existing M2 and M3 replay manifests.

The restart comparison is exact at recorded precision: maximum absolute
displacement difference `0.0` and cumulative local dissipation difference
`0.0`. The resumed run wrote three accepted-step records, corresponding to
steps 5, 6 and 7. A terminal checkpoint is not accepted as a continuation
source; only a non-terminal accepted checkpoint can be used for restart.

## Explicit transition: historical M2 failure to M2/M3 pass evidence

The final candidate is not based on silently replacing a failed result. The
failure and the subsequent correction are both retained as separate evidence
generations:

| Generation | Source/evidence commit | Result | Meaning |
| --- | --- | --- | --- |
| Contract-aligned M2 failure | `624e5ba6759a296efba24ca4f5b1b7bc1c4b8238` / recorded by `45eadb3d9d2c8bc5649c81ec01d351be53e015dc` | `FAIL_CLOSED` at increment 5 | The frozen route reached active set `[3,7,11]`; the hybrid active-slip root failed and rollback was performed. No replay or M3 was allowed. |
| Production hybrid remediation | `b11726c6d7318762c3a892821f9fd3ca0a8a5eaf` | production candidate recovered | Stick contacts contribute elastic KKT terms; only observed slip contacts enter the hybrid root. Thresholds, loads, mesh and fallback policy were unchanged. |
| Reference alignment and M2 closure | `5fe0451a21ac33de9ddaca6b480748238ac04779` / evidence `ab64fc5bc9373bb7c12e96d7259cc148a1fe1d8b` | `M2 PASS_REFERENCE`, replay `PASS`, 7/7 | The independent reference was corrected to represent the observed SSK hybrid mode while remaining independent of production contact routines. |
| M3 authorized closure | authorization `7761692203060879366594052ab122415bdab274` / evidence `4f972b5db98cc9313bf0129adaeaa0b218da5375` | production, reference and replay `PASS`, 7/7 | M3 was run only after M2 reference and replay passed. |
| Provenance clarification | `7916d37a32af405fb5d710f56693c572f43aa298` | audit correction | The distinction between execution SHA, evidence SHA, contract digest and policy digest was made explicit. |

The old failure remains available in
`docs/verification/0_2_9/wp08d-hybrid-stick-slip-m1-m2-report.md` and the
contract-aligned artifacts. The new M2 evidence is in
`qualification/0_2_9/wp08d_phase1_hybrid_stick_slip_reference_replay/`, and
the M3 evidence is in the same evidence root under `production/M3`,
`independent_reference/M3` and `replay/M3`.

The transition is therefore:

```text
M2 old = FAIL_CLOSED
  -> preserve failure and rollback evidence
  -> remediate the actual hybrid stick/slip implementation/reference path
  -> rerun independent reference and replay on the frozen inputs
M2 new = PASS_REFERENCE + PASS replay, 7/7
  -> authorize M3
M3 new = PASS production + PASS_REFERENCE + PASS replay, 7/7
```

No threshold relaxation, result overwrite, silent fallback or retroactive
point assignment occurred.

## A→D closure audit

The existing bounded evidence was checked without rewriting historical
results or awarding points automatically:

| Component | Candidate result | Candidate points |
| --- | --- | ---: |
| WP08-A — formulation/input/state contract | bounded candidate with limitations | `1/1` |
| WP08-B — identities, state transactions and rollback | candidate with limitations | `2/2` |
| WP08-C — tangent and local dissipation V&V | candidate with limitations | `2/2` |
| WP08-D — M1/M2/M3 structural/reference/replay evidence | candidate with limitations | `2/2` |
| WP08-E — replay, restart and fail-closed closure | candidate | `1/1` |
| **WP08 total** | **candidate pending Owner review** | **`8/8`** |

WP08-D checks include M1, M2 and M3 production evidence, independent
references, replay comparisons, contract/policy digest consistency, and all
available manifests. The independent references are verified as not calling
production contact routines.

### A — formulation, input and state contract

The evidence freezes the supported route as serial/direct `linear_static`,
small displacement, node-to-triangle contact, fixed initial face/normal,
positive `mu` and positive tangential stiffness. It explicitly excludes
updated-search friction, finite sliding, common nonlinear friction, dynamics,
MPI/PETSc and unqualified restart behavior. This supports candidate `1/1`
only inside that bounded scope.

### B — identities, transitions and rollback

The evidence covers open, stick, slip, zero-pressure safety, Coulomb radius,
slip direction, reversal and transactional rollback. The historical
zero-pressure `0/0` defect remains recorded as R0; the Owner-authorized R1
guard is preserved. This supports candidate `2/2` with the documented
direct-dataclass validation limitation.

### C — tangent and dissipation V&V

The evidence verifies the fixed-branch stick tangent, sampled finite
differences, fixed-pressure slip Jacobian, nonsmooth transition
classification, stick energy gradient and non-negative local work proxy. It
does not claim a pressure-coupled global tangent or a complete global energy
decomposition. This supports candidate `2/2` as a bounded result, not a
universal friction claim.

### D — structural, independent-reference and replay evidence

The audit found the required M1, M2 and M3 production/reference/replay
artifacts. Each required manifest re-hashed successfully. M1, M2 and M3
references report pass classifications, replay comparisons report `PASS`,
contract and policy digests match, and the independent implementations state
that production contact routines were not called. This supports candidate
`2/2`, subject to Owner review and the exact execution SHAs retained in the
source artifacts.

### E — closure

WP08-E adds the missing accepted-state continuation proof and negative
controls. Its candidate contribution is `1/1`; it does not upgrade the scope
to mid-Newton restart or general nonlinear restart.

## Governance

The accepted-state checkpoint persistence is a production-scope change, but
it is limited to the new WP08-E restart contract and validation. No frozen
threshold, solver parameter, backend, fallback policy, load, mesh or contact
law was changed. The original M2/M3 evidence remains immutable evidence for
the source SHAs under which it was executed.

```text
PRODUCTION_MECHANICS_CHANGED = YES, WP08-E checkpoint persistence/validation only
THRESHOLDS_CHANGED = NO
SOLVER_PARAMETERS_CHANGED = NO
FALLBACK_CHANGED = NO
FULL_TEST_SUITE_RUN = NO
STRUCTURAL_SOLVES_RUN_BY_CLOSURE = NO
OFFICIAL_WP08_POINTS_BEFORE_OWNER_REVIEW = 0/8
CANDIDATE_WP08_POINTS = 8/8
FINAL_STATUS = PASS_CANDIDATE_OWNER_REVIEW_REQUIRED
NEXT_STEP = Owner review and explicit point attribution; do not self-merge
```

The following claims remain out of scope: mid-Newton restart, frictional
updated search, finite sliding, general nonlinear friction, global
pressure-coupled tangent consistency, global energy decomposition, external
solver correlation and automatic official point attribution.

## Owner direct-inspection package

The Owner HOLD requested a reviewable state without any solve rerun. The
inspection target is exactly
`123c46eb6900647679c4b96350dafd4d05efa355`; the evidence snapshot
`bba9f7bc54ccd804824b58cb3e8684dc185fe8a7` is its ancestor, and the two
intervening commits alter this report only.

The direct-inspection package consists of:

- `qualification/0_2_9/wp08_closure/wp08_owner_review_inspection.json`:
  SHA chain, exact closure JSON hashes, M1/M2/M3 manifest re-hashes and
  source-level reference-import audit;
- `qualification/0_2_9/wp08e_closure/wp08e_closure_integrity_manifest.json`:
  hashes for the E closure record and both checkpoint files, plus the accepted
  step-4 and terminal-step-7 consistency facts;
- `qualification/0_2_9/wp08e_closure/restart/accepted_step4.json` and
  `restart/resumed_final.json`: the raw persisted contact states;
- `scripts/run_wp08d_m1_independent_reference.py`,
  `scripts/run_wp08d_independent_reference.py` and
  `scripts/wp08d_independent_kkt_reference.py`: source reviewed for direct
  production-contact imports.

The static import audit found no `solveur.contact` import in any independent
M1/M2/M3 reference runner or KKT reference module. M1 imports the generic
Phase-1 helper for telemetry and file writing; that helper’s lazy imports are
`solveur.core.telemetry` and production imports live only in a distinct
production-run function, not in the independent reference execution path.
The M1/M2/M3 result and manifest artifacts also each declare
`production_contact_routines_called=false`.

## Validation

The local-source targeted validation completed as follows:

```text
55 targeted tests passed
Ruff = PASS
mypy = PASS, 4 source files
compileall = PASS
JSON validation = PASS
manifest/hash validation = PASS
git diff --check = PASS
```
