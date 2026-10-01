---
doc_id: DOC-029-WP07-E-CLOSURE-001
revision: R1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-E refinement, replay and Owner closure contract

This document freezes the decision procedure for the final WP07 closure. It
is preparation only: no WP07-D structural solve, external solver run, point
award or maturity promotion is recorded here. The machine-readable contract
is [`wp07e_closure_contract.json`](../../../qualification/0_2_9/wp07e_closure_contract.json),
and the deterministic report builder is
[`build_wp07e_closure.py`](../../../scripts/build_wp07e_closure.py).

Source snapshot: `1cadaf6ab2bafe4b5da4731dc0fd06dec09bbb63`<br>
Owner status: `PASS_PREPARATION_WITH_OWNER_CORRECTION_R1`<br>
Correction: `OWNER_CORRECTION_R1`<br>
WP07-E formal points: `0/2`<br>
WP07 formal points: `0/10`
Validated total: `29/100`

## R1 derived-gate correction

The original Phase-0 candidate history is preserved: it accepted a
runtime-supplied `PASS`/`FAIL` label as a closure check. Owner Correction R1
removes that authority. The builder now requires raw observations and derives
each gate from those observations and the frozen thresholds below. A
runtime/reference `reported_status` is retained only as an audit field.

If a reported status disagrees with the independently derived status, the
report records `STATUS_MISMATCH` and cannot close as a pass. A raw failure is
still classified by its highest-precedence failure category (for example
`WP07_HOLD_STRUCTURAL_CONVERGENCE` or `WP07_FAIL_IDENTITY`) so the failed
gate is not hidden. A reported `FAIL` against raw passing data is incomplete.

The raw runtime schema is deliberately explicit. Each active-set track must
provide M2/M3 selected displacement, support-reaction, reaction-moment and
contact-resultant vectors, contact-region measure and declared scales; open
force, closed gap, pressure and `L_char`/`F_char`/`P_char`; vector equilibrium
terms; and replay fields. The penalty track additionally provides maximum
penetration, penetration scale, contact energy/applicability, WP07-B rollback
digests, accepted load-path statuses and restart metadata. WP07-C numerical
identity observations are consumed from `observed_results`, not from a status
label. Independent references provide raw QF/reference values, scales,
formulation-match flags and independent-implementation provenance.

Every runtime and reference record must relate to the same integrated source,
case-definition digest and R1 contract revision/digest. M2 and M3 must use the
runtime case digest; historical A/B/C contract source SHAs may differ. Missing,
mixed, stale or nonfinite values are `WP07_INCOMPLETE_EVIDENCE`.

## Closure inputs and fail-closed rule

WP07-E consumes immutable artifacts from WP07-A through WP07-D and two
independent formulation-specific references. The required IDs and paths are
declared in the JSON contract; they are not inferred from file names.

| Role | Artifact ID | Required content |
| --- | --- | --- |
| WP07-A contract | `WP07A-CONTACT-FORMULATION-001` | bounded regimes, scope and governance |
| WP07-B contract | `QF-029-WP07-B-CONTACT-EVALUATION-RESTART-001` | pure evaluation, rollback, digest and restart contract |
| WP07-C contract | `QF-029-WP07-C-CONTACT-IDENTITIES-001` | identities and frozen mathematical thresholds |
| WP07-D contract | `QF-029-WP07-D-STRUCTURAL-VNV-001` | physics, meshes, loads, thresholds and execution policy |
| WP07-D runtime | `QF-029-WP07-D-STRUCTURAL-EVIDENCE-001` | executed track results, provenance, policy binding and negative cases |
| active-set reference | `QF-029-WP07-D-REFERENCE-ACTIVE-SET-001` | independent KKT/unilateral implementation and matched results |
| penalty reference | `QF-029-WP07-D-REFERENCE-PENALTY-001` | independent fixed-normal penalty implementation and matched results |

Every artifact must carry its declared schema, WP07 identity, source SHA and
the fields listed in the machine-readable contract. Runtime and reference
artifacts additionally require provenance. A missing, malformed, nonfinite or
policy-mismatched field yields `WP07_INCOMPLETE_EVIDENCE`; it is never treated
as a passing or bounded value. No default observations are generated.

