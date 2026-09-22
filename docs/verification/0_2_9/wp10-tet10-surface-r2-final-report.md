# WP10 TET10 surface R2 — M1/M2/M3 final report

## Decision state

```text
STATUS = READY_FOR_OWNER_REVIEW
BRANCH = codex/wp10-tet10-surface-r1
AUTHORIZED_BASE_SHA = cfec576ed44e8c68469ba45613ecbd46792ce7ff
EXECUTION_SHA = 3356dabb38ff4f660dfc905aa75da3e3a6f7c863
RUNNER_SHA = 8a2797c6d5b9559d7704ff8581edbb068daa3ecc
REFERENCE_SHA = 72da44492402939557f29ba72734cd5fad62e30f
CONTRACT_SHA256 = 9cf4c1b8c8bb7ea3a5af2581e2181e56f7c048de43f07d336065c4f728e70bda
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
FULL_TEST_SUITE = NO
FORMAL_POINTS = PENDING_OWNER_REVIEW
```

The R2 contract was frozen and rebound to the directly-invokable runner before
the calculations. No production mechanics, solver thresholds, material/load
parameters, or fallback policy were changed by this campaign.

## Executed sequence

The sequence was executed without skipping dependencies:

1. M1 H1, H2, H3, each with five accepted load increments;
2. M2 H3 with frictionless penalty contact and initial search;
3. independent JSON/NumPy observable recomputation for M1 and M2;
4. fresh-process M3 replay of M2;
5. replay checker over status, contract/runner provenance, displacements,
   load path, contact gaps, active contacts, equilibrium and envelope.

The reference is independent at the observable level. It does not import
production contact or FEM/Newton routines and is not an independent global
nonlinear FEM solve.

## Results

| Case | DOFs | Accepted steps | Fallbacks | Status |
|---|---:|---:|---:|---|
| M1 H1 | 78 | 5/5 | 0 | PASS candidate + reference |
| M1 H2 | 129 | 5/5 | 0 | PASS candidate + reference |
| M1 H3 | 231 | 5/5 | 0 | PASS candidate + reference |
| M2 H3 | 240 | 5/5 | 0 | PASS candidate + reference |
| M3 fresh replay of M2 | 240 | 5/5 | 0 | PASS replay |

M2 final contact state is open, with a recomputed gap of
`0.004991784743427541`, production gap error `8.67e-17`, and no active contact.
The integrated load resultant error is `5.55e-17`.

The M3 checker reported zero differences for displacement, load path, contact
gaps, active contacts, equilibrium and envelope, and confirmed the independent
reference PASS status.

## Recorded envelopes and equilibrium

The most restrictive recorded local envelope is M2 H3:

```text
max PEEQ = 0.028219983125216
max corotational strain norm = 0.03396738272983241
```

The M2 H3 production result records:

```text
force balance relative error  = 7.52190064511669e-09
moment balance relative error = 7.96706507124153e-05
```

These values are preserved as raw observations. The frozen R2 contract does
not define an additional numerical equilibrium threshold gate, so this report
does not relabel them as a threshold PASS. Owner review should decide whether
the bounded R2 scope is acceptable with this limitation or whether a future
contract must add an explicit equilibrium gate.

M1 H3 records force/moment balance relative errors of
`4.9082574116796e-10` and `3.47111749135209e-10`, respectively. No general
mesh-convergence claim is made: the frozen hierarchy refines only the x axis.

## Verification and integrity

```text
TARGETED_TESTS = 39 passed
MYPY = PASS — 4 files
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
RUFF = NOT_AVAILABLE_IN_ENVIRONMENT
RAW_MANIFEST = qualification/0_2_9/wp10_tet10_surface_r2_manifest.json
```

All primary, reference, replay and QA artifacts are listed in the manifest
with SHA-256 hashes over canonical Git index blob bytes. Historical R1
failure/evidence is preserved separately and was not overwritten.

## Owner decision requested

```text
WP10_TET10_R2_CANDIDATE = PASS_CANDIDATE_WITH_LIMITATIONS
WP10_TET10_R2_OFFICIAL_POINTS = PENDING_OWNER_REVIEW
```

The candidate is bounded to TET10 corotational J2, the frozen load path, the
x-only M1 hierarchy, and initial-search frictionless penalty contact in M2.
It does not establish HEX20/TET4 generalization, friction or finite sliding,
dynamic/MPI/PETSc behavior, or correlation with Code_Aster/CalculiX.

`FINAL_SHA` is the Git commit that adds this report and its final manifest;
the exact commit is recorded in the handoff after that commit is created.
