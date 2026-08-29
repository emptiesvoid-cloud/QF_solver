# G05-B Family Coverage

## Status

This document records the controlled internal prequalification campaign for
`026-G05` modal, Newmark and harmonic routes. It does **not** close the
official gate. The distinction is deliberate:

`SUPPORTED` != `TESTED` != `VERIFIED` != `QUALIFIED`.

The generated numerical source of truth is
`qualification/vnv/g05b_family_coverage/summary.json`; its `vnv_manifest.json`
records the exact source SHA, runtime and artifact digests after a clean run.

## Executed campaign

| Analysis | Executed | Contract target | Result |
| --- | ---: | ---: | --- |
| Modal | 14 | 14 | PASS_INTERNAL_PREQUAL |
| Newmark | 32 time-level cases | 16 | PASS_INTERNAL_PREQUAL |
| Harmonic | 12 | 12 | PASS_INTERNAL_PREQUAL |

The modal catalog contains one baseline solve for each family and six declared
two-mode variants. The Newmark count represents four actual integrations per
baseline family at 30, 60, 120 and 240 steps per period. The harmonic catalog
contains one baseline sweep per family and four refined-grid sweeps. Every
listed case is executed; no `READY` status is counted as a result.

## Element x analysis matrix

| Element family | MOD | DYN | HAR | Qualification state |
| --- | --- | --- | --- | --- |
| TET4 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| TET10 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| HEX8 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| HEX20 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| BEAM2 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| MITC3 / MITC3+ | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | MITC3+ is the route label, not a second registry element |
| MITC4 | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | INTERNAL_PREQUAL, not closed |
| discrete | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | SUPPORTED / TESTED / VERIFIED | `SPRING_MASS` retained as legacy alias |

The compact family models exercise the common `solve_model` routes. They are
not a replacement for each element's static evidence, external correlation,
or the final Owner qualification decision.

## Refinement evidence

### Modal mesh

The campaign aggregates existing controlled mesh studies rather than claiming
that one-element family models constitute a universal mesh proof:

- `qualification/vnv/external/code_aster_modal_refinement_048/reference/summary.json`
- `qualification/vnv/tet10_stable_refinement/reference/summary.json`

The proposed policy is a final adjacent-level tracked-mode relative frequency
change of `<= 1e-2` over at least three compatible levels. This is marked
`PROPOSED_OWNER_REVIEW`, not approved.

### Newmark time

All baseline families run at 30/60/120/240 steps per period. The final
adjacent-level error is below the proposed one-percent band for the campaign;
the maximum over all levels is retained as a diagnostic because coarse starts
are intentionally less accurate. The proposed metric is

`||u_(dt/2) - u_dt|| / max(||u_(dt/2)||, u_floor) <= 1e-2`.

It applies only to the same physical interval, load history and compatible
output times. It remains `PROPOSED_OWNER_REVIEW`.

### Harmonic frequency

Baseline sweeps include zero, off-resonance, resonance and post-resonance
points. TET4, HEX8, MITC4 and discrete receive a refined grid with local
sampling around the first resonance. The proposed final-grid amplitude band is
`<= 1e-2`, with phase and peak-bin movement reported separately. It is not
applied at singular exact resonance or across changed damping/material data.

## Observed internal bounds

| Family | First modal frequency (Hz) | Modal residual | Newmark final-study residual | Newmark energy drift | Harmonic residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | 1.589281e3 | 1.78e-16 | 8.52e-08 | 5.76e-13 | 6.94e-11 |
| TET10 | 3.257056e3 | 1.28e-16 | 3.67e-08 | 4.73e-13 | 1.75e-16 |
| HEX8 | 1.591549 | 1.80e-16 | 1.54e-14 | 3.80e-13 | 7.02e-16 |
| HEX20 | 1.591549 | 1.80e-16 | 1.54e-14 | 3.80e-13 | 7.02e-16 |
| BEAM2 | 1.026597e1 | 1.18e-12 | 3.07e-12 | 2.36e-13 | 3.29e-11 |
| MITC3 | 8.454679 | 4.39e-09 | 6.56e-14 | 6.88e-13 | 2.09e-09 |
| MITC4 | 8.433214 | 1.32e-08 | 2.13e-12 | 3.55e-11 | 1.88e-09 |
| discrete | 1.591549 | 1.80e-16 | 1.54e-14 | 3.80e-13 | 7.02e-16 |

The identical HEX8/HEX20 values in this compact constrained block are an
observed result of this particular model and are not evidence of formulation
equivalence in general. Larger or element-specific studies remain necessary.

## Remaining G05 requirements

1. Owner approval of the three proposed refinement policies.
2. Family-specific external correlations and analytical oracles where the
   G05 contract requires them.
3. Complete gate aggregation with exact-SHA evidence and no promotion from
   internal prequalification to `QUALIFIED` by implication.

`026-G05` remains `NOT_STARTED` until its official contract is satisfied.