The R1 synthetic suite is deliberately numerical rather than label-based:
R1-01 exercises valid raw closure; R1-02 through R1-05 corrupt refinement,
equilibrium, replay and reference observations while leaving reported PASS
labels in place; R1-06 checks a wrong negative-case classification; R1-07 and
R1-08 check missing/nonfinite raw values; R1-09 checks governing-policy SHA
binding; R1-10 checks a stale case digest; R1-11 records a reported/derived
status mismatch; R1-12 rejects updated-search evidence; and R1-13/R1-14
exercise the explicit Owner-authorized exclusion rule and its anti-downgrade
guard. These tests produce no qualification data and award no points.

## Separate formulation tracks

The closure has two independent tracks. A result in one track cannot average
away a failure in the other.

### Track A — linear active set

`LINEAR_ACTIVE_SET_INITIAL_SEARCH` is limited to the WP07-A contract:
`linear_static`, small displacement, frictionless node-to-triangle contact,
fixed initial face/normal and the existing serial direct route. The required
gates are:

1. open zero force;
2. closed normalized gap `<= 1e-10`;
3. wrong-sign pressure `<= 1e-12`;
4. normalized complementarity `<= 1e-10`;
5. vector force equilibrium;
6. vector moment equilibrium;
7. M2→M3 structural refinement;
8. deterministic replay;
9. formulation-matched independent reference;
10. negative-case guards, finite observables and no silent PASS.

An open-only case may establish `PASS_OPEN_NO_CONTACT`, but cannot establish
closed contact qualification. Every required gate must be `PASS`; a required
`NOT_APPLICABLE` is incomplete unless the contract explicitly makes it
optional with a controlled reason.

### Track B — nonlinear penalty

`NONLINEAR_PENALTY_INITIAL_SEARCH` is limited to the existing fixed-normal,
frictionless, node-to-triangle penalty route. The required gates are:

1. open zero force;
2. WP07-C energy-gradient identity;
3. WP07-C tangent finite-difference identity;
4. no ghost force after reopen;
5. WP07-B rollback/re-evaluation;
6. vector force and moment equilibrium;
7. M2→M3 structural refinement;
8. accepted load path;
9. deterministic replay including restart metadata;
10. formulation-matched independent reference;
11. negative-case guards, finite observables and no silent PASS.

Penalty penetration is finite by formulation and does not have a zero-gap
requirement. Contact energy is `NOT_APPLICABLE` only where its declared
measurement/reference is genuinely invalid and the runtime record supplies a
nonempty reason; this does not erase any other required gate.

`UPDATED_SEARCH_FINITE_SLIDING` is excluded from both claims. It remains
`RESEARCH_ONLY`, uses an `APPROXIMATE_GEOMETRIC_CONTACT_TANGENT`, has no
energy claim and has `UNQUALIFIED_RESTART`. Attempted evidence from that path
is rejected as incomplete rather than downgraded to a bounded pass.

## Refinement policy

The structural contract freezes M2→M3 comparisons before execution. For a
scalar or vector observable, the relative delta is:

```text
abs(M3 - M2) / max(abs(M2), abs(M3), scale_floor)
```

The scale floor is `max(1e-14, 64 * machine_epsilon * declared_physical_scale)`.
The declared physical scale is `U_char`, `F_char`, `M_char`,
`penetration_scale`, `E_char` or `stress_scale` as appropriate. Vector values
use their Euclidean norm. A contact-region measure uses its declared
dimensionless measure and `max(abs(M2), abs(M3), 1)`.

Missing or nonfinite observables fail closed. The frozen candidate limits are:

| Track | Displacement | Reaction | Moment | Contact result. | Additional |
| --- | ---: | ---: | ---: | ---: | --- |
| Active set | 3% | 2% | 3% | 3% | contact region 10% |
| Penalty | 3% | 2% | 3% | 3% | penetration 5%, energy 5% when valid |

An optional averaged stress observable is limited to 12% and is not a
substitute for a missing required observable.

## Equilibrium gate

Both tracks require all three components of the following vector checks,
about the global origin `[0, 0, 0]`:

```text
force_error  = norm(R_support + F_external)
               / max(norm(R_support), norm(F_external), F_char, absolute_floor)
moment_error = norm(M_reaction + M_external)
               / max(norm(M_reaction), norm(M_external), M_char, absolute_floor)
```

Both limits are `1e-8`. A scalar force check is not sufficient. Missing
components or missing scales are incomplete evidence.

