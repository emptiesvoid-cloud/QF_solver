# WP09 corotational J2 implementation report

## Status

```text
BRANCH = codex/wp09-corotational-j2
GOVERNING_BASE_SHA = 03c35eb7a634a57e5c29d95555316cfb2701d2ad
IMPLEMENTATION_SHA = 0b9501ce2091a146aa895d77b24828114265e84b
FINAL_REVIEWED_SOURCE_SHA = 0c32751970356db7a90098293da84e14a9832e0a
EVIDENCE_COMMIT_SHA = 5ac9b81 (report and contract evidence commit)
REMOTE_HEAD = NOT_PUSHED
WORKING_TREE = CLEAN_BEFORE_REPORT_COMMIT

WP09_FORMAL_STATUS = IMPLEMENTATION_CANDIDATE
WP09_OFFICIAL_POINTS = 0/8
OD-029-01 = NOT_CLOSED_BY_THIS_PACKAGE
```

Option A has been implemented on a separate branch after explicit Owner
authorization. This is an additive route; it does not remove or alter the
existing Green–Lagrange/J2 route.

## What was added

- `src/solveur/elements/solid/corotational_j2.py`
  - polar decomposition `F = R U`;
  - bounded local strain `||U-I||_F`;
  - additive small-strain von Mises/J2 constitutive update;
  - local tensor-state transport between committed corotated frames;
  - `P = R sigma_local` force measure;
  - central-difference tangent at fixed committed state;
  - explicit determinant and local-strain fail-closed guards.
- Opt-in nonlinear assembly dispatch through
  `kinematics=corotational_j2` for TET4, TET10, HEX8, and HEX20.
- Corotational post-processing fields: rotation, right stretch, local strain,
  local stress, first Piola stress, Cauchy stress, and determinant.
- Targeted tests in `tests/unit/test_corotational_j2.py`.
- Candidate contract and limitations in
  `qualification/0_2_9/wp09_corotational_contract.json` and this directory.

## Numerical and governance limits

The default bound is `||U-I||_F <= 0.05`. A violation raises a controlled
failure; it is not clipped. The path is intended for large rigid rotations
with small local strains. It is not a finite-strain multiplicative plasticity
model and does not establish a general large-local-strain J2 claim.

The initial candidate scope is homogeneous solid meshes, Full Newton, and the
TET4/HEX8 verification families. TET10/HEX20 dispatch is implemented but not
formally qualified here. Contact, dynamics, MPI/PETSc, follower loads,
external-solver correlation, and general postbuckling remain out of scope.

The existing `kinematics=total_lagrangian_j2` path and its Green–Lagrange /
second-Piola observables remain unchanged. Results from the two routes must
remain separately labelled and must not be mixed in a qualification record.

## Verification performed

```text
TARGETED_TESTS = 53 passed
  - corotational J2 tests: 7
  - existing total-Lagrangian J2 and assembly-plan tests: 25
  - nonlinear assembly/transaction/geometric/element-contract tests: 21
RUFF = PASS
COMPILEALL = PASS
JSON_VALIDATION = PASS
GIT_DIFF_CHECK = PASS
```

The tests cover:

- TET4 and HEX8 nonlinear solves with the new kinematics label;
- post-processing labels and integration-point fields;
- rigid-rotation objectivity with negligible internal force/stress;
- tensor-state transport;
- committed-state immutability;
- explicit failure above the local-strain bound;
- uncached assembly dispatch;
- existing Green–Lagrange/J2 regression behavior.

The independent reference solve, production replay, mesh campaign, and formal
WP09 qualification were not run. The current package therefore supports only
an implementation candidate, not a WP09 score.

## Next formal step

Prepare a separately frozen TET4/HEX8 benchmark contract with its loads,
mesh hierarchy, local-strain envelope, equilibrium limits, reference/replay
requirements, and failure classification. Only then should a formal
requalification be authorized. No ledger update, merge, or push is implied by
this implementation checkpoint.
