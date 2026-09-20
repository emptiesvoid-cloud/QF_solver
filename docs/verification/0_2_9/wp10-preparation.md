---
doc_id: DOC-029-WP10-PREP
revision: 1.0
status: frozen-execution
applicable_version: 0.2.9-development
---

# WP10 preparation — coupled nonlinear mechanics

## Starting point

WP07 is Owner-accepted at 10/10 within its bounded frictionless-contact
scope. WP09 is Owner-accepted at 8/8 for HEX8-only bounded corotational J2.
Those decisions do not qualify their coupled use. WP10 therefore starts as a
new contract and must not reuse either result as a coupled qualification.

```text
BASE_SHA = 04d1f1a60dcb4435c925cf5f788302da698aaf0e
BRANCH = codex/wp10-preparation
WP10_STATUS = FROZEN_EXECUTION
WP10_OFFICIAL_POINTS = 0/6
STRUCTURAL_SOLVES_RUN = AUTHORIZED_BOUNDED_HEX8_ONLY
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

## Proposed bounded scope

The first WP10 contract is deliberately limited to a serial CPU HEX8 route:

- bounded corotational J2 material from the accepted WP09 HEX8 scope;
- frictionless active-set contact from the accepted WP07 scope;
- small local strain, with the WP09 bound retained;
- fixed initial contact search/face/normal;
- no friction, finite sliding, updated search, MPI/PETSc, dynamics or general
  finite-strain plasticity claim.

The coupled route must prove both material and contact state transactions in
the same accepted increment. A passing WP07 or WP09 standalone result cannot
be substituted for a coupled result.

## Proposed evidence gates

These gates are frozen for this bounded execution. They do not expand the
accepted WP07/WP09 scopes:

1. M1 — coupled no-contact baseline: HEX8 corotational J2 with contact
   disabled/open; compare equilibrium, energy, deformation envelope and
   constitutive observables against an independent material recomputation.
2. M2 — coupled contact path: the same material route with frictionless
   contact activation, including open/contact transition, rollback and
   accepted-state consistency.
3. M3 — fresh-process replay and independent evidence check. The reference
   must not import production contact or constitutive routines; it may be an
   independent algebraic/material/contact recomputation and must be labelled
   accordingly, not as an independent global FEM solve.

Every gate must preserve raw evidence, contract/policy digests, source and
execution SHAs, finite observables, force/moment equilibrium, contact state,
plastic state, replay status and failure classification.

## Fail-closed rules

- No production implementation change during contract preparation.
- No threshold relaxation after seeing results.
- Missing coupled state, provenance or reference evidence means HOLD.
- A standalone PASS does not imply a coupled PASS.
- Any failed M1/M2 gate blocks the dependent M3 claim.
- WP10 points remain 0/6 until an explicit Owner decision.

## Next step

The contract is now frozen on the runner SHA recorded in the machine-readable
contract. M3 remains dependency-gated on passing M1/M2 references.