## Replay and restart gate

Replay uses relative tolerance `1e-12` and absolute floor `1e-14`:

```text
abs(a - b) <= max(1e-14, 1e-12 * max(abs(a), abs(b)))
```

The runtime evidence must compare final displacement, reaction resultant and
moment, contact resultant, qualitative contact status, active count where
meaningful, load-history length and elementwise load-factor history. Newton
iteration counts are exact when required by the governing execution policy;
terminal classification is exact. Penalty restart also records the WP07-B
contact-topology digest, model signature and accepted-state digest. A failed
replay is `WP07_HOLD_REPLAY`, not a limitation.

## Independent references

The active-set reference must independently assemble a KKT/unilateral
problem. The penalty reference must independently assemble the fixed-normal
penalty contribution with the same mesh, normal, gap, penalty, loads and
boundary conditions. Neither reference may call production contact routines.

`FORMULATION_MATCH = YES` is mandatory. Candidate comparison limits are:

| Observable | Limit |
| --- | ---: |
| displacement | 2% |
| reaction resultant | 2% |
| reaction moment | 2% |
| contact resultant | 3% |
| penalty penetration | 5% |
| active-set contact-region measure | 10% |

A stronger analytical reference may tighten a limit. No result-driven
threshold tuning is allowed. Missing, incompatible or out-of-limit reference
evidence produces `WP07_HOLD_REFERENCE`.

## Negative cases

Negative cases are safety evidence, not structural qualification passes:

| Case | Expected classification |
| --- | --- |
| reversed orientation | `VALIDATION_FAILURE` |
| open/no-contact | `PASS_OPEN_NO_CONTACT` without a closed-contact claim |
| excessive penetration | `CONTACT_PENETRATION_EXCESSIVE` or route-native failure |
| unsupported combination | `UNSUPPORTED_EXPLICIT` |
| nonfinite observable | `EVIDENCE_VALIDATION_FAILURE` |
| incompatible restart metadata | `RESTART_METADATA_MISMATCH` |

## Governing policy and integration train

WP07 physics is frozen, but the execution policy remains
`PENDING_GOVERNING_BRANCH_INTEGRATION`. The future runtime artifact must
record the governing policy SHA, Newton convergence contract, any approved
floor-aware convergence rule, linear backend, line-search policy and
load-step/retry policy. A mismatch is invalid evidence unless explicitly
reauthorized.

Formal WP07 closure is permitted only after:

1. WP04 governing branch closure;
2. clean integration of the WP07 candidate artifacts;
3. targeted revalidation on the integrated code;
4. WP07-D structural and independent-reference execution;
5. WP07-E evaluation and Owner decision.

## Final decision matrix

The report builder `scripts/build_wp07e_closure.py` consumes a JSON evidence
map and emits a deterministic JSON report. It reports only supplied values
and sets `fabricated_data` to `false`.

The fail-closed precedence, highest first, is:

1. `WP07_INCOMPLETE_EVIDENCE` — missing/malformed/provenance/policy input;
2. `WP07_FAIL_IDENTITY` — formulation identity, finiteness or no-silent-pass failure;
3. `WP07_FAIL_EQUILIBRIUM` — vector force or moment failure;
4. `WP07_HOLD_REPLAY` — replay/restart/state failure;
5. `WP07_HOLD_STRUCTURAL_CONVERGENCE` — refinement or structural failure;
6. `WP07_HOLD_REFERENCE` — missing/incompatible/out-of-limit reference;
7. `WP07_PARTIAL_ACTIVE_SET_ONLY` — active set closes and penalty is explicitly not covered;
8. `WP07_PARTIAL_PENALTY_ONLY` — penalty closes and active set is explicitly not covered;
9. `WP07_PASS_BOUNDED` — both tracks close within the declared scope.

A higher-precedence failure cannot be relabeled as `PARTIAL` or
`PASS_BOUNDED`. The evaluator also rejects a required check with an unknown
status and rejects `NOT_APPLICABLE` without a controlled reason.

## Point and governance policy

The candidate point split is WP07-A `1`, WP07-B `2`, WP07-C `2`, WP07-D `3`
and WP07-E `2`, for a total of `10`. This preparation artifact awards no
points: WP07-E remains `0/2`, WP07 remains `0/10`, and the validated total
remains `29/100`. No public maturity claim is promoted automatically.
